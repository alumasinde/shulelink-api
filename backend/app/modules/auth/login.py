"""Backward-compatible auth login import surface.

The hardened implementation lives in service.py so all callers share throttling,
MFA challenge handling, tenant login identifiers and transactional session creation.
"""

from app.modules.auth.service import login_user

__all__ = ["login_user"]
