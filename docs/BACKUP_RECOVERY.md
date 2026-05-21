# Backup And Recovery

This document defines production backup, restore, rollback, and outage recovery foundations for `teemails.com`.

## Backup Policy

The production compose stack includes a `backup` container that runs daily:

```text
pg_dump -> gzip -> optional AES-256 encrypted backup -> /backups
```

If `BACKUP_ENCRYPTION_KEY` is set, backups are written as `.sql.gz.enc`. If it is not set, backups are written as `.sql.gz` for development-style environments only.

Default retention: 14 days.

## Manual Backup

```bash
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > clinical_donor_manual.sql.gz
```

Encrypted manual backup:

```bash
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" |
  gzip |
  openssl enc -aes-256-cbc -salt -pbkdf2 \
    -pass env:BACKUP_ENCRYPTION_KEY \
    -out clinical_donor_manual.sql.gz.enc
```

## Restore Procedure

1. Put the application in maintenance mode at the reverse proxy or host firewall.
2. Stop backend and frontend services.

```bash
docker compose -f docker-compose.prod.yml stop backend frontend
```

3. Decrypt if needed.

```bash
openssl enc -d -aes-256-cbc -pbkdf2 \
  -pass env:BACKUP_ENCRYPTION_KEY \
  -in clinical_donor_backup.sql.gz.enc |
  gunzip > clinical_donor_restore.sql
```

4. Restore into PostgreSQL.

```bash
cat clinical_donor_restore.sql |
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

5. Run migrations and restart services.

```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
docker compose -f docker-compose.prod.yml up -d backend frontend reverse-proxy
```

6. Validate `/health`, login, dashboard load, and SysAdmin System Health.

## Migration Rollback

Use Alembic only after confirming a database backup exists:

```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic current
docker compose -f docker-compose.prod.yml run --rm backend alembic downgrade -1
```

Prefer forward-fix migrations for production data issues when possible.

## Application Rollback

```bash
git checkout <known-good-commit>
docker compose -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.prod.yml up -d backend frontend
```

Validate:

- API `/health`
- login and MFA
- donor route resolution
- workflow transition action
- document signed link
- SysAdmin System Health

## Outage Recovery

For database outage:

- verify DB container health
- inspect disk space
- inspect backup volume
- restore from latest validated backup if corruption is confirmed

For auth outage:

- inspect `fact_security_audit`
- review active sessions in System Health
- rotate `SECRET_KEY` only with a planned session invalidation window

For reverse proxy or TLS outage:

- renew certificates with certbot
- validate Nginx config
- restart reverse proxy

```bash
docker compose -f docker-compose.prod.yml exec reverse-proxy nginx -t
docker compose -f docker-compose.prod.yml restart reverse-proxy
```
