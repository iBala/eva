"""
Eva Authentication Manager.

Handles Eva's Gmail and Calendar authentication with full access permissions.
This is Eva's own account that she uses to send emails and manage her calendar.

Key features:
- Full Gmail access (read, send, modify)
- Full Calendar access (read, write, create, delete)
- Singleton pattern for app-level credentials
- Automatic token refresh and persistence
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import Optional
from concurrent.futures import TimeoutError as FuturesTimeoutError

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from eva_assistant.config import settings

logger = logging.getLogger(__name__)


class EvaAuthManager:
    """
    Manages Eva's Gmail and Calendar authentication.
    
    This is a singleton class that handles Eva's personal Google account
    authentication for the entire application lifecycle.
    """
    
    _instance: Optional["EvaAuthManager"] = None
    _credentials: Optional[Credentials] = None
    
    def __new__(cls) -> "EvaAuthManager":
        """Ensure singleton pattern for Eva's authentication."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize Eva's authentication manager."""
        if self._initialized:
            return
            
        # Eva's OAuth configuration
        self.client_id = settings.eva_gmail_client_id
        self.client_secret = settings.eva_gmail_client_secret
        self.scopes = settings.eva_gmail_scopes
        
        # Eva's token storage directory and file
        self.token_dir = settings.data_dir / "eva_tokens"
        self.token_file = self.token_dir / "eva_gmail_calendar_token.json"
        
        # Note: Directory creation moved to async methods to avoid blocking in __init__
        
        logger.info("Eva authentication manager initialized")
        self._initialized = True
    
    def _load_credentials(self) -> Optional[Credentials]:
        """
        Load Eva's credentials from token file.
        
        Returns:
            Credentials if found and valid, None otherwise
        """
        if not self.token_file.exists():
            logger.info(f"Eva token file {self.token_file} does not exist")
            return None
        
        try:
            creds = Credentials.from_authorized_user_file(
                str(self.token_file), 
                self.scopes
            )
            logger.info("Successfully loaded Eva's credentials from token file")
            return creds
        except Exception as e:
            logger.error(f"Failed to load Eva's credentials: {e}")
            return None
    
    async def _save_credentials(self, creds: Credentials) -> None:
        """
        Save Eva's credentials to token file.
        
        Args:
            creds: Google OAuth credentials to save
            
        Raises:
            Exception: If credentials cannot be saved
        """
        # Ensure token directory exists (async to avoid blocking)
        await asyncio.to_thread(self.token_dir.mkdir, parents=True, exist_ok=True)
        
        try:
            with open(self.token_file, 'w') as f:
                f.write(creds.to_json())
            logger.info(f"Saved Eva's credentials to {self.token_file}")
        except Exception as e:
            logger.error(f"Failed to save Eva's credentials: {e}")
            raise
    
    async def _refresh_credentials(self, creds: Credentials) -> Credentials:
        """
        Refresh expired credentials.
        
        Args:
            creds: Expired credentials to refresh
            
        Returns:
            Refreshed credentials
            
        Raises:
            Exception: If credentials cannot be refreshed
        """
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                await self._save_credentials(creds)
                logger.info("Successfully refreshed Eva's credentials")
                return creds
            except Exception as e:
                logger.error(f"Failed to refresh Eva's credentials: {e}")
                raise
        return creds
    
    async def _run_oauth_flow(self) -> Credentials:
        """
        Run OAuth flow to get new credentials for Eva with timeout protection.
        
        Returns:
            New OAuth credentials
            
        Raises:
            Exception: If OAuth flow fails or times out
        """
        logger.info("Starting OAuth flow for Eva's account...")
        
        # Create client config for installed app flow
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        
        # Define the complete OAuth flow function to run in thread (including flow creation)
        def run_complete_oauth():
            try:
                # Create OAuth flow inside the thread to avoid blocking calls
                flow = InstalledAppFlow.from_client_config(
                    client_config, 
                    self.scopes
                )
                
                # Run the OAuth flow
                return flow.run_local_server(
                    port=settings.oauth_port,
                    authorization_prompt_message="Please visit this URL to authorize Eva's account: {url}",
                    success_message="Eva authentication completed successfully! You can close this window.",
                    open_browser=True
                )
            except Exception as e:
                logger.error(f"Eva OAuth flow error: {e}")
                raise
        
        # Run OAuth flow with timeout protection
        try:
            timeout_minutes = settings.oauth_timeout // 60
            logger.info(f"Eva OAuth flow will timeout after {timeout_minutes} minutes if not completed")
            
            # Use asyncio.to_thread to run the complete OAuth flow (including creation)
            creds = await asyncio.wait_for(
                asyncio.to_thread(run_complete_oauth),
                timeout=float(settings.oauth_timeout)
            )
            
            # Save the credentials
            await self._save_credentials(creds)
            logger.info("Eva's OAuth flow completed successfully")
            
            return creds
            
        except asyncio.TimeoutError:
            timeout_minutes = settings.oauth_timeout // 60
            logger.warning(f"Eva OAuth flow timed out ({timeout_minutes} minutes)")
            raise Exception(f"Eva OAuth flow timed out. Please try again and complete the authorization within {timeout_minutes} minutes.")
        except FuturesTimeoutError:
            logger.warning("Eva OAuth flow execution timed out")
            raise Exception("Eva OAuth flow timed out. Please try again.")
        except KeyboardInterrupt:
            logger.info("Eva OAuth flow cancelled by user or system")
            raise Exception("Eva OAuth flow was cancelled")
        except Exception as e:
            logger.error(f"Eva OAuth flow failed: {e}")
            raise Exception(f"Eva OAuth flow failed: {str(e)}")
    
    async def get_credentials(self) -> Credentials:
        """
        Get valid credentials for Eva's Google account.
        
        This method ensures Eva always has valid credentials for Gmail and Calendar.
        It handles token loading, refresh, and OAuth flow as needed.
        
        Returns:
            Valid Google OAuth credentials for Eva's account
            
        Raises:
            Exception: If credentials cannot be obtained
        """
        logger.info("Getting Eva's Google credentials...")
        
        # Use cached credentials if available and valid
        if self._credentials and self._credentials.valid:
            logger.info("Using cached Eva credentials")
            return self._credentials
        
        # Try to load credentials from file
        creds = self._load_credentials()
        
        if creds is None:
            # No credentials found, run OAuth flow
            logger.info("No Eva credentials found, starting OAuth flow")
            creds = await self._run_oauth_flow()
        elif not creds.valid:
            # Credentials exist but are invalid
            if creds.expired and creds.refresh_token:
                # Try to refresh
                logger.info("Eva credentials expired, attempting refresh")
                creds = await self._refresh_credentials(creds)
            else:
                # Cannot refresh, need new OAuth flow
                logger.info("Eva credentials invalid and cannot refresh, starting OAuth flow")
                creds = await self._run_oauth_flow()
        
        # Cache the valid credentials
        self._credentials = creds
        logger.info("Eva credentials ready")
        return creds
    
    async def get_gmail_service(self):
        """
        Get Gmail service for Eva's account.
        
        Returns:
            Google Gmail API service object
        """
        creds = await self.get_credentials()
        # Wrap blocking build() call in asyncio.to_thread()
        service = await asyncio.to_thread(
            build, 'gmail', 'v1', credentials=creds, cache_discovery=False
        )
        logger.info("Eva Gmail service created")
        return service
    
    async def get_calendar_service(self):
        """
        Get Calendar service for Eva's account.
        
        Returns:
            Google Calendar API service object
        """
        creds = await self.get_credentials()
        # Wrap blocking build() call in asyncio.to_thread()
        service = await asyncio.to_thread(
            build, 'calendar', 'v3', credentials=creds, cache_discovery=False
        )
        logger.info("Eva Calendar service created")
        return service
    
    def revoke_credentials(self) -> bool:
        """
        Revoke Eva's credentials and remove token file.
        
        Returns:
            True if credentials were successfully revoked, False otherwise
        """
        try:
            if self._credentials:
                # Revoke the credentials
                self._credentials.revoke(Request())
                logger.info("Eva's credentials revoked successfully")
            
            # Remove token file if it exists
            if self.token_file.exists():
                self.token_file.unlink()
                logger.info("Eva's token file removed")
            
            # Clear cached credentials
            self._credentials = None
            
            return True
        except Exception as e:
            logger.error(f"Failed to revoke Eva's credentials: {e}")
            return False
    
    def get_auth_status(self) -> dict:
        """
        Get Eva's authentication status.
        
        Returns:
            Dictionary containing authentication status information
        """
        return {
            'has_token_file': self.token_file.exists(),
            'has_cached_credentials': self._credentials is not None,
            'credentials_valid': self._credentials.valid if self._credentials else False,
            'token_file_path': str(self.token_file),
            'scopes': self.scopes
        } 