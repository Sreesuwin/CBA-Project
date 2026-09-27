# Daily Progress Log

**Project:** Loan Application & Credit Assessment Platform
**Date:** 22 September 2026
**Scope of this log:** Backend (Python + Flask REST API)
**Repo:** `backend/` (own git repository, branch `main`)

---

## 1. What the project is, in one paragraph

A role-based web platform where a customer applies for a loan online, a loan
officer reviews the application, and a **transparent rule-based engine** produces
a credit score, a risk level and a recommendation. The lending decision always
stays with the officer — the engine advises, it does not approve. Three roles:
`CUSTOMER`, `LOAN_OFFICER`, `ADMIN`.

---

## 2. Status at a glance

| # | Milestone | State |
|---|---|---|
| 1 | Backend + database foundation | **Complete** |
| 2 | Database layer + schema contract for the DB teammate | **Complete** |
| 3 | Authentication, JWT and role authorization | **Complete** |
| 4 | Loan products API | **Complete** |
| 5 | Application create / draft / submit | **Complete** |
| 6 | Credit assessment service | **Complete** |
| 7 | Officer review & decision workflow | **Complete** |
| 8 | Documents + audit trail | **Complete** |
| 9 | React frontend wired to the API | **Complete** |

**By the numbers:** 8 database tables, 23 live API endpoints, 123 passing
automated tests, and a React SPA that talks to the API for real (no mock data).

> Update (27 September 2026): everything below this line describes milestone 3.
> The work completed afterwards is written up in **§9** at the end of this file.

---

## 3. Completed work

### 3.1 Backend foundation

Set up the skeleton the rest of the project is built on, before writing any
business logic:

- **Application factory** (`app/__init__.py`) — the application is created by a
  function that takes a config, so tests can build their own instance with their
  own database and secrets. Nothing is configured at import time.
- **Central configuration** (`app/config.py`) — all settings come from
  environment variables, with safe development defaults. This is the *only*
  file in the codebase that reads the database URL.
- **Shared extensions** (`extensions.py`) — SQLAlchemy and JWT initialised as
  singletons and attached to the application at startup.
- **Consistent error handling** — every error in the API, including framework
  errors like 404 and 405, returns the same JSON shape:

  ```json
  { "error": { "status": 404, "code": "NOT_FOUND", "message": "...", "details": {} } }
  ```

  A frontend can therefore handle every failure the same way, and success
  responses carry `data`. No endpoint can accidentally return an HTML error page.
- **Health endpoints** — `/api/health` (liveness) and `/api/health/ready`
  (readiness, reports both datastores).
- **CLI commands** — `flask create-db`, `flask drop-db`, `flask seed-db`
  (and `--reset`), so setting up a fresh machine is one command.

### 3.2 Database layer, on a dummy database

The real schema is owned by a teammate, so the goal here was to make the
database **swappable in one line** rather than to commit to a database we do not
control.

- **All 8 tables modelled** — `users`, `customers`, `loan_products`,
  `loan_applications`, `application_documents`, `credit_assessments`,
  `loan_decisions`, `repayments` — with primary keys, foreign keys, unique
  constraints, indexes and CHECK constraints.
- **Currently running on SQLite** (a local file), which needs no database server
  to be installed. Switching to MySQL later is a change to one environment
  variable, `DATABASE_URL`.
- **Written to be portable.** Models are Python classes, so the same definitions
  compile to valid `CREATE TABLE` statements on both SQLite and MySQL. Nothing
  is written in MySQL-only syntax.
- **Seed script** — inserts 3 loan products, 5 users (one per role), 3 customer
  profiles and 3 sample applications. It is **idempotent**: running it twice
  changes nothing and reports "Nothing to do".
- **`docs/schema-contract.md`** — the written handover document for the DB
  teammate: every table with its columns, types, nullability, foreign keys and
  enum vocabularies, plus the deviations I made from the original spec and why.

**One issue found and settled here:** the project blueprint contradicts itself
about which table `loan_applications` points at — the starter SQL in one section
references `users`, which would leave its own `customers` table unreachable. I
followed the table listing and documented it as deviation #1 in the contract, so
the teammate builds to one agreed answer instead of us guessing separately.

### 3.3 Authentication and role authorization

