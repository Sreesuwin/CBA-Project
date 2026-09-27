# Loan Application & Credit Assessment Platform

A role-based web platform where customers apply for loans online, loan officers
review applications, and a **transparent rule-based** engine produces a credit
score, risk level and recommendation. The lending decision always stays with the
loan officer.

Full-stack apprenticeship project. Stack: React (frontend), Python + Flask REST
API (backend), SQL for transactional data, MongoDB for document/audit data.

> The scoring engine is an educational business-rule simulation, not a real
> credit score, and its recommendation is not suitable for actual lending.

---

## Current status

| Milestone | State |
|---|---|
| Backend + database foundation | **done** |
| Auth, JWT and role authorization | **done** |
| Loan products API | **done** |
| Application create/draft/submit | **done** |
| Credit assessment service | **done** |
| Officer review & decision workflow | **done** |
| Documents + audit trail | **done** |
| React frontend | **done** |

Working today: the full customer-to-officer workflow end to end. A customer can
browse products, save an application as a draft, attach document metadata and
submit it (with full server-side validation against the product's rules).
Submitting runs the rule-based credit engine and stores a score, risk level and
recommendation. A loan officer sees the queue, reads the assessment and its
reasons, and approves, rejects or requests more information; approving seeds the
repayment schedule. Every step is written to an audit trail. The React SPA calls
this API for real - it holds no mock data.

The backend runs against a **dummy SQLite database** by default. Two create-ready
schemas live in [`database/`](database): `loan_platform.sql` (MySQL 8) and
`loan_platform_postgres.sql` (PostgreSQL 14+). **Deployment target is Supabase
(cloud Postgres)** — no database container needed in docker-compose or
production; switch with `DATABASE_URL` only. Both schemas are compiled from the
same models, seed demo data with working bcrypt hashes, and are kept in sync
with the models by the test suite.
See [`docs/schema-contract.md`](docs/schema-contract.md) for the interface and
[`database/README.md`](database/README.md) for the create/switch instructions.

---

## Prerequisites

- Python 3.11+
- A Supabase project (cloud Postgres — the deployment target), or MySQL 8+ /
  PostgreSQL 14+ locally; create-ready schemas are in `database/`. MongoDB —
  none of these are needed to run the current backend (SQLite default)
- Node.js LTS (frontend milestone only)

## Setup

```bash
cd backend
python -m venv venv
source venv/Scripts/activate      # Windows (Git Bash)
# source venv/bin/activate        # macOS / Linux

pip install -r requirements.txt
cp .env.example .env              # then fill in the secrets
```

`DATABASE_URL` defaults to SQLite, so no database server is required yet.

## Running

```bash
cd backend
export FLASK_APP=run.py

flask seed-db --reset     # create tables and insert demo data
flask run                 # or: python run.py
```

The SQLite file is created at `backend/instance/loan_platform.db`.

```bash
curl http://127.0.0.1:5000/api/health
curl http://127.0.0.1:5000/api/health/ready
```

### CLI commands

| Command | Purpose |
|---|---|
| `flask create-db` | Create all tables |
| `flask drop-db --yes` | Drop all tables (destructive) |
| `flask seed-db` | Insert demo data; safe to run repeatedly |
| `flask seed-db --reset` | Drop, recreate and seed |

## Demo accounts

Seeded by `flask seed-db`. All share the password `Password@123`.

| Role | Email |
|---|---|
| ADMIN | `admin@loanplatform.test` |
| LOAN_OFFICER | `officer@loanplatform.test` |
| CUSTOMER | `rahul.kumar@example.test` |
| CUSTOMER | `ananya.rao@example.test` |
| CUSTOMER | `arjun.singh@example.test` |

All seeded data is fictional.

## API

| Method | Endpoint | Access |
|---|---|---|
| GET | `/api/health` | public |
| GET | `/api/health/ready` | public |
| POST | `/api/auth/register` | public |
| POST | `/api/auth/login` | public |
| POST | `/api/auth/change-password` | signed in |
| GET | `/api/users/me` | signed in |
| PUT | `/api/users/me` | signed in |
| GET | `/api/users` | ADMIN |
| GET | `/api/loan-products` | public (active only; `?all=1` for staff) |
| GET | `/api/loan-products/<id>` | public |
| POST | `/api/loan-products` | ADMIN |
| PUT | `/api/loan-products/<id>` | ADMIN |
| GET | `/api/applications` | signed in (customer: own; staff: all) |
| POST | `/api/applications` | CUSTOMER |
| GET | `/api/applications/<id>` | owner or staff |
| PUT | `/api/applications/<id>` | owner, while DRAFT |
| POST | `/api/applications/<id>/submit` | owner |
| POST | `/api/applications/<id>/assess` | owner or staff |
| POST | `/api/applications/<id>/approve` | LOAN_OFFICER / ADMIN |
| POST | `/api/applications/<id>/reject` | LOAN_OFFICER / ADMIN |
| POST | `/api/applications/<id>/request-info` | LOAN_OFFICER / ADMIN |
| GET | `/api/applications/<id>/documents` | owner or staff |
| POST | `/api/applications/<id>/documents` | owner or staff |
| GET | `/api/applications/<id>/audit` | owner or staff |
| GET | `/api/audit` | ADMIN |

### Authentication

Tokens are JWTs signed with `JWT_SECRET_KEY`, sent as
`Authorization: Bearer <token>`. A protected request without a valid token gets
`401` and a specific code: `UNAUTHENTICATED`, `INVALID_TOKEN` or `TOKEN_EXPIRED`.
A valid token whose role is not permitted gets `403 FORBIDDEN`.

| Endpoint | Access | Notes |
|---|---|---|
| `POST /api/auth/register` | public | always creates a CUSTOMER, returns a token |
| `POST /api/auth/login` | public | returns a token |
| `POST /api/auth/change-password` | any signed-in user | requires the current password |
| `GET /api/users/me` | any signed-in user | own account plus borrower profile |
| `PUT /api/users/me` | any signed-in user | update own name and profile fields |
| `GET /api/users` | ADMIN | the user-management registry |
| `POST`/`PUT /api/loan-products` | ADMIN | catalogue management; ranges are validated |
| `POST /api/applications` | CUSTOMER | create a draft |
| `GET/PUT /api/applications/<id>` | owner (or staff to read) | editing is allowed only while DRAFT |
| `POST /api/applications/<id>/submit` | owner | full validation, then scores the application |
| `POST /api/applications/<id>/{approve,reject,request-info}` | LOAN_OFFICER | the three officer outcomes |

The credit engine lives in `app/services/credit_service.py` as a pure function:
financials in, `{score, risk, recommendation, reasons}` out, with no database or
request involved. Its rules follow §13/§14 of the blueprint and are asserted
exactly in `tests/test_credit_service.py`.

Password rule for new passwords: 8-72 characters with at least one letter and
one digit. A login attempt is only checked for correctness, never complexity.

Two deliberate choices worth knowing:

- **There is no `/logout`.** A JWT stays valid until it expires, and without a
token blocklist a logout endpoint would be a lie. The frontend drops the token.
It becomes a real endpoint once revocation exists.
- **`role` is not a token claim.** It is read from the database on every
request, so changing or deactivating an account takes effect immediately
instead of when the token expires. There is a test for exactly this.

Login failures are deliberately indistinguishable: an unknown email, a wrong
password and a disabled account all return the same 401 body, and an unknown
email still performs a bcrypt check so the response times match.

Errors use one shape everywhere:

```json
{"error": {"status": 404, "code": "NOT_FOUND", "message": "...", "details": {}}}
```

`/api/health/ready` reports both datastores. MongoDB being unreachable is
reported but does not make the service unhealthy — it only holds audit and
document data.

## Tests

```bash
cd backend
pytest
```

150 tests run against an in-memory SQLite database, so they never touch the
development data. They cover foreign-key enforcement, unique constraints, enum
round-tripping, decimal money handling, cascades, the seed script's idempotency,
the error envelope, the whole auth surface, the credit engine's worked examples,
product CRUD and validation, application ownership and submission rules, the
officer state machine, document/audit storage, and schema-vs-model parity for
**both** the MySQL and PostgreSQL schema files. Run this after any change to
models, services or auth.

bcrypt is set to 4 rounds in tests (`BCRYPT_ROUNDS`) so the suite finishes in
under a second. Each stored hash records its own cost, so production hashes are
unaffected.

## Layout

```
backend/
  app/
    __init__.py        application factory
    config.py          env-driven config; the only place the DB URL is read
    extensions.py      SQLAlchemy + JWT singletons, SQLite FK enforcement
    cli.py             flask create-db / drop-db / seed-db
    models/            SQLAlchemy models, one file per table
    routes/            blueprints: health, auth, users, loan_products,
                       applications, audit
    services/          business logic (DB access lives here, not in routes)
    schemas/           marshmallow request/response schemas
    middleware/        @roles_required and current-user resolution
    utils/             errors, ids, mongo, store, security, seed, time
  tests/
  run.py
frontend/
  src/
    assets/           logo, hero illustration, product icons (SVG)
    context/          AuthContext - the API-backed data layer
    services/         api.js (axios client), mappers.js (snake_case <-> camelCase)
    pages/            customer / officer / admin screens
    components/       shared UI (table, cards, badges, stepper, modals)
docs/
  schema-contract.md   what the database must provide
  progress-log.md      day-by-day engineering log
```

## Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The SPA calls the backend at `VITE_API_URL` (default
`http://localhost:5000/api`). Start the backend first, or the login screen will
report that the API is unreachable - by design, there is no mock fallback.

