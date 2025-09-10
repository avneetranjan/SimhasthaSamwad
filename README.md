1. Overview
Simhastha Samwad is an AI‑assisted, WhatsApp‑first civic helpdesk built for large public events like Simhastha Kumbh. It ingests citizen messages, classifies intent, and replies contextually (multi‑lingual), including optional location‑aware guidance. Admins monitor conversations, broadcast notices, manage templates and zone ETAs, and approve high‑risk tool actions. The system integrates with the Samwad WPBOX API for messaging and drives responsive, data‑backed operations with real‑time dashboards and metrics.

2. Problem Solution
Problem Statement:
During mass‑gathering events, helpdesks face overwhelming, multi‑lingual inbound queries (sanitation, emergencies, directions, lost & found). Manual triage is slow, responses are inconsistent, and escalation/assignment lacks traceability. Broadcasting timely updates at zone/segment level and measuring impact is equally challenging.

Solution:
An agentic WhatsApp helpdesk that normalizes webhooks, detects language and intent, and generates concise, brand‑safe replies. It requests or sends location pins when useful, auto‑logs feedback tickets, supports assignments, and offers a secure approvals queue for high‑risk tool actions. Admins get a React dashboard for conversations, broadcasts, zone configuration, templates, metrics, and audit trails. Messaging is delivered via Samwad WPBOX, with optional AI‑powered summarization, translation, and classification.

3. Logic Workflow
Data Collection:
- WhatsApp webhook payloads (phone, text/media, timestamp); optional location
- Contact metadata (name, zone, language preference)
- Admin inputs (reply templates, broadcast notices, zone ETAs)
- AI model outputs (classification, summaries, translations)
- Operational metrics (message counts, statuses, CTA events)

Processing:
- Normalize inbound payloads; persist messages and contacts
- Detect language; classify intent (sanitation, emergency, info, guidance, directions, lost_found)
- Heuristics for guidance/lost & found; resolve zone from contact/history
- Request live location when needed; compute ETAs from zone config
- Generate or template‑select reply; route high‑risk tools through approvals
- Escalate emergencies and log assignments; push updates via WebSocket to UI

Output:
- WhatsApp text/media messages and location requests via Samwad WPBOX
- Feedback tickets, assignments, approvals, and broadcast notices stored in DB
- Real‑time UI updates, metrics endpoints, and reusable reply templates (JSON)

User Side:
- Citizens message the WhatsApp number, receive helpful, concise replies
- Share live location when prompted; receive timely notices per zone
- Multi‑lingual support (detect + translate) for accessibility

Admin Side:
- React dashboard for Conversations, Broadcasts, Templates, ZoneConfig, Issues, Metrics
- Create/update templates; configure per‑zone ETAs; manage assignments and escalations
- Review and decide high‑risk agent tool approvals; view audit and performance metrics

4. Tech Stack
- Frontend: React 18 (Vite), Tailwind CSS, Axios, i18next, WebSocket client
- Backend: FastAPI (Starlette), ORJSON responses, SQLModel ORM
- Database: SQLite (dev); compatible with Postgres for scale
- Messaging Integration: Samwad WPBOX API (send text/media, request/send location)
- AI: OpenAI/Ollama‑compatible Chat Completions (httpx client)
- Realtime: WebSocket endpoint for live updates
- Config/Env: python‑dotenv; CORS configured for local and hosted frontends
- Ops: systemd unit and OpenLiteSpeed rewrite for deployment (see deploy/)

5. Future Scope
- Scale to Postgres + Redis; role‑based access control and SSO
- Rich geospatial features (nearby facilities, routing), and map UI
- Deeper multi‑lingual NLU and on‑device/offline fallbacks for resilience
- Knowledge‑base/RAG for FAQs, policies, and event SOPs; smarter suggested replies
- Mobile app for field teams (tasking, offline sync, incident photo capture)
- Structured analytics dashboards (funnel, SLAs, zone heatmaps) and A/B content tests
- One-click cloud deploy workflows and multi-tenant event support

