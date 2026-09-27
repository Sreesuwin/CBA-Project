# Database Schema Contract

**Audience:** whoever is building the real database schema for the Loan
Application & Credit Assessment Platform.
**Status:** the backend currently runs against a dummy SQLite database. The
tables below are the interface the backend code expects. **This contract has
been merged with the hand-built dump into create-ready schemas at
`database/loan_platform.sql` (MySQL 8) and
`database/loan_platform_postgres.sql` (PostgreSQL 14+ — the deployment target,
cloud-hosted on Supabase)** — import either file and the backend points at it by
changing one environment variable (`DATABASE_URL`); no code changes. See §9.

Last updated: both schemas create-ready and verified live (MySQL 8.0 in Docker,
PostgreSQL 16 in Docker; 150 checks pass). All 23 API endpoints run against the
models below; document and audit data live in MongoDB, everything else here.
`backend/tests/test_schema_sql.py` fails if either SQL file drifts from the
models.

---

## 1. Naming and conventions

| Convention | Rule |
|---|---|
| Table names | `snake_case`, plural (`loan_applications`, not `LoanApplication`) |
| Column names | `snake_case` (`monthly_income`, not `monthlyIncome`) |
| Primary keys | `id`, 64-bit integer, auto-increment |
| Foreign keys | `<referenced_entity>_id` (`customer_id`, `product_id`, `officer_id`) |
| Booleans | `is_*` / adjective form, stored as tinyint/bool (`is_active`, `active`) |
| Money | `DECIMAL(12,2)` — **never** `FLOAT`/`DOUBLE`. The backend compares and sums these values; binary floating point rounding would corrupt the credit calculation. |
| Rates | `DECIMAL(5,2)`, stored as a percentage (`11.50` means 11.5% p.a.) |
| Timestamps | UTC, naive (no timezone suffix stored) |
| Status/role columns | `VARCHAR(40)` holding one of the fixed strings in §3. **Not** a MySQL `ENUM`. |

**Why not MySQL `ENUM`?** We need the same DDL on SQLite during development and
MySQL in production. A `VARCHAR` plus the values in §3 keeps both in step, and
changing a status later is an `UPDATE`, not an `ALTER TABLE`. If you prefer a
native `ENUM`, it is compatible as long as the stored strings match §3 exactly —
but tell the backend owner so the model definitions are updated to match.

**Why the fixed string lengths?** They are not enforced by SQLite, so the
backend does not rely on them for validation. They are there to constrain the
real schema so a column can never silently expand past its declared width.

---

## 2. Tables

### `users` — login accounts for all three roles

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | BIGINT | no | PK | auto-increment |
| `name` | VARCHAR(120) | no | | display name |
| `email` | VARCHAR(255) | no | **UNIQUE**, indexed | used as the login identifier; store lower-cased |
| `password_hash` | VARCHAR(255) | no | | bcrypt output (always 60 chars today); never a plain digest |
| `role` | VARCHAR(40) | no | indexed | one of §3.1 |
| `is_active` | BOOLEAN | no | | default `TRUE`; deactivated users must not be able to log in |
| `created_at` | DATETIME | no | | default now |

### `customers` — borrower profile, 1:1 with `users`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | BIGINT | no | PK | auto-increment |
| `user_id` | BIGINT | no | **UNIQUE**, FK → `users.id` | one profile per login |
| `dob` | DATE | yes | | |
| `phone` | VARCHAR(20) | yes | | |
| `address` | VARCHAR(255) | yes | | |
| `employment_type` | VARCHAR(40) | yes | | one of §3.6 |
| `created_at` | DATETIME | no | | default now |

Only customers have a row here. Loan officers and admins exist only in `users`.

### `loan_products` — the catalogue admins maintain

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | BIGINT | no | PK | auto-increment |
| `name` | VARCHAR(100) | no | **UNIQUE** | natural key for the seed script and admin UI |
| `min_amount` | DECIMAL(12,2) | no | | inclusive lower bound |
| `max_amount` | DECIMAL(12,2) | no | | inclusive upper bound |
| `interest_rate` | DECIMAL(5,2) | no | | annual %, used for EMI display |
| `min_tenure` | INT | no | | months, inclusive |
| `max_tenure` | INT | no | | months, inclusive |
| `min_income` | DECIMAL(12,2) | no | | applicant must earn at least this much |
| `active` | BOOLEAN | no | | default `TRUE`; inactive products are hidden from customers but existing applications stay valid |

