Here’s a presentation-ready summary you can paste into your PPT agent.

Overview

Purpose: Admin dashboard + agentic AI for Simhastha operations (WhatsApp).
Channels: Ingests WhatsApp webhooks; replies via SAMWAD; realtime UI via WebSocket.
Domains: Sanitation feedback, emergencies, crowd notices, advisories.
Outcomes: Faster response, structured logging, targeted broadcasts, multilingual support.
Tech Stack

Backend: FastAPI, SQLModel (SQLite), httpx, langdetect, WebSocket, Pydantic.
AI: Ollama/OpenAI-compatible chat API (configurable AI_BASE_URL, AI_MODEL).
Frontend: React (Vite), Tailwind CSS, Axios, i18next.
Deploy: OpenLiteSpeed (static + reverse proxy), systemd service, dotenv-configured.
Architecture

Ingress: POST /whatsapp/webhook normalizes Meta WA payloads → DB.
Realtime: New messages broadcast to UI on /ws.
Egress: Replies/broadcasts via SAMWAD (send_via_samwad).
AI Services: Reply generation, intent classification, translation, summarization.
Agent Layer: Tool registry + guarded invocation with human approvals.
Core Functionalities

Live Chat: View conversations by phone, send admin replies, realtime updates.
Auto-Reply: Structured templates for sanitation/emergency; LLM fallback.
Issue Logging: Auto classify → log Feedback → auto-assign team.
Broadcasts: Heat/crowd/water/waste presets; targeted by zones/phone lists.
Zone ETAs: Per-zone SLA overrides drive ETAs in replies and UI badges.
Agentic Capabilities

Tool Registry: GET /api/agent/tools (name, risk, params).
Tool Invoke: POST /api/agent/tools/invoke (high-risk requires approval).
Approvals: List/decide approvals; executes on approve; audits kept.
Tools (highlights): classify_intent, summarize, translate, log/assign/update issues, set_contact_metadata, send_template, broadcast_notice, send_media, escalate_emergency.
Data Model

Message: chat log (phone, body, timestamp, language, is_from_admin).
Feedback: issues (category, status, location, zone, created_at).
AdminNotice: broadcast records.
ReplyTemplate: key/text for official templates.
Contact: per-phone metadata (zone, language_pref, name).
ZoneConfig: per-zone sanitation_eta_minutes, medical_eta_minutes.
FeedbackAssignment: issue → assignee mapping.
Approval: pending/approved/denied high-risk tool calls.
APIs (Selected)

Webhook: POST /whatsapp/webhook, verify GET /whatsapp/webhook.
Messages: GET /api/messages, GET /api/messages/by_phone/{phone}.
Replies: POST /api/reply, POST /api/tools/send_template, POST /api/tools/send_media.
Tools: classify/summarize/translate/log/update/assign/set_contact/escalate.
Broadcast: POST /api/tools/broadcast_notice.
Zone Config: GET/POST /api/admin/zone_config.
Metrics: GET /api/admin/metrics?since_hours=24.
Agent: GET /api/agent/tools, POST /api/agent/tools/invoke, approvals endpoints.
Frontend (Admin UI)

Conversations: chat list + message window; actions: Classify, Summarize, Set Zone; header shows Zone + San/Med ETAs.
Issues: table with filters (category/status/zone), status/assign actions; detail drawer with full conversation.
Broadcasts: message composer, presets, template picker.
Templates: CRUD manager for official texts.
Zone ETAs: table + upsert editor for per-zone overrides.
Metrics: cards (totals), top zones, issues-per-hour chart.
Dynamic Zone & ETAs

Zone Extraction: “Zone/Sector/Gate/Ghat N” from text; fallback to Contact or latest Feedback.
ETA Resolution: per-zone overrides (ZoneConfig) with env fallback; used in replies and UI.
Emergency Escalation: sends to configured ESCALATION_NUMBERS including normalized zone.
Security & Governance

Approvals: High-risk tools require human decision (unless AGENT_AUTO_APPROVE_HIGHRISK=true).
CORS: FRONTEND_ORIGIN enforced.
Config: .env flags for AI, ETAs, escalation, default assignees.
Roadmap: rate limits, content guardrails, role-based access.
Metrics & Observability

Metrics API: totals, by_category/status/zone, hourly time series.
Logs: webhook parsing, auto-reply/classify outcomes, escalation attempts.
Systemd journald compatible; health GET /healthz.
Deployment

Backend: systemd unit runs uvicorn on 127.0.0.1
; .env-driven config.
Frontend: Vite build served by OpenLiteSpeed (/dist), proxy /api + /ws.
Build Vars: VITE_API_BASE, VITE_WS_URL; AI configured by AI_BASE_URL (base ending /v1).
Demo Scenarios

Cleanliness: “Toilet near Gate 5…” → logs Feedback, replies “Team for Gate 5… ETA: 12 min”.
Emergency: “Fainted near Sector 9…” → reply “Help on the way. ETA: 7 min”, escalates ops.
Broadcasts: Heat advisory to selected zones; water update near Ghat 3.
Crowd: Redirect notice from overcrowded Gate 2 to Gate 5.
What’s Done

Fixed AI base URL logic; robust client.
Auto classify/log/assign + escalation; structured auto-replies with ETAs.
Zone extraction + per-zone ETA overrides.
Tool endpoints; agent registry + guarded invoke; approvals backend.
Admin UI pages (Conversations, Issues, Broadcasts, Templates, ZoneConfig, Metrics).
Roadmap (Next)

Approvals UI page; actioning pending requests in frontend.
Templates: variable interpolation ({zone}/{gate}) + preview in Broadcasts.
Conversations: Translate + Escalate buttons; template-send in chat.
Metrics: date-range filters, richer charts; by-category-per-zone heatmap.
Safety: RBAC, rate limiting, content guardrails, audit enhancements.
Knowledge grounding: small FAQ/RAG for info queries.
Quick Dev Checks

Tools: curl -s http://127.0.0.1:8000/api/agent/tools
Metrics: curl -s http://127.0.0.1:8000/api/admin/metrics
Zone ETA: curl -s 'http://127.0.0.1:8000/api/admin/zone_config'
Approvals: curl -s 'http://127.0.0.1:8000/api/admin/approvals?status=pending'
This structure should give your PPT agent enough detail to generate slides on architecture, features, AI agent behavior, and the deployment story.

