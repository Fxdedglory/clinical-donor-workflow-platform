# Production Deployment

Target domain: `https://teemails.com`

This project is prepared for a containerized production deployment with four required services:

- `reverse-proxy`: Nginx TLS termination, redirects, security headers, compression, and rate limiting
- `frontend`: Streamlit operational console
- `backend`: FastAPI API and workflow services
- `db`: PostgreSQL 16

An optional `certbot` service renews certificates and the `backup` service creates scheduled database backups.

## Required DNS

Point these records to the production host:

- `A teemails.com -> <server-ip>`
- `A www.teemails.com -> <server-ip>`

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
```

## First Deploy

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
curl -I https://teemails.com/health
curl -I https://teemails.com
```

SysAdmins can also open `System Health` inside the app to review database health, auth status, email provider status, backup posture, uptime, and active sessions.

## Deployment Notes

- Public production deployment still requires host access, DNS control, and real production secrets.
- Nginx enforces HTTPS, HSTS, CSP, clickjacking protection, content sniffing protection, and auth/API rate limits.
- The application uses platform-native accounts by default. No external identity-provider dependency is required.
- Future external identity integrations should attach to `dim_auth_identity` without replacing the native account model.
