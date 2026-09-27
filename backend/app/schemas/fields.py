"""Shared marshmallow field helpers."""

from marshmallow import fields


def enum_value(attribute):
    """A field that emits an enum column's *value*, e.g. ``"ADMIN"``.

    ``fields.String`` would call ``str()`` on a ``(str, Enum)`` member, which
    yields ``"UserRole.ADMIN"`` rather than ``"ADMIN"``, so serialise the value
    explicitly instead.
    """
    return fields.Function(
        serialize=lambda obj: getattr(getattr(obj, attribute, None), "value", None)
    )
