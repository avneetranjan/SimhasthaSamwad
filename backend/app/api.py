from datetime import datetime
import json
from typing import List

import logging
from datetime import datetime
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Request, HTTPException, BackgroundTasks
from starlette.responses import PlainTextResponse
from fastapi import Query
from fastapi.encoders import jsonable_encoder
from sqlmodel import select, Session

from .database import get_session
from .models import Message, Feedback, AdminNotice, Contact, FeedbackAssignment, ZoneConfig, Approval, ReplyTemplate
from .schemas import (
    WebhookMessage,
    MessageOut,
    MessagesResponse,
    SendReplyIn,
    FeedbackIn,
    FeedbackOut,
    FeedbackListOut,
    NoticeIn,
    NoticeOut,
    TranslateIn,
    TranslateOut,
    AIReplyIn,
    AIReplyOut,
    IssueStatusUpdateIn,
    IssueAssignIn,
    IssueAssignOut,
    ContactUpdateIn,
    ContactOut,
    ClassifyIn,
    ClassifyOut,
    SummarizeIn,
    SummarizeOut,
    SendMediaIn,
    EscalateIn,
    ZoneConfigIn,
    ZoneConfigOut,
    TemplateIn,
    TemplateOut,
    AgentToolOut,
    AgentInvokeIn,
    AgentInvokeOut,
    ApprovalOut,
    ApprovalDecisionIn,
    RequestLocationIn,
    SendLocationPinIn,
)
from .services.language import detect_language
from .services.samwad import send_via_samwad, send_location_pin, request_location
from .services.ai import generate_reply, translate as ai_translate, classify_intent as ai_classify_intent, summarize_conversation as ai_summarize
from .config import get_settings
from .database import engine
from sqlmodel import Session as DBSession
from .websocket_manager import manager
import httpx
import mimetypes
from urllib.parse import urlparse, quote_plus
import re
import json as _json


router = APIRouter()
webhook_logger = logging.getLogger("simhastha.webhook")
settings = get_settings()

"""Templates CRUD, Agent registry + approvals, metrics, helpers"""

# Templates CRUD
@router.get("/api/templates", response_model=List[TemplateOut])
def list_templates(session: Session = Depends(get_session)):
    return session.exec(select(ReplyTemplate).order_by(ReplyTemplate.key.asc())).all()


@router.post("/api/templates", response_model=TemplateOut)
def create_template(data: TemplateIn, session: Session = Depends(get_session)):
    rec = ReplyTemplate(key=data.key, text=data.text)
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec


@router.put("/api/templates/{template_id}", response_model=TemplateOut)
def update_template(template_id: int, data: TemplateIn, session: Session = Depends(get_session)):
    rec = session.get(ReplyTemplate, template_id)
    if not rec:
        raise HTTPException(status_code=404, detail="template_not_found")
    rec.key = data.key
    rec.text = data.text
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec


@router.delete("/api/templates/{template_id}")
def delete_template(template_id: int, session: Session = Depends(get_session)):
    rec = session.get(ReplyTemplate, template_id)
    if not rec:
        raise HTTPException(status_code=404, detail="template_not_found")
    session.delete(rec)
    session.commit()
    return {"status": "ok"}



def _extract_field(d: Dict[str, Any], aliases: List[str]) -> Optional[Any]:
    lower = {k.lower(): v for k, v in d.items()}
    for name in aliases:
        if name in d:
            return d[name]
        # also try case-insensitive
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def _normalize_webhook(data: Dict[str, Any]) -> WebhookMessage:
    # Special case: Meta/WhatsApp Business style payload
    try:
        if isinstance(data, dict) and data.get("object") == "whatsapp_business_account" and "entry" in data:
            entries = data.get("entry") or []
            if entries:
                changes = (entries[0] or {}).get("changes") or []
                if changes:
                    value = (changes[0] or {}).get("value") or {}
                    messages = value.get("messages") or []
                    if messages:
                        m = messages[0]
                        phone = m.get("from") or ((value.get("contacts") or [{}])[0] or {}).get("wa_id")
                        body: Optional[str] = None
                        mtype = m.get("type")
                        if mtype == "text":
                            body = (m.get("text") or {}).get("body")
                        elif mtype == "location":
                            loc = m.get("location") or {}
                            lat = loc.get("latitude")
                            lng = loc.get("longitude")
                            if lat is not None and lng is not None:
                                body = f"geo:{lat},{lng}"
                        elif mtype == "button":
                            body = (m.get("button") or {}).get("text")
                        elif mtype == "interactive":
                            inter = m.get("interactive") or {}
                            itype = inter.get("type")
                            if itype == "button_reply":
                                body = (inter.get("button_reply") or {}).get("title")
                            elif itype == "list_reply":
                                body = (inter.get("list_reply") or {}).get("title")
                        # Fallbacks
                        if not body:
                            body = (m.get("text") or {}).get("body") or m.get("caption") or str(m.get("type", ""))

                        ts_raw = m.get("timestamp")
                        ts_val: Optional[datetime] = None
                        if ts_raw:
                            try:
                                ts_val = datetime.utcfromtimestamp(int(ts_raw))
                            except Exception:
                                ts_val = None

                        if phone and body:
                            return WebhookMessage(phone_number=str(phone), body=str(body), timestamp=ts_val)
    except Exception:
        # fall back to generic normalization
        pass

    phone_aliases = [
        "phone_number",
        "phoneNumber",
        "phone",
        "from",
        "sender",
        "mobile",
        "msisdn",
    ]
    body_aliases = [
        "body",
        "message",
        "text",
        "content",
        "msg",
    ]
    ts_aliases = [
        "timestamp",
        "time",
        "created_at",
        "createdAt",
        "date",
        "sentAt",
    ]

    phone = _extract_field(data, phone_aliases)
    body = _extract_field(data, body_aliases)
    ts = _extract_field(data, ts_aliases)

    if phone is None or body is None:
        raise HTTPException(status_code=422, detail={
            "error": "missing_fields",
            "required": ["phone_number", "body"],
            "received_keys": list(data.keys()),
        })

    norm: Dict[str, Any] = {
        "phone_number": str(phone),
        "body": str(body),
    }
    if ts is not None:
        norm["timestamp"] = ts  # pydantic will attempt to parse

    return WebhookMessage(**norm)


