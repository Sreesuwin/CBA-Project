-- =====================================================================
-- Loan Application & Credit Assessment Platform - MySQL 8 schema
-- Database: loan_platform
--
-- MERGED, CREATE-READY SCHEMA
-- ---------------------------------------------------------------------
-- This file reconciles two sources into one schema that the backend can
-- use by changing DATABASE_URL only:
--
--   * the original hand-built dump (int keys, a few missing columns,
--     plaintext placeholder password hashes, APP001-style numbers), and
--   * the SQLAlchemy models in backend/app/models/*, which are the
--     authoritative interface documented in docs/schema-contract.md.
--
-- Where the two disagreed the models win, because the backend code is
-- written against them. The reconciliation applied here:
--
--   1. id / *_id columns are BIGINT AUTO_INCREMENT (models), not INT.
--   2. users.role is VARCHAR(40) (was 30); loan statuses/levels are
--      VARCHAR(40) (was 50) - the longest value is
--      MORE_INFORMATION_REQUIRED (26 chars). Plain VARCHAR, not ENUM,
--      so the same DDL works on SQLite during development.
--   3. loan_applications gains updated_at (NOT NULL, auto-updating) and
--      submitted_at (nullable) - contract deviation #4.
--   4. credit_assessments gains assessed_by_id (nullable FK -> users.id)
--      - contract deviation #5.
--   5. customers gains created_at (NOT NULL) to match the model.
--   6. financial_details.employment_years is INT (whole years), was
--      DECIMAL(5,2).
--   7. credit_assessments.reasons_json is TEXT holding a JSON string,
--      was native JSON - portable and identical in both databases.
--   8. loan_products.name is UNIQUE - contract deviation #2; the seed
--      script keys off it.
--   9. loan_decisions.remarks is TEXT (was VARCHAR(500)).
--  10. All foreign keys use ON DELETE CASCADE where the ORM cascades
--      (application children, user -> customer), so deletes behave the
--      same on MySQL as they do in the test suite.
--  11. Seed accounts use the backend's .test addresses and a REAL bcrypt
--      hash for the shared demo password "Password@123" - the dump's
--      DEMO_HASH_* placeholders could never log in.
--  12. Application numbers use the LN-<year>-<4 digits> format the
--      backend generates, not APP001.
--
-- Create and seed:
--   mysql -u <user> -p < database/loan_platform.sql
--   # then point the backend at it:
--   #   DATABASE_URL=mysql+pymysql://<user>:<password>@127.0.0.1:3306/loan_platform
--   #   cd backend && flask seed-db   # idempotent: sees this data, adds nothing
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `loan_platform`
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE `loan_platform`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `repayments`;
DROP TABLE IF EXISTS `loan_decisions`;
DROP TABLE IF EXISTS `credit_assessments`;
DROP TABLE IF EXISTS `financial_details`;
DROP TABLE IF EXISTS `loan_applications`;
DROP TABLE IF EXISTS `loan_products`;
DROP TABLE IF EXISTS `customers`;
DROP TABLE IF EXISTS `users`;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- users - login accounts for all three roles
-- ---------------------------------------------------------------------
CREATE TABLE `users` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT,
  `name`          VARCHAR(120) NOT NULL,
  `email`         VARCHAR(255) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role`          VARCHAR(40)  NOT NULL,
  `is_active`     TINYINT(1)   NOT NULL DEFAULT 1,
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_email` (`email`),
  KEY `ix_users_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- customers - borrower profile, 1:1 with users
-- ---------------------------------------------------------------------
CREATE TABLE `customers` (
  `id`              BIGINT       NOT NULL AUTO_INCREMENT,
  `user_id`         BIGINT       NOT NULL,
  `dob`             DATE         DEFAULT NULL,
  `phone`           VARCHAR(20)  DEFAULT NULL,
  `address`         VARCHAR(255) DEFAULT NULL,
  `employment_type` VARCHAR(40)  DEFAULT NULL,
  `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_customers_user_id` (`user_id`),
  CONSTRAINT `fk_customers_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- loan_products - the catalogue admins maintain
-- ---------------------------------------------------------------------
CREATE TABLE `loan_products` (
  `id`            BIGINT        NOT NULL AUTO_INCREMENT,
  `name`          VARCHAR(100)  NOT NULL,
  `min_amount`    DECIMAL(12,2) NOT NULL,
  `max_amount`    DECIMAL(12,2) NOT NULL,
  `interest_rate` DECIMAL(5,2)  NOT NULL,
  `min_tenure`    INT           NOT NULL,
  `max_tenure`    INT           NOT NULL,
  `min_income`    DECIMAL(12,2) NOT NULL,
  `active`        TINYINT(1)    NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_loan_products_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- loan_applications
-- ---------------------------------------------------------------------
CREATE TABLE `loan_applications` (
  `id`             BIGINT        NOT NULL AUTO_INCREMENT,
  `application_no` VARCHAR(30)   NOT NULL,
  `customer_id`    BIGINT        NOT NULL,
  `product_id`     BIGINT        NOT NULL,
  `amount`         DECIMAL(12,2) NOT NULL,
  `tenure`         INT           NOT NULL,
  `purpose`        VARCHAR(255)  DEFAULT NULL,
  `status`         VARCHAR(40)   NOT NULL DEFAULT 'DRAFT',
  `created_at`     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                            ON UPDATE CURRENT_TIMESTAMP,
  `submitted_at`   DATETIME      DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_loan_applications_application_no` (`application_no`),
  KEY `ix_loan_applications_customer_id` (`customer_id`),
  KEY `ix_loan_applications_product_id` (`product_id`),
  KEY `ix_loan_applications_status` (`status`),
  CONSTRAINT `fk_applications_customer`
    FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_applications_product`
    FOREIGN KEY (`product_id`) REFERENCES `loan_products` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- financial_details - 1:1 with loan_applications
-- ---------------------------------------------------------------------
CREATE TABLE `financial_details` (
  `id`               BIGINT        NOT NULL AUTO_INCREMENT,
  `application_id`   BIGINT        NOT NULL,
  `monthly_income`   DECIMAL(12,2) NOT NULL,
  `monthly_expenses` DECIMAL(12,2) NOT NULL,
  `existing_emi`     DECIMAL(12,2) NOT NULL,
  `existing_loans`   INT           NOT NULL,
  `employment_years` INT           NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_financial_details_application_id` (`application_id`),
  CONSTRAINT `fk_financial_details_application`
    FOREIGN KEY (`application_id`) REFERENCES `loan_applications` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- credit_assessments - every score run, kept as history
-- ---------------------------------------------------------------------
CREATE TABLE `credit_assessments` (
  `id`             BIGINT      NOT NULL AUTO_INCREMENT,
  `application_id` BIGINT      NOT NULL,
  `score`          INT         NOT NULL,
  `risk_level`     VARCHAR(40) NOT NULL,
  `recommendation` VARCHAR(40) NOT NULL,
  `reasons_json`   TEXT        NOT NULL,
  `assessed_at`    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `assessed_by_id` BIGINT      DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_credit_assessments_application_id` (`application_id`),
  CONSTRAINT `fk_credit_assessments_application`
    FOREIGN KEY (`application_id`) REFERENCES `loan_applications` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_credit_assessments_user`
    FOREIGN KEY (`assessed_by_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- loan_decisions
-- ---------------------------------------------------------------------
CREATE TABLE `loan_decisions` (
  `id`             BIGINT      NOT NULL AUTO_INCREMENT,
  `application_id` BIGINT      NOT NULL,
  `officer_id`     BIGINT      NOT NULL,
  `decision`       VARCHAR(40) NOT NULL,
  `remarks`        TEXT        DEFAULT NULL,
  `decision_date`  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_loan_decisions_application_id` (`application_id`),
  CONSTRAINT `fk_loan_decisions_application`
    FOREIGN KEY (`application_id`) REFERENCES `loan_applications` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_loan_decisions_officer`
    FOREIGN KEY (`officer_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- repayments
-- ---------------------------------------------------------------------
CREATE TABLE `repayments` (
  `id`             BIGINT        NOT NULL AUTO_INCREMENT,
  `application_id` BIGINT        NOT NULL,
  `due_date`       DATE          NOT NULL,
  `amount`         DECIMAL(12,2) NOT NULL,
  `status`         VARCHAR(40)   NOT NULL DEFAULT 'PENDING',
  PRIMARY KEY (`id`),
  KEY `ix_repayments_application_id` (`application_id`),
  CONSTRAINT `fk_repayments_application`
    FOREIGN KEY (`application_id`) REFERENCES `loan_applications` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =====================================================================
-- Seed data
-- ---------------------------------------------------------------------
-- Matches backend/app/utils/seed.py so `flask seed-db` is a no-op after
-- import. All accounts share the password:  Password@123
-- The bcrypt hash below (cost 12) verifies that password.
-- =====================================================================

INSERT INTO `users` (`id`,`name`,`email`,`password_hash`,`role`,`is_active`,`created_at`) VALUES
  (1,'Rahul Kumar','rahul.kumar@example.test','$2b$12$E5P0w7jDEM2scWZAg90H0OoMXIvNpWNQLBSRNcQbXaRvtw5lYC.eW','CUSTOMER',1,'2026-09-18 13:14:00'),
  (2,'Ananya Rao','ananya.rao@example.test','$2b$12$E5P0w7jDEM2scWZAg90H0OoMXIvNpWNQLBSRNcQbXaRvtw5lYC.eW','CUSTOMER',1,'2026-09-18 13:14:00'),
  (3,'Arjun Singh','arjun.singh@example.test','$2b$12$E5P0w7jDEM2scWZAg90H0OoMXIvNpWNQLBSRNcQbXaRvtw5lYC.eW','CUSTOMER',1,'2026-09-18 13:14:00'),
  (4,'Vikram Desai','officer@loanplatform.test','$2b$12$E5P0w7jDEM2scWZAg90H0OoMXIvNpWNQLBSRNcQbXaRvtw5lYC.eW','LOAN_OFFICER',1,'2026-09-18 13:14:00'),
  (5,'Priya Menon','admin@loanplatform.test','$2b$12$E5P0w7jDEM2scWZAg90H0OoMXIvNpWNQLBSRNcQbXaRvtw5lYC.eW','ADMIN',1,'2026-09-18 13:14:00');

INSERT INTO `customers` (`id`,`user_id`,`dob`,`phone`,`address`,`employment_type`,`created_at`) VALUES
  (1,1,'1998-05-12','9876500001','12 MG Road, Bengaluru','SALARIED','2026-09-18 13:14:00'),
  (2,2,'1996-08-21','9876500002','48 Indiranagar, Bengaluru','SALARIED','2026-09-18 13:14:00'),
  (3,3,'2000-02-15','9876500003','9 Sector 21, Noida','SELF_EMPLOYED','2026-09-18 13:14:00');

INSERT INTO `loan_products`
  (`id`,`name`,`min_amount`,`max_amount`,`interest_rate`,`min_tenure`,`max_tenure`,`min_income`,`active`) VALUES
  (1,'Personal Loan', 50000.00, 1000000.00,11.50, 12, 60,25000.00,1),
  (2,'Vehicle Loan', 100000.00, 2000000.00, 9.25, 12, 84,30000.00,1),
  (3,'Home Loan',    500000.00,10000000.00, 8.50, 60,360,40000.00,1);

INSERT INTO `loan_applications`
  (`id`,`application_no`,`customer_id`,`product_id`,`amount`,`tenure`,`purpose`,`status`,`created_at`,`updated_at`,`submitted_at`) VALUES
  (1,'LN-2026-0001',1,1,500000.00,48,'Home renovation', 'SUBMITTED','2026-09-18 13:14:41','2026-09-18 13:14:41','2026-09-18 13:14:41'),
  (2,'LN-2026-0002',2,2,800000.00,60,'New car purchase','SUBMITTED','2026-09-18 13:14:41','2026-09-18 13:14:41','2026-09-18 13:14:41'),
  (3,'LN-2026-0003',3,1,200000.00,36,'Debt consolidation','SUBMITTED','2026-09-18 13:14:41','2026-09-18 13:14:41','2026-09-18 13:14:41');

INSERT INTO `financial_details`
  (`id`,`application_id`,`monthly_income`,`monthly_expenses`,`existing_emi`,`existing_loans`,`employment_years`) VALUES
  (1,1,65000.00,26000.00, 8000.00,1,4),
  (2,2,90000.00,40000.00,12000.00,0,7),
  (3,3,28000.00,18000.00,14000.00,3,1);

-- Assessments, decisions and repayments start empty; they are produced by the
-- application workflow (POST /applications/:id/submit|assess|approve|...).
