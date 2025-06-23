#!/usr/bin/env python3
"""
Test script for calendar availability checking.
This will test the fixed _find_free_slots logic.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from eva_assistant.tools.calendar import CheckAvailabilityTool, CheckAvailabilityArgs

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_availability():
    """Test calendar availability checking."""
    logger.info("=== AVAILABILITY TEST SCRIPT ===")
    
    # Test arguments (same as in your error)
    args = CheckAvailabilityArgs(
        user_id="john_doe",
        start_time="2025-06-23T09:00:00+00:00",
        end_time="2025-06-23T17:00:00+00:00",
        duration_minutes=30,
        max_suggestions=4
    )
    
    logger.info(f"Testing availability for user: {args.user_id}")
    logger.info(f"Time range: {args.start_time} to {args.end_time}")
    logger.info(f"Duration: {args.duration_minutes} minutes")
    logger.info(f"Max suggestions: {args.max_suggestions}")
    
    # Initialize availability tool
    tool = CheckAvailabilityTool()
    
    # Run the availability check
    try:
        result = await tool.run(args)
        
        logger.info("=== AVAILABILITY RESULT ===")
        logger.info(f"Success: {result.get('success')}")
        logger.info(f"Free slots count: {len(result.get('free_slots', []))}")
        logger.info(f"Busy times count: {len(result.get('busy_times', []))}")
        
        if result.get('success'):
            free_slots = result.get('free_slots', [])
            logger.info("Free slots:")
            for i, slot in enumerate(free_slots):
                logger.info(f"  {i+1}. {slot['start']} - {slot['end']} ({slot['duration_minutes']}min)")
        else:
            logger.error(f"Error: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_availability()) 