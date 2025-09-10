Phase 1 — Foundations

Tool registry: JSON-schema contracts for log_issue, send_template, broadcast_notice, translate (reuse existing endpoints).
Agent API: POST /api/agent/act taking goal + context; returns steps, tool calls, results.
Context store: thread/session model (messages, roles, metadata like zone, language).
Structured outputs: enforce function-calling / tool-use via schema (OpenAI/Ollama-compatible).
Config toggles: env flags for autonomy, timeouts, max-steps, model/fallbacks.
Security: API key/JWT for agent endpoints; rate limits.
Phase 2 — Orchestration

Planner/executor: loop of plan → choose tool → execute → observe → revise (max N steps).
Router/fallbacks: local Ollama first; fallback to cloud; per-tool timeouts and retries.
Guardrails: input/output validation, prompt templates, content/PII filters.
Error handling: partial failure recovery, safe abort with user-facing explanation.
Memory: short-term (thread) and optional long-term (summary vectors/notes).
Deterministic tool calls: idempotency keys; replay protection.
Phase 3 — UX & Ops

HITL approvals: UI to preview tool calls (e.g., broadcast/templated send) with approve/deny.
Agent timeline UI: step-by-step reasoning summaries, tool inputs/outputs, and final answer.
Notices/Template UI: manage templates, categories, zones; invoke via agent or manual.
Metrics: dashboard for issues logged, resolutions, broadcasts, SLA, tool error rates.
Observability: structured logs, request IDs, prompt/tool-call traces, redaction.
Admin controls: toggle autonomy per action, per-category routing rules.
Data & Models

Extend Message with source, zone, intent, confidence.
Add AgentRun + ToolCall entities for audit.
Multilingual: auto-detect + translate in/out; persist detected language and normalized text.
Migrations: safe schema updates, backfill where possible.
Testing & Validation

Unit tests: prompt templates, tool schemas, planner policies.
Integration tests: mocked Samwad + AI; golden outputs for common flows.
Eval harness: scenario set (sanitation/emergency/in

MVP Tool Set (Phase 1)

send_message: send WhatsApp/Samwad message to one number; inputs: phone_number, body, optional image/url; high-risk (approval).
send_template: send a predefined template with variables; inputs: phone_number(s), template_key, variables; high-risk.
broadcast_notice: broadcast to zones/phones; inputs: message, zones[], phone_numbers[]; high-risk.
log_issue: persist feedback/complaint; inputs: phone_number, category, message, location, zone; medium-risk.
update_issue_status: change status; inputs: id, status(new|in_progress|resolved), optional note; medium-risk.
get_issue_status: fetch one issue; inputs: id; low-risk.
translate_text: translate; inputs: text, target_language; low-risk.
detect_language: detect; inputs: text; low-risk.
get_conversation: fetch messages for a phone; inputs: phone_number; low-risk.
list_conversations: list phones with last message; inputs: optional filters (zone, since); low-risk.
Phase 1+ (Useful Next)

assign_issue: assign ticket; inputs: id, assignee; medium-risk.
escalate_emergency: notify ops channel; inputs: phone_number, message, location, severity; high-risk (approval).
send_media: image/doc push; inputs: phone_number, caption, media_url or upload_id; high-risk.
summarize_conversation: produce short summary; inputs: phone_number, window (n messages); low-risk.
classify_intent: categorize message; inputs: text; output: intent, confidence; low-risk.
set_contact_metadata: update zone/language; inputs: phone_number, zone?, language_pref?; medium-risk.
retrieve_faq: semantic search in FAQ; inputs: query, top_k; low-risk.
generate_qr: create QR for zone/desk; inputs: data, label; returns url/blob; low-risk.
schedule_followup: reminder/task; inputs: phone_number, when, note; medium-risk.
Admin/HITL Controls

request_approval: create approval for a pending action; inputs: action_id, summary; low-risk.
tools.list: discoverable registry; no inputs; low-risk.
tools.health: readiness for samwad/ai/db; no inputs; low-risk.
Guardrails (proposed defaults)

High-risk (approval): send_template, broadcast_notice, escalate_emergency, send_media, bulk sends.
Medium-risk: log_issue, update_issue_status, assign_issue, set_contact_metadata, schedule_followup.
Low-risk: reads, translate/detect, classify/summarize, faq search, generate_qr.
Notes

Reuse existing endpoints: log_issue, send_template (alias), broadcast_notice, translate_message, list/get messages.
Add idempotency_key to write tools to prevent duplicates on retries.
Include zone/intent fields in logs to power routing and metrics.
Want me to draft the JSON-schema specs and a registry stub for the MVP set next?