| Method | Endpoint | Access |
|---|---|---|
| POST | `/api/auth/register` | public — always creates a CUSTOMER, returns a token |
| POST | `/api/auth/login` | public — returns a token |
| POST | `/api/auth/change-password` | signed in — requires the current password |
| GET | `/api/users/me` | signed in — own account plus borrower profile |
| PUT | `/api/users/me` | signed in — update own name and profile fields |

- **Passwords** hashed with bcrypt. The hashing cost is configurable, where
  production uses a deliberately slow setting.
- **JWTs** signed with a server secret, sent as `Authorization: Bearer <token>`.
  A rejected request returns a specific code — `UNAUTHENTICATED`, `INVALID_TOKEN`
  or `TOKEN_EXPIRED` — so the frontend can tell "please log in" apart from
  "your session timed out".
- **`@roles_required(...)` middleware** — the mechanism that makes the whole
  role-based design work. Routes declare who may call them, and a valid token
  belonging to the wrong role gets `403`, not `401`.
- **Request validation** with marshmallow schemas, so malformed input is
  rejected at the edge and route handlers only ever see clean data.

Three deliberate security decisions worth calling out:

1. **The role is not trusted from the token.** It is re-read from the database on
   every request. Deactivating an account therefore cuts access immediately,
   instead of the account staying usable until its token expires. There is a test
   that mints a valid token, deactivates the user, and asserts the next request
   is rejected.
2. **Registration rejects a client-supplied `role` field outright** (a 400
   naming the unknown field) instead of silently ignoring it, so an attempt to
   self-promote to ADMIN is visible in the logs rather than invisible. The test
   also asserts no user row was created by the attempt.
3. **Login failures are indistinguishable.** A wrong password, an unknown email
   and a disabled account return a byte-identical 401 body, and an unknown email
   still performs a bcrypt check so the response takes the same time. Otherwise
   the error messages become an oracle for "which emails have accounts here".
   There is a test asserting the two response bodies are equal.

### 3.4 Test suite

**53 automated tests, passing in under a second.**

They run against an in-memory database that is created and destroyed per test, so
they never touch development data and can be run at any time. Coverage includes:

- Foreign keys actually enforced (see the note below on why this needed a test)
- Unique constraints, enum round-tripping, money stored as exact decimal
- Cascade behaviour when a parent row is deleted
- Seed script idempotency
- The error envelope shape
- The whole auth surface: registration rules, generic login failures,
  expired and malformed tokens, role authorization, password changes

### 3.5 Documentation

- `README.md` — what the project is, how to run it, every endpoint and its access
  level, environment variables, project layout, and known limitations.
- `docs/schema-contract.md` — the interface for the DB teammate.

---

## 4. Engineering problems found and solved

These are the parts worth a mentor's attention, because each was a bug that would
have shipped silently.

**1. Auto-increment primary keys silently break on SQLite.**
SQLite only auto-generates a key for a column declared exactly `INTEGER PRIMARY
KEY`. A `BIGINT` key — the correct type for MySQL — is accepted, but every insert
fails on a null key. Since we are building on SQLite and deploying to MySQL, the
types layer maps each key to the right type per database, instead of picking one
and breaking the other backend.

**2. SQLite does not enforce foreign keys by default.**
It parses and stores foreign key definitions and then ignores them unless a pragma
is switched on per connection. Left alone, we would have shipped code that creates
orphaned rows — and it would only have surfaced after the real schema went live.
The pragma is enabled on connect, and a test inserts a row with a missing parent
and asserts it is rejected.

**3. marshmallow's `Regexp` validator is anchored at the start.**
A password pattern using `\d` matched a *leading* digit only, so a perfectly valid
password like `Secret@123` was rejected with a confusing message. Found by testing
the endpoint rather than trusting the schema, and now noted in the code.

**4. A stray process was answering our own health checks.**
During an end-to-end check, requests kept returning 404 for routes that existed.
The cause was an earlier development server still holding the port; on Windows two
processes can bind the same port, so the stale one was silently responding. Worth
knowing because it produces symptoms that look like a routing bug.

---

## 5. How the work was verified

Nothing here is "written, therefore working". Each milestone was checked by
running it:

- `python run.py` starts the server; `/api/health` and `/api/health/ready` both
  return 200; an unknown route returns the expected 404 envelope.
