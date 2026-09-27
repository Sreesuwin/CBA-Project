-- =====================================================================
-- Loan Application & Credit Assessment Platform - PostgreSQL schema
-- Target: any PostgreSQL 14+ database. Verified on 16.x; Supabase-ready.
--
-- MERGED, CREATE-READY SCHEMA (Postgres edition)
-- ---------------------------------------------------------------------
-- Same source of truth as database/loan_platform.sql (MySQL): the
-- SQLAlchemy models in backend/app/models/*, compiled with the
-- postgresql dialect and then reconciled. Where a plain compile and the
-- hand-maintained MySQL file disagreed, the MySQL file's decisions win
-- so both databases behave identically:
--
--   * id / *_id columns are BIGSERIAL (BIGINT + sequence), matching the
--     models' BigInt (BIGINT, auto-increment).
--   * Enum-like columns are plain VARCHAR(40), not native enums - the
--     models use native_enum=False so the same values work on SQLite.
--   * Foreign keys are NAMED (fk_*) and use ON DELETE CASCADE exactly
--     where the MySQL file does: application children
--     (financial_details, credit_assessments, loan_decisions,
--     repayments) and customers.user_id -> users. Officer/product links
--     stay RESTRICT (no action).
--   * Indexes carry the same ix_* names the ORM generates, so
--     db.create_all() and this file produce equivalent objects.
--   * Seed data matches backend/app/utils/seed.py with a REAL bcrypt
--     hash for the shared demo password "Password@123".
--   * Sequences are reset with setval() after the explicit-id seed
--     inserts. PostgreSQL does not auto-advance sequences past explicit
--     values (MySQL AUTO_INCREMENT does), so skipping this would make
--     the next API-created row collide with a seeded id.
--
-- Run it (choose ONE):
--   Supabase:  paste into the SQL Editor of your project, or
--              psql "$DATABASE_URL" -f database/loan_platform_postgres.sql
--   Local:     createdb loan_platform
--              psql -d loan_platform -f database/loan_platform_postgres.sql
--
-- The script drops and recreates the 8 tables, so it is safe to re-run
-- to get back to a pristine seeded database.
--
-- Then point the backend at it (bare postgres:// is rewritten to
-- postgresql+psycopg2:// by backend/app/config.py):
--   DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres
--   cd backend && flask seed-db   # idempotent: sees this data, adds nothing
-- =====================================================================

DROP TABLE IF EXISTS repayments CASCADE;
DROP TABLE IF EXISTS loan_decisions CASCADE;
DROP TABLE IF EXISTS credit_assessments CASCADE;
DROP TABLE IF EXISTS financial_details CASCADE;
DROP TABLE IF EXISTS loan_applications CASCADE;
DROP TABLE IF EXISTS loan_products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ---------------------------------------------------------------------
-- users - login accounts for all three roles
-- ---------------------------------------------------------------------
CREATE TABLE users (
  id            BIGSERIAL    NOT NULL,
  name          VARCHAR(120) NOT NULL,
  email         VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role          VARCHAR(40)  NOT NULL,
  is_active     BOOLEAN      NOT NULL DEFAULT true,
  created_at    TIMESTAMP    NOT NULL DEFAULT now(),
  CONSTRAINT pk_users PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_role ON users (role);

-- ---------------------------------------------------------------------
-- customers - borrower profile, 1:1 with users
-- ---------------------------------------------------------------------
CREATE TABLE customers (
  id              BIGSERIAL    NOT NULL,
  user_id         BIGINT       NOT NULL,
  dob             DATE,
  phone           VARCHAR(20),
  address         VARCHAR(255),
  employment_type VARCHAR(40),
  created_at      TIMESTAMP    NOT NULL DEFAULT now(),
  CONSTRAINT pk_customers PRIMARY KEY (id),
  CONSTRAINT fk_customers_user
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_customers_user_id ON customers (user_id);

-- ---------------------------------------------------------------------
-- loan_products - the catalogue admins maintain
-- ---------------------------------------------------------------------
CREATE TABLE loan_products (
  id            BIGSERIAL      NOT NULL,
  name          VARCHAR(100)   NOT NULL,
  min_amount    NUMERIC(12, 2) NOT NULL,
  max_amount    NUMERIC(12, 2) NOT NULL,
  interest_rate NUMERIC(5, 2)  NOT NULL,
  min_tenure    INTEGER        NOT NULL,
  max_tenure    INTEGER        NOT NULL,
  min_income    NUMERIC(12, 2) NOT NULL,
  active        BOOLEAN        NOT NULL DEFAULT true,
  CONSTRAINT pk_loan_products PRIMARY KEY (id),
  CONSTRAINT ix_loan_products_name UNIQUE (name)
);

-- ---------------------------------------------------------------------
-- loan_applications
-- ---------------------------------------------------------------------
CREATE TABLE loan_applications (
  id             BIGSERIAL      NOT NULL,
  application_no VARCHAR(30)    NOT NULL,
  customer_id    BIGINT         NOT NULL,
  product_id     BIGINT         NOT NULL,
  amount         NUMERIC(12, 2) NOT NULL,
  tenure         INTEGER        NOT NULL,
  purpose        VARCHAR(255),
  status         VARCHAR(40)    NOT NULL DEFAULT 'DRAFT',
  created_at     TIMESTAMP      NOT NULL DEFAULT now(),
  updated_at     TIMESTAMP      NOT NULL DEFAULT now(),
  submitted_at   TIMESTAMP,
  CONSTRAINT pk_loan_applications PRIMARY KEY (id),
  CONSTRAINT fk_applications_customer
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE,
  CONSTRAINT fk_applications_product
    FOREIGN KEY (product_id) REFERENCES loan_products (id)
);

CREATE UNIQUE INDEX ix_loan_applications_application_no ON loan_applications (application_no);
CREATE INDEX ix_loan_applications_customer_id ON loan_applications (customer_id);
CREATE INDEX ix_loan_applications_product_id ON loan_applications (product_id);
CREATE INDEX ix_loan_applications_status ON loan_applications (status);

-- updated_at mirrors MySQL's ON UPDATE CURRENT_TIMESTAMP: the ORM sets
-- it via onupdate, this trigger keeps raw SQL honest too.
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_loan_applications_updated_at
  BEFORE UPDATE ON loan_applications
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------
-- financial_details - 1:1 with loan_applications
-- ---------------------------------------------------------------------
CREATE TABLE financial_details (
  id                BIGSERIAL      NOT NULL,
  application_id    BIGINT         NOT NULL,
  monthly_income    NUMERIC(12, 2) NOT NULL,
  monthly_expenses  NUMERIC(12, 2) NOT NULL,
  existing_emi      NUMERIC(12, 2) NOT NULL,
  existing_loans    INTEGER        NOT NULL,
  employment_years  INTEGER        NOT NULL,
  CONSTRAINT pk_financial_details PRIMARY KEY (id),
  CONSTRAINT fk_financial_details_application
    FOREIGN KEY (application_id) REFERENCES loan_applications (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_financial_details_application_id ON financial_details (application_id);

-- ---------------------------------------------------------------------
-- credit_assessments - every score run, kept as history
-- ---------------------------------------------------------------------
CREATE TABLE credit_assessments (
  id             BIGSERIAL   NOT NULL,
  application_id BIGINT      NOT NULL,
  score          INTEGER     NOT NULL,
  risk_level     VARCHAR(40) NOT NULL,
  recommendation VARCHAR(40) NOT NULL,
  reasons_json   TEXT        NOT NULL,
  assessed_at    TIMESTAMP   NOT NULL DEFAULT now(),
  assessed_by_id BIGINT,
  CONSTRAINT pk_credit_assessments PRIMARY KEY (id),
  CONSTRAINT fk_credit_assessments_application
    FOREIGN KEY (application_id) REFERENCES loan_applications (id) ON DELETE CASCADE,
  CONSTRAINT fk_credit_assessments_user
    FOREIGN KEY (assessed_by_id) REFERENCES users (id)
);

CREATE INDEX ix_credit_assessments_application_id ON credit_assessments (application_id);

-- ---------------------------------------------------------------------
-- loan_decisions
-- ---------------------------------------------------------------------
CREATE TABLE loan_decisions (
  id             BIGSERIAL   NOT NULL,
  application_id BIGINT      NOT NULL,
  officer_id     BIGINT      NOT NULL,
  decision       VARCHAR(40) NOT NULL,
  remarks        TEXT,
  decision_date  TIMESTAMP   NOT NULL DEFAULT now(),
  CONSTRAINT pk_loan_decisions PRIMARY KEY (id),
  CONSTRAINT fk_loan_decisions_application
    FOREIGN KEY (application_id) REFERENCES loan_applications (id) ON DELETE CASCADE,
  CONSTRAINT fk_loan_decisions_officer
    FOREIGN KEY (officer_id) REFERENCES users (id)
);

CREATE INDEX ix_loan_decisions_application_id ON loan_decisions (application_id);

-- ---------------------------------------------------------------------
-- repayments
-- ---------------------------------------------------------------------
CREATE TABLE repayments (
  id             BIGSERIAL      NOT NULL,
  application_id BIGINT         NOT NULL,
  due_date       DATE           NOT NULL,
  amount         NUMERIC(12, 2) NOT NULL,
  status         VARCHAR(40)    NOT NULL DEFAULT 'PENDING',
  CONSTRAINT pk_repayments PRIMARY KEY (id),
  CONSTRAINT fk_repayments_application
    FOREIGN KEY (application_id) REFERENCES loan_applications (id) ON DELETE CASCADE
);

CREATE INDEX ix_repayments_application_id ON repayments (application_id);

-- =====================================================================
-- Seed data
-- ---------------------------------------------------------------------
-- Matches backend/app/utils/seed.py so `flask seed-db` is a no-op after
-- import. All accounts share the password:  Password@123
-- The bcrypt hash below (cost 12) verifies that password.
-- =====================================================================

-- PostgreSQL is strict about booleans: TRUE/FALSE, not the 1/0 the MySQL
-- edition can use.
INSERT INTO users (id, name, email, password_hash, role, is_active, created_at) VALUES
  (1,'Rahul Kumar','rahul.kumar@example.test','$2b$12$E5P0w7jDEM2scWZAg90H0OoMXIvNpWNQLBSRNcQbXaRvtw5lYC.eW','CUSTOMER',TRUE,'2026-09-18 13:14:00'),
  (2,'Ananya Rao','ananya.rao@example.test','$2b$12$E5P0w7jDEM2scWZAg90H0OoMXIvNpWNQLBSRNcQbXaRvtw5lYC.eW','CUSTOMER',TRUE,'2026-09-18 13:14:00'),
  (3,'Arjun Singh','arjun.singh@example.test','$2b$12$E5P0w7jDEM2scWZAg90H0OoMXIvNpWNQLBSRNcQbXaRvtw5lYC.eW','CUSTOMER',TRUE,'2026-09-18 13:14:00'),
  (4,'Vikram Desai','officer@loanplatform.test','$2b$12$E5P0w7jDEM2scWZAg90H0OoMXIvNpWNQLBSRNcQbXaRvtw5lYC.eW','LOAN_OFFICER',TRUE,'2026-09-18 13:14:00'),
  (5,'Priya Menon','admin@loanplatform.test','$2b$12$E5P0w7jDEM2scWZAg90H0OoMXIvNpWNQLBSRNcQbXaRvtw5lYC.eW','ADMIN',TRUE,'2026-09-18 13:14:00');

INSERT INTO customers (id, user_id, dob, phone, address, employment_type, created_at) VALUES
  (1,1,'1998-05-12','9876500001','12 MG Road, Bengaluru','SALARIED','2026-09-18 13:14:00'),
  (2,2,'1996-08-21','9876500002','48 Indiranagar, Bengaluru','SALARIED','2026-09-18 13:14:00'),
  (3,3,'2000-02-15','9876500003','9 Sector 21, Noida','SELF_EMPLOYED','2026-09-18 13:14:00');

INSERT INTO loan_products
  (id, name, min_amount, max_amount, interest_rate, min_tenure, max_tenure, min_income, active) VALUES
  (1,'Personal Loan', 50000.00, 1000000.00,11.50, 12, 60,25000.00,TRUE),
  (2,'Vehicle Loan', 100000.00, 2000000.00, 9.25, 12, 84,30000.00,TRUE),
  (3,'Home Loan',    500000.00,10000000.00, 8.50, 60,360,40000.00,TRUE);

INSERT INTO loan_applications
  (id, application_no, customer_id, product_id, amount, tenure, purpose, status, created_at, updated_at, submitted_at) VALUES
  (1,'LN-2026-0001',1,1,500000.00,48,'Home renovation', 'SUBMITTED','2026-09-18 13:14:41','2026-09-18 13:14:41','2026-09-18 13:14:41'),
  (2,'LN-2026-0002',2,2,800000.00,60,'New car purchase','SUBMITTED','2026-09-18 13:14:41','2026-09-18 13:14:41','2026-09-18 13:14:41'),
  (3,'LN-2026-0003',3,1,200000.00,36,'Debt consolidation','SUBMITTED','2026-09-18 13:14:41','2026-09-18 13:14:41','2026-09-18 13:14:41');

INSERT INTO financial_details
  (id, application_id, monthly_income, monthly_expenses, existing_emi, existing_loans, employment_years) VALUES
  (1,1,65000.00,26000.00, 8000.00,1,4),
  (2,2,90000.00,40000.00,12000.00,0,7),
  (3,3,28000.00,18000.00,14000.00,3,1);

-- Assessments, decisions and repayments start empty; they are produced by the
-- application workflow (POST /applications/:id/submit|assess|approve|...).

-- ---------------------------------------------------------------------
-- Sequence sync. The seed inserts used explicit ids; PostgreSQL does not
-- advance the sequences for those, so without this the next
-- API-generated row would reuse an existing id and fail. MySQL does this
-- implicitly via AUTO_INCREMENT.
--
-- setval(seq, max+1, false) makes the next nextval() return max+1. The
-- is_called=false form matters for empty tables: setval(seq, 1) alone
-- would make the first generated id 2 instead of 1.
-- ---------------------------------------------------------------------
SELECT setval(pg_get_serial_sequence('users', 'id'),              COALESCE((SELECT MAX(id) FROM users), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('customers', 'id'),          COALESCE((SELECT MAX(id) FROM customers), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('loan_products', 'id'),      COALESCE((SELECT MAX(id) FROM loan_products), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('loan_applications', 'id'),  COALESCE((SELECT MAX(id) FROM loan_applications), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('financial_details', 'id'),  COALESCE((SELECT MAX(id) FROM financial_details), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('credit_assessments', 'id'), COALESCE((SELECT MAX(id) FROM credit_assessments), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('loan_decisions', 'id'),     COALESCE((SELECT MAX(id) FROM loan_decisions), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('repayments', 'id'),         COALESCE((SELECT MAX(id) FROM repayments), 0) + 1, false);
