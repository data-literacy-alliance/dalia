"""
Modular admin configuration for account_deletion app.

GDPR Article 17 Compliance
---------------------------
This app implements the Right to Erasure (GDPR Article 17) with:
- 30-day grace period before deletion
- Email confirmation required
- Token-based verification
- Audit logging for compliance
- Content review workflow for administrators
- Soft delete with reversibility during grace period
"""

# Import all admin modules to register them with Django
from .inlines import *  # noqa
from .requests import *  # noqa
from .items import *  # noqa
from .logs import *  # noqa