async def _auto_reply_task(phone_number: str, body: str) -> None:
    try:
        # Classify to decide if we should use a crisp civic template
        intent_res, _r = await ai_classify_intent(body)
        intent = (intent_res.get("intent") or "").lower()
        conf = float(intent_res.get("confidence") or 0)
        zone = _resolve_zone(phone_number, body)
        # Heuristic override for POC consistency
        def _hi(txt: str) -> Optional[str]:
            t = txt.lower()
            # Guidance first (e.g., lost my way)
            if any(k in t for k in [
                "how to reach", "how do i get", "route", "directions", "raasta", "rasta",
                "kaise pahu", "kaise pahun", "kaise jaa", "lost my way", "lost way", "rasta bhool"
            ]):
                return "guidance"
            # Lost & found only if an item mentioned
            if any(k in t for k in ["wallet", "purse", "phone", "mobile", "bag", "keys", "id card", "aadhaar", "pan card"]) or \
               any(k in t for k in ["kho gaya", "kho gyi", "gum gaya", "stolen", "missing item"]):
                return "lost_found"
            return None
        hint = _hi(body)
        if hint:
            intent = hint
            conf = max(conf, 0.8)

        reply_text: Optional[str] = None
        requested_loc = False
        if intent in {"guidance", "directions", "lost_found"} and not zone:
            try:
                await request_location(phone_number, "Please share your live location to assist you better")
                requested_loc = True
                reply_text = (
                    "I just sent a location request. Please tap Share Location, "
                    "or tell me your nearest gate/ghat/zone."
                )
            except Exception:
                pass
        if intent in {"sanitation", "emergency", "guidance", "info", "directions", "lost_found"} and conf >= 0.4:
            _structured = _compose_structured_reply2(intent=intent, zone=zone, original=body)
            if _structured:
                reply_text = f"{reply_text}\n{_structured}" if reply_text else _structured

        # Special case: guidance → generate steps
        if intent in {"guidance", "directions"}:
            dest = None
            t = body.lower()
            if "main ghat" in t:
                dest = "Main Ghat"
            else:
                m = re.search(r"ghat\s*(\d{1,2})", t)
                if m:
                    dest = f"Ghat {m.group(1)}"
            if zone or dest:
                steps = []
                if zone:
                    steps = [
                        f"Start at {zone}",
                        "Walk ~200m to the main corridor",
                        "Follow signs towards the plaza",
                        f"Proceed to {dest or 'destination'}",
                    ]
                else:
                    steps = [f"Head to nearest info kiosk and ask for directions to {dest or 'the venue'}"]
                reply_text = " → ".join(steps)

        # Special case: lost & found → register ticket and respond with ID
        # Guidance/directions: ensure concrete destination and helpful prompt
        if intent in {"guidance", "directions"}:
            t2 = body.lower()
            dest2: Optional[str] = None
            if "main ghat" in t2:
                dest2 = "Main Ghat"
            else:
                m = re.search(r"\bghat\s*(\d{1,2})\b", t2)
                if m:
                    dest2 = f"Ghat {m.group(1)}"
                else:
                    m2 = re.search(r"\b(zone|sector|gate)\s*([A-Za-z0-9-]{1,6})\b", t2)
                    if m2:
                        dest2 = f"{m2.group(1).title()} {m2.group(2)}"
                    elif "ghat" in t2:
                        dest2 = "Main Ghat"
            if zone and dest2:
                steps = [f"Start at {zone}", "Walk ~200m to the main corridor", "Follow signs towards the plaza", f"Proceed to {dest2}"]
                st = " → ".join(steps)
                reply_text = f"{reply_text}\n{st}" if reply_text and (st not in (reply_text or "")) else (reply_text or st)
            elif zone and not dest2 and not requested_loc:
                ask = ("I can guide you. Which destination (ghat/gate/zone) should I route to? If unsure, please share your live location and I will send directions.")
                reply_text = f"{reply_text}\n{ask}" if reply_text else ask
            elif not zone and dest2:
                st = f"Head to nearest info kiosk and ask for directions to {dest2}"
                reply_text = f"{reply_text}\n{st}" if reply_text else st

        if intent == "lost_found":
            with DBSession(engine) as s:
                fb = Feedback(
                    phone_number=phone_number,
                    category="lost_found",
                    status="new",
                    zone=zone,
                    location=zone,
                    message=body,
                )
                s.add(fb)
                s.commit()
                s.refresh(fb)
                reply_text = (
                    f"Lost & Found ticket created{(' for ' + zone) if zone else ''}. "
                    f"Ticket ID: {fb.id}. Please share your contact number to reach you if found."
                )

        # Fallback to LLM if we didn't produce a structured reply
        if not reply_text:
            reply_text, _raw = await generate_reply(body, company=settings.APP_NAME)
        if not reply_text:
            return

        _ = await send_via_samwad(phone_number, reply_text)
        # persist and broadcast as admin message
        with DBSession(engine) as s:
            msg = Message(
                phone_number=phone_number,
                body=reply_text,
                language=detect_language(reply_text),
                is_from_admin=True,
            )
            s.add(msg)
            s.commit()
            s.refresh(msg)
            await manager.broadcast(json.dumps(jsonable_encoder({"type": "message", "data": MessageOut.model_validate(msg)})))
    except Exception as e:
        webhook_logger.warning("auto-reply failed phone=%s error=%s", phone_number, str(e))


_zone_re = re.compile(r"\b(zone|sector|gate|ghat)\s*([A-Za-z0-9-]{1,6})\b", re.IGNORECASE)


def _extract_zone(text: str) -> Optional[str]:
    try:
        m = _zone_re.search(text or "")
        if m:
            kind = m.group(1)
            val = m.group(2)
            return f"{kind.title()} {val}"
    except Exception:
        pass
    return None