- `flask seed-db --reset` produces `3 products, 5 users, 3 customers, 3
  applications`; running it a second time reports `Nothing to do`.
- `flask routes` lists exactly the 7 endpoints above and nothing more.
- `pytest` → **53 passed**.
- The table definitions were compiled against *both* SQLite and MySQL dialects to
  confirm the generate SQL is valid on each, rather than assuming it.
- A full live sequence was run over real HTTP: register → `/users/me` → `/users/me`
  without a token (401) → login with a wrong password (401) → update profile →
  change password → old password rejected, new password accepted. The server log
  contains no warnings.

---

## 6. Plan for today

**Goal for the day: a customer can create a loan application, save it as a draft,
and submit it — with the server rejecting anything outside the product's rules.**

### Objective 1 — Loan products API

- `GET /api/loan-products` — public, returns only active products.
- `POST` / `PUT` — restricted to ADMIN via `@roles_required("ADMIN")`.
- Validation so a product cannot be created with an invalid amount range, tenure
  range or interest rate (e.g. minimum above maximum).

*Check:* a customer can list products but gets `403` when trying to create one.

### Objective 2 — Application create, draft and update

- `POST /api/applications` — create a draft against a product.
- `GET /api/applications` — a customer sees only their own; an officer sees all.
- `GET` / `PUT /api/applications/<id>` — edit a draft.
- **Ownership enforcement on every one of these routes** — a customer can never
  read or modify another customer's application.

*Check:* customer A gets `403`/`404` (never the data) when requesting customer B's
application id.

### Objective 3 — Submit, with full server-side validation

- `POST /api/applications/<id>/submit` — transitions the application from `DRAFT`
  to `SUBMITTED` and runs the complete validation pass:
  - requested amount within the product's minimum and maximum
  - tenure within the product's allowed range
  - applicant's income meets the product's minimum income requirement
  - all mandatory fields present
  - state transition is legal (a submitted application cannot be re-submitted)

*Check:* submitting with an amount or tenure outside the product limits returns
`400` with a message naming the offending field; a valid submission returns `200`
with the new status.

### Confirmed definition of done for today

A complete write-side flow demonstrable in Postman end to end:
**register → log in → list products → create a draft → submit → see the
application in `SUBMITTED` state**, with every access-control and validation rule
covered by a test.

That point matters beyond today: once the write side is proven, the React
frontend can be built against fixed, tested endpoints instead of against an API
that keeps moving.

**Tomorrow:** the credit assessment engine as a pure function — score, risk level
and recommendation from the applicant's financials, exactly per the project
blueprint's rules — plus its unit tests against the three sample applicants named
in the blueprint. Being a pure function, it takes data in and returns a result with
no database or web layer involved, which makes it fully testable and is why the
blueprint's worked examples can be asserted exactly.

---

## 7. Running and demonstrating the backend

### It does run today

The backend is in a runnable state. It needs **no database server installed** —
the current database is a single local file — and no MongoDB. From a fresh clone:

```bash
cd backend
python -m venv venv
source venv/Scripts/activate        # Windows (Git Bash)
# source venv/bin/activate          # macOS / Linux

pip install -r requirements.txt
cp .env.example .env
flask seed-db --reset
flask run
```

Three commands then demonstrate it:

```bash
# 1. Service is alive
curl http://127.0.0.1:5000/api/health

# 2. Log in as the seeded customer and capture the token
curl -s -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"rahul.kumar@example.test","password":"Password@123"}'

# 3. Call a protected endpoint — first without a token (401), then with it (200)
curl http://127.0.0.1:5000/api/users/me
curl http://127.0.0.1:5000/api/users/me -H "Authorization: Bearer <token>"
```

Or the same in Postman, which is more legible in a review meeting: import the
three requests, show the 401, add the header, show the 200.

### What genuinely cannot be shown yet

Being straight about the limits, because they are about maturity, not breakage:

1. **There is no user interface.** Everything is reachable only through curl or
   Postman. This is by design — the plan deliberately proves the API before
   building the React frontend against it — but it means there is nothing to
   click through, and the whole product currently looks like JSON.
2. **Nothing is deployed.** It runs on `localhost`. There is no public URL to
   open, so it cannot be demonstrated from another machine or from a link.
