"""
OAuth Manager for Eva Assistant.

Handles Google OAuth flows for:
1. Eva's Gmail account (for sending emails and calendar invites)
2. Dynamic user calendar connections (READ-ONLY access for availability checking)

This module provides secure token management, automatic refresh, and
multi-user calendar authentication.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from eva_assistant.config import get_eva_oauth_config, get_user_oauth_config

logger = logging.getLogger(__name__)


class OAuthManager:
    """Manages OAuth credentials for Eva's Gmail and dynamic user calendar connections."""
    
    def __init__(self):
        """Initialize OAuth manager with configuration."""
        self.eva_config = get_eva_oauth_config()
        
        # Ensure token directory exists
        self.eva_config["token_file"].parent.mkdir(parents=True, exist_ok=True)
    
    def _load_credentials(self, config: Dict[str, Any]) -> Optional[Credentials]:
        """Load credentials from token file if it exists."""
        token_file = config["token_file"]
        if not token_file.exists():
            logger.info(f"Token file {token_file} does not exist")
            return None
        
        try:
            creds = Credentials.from_authorized_user_file(
                str(token_file), 
                config["scopes"]
            )
            logger.info(f"Loaded credentials from {token_file}")
            return creds
        except Exception as e:
            logger.error(f"Failed to load credentials from {token_file}: {e}")
            return None
    
    def _save_credentials(self, creds: Credentials, config: Dict[str, Any]) -> None:
        """Save credentials to token file."""
        token_file = config["token_file"]
        try:
            with open(token_file, 'w') as f:
                f.write(creds.to_json())
            logger.info(f"Saved credentials to {token_file}")
        except Exception as e:
            logger.error(f"Failed to save credentials to {token_file}: {e}")
            raise
    
    def _refresh_credentials(self, creds: Credentials, config: Dict[str, Any]) -> Credentials:
        """Refresh expired credentials."""
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_credentials(creds, config)
                logger.info("Successfully refreshed credentials")
                return creds
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}")
                raise
        return creds
    
    def _run_oauth_flow(self, config: Dict[str, Any]) -> Credentials:
        """Run OAuth flow to get new credentials."""
        logger.info("Starting OAuth flow...")
        
        # Create client config for installed app flow
        client_config = {
            "web": {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        
        flow = InstalledAppFlow.from_client_config(
            client_config, 
            config["scopes"]
        )
        
        # Run local server for OAuth callback
        # Using port 8080 for consistent redirect URI
        creds = flow.run_local_server(port=8080)
        
        # Save the credentials
        self._save_credentials(creds, config)
        logger.info("OAuth flow completed successfully")
        
        return creds
    
    def get_eva_credentials(self) -> Credentials:
        """
        Get valid credentials for Eva's Gmail account.
        
        Returns:
            Credentials: Valid Google OAuth credentials for Eva's account
            
        Raises:
            Exception: If OAuth flow fails or credentials cannot be obtained
        """
        logger.info("Getting Eva's Gmail credentials...")
        
        # Try to load existing credentials
        creds = self._load_credentials(self.eva_config)
        
        if creds is None:
            # No credentials found, run OAuth flow
            logger.info("No Eva credentials found, starting OAuth flow")
            creds = self._run_oauth_flow(self.eva_config)
        elif not creds.valid:
            # Credentials exist but are invalid
            if creds.expired and creds.refresh_token:
                # Try to refresh
                logger.info("Eva credentials expired, attempting refresh")
                creds = self._refresh_credentials(creds, self.eva_config)
            else:
                # Cannot refresh, need new OAuth flow
                logger.info("Eva credentials invalid and cannot refresh, starting OAuth flow")
                creds = self._run_oauth_flow(self.eva_config)
        
        logger.info("Eva credentials ready")
        return creds
    
    def get_user_credentials(self, user_id: str) -> Credentials:
        """
        Get valid credentials for a user's calendar account (READ-ONLY).
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Credentials: Valid Google OAuth credentials for user's calendar
            
        Raises:
            Exception: If OAuth flow fails or credentials cannot be obtained
        """
        logger.info(f"Getting calendar credentials for user: {user_id}")
        
        # Get user-specific OAuth config
        user_config = get_user_oauth_config(user_id)
        
        # Try to load existing credentials
        creds = self._load_credentials(user_config)
        
        if creds is None:
            # No credentials found, run OAuth flow
            logger.info(f"No credentials found for user {user_id}, starting OAuth flow")
            creds = self._run_oauth_flow(user_config)
        elif not creds.valid:
            # Credentials exist but are invalid
            if creds.expired and creds.refresh_token:
                # Try to refresh
                logger.info(f"User {user_id} credentials expired, attempting refresh")
                creds = self._refresh_credentials(creds, user_config)
            else:
                # Cannot refresh, need new OAuth flow
                logger.info(f"User {user_id} credentials invalid and cannot refresh, starting OAuth flow")
                creds = self._run_oauth_flow(user_config)
        
        logger.info(f"User {user_id} credentials ready")
        return creds
    
    async def connect_user_calendar(self, user_id: str) -> Dict[str, Any]:
        """
        Connect a user's calendar through OAuth flow.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dict containing user info and connected calendars
            
        Raises:
            Exception: If OAuth flow fails or calendar access fails
        """
        logger.info(f"Initiating calendar connection for user: {user_id}")
        
        # Get credentials (this will trigger OAuth flow if needed)
        creds = self.get_user_credentials(user_id)
        
        # Get calendar service - wrap blocking build() call in asyncio.to_thread()
        service = await asyncio.to_thread(build, 'calendar', 'v3', credentials=creds)
        
        # Get user's calendar list - wrap blocking API call in asyncio.to_thread()
        calendar_list = await asyncio.to_thread(service.calendarList().list().execute)
        calendars = calendar_list.get('items', [])
        
        # Get user's profile info
        user_info = {
            'user_id': user_id,
            'email': creds.id_token_json.get('email') if hasattr(creds, 'id_token_json') else 'unknown',
            'connected_at': creds.expiry.isoformat() if creds.expiry else None,
            'calendars': [
                {
                    'id': cal.get('id'),
                    'summary': cal.get('summary'),
                    'primary': cal.get('primary', False),
                    'access_role': cal.get('accessRole')
                }
                for cal in calendars
            ]
        }
        
        logger.info(f"Successfully connected {len(calendars)} calendars for user {user_id}")
        return user_info
    
    def disconnect_user_calendar(self, user_id: str) -> bool:
        """
        Disconnect a user's calendar by removing stored credentials.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            bool: True if successfully disconnected, False if no connection existed
        """
        user_config = get_user_oauth_config(user_id)
        token_file = user_config["token_file"]
        
        if token_file.exists():
            try:
                token_file.unlink()
                logger.info(f"Disconnected calendar for user {user_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to disconnect calendar for user {user_id}: {e}")
                raise
        else:
            logger.info(f"No calendar connection found for user {user_id}")
            return False
    
    async def get_eva_gmail_service(self):
        """Get authenticated Gmail service for Eva's account."""
        creds = self.get_eva_credentials()
        return await asyncio.to_thread(build, 'gmail', 'v1', credentials=creds)
    
    async def get_eva_calendar_service(self):
        """Get authenticated Calendar service for Eva's account."""
        creds = self.get_eva_credentials()
        return await asyncio.to_thread(build, 'calendar', 'v3', credentials=creds)
    
    async def get_user_calendar_service(self, user_id: str):
        """Get authenticated Calendar service for a user's account (READ-ONLY)."""
        creds = self.get_user_credentials(user_id)
        return await asyncio.to_thread(build, 'calendar', 'v3', credentials=creds)
    
    async def test_eva_authentication(self) -> Dict[str, Any]:
        """
        Test Eva's authentication.
        
        Returns:
            Dict containing authentication status and details
        """
        try:
            eva_service = await self.get_eva_gmail_service()
            profile = await asyncio.to_thread(eva_service.users().getProfile(userId='me').execute)
            logger.info(f"Eva Gmail authentication successful: {profile.get('emailAddress')}")
            return {
                'success': True,
                'email': profile.get('emailAddress'),
                'message': 'Eva Gmail authentication successful'
            }
        except Exception as e:
            logger.error(f"Eva Gmail authentication failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Eva Gmail authentication failed'
            }
    
    async def test_user_authentication(self, user_id: str) -> Dict[str, Any]:
        """
        Test a user's calendar authentication.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dict containing authentication status and details
        """
        try:
            user_service = await self.get_user_calendar_service(user_id)
            calendar_list = await asyncio.to_thread(user_service.calendarList().list().execute)
            calendars = calendar_list.get('items', [])
            logger.info(f"User {user_id} calendar authentication successful: {len(calendars)} calendars found")
            return {
                'success': True,
                'user_id': user_id,
                'calendar_count': len(calendars),
                'calendars': [cal.get('summary') for cal in calendars],
                'message': f'User calendar authentication successful'
            }
        except Exception as e:
            logger.error(f"User {user_id} calendar authentication failed: {e}")
            return {
                'success': False,
                'user_id': user_id,
                'error': str(e),
                'message': f'User calendar authentication failed'
            }


# Global OAuth manager instance
oauth_manager = OAuthManager() 