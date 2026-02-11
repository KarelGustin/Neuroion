## Cron SQLite Storage

Cron jobs and run history are stored in the main SQLite database (the same DB used by Homebase).
This replaces the legacy JSON file storage.

### Tables

#### `cron_jobs`
- `id` (string, primary key): job UUID
- `user_id` (string, indexed): job owner (string form)
- `created_at` (datetime, indexed): job creation time (UTC)
- `job_json` (JSON): full serialized cron job (schedule, payload, etc.)

#### `cron_runs`
- `id` (integer, primary key)
- `job_id` (string, indexed, FK -> `cron_jobs.id`): owning job
- `timestamp` (datetime, indexed): run time (UTC)
- `run_json` (JSON): run record (status, error, etc.)

### Migration From Legacy JSON

On first cron access, the system will attempt a one-time migration from:
- `~/.neuroion/cron/jobs.json`
- `~/.neuroion/cron/runs/<jobId>.jsonl`

Migration behavior:
- Only runs if `cron_sqlite_migrated` flag is not set in `system_config`.
- If SQLite already has cron jobs, migration is skipped and the flag is set.
- Legacy files are not deleted.

### Migration Flag

`system_config.key = "cron_sqlite_migrated"` is set to `true` after migration or if SQLite already contains cron jobs.

### Troubleshooting

- **No cron jobs after upgrade**: verify the legacy JSON files exist and that `cron_sqlite_migrated` is not already set.
- **Duplicate jobs**: delete the `cron_sqlite_migrated` flag and clear cron tables, then restart to re-migrate.
- **Run history missing**: check that `runs/<jobId>.jsonl` exists; only runs present in legacy files are migrated.

### Developer Notes

- All cron persistence is handled in `neuroion/core/cron/storage.py`.
- Cron business logic lives in `neuroion/core/cron/service.py`.