### `loan_applications`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | BIGINT | no | PK | auto-increment |
| `application_no` | VARCHAR(30) | no | **UNIQUE**, indexed | human-readable, format `LN-<year>-<4 digits>` e.g. `LN-2026-0001`. **Generated server-side only** — never accepted from a client. |
| `customer_id` | BIGINT | no | FK → `customers.id`, indexed | |
| `product_id` | BIGINT | no | FK → `loan_products.id`, indexed | |
| `amount` | DECIMAL(12,2) | no | | must fall inside the product's limits |
| `tenure` | INT | no | | months; must fall inside the product's limits |
| `purpose` | VARCHAR(255) | yes | | free text as typed by the customer |
| `status` | VARCHAR(40) | no | indexed | one of §3.2, default `DRAFT` |
| `created_at` | DATETIME | no | | |
| `updated_at` | DATETIME | no | | set on every write |
| `submitted_at` | DATETIME | yes | | null while `DRAFT` |

### `financial_details` — 1:1 with `loan_applications`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | BIGINT | no | PK | auto-increment |
| `application_id` | BIGINT | no | **UNIQUE**, FK → `loan_applications.id` | |
| `monthly_income` | DECIMAL(12,2) | no | | must be > 0; the credit engine divides by it |
| `monthly_expenses` | DECIMAL(12,2) | no | | must be >= 0 |
| `existing_emi` | DECIMAL(12,2) | no | | must be >= 0; drives the EMI-ratio rule |
| `existing_loans` | INT | no | | must be >= 0 |
| `employment_years` | INT | no | | must be >= 0 |

