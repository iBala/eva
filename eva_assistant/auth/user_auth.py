"""
User Authentication Manager.

Handles user calendar authentication with read-only permissions.
Users can connect multiple calendars for availability checking.

Key features:
- Read-only calendar access
- Multiple calendar support per user
- Per-user token management
- OAuth flow for calendar connections
- Calendar selection during setup
"""

import json
import logging
import asyncio
import signal
from pathlib import Path
from typing import Optional, Dict, List, Any, Set
from concurrent.futures import TimeoutError as FuturesTimeoutError
import os
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from eva_assistant.config import settings

logger = logging.getLogger(__name__)


class UserAuthManager:
    """
    Manages user calendar authentication with read-only permissions.
    
    This class handles OAuth flows for users who want to connect their
    calendars to Eva for availability checking and scheduling.
    """
    
    def __init__(self):
        """Initialize user authentication manager."""
        # User OAuth configuration
        self.client_id = settings.google_oauth_client_id
        self.client_secret = settings.google_oauth_client_secret
        self.scopes = settings.user_calendar_scopes  # Read-only calendar access
        
        # User token storage directory
        self.token_dir = settings.user_tokens_dir
        
        # Note: Directory creation moved to async methods to avoid blocking in __init__
        
        logger.info("=== USER AUTH MANAGER INITIALIZED ===")
        logger.info("User authentication manager initialized")
        logger.info(f"Token directory: {self.token_dir}")
        logger.info(f"Token directory exists: {self.token_dir.exists()}")
        logger.info(f"OAuth client ID: {self.client_id[:20]}..." if self.client_id else "No client ID")
        logger.info(f"OAuth scopes: {self.scopes}")
        
        if self.token_dir.exists():
            existing_tokens = list(self.token_dir.glob("user_*_calendar_token.json"))
            logger.info(f"Existing token files found: {len(existing_tokens)}")
            for token_file in existing_tokens:
                logger.info(f"  - {token_file.name}")
        logger.info("=======================================")
    
    def _get_user_token_file(self, user_id: str) -> Path:
        """
        Get token file path for a specific user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Path to user's token file
        """
        return self.token_dir / f"user_{user_id}_calendar_token.json"
    
    def _get_user_calendar_selection_file(self, user_id: str) -> Path:
        """
        Get calendar selection file path for a specific user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Path to user's calendar selection file
        """
        return self.token_dir / f"user_{user_id}_calendar_selection.json"
    
    def _get_user_profile_file(self, user_id: str) -> Path:
        """
        Get user profile file path for a specific user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Path to user's profile file (includes timezone and other settings)
        """
        return self.token_dir / f"user_{user_id}_profile.json"
    
    def _load_user_credentials(self, user_id: str) -> Optional[Credentials]:
        """
        Load credentials for a specific user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Credentials if found and valid, None otherwise
        """
        token_file = self._get_user_token_file(user_id)
        
        logger.info(f"=== LOAD_USER_CREDENTIALS DEBUG for {user_id} ===")
        logger.info(f"Looking for token file: {token_file}")
        
        if not token_file.exists():
            logger.info(f"❌ Token file for user {user_id} does not exist: {token_file}")
            logger.info(f"Directory exists: {token_file.parent.exists()}")
            if token_file.parent.exists():
                logger.info(f"Files in token directory: {list(token_file.parent.glob('*'))}")
            return None
        
        logger.info(f"✅ Token file exists for user {user_id}")
        logger.info(f"File size: {token_file.stat().st_size} bytes")
        
        # Check for empty/corrupted token files and clean them up
        if token_file.stat().st_size == 0:
            logger.warning(f"⚠️ Token file for user {user_id} is empty (0 bytes). Deleting corrupted file.")
            try:
                token_file.unlink()
                logger.info(f"✅ Deleted empty token file: {token_file}")
            except Exception as delete_error:
                logger.error(f"❌ Failed to delete empty token file: {delete_error}")
            return None
        
        try:
            # Read the token file content for debugging
            with open(token_file, 'r') as f:
                token_content = f.read()
                logger.info(f"Token file content preview (first 200 chars): {token_content[:200]}...")
            
            # Additional check for very small files that might be corrupted
            if len(token_content.strip()) < 50:  # Valid tokens are much longer
                logger.warning(f"⚠️ Token file for user {user_id} appears corrupted (too small: {len(token_content)} chars). Deleting.")
                try:
                    token_file.unlink()
                    logger.info(f"✅ Deleted corrupted token file: {token_file}")
                except Exception as delete_error:
                    logger.error(f"❌ Failed to delete corrupted token file: {delete_error}")
                return None
            
            logger.info(f"Attempting to load credentials with scopes: {self.scopes}")
            creds = Credentials.from_authorized_user_file(
                str(token_file), 
                self.scopes
            )
            logger.info(f"✅ Successfully loaded credentials for user {user_id}")
            logger.info(f"Credentials details:")
            logger.info(f"  - valid: {creds.valid}")
            logger.info(f"  - expired: {creds.expired}")
            logger.info(f"  - has_token: {bool(creds.token)}")
            logger.info(f"  - has_refresh_token: {bool(creds.refresh_token)}")
            logger.info(f"  - client_id: {creds.client_id}")
            logger.info(f"  - scopes: {getattr(creds, '_scopes', 'N/A')}")
            return creds
        except Exception as e:
            logger.error(f"❌ Failed to load credentials for user {user_id}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Token file path: {token_file}")
            logger.error(f"Expected scopes: {self.scopes}")
            
            # Try to read the file to see if it's corrupted
            try:
                with open(token_file, 'r') as f:
                    content = f.read()
                    logger.error(f"Token file content (for debugging): {content}")
                    
                # If it's a JSON error, the file is likely corrupted - delete it
                if "JSONDecodeError" in str(type(e).__name__) or "Expecting value" in str(e):
                    logger.warning(f"⚠️ Token file appears corrupted (JSON error). Deleting: {token_file}")
                    try:
                        token_file.unlink()
                        logger.info(f"✅ Deleted corrupted token file: {token_file}")
                    except Exception as delete_error:
                        logger.error(f"❌ Failed to delete corrupted token file: {delete_error}")
                        
            except Exception as read_error:
                logger.error(f"Cannot even read token file: {read_error}")
            
            return None
    
    async def _save_user_credentials(self, user_id: str, creds: Credentials) -> None:
        """
        Save credentials for a specific user.
        
        Args:
            user_id: Unique identifier for the user
            creds: Google OAuth credentials to save
            
        Raises:
            Exception: If credentials cannot be saved
        """
        logger.info(f"=== SAVE_USER_CREDENTIALS DEBUG for {user_id} ===")
        
        # Ensure token directory exists (async to avoid blocking)
        logger.info(f"Ensuring token directory exists: {self.token_dir}")
        await asyncio.to_thread(self.token_dir.mkdir, parents=True, exist_ok=True)
        logger.info(f"Token directory created/exists: {self.token_dir.exists()}")
        
        token_file = self._get_user_token_file(user_id)
        logger.info(f"Saving credentials to: {token_file}")
        
        try:
            # Prepare credentials JSON
            creds_json = creds.to_json()
            logger.info(f"Credentials JSON length: {len(creds_json)} characters")
            logger.info(f"Credentials JSON preview (first 100 chars): {creds_json[:100]}...")
            
            # Save to file
            with open(token_file, 'w') as f:
                f.write(creds_json)
            
            # Verify the file was saved
            if token_file.exists():
                file_size = token_file.stat().st_size
                logger.info(f"✅ Successfully saved credentials for user {user_id}")
                logger.info(f"File size: {file_size} bytes")
                logger.info(f"File path: {token_file}")
                
                # Verify we can read it back
                with open(token_file, 'r') as f:
                    saved_content = f.read()
                    logger.info(f"Verification: Can read back {len(saved_content)} characters")
            else:
                logger.error(f"❌ File was not created: {token_file}")
                raise Exception(f"Failed to create token file: {token_file}")
                
        except Exception as e:
            logger.error(f"❌ Failed to save credentials for user {user_id}: {e}")
            logger.error(f"Token file path: {token_file}")
            logger.error(f"Token directory: {self.token_dir}")
            logger.error(f"Token directory exists: {self.token_dir.exists()}")
            logger.error(f"Token directory writable: {os.access(self.token_dir, os.W_OK)}")
            raise
    
    def get_user_selected_calendars(self, user_id: str) -> Set[str]:
        """
        Get the calendar IDs that the user has selected for Eva to use.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Set of selected calendar IDs, empty set if none selected
        """
        selection_file = self._get_user_calendar_selection_file(user_id)
        
        if not selection_file.exists():
            logger.info(f"No calendar selection file for user {user_id}")
            return set()
        
        try:
            with open(selection_file, 'r') as f:
                data = json.load(f)
                selected_calendars = set(data.get('selected_calendar_ids', []))
                logger.info(f"Loaded {len(selected_calendars)} selected calendars for user {user_id}")
                return selected_calendars
        except Exception as e:
            logger.error(f"Failed to load calendar selection for user {user_id}: {e}")
            return set()
    
    def _save_user_calendar_selection(self, user_id: str, selected_calendar_ids: List[str]) -> None:
        """
        Save the user's selected calendar IDs.
        
        Args:
            user_id: Unique identifier for the user
            selected_calendar_ids: List of calendar IDs the user wants to use
            
        Raises:
            Exception: If selection cannot be saved
        """
        selection_file = self._get_user_calendar_selection_file(user_id)
        
        try:
            selection_data = {
                'user_id': user_id,
                'selected_calendar_ids': selected_calendar_ids,
                'updated_at': str(Path().stat().st_mtime if Path().exists() else 0)
            }
            
            with open(selection_file, 'w') as f:
                json.dump(selection_data, f, indent=2)
            
            logger.info(f"Saved calendar selection for user {user_id}: {len(selected_calendar_ids)} calendars")
            
        except Exception as e:
            logger.error(f"Failed to save calendar selection for user {user_id}: {e}")
            raise
    
    def _prompt_calendar_selection(self, user_id: str, calendars: List[Dict]) -> List[str]:
        """
        Prompt user to select which calendars to use for Eva.
        
        Args:
            user_id: Unique identifier for the user
            calendars: List of available calendars
            
        Returns:
            List of selected calendar IDs
        """
        print(f"\n🗓️  Calendar Selection for {user_id}")
        print("=" * 50)
        print("Eva found the following calendars in your Google account.")
        print("Please select which calendars you want Eva to use for availability checking:\n")
        
        # Filter to only show calendars the user can meaningfully select
        selectable_calendars = []
        for i, cal in enumerate(calendars):
            access_role = cal.get('accessRole', 'unknown')
            summary = cal.get('summary', 'Unnamed Calendar')
            is_primary = cal.get('primary', False)
            
            # Only show calendars they own or have write access to
            if access_role in ['owner', 'writer']:
                selectable_calendars.append(cal)
                primary_indicator = " (Primary)" if is_primary else ""
                print(f"  {len(selectable_calendars)}. {summary}{primary_indicator}")
                print(f"     Role: {access_role}")
                print()
        
        if not selectable_calendars:
            print("❌ No selectable calendars found. Eva needs at least owner or writer access.")
            return []
        
        print("Options:")
        print("  - Enter numbers separated by commas (e.g., 1,3,5)")
        print("  - Enter 'all' to select all calendars")
        print("  - Enter 'primary' to select only your primary calendar")
        print("  - Press Enter to select primary calendar by default")
        
        while True:
            try:
                selection = input(f"\nSelect calendars for {user_id}: ").strip()
                
                if not selection:
                    # Default to primary calendar
                    primary_cal = next((cal for cal in selectable_calendars if cal.get('primary')), None)
                    if primary_cal:
                        selected_ids = [primary_cal['id']]
                        print(f"✅ Selected primary calendar: {primary_cal.get('summary')}")
                        break
                    else:
                        print("❌ No primary calendar found. Please make a selection.")
                        continue
                
                elif selection.lower() == 'all':
                    selected_ids = [cal['id'] for cal in selectable_calendars]
                    print(f"✅ Selected all {len(selected_ids)} calendars")
                    break
                
                elif selection.lower() == 'primary':
                    primary_cal = next((cal for cal in selectable_calendars if cal.get('primary')), None)
                    if primary_cal:
                        selected_ids = [primary_cal['id']]
                        print(f"✅ Selected primary calendar: {primary_cal.get('summary')}")
                        break
                    else:
                        print("❌ No primary calendar found. Please select by number.")
                        continue
                
                else:
                    # Parse comma-separated numbers
                    indices = [int(x.strip()) for x in selection.split(',')]
                    selected_ids = []
                    selected_names = []
                    
                    for idx in indices:
                        if 1 <= idx <= len(selectable_calendars):
                            cal = selectable_calendars[idx - 1]
                            selected_ids.append(cal['id'])
                            selected_names.append(cal.get('summary', 'Unnamed'))
                        else:
                            print(f"❌ Invalid selection: {idx}. Please choose numbers between 1 and {len(selectable_calendars)}")
                            selected_ids = []
                            break
                    
                    if selected_ids:
                        print(f"✅ Selected {len(selected_ids)} calendars:")
                        for name in selected_names:
                            print(f"   - {name}")
                        break
                        
            except ValueError:
                print("❌ Invalid input. Please enter numbers separated by commas, 'all', 'primary', or press Enter.")
            except KeyboardInterrupt:
                print("\n❌ Calendar selection cancelled.")
                return []
        
        return selected_ids
    
    def _is_interactive_environment(self) -> bool:
        """
        Detect if we're running in an interactive environment or production/LangGraph.
        
        Returns:
            True if interactive (standalone scripts), False if production/LangGraph
        """
        import sys
        import os
        
        # Check various indicators of non-interactive environment
        non_interactive_indicators = [
            # Standard non-interactive indicators
            not sys.stdin.isatty(),  # Not connected to a terminal
            not sys.stdout.isatty(),  # Output not going to terminal
            os.getenv('CI') is not None,  # Running in CI
            os.getenv('LANGGRAPH_DEV') is not None,  # LangGraph dev mode
            os.getenv('LANGGRAPH_API') is not None,  # LangGraph API mode
            os.getenv('DEPLOYMENT') is not None,  # Generic deployment indicator
            os.getenv('DOCKER_CONTAINER') is not None,  # Running in Docker
            os.getenv('KUBERNETES_SERVICE_HOST') is not None,  # Running in Kubernetes
            os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None,  # Running in AWS Lambda
            
            # Web server indicators
            os.getenv('UVICORN_HOST') is not None,  # Uvicorn web server
            os.getenv('GUNICORN_CMD_ARGS') is not None,  # Gunicorn web server
            
            # Python execution context indicators
            hasattr(sys, 'ps1') is False,  # Not in interactive Python
            
            # Check if asyncio event loop is running (typically means web/async context)
            self._is_async_context(),
        ]
        
        is_non_interactive = any(non_interactive_indicators)
        
        # Log the detection for debugging
        logger.info(f"Interactive environment detection:")
        logger.info(f"  - stdin.isatty(): {sys.stdin.isatty()}")
        logger.info(f"  - stdout.isatty(): {sys.stdout.isatty()}")
        logger.info(f"  - CI: {os.getenv('CI')}")
        logger.info(f"  - LANGGRAPH_DEV: {os.getenv('LANGGRAPH_DEV')}")
        logger.info(f"  - LANGGRAPH_API: {os.getenv('LANGGRAPH_API')}")
        logger.info(f"  - async_context: {self._is_async_context()}")
        logger.info(f"  - Final decision: {'NON-INTERACTIVE' if is_non_interactive else 'INTERACTIVE'}")
        
        return not is_non_interactive
    
    def _is_async_context(self) -> bool:
        """Check if we're running in an async context."""
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False
    
    async def _refresh_user_credentials(self, user_id: str, creds: Credentials) -> Credentials:
        """
        Refresh expired credentials for a user.
        
        Args:
            user_id: Unique identifier for the user
            creds: Expired credentials to refresh
            
        Returns:
            Refreshed credentials
            
        Raises:
            Exception: If credentials cannot be refreshed
        """
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                await self._save_user_credentials(user_id, creds)
                logger.info(f"Successfully refreshed credentials for user {user_id}")
                return creds
            except Exception as e:
                logger.error(f"Failed to refresh credentials for user {user_id}: {e}")
                raise
        return creds
    
    async def _run_user_oauth_flow(self, user_id: str) -> Credentials:
        """
        Run OAuth flow for a user's calendar connection with timeout protection.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            New OAuth credentials for the user
            
        Raises:
            Exception: If OAuth flow fails or times out
        """
        logger.info(f"Starting OAuth flow for user {user_id} calendar connection...")
        
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
                    authorization_prompt_message=f"Please visit this URL to connect {user_id}'s calendar: {{url}}",
                    success_message=f"Calendar connection completed for {user_id}! You can close this window.",
                    open_browser=True,
                    access_type='offline',  # Required for refresh token
                    prompt='consent'        # Force consent screen to get refresh token
                )
            except Exception as e:
                logger.error(f"OAuth flow error for user {user_id}: {e}")
                raise
        
        # Run OAuth flow with timeout protection
        try:
            timeout_minutes = settings.oauth_timeout // 60
            logger.info(f"OAuth flow will timeout after {timeout_minutes} minutes if not completed by user {user_id}")
            
            # Use asyncio.to_thread to run the complete OAuth flow (including creation)
            creds = await asyncio.wait_for(
                asyncio.to_thread(run_complete_oauth),
                timeout=float(settings.oauth_timeout)
            )
            
            # Save the credentials
            await self._save_user_credentials(user_id, creds)
            logger.info(f"OAuth flow completed successfully for user {user_id}")
            
            return creds
            
        except asyncio.TimeoutError:
            timeout_minutes = settings.oauth_timeout // 60
            logger.warning(f"OAuth flow timed out for user {user_id} ({timeout_minutes} minutes)")
            raise Exception(f"OAuth flow timed out for user {user_id}. Please try again and complete the authorization within {timeout_minutes} minutes.")
        except FuturesTimeoutError:
            logger.warning(f"OAuth flow execution timed out for user {user_id}")
            raise Exception(f"OAuth flow timed out for user {user_id}. Please try again.")
        except KeyboardInterrupt:
            logger.info(f"OAuth flow cancelled by user or system for user {user_id}")
            raise Exception(f"OAuth flow was cancelled for user {user_id}")
        except Exception as e:
            logger.error(f"OAuth flow failed for user {user_id}: {e}")
            raise Exception(f"OAuth flow failed for user {user_id}: {str(e)}")
    
    async def get_user_credentials(self, user_id: str) -> Credentials:
        """
        Get valid credentials for a user's calendar.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Valid Google OAuth credentials for user's calendar
            
        Raises:
            Exception: If credentials cannot be obtained
        """
        logger.info(f"=== GET_USER_CREDENTIALS DEBUG START for {user_id} ===")
        logger.info(f"Getting calendar credentials for user {user_id}...")
        
        # Debug: Check token directory and file paths
        token_file = self._get_user_token_file(user_id)
        logger.info(f"Token directory: {self.token_dir}")
        logger.info(f"Token file path: {token_file}")
        logger.info(f"Token file exists: {token_file.exists()}")
        
        if token_file.exists():
            logger.info(f"Token file size: {token_file.stat().st_size} bytes")
            logger.info(f"Token file modified: {token_file.stat().st_mtime}")
        
        # Try to load existing credentials
        logger.info(f"Attempting to load existing credentials for user {user_id}")
        creds = self._load_user_credentials(user_id)
        
        if creds is None:
            # No credentials found, run OAuth flow
            logger.warning(f"❌ No credentials found for user {user_id}, starting OAuth flow")
            logger.info(f"This means either:")
            logger.info(f"  1. Token file doesn't exist: {not token_file.exists()}")
            logger.info(f"  2. Token file is corrupted or unreadable")
            logger.info(f"  3. Token file has wrong format/scopes")
            creds = await self._run_user_oauth_flow(user_id)
        elif not creds.valid:
            # Credentials exist but are invalid
            logger.warning(f"⚠️ User {user_id} credentials exist but are INVALID")
            logger.info(f"Credential details:")
            logger.info(f"  - expired: {creds.expired}")
            logger.info(f"  - has_refresh_token: {bool(creds.refresh_token)}")
            logger.info(f"  - token_present: {bool(creds.token)}")
            logger.info(f"  - scopes: {getattr(creds, '_scopes', 'N/A')}")
            
            if creds.expired and creds.refresh_token:
                # Try to refresh
                logger.info(f"🔄 User {user_id} credentials expired, attempting refresh")
                try:
                    creds = await self._refresh_user_credentials(user_id, creds)
                    logger.info(f"✅ Successfully refreshed credentials for user {user_id}")
                except Exception as refresh_error:
                    logger.error(f"❌ Failed to refresh credentials for user {user_id}: {refresh_error}")
                    logger.info(f"Starting new OAuth flow due to refresh failure")
                    creds = await self._run_user_oauth_flow(user_id)
            else:
                # Cannot refresh, need new OAuth flow
                logger.warning(f"❌ User {user_id} credentials invalid and cannot refresh")
                logger.info(f"Reason: expired={creds.expired}, has_refresh_token={bool(creds.refresh_token)}")
                logger.info(f"Starting new OAuth flow")
                creds = await self._run_user_oauth_flow(user_id)
        else:
            # Credentials are valid!
            logger.info(f"✅ User {user_id} has VALID existing credentials - no OAuth needed!")
            logger.info(f"Credential details:")
            logger.info(f"  - valid: {creds.valid}")
            logger.info(f"  - expired: {creds.expired}")
            logger.info(f"  - token_present: {bool(creds.token)}")
        
        logger.info(f"=== GET_USER_CREDENTIALS DEBUG END for {user_id} ===")
        logger.info(f"User {user_id} credentials ready")
        return creds
    
    async def get_user_calendar_service(self, user_id: str):
        """
        Get Calendar service for a user's account.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Google Calendar API service object for the user
        """
        creds = await self.get_user_credentials(user_id)
        # Wrap blocking build() call in asyncio.to_thread()
        service = await asyncio.to_thread(
            build, 'calendar', 'v3', credentials=creds, cache_discovery=False
        )
        logger.info(f"User {user_id} Calendar service created")
        return service
    
    async def connect_user_calendar(self, user_id: str, auto_select_primary: bool = False) -> Dict[str, Any]:
        """
        Connect a user's calendar through OAuth flow with calendar selection.
        
        Args:
            user_id: Unique identifier for the user
            auto_select_primary: If True, automatically select primary calendar without prompting
            
        Returns:
            Dictionary containing user info and connected calendars
            
        Raises:
            Exception: If OAuth flow fails or calendar access fails
        """
        logger.info(f"Initiating calendar connection for user {user_id}")
        
        # Get credentials (this will trigger OAuth flow if needed)
        creds = await self.get_user_credentials(user_id)
        
        # Get calendar service
        # Wrap blocking build() call in asyncio.to_thread()
        service = await asyncio.to_thread(
            build, 'calendar', 'v3', credentials=creds
        )
        
        try:
            # Get user's calendar list
            # Wrap blocking API call in asyncio.to_thread()
            calendar_list = await asyncio.to_thread(
                service.calendarList().list().execute
            )
            calendars = calendar_list.get('items', [])
            
            # Get basic user info
            # Note: We only have calendar scope, so we can't get user profile
            primary_calendar = next((cal for cal in calendars if cal.get('primary')), {})
            
            # IMPORTANT: Auto-detect non-interactive environment to avoid blocking I/O
            # Check if we're running in LangGraph/production environment
            is_interactive = self._is_interactive_environment()
            
            logger.info(f"Environment detection for user {user_id}: interactive={is_interactive}, auto_select_primary={auto_select_primary}")
            
            # Handle calendar selection
            if auto_select_primary or not is_interactive:
                # Automatically select primary calendar (avoid blocking I/O in production)
                if primary_calendar:
                    selected_calendar_ids = [primary_calendar['id']]
                    logger.info(f"Auto-selected primary calendar for user {user_id}: {primary_calendar.get('summary')}")
                else:
                    # Fallback to first owned calendar
                    owned_calendars = [cal for cal in calendars if cal.get('accessRole') == 'owner']
                    if owned_calendars:
                        selected_calendar_ids = [owned_calendars[0]['id']]
                        logger.info(f"Auto-selected first owned calendar for user {user_id}: {owned_calendars[0].get('summary')}")
                    else:
                        raise Exception("No suitable calendars found for auto-selection")
            else:
                # Interactive mode: Prompt user for calendar selection (only in standalone usage)
                logger.info(f"Running in interactive mode, prompting user {user_id} for calendar selection")
                selected_calendar_ids = self._prompt_calendar_selection(user_id, calendars)
                if not selected_calendar_ids:
                    raise Exception("No calendars selected. Calendar connection cancelled.")
            
            # Save the user's calendar selection
            self._save_user_calendar_selection(user_id, selected_calendar_ids)
            
            # Filter calendars to show only selected ones in response
            selected_calendars = [
                cal for cal in calendars 
                if cal.get('id') in selected_calendar_ids
            ]
            
            user_info = {
                'user_id': user_id,
                'email': primary_calendar.get('id', 'unknown'),
                'total_calendars': len(calendars),
                'selected_calendars': [
                    {
                        'id': cal.get('id'),
                        'summary': cal.get('summary'),
                        'primary': cal.get('primary', False),
                        'access_role': cal.get('accessRole'),
                        'color_id': cal.get('colorId')
                    }
                    for cal in selected_calendars
                ],
                'selected_calendar_count': len(selected_calendars),
                'connected_at': str(Path(self._get_user_token_file(user_id)).stat().st_mtime),
                'scopes': self.scopes
            }
            
            logger.info(f"Successfully connected calendar for user {user_id} with {len(selected_calendars)} selected calendars")
            return user_info
            
        except Exception as e:
            logger.error(f"Failed to connect calendar for user {user_id}: {e}")
            raise
    
    async def update_user_calendar_selection(self, user_id: str) -> Dict[str, Any]:
        """
        Update a user's calendar selection.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dictionary containing updated calendar selection info
            
        Raises:
            Exception: If user is not connected or update fails
        """
        logger.info(f"Updating calendar selection for user {user_id}")
        
        # Check if user is connected
        if not self._get_user_token_file(user_id).exists():
            raise Exception(f"User {user_id} is not connected. Please connect calendar first.")
        
        # Get calendar service
        service = await self.get_user_calendar_service(user_id)
        
        try:
            # Get user's calendar list
            calendar_list = await asyncio.to_thread(
                service.calendarList().list().execute
            )
            calendars = calendar_list.get('items', [])
            
            # Check if we're in interactive environment
            is_interactive = self._is_interactive_environment()
            
            if is_interactive:
                # Show current selection in interactive mode only
                current_selection = self.get_user_selected_calendars(user_id)
                if current_selection:
                    print(f"\n📅 Current calendar selection for {user_id}:")
                    current_calendars = [cal for cal in calendars if cal.get('id') in current_selection]
                    for cal in current_calendars:
                        print(f"  - {cal.get('summary', 'Unnamed Calendar')}")
                    print()
                
                # Prompt for new selection
                selected_calendar_ids = self._prompt_calendar_selection(user_id, calendars)
                if not selected_calendar_ids:
                    raise Exception("No calendars selected. Update cancelled.")
            else:
                # Non-interactive mode: auto-select primary calendar (avoid blocking I/O)
                logger.info(f"Running in non-interactive mode, auto-selecting primary calendar for user {user_id}")
                primary_calendar = next((cal for cal in calendars if cal.get('primary')), None)
                
                if primary_calendar:
                    selected_calendar_ids = [primary_calendar['id']]
                    logger.info(f"Auto-selected primary calendar for user {user_id}: {primary_calendar.get('summary')}")
                else:
                    # Fallback to first owned calendar
                    owned_calendars = [cal for cal in calendars if cal.get('accessRole') == 'owner']
                    if owned_calendars:
                        selected_calendar_ids = [owned_calendars[0]['id']]
                        logger.info(f"Auto-selected first owned calendar for user {user_id}: {owned_calendars[0].get('summary')}")
                    else:
                        raise Exception("No suitable calendars found for auto-selection")
            
            # Save the updated selection
            self._save_user_calendar_selection(user_id, selected_calendar_ids)
            
            # Get updated calendar info
            selected_calendars = [
                cal for cal in calendars 
                if cal.get('id') in selected_calendar_ids
            ]
            
            result = {
                'user_id': user_id,
                'total_calendars': len(calendars),
                'selected_calendars': [
                    {
                        'id': cal.get('id'),
                        'summary': cal.get('summary'),
                        'primary': cal.get('primary', False),
                        'access_role': cal.get('accessRole')
                    }
                    for cal in selected_calendars
                ],
                'selected_calendar_count': len(selected_calendars),
                'updated_at': str(Path().stat().st_mtime if Path().exists() else 0)
            }
            
            logger.info(f"Updated calendar selection for user {user_id}: {len(selected_calendars)} calendars")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update calendar selection for user {user_id}: {e}")
            raise
    
    def get_user_calendar_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get information about a user's calendar connection and selection.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dictionary containing calendar connection info
        """
        token_file = self._get_user_token_file(user_id)
        selection_file = self._get_user_calendar_selection_file(user_id)
        
        if not token_file.exists():
            return {
                'user_id': user_id,
                'connected': False,
                'message': 'User calendar not connected'
            }
        
        selected_calendars = self.get_user_selected_calendars(user_id)
        
        return {
            'user_id': user_id,
            'connected': True,
            'has_calendar_selection': selection_file.exists(),
            'selected_calendar_count': len(selected_calendars),
            'selected_calendar_ids': list(selected_calendars),
            'token_file_exists': token_file.exists(),
            'selection_file_exists': selection_file.exists()
        }

    def disconnect_user_calendar(self, user_id: str) -> bool:
        """
        Disconnect a user's calendar by removing their token and calendar selection.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            True if disconnection was successful, False otherwise
        """
        try:
            token_file = self._get_user_token_file(user_id)
            selection_file = self._get_user_calendar_selection_file(user_id)
            
            # Load credentials to revoke them
            creds = self._load_user_credentials(user_id)
            if creds:
                try:
                    creds.revoke(Request())
                    logger.info(f"Revoked credentials for user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to revoke credentials for user {user_id}: {e}")
            
            # Remove token file
            if token_file.exists():
                token_file.unlink()
                logger.info(f"Removed token file for user {user_id}")
            
            # Remove calendar selection file
            if selection_file.exists():
                selection_file.unlink()
                logger.info(f"Removed calendar selection file for user {user_id}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect calendar for user {user_id}: {e}")
            return False
    
    def list_connected_users(self) -> List[str]:
        """
        List all users who have connected their calendars.
        
        Returns:
            List of user IDs who have valid token files
        """
        user_ids = []
        try:
            for token_file in self.token_dir.glob("user_*_calendar_token.json"):
                # Extract user_id from filename
                filename = token_file.stem  # removes .json
                parts = filename.split('_')
                if len(parts) >= 3:  # user_{user_id}_calendar
                    user_id = '_'.join(parts[1:-1])  # everything between 'user' and 'calendar'
                    user_ids.append(user_id)
            
            logger.info(f"Found {len(user_ids)} connected users")
            return user_ids
        except Exception as e:
            logger.error(f"Failed to list connected users: {e}")
            return []
    
    def get_user_auth_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get authentication status for a specific user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dictionary containing user's authentication status
        """
        token_file = self._get_user_token_file(user_id)
        creds = self._load_user_credentials(user_id)
        
        return {
            'user_id': user_id,
            'has_token_file': token_file.exists(),
            'has_valid_credentials': creds is not None and creds.valid if creds else False,
            'credentials_expired': creds is not None and creds.expired if creds else True,
            'token_file_path': str(token_file),
            'scopes': self.scopes
        }
    
    async def test_user_calendar_access(self, user_id: str) -> Dict[str, Any]:
        """
        Test calendar access for a user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dictionary containing test results
        """
        try:
            service = await self.get_user_calendar_service(user_id)
            
            # Test by getting calendar list
            # Wrap blocking API call in asyncio.to_thread()
            calendar_list = await asyncio.to_thread(
                service.calendarList().list().execute
            )
            calendars = calendar_list.get('items', [])
            
            return {
                'success': True,
                'user_id': user_id,
                'calendars_count': len(calendars),
                'calendars': [
                    {'id': cal.get('id'), 'summary': cal.get('summary')}
                    for cal in calendars[:3]  # Show first 3 calendars
                ],
                'message': f'Successfully accessed {len(calendars)} calendars for user {user_id}'
            }
        except Exception as e:
            logger.error(f"Failed to test calendar access for user {user_id}: {e}")
            return {
                'success': False,
                'user_id': user_id,
                'error': str(e),
                'message': f'Failed to access calendar for user {user_id}'
            }
    
    def get_user_timezone(self, user_id: str) -> str:
        """
        Get the user's preferred timezone.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            User's timezone string (e.g., 'America/New_York', 'UTC', etc.)
            Defaults to 'UTC' if not set
        """
        profile_file = self._get_user_profile_file(user_id)
        
        if not profile_file.exists():
            logger.info(f"No profile file for user {user_id}, defaulting to UTC timezone")
            return 'UTC'
        
        try:
            with open(profile_file, 'r') as f:
                profile_data = json.load(f)
                timezone = profile_data.get('timezone', 'UTC')
                logger.info(f"Loaded timezone for user {user_id}: {timezone}")
                return timezone
        except Exception as e:
            logger.error(f"Failed to load timezone for user {user_id}: {e}")
            return 'UTC'
    
    def set_user_timezone(self, user_id: str, timezone: str) -> bool:
        """
        Set the user's preferred timezone.
        
        Args:
            user_id: Unique identifier for the user
            timezone: Timezone string (e.g., 'America/New_York', 'Europe/London', 'UTC')
            
        Returns:
            True if timezone was saved successfully, False otherwise
        """
        # Validate timezone
        try:
            import pytz
            pytz.timezone(timezone)  # This will raise an exception if invalid
        except Exception as e:
            logger.error(f"Invalid timezone '{timezone}' for user {user_id}: {e}")
            return False
        
        profile_file = self._get_user_profile_file(user_id)
        
        # Load existing profile or create new one
        profile_data = {}
        if profile_file.exists():
            try:
                with open(profile_file, 'r') as f:
                    profile_data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load existing profile for user {user_id}: {e}")
        
        # Update timezone
        profile_data.update({
            'user_id': user_id,
            'timezone': timezone,
            'updated_at': str(datetime.utcnow().isoformat())
        })
        
        try:
            # Ensure directory exists
            profile_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(profile_file, 'w') as f:
                json.dump(profile_data, f, indent=2)
            
            logger.info(f"Set timezone for user {user_id}: {timezone}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save timezone for user {user_id}: {e}")
            return False
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get the user's complete profile including timezone and other settings.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            User profile dictionary
        """
        profile_file = self._get_user_profile_file(user_id)
        
        # Default profile with working hours
        default_profile = {
            'user_id': user_id,
            'timezone': 'UTC',
            'created_at': str(datetime.utcnow().isoformat()),
            'updated_at': str(datetime.utcnow().isoformat()),
            'working_hours': {
                'monday': {'enabled': True, 'start': '09:00', 'end': '17:00'},
                'tuesday': {'enabled': True, 'start': '09:00', 'end': '17:00'},
                'wednesday': {'enabled': True, 'start': '09:00', 'end': '17:00'},
                'thursday': {'enabled': True, 'start': '09:00', 'end': '17:00'},
                'friday': {'enabled': True, 'start': '09:00', 'end': '17:00'},
                'saturday': {'enabled': False, 'start': '09:00', 'end': '17:00'},
                'sunday': {'enabled': False, 'start': '09:00', 'end': '17:00'}
            }
        }
        
        if not profile_file.exists():
            logger.info(f"No profile file for user {user_id}, returning default profile")
            return default_profile
        
        try:
            with open(profile_file, 'r') as f:
                profile_data = json.load(f)
                # Merge with defaults to ensure all fields exist
                merged_profile = {**default_profile, **profile_data}
                
                # Ensure working hours exist and are complete
                if 'working_hours' not in merged_profile:
                    merged_profile['working_hours'] = default_profile['working_hours']
                else:
                    # Ensure all days exist
                    for day in default_profile['working_hours']:
                        if day not in merged_profile['working_hours']:
                            merged_profile['working_hours'][day] = default_profile['working_hours'][day]
                
                logger.info(f"Loaded profile for user {user_id}: timezone={merged_profile.get('timezone')}")
                return merged_profile
        except Exception as e:
            logger.error(f"Failed to load profile for user {user_id}: {e}")
            return default_profile
    
    def get_user_working_hours(self, user_id: str) -> Dict[str, Any]:
        """
        Get the user's working hours configuration.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Working hours dictionary with day-wise schedule
        """
        profile = self.get_user_profile(user_id)
        return profile.get('working_hours', {})
    
    def set_user_working_hours(self, user_id: str, working_hours: Dict[str, Any]) -> bool:
        """
        Set the user's working hours configuration.
        
        Args:
            user_id: Unique identifier for the user
            working_hours: Dictionary with day-wise schedule
                Format: {
                    'monday': {'enabled': True, 'start': '09:00', 'end': '17:00'},
                    'tuesday': {'enabled': True, 'start': '09:00', 'end': '17:00'},
                    ...
                }
            
        Returns:
            True if working hours were saved successfully, False otherwise
        """
        try:
            profile = self.get_user_profile(user_id)
            profile['working_hours'] = working_hours
            profile['updated_at'] = str(datetime.utcnow().isoformat())
            
            profile_file = self._get_user_profile_file(user_id)
            
            # Ensure directory exists
            profile_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(profile_file, 'w') as f:
                json.dump(profile, f, indent=2)
            
            logger.info(f"Updated working hours for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save working hours for user {user_id}: {e}")
            return False
    
    def get_user_availability_for_date(self, user_id: str, date_str: str) -> Dict[str, Any]:
        """
        Get user's availability for a specific date based on their working hours.
        
        Args:
            user_id: Unique identifier for the user
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Dictionary with availability info for the date
        """
        try:
            import pytz
            from datetime import datetime, timedelta
            
            # Get user profile
            profile = self.get_user_profile(user_id)
            user_timezone = profile.get('timezone', 'UTC')
            working_hours = profile.get('working_hours', {})
            
            # Parse date and get day of week
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_name = date_obj.strftime('%A').lower()
            
            # Get working hours for this day
            day_config = working_hours.get(day_name, {'enabled': False})
            
            if not day_config.get('enabled', False):
                return {
                    'date': date_str,
                    'day': day_name,
                    'available': False,
                    'reason': 'Not a working day',
                    'timezone': user_timezone
                }
            
            # Create start and end times for the day
            start_time = day_config.get('start', '09:00')
            end_time = day_config.get('end', '17:00')
            
            # Convert to full datetime strings in user timezone
            user_tz = pytz.timezone(user_timezone)
            start_datetime = user_tz.localize(
                datetime.strptime(f"{date_str} {start_time}", '%Y-%m-%d %H:%M')
            )
            end_datetime = user_tz.localize(
                datetime.strptime(f"{date_str} {end_time}", '%Y-%m-%d %H:%M')
            )
            
            return {
                'date': date_str,
                'day': day_name,
                'available': True,
                'start_time': start_datetime.isoformat(),
                'end_time': end_datetime.isoformat(),
                'start_time_local': start_time,
                'end_time_local': end_time,
                'timezone': user_timezone
            }
            
        except Exception as e:
            logger.error(f"Failed to get availability for user {user_id} on {date_str}: {e}")
            return {
                'date': date_str,
                'available': False,
                'error': str(e),
                'timezone': self.get_user_timezone(user_id)
            } 