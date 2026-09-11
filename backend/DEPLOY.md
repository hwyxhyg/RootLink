# RootLink Backend Deployment

The recommended production path is:

```text
Internet -> Nginx or Caddy -> 127.0.0.1:8000 -> FastAPI
```

Do not expose port 8000 directly to the public internet.

## 1. Server prerequisites

Use a current Ubuntu or Debian server with Python 3.11 or 3.12. The examples below assume the project is installed at `/opt/rootlink/backend` and runs as a dedicated `rootlink` system user.

Point the DNS `A` or `AAAA` record for `api.getrootlink.com` to the server before requesting a TLS certificate.

## 2. Virtual environment

```bash
cd /opt/rootlink/backend
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Environment

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

Required values are `VOLCENGINE_API_KEY`, `SUPABASE_URL`, and `SUPABASE_SERVICE_KEY`. Set `PGDATABASE_URL` to the Supabase PostgreSQL connection string when conversation memory must survive restarts. Keep the service role key on the backend only.

For local frontend development, add its exact origin to `FRONTEND_ORIGINS`, for example `http://localhost:5500`. Never use `*` together with authenticated browser requests.

## 4. Manual start

```bash
cd /opt/rootlink/backend
. .venv/bin/activate
uvicorn src.api.chat_sse:app --host 127.0.0.1 --port 8000
```

Verify locally:

```bash
curl http://127.0.0.1:8000/health
```

## 5. systemd

Create `/etc/systemd/system/rootlink.service`:

```ini
[Unit]
Description=RootLink FastAPI backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=rootlink
Group=rootlink
WorkingDirectory=/opt/rootlink/backend
EnvironmentFile=/opt/rootlink/backend/.env
ExecStart=/opt/rootlink/backend/.venv/bin/uvicorn src.api.chat_sse:app --host 127.0.0.1 --port 8000 --proxy-headers
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rootlink
sudo systemctl status rootlink
```

View logs and restart:

```bash
sudo journalctl -u rootlink -f
sudo systemctl restart rootlink
```

## 6. Nginx and HTTPS

Install Nginx, then create `/etc/nginx/sites-available/rootlink-api`:

```nginx
server {
    listen 80;
    server_name api.getrootlink.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/rootlink-api /etc/nginx/sites-enabled/rootlink-api
sudo nginx -t
sudo systemctl reload nginx
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.getrootlink.com
```

Caddy can replace Nginx with automatic HTTPS:

```caddyfile
api.getrootlink.com {
    reverse_proxy 127.0.0.1:8000 {
        flush_interval -1
    }
}
```

## 7. Smoke tests

```bash
curl -N https://api.getrootlink.com/api/chat/sse \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"test_en","message":"My family is from Anxi. Where should I begin?","lang":"en"}'
```

Repeat with a Chinese message and with `"lang":"abc"`; the latter should use the Chinese agent. Use different IDs or the language suffix behavior to verify that Chinese and English memory do not mix.

Archive save/load requests require a valid Supabase user access token in the `Authorization: Bearer <token>` header.