3. **The database is a stand-in.** Data lives in a local SQLite file, not in the
   real schema, which is owned by another team member. Sequences run against
   throwaway seeded data.
4. **The credit engine does not exist yet**, so no application can currently be
   scored or decided. The flow today ends at "submitted".
5. **No document upload.** MongoDB-backed document storage and the audit log are
   scaffolded but not wired to endpoints.

**If asked to run it live and it does not start on that machine**, the usual
causes are mechanical, not defects: the virtual environment is not activated, or
dependencies were not installed (`pip install -r requirements.txt`); the `.env`
file is missing (`cp .env.example .env`) — it is deliberately not committed
because it holds secrets; or port 5000 is already in use. One note from the
point above: because the database is a file, it is created automatically on first
run, so a missing database never needs to be provisioned by hand.

### The honest one-line answer

> The backend is complete and tested for the foundations, authentication and
> authorization — 7 endpoints and 53 passing tests — but it is an API only at
> this stage, so it can be demonstrated with curl or Postman rather than clicked
> through in a browser. The React interface is the next milestone after the API
> is fully proven, and I can run a live request sequence if that is useful.

---

## 8. Next milestones

| Order | Milestone |
|---|---|
| 1 | Credit assessment service (pure function) + unit tests |
| 2 | Officer review and decision workflow, enforcing the application state machine |
| 3 | MongoDB document upload and audit trail wired to endpoints |
| 4 | React frontend |
| 5 | Re-point `DATABASE_URL` at the real MySQL schema once the teammate delivers it |

---

# 9. Session update - 27 September 2026

Everything above covered milestones 1-3. This section records the rest of the
build: the whole write side, the credit engine, the officer workflow, the
supporting document and audit stores, and the React frontend wired to the real
API.

## 9.1 What was completed

| # | Milestone | Verification |
|---|---|---|
| 4 | **Loan products API** - public active-only listing, admin CRUD, range validation | tests + live requests |
| 5 | **Applications** - create, draft edit, list, submit with full validation | tests + live requests |
| 6 | **Credit engine** - pure function, blueprint rules, exact worked examples | 11 unit tests |
| 7 | **Officer decisions** - approve / reject / request-info, state machine, repayment schedule | tests + live requests |
| 8 | **Documents + audit** - metadata and append-only event trail, MongoDB with an in-memory fallback | tests + live requests |
| 9 | **React frontend** - mock data layer replaced with real API calls; product and borrower imagery added | production build passes |

**BY THE NUMBERS:** 23 API endpoints, 8 tables, 123 tests (from 53 at the start
of the session), and a frontend that builds clean with 0 lint errors.

## 9.2 The credit engine, and a flaw in the supplied rules

The engine is a pure function - financials in, `{score, risk, recommendation,
reasons}` out - so it can be asserted exactly. The three sample applicants from
the blueprint score 510, 590 and 270, and the first two both land on
`HIGH / MANUAL_REVIEW`.

Working through the arithmetic surfaced a **genuine bug in the blueprint's own
policy**: the additive rules peak at `300 + 100 + 80 + 60 + 50 = 590`, but the
document's bands then require `>= 700` for `LOW` and `>= 600` for `MODERATE`.
Both are therefore unreachable, and so is the `ELIGIBLE` recommendation - even a
perfect applicant can only ever be `HIGH / MANUAL_REVIEW`.

I implemented the rules **exactly as specified** (so the blueprint's worked
examples still hold byte for byte) and wrote a test that asserts the 590 ceiling,
with the flaw documented here rather than silently "fixed". That keeps the
engine auditable against the spec and leaves the threshold decision with the
mentor instead of me quietly inventing a policy. If the intent was for the bands
to be reachable, the fix is either a higher base score or lower band
boundaries - a one-line change in `classify()`.

## 9.3 Engineering problems found and solved this session

**1. `g.current_user` leaked between requests in tests.**
The signed-in user was cached on Flask's `g` without a cache key. `g` lives for
the whole application context, and the Flask test client serves several requests
within one context - so a request could see the *previous* request's user. The
symptom was a customer seeing the admin's view of the product catalogue. Fixed by
keying the cache on the JWT identity, so it reloads whenever the identity
changes. In a real server each request gets its own context so it never
surfaced, which is exactly why it was worth catching in tests.

