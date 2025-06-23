#!/usr/bin/env python3
"""
Debug script to test user authentication flow.
This will help identify why OAuth is triggering every time.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from eva_assistant.auth.user_auth import UserAuthManager
from eva_assistant.config import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def debug_auth():
    """Debug user authentication flow."""
    logger.info("=== AUTHENTICATION DEBUG SCRIPT ===")
    
    # Test user ID (same as in your error)
    user_id = "john_doe"
    
    logger.info(f"Testing authentication for user: {user_id}")
    logger.info(f"Current working directory: {Path.cwd()}")
    logger.info(f"Settings data_dir: {settings.data_dir}")
    logger.info(f"Settings user_tokens_dir: {settings.user_tokens_dir}")
    
    # Initialize UserAuthManager
    logger.info("Initializing UserAuthManager...")
    user_auth = UserAuthManager()
    
    # Check current status
    logger.info("Checking current authentication status...")
    auth_status = user_auth.get_user_auth_status(user_id)
    logger.info(f"Auth status: {auth_status}")
    
    # List all connected users
    connected_users = user_auth.list_connected_users()
    logger.info(f"Connected users: {connected_users}")
    
    # Try to get credentials (this will show the detailed logs)
    logger.info("Attempting to get user credentials...")
    try:
        creds = await user_auth.get_user_credentials(user_id)
        logger.info(f"✅ Successfully got credentials for {user_id}")
        logger.info(f"Credentials valid: {creds.valid}")
        logger.info(f"Credentials expired: {creds.expired}")
    except Exception as e:
        logger.error(f"❌ Failed to get credentials: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(debug_auth()) 