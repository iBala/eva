#!/usr/bin/env python3
"""
Re-authorize Eva's Gmail account with updated scopes.

This script will:
1. Revoke Eva's current credentials
2. Remove the old token file
3. Trigger a new OAuth flow with updated scopes
"""

import asyncio
import logging
from pathlib import Path

from eva_assistant.auth.eva_auth import EvaAuthManager
from eva_assistant.config import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def reauthorize_eva():
    """Re-authorize Eva's Gmail account with updated scopes."""
    logger.info("=== EVA RE-AUTHORIZATION PROCESS ===")
    
    # Initialize Eva's auth manager
    eva_auth = EvaAuthManager()
    
    # Step 1: Revoke existing credentials
    logger.info("Step 1: Revoking existing Eva credentials...")
    revoke_success = eva_auth.revoke_credentials()
    if revoke_success:
        logger.info("✅ Eva's credentials revoked successfully")
    else:
        logger.warning("⚠️  Failed to revoke credentials, but continuing...")
    
    # Step 2: Remove token file to force new OAuth flow
    token_file = settings.eva_tokens_dir / "eva_gmail_calendar_token.json"
    if token_file.exists():
        logger.info(f"Step 2: Removing old token file: {token_file}")
        token_file.unlink()
        logger.info("✅ Old token file removed")
    else:
        logger.info("Step 2: No existing token file found")
    
    # Step 3: Show current scopes that will be requested
    logger.info("Step 3: New scopes that will be requested:")
    for i, scope in enumerate(settings.eva_gmail_scopes, 1):
        logger.info(f"  {i}. {scope}")
    
    # Step 4: Trigger new OAuth flow
    logger.info("Step 4: Starting new OAuth flow...")
    logger.info("🌐 Your browser will open for Eva's Gmail authorization...")
    logger.info("📋 Please authorize ALL requested permissions for Eva's account")
    
    try:
        # This will trigger the OAuth flow since no valid credentials exist
        credentials = await eva_auth.get_credentials()
        logger.info("✅ Eva's Gmail account re-authorized successfully!")
        
        # Step 5: Verify new scopes
        logger.info("Step 5: Verifying new scopes...")
        if hasattr(credentials, 'scopes'):
            logger.info("📋 Authorized scopes:")
            for i, scope in enumerate(credentials.scopes, 1):
                logger.info(f"  {i}. {scope}")
        
        # Step 6: Test Gmail service creation
        logger.info("Step 6: Testing Gmail service...")
        gmail_service = await eva_auth.get_gmail_service()
        logger.info("✅ Gmail service created successfully")
        
        # Step 7: Test Calendar service creation  
        logger.info("Step 7: Testing Calendar service...")
        calendar_service = await eva_auth.get_calendar_service()
        logger.info("✅ Calendar service created successfully")
        
        logger.info("🎉 EVA RE-AUTHORIZATION COMPLETED SUCCESSFULLY!")
        logger.info("Eva can now:")
        logger.info("  ✅ Read emails (gmail.readonly)")
        logger.info("  ✅ Send emails (gmail.send)")
        logger.info("  ✅ Create drafts (gmail.compose)")
        logger.info("  ✅ Manage calendar (calendar)")
        logger.info("  ✅ Create events (calendar.events)")
        
    except Exception as e:
        logger.error(f"❌ Re-authorization failed: {e}")
        logger.error("Please check your network connection and try again")
        raise


if __name__ == "__main__":
    asyncio.run(reauthorize_eva()) 