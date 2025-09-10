from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import httpx
from ..config import get_settings


settings = get_settings()


def default_system_prompt(company: Optional[str] = None) -> str:
    name = company or settings.APP_NAME
    return (
        "You are a highly engaging, positive festival assistant for Simhastha. "
        f"Greet users warmly and keep responses concise. You represent {name}. "
        "Understand intent (sanitation/emergency/info/guidance) and provide clear, empathetic replies. "
        "Do not invent facts. If you need to escalate, say you will inform the authorities."
    )


async def chat_completion(messages: List[Dict[str, str]], *,
                          model: Optional[str] = None,
                          temperature: Optional[float] = None,
                          max_tokens: Optional[int] = None) -> Dict[str, Any]:
    """Call an OpenAI/Ollama-compatible chat completions endpoint."""
    base = settings.AI_BASE_URL.rstrip('/')
    # Be tolerant if AI_BASE_URL was mistakenly set to the full endpoint
    url = base if base.endswith('/chat/completions') else f"{base}/chat/completions"
    payload = {
        "model": model or settings.AI_MODEL,
        "messages": messages,
        "temperature": settings.AI_TEMPERATURE if temperature is None else temperature,
        "max_tokens": settings.AI_MAX_TOKENS if max_tokens is None else max_tokens,
        # Ollama extras are ignored by OpenAI; harmless if unsupported
        "keep_alive": settings.AI_KEEP_ALIVE,
        "options": {"num_predict": settings.AI_MAX_TOKENS},
    }
    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


async def generate_reply(user_text: str, *, company: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    system = default_system_prompt(company)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_text},
    ]
    data = await chat_completion(messages)
    reply = (
        (data.get("choices") or [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    return reply or "", data


async def translate(text: str, target_language: str) -> Tuple[str, Dict[str, Any]]:
    system = (
        "You are a translation assistant. Translate the user's message to the target language faithfully, "
        "preserving meaning and tone. Return only the translated text."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Target language: {target_language}\nText: {text}"},
    ]
    data = await chat_completion(messages, temperature=0.2)
    out = (
        (data.get("choices") or [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    return out or "", data


async def classify_intent(text: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Classify text into one of predefined intents with confidence.

    Returns a tuple: (result, raw_response) where result is a dict
    like {"intent": str, "confidence": float, "reason": str}.
    """
    system = (
        "You are an intent classifier for civic festival support. "
        "Return STRICT JSON with fields: intent (one of: sanitation, emergency, info, guidance, directions, lost_found, other), "
        "confidence (0..1), reason (short). No extra text."
        "Interpret synonyms and Hindi phrases, e.g., 'kho gaya/kho gyi' => lost_found; 'how to reach/route/raasta' => guidance/directions."
    )
    user = f"Classify this message: {text}"
    data = await chat_completion([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], temperature=0.1, max_tokens=200)
    content = (
        (data.get("choices") or [{}])[0]
        .get("message", {})
        .get("content", "")
    ).strip()
    result: Dict[str, Any] = {"intent": "other", "confidence": 0.0, "reason": ""}
    # Try to parse JSON strictly, tolerate minor wrappers
    try:
        import json as _json
        # Extract first JSON object if wrapped
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            obj = _json.loads(content[start:end+1])
            intent = str(obj.get("intent", "other")).lower()
            if intent not in {"sanitation", "emergency", "info", "guidance", "directions", "lost_found", "other"}:
                intent = "other"
            conf = float(obj.get("confidence", 0) or 0)
            reason = str(obj.get("reason", ""))
            result = {"intent": intent, "confidence": max(0.0, min(1.0, conf)), "reason": reason}
    except Exception:
        pass
    return result, data


async def summarize_conversation(pairs: List[Tuple[str, str]]) -> Tuple[str, Dict[str, Any]]:
    """Summarize a conversation as a short brief.

    pairs: list of (speaker, text) where speaker is "user" or "admin".
    Returns (summary, raw_response).
    """
    system = (
        "You summarize short WhatsApp conversations succinctly (2-4 sentences). "
        "Mention key issues, requests, actions, and current status."
    )
    # Build a simple transcript
    transcript = "\n".join([f"{('User' if who=='user' else 'Admin')}: {msg}" for who, msg in pairs])
    user = f"Summarize this chat briefly:\n\n{transcript}"
    data = await chat_completion([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], temperature=0.2, max_tokens=250)
    out = (
        (data.get("choices") or [{}])[0]
        .get("message", {})
        .get("content", "")
    ).strip()
    return out, data
