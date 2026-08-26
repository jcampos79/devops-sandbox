"""SQLAlchemy models: User, ApiKey, Instance, CreditTransaction.

Imported here so `Base.metadata` is fully populated for Alembic
autogenerate and for `Base.metadata.create_all()` in tests.
"""

from app.models.api_key import ApiKey  # noqa: F401
from app.models.credit_transaction import CreditTransaction, TransactionType  # noqa: F401
from app.models.instance import Distribution, Instance, InstanceStatus  # noqa: F401
from app.models.user import User  # noqa: F401
