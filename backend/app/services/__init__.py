"""Business logic lives here, not in route handlers.

All database access goes through services so that swapping the underlying
schema is a change to this package rather than to every endpoint.

Modules:
    auth_service.py        register / authenticate / change password
    product_service.py     loan product catalogue and admin CRUD
    application_service.py create, update draft, submit, ownership, assessment
    credit_service.py      pure rule-based scoring engine (no DB, no request)
    decision_service.py    approve / reject / request-info + repayment schedule
    audit_service.py       append-only audit trail
    document_service.py    document metadata
"""