6. Run Locally
- Prerequisites: Python 3.10+ (recommended 3.11), Node.js 18+, npm, Git, SQLite
- Backend setup:
  - `cd backend`
  - Create venv and install deps: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
    - On Windows: `python -m venv .venv && .venv\\Scripts\\activate && pip install -r requirements.txt`
  - Copy env: `cp .env.example .env` (then edit values as below)
  - Run API: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Frontend setup:
  - `cd frontend`
  - Install deps: `npm install`
  - Run dev server: `npm run dev` (serves at `http://localhost:5173`)
- Test:
  - Backend health: `http://localhost:8000/healthz`
  - WebSocket: `ws://localhost:8000/ws`
  - Ensure `FRONTEND_ORIGIN` in `backend/.env` includes `http://localhost:5173` for CORS.

7. Configuration & Environment
- Location: `backend/.env` (start from `backend/.env.example`)
- Core server:
  - `APP_NAME`, `HOST`, `PORT`, `SQLITE_PATH`, `FRONTEND_ORIGIN`
- Samwad (WPBOX) messaging:
  - `SAMWAD_SEND_URL=https://www.app.samwad.tech/api/wpbox/sendmessage`
  - `SAMWAD_TOKEN=<your_wpbox_token>` (required)
  - `SAMWAD_LOCATION_URL=https://www.app.samwad.tech/api/wpbox/sendlocation`
  - `SAMWAD_LOCATION_REQUEST_URL=https://www.app.samwad.tech/api/wpbox/sendlocationrequest`
  - Incoming webhook (configure in Samwad/bridge): `POST https://<your-backend>/whatsapp/webhook`
    - Verification (Meta-style): `GET /whatsapp/webhook?hub.mode=subscribe&hub.challenge=...`
- AI (OpenAI/Ollama-compatible chat completions):
  - `AI_BASE_URL` must point to a base that ends with `/v1` (the app appends `/chat/completions`).
  - `AI_MODEL` (e.g., `gpt-4o-mini`, `gemma3:12b`, or your provider’s model ID)
  - `AI_API_KEY` (provider token), `AI_TEMPERATURE`, `AI_MAX_TOKENS`, `AI_KEEP_ALIVE`, `AI_AUTOREPLY`
- Assignments, ETAs, approvals:
  - `ESCALATION_NUMBERS` (comma-separated phone numbers for emergencies)
  - `ASSIGNEE_SANITATION`, `ASSIGNEE_EMERGENCY`, `ASSIGNEE_INFO`
  - `SANITATION_ETA_MINUTES`, `MEDICAL_ETA_MINUTES`
  - `AGENT_AUTO_APPROVE_HIGHRISK` (careful in production)

Yara AI Connection (example)
- If your Yara AI system exposes an OpenAI-compatible Chat Completions API:
  - Set in `backend/.env`:
    - `AI_BASE_URL=https://yara.example.com/v1`  (replace with your Yara endpoint)
    - `AI_API_KEY=<your_yara_api_key>`
    - `AI_MODEL=<yara_model_name>`  (e.g., `yara-chat-small`, per Yara docs)
  - Optional: `AI_TEMPERATURE=0.4`, `AI_MAX_TOKENS=500`
  - Validate: start the backend, then use features like translations, intent classification, or enable `AI_AUTOREPLY=true` for auto replies on new messages.

Samwad Keys & Webhook Setup
- Obtain your WPBOX token from Samwad and set `SAMWAD_TOKEN`.
- Verify send: from backend (after configuring `.env`), send a test:
  - `curl -X POST http://localhost:8000/api/reply -H "Content-Type: application/json" -d '{"phone_number":"<recipient>","body":"Test from Simhastha"}'`
- Configure incoming messages to your backend URL:
  - Webhook endpoint: `POST https://<your-backend-domain>/whatsapp/webhook`
  - For local testing, tunnel with `ngrok http 8000` and use the public URL in your Samwad/bridge settings.
