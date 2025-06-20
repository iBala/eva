#!/usr/bin/env python3
"""
OAuth Setup Script for Eva Assistant.

This script helps set up and test Google OAuth authentication for Eva's Gmail account.
User calendar connections will be handled dynamically through the app interface.

Usage:
    python scripts/setup_oauth.py --eva      # Set up Eva's Gmail OAuth
    python scripts/setup_oauth.py --test     # Test Eva's authentication
    python scripts/setup_oauth.py --all      # Set up Eva's OAuth and test
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from eva_assistant.auth.oauth_manager import oauth_manager
from eva_assistant.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_eva_oauth():
    """Set up OAuth for Eva's Gmail account."""
    logger.info("Setting up OAuth for Eva's Gmail account...")
    logger.info("This will open a browser window for authentication.")
    logger.info("Please log in with Eva's test Gmail account.")
    
    try:
        # This will trigger OAuth flow if credentials don't exist or are invalid
        creds = oauth_manager.get_eva_credentials()
        logger.info("✅ Eva's Gmail OAuth setup completed successfully!")
        
        # Test the connection
        service = oauth_manager.get_eva_gmail_service()
        profile = service.users().getProfile(userId='me').execute()
        logger.info(f"✅ Connected to Eva's Gmail: {profile.get('emailAddress')}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Eva's Gmail OAuth setup failed: {e}")
        return False


def test_eva_authentication():
    """Test Eva's authentication."""
    logger.info("Testing Eva's authentication...")
    
    result = oauth_manager.test_eva_authentication()
    
    logger.info("\n" + "="*50)
    logger.info("EVA AUTHENTICATION TEST RESULTS")
    logger.info("="*50)
    
    if result.get('success', False):
        logger.info(f"✅ Eva's Gmail: {result.get('message')}")
        logger.info(f"   Email: {result.get('email')}")
    else:
        logger.error(f"❌ Eva's Gmail: {result.get('message')}")
        logger.error(f"   Error: {result.get('error')}")
    
    logger.info("="*50)
    
    if result.get('success', False):
        logger.info("🎉 Eva's authentication successful! Ready for user calendar connections.")
        logger.info("💡 Users can now connect their calendars through the app interface.")
    else:
        logger.warning("⚠️  Eva's authentication failed. Please check the errors above.")
    
    return result.get('success', False)


def check_environment():
    """Check if environment variables are properly configured."""
    logger.info("Checking environment configuration...")
    
    required_vars = [
        'EVA_GMAIL_CLIENT_ID',
        'EVA_GMAIL_CLIENT_SECRET',
        'GOOGLE_OAUTH_CLIENT_ID',  # For user calendar connections
        'GOOGLE_OAUTH_CLIENT_SECRET',  # For user calendar connections
        'OPENAI_API_KEY',
        'SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var.lower(), None):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error("❌ Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        logger.error("\nPlease copy env.example to .env and fill in the values.")
        return False
    
    logger.info("✅ Environment configuration looks good!")
    return True


def demo_user_connection():
    """Demonstrate how user calendar connection will work."""
    logger.info("\n" + "="*60)
    logger.info("USER CALENDAR CONNECTION DEMO")
    logger.info("="*60)
    logger.info("📅 User calendar connections are now handled dynamically!")
    logger.info("")
    logger.info("How it works:")
    logger.info("1. User visits the Eva app interface")
    logger.info("2. User clicks 'Connect Calendar'")
    logger.info("3. OAuth flow opens in browser")
    logger.info("4. User grants calendar READ-ONLY permissions")
    logger.info("5. Eva can now access that user's calendar for scheduling")
    logger.info("")
    logger.info("Benefits:")
    logger.info("✅ No manual OAuth setup required for users")
    logger.info("✅ Each user has their own secure token")
    logger.info("✅ Easy to connect multiple users")
    logger.info("✅ Users can disconnect anytime")
    logger.info("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Set up OAuth authentication for Eva Assistant"
    )
    parser.add_argument(
        '--eva', 
        action='store_true', 
        help="Set up Eva's Gmail OAuth"
    )
    parser.add_argument(
        '--test', 
        action='store_true', 
        help="Test Eva's authentication"
    )
    parser.add_argument(
        '--all', 
        action='store_true', 
        help="Set up Eva's OAuth and test"
    )
    parser.add_argument(
        '--demo', 
        action='store_true', 
        help="Show user calendar connection demo"
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any([args.eva, args.test, args.all, args.demo]):
        parser.print_help()
        return
    
    # Check environment first (unless just showing demo)
    if not args.demo and not check_environment():
        sys.exit(1)
    
    success = True
    
    if args.demo:
        demo_user_connection()
        return
    
    if args.all or args.eva:
        success &= setup_eva_oauth()
    
    if args.all or args.test:
        success &= test_eva_authentication()
    
    # Always show demo info after successful setup
    if success and (args.all or args.eva):
        demo_user_connection()
    
    if success:
        logger.info("\n🎉 Setup completed successfully!")
        logger.info("Eva is ready to handle user calendar connections!")
    else:
        logger.error("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main() 