def _resolve_zone(phone_number: str, body: str) -> Optional[str]:
    z = _extract_zone(body)
    if z:
        return z
    try:
        with DBSession(engine) as s:
            c = s.get(Contact, phone_number)
            if c and c.zone:
                return c.zone
            fb = s.exec(select(Feedback).where(Feedback.phone_number == phone_number).order_by(Feedback.created_at.desc())).first()
            if fb and fb.zone:
                return fb.zone
    except Exception:
        pass
    return None


def _resolve_etas(zone: Optional[str]) -> tuple[int, int]:
    se = settings.SANITATION_ETA_MINUTES
    me = settings.MEDICAL_ETA_MINUTES
    if zone:
        try:
            with DBSession(engine) as s:
                cfg = s.get(ZoneConfig, zone)
                if cfg:
                    if cfg.sanitation_eta_minutes is not None:
                        se = cfg.sanitation_eta_minutes
                    if cfg.medical_eta_minutes is not None:
                        me = cfg.medical_eta_minutes
                else:
                    # Try numeric-only zone key and common labels
                    m = re.search(r"(\d{1,3})", zone)
                    if m:
                        n = m.group(1)
                        for key in (n, f"Zone {n}", f"Sector {n}", f"Gate {n}", f"Ghat {n}"):
                            cfg2 = s.get(ZoneConfig, key)
                            if cfg2:
                                if cfg2.sanitation_eta_minutes is not None:
                                    se = cfg2.sanitation_eta_minutes
                                if cfg2.medical_eta_minutes is not None:
                                    me = cfg2.medical_eta_minutes
                                break
        except Exception:
            pass
    return se, me


def _compose_structured_reply(*, intent: str, zone: Optional[str], original: str) -> str:
    ztxt = zone if zone else None
    if intent == "sanitation":
        eta, _ = _resolve_etas(zone)
        parts = ["Thank you for reporting.", "Our sanitation team has been notified."]
        if ztxt:
            parts.append(f"Team for {ztxt} is on the way.")
        parts.append(f"ETA: {eta} minutes. ✅🙏")
        return " ".join(parts)
    if intent == "emergency":
        _, eta = _resolve_etas(zone)
        parts = ["🚑 Help is on the way."]
        if ztxt:
            parts.append(f"Nearest medical unit is being alerted for {ztxt}.")
        parts.append(f"Estimated arrival: {eta} minutes.")
        parts.append("Please keep the area clear for paramedics and share live location if possible.")
        return " ".join(parts)
    if intent == "guidance":
        # Short, directional guidance
        return "Here to help. Please tell me your current location or nearest gate/landmark so I can guide you."
    if intent == "info":
        return "I can help with festival info (timings, routes, facilities). What would you like to know?"
    return ""


def _compose_structured_reply2(*, intent: str, zone: Optional[str], original: str) -> str:
    ztxt = zone if zone else None
    if intent == "sanitation":
        eta, _ = _resolve_etas(zone)
        parts = ["Thank you for reporting.", "Our sanitation team has been notified."]
        if ztxt:
            parts.append(f"Team for {ztxt} is on the way.")
        parts.append(f"ETA: {eta} minutes.")
        return " ".join(parts)
    if intent == "emergency":
        _, eta = _resolve_etas(zone)
        parts = ["Help is on the way."]
        if ztxt:
            parts.append(f"Nearest medical unit is being alerted for {ztxt}.")
        parts.append(f"Estimated arrival: {eta} minutes.")
        parts.append("Please keep the area clear for paramedics and share live location if possible.")
        return " ".join(parts)
    if intent == "guidance":
        return "Here to help. Please tell me your current location or nearest gate/landmark so I can guide you."
    if intent == "info":
        return "I can help with festival info (timings, routes, facilities). What would you like to know?"
    return ""


# Admin: Upsert zone config (ETA overrides)
@router.post("/api/admin/zone_config", response_model=ZoneConfigOut)
def upsert_zone_config(data: ZoneConfigIn, session: Session = Depends(get_session)):
    rec = session.get(ZoneConfig, data.zone)
    if rec:
        if data.sanitation_eta_minutes is not None:
            rec.sanitation_eta_minutes = data.sanitation_eta_minutes
        if data.medical_eta_minutes is not None:
            rec.medical_eta_minutes = data.medical_eta_minutes
        rec.updated_at = datetime.utcnow()
        session.add(rec)
        session.commit()
        session.refresh(rec)
        return rec
    rec = ZoneConfig(
        zone=data.zone,
        sanitation_eta_minutes=data.sanitation_eta_minutes,
        medical_eta_minutes=data.medical_eta_minutes,
    )
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec


@router.get("/api/admin/zone_config", response_model=List[ZoneConfigOut])
def list_zone_config(session: Session = Depends(get_session)):
    rows = session.exec(select(ZoneConfig).order_by(ZoneConfig.zone.asc())).all()
    return rows


async def _auto_classify_and_log_task(phone_number: str, body: str) -> None:
    try:
        result, _raw = await ai_classify_intent(body)
        intent = (result.get("intent") or "").lower()
        conf = float(result.get("confidence") or 0)
        # Only log for clear actionable categories
        # Only auto-log sanitation/emergency here to avoid double-logging.
        if intent in {"sanitation", "emergency"} and conf >= 0.4:
            zone = _resolve_zone(phone_number, body)
            with DBSession(engine) as s:
                fb = Feedback(
                    phone_number=phone_number,
                    category=intent,
                    status="new",
                    zone=zone,
                    location=(zone if zone else None),
                    message=body,
                )
                s.add(fb)
                s.commit()
                s.refresh(fb)

                # Auto-assign based on category if configured
                assignee = None
                if intent == "sanitation" and settings.ASSIGNEE_SANITATION:
                    assignee = settings.ASSIGNEE_SANITATION
                elif intent == "emergency" and settings.ASSIGNEE_EMERGENCY:
                    assignee = settings.ASSIGNEE_EMERGENCY
                if assignee:
                    rec = FeedbackAssignment(feedback_id=fb.id, assignee=assignee, note="auto-assigned")
                    s.add(rec)
                    s.commit()
                # Auto-escalate for emergencies to configured numbers
                if intent == "emergency":
                    raw = (settings.ESCALATION_NUMBERS or "").strip()
                    numbers = [n.strip() for n in raw.split(",") if n.strip()] if raw else []
                    for pn in numbers:
                        try:
                            msg = f"Emergency reported{(' in ' + zone) if zone else ''}: {body}\nPlease dispatch medical team."
                            _ = await send_via_samwad(pn, msg)
                        except Exception:
                            pass
                webhook_logger.info(
                    "auto-logged feedback id=%s intent=%s conf=%.2f zone=%s",
                    fb.id, intent, conf, zone or "-",
                )
        else:
            webhook_logger.info("intent=%s conf=%.2f not logged", intent or "other", conf)
    except Exception as e:
        webhook_logger.warning("auto-classify/log failed phone=%s error=%s", phone_number, str(e))


