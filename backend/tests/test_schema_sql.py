"""Guard the hand-maintained schema files against the SQLAlchemy models.

``database/loan_platform.sql`` (MySQL 8) and
``database/loan_platform_postgres.sql`` (PostgreSQL 14+, the Supabase
edition) are maintained by hand, so either can silently drift from the
models the backend actually queries. This test compiles each model column
with the matching SQLAlchemy dialect and compares it to the file text, so
any divergence fails in CI rather than at deployment time.

No database server is needed: the comparison is purely textual.
"""

import re
from pathlib import Path

import pytest
from sqlalchemy.dialects import mysql, postgresql

from app.extensions import db

BASE_DIR = Path(__file__).resolve().parents[2]
SCHEMA_FILES = {
    "mysql": BASE_DIR / "database" / "loan_platform.sql",
    "postgres": BASE_DIR / "database" / "loan_platform_postgres.sql",
}

_CREATE_TABLE = {
    "mysql": re.compile(
        r"CREATE TABLE `(?P<name>\w+)` \((?P<body>.*?)\) ENGINE=", re.DOTALL
    ),
    "postgres": re.compile(r"CREATE TABLE (?P<name>\w+) \((?P<body>.*?)\);", re.DOTALL),
}

# Lines inside CREATE TABLE that are constraints, not columns.
_CONSTRAINT_PREFIXES = {
    "mysql": ("PRIMARY KEY", "UNIQUE KEY", "KEY ", "CONSTRAINT "),
    "postgres": ("CONSTRAINT", "PRIMARY KEY", "FOREIGN KEY", "UNIQUE"),
}

# Type spellings that mean the same thing; normalise before comparing.
_TYPE_ALIASES = {
    "mysql": {"INTEGER": "INT", "NUMERIC": "DECIMAL"},
    "postgres": {
        "BIGSERIAL": "BIGINT",
        "SERIAL": "INT",
        # The model compiles DateTime as TIMESTAMP WITHOUT TIME ZONE; the
        # hand-written file spells it TIMESTAMP.
        "TIMESTAMP": "TIMESTAMP",
    },
}


def _normalize_type(raw: str, dialect: str) -> str:
    text = re.sub(r"\s+", " ", raw.upper().strip())
    if dialect == "postgres":
        text = text.replace("WITHOUT TIME ZONE", "").strip()
    text = re.sub(r"\s+", "", text)
    match = re.match(r"^([A-Z]+)(\(.*\))?$", text)
    if not match:
        return text
    base, params = match.group(1), match.group(2) or ""
    base = _TYPE_ALIASES[dialect].get(base, base)
    if dialect == "mysql" and base == "BOOL":
        base, params = "TINYINT", "(1)"
    return f"{base}{params}"


def _parse_column_mysql(line: str):
    col = re.match(r"`(\w+)`\s+([A-Z0-9_]+(?:\(\d+(?:,\d+)?\))?)(.*)", line)
    if not col:
        return None
    return col.group(1), col.group(2), "NOT NULL" not in col.group(3).upper()


def _parse_column_postgres(line: str):
    col = re.match(r"(\w+)\s+(.*)", line)
    if not col:
        return None
    rest = col.group(2)
    nullable = "NOT NULL" not in rest.upper()
    # The type is everything before the first NOT NULL / DEFAULT qualifier.
    type_part = re.split(r"\bNOT NULL\b|\bDEFAULT\b|\bNULL\b", rest, maxsplit=1, flags=re.IGNORECASE)[0]
    return col.group(1), type_part.strip(), nullable


_COLUMN_PARSERS = {"mysql": _parse_column_mysql, "postgres": _parse_column_postgres}


def _parse_schema(dialect: str):
    """Return ``{table: {column: (type, nullable)}}`` from the SQL file."""
    text = SCHEMA_FILES[dialect].read_text(encoding="utf-8")
    tables = {}
    for match in _CREATE_TABLE[dialect].finditer(text):
        columns = {}
        for line in match.group("body").splitlines():
            line = line.strip().rstrip(",")
            if not line or line.upper().startswith(_CONSTRAINT_PREFIXES[dialect]):
                continue
            parsed = _COLUMN_PARSERS[dialect](line)
            if parsed:
                name, raw_type, nullable = parsed
                columns[name] = (_normalize_type(raw_type, dialect), nullable)
        tables[match.group("name")] = columns
    return tables


def _model_dialect(dialect: str):
    return mysql.dialect() if dialect == "mysql" else postgresql.dialect()


def test_schema_files_exist():
    for dialect, path in SCHEMA_FILES.items():
        assert path.is_file(), f"missing {dialect} schema: {path}"


@pytest.mark.parametrize("dialect", ["mysql", "postgres"])
def test_every_model_table_is_created(dialect):
    created = set(_parse_schema(dialect))
    expected = set(db.metadata.tables)
    assert expected <= created, f"tables missing from the SQL file: {expected - created}"
    assert created == expected, f"SQL file defines unknown tables: {created - expected}"


