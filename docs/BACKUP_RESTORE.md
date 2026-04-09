# Backup and Restore Runbook

## Scope
This runbook covers PostgreSQL data backups and restore checks for the Youth Sports site.

## Recommended Cadence
- Daily automated backup of the production database.
- Weekly restore validation in a non-production environment.
- Keep at least 14 daily backups and 8 weekly backups.

## Backup Command (PostgreSQL)
Use a timestamped dump file:

```bash
pg_dump -Fc -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" > backup_$(date +%Y%m%d_%H%M%S).dump
```

## Restore Command (PostgreSQL)
Restore to a non-production database first:

```bash
dropdb --if-exists "$RESTORE_DB_NAME"
createdb "$RESTORE_DB_NAME"
pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$RESTORE_DB_NAME" --clean --if-exists backup_file.dump
```

## Post-Restore Validation
Run Django checks after restore:

```bash
python manage.py migrate
python manage.py listing_health_check --json
python manage.py test core.tests -v 1
```

## Recurring Safety Checks
Use this command in a scheduler (cron, Task Scheduler, or platform job):

```bash
python manage.py listing_health_check --json --send-email
```

Optional hard-fail mode for CI/monitoring:

```bash
python manage.py listing_health_check --json --fail-on-alert
```

## Alert Email Configuration
Set `OPS_ALERT_EMAIL` in environment variables (comma-separated list supported):

```env
OPS_ALERT_EMAIL=ops@example.com,admin@example.com
```

## Incident Notes Template
- Date/time detected:
- Trigger source:
- Affected area:
- Immediate mitigation:
- Follow-up actions:
