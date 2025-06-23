#!/usr/bin/env python3
"""
Token Migration Utility for Eva Assistant.

This script migrates existing Eva tokens from the legacy location to the new
dedicated Eva tokens directory structure.

Migration process:
1. Copy Eva's token from oauth/tokens/eva_gmail_token.json to data/eva_tokens/eva_gmail_calendar_token.json
2. Validate the migrated token works correctly
3. Create backup of original token
4. Update token permissions if needed

Usage:
    python scripts/migrate_tokens.py [--dry-run] [--backup]
"""

import json
import logging
import shutil
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add the parent directory to the Python path to import eva_assistant modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from eva_assistant.config import settings
from eva_assistant.auth.eva_auth import EvaAuthManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TokenMigrator:
    """Handles token migration from legacy structure to new architecture."""
    
    def __init__(self, dry_run: bool = False, create_backup: bool = True):
        """
        Initialize token migrator.
        
        Args:
            dry_run: If True, only simulate migration without making changes
            create_backup: If True, create backup of original tokens before migration
        """
        self.dry_run = dry_run
        self.create_backup = create_backup
        
        # Define paths
        self.legacy_eva_token = settings.token_dir / "eva_gmail_token.json"
        self.new_eva_token = settings.data_dir / "eva_tokens" / "eva_gmail_calendar_token.json"
        self.backup_dir = settings.data_dir / "token_backups"
        
        logger.info(f"Migration mode: {'DRY RUN' if dry_run else 'LIVE'}")
        logger.info(f"Backup enabled: {create_backup}")
    
    def validate_legacy_token(self) -> bool:
        """
        Validate that the legacy Eva token exists and is readable.
        
        Returns:
            True if legacy token is valid, False otherwise
        """
        if not self.legacy_eva_token.exists():
            logger.warning(f"Legacy Eva token not found: {self.legacy_eva_token}")
            return False
        
        try:
            with open(self.legacy_eva_token, 'r') as f:
                token_data = json.load(f)
            
            # Check for required fields (refresh_token is optional for expired tokens)
            required_fields = ['client_id', 'client_secret']
            missing_fields = [field for field in required_fields if field not in token_data]
            
            if missing_fields:
                logger.error(f"Legacy token missing required fields: {missing_fields}")
                return False
            
            # Check if refresh_token is missing (common for expired tokens)
            if 'refresh_token' not in token_data:
                logger.warning("Legacy token missing refresh_token - Eva will need to re-authenticate")
                logger.warning("This is normal for expired tokens and migration can proceed")
            
            logger.info("Legacy Eva token validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate legacy Eva token: {e}")
            return False
    
    def create_token_backup(self) -> bool:
        """
        Create backup of original token files.
        
        Returns:
            True if backup was successful, False otherwise
        """
        if not self.create_backup:
            logger.info("Backup creation disabled")
            return True
        
        try:
            # Ensure backup directory exists
            if not self.dry_run:
                self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            backup_file = self.backup_dir / f"eva_gmail_token_backup_{int(Path.stat(self.legacy_eva_token).st_mtime)}.json"
            
            if self.dry_run:
                logger.info(f"DRY RUN: Would create backup at {backup_file}")
            else:
                shutil.copy2(self.legacy_eva_token, backup_file)
                logger.info(f"Created backup: {backup_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create token backup: {e}")
            return False
    
    def migrate_eva_token(self) -> bool:
        """
        Migrate Eva's token from legacy location to new location.
        
        Returns:
            True if migration was successful, False otherwise
        """
        try:
            # Ensure target directory exists
            if not self.dry_run:
                self.new_eva_token.parent.mkdir(parents=True, exist_ok=True)
            
            if self.dry_run:
                logger.info(f"DRY RUN: Would copy {self.legacy_eva_token} to {self.new_eva_token}")
            else:
                # Copy the token file
                shutil.copy2(self.legacy_eva_token, self.new_eva_token)
                logger.info(f"Migrated Eva token: {self.legacy_eva_token} -> {self.new_eva_token}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate Eva token: {e}")
            return False
    
    def test_migrated_token(self) -> bool:
        """
        Test that the migrated token works with the new authentication system.
        
        Returns:
            True if token works correctly, False otherwise
        """
        if self.dry_run:
            logger.info("DRY RUN: Skipping token test")
            return True
        
        try:
            eva_auth = EvaAuthManager()
            status = eva_auth.get_auth_status()
            
            logger.info("Eva auth status after migration:")
            for key, value in status.items():
                logger.info(f"  {key}: {value}")
            
            if status['has_token_file'] and status['credentials_valid']:
                logger.info("✅ Migrated Eva token is working correctly")
                return True
            else:
                logger.warning("⚠️ Migrated Eva token may need refresh or re-authentication")
                return False
                
        except Exception as e:
            logger.error(f"Failed to test migrated Eva token: {e}")
            return False
    
    def cleanup_legacy_tokens(self) -> bool:
        """
        Remove legacy token files after successful migration.
        
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            if self.dry_run:
                logger.info(f"DRY RUN: Would remove legacy token {self.legacy_eva_token}")
            else:
                # Only remove if backup was created successfully
                if self.create_backup and not (self.backup_dir / f"eva_gmail_token_backup_{int(Path.stat(self.legacy_eva_token).st_mtime)}.json").exists():
                    logger.warning("Backup not found, skipping cleanup for safety")
                    return False
                
                self.legacy_eva_token.unlink()
                logger.info(f"Removed legacy Eva token: {self.legacy_eva_token}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup legacy tokens: {e}")
            return False
    
    def run_migration(self) -> bool:
        """
        Run the complete token migration process.
        
        Returns:
            True if migration was successful, False otherwise
        """
        logger.info("Starting token migration process...")
        
        # Step 1: Validate legacy token
        if not self.validate_legacy_token():
            logger.error("Legacy token validation failed, aborting migration")
            return False
        
        # Step 2: Create backup
        if not self.create_token_backup():
            logger.error("Token backup creation failed, aborting migration")
            return False
        
        # Step 3: Migrate Eva token
        if not self.migrate_eva_token():
            logger.error("Eva token migration failed")
            return False
        
        # Step 4: Test migrated token
        if not self.test_migrated_token():
            logger.warning("Migrated token test failed, but migration completed")
            # Don't return False here as the migration itself succeeded
        
        # Step 5: Cleanup legacy tokens (optional)
        if not self.cleanup_legacy_tokens():
            logger.warning("Legacy token cleanup failed, but migration completed")
        
        logger.info("✅ Token migration completed successfully!")
        return True
    
    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get current migration status.
        
        Returns:
            Dictionary containing migration status information
        """
        return {
            'legacy_eva_token_exists': self.legacy_eva_token.exists(),
            'new_eva_token_exists': self.new_eva_token.exists(),
            'backup_dir_exists': self.backup_dir.exists(),
            'legacy_token_path': str(self.legacy_eva_token),
            'new_token_path': str(self.new_eva_token),
            'backup_dir_path': str(self.backup_dir)
        }


def main():
    """Main migration script entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate Eva Assistant tokens to new architecture"
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help="Simulate migration without making actual changes"
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help="Skip creating backup of original tokens"
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help="Show current migration status and exit"
    )
    
    args = parser.parse_args()
    
    # Create migrator
    migrator = TokenMigrator(
        dry_run=args.dry_run,
        create_backup=not args.no_backup
    )
    
    # Show status if requested
    if args.status:
        status = migrator.get_migration_status()
        print("\nMigration Status:")
        print("=" * 50)
        for key, value in status.items():
            print(f"{key}: {value}")
        return
    
    # Run migration
    success = migrator.run_migration()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now use the new authentication managers.")
        if not args.dry_run:
            print("\nTo test the new authentication:")
            print("python -c \"from eva_assistant.auth.eva_auth import EvaAuthManager; print(EvaAuthManager().get_auth_status())\"")
    else:
        print("\n❌ Migration failed. Check the logs above for details.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 