@router.post("/whatsapp/webhook", response_model=MessageOut)
async def whatsapp_webhook(request: Request, background: BackgroundTasks, session: Session = Depends(get_session)):
    # Minimal, safe logging of incoming webhook
    client_ip = getattr(request.client, "host", "-")
    ua = request.headers.get("user-agent", "-")

    data: Dict[str, Any]
    ctype = request.headers.get("content-type", "").lower()
    try:
        if "application/json" in ctype:
            data = await request.json()
        elif "application/x-www-form-urlencoded" in ctype or "multipart/form-data" in ctype:
            form = await request.form()
            data = dict(form)
        else:
            # Try JSON first, then form
            try:
                data = await request.json()
            except Exception:
                form = await request.form()
                data = dict(form)
    except Exception as e:
        webhook_logger.warning("webhook parse error ip=%s ua=%s error=%s", client_ip, ua, str(e))
        raise HTTPException(status_code=400, detail="invalid payload")

    webhook_logger.info("received webhook ip=%s ua=%s payload=%s", client_ip, ua, data)

    payload = _normalize_webhook(data)
    ts = payload.timestamp or datetime.utcnow()
    lang = detect_language(payload.body)
    msg = Message(
        phone_number=payload.phone_number,
        body=payload.body,
        timestamp=ts,
        language=lang,
        is_from_admin=False,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)

    await manager.broadcast(
        json.dumps(
            jsonable_encoder({
                "type": "message",
                "data": MessageOut.model_validate(msg),
            })
        )
    )

    # If user shared a geo location like "geo:lat,lng", reply with a Google Maps link
    try:
        if isinstance(payload.body, str) and payload.body.startswith("geo:"):
            coords = payload.body.split(":", 1)[1]
            lat, lng = coords.split(",", 1)
            # Infer destination from recent messages (simple heuristic)
            dest = "Main Ghat"
            prev = session.exec(
                select(Message)
                .where(Message.phone_number == payload.phone_number)
                .order_by(Message.timestamp.desc())
            ).all()
            txtblob = "\n".join([p.body or "" for p in prev[:5]])
            t = (txtblob or "").lower()
            if "main ghat" in t:
                dest = "Main Ghat"
            else:
                m = re.search(r"ghat\s*(\d{1,2})", t)
                if m:
                    dest = f"Ghat {m.group(1)}"
            link = f"https://www.google.com/maps/dir/?api=1&origin={lat},{lng}&destination={quote_plus(dest)}"
            gm_reply = f"Thanks for the location. Open directions to {dest}: {link}"
            _ = await send_via_samwad(payload.phone_number, gm_reply)
            msg2 = Message(
                phone_number=payload.phone_number,
                body=gm_reply,
                language=detect_language(gm_reply),
                is_from_admin=True,
            )
            session.add(msg2)
            session.commit()
            session.refresh(msg2)
            await manager.broadcast(
                json.dumps(jsonable_encoder({"type": "message", "data": MessageOut.model_validate(msg2)}))
            )
    except Exception:
        pass

    # Always trigger auto classify/log/assign in background
    background.add_task(_auto_classify_and_log_task, payload.phone_number, payload.body)

    # Optionally trigger AI auto-reply for pilgrim messages
    if settings.AI_AUTOREPLY:
        background.add_task(_auto_reply_task, payload.phone_number, payload.body)
    return msg