```bash
cp .env.example .env   # optional; only needed to point at another API host
```

The "quick demo" buttons on the login screen sign in as the three seeded
accounts, so a reviewer can switch roles without typing passwords.

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | dev value | Flask session secret |
| `JWT_SECRET_KEY` | dev value | signs access tokens |
| `JWT_ACCESS_TOKEN_MINUTES` | `60` | token lifetime |
| `BCRYPT_ROUNDS` | `12` | bcrypt cost factor; tests use 4 |
| `DATABASE_URL` | `sqlite:///loan_platform.db` | SQLite dev default; Supabase pooler URL for deployment (see `database/README.md`) |
| `MONGO_URI` | `mongodb://localhost:27017/` | empty string disables MongoDB |
| `MONGO_DB` | `loan_platform` | |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | allowed CORS origin |

Never commit `.env`. It is already in `.gitignore`.

## Known limitations

- **No real file upload.** Document *metadata* is stored; the bytes are not.
- **No `/logout`.** A JWT is valid until it expires; the client drops the token.
- **MongoDB is optional.** Without it, documents and audit entries fall back to an
  in-process store, so they are lost on restart. Everything else is unaffected.
- **The demo runs on SQLite by default.** Import `database/loan_platform_postgres.sql`
  into Supabase (or `database/loan_platform.sql` into MySQL) and point
  `DATABASE_URL` at it to switch. No code changes are needed.
- **The credit engine cannot reach its own LOW band.** The blueprint's additive
  rules peak at 590, below the 700 needed for LOW/ELIGIBLE. It is implemented
  faithfully and the flaw is documented in `docs/progress-log.md` rather than
  silently patched.

## Next steps

1. Create the Supabase project, run `database/loan_platform_postgres.sql` in its
   SQL Editor, and re-point `DATABASE_URL` at the pooler connection string.
2. Add file upload (object storage) behind the existing document metadata.
3. Add token revocation so `/logout` can be honest.
4. Deploy the API and SPA so the demo has a public URL.

The full requirements and milestone plan live in the project blueprint document
(`CBA Micro Project.docx`). The database interface is specified in
[`docs/schema-contract.md`](docs/schema-contract.md).
