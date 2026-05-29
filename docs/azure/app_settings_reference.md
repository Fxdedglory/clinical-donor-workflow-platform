# App Settings Reference

## Required

| Setting | Example | Notes |
|---|---|---|
| `APP_ENV` | `prod` | Use `dev` locally, `prod` in hosted app. |
| `DATABASE_URL` | `postgresql+psycopg://...` | Store only in App Service settings or local `.env`. |
| `SECRET_KEY` | generated secret | Must be unique and rotated outside Git. |
| `APP_BASE_URL` | `https://teemails.com/Clinical` | Public frontend URL. |
| `PORT` | `8000` | App Service public port injected by platform. |
| `STARTUP_MODE` | `fastapi_react` | Current no-Docker target. |
| `SERVE_FRONTEND` | `true` | FastAPI serves `frontend/dist` when built. |
| `FRONTEND_DIST_DIR` | `frontend/dist` | React/Vite build directory. |

## Security

| Setting | Notes |
|---|---|
| `ENCRYPTION_KEY` | Required for production-grade sensitive-field encryption. |
| `BACKUP_ENCRYPTION_KEY` | Required before automated hosted backup routines are enabled. |
| `COOKIE_SECURE` | Set `true` behind HTTPS. |
| `COOKIE_SAMESITE` | Prefer `lax`; review for partner portal redirects later. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Default 30. |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Default 20160. |
| `MFA_DEV_BYPASS_CODE` | Do not use a predictable value in production. |

## CORS

| Setting | Example |
|---|---|
| `CORS_ORIGINS` | `https://teemails.com,https://www.teemails.com,http://localhost:5173,http://127.0.0.1:5173` |

Comma-separated values are accepted.

## Email

| Setting | Notes |
|---|---|
| `EMAIL_PROVIDER` | `console`, `smtp`, `sendgrid`, or future provider. |
| `EMAIL_FROM` | Sender address. |
| `EMAIL_FROM_NAME` | Sender display name. |
| `SMTP_HOST` / `SMTP_PORT` | SMTP settings if used. |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | Store only in App Service settings. |
| `SENDGRID_API_KEY` | Store only in App Service settings. |
| `MAILGUN_API_KEY` / `MAILGUN_DOMAIN` | Store only in App Service settings. |

## Data Producer

| Setting | Default | Notes |
|---|---|---|
| `ENABLE_DATA_PRODUCER_API` | `true` | Disable in production if no admin producer controls are desired. |
| `DATA_PRODUCER_METADATA_ROOT` | `data/generated` | Ignored by Git. |
| `DATA_PRODUCER_EXPORT_ROOT` | `data/exports` | Ignored by Git. |
| `DATA_PRODUCER_STOP_FILE` | `data/generated/STOP_CONTINUOUS` | Stop-file for continuous mode. |
| `DATA_PRODUCER_MIN_INTERVAL_SECONDS` | `1` | Raise for hosted environments. |
| `DATA_PRODUCER_MAX_CYCLES` | `1000` | Guardrail against runaway loops. |
| `DATA_PRODUCER_ALLOW_INFINITE` | `false` | Infinite mode requires explicit opt-in. |
