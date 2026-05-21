# Production Deployment

Target domain: `https://teemails.com`

This project is prepared for a containerized production deployment with four core services:

- `reverse-proxy`: Nginx TLS termination, redirects, security headers, compression, and rate limiting
- `frontend`: Streamlit operational console
- `backend`: FastAPI API and workflow services
- `db`: PostgreSQL 16

An optional `certbot` service renews certificates, the `backup` service creates scheduled database backups, and the optional `cloudflared` service publishes the app through Cloudflare Tunnel.

## Recommended Cloudflare Deployment

For `teemails.com`, Cloudflare Tunnel is the cleanest path because it publishes the Docker app without exposing origin ports directly.

This app is a Streamlit + FastAPI + PostgreSQL container stack, so it should not be deployed as a Cloudflare Pages static site.

### Cloudflare Dashboard Steps

1. In Cloudflare, create a Tunnel for this production app.
2. Add a published application route:
   - Public hostname: `teemails.com`
   - Service URL: `http://frontend:8501`
3. Add a second published application route:
   - Public hostname: `www.teemails.com`
   - Service URL: `http://frontend:8501`
4. If Cloudflare reports that a DNS record already exists for either hostname, remove or replace the old root or `www` record.
5. Copy the Tunnel token and add it to the production `.env` as `CLOUDFLARE_TUNNEL_TOKEN`.

When `cloudflared` runs inside this Compose project, use `http://frontend:8501`, not `http://localhost:8501`. Inside the Tunnel container, `localhost` means the Tunnel container itself.

### Cloudflare Tunnel Deploy

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d db backend frontend backup
docker compose -f docker-compose.prod.yml --profile cloudflare up -d cloudflared
```

Check the Tunnel status in Cloudflare. It should show as healthy, and `https://teemails.com` should load the Clinical Donor Workflow Platform.

## Alternative Direct DNS Deployment

If you prefer a traditional public host with Nginx and Let's Encrypt, point these records to the production host:

- `A teemails.com -> <server-ip>`
- `A www.teemails.com -> <server-ip>`

Set both records to proxied in Cloudflare for HTTP/HTTPS protection and analytics.

## Required Environment

Create a production `.env` on the host. Do not reuse local development credentials.

```bash
APP_ENV=prod
APP_BASE_URL=https://teemails.com
API_URL=http://backend:8000
POSTGRES_DB=clinical_donor_workflow
POSTGRES_USER=<prod-user>
POSTGRES_PASSWORD=<prod-password>
DATABASE_URL=postgresql+psycopg://<prod-user>:<prod-password>@db:5432/clinical_donor_workflow
SECRET_KEY=<long-random-secret>
ENCRYPTION_KEY=<fernet-or-aes-key-material>
BACKUP_ENCRYPTION_KEY=<long-random-backup-key>
COOKIE_SECURE=true
COOKIE_SAMESITE=strict
EMAIL_PROVIDER=console
EMAIL_FROM=no-reply@teemails.com
CLOUDFLARE_TUNNEL_TOKEN=<cloudflare-tunnel-token-if-using-tunnel>
```

## First Direct-Nginx Deploy

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d db backend frontend
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d teemails.com -d www.teemails.com \
  --email admin@teemails.com --agree-tos --no-eff-email
docker compose -f docker-compose.prod.yml up -d
```

## Operational Checks

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 backend
docker compose -f docker-compose.prod.yml --profile cloudflare logs --tail=100 cloudflared
curl -I https://teemails.com/health
curl -I https://teemails.com
```

SysAdmins can also open `System Health` inside the app to review database health, auth status, email provider status, backup posture, uptime, and active sessions.

## Deployment Notes

- Public production deployment still requires host access, DNS control, and real production secrets.
- Nginx enforces HTTPS, HSTS, CSP, clickjacking protection, content sniffing protection, and auth/API rate limits.
- Cloudflare Tunnel terminates public ingress at Cloudflare and forwards traffic to the internal Streamlit container.
- The application uses platform-native accounts by default. No external identity-provider dependency is required.
- Future external identity integrations should attach to `dim_auth_identity` without replacing the native account model.