@pytest.mark.parametrize("dialect", ["mysql", "postgres"])
def test_columns_match_the_models_exactly(dialect):
    schema = _parse_schema(dialect)
    model_dialect = _model_dialect(dialect)
    problems = []

    for table_name, table in db.metadata.tables.items():
        sql_columns = schema[table_name]
        model_columns = {col.name for col in table.columns}

        missing = model_columns - set(sql_columns)
        extra = set(sql_columns) - model_columns
        if missing:
            problems.append(f"{table_name}: missing columns {sorted(missing)}")
        if extra:
            problems.append(f"{table_name}: unexpected columns {sorted(extra)}")

        for column in table.columns:
            if column.name not in sql_columns:
                continue
            expected = _normalize_type(
                column.type.compile(dialect=model_dialect), dialect
            )
            actual = sql_columns[column.name][0]
            if expected != actual:
                problems.append(
                    f"{table_name}.{column.name}: model={expected} sql={actual}"
                )

    assert not problems, "schema drift from the models:\n" + "\n".join(problems)


@pytest.mark.parametrize("dialect", ["mysql", "postgres"])
def test_not_null_matches_the_models(dialect):
    schema = _parse_schema(dialect)
    problems = []

    for table_name, table in db.metadata.tables.items():
        for column in table.columns:
            if column.name not in schema[table_name]:
                continue
            sql_nullable = schema[table_name][column.name][1]
            if bool(column.nullable) != sql_nullable:
                problems.append(
                    f"{table_name}.{column.name}: model nullable={column.nullable} "
                    f"sql nullable={sql_nullable}"
                )

    assert not problems, "nullability drift:\n" + "\n".join(problems)


_UNIQUE_FRAGMENTS = {
    "mysql": [
        ("users", "UNIQUE KEY `ix_users_email` (`email`)"),
        ("loan_products", "UNIQUE KEY `ix_loan_products_name` (`name`)"),
        ("customers", "UNIQUE KEY `ix_customers_user_id` (`user_id`)"),
        (
            "loan_applications",
            "UNIQUE KEY `ix_loan_applications_application_no` (`application_no`)",
        ),
        (
            "financial_details",
            "UNIQUE KEY `ix_financial_details_application_id` (`application_id`)",
        ),
    ],
    "postgres": [
        ("users", "CREATE UNIQUE INDEX ix_users_email ON users (email)"),
        ("loan_products", "CONSTRAINT ix_loan_products_name UNIQUE (name)"),
        ("customers", "CREATE UNIQUE INDEX ix_customers_user_id ON customers (user_id)"),
        (
            "loan_applications",
            "CREATE UNIQUE INDEX ix_loan_applications_application_no ON loan_applications (application_no)",
        ),
        (
            "financial_details",
            "CREATE UNIQUE INDEX ix_financial_details_application_id ON financial_details (application_id)",
        ),
    ],
}


@pytest.mark.parametrize(
    ("dialect", "table", "fragment"),
    [(d, t, f) for d, rows in _UNIQUE_FRAGMENTS.items() for (t, f) in rows],
)
def test_required_unique_constraints_present(dialect, table, fragment):
    text = SCHEMA_FILES[dialect].read_text(encoding="utf-8")
    assert fragment in text, f"{dialect}: {table} is missing {fragment}"


@pytest.mark.parametrize(
    ("dialect", "table"),
    [
        (d, t)
        for d in ("mysql", "postgres")
        for t in ("financial_details", "credit_assessments", "loan_decisions", "repayments")
    ],
)
def test_application_children_cascade_on_delete(dialect, table):
    text = SCHEMA_FILES[dialect].read_text(encoding="utf-8")
    if dialect == "mysql":
        block = re.search(
            rf"CREATE TABLE `{table}` \((.*?)\) ENGINE=", text, re.DOTALL
        ).group(1)
    else:
        block = re.search(
            rf"CREATE TABLE {table} \((.*?)\);", text, re.DOTALL
        ).group(1)
    assert "ON DELETE CASCADE" in block, f"{dialect}: {table} does not cascade on delete"


@pytest.mark.parametrize("dialect", ["mysql", "postgres"])
def test_seed_uses_a_real_bcrypt_hash(dialect):
    # Ignore comment lines - the header explains the placeholders being replaced.
    statements = "\n".join(
        line
        for line in SCHEMA_FILES[dialect].read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    )
    assert "DEMO_HASH_" not in statements, "placeholder hashes cannot log in"
    assert statements.count("$2b$12$") >= 5, "seed users should carry a bcrypt hash"

    # The embedded hash must actually verify the shared demo password, otherwise
    # the seeded accounts cannot log in even though they look real.
    from app.utils.security import verify_password

    stored = re.search(r"(\$2b\$12\$[^']+)", statements).group(1)
    assert verify_password("Password@123", stored)
