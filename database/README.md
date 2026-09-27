# Database

This folder holds the production schemas and the MongoDB sample documents:

- [`loan_platform.sql`](loan_platform.sql) — MySQL 8, create-ready.
- [`loan_platform_postgres.sql`](loan_platform_postgres.sql) — PostgreSQL 14+,
  create-ready. **The deployment target**: cloud-hosted on Supabase so no
  database container is needed in docker-compose or production.

## `loan_platform.sql` — merged, create-ready MySQL 8 schema

This is the single source of truth for the production database. It reconciles
the original hand-built dump with the SQLAlchemy models in `backend/app/models/`
(the authoritative interface documented in [`docs/schema-contract.md`](../docs/schema-contract.md)).

Where the dump and the models disagreed, the models won. The changes:

| Area | Dump | Merged schema |
|---|---|---|
| Primary/foreign keys | `INT` | `BIGINT AUTO_INCREMENT` |
| `users.role` | `VARCHAR(30)` | `VARCHAR(40)` |
| application status / risk / decision / repayment columns | `VARCHAR(50)` | `VARCHAR(40)` |
| `loan_applications` | no `updated_at` / `submitted_at` | both added (`updated_at` auto-updating) |
| `credit_assessments` | no `assessed_by_id` | nullable FK → `users.id` added |
| `customers` | no `created_at` | added |
| `financial_details.employment_years` | `DECIMAL(5,2)` | `INT` |
| `credit_assessments.reasons_json` | native `JSON` | `TEXT` (portable, JSON string) |
| `loan_decisions.remarks` | `VARCHAR(500)` | `TEXT` |
| `loan_products.name` | not unique | `UNIQUE` |
| foreign keys | no delete behaviour | `ON DELETE CASCADE` on application children and `users → customers` |
| seed passwords | `DEMO_HASH_*` placeholders (unusable) | real bcrypt hash for `Password@123` |
| seed emails | `rahul@example.com`, … | backend's `.test` addresses |
| application numbers | `APP001` | `LN-<year>-<4 digits>` |

### Create

```bash
mysql -u <user> -p < database/loan_platform.sql
```

This creates the `loan_platform` database, its 8 tables and the demo seed data.
It is safe to re-run: the script drops and recreates the tables.

### Create in Docker (no local MySQL needed)

If you only have Docker, run MySQL 8 in a container and import into it. Verified
against `mysql:8.0` (`8.0.46`).

```bash
docker run --name cba-mysql \
  -e MYSQL_ROOT_PASSWORD=rootpass \
  -e MYSQL_DATABASE=loan_platform \
  -p 3306:3306 -d mysql:8.0

# wait until a real login works, then import
until docker exec cba-mysql mysql -uroot -prootpass -N -e "SELECT 1" >/dev/null 2>&1; do sleep 3; done
docker exec -i cba-mysql mysql -uroot -prootpass < database/loan_platform.sql
```

Then use `DATABASE_URL=mysql+pymysql://root:rootpass@127.0.0.1:3306/loan_platform`
(see below). To start over with a pristine seeded database, re-run the import —
it drops and recreates the tables. To remove the container entirely:
`docker rm -f cba-mysql`.

### Point the backend at it

In `backend/.env`:

```env
DATABASE_URL=mysql+pymysql://<user>:<password>@127.0.0.1:3306/loan_platform
```

Then, in `backend/`:

```bash
flask seed-db     # idempotent - sees the seeded rows and adds nothing
pytest            # 150 checks
```

No application code changes are needed; `PyMySQL` is already in
`backend/requirements.txt`.

Confirm the app is really on MySQL — `/api/health` reports the dialect:

```bash
python run.py
curl http://127.0.0.1:5000/api/health
# {"database_dialect":"mysql","environment":"development",...,"status":"ok"}
```

For PostgreSQL, see `loan_platform_postgres.sql` below — it is now the
deployment target, and `psycopg2-binary` ships in `backend/requirements.txt`.

### Keeping it in sync

`backend/tests/test_schema_sql.py` compiles every model column to MySQL **and**
PostgreSQL DDL and compares them to both files. If a model changes and a SQL
file is not updated, the suite fails — so edit all three together.

## `loan_platform_postgres.sql` — PostgreSQL 14+ (Supabase edition)

The same schema compiled from the same models with the PostgreSQL dialect: same
tables, columns, vocabulary, cascade rules and seed data. Dialect differences
handled inside the file:

- `BIGSERIAL` keys (BIGINT + sequence) instead of `AUTO_INCREMENT`.
- `TIMESTAMP` instead of `DATETIME`; booleans are real `BOOLEAN` and the seed
  inserts use `TRUE` (Postgres rejects the `1`/`0` MySQL accepts).
- `loan_applications.updated_at` is maintained by a `BEFORE UPDATE` trigger
  (`set_updated_at()`), mirroring MySQL's `ON UPDATE CURRENT_TIMESTAMP`.
- After the seed inserts, every sequence is resynchronised with
  `setval(..., max+1, false)`. Postgres does **not** advance sequences past
  explicit-id inserts (MySQL's AUTO_INCREMENT does), so without this the first
  API-created row would collide with a seeded id. The `false` form matters for
  empty tables: it makes the first generated id `1`, not `2`.

### Create on Supabase

1. Create a project at [supabase.com/dashboard](https://supabase.com/dashboard).
2. Open **SQL Editor**, paste the file contents, run. (Or
   `psql "$DATABASE_URL" -f database/loan_platform_postgres.sql` from a shell.)
3. Copy the connection string from **Project Settings → Database**:

```env
# Session pooler (recommended; IPv4-safe, survives serverless):
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
# Direct connection (long-lived backends; may need IPv6):
DATABASE_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

A bare `postgres://` URL is also accepted and rewritten by `app/config.py`.

### Create locally (Docker)

Verified against `postgres:16`:

```bash
docker run --name cba-postgres -e POSTGRES_PASSWORD=pgpass \
  -e POSTGRES_DB=loan_platform -p 5437:5432 -d postgres:16
docker exec -i cba-postgres psql -U postgres -d loan_platform -v ON_ERROR_STOP=1 \
  < database/loan_platform_postgres.sql
```

Then `DATABASE_URL=postgresql://postgres:pgpass@127.0.0.1:5437/loan_platform`.
Re-run the import for a pristine seeded database; `docker rm -f cba-postgres`
removes the container.

### Verify

Same as MySQL: `flask seed-db` says "Nothing to do", and `/api/health` reports
`{"database_dialect":"postgresql",...}`.

## MongoDB sample documents

`documents.json` and `audit_logs.json` are samples of the two collections the
backend writes (via `backend/app/utils/store.py`). They use the controlled
vocabularies from `backend/app/models/enums.py`.

- `documents`: one doc per application, `files[].type` one of `SALARY_SLIP`,
  `BANK_STATEMENT`, `ID_PROOF`, `ADDRESS_PROOF`, `ITR`, `OTHER`; `status` one of
  `PENDING`, `VERIFIED`, `REJECTED`.
- `audit_logs`: append-only; `metadata` for a submit is
  `{"status_from": "DRAFT", "status_to": "SUBMITTED"}`.

MongoDB is optional at runtime — without a server the backend falls back to an
in-process store.