**2. pymongo's `find()` is lazy, so errors escaped the fallback.**
The document/audit store falls back to memory when MongoDB is down. Inserts
failed eagerly and fell back correctly, but `find()` returns a *cursor* without
contacting the server - the connection error then surfaced when the cursor was
iterated, outside the guarded call, and became a 500. Fixed by materialising the
result to a list inside the guarded call. The wrapper also now remembers a
degraded collection for the life of the process, so a down MongoDB is paid for
once (2s) instead of on every request.

**3. marshmallow 4 forbids `required=True` together with `load_default`.**
A validation schema mixed the two and crashed at import. Split into required and
optional fields explicitly.

## 9.4 The frontend: from mock to real

The frontend already existed as a clickable prototype, but **all of its data was
fake**. `AuthContext` held hard-coded products and applications in
`localStorage`, login accepted any password, and the API client silently
returned mock data whenever the backend was unreachable - so the app *looked*
fine with no backend at all.

Changes:

- The API client no longer fabricates responses. A failure is now a failure, with
the backend's own message surfaced to the user.
- `AuthContext` talks to the API for login, registration, products, applications,
submission, assessment, decisions, users and audit.
- A mapping layer translates the API's `snake_case` / decimal-string fields into
the `camelCase` shapes the existing components were written against, so the UI
did not have to be rewritten.
- The officer's decision buttons now really change state on the server, and the
  customer's status updates because the data is re-fetched.
- Role switching in the navbar performs a real login as the corresponding seeded
  demo account.

UI work: the login and register screens gained a banking-theme hero
illustration, the navbar got a proper logo mark, and loan products now show
family icons (personal / vehicle / home). All are hand-written SVG assets - no
binary blobs, no external image hosts.

## 9.5 Verification

- `pytest` -> **123 passed**.
- `flask routes` lists 23 API endpoints.
- A full live sequence was run over real HTTP against `python run.py`:
  login as customer/officer/admin -> list products -> create a draft -> attach a
  document -> submit (scored `510 HIGH MANUAL_REVIEW`) -> a second submit is
  rejected `409 INVALID_STATE` -> the officer approves -> the customer sees
  `APPROVED` with the remarks and documents -> the audit trail shows
  `APPLICATION_CREATED, CREDIT_ASSESSED, APPLICATION_SUBMITTED,
  DECISION_RECORDED`. Rejecting without remarks returns `400`; another customer
  reading the application gets `404`.
- `npm run build` succeeds; `npm run lint` -> **0 errors**.

## 9.6 The honest one-line answer

> The platform is now complete end to end and demonstrable in a browser: a
> customer applies and is scored by a transparent rule engine, an officer decides
> with the assessment in front of them, and every step is audited - 23 endpoints
> and 123 passing tests behind it. The remaining work is swapping the dummy
> SQLite database for the teammate's MySQL schema (a one-line environment change)
> and the deployment/upload items in the README's limitations.

---

# 10. Session update - schema merge

## 10.1 What was asked

"Merge and create the MySQL schema." The teammate's dump (`database/loan_platform.sql`)
and the backend models had drifted apart and the dump's seed hashes could not log
in. The task was to reconcile them into one create-ready schema.

## 10.2 Direction of the merge

The models are the source of truth, because the backend code is written against
them and they are what `docs/schema-contract.md` specifies. Rather than trust a
hand-typed diff, the canonical DDL was **compiled from the models** with
SQLAlchemy's MySQL dialect and then reconciled with the dump's seed data, so the
file cannot disagree with the code it was generated from.

## 10.3 Reconciliation

- Keys `INT` -> `BIGINT`; role/status columns to `VARCHAR(40)` per the contract.
- Added the columns the contract requires but the dump lacked:
  `loan_applications.updated_at`/`submitted_at`,
  `credit_assessments.assessed_by_id`, `customers.created_at`.
- `financial_details.employment_years` `DECIMAL(5,2)` -> `INT`;
  `credit_assessments.reasons_json` JSON -> `TEXT`; `loan_decisions.remarks`
  -> `TEXT`; `loan_products.name` gained `UNIQUE`.
- `ON DELETE CASCADE` added where the ORM cascades (application children,
  `users -> customers`), which the dump did not have.
