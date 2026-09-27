"""Column types shared by every model.

Defined once so the dummy SQLite database and the real MySQL schema stay in
step: we change the database URL, never the type definitions.
"""

from ..extensions import db

# SQLite only auto-increments a column whose declared type is exactly
# ``INTEGER PRIMARY KEY``, so a literal BIGINT key would never be populated.
# ``with_variant`` renders BIGINT on MySQL and INTEGER on SQLite.
BigInt = db.BigInteger().with_variant(db.Integer, "sqlite")


def enum_column(enum_cls, name):
    """A portable enum column.

    ``native_enum=False`` stores members as VARCHAR on every backend rather than
    using MySQL ENUM, so the same model produces comparable DDL everywhere.
    ``length`` must exceed the longest member name (MORE_INFORMATION_REQUIRED).
    """
    return db.Enum(enum_cls, name=name, native_enum=False, length=40)
