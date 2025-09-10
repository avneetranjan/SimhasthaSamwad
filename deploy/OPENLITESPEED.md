OpenLiteSpeed deployment guide for SimhasthaProject

Overview

- Goal: Serve the React frontend as static files and reverse‑proxy API and WebSocket traffic to a FastAPI backend (uvicorn) on localhost:8000.
- Domain: Replace all occurrences of <DOMAIN> with your actual domain.
- System user: simhastha, home: /var/www/SimhasthaProject

Prerequisites

- DNS: A record for <DOMAIN> -> your server IP
- OpenLiteSpeed installed and WebAdmin accessible (usually https://<serverIP>:7080)
- Ubuntu/Debian or similar with sudo

Directory layout

- /var/www/SimhasthaProject/
  - backend/            (FastAPI app + venv)
  - frontend/           (React project; built to ./dist)
  - data/               (SQLite DB, uploads)
  - logs/               (app logs)

Server setup (SSH)

1) Create directories and permissions

  sudo mkdir -p /var/www/SimhasthaProject/{backend,frontend,data,logs}
  sudo chown -R simhastha:simhastha /var/www/SimhasthaProject

2) Backend: Python environment and dependencies

  # Copy your backend folder contents to /var/www/SimhasthaProject/backend
  # Then as the simhastha user:
  sudo -u simhastha bash -lc '
    cd /var/www/SimhasthaProject/backend && \
    python3 -m venv .venv && \
    source .venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt
  '

3) Backend: Environment file

  # Create /var/www/SimhasthaProject/backend/.env
  # See backend/.env.example in this repo; minimally:
  APP_NAME="Simhastha Samwad"
  ENV=production
  DEBUG=false
  HOST=127.0.0.1
  PORT=8000
  SQLITE_PATH=/var/www/SimhasthaProject/data/simhastha.db
  FRONTEND_ORIGIN=https://<DOMAIN>
  SAMWAD_BASE_URL=https://api.samwad.example.com
  SAMWAD_API_KEY=changeme

4) Backend: systemd service

  # Create /etc/systemd/system/simhastha.service with content from deploy/systemd/simhastha.service
  sudo cp /var/www/SimhasthaProject/deploy/systemd/simhastha.service /etc/systemd/system/simhastha.service
  sudo systemctl daemon-reload
  sudo systemctl enable --now simhastha
  sudo systemctl status simhastha

5) Frontend: Build for production

  # Copy your frontend folder to /var/www/SimhasthaProject/frontend
  # Install Node (v18+ recommended) then build as the simhastha user:
  sudo -u simhastha bash -lc '
    cd /var/www/SimhasthaProject/frontend && \
    npm ci && \
    VITE_API_BASE=https://<DOMAIN> VITE_WS_URL=wss://<DOMAIN> npm run build
  '

  # Output will be in /var/www/SimhasthaProject/frontend/dist

OpenLiteSpeed configuration

You can configure via WebAdmin GUI or by editing config files. Below are GUI steps (safest), followed by optional file snippets.

Via WebAdmin GUI (recommended)

1) Create a Virtual Host

- Virtual Hosts -> Add:
  - Virtual Host Name: simhastha
  - Virtual Host Root: /var/www/SimhasthaProject/frontend/dist/
  - Config File: leave blank to auto-create, or set to /usr/local/lsws/conf/vhosts/simhastha/vhconf.conf
- Click Save, then click the virtual host to edit details.

2) Add Static Context for root

- Context -> Add -> Static
  - URI: /
  - Location: /var/www/SimhasthaProject/frontend/dist/
  - Accessible: Yes
  - Index Files: index.html

3) Add Proxy Context for API

- Context -> Add -> Proxy
  - URI: /api/
  - Address: 127.0.0.1:8000
  - Enable Rewrite: Yes (optional)
  - Keep-Alive: Yes

4) Add WebSocket Proxy for /ws

- Context -> Add -> Web Socket
  - URI: /ws
  - Address: 127.0.0.1:8000

5) SPA rewrite to index.html

- Under the vhost: Rewrite -> Enable Rewrite: Yes
- Rewrite Rules (or use an external rewrite file):

  RewriteEngine On
  RewriteCond %{REQUEST_URI} !^/api/
  RewriteCond %{REQUEST_URI} !^/ws
  RewriteCond %{REQUEST_FILENAME} !-f
  RewriteCond %{REQUEST_FILENAME} !-d
  RewriteRule ^ /index.html [L]

6) Listener and domain mapping

- Listeners -> Add HTTPS (if not existing):
  - Port: 443
  - Secure: Yes
  - SSL Certificate: add later after issuance
  - Add Virtual Host Mapping: map simhastha -> Domains: <DOMAIN>

- Optionally, add an HTTP listener on port 80 and set a redirect to HTTPS (Listener -> Rewrite -> force redirect).

TLS certificate (Let's Encrypt via built-in acme.sh)

Option A: Use WebAdmin SSL -> Let's Encrypt (if available in your build)

Option B: Shell via acme.sh (webroot method)

  sudo /usr/local/lsws/admin/misc/acme.sh --issue -d <DOMAIN> -w /var/www/SimhasthaProject/frontend/dist --keylength ec-256 --server letsencrypt

  # Install the cert to the listener paths (adjust if different):
  sudo /usr/local/lsws/admin/misc/acme.sh --install-cert -d <DOMAIN> \
    --ecc \
    --key-file       /usr/local/lsws/conf/<DOMAIN>.key \
    --fullchain-file /usr/local/lsws/conf/<DOMAIN>.fullchain.cer \
    --reloadcmd     "/usr/local/lsws/bin/lswsctrl restart"

Then set the HTTPS listener's SSL Cert/Key paths accordingly and restart OpenLiteSpeed.

Checks

- Backend service: curl -s http://127.0.0.1:8000/healthz -> {"status":"ok"}
- Frontend over HTTPS: https://<DOMAIN>
- API via proxy: https://<DOMAIN>/api/messages
- WebSockets: browser console should show a successful connection to wss://<DOMAIN>/ws

Troubleshooting

- CORS: ensure backend FRONTEND_ORIGIN=https://<DOMAIN>
- 404 for client routes: ensure SPA rewrite rules are enabled
- WebSocket fails: ensure Web Socket context exists for /ws and backend is listening on 127.0.0.1:8000
- Permissions: ensure /var/www/SimhasthaProject is world-readable where needed; SQLite file in /var/www/SimhasthaProject/data should be writable by the service user