- Seed data reconciled to `app/utils/seed.py`: `.test` emails, a real bcrypt hash
  for `Password@123` (the placeholder `DEMO_HASH_*` values were unusable),
  `LN-2026-####` application numbers, three products, and financial figures
  matching the demo applicants.
- MongoDB samples reconciled to the enums: valid document type/status and the
  `status_from`/`status_to` audit shape.

## 10.4 Verification

- New `backend/tests/test_schema_sql.py` compiles every model column to MySQL DDL
  and compares type, nullability, column set, unique constraints and cascade
  rules against the SQL file. It also asserts the embedded hash actually
  verifies `Password@123`. **No MySQL server is needed.**
- `pytest` -> **137 passed** (was 123; 14 new schema checks).
- Seed `INSERT` statements were checked for column/value-count consistency.

## 10.5 Remaining

No MySQL 8 server is available on this machine, so the file was validated by
DDL compilation and parity tests rather than by executing it. Importing it and
re-pointing `DATABASE_URL` is the one remaining swap; instructions are in
`database/README.md`.

---

# 11. Session update - move to Supabase (cloud PostgreSQL)

## 11.1 Decision

The MySQL-in-Docker setup works, but every compose file and deployment then
needs a database container to babysit. The database moves to **Supabase
(cloud PostgreSQL, free tier)**: the app reaches it over a connection string,
so neither docker-compose nor the deployment carries a DB container. The
schema contract's "MySQL or PostgreSQL?" question (§10.1) is closed:
PostgreSQL is the deployment target, MySQL stays supported for local parity.

## 11.2 What was done

- `psycopg2-binary>=2.9` added to `backend/requirements.txt` (and installed in
  the venv). It was the one missing driver; the config already rewrote bare
  `postgres://` URLs.
- **`database/loan_platform_postgres.sql`** - the MySQL file compiled from the
  same SQLAlchemy models with the PostgreSQL dialect, then reconciled:
  `BIGSERIAL` keys, named `fk_*` constraints with the same CASCADE rules,
  ORM-named `ix_*` indexes, `BOOLEAN` literals (`TRUE`, not `1`), a
  `set_updated_at()` trigger replacing `ON UPDATE CURRENT_TIMESTAMP`, and
  `setval(..., max+1, false)` sequence resync after the seed inserts.
- `backend/tests/test_schema_sql.py` now guards **both** files against model
  drift (column sets, types, nullability, uniques, cascades, bcrypt hash):
  14 -> 27 checks.
- `.env.example` documents the Supabase pooler/direct URLs.

## 11.3 Traps found by actually running it

- **Boolean literals:** the seed's `1`/`0` booleans fail on PostgreSQL with
  `column "is_active" is of type boolean but expression is of type integer`.
  The Postgres seed uses `TRUE`. (`ON_ERROR_STOP=1` caught it mid-import.)
- **Sequence resync form:** `setval(seq, 1)` on an empty table makes the next
  generated id `2`, not `1` (is_called defaults to true). The file uses
  `setval(seq, max+1, false)` so a pristine database starts children at id 1,
  matching MySQL. Caught because the first E2E application got assessment
  id 2 instead of 1.

## 11.4 Verification (all against live PostgreSQL 16.15 in Docker)

- Import clean and **re-runnable** (drops + recreates; verified by importing
  twice).
- 8 tables, seed counts match `seed.py`; `flask seed-db` -> "Nothing to do".
- Trigger `trg_loan_applications_updated_at` present and firing.
- Sequences positioned exactly: next ids 6/4/4/1/1/1 after reimport.
- FK enforcement live: orphan insert rejected
  (`fk_financial_details_application`).
- App boot on Postgres: `/api/health` -> `database_dialect: postgresql`.
- Full HTTP E2E: login x3 roles -> create draft `LN-2026-0004` (id 4 - the
  resync working) -> submit (score 590, MANUAL_REVIEW) -> approve -> audit
  trail -> document metadata. All rows verified in psql.
- `pytest` -> **150 passed** (was 137; 13 new dual-dialect parity checks).

## 11.5 Remaining

One user step: create the Supabase project and hand over the connection
string; then import the SQL there and re-point `DATABASE_URL` (pooler URL
recommended). Everything else is done and verified.
