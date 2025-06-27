#!/usr/bin/env python3
"""
Test Eva's draft email functionality with the new gmail.compose scope.
"""

import asyncio
import logging

from eva_assistant.tools.email import DraftEmailTool

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_eva_draft():
    """Test Eva's email draft creation."""
    logger.info("=== TESTING EVA'S DRAFT EMAIL FUNCTIONALITY ===")
    
    # Initialize the draft email tool
    draft_tool = DraftEmailTool()
    
    # Test draft creation
    test_args = draft_tool.schema(
        to=["test@example.com"],
        subject="Test Draft - Eva's New Compose Permission",
        body="This is a test draft to verify Eva's gmail.compose scope is working correctly.\n\nThis draft should be created successfully now!",
        cc=[],
        bcc=[]
    )
    
    logger.info("Testing draft creation...")
    logger.info(f"To: {test_args.to}")
    logger.info(f"Subject: {test_args.subject}")
    
    try:
        result = await draft_tool.run(test_args)
        
        if result.get('success'):
            logger.info("✅ DRAFT CREATION SUCCESS!")
            logger.info(f"Draft ID: {result.get('draft_id')}")
            logger.info(f"Message ID: {result.get('message_id')}")
            logger.info(f"Recipients: {result.get('recipients')}")
            logger.info(f"Subject: {result.get('subject')}")
            logger.info("🎉 Eva can now create email drafts successfully!")
        else:
            logger.error("❌ DRAFT CREATION FAILED!")
            logger.error(f"Error: {result.get('error')}")
            logger.error("The gmail.compose scope may not be working correctly")
            
    except Exception as e:
        logger.error(f"❌ EXCEPTION DURING DRAFT CREATION: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_eva_draft()) 