### `credit_assessments` — every score run, kept as history

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | BIGINT | no | PK | auto-increment |
| `application_id` | BIGINT | no | FK → `loan_applications.id`, indexed | |
| `score` | INT | no | | rule-engine total (see the doc's §13/§14) |
| `risk_level` | VARCHAR(40) | no | | one of §3.3 |
| `recommendation` | VARCHAR(40) | no | | one of §3.4 |
| `reasons_json` | TEXT | no | | JSON-encoded `list[str]`, e.g. `["High monthly income","Low existing EMI burden"]`. TEXT rather than a native JSON column so both databases behave identically. |
| `assessed_at` | DATETIME | no | | insert order = reassessment order |
| `assessed_by_id` | BIGINT | yes | FK → `users.id` | who triggered it (officer), null when the customer triggered it on submit |

One application may accumulate **many** assessments. The newest row is the
current one; older rows are the audit trail.

### `loan_decisions`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | BIGINT | no | PK | auto-increment |
| `application_id` | BIGINT | no | FK → `loan_applications.id`, indexed | |
| `officer_id` | BIGINT | no | FK → `users.id` | must reference a user whose `role = 'LOAN_OFFICER'` — the FK cannot express this, so the backend service enforces it |
| `decision` | VARCHAR(40) | no | | one of §3.5 |
| `remarks` | TEXT | yes | | mandatory in the UI when rejecting or requesting information |
| `decision_date` | DATETIME | no | | |

### `repayments`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| `id` | BIGINT | no | PK | auto-increment |
| `application_id` | BIGINT | no | FK → `loan_applications.id`, indexed | |
| `due_date` | DATE | no | | |
| `amount` | DECIMAL(12,2) | no | | instalment amount |
| `status` | VARCHAR(40) | no | | one of §3.7, default `PENDING` |

Populated only for approved loans; not on the critical path for the first demo.

---

## 3. Controlled vocabularies

Stored strings must match these **exactly** (upper case, underscore separators).
The backend compares them as strings.

**3.1 `users.role`** — `CUSTOMER`, `LOAN_OFFICER`, `ADMIN`

**3.2 `loan_applications.status`** — `DRAFT`, `SUBMITTED`, `UNDER_REVIEW`,
`MORE_INFORMATION_REQUIRED`, `APPROVED`, `REJECTED`

**3.3 `credit_assessments.risk_level`** — `LOW`, `MODERATE`, `HIGH`, `VERY_HIGH`

**3.4 `credit_assessments.recommendation`** — `ELIGIBLE`, `MANUAL_REVIEW`,
`NOT_RECOMMENDED`

**3.5 `loan_decisions.decision`** — `APPROVE`, `REJECT`, `REQUEST_INFO`

**3.6 `customers.employment_type`** — `SALARIED`, `SELF_EMPLOYED`,
`BUSINESS_OWNER`, `STUDENT`, `UNEMPLOYED`, `RETIRED`

**3.7 `repayments.status`** — `PENDING`, `PAID`, `OVERDUE`

The longest value is `MORE_INFORMATION_REQUIRED` (26 characters), which is why
these columns are sized `VARCHAR(40)`.

---

## 4. Relationships

```
users 1 ──── 1 customers            (customers.user_id, UNIQUE)
users 1 ──── * loan_decisions       (loan_decisions.officer_id)
users 1 ──── * credit_assessments   (credit_assessments.assessed_by_id, nullable)
customers 1 ──── * loan_applications (loan_applications.customer_id)
loan_products 1 ──── * loan_applications (loan_applications.product_id)
loan_applications 1 ──── 1 financial_details   (financial_details.application_id, UNIQUE)
loan_applications 1 ──── * credit_assessments  (reassessment history)
loan_applications 1 ──── * loan_decisions
loan_applications 1 ──── * repayments
```

**Every foreign key must be enforced** (InnoDB on MySQL). The backend relies on
this: a `Customer` row pointing at a non-existent user would break the
ownership check that stops one customer reading another's application.

---

## 5. Deliberate deviations from §9/§10 of the project doc

Please implement these instead of the doc's starter schema — the doc contradicts
itself and the backend follows the version below.

| # | Deviation | Reason |
|---|---|---|
| 1 | `loan_applications.customer_id` references **`customers.id`**, not `users.id` | §9 lists a `customers` table with `user_id`, but §10's starter SQL points the FK at `users`. Following §10 would make the `customers` table unreachable from an application and duplicate the profile fields. The backend resolves the signed-in user through `customers.user_id`. |
| 2 | `loan_products.name` is **UNIQUE** | The seed script is idempotent keyed on the product name, and the admin UI must not allow duplicate display names. |
| 3 | Status/role columns are **VARCHAR(40)**, not MySQL `ENUM` | Portability between the development and production databases (§1). |
| 4 | `loan_applications.updated_at` and `submitted_at` added | §9 has only `created_at`, but the officer queue wants to sort by submission time and the UI needs a "last modified" value. |
| 5 | `credit_assessments.assessed_by_id` added (nullable) | Lets the audit trail distinguish "customer triggered on submit" from "officer re-ran the assessment". |
| 6 | `customers.employment_type` is `VARCHAR(40)`, not free text | Kept in step with the vocabulary in §3.6. |

---

## 6. Guarantees the backend assumes

These are enforced by the database today (and are covered by the test suite
against SQLite). If your schema cannot provide one, say so before the swap.

1. `users.email` is unique, and the app treats it case-insensitively.
2. `loan_applications.application_no` is unique.
3. `customers.user_id` is unique (one profile per login).
4. `financial_details.application_id` is unique (one financial record per application).
5. Foreign keys are enforced, not merely declared.
6. Deleting a `loan_application` removes its `financial_details`,
   `credit_assessments`, `loan_decisions` and `repayments`
   (the ORM configures `ON DELETE CASCADE` behaviour; an explicit
   `ON DELETE CASCADE` in the schema is acceptable and preferred).
7. Money columns return exact decimals, not floats.

Validation the backend does **not** delegate to the database (it repeats these in
Python, so a lax column type is not a correctness risk): email format, password
strength, loan amount/tenure inside product limits, income > 0, `existing_emi`
and `existing_loans` non-negative, and every status/role value being one of §3.

---

## 7. Indexes

Already declared by the models, so on MySQL they will be created automatically:

| Table | Indexed columns |
|---|---|
| `users` | `email` (unique), `role` |
| `customers` | `user_id` (unique) |
| `loan_products` | `name` (unique) |
| `loan_applications` | `application_no` (unique), `customer_id`, `product_id`, `status` |
| `financial_details` | `application_id` (unique) |
| `credit_assessments` | `application_id` |
| `loan_decisions` | `application_id` |
| `repayments` | `application_id` |

The `status` and `customer_id` indexes exist for the two hot queries: the
officer's pending queue (filter by status) and a customer's own application list
(filter by customer).

---

## 8. MongoDB collections

MongoDB holds only data whose shape may change: document metadata and the audit
trail. It is never the source of truth for a loan decision.

`documents` — one document per application, keyed by `application_id`

```json
{
  "application_id": 10025,
  "files": [
    {
      "type": "SALARY_SLIP",
      "filename": "salary.pdf",
      "status": "PENDING",
      "uploaded_at": "2026-09-08T10:00:00Z"
    }
  ]
}
```

`type` is one of `SALARY_SLIP`, `BANK_STATEMENT`, `ID_PROOF`, `ADDRESS_PROOF`,
`ITR`, `OTHER`; `status` is one of `PENDING`, `VERIFIED`, `REJECTED`.

`audit_logs` — append-only, one document per event

```json
{
  "application_id": 10025,
  "actor_id": 51,
  "action": "APPLICATION_SUBMITTED",
  "metadata": {"status_from": "DRAFT", "status_to": "SUBMITTED"},
  "timestamp": "2026-09-08T10:05:00Z"
}
```

Suggested indexes: `documents` unique on `application_id`; `audit_logs` on
`application_id` and `timestamp`.

---

## 9. Swapping this in

### 9.1 The merged, create-ready schema

`database/loan_platform.sql` is the contract above reconciled with the
teammate's original dump. Where the two disagreed, this document (and the
models) won. The merge applied:

- `BIGINT` keys (was `INT`); status/role columns `VARCHAR(40)` (was 30/50).
- Added `loan_applications.updated_at` / `submitted_at`,
  `credit_assessments.assessed_by_id`, `customers.created_at` (deviations #4, #5).
- `financial_details.employment_years` is `INT`; `credit_assessments.reasons_json`
  is `TEXT`; `loan_products.name` is `UNIQUE` (deviation #2).
- `ON DELETE CASCADE` on application children and `users → customers`, matching
  the ORM cascade.
- Seed rows reconciled to the backend's demo dataset (`app/utils/seed.py`):
  `.test` email addresses and a **real bcrypt hash** for `Password@123`, so the
  seeded accounts can actually log in (the dump's `DEMO_HASH_*` placeholders
  could not). Application numbers use the `LN-<year>-<4 digits>` format.

The MongoDB sample documents (`database/documents.json`,
`database/audit_logs.json`) were reconciled the same way: valid `DocumentType` /
`DocumentStatus` values and the `status_from` / `status_to` audit metadata shape.

Create it and point the backend at it:

```bash
mysql -u <user> -p < database/loan_platform.sql
# DATABASE_URL=mysql+pymysql://<user>:<password>@127.0.0.1:3306/loan_platform
```

Then `flask seed-db` is idempotent — it sees the seeded rows and adds nothing.

### 9.2 Switching the running app

No application code changes. In `backend/.env`:

```env
# before
DATABASE_URL=sqlite:///loan_platform.db

# after — MySQL
dATABASE_URL=mysql+pymysql://<user>:<password>@<host>:<port>/<schema>
# after — PostgreSQL / Supabase
dATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<schema>
```

A bare `mysql://…` URL is rewritten to `mysql+pymysql://` and a bare
`postgres://…` to `postgresql+psycopg2://` (see `app/config.py`).

Then:

```bash
cd backend
flask seed-db          # inserts loan products, demo users and applications
pytest                 # 150 checks, incl. schema-vs-model parity for both dialects
```

If your column names differ from §2, that is workable but not free — tell the
backend owner the exact names and only the model definitions change, since all
queries live in `app/models/` and `app/services/`.

---

## 10. Decisions (previously open questions)

1. **MySQL or PostgreSQL?** ~~Open.~~ **PostgreSQL, cloud-hosted on Supabase,
   is the deployment target** (no database container to run in docker-compose
   or production). MySQL remains fully supported for local parity — both
   schemas are generated from the same models and guarded by the same tests.
   `psycopg2-binary` and `PyMySQL` are both in `requirements.txt`.
2. **Native `ENUM` or `VARCHAR`?** Either is fine as long as the stored strings
   match §3. State which you pick.
3. **`ON DELETE CASCADE` explicitly?** The backend expects deletes to cascade;
   confirm you have added it rather than relying on the ORM to do the work.
4. **Any extra feature columns** (e.g. soft-delete flags, audit columns) — add
   them as nullable so the existing inserts keep working.
