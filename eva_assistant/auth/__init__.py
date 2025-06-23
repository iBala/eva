"""
Eva Assistant Authentication Package.

This package provides separate authentication managers for different types of access:
- EvaAuthManager: Handles Eva's own Gmail and Calendar with full permissions
- UserAuthManager: Handles user calendar connections with read-only permissions
- OAuthManager: Legacy manager (deprecated, for backward compatibility)

Usage:
    # For Eva's operations (sending emails, creating events)
    from eva_assistant.auth.eva_auth import EvaAuthManager
    eva_auth = EvaAuthManager()
    gmail_service = await eva_auth.get_gmail_service()
    
    # For user calendar operations (reading events, checking availability)
    from eva_assistant.auth.user_auth import UserAuthManager
    user_auth = UserAuthManager()
    calendar_service = await user_auth.get_user_calendar_service("user123")
"""

from eva_assistant.auth.eva_auth import EvaAuthManager
from eva_assistant.auth.user_auth import UserAuthManager
from eva_assistant.auth.oauth_manager import OAuthManager  # Legacy - deprecated

__all__ = [
    "EvaAuthManager",
    "UserAuthManager", 
    "OAuthManager"  # Kept for backward compatibility
] 