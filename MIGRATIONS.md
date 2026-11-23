# Pagetrail database migrations

## Safety boundaries

- Migrations are version-controlled Alembic operations.
- FastAPI startup does not execute migrations or call schema mutation helpers.
- Legacy `init_db()`, `init_rag_db()` and `init_database.main()` remain callable
  as backward-compatible explicit local-development wrappers. They require
  `PAGETRAIL_ALLOW_LEGACY_INIT=true` and `ALEMBIC_DATABASE_URL`, refuse remote
  hosts, and invoke Alembic instead of calling `create_all()`.
- Do not stamp or upgrade production until a read-only schema comparison is
  complete and the baseline matches.
- Never commit database URLs or credentials.
- The migration role must be separate from the runtime role where possible.

## Legacy initialization behavior

`app.db.session.init_db()` is an explicit local-development compatibility
wrapper. It requires `PAGETRAIL_ALLOW_LEGACY_INIT=true` and
`ALEMBIC_DATABASE_URL`, refuses remote hosts, and invokes Alembic. It does not
fall back to `DATABASE_URL` or `DATABASE_ADMIN_URL`.
`app.services.rag.init_rag_db()` delegates to the same Alembic wrapper.
`app.scripts.init_database.main()` delegates to the same wrapper and is
deprecated.

FastAPI lifespan does not call any of these functions. Render deployments
must not run legacy initialization or migrations automatically.

## Initial revisions

- `001_existing_production` describes the read-only-inspected production-era
  schema: users, conversations, chat messages, long-term memory, RAG documents,
  LangGraph checkpoint tables, keep-alive logs, pgvector, and the RLS state on
  existing application tables.
- `002_project_operations` creates only the newly introduced project,
  organization, agent, integration, and audit tables.

The baseline has not been stamped against production. The production schema
was read-only inspected and contains no project operations tables. It also
contains no RLS policies, while RLS is enabled on several existing tables.
The migration account observed was PostgreSQL with `BYPASSRLS=true`; this does
not prove RLS protection for the application role.

RLS for the new tables is intentionally not enabled by 002 until ownership
relationships and backend roles/policies are explicitly designed and reviewed.
Application membership checks remain required. Do not assume RLS is secure
without policy inspection.

## Read-only database comparison

| Database object | Production currently | Expected after migrations | Action |
|---|---|---|---|
| `users`, `conversations`, `chat_messages`, `long_term_memory` | Present with baseline columns and indexes | Same | Document in 001; no destructive changes |
| `rag_documents` (`vector(3072)`) | Present; pgvector 0.8.2 | Same | Document in 001; verify existing dimension |
| LangGraph `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations` | Present | Same | Document baseline; library owns future checkpoint migrations |
| `keep_alive_logs` | Present | Same | Document in 001 |
| `projects`, `project_members`, `tasks`, `milestones`, `task_dependencies`, `project_documents`, `meeting_notes` | Missing | Created by 002 | Create only missing tables |
| `organizations`, `organization_members` | Missing | Created by 002 | Create before projects |
| `agent_runs`, `agent_approvals`, `agent_events`, `agent_artifacts`, `agent_schedules` | Missing | Created by 002 | Create with relationships |
| `integration_connections`, `audit_logs` | Missing | Created by 002 | Create with indexes and constraints |
| Existing RLS enabled tables | RLS enabled; no policies found | Preserve existing state | Do not invent policies |
| New-table RLS | N/A | Still no policy migration | Gap remains; application authorization required |
| Current role | `postgres`, `BYPASSRLS=true` | Migration role TBD | RLS protection of backend role is unverified |

## Development setup

Set only the migration target:

```powershell
$env:PYTHONPATH="backend"
$env:ALEMBIC_DATABASE_URL="postgresql+psycopg://<development-user>:<password>@<development-host>:5432/postgres"
```

The URL must use SSL. The Alembic environment refuses to run without
`ALEMBIC_DATABASE_URL`; it does not fall back to runtime database settings.

Install and inspect:

```powershell
python -m pip install -r backend/requirements.txt
python -m alembic -c backend/alembic.ini current
python -m alembic -c backend/alembic.ini heads
python -m alembic -c backend/alembic.ini history
```

Review SQL before applying:

```powershell
python -m alembic -c backend/alembic.ini upgrade head --sql
python -m alembic -c backend/alembic.ini upgrade head --sql > migration.sql
```

Apply to development only:

```powershell
python -m alembic -c backend/alembic.ini upgrade head
python -m pytest backend/tests -v
```

After the development migration succeeds, inspect the target:

```powershell
python -m alembic -c backend/alembic.ini current
python -m alembic -c backend/alembic.ini check
```

## Production procedure

1. Export a verified backup or Supabase point-in-time backup.
2. Run the read-only target preflight in the GitHub migration workflow or
   locally against a reviewed production connection.
3. Confirm every baseline table, column, constraint, and index matches.
4. Confirm no project-operation tables exist, or stop if migration 003 has
   already been applied.
5. Set `ALEMBIC_DATABASE_URL` to the reviewed production migration URL.
6. Confirm the printed host and database on a terminal session.
7. Run the migration only from the manual, environment-approved GitHub
   workflow. The workflow never stamps revisions and never runs on application
   startup or normal GitHub auto-deploy.

For an operator review, use:

```powershell
$env:PYTHONPATH="backend"
$env:ALEMBIC_DATABASE_URL="postgresql+psycopg://<migration-user>:<password>@<host>:5432/<database>"
python backend/scripts/verify_migration_target.py
python -m alembic -c backend/alembic.ini upgrade 003_personal_organizations
python -m alembic -c backend/alembic.ini current
python -m alembic -c backend/alembic.ini check
```

This path applies 001 as a no-op baseline against an existing production
schema, then applies 002 and 003. It never uses `stamp head`, `stamp 001`, or
`Base.metadata.create_all()` as migration replacements.

## Failed migration

Alembic records a revision only after the transaction completes. Before
retrying, inspect `alembic_version` and application logs, restore only under
the organization's incident procedure if rollback is required, and resolve the
failed SQL manually. Do not reset or drop tables. Do not edit an already
applied migration; add a new forward-only repair revision.