@router.get("/whatsapp/webhook")
async def whatsapp_webhook_verify(
    hub_mode: Optional[str] = Query(default=None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(default=None, alias="hub.challenge"),
    hub_token: Optional[str] = Query(default=None, alias="hub.verify_token"),
):
    # Simple verification endpoint compatible with Meta callback verification.
    # Optionally, compare hub_token to an environment variable if needed.
    if hub_mode == "subscribe" and hub_challenge:
        return PlainTextResponse(hub_challenge)
    return PlainTextResponse("ok")


@router.get("/api/messages", response_model=MessagesResponse)
def list_messages(session: Session = Depends(get_session)):
    results: List[Message] = session.exec(select(Message).order_by(Message.timestamp.asc())).all()
    return {"messages": [MessageOut.model_validate(r) for r in results]}


@router.get("/api/messages/by_phone/{phone_number}", response_model=MessagesResponse)
def list_messages_by_phone(phone_number: str, session: Session = Depends(get_session)):
    results: List[Message] = session.exec(
        select(Message).where(Message.phone_number == phone_number).order_by(Message.timestamp.asc())
    ).all()
    return {"messages": [MessageOut.model_validate(r) for r in results]}


@router.post("/api/reply", response_model=MessageOut)
async def send_reply(data: SendReplyIn, session: Session = Depends(get_session)):
    # Send to external API (stubbed)
    _ = await send_via_samwad(data.phone_number, data.body)

    # Store outgoing message
    msg = Message(
        phone_number=data.phone_number,
        body=data.body,
        timestamp=datetime.utcnow(),
        language=detect_language(data.body),
        is_from_admin=True,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)

    await manager.broadcast(
        json.dumps(
            jsonable_encoder({
                "type": "message",
                "data": MessageOut.model_validate(msg),
            })
        )
    )

    return msg


# Tools: log_issue
@router.post("/api/tools/log_issue", response_model=FeedbackOut)
async def log_issue(data: FeedbackIn, session: Session = Depends(get_session)):
    fb = Feedback(
        phone_number=data.phone_number,
        category=data.category,
        location=data.location,
        zone=data.zone,
        message=data.message,
        status="new",
    )
    session.add(fb)
    session.commit()
    session.refresh(fb)
    return fb


# Tools: list feedback (with simple filters)
@router.get("/api/tools/feedback/list", response_model=FeedbackListOut)
def list_feedback(
    category: Optional[str] = None,
    status: Optional[str] = None,
    zone: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    q = select(Feedback)
    if category:
        q = q.where(Feedback.category == category)
    if status:
        q = q.where(Feedback.status == status)
    if zone:
        q = q.where(Feedback.zone == zone)
    q = q.order_by(Feedback.created_at.desc()).offset(offset).limit(limit)
    rows = session.exec(q).all()
    return {"items": rows}


# Tools: get single feedback
@router.get("/api/tools/feedback/{feedback_id}", response_model=FeedbackOut)
def get_feedback(feedback_id: int, session: Session = Depends(get_session)):
    fb = session.get(Feedback, feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="feedback_not_found")
    return fb


# Tools: send_template (alias to reply endpoint; can later support template IDs)
@router.post("/api/tools/send_template", response_model=MessageOut)
async def send_template(data: SendReplyIn, session: Session = Depends(get_session)):
    return await send_reply(data, session)


# Tools: broadcast_notice
@router.post("/api/tools/broadcast_notice", response_model=NoticeOut)
async def broadcast_notice(data: NoticeIn, session: Session = Depends(get_session)):
    zones_csv = ",".join(data.zones) if data.zones else None
    notice = AdminNotice(message=data.message, zones=zones_csv)
    session.add(notice)
    session.commit()
    session.refresh(notice)

    # Optionally send to provided phone_numbers
    numbers = data.phone_numbers or []
    for pn in numbers:
        try:
            _ = await send_via_samwad(pn, data.message)
        except Exception as e:
            webhook_logger.warning("broadcast failed phone=%s error=%s", pn, str(e))
    return notice


# Tools: translate_message (stub; echoes text and labels languages)
@router.post("/api/tools/translate", response_model=TranslateOut)
async def translate_message(data: TranslateIn):
    detected = detect_language(data.text)
    try:
        translated, _raw = await ai_translate(data.text, data.target_language)
        return TranslateOut(text=translated or data.text, detected_language=detected, target_language=data.target_language)
    except Exception:
        return TranslateOut(text=data.text, detected_language=detected, target_language=data.target_language)


@router.post("/api/ai/reply", response_model=AIReplyOut)
async def ai_reply(data: AIReplyIn):
    reply, raw = await generate_reply(data.text, company=settings.APP_NAME)
    return AIReplyOut(reply=reply, raw=raw)


# Resolve context (zone + ETAs) for a phone
@router.get("/api/tools/resolve_context")
def resolve_context(phone_number: str):
    zone = _resolve_zone(phone_number, "")
    se, me = _resolve_etas(zone)
    return {"zone": zone, "sanitation_eta_minutes": se, "medical_eta_minutes": me}


# Phase 1+: update issue status
@router.post("/api/tools/update_issue_status", response_model=FeedbackOut)
def update_issue_status(data: IssueStatusUpdateIn, session: Session = Depends(get_session)):
    fb = session.get(Feedback, data.id)
    if not fb:
        raise HTTPException(status_code=404, detail="feedback_not_found")
    fb.status = data.status
    session.add(fb)
    session.commit()
    session.refresh(fb)
    return fb


# Phase 1+: assign issue
@router.post("/api/tools/assign_issue", response_model=IssueAssignOut)
def assign_issue(data: IssueAssignIn, session: Session = Depends(get_session)):
    # find existing assignment
    existing = session.exec(select(FeedbackAssignment).where(FeedbackAssignment.feedback_id == data.feedback_id)).first()
    if existing:
        existing.assignee = data.assignee
        existing.note = data.note
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    rec = FeedbackAssignment(feedback_id=data.feedback_id, assignee=data.assignee, note=data.note)
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec


# Phase 1+: list assignments
@router.get("/api/tools/assignments", response_model=List[IssueAssignOut])
def list_assignments(feedback_id: Optional[int] = None, session: Session = Depends(get_session)):
    q = select(FeedbackAssignment)
    if feedback_id is not None:
        q = q.where(FeedbackAssignment.feedback_id == feedback_id)
    q = q.order_by(FeedbackAssignment.assigned_at.desc())
    return session.exec(q).all()


# Admin metrics
@router.get("/api/admin/metrics")
def admin_metrics(since_hours: int = 24, session: Session = Depends(get_session)):
    # Load all rows (simple approach). Optionally filter to recent window for hourly series.
    rows: List[Feedback] = session.exec(select(Feedback)).all()

    by_category: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    by_zone: Dict[str, int] = {}
    total = 0
    resolved = 0
    for fb in rows:
        total += 1
        by_category[fb.category] = by_category.get(fb.category, 0) + 1
        by_status[fb.status] = by_status.get(fb.status, 0) + 1
        if fb.zone:
            by_zone[fb.zone] = by_zone.get(fb.zone, 0) + 1
        if fb.status == "resolved":
            resolved += 1

    # Hourly timeseries for the last N hours
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    start = now - timedelta(hours=max(1, since_hours))
    # Initialize buckets
    buckets: Dict[str, int] = {}
    cursor = start.replace(minute=0, second=0, microsecond=0)
    end_hour = now.replace(minute=0, second=0, microsecond=0)
    while cursor <= end_hour:
        label = cursor.strftime("%Y-%m-%d %H:00")
        buckets[label] = 0
        cursor += timedelta(hours=1)
    # Fill buckets
    for fb in rows:
        ts = fb.created_at
        if ts >= start:
            label = ts.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:00")
            if label in buckets:
                buckets[label] += 1
    hourly = [{"hour": k, "count": buckets[k]} for k in sorted(buckets.keys())]

    return {
        "generated_at": now.isoformat() + "Z",
        "since_hours": since_hours,
        "total_issues": total,
        "resolved": resolved,
        "by_category": by_category,
        "by_status": by_status,
        "by_zone": by_zone,
        "hourly": hourly,
    }


# Phase 1+: contact metadata upsert
@router.post("/api/tools/set_contact_metadata", response_model=ContactOut)
def set_contact_metadata(data: ContactUpdateIn, session: Session = Depends(get_session)):
    existing = session.get(Contact, data.phone_number)
    if existing:
        if data.name is not None:
            existing.name = data.name
        if data.zone is not None:
            existing.zone = data.zone
        if data.language_pref is not None:
            existing.language_pref = data.language_pref
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    contact = Contact(
        phone_number=data.phone_number,
        name=data.name,
        zone=data.zone,
        language_pref=data.language_pref,
    )
    session.add(contact)
    session.commit()
    session.refresh(contact)
    return contact


# Phase 1+: classify intent
@router.post("/api/tools/classify_intent", response_model=ClassifyOut)
async def classify_intent(data: ClassifyIn):
    result, _raw = await ai_classify_intent(data.text)
    return ClassifyOut(**result)


# Phase 1+: summarize conversation
@router.post("/api/tools/summarize", response_model=SummarizeOut)
async def summarize(data: SummarizeIn, session: Session = Depends(get_session)):
    q = select(Message).where(Message.phone_number == data.phone_number).order_by(Message.timestamp.asc())
    msgs: List[Message] = session.exec(q).all()
    if data.max_messages and len(msgs) > data.max_messages:
        msgs = msgs[-data.max_messages :]
    pairs = [("admin" if m.is_from_admin else "user", m.body) for m in msgs]
    summary, _raw = await ai_summarize(pairs)
    return SummarizeOut(summary=summary)


# Phase 1+: send media via URL
@router.post("/api/tools/send_media", response_model=MessageOut)
async def send_media(data: SendMediaIn, session: Session = Depends(get_session)):
    # Fetch image and send via Samwad
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(data.image_url)
            resp.raise_for_status()
            content = resp.content
            mime = resp.headers.get("content-type") or mimetypes.guess_type(data.image_url)[0] or "application/octet-stream"
            path = urlparse(data.image_url).path
            fname = (path.rsplit("/", 1)[-1] or "image").split("?")[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"image_fetch_failed: {str(e)}")

    _ = await send_via_samwad(data.phone_number, data.body or "", image=(fname, content, mime))

    msg = Message(
        phone_number=data.phone_number,
        body=data.body or f"[sent image] {fname}",
        language=detect_language(data.body or ""),
        is_from_admin=True,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    await manager.broadcast(json.dumps(jsonable_encoder({"type": "message", "data": MessageOut.model_validate(msg)})))
    return msg


# Phase 1+: escalate emergency
@router.post("/api/tools/escalate_emergency")
async def escalate_emergency(data: EscalateIn):
    numbers = data.phone_numbers or []
    if not numbers:
        raw = (settings.ESCALATION_NUMBERS or "").strip()
        if raw:
            numbers = [n.strip() for n in raw.split(",") if n.strip()]
    if not numbers:
        raise HTTPException(status_code=400, detail="no_numbers_provided")
    failures: List[str] = []
    for pn in numbers:
        try:
            msg = data.message
            if data.severity or data.location:
                parts = [msg]
                if data.severity:
                    parts.append(f"[severity: {data.severity}]")
                if data.location:
                    parts.append(f"[location: {data.location}]")
                msg = " ".join(parts)
            resp = await send_via_samwad(pn, msg)
            if (resp or {}).get("status") != "ok":
                failures.append(pn)
        except Exception:
            failures.append(pn)
    return {"status": "ok", "failed": failures}


# Location tools
@router.post("/api/tools/request_location")
async def api_request_location(data: RequestLocationIn):
    out = await request_location(data.phone_number, data.body or "Please share your location")
    return out


@router.post("/api/tools/send_location")
async def api_send_location(data: SendLocationPinIn):
    out = await send_location_pin(
        data.phone_number,
        data.latitude,
        data.longitude,
        name=data.name,
        address=data.address,
    )
    return out


_HIGH_RISK = {"send_template", "broadcast_notice", "send_media", "escalate_emergency"}


def _tools_registry() -> List[Dict[str, Any]]:
    return [
        {"name": "classify_intent", "risk": "low", "description": "Classify text intent.", "params": {"text": "string"}},
        {"name": "summarize", "risk": "low", "description": "Summarize conversation for a phone.", "params": {"phone_number": "string", "max_messages": "int"}},
        {"name": "translate", "risk": "low", "description": "Translate text.", "params": {"text": "string", "target_language": "string"}},
        {"name": "log_issue", "risk": "medium", "description": "Log sanitation/emergency/info issue.", "params": {"phone_number": "string", "category": "string", "message": "string", "location": "string?", "zone": "string?"}},
        {"name": "update_issue_status", "risk": "medium", "description": "Update issue status.", "params": {"id": "int", "status": "new|in_progress|resolved"}},
        {"name": "assign_issue", "risk": "medium", "description": "Assign issue.", "params": {"feedback_id": "int", "assignee": "string", "note": "string?"}},
        {"name": "set_contact_metadata", "risk": "medium", "description": "Upsert contact zone/language/name.", "params": {"phone_number": "string", "zone": "string?", "language_pref": "string?", "name": "string?"}},
        {"name": "send_template", "risk": "high", "description": "Send a templated message to a phone.", "params": {"phone_number": "string", "body": "string"}},
        {"name": "broadcast_notice", "risk": "high", "description": "Broadcast message to zones/phones.", "params": {"message": "string", "zones": "string[]?", "phone_numbers": "string[]?"}},
        {"name": "send_media", "risk": "high", "description": "Send image via URL.", "params": {"phone_number": "string", "image_url": "string", "body": "string?"}},
        {"name": "escalate_emergency", "risk": "high", "description": "Notify ops escalation numbers.", "params": {"message": "string", "phone_numbers": "string[]?", "severity": "string?", "location": "string?"}},
        {"name": "resolve_context", "risk": "low", "description": "Resolve zone + ETAs for a phone.", "params": {"phone_number": "string"}},
        {"name": "request_location", "risk": "low", "description": "Ask user to share live location.", "params": {"phone_number": "string", "body": "string?"}},
        {"name": "send_location", "risk": "low", "description": "Send a location pin.", "params": {"phone_number": "string", "latitude": "float", "longitude": "float", "name": "string?", "address": "string?"}},
        # POC tools
        {"name": "get_sanitation_facility", "risk": "low", "description": "List nearby toilets/water/cleaning crews (dummy).", "params": {"zone": "string?", "phone_number": "string?"}},
        {"name": "get_festival_schedule", "risk": "low", "description": "Festival schedule for today (dummy).", "params": {"date": "string?"}},
        {"name": "get_route_to_venue", "risk": "low", "description": "Route guidance (dummy).", "params": {"origin": "string?", "destination": "string"}},
        {"name": "register_lost_item", "risk": "medium", "description": "Register lost & found ticket (stores as feedback).", "params": {"phone_number": "string", "description": "string", "zone": "string?"}},
        {"name": "escalate_to_authorities", "risk": "high", "description": "Alias to emergency escalation.", "params": {"message": "string", "phone_numbers": "string[]?", "severity": "string?", "location": "string?"}},
    ]


@router.get("/api/agent/tools", response_model=List[AgentToolOut])
def agent_tools():
    return _tools_registry()


_INTENT_TOOL_MAP: Dict[str, str] = {
    "sanitation": "get_sanitation_facility",
    "emergency": "escalate_to_authorities",
    "info": "get_festival_schedule",
    "guidance": "get_route_to_venue",
    "directions": "get_route_to_venue",
    "lost_found": "register_lost_item",
}


@router.get("/api/agent/intent_map")
def intent_map():
    return _INTENT_TOOL_MAP


async def _execute_tool(tool: str, args: Dict[str, Any], session: Session) -> Dict[str, Any]:
    if tool == "classify_intent":
        out, _ = await ai_classify_intent(args.get("text", ""))
        return out
    if tool == "summarize":
        pn = args.get("phone_number")
        max_messages = int(args.get("max_messages") or 50)
        q = select(Message).where(Message.phone_number == pn).order_by(Message.timestamp.asc())
        msgs: List[Message] = session.exec(q).all()
        if len(msgs) > max_messages:
            msgs = msgs[-max_messages:]
        pairs = [("admin" if m.is_from_admin else "user", m.body) for m in msgs]
        summary, _raw = await ai_summarize(pairs)
        return {"summary": summary}
    if tool == "translate":
        out, _ = await ai_translate(args.get("text", ""), args.get("target_language", "en"))
        return {"text": out}
    if tool == "log_issue":
        fb = Feedback(
            phone_number=args.get("phone_number", ""),
            category=args.get("category", "info"),
            status="new",
            location=args.get("location"),
            zone=args.get("zone"),
            message=args.get("message"),
        )
        session.add(fb); session.commit(); session.refresh(fb)
        return {"id": fb.id}
    if tool == "update_issue_status":
        fb = session.get(Feedback, int(args.get("id")))
        if not fb:
            raise HTTPException(status_code=404, detail="feedback_not_found")
        fb.status = args.get("status", fb.status)
        session.add(fb); session.commit(); session.refresh(fb)
        return {"id": fb.id, "status": fb.status}
    if tool == "assign_issue":
        existing = session.exec(select(FeedbackAssignment).where(FeedbackAssignment.feedback_id == int(args.get("feedback_id")))).first()
        if existing:
            existing.assignee = args.get("assignee")
            existing.note = args.get("note")
            session.add(existing); session.commit(); session.refresh(existing)
            return {"id": existing.id}
        rec = FeedbackAssignment(feedback_id=int(args.get("feedback_id")), assignee=args.get("assignee"), note=args.get("note"))
        session.add(rec); session.commit(); session.refresh(rec)
        return {"id": rec.id}
    if tool == "set_contact_metadata":
        pn = args.get("phone_number")
        c = session.get(Contact, pn)
        if c is None:
            c = Contact(phone_number=pn)
        if "zone" in args and args.get("zone") is not None:
            c.zone = args.get("zone")
        if "language_pref" in args and args.get("language_pref") is not None:
            c.language_pref = args.get("language_pref")
        if "name" in args and args.get("name") is not None:
            c.name = args.get("name")
        session.add(c); session.commit(); session.refresh(c)
        return {"phone_number": c.phone_number, "zone": c.zone, "language_pref": c.language_pref, "name": c.name}
    if tool == "send_template":
        data = SendReplyIn(phone_number=args.get("phone_number"), body=args.get("body", ""))
        saved = await send_reply(data, session)
        return {"message_id": saved.id}
    if tool == "broadcast_notice":
        data = NoticeIn(message=args.get("message", ""), zones=args.get("zones"), phone_numbers=args.get("phone_numbers"))
        out = await broadcast_notice(data, session)  # type: ignore
        return {"id": out.id}
    if tool == "send_media":
        data = SendMediaIn(phone_number=args.get("phone_number"), image_url=args.get("image_url"), body=args.get("body"))
        out = await send_media(data, session)  # type: ignore
        return {"message_id": out.id}
    if tool == "escalate_emergency":
        data = EscalateIn(message=args.get("message", ""), phone_numbers=args.get("phone_numbers"), severity=args.get("severity"), location=args.get("location"))
        out = await escalate_emergency(data)  # type: ignore
        return out
    if tool == "resolve_context":
        pn = args.get("phone_number")
        zone = _resolve_zone(pn, "")
        se, me = _resolve_etas(zone)
        return {"zone": zone, "sanitation_eta_minutes": se, "medical_eta_minutes": me}
    if tool == "request_location":
        pn = args.get("phone_number")
        body = args.get("body") or "Please share your location"
        return await request_location(pn, body)
    if tool == "send_location":
        return await send_location_pin(
            args.get("phone_number"),
            float(args.get("latitude")),
            float(args.get("longitude")),
            name=args.get("name"),
            address=args.get("address"),
        )
    # POC tools with dummy data
    if tool == "get_sanitation_facility":
        zone = args.get("zone")
        if not zone and args.get("phone_number"):
            zone = _resolve_zone(args.get("phone_number"), "")
        facilities = _POC_SAN_FACILITIES.get(zone or "", [])
        return {"zone": zone, "facilities": facilities}
    if tool == "get_festival_schedule":
        return {"schedule": _POC_SCHEDULE}
    if tool == "get_route_to_venue":
        origin = args.get("origin") or args.get("zone") or args.get("from")
        dest = args.get("destination") or "Main Ghat"
        steps = []
        if origin:
            steps = [
                f"Start at {origin}",
                "Walk 200m to the main corridor",
                "Follow signs towards the plaza",
                f"Proceed to {dest}",
            ]
        else:
            steps = ["Head to the nearest info kiosk", f"Ask for directions to {dest}"]
        return {"origin": origin, "destination": dest, "steps": steps}
    if tool == "register_lost_item":
        # Store as Feedback with category 'lost_found'
        fb = Feedback(
            phone_number=args.get("phone_number", ""),
            category="lost_found",
            status="new",
            zone=args.get("zone"),
            message=f"Lost item: {args.get('description','')}",
        )
        session.add(fb); session.commit(); session.refresh(fb)
        return {"ticket_id": fb.id, "status": fb.status}
    if tool == "escalate_to_authorities":
        data = EscalateIn(message=args.get("message", ""), phone_numbers=args.get("phone_numbers"), severity=args.get("severity"), location=args.get("location"))
        out = await escalate_emergency(data)  # type: ignore
        return out
    raise HTTPException(status_code=400, detail="unknown_tool")


@router.post("/api/agent/tools/invoke", response_model=AgentInvokeOut)
async def agent_invoke(data: AgentInvokeIn, session: Session = Depends(get_session)):
    tool = data.tool
    args = data.args or {}
    high_risk = tool in _HIGH_RISK
    if data.dry_run:
        return AgentInvokeOut(status="ok", result={"dry_run": True, "tool": tool, "args": args})
    if high_risk and not settings.AGENT_AUTO_APPROVE_HIGHRISK:
        rec = Approval(tool_name=tool, args_json=_json.dumps(args), status="pending")
        session.add(rec); session.commit(); session.refresh(rec)
        return AgentInvokeOut(status="pending", approval_id=rec.id)
    try:
        result = await _execute_tool(tool, args, session)
        return AgentInvokeOut(status="ok", result=result)
    except HTTPException as e:
        return AgentInvokeOut(status="error", error=str(e.detail))
    except Exception as e:
        return AgentInvokeOut(status="error", error=str(e))


@router.get("/api/admin/approvals", response_model=List[ApprovalOut])
def approvals(status: Optional[str] = None, limit: int = 100, offset: int = 0, session: Session = Depends(get_session)):
    q = select(Approval)
    if status:
        q = q.where(Approval.status == status)
    q = q.order_by(Approval.created_at.desc()).offset(offset).limit(limit)
    rows = session.exec(q).all()
    out = []
    for r in rows:
        out.append(ApprovalOut(
            id=r.id,
            tool_name=r.tool_name,
            args=_json.loads(r.args_json or "{}"),
            status=r.status,
            result=_json.loads(r.result_json) if r.result_json else None,
            created_at=r.created_at,
            decided_at=r.decided_at,
            decided_by=r.decided_by,
        ))
    return out


@router.post("/api/admin/approvals/{approval_id}/decision", response_model=ApprovalOut)
async def approval_decision(approval_id: int, data: ApprovalDecisionIn, session: Session = Depends(get_session)):
    rec = session.get(Approval, approval_id)
    if not rec:
        raise HTTPException(status_code=404, detail="approval_not_found")
    if rec.status != "pending":
        raise HTTPException(status_code=400, detail="already_decided")
    if data.approve:
        try:
            result = await _execute_tool(rec.tool_name, _json.loads(rec.args_json or "{}"), session)
            rec.result_json = _json.dumps(result)
            rec.status = "approved"
        except Exception as e:
            rec.result_json = _json.dumps({"error": str(e)})
            rec.status = "approved"
    else:
        rec.status = "denied"
    rec.decided_at = datetime.utcnow()
    rec.decided_by = data.actor
    session.add(rec); session.commit(); session.refresh(rec)
    return ApprovalOut(
        id=rec.id,
        tool_name=rec.tool_name,
        args=_json.loads(rec.args_json or "{}"),
        status=rec.status,
        result=_json.loads(rec.result_json) if rec.result_json else None,
        created_at=rec.created_at,
        decided_at=rec.decided_at,
        decided_by=rec.decided_by,
    )
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; optionally receive pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

"""POC dummy datasets for agent tools."""
_POC_SAN_FACILITIES: Dict[str, List[Dict[str, Any]]] = {
    "Zone 4": [
        {"name": "Toilet Block T4-A", "type": "toilet", "distance_m": 120, "location": "Gate 5, east side"},
        {"name": "Drinking Water W4-2", "type": "water", "distance_m": 200, "location": "Near info kiosk"},
        {"name": "Cleaning Crew C4", "type": "cleaning", "distance_m": 350, "location": "Behind food stalls"},
    ],
    "Sector 9": [
        {"name": "First Aid SA-9", "type": "first_aid", "distance_m": 180, "location": "Opp. food court"},
        {"name": "Toilet Block T9-B", "type": "toilet", "distance_m": 240, "location": "Lane 3"},
    ],
}

_POC_SCHEDULE: List[Dict[str, Any]] = [
    {"time": "06:00", "event": "Morning Aarti", "venue": "Main Ghat"},
    {"time": "10:30", "event": "Cultural Procession", "venue": "Gate 2 → Plaza"},
    {"time": "16:00", "event": "Discourse", "venue": "Hall B"},
    {"time": "19:00", "event": "Evening Aarti", "venue": "Main Ghat"},
]
