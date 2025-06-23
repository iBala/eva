"""
Google Calendar tools for Eva Assistant.

Provides comprehensive calendar management capabilities:
- Get all events, specific events
- Create, update, delete events  
- Check availability and find free slots
- Handle attendees and conflicts
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator

from eva_assistant.tools.base import ToolABC
from eva_assistant.auth.eva_auth import EvaAuthManager
from eva_assistant.auth.user_auth import UserAuthManager

logger = logging.getLogger(__name__)


def normalize_datetime_for_google_api(dt_string: str) -> str:
    """
    Normalize datetime string for Google Calendar API.
    
    The Google Calendar API requires ISO 8601 format with timezone information.
    This function ensures the datetime string is properly formatted.
    
    Args:
        dt_string: Input datetime string
        
    Returns:
        Properly formatted datetime string for Google Calendar API
        
    Examples:
        "2025-01-23T09:00:00" -> "2025-01-23T09:00:00Z"
        "2025-01-23 09:00:00" -> "2025-01-23T09:00:00Z"
        "2025-01-23T09:00:00+05:30" -> "2025-01-23T09:00:00+05:30" (unchanged)
    """
    try:
        # Remove any extra whitespace
        dt_string = dt_string.strip()
        
        # Check if already has timezone info
        has_timezone = (dt_string.endswith('Z') or 
                       ('+' in dt_string and len(dt_string.split('+')[-1]) >= 2) or
                       (dt_string.count('-') >= 3))  # More than just date dashes
        
        if has_timezone:
            logger.debug(f"Datetime already has timezone: {dt_string}")
            return dt_string
            
        # Replace space with T if needed
        if ' ' in dt_string and 'T' not in dt_string:
            dt_string = dt_string.replace(' ', 'T')
            
        # Ensure T separator exists for date+time
        if 'T' not in dt_string and len(dt_string) > 10:
            # Has time but no T separator, try to add it
            if len(dt_string) >= 16:  # YYYY-MM-DD HH:MM format minimum
                dt_string = dt_string[:10] + 'T' + dt_string[11:]
        elif 'T' not in dt_string and len(dt_string) <= 10:
            # Only date provided, add default time
            dt_string += 'T00:00:00'
        
        # Add Z suffix for UTC timezone
        dt_string += 'Z'
            
        # Validate the format by parsing
        datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        
        logger.debug(f"Normalized datetime: {dt_string}")
        return dt_string
        
    except Exception as e:
        logger.error(f"Failed to normalize datetime '{dt_string}': {e}")
        # Fallback to current time with Z suffix
        fallback = datetime.utcnow().isoformat() + 'Z'
        logger.warning(f"Using fallback datetime: {fallback}")
        return fallback


def convert_datetime_to_user_timezone(dt_string: str, user_timezone: str) -> str:
    """
    Convert datetime string to user's timezone.
    
    Args:
        dt_string: ISO 8601 datetime string
        user_timezone: User's timezone (e.g., 'America/New_York')
        
    Returns:
        Datetime string converted to user's timezone
    """
    try:
        import pytz
        from dateutil.parser import parse
        
        # Parse the datetime
        dt = parse(dt_string)
        
        # If no timezone info, assume UTC
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        
        # Convert to user timezone
        user_tz = pytz.timezone(user_timezone)
        user_dt = dt.astimezone(user_tz)
        
        # Return in ISO format with timezone
        result = user_dt.isoformat()
        logger.debug(f"Converted {dt_string} to {user_timezone}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to convert datetime to user timezone: {e}")
        return dt_string  # Return original if conversion fails


def convert_datetime_from_user_timezone(dt_string: str, user_timezone: str) -> str:
    """
    Convert datetime string from user's timezone to UTC for API calls.
    
    Args:
        dt_string: Datetime string in user's timezone
        user_timezone: User's timezone (e.g., 'America/New_York')
        
    Returns:
        UTC datetime string for Google Calendar API
    """
    try:
        import pytz
        from dateutil.parser import parse
        
        # Parse the datetime
        dt = parse(dt_string)
        
        # If no timezone info, assume it's in user's timezone
        if dt.tzinfo is None:
            user_tz = pytz.timezone(user_timezone)
            dt = user_tz.localize(dt)
        
        # Convert to UTC
        utc_dt = dt.astimezone(pytz.UTC)
        
        # Return in ISO format with Z suffix
        result = utc_dt.isoformat().replace('+00:00', 'Z')
        logger.debug(f"Converted {dt_string} from {user_timezone} to UTC: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to convert datetime from user timezone: {e}")
        return normalize_datetime_for_google_api(dt_string)  # Fallback to normal normalization


# Pydantic schemas for tool arguments

class GetAllEventsArgs(BaseModel):
    """Arguments for getting all calendar events."""
    user_id: str = Field(..., description="User ID whose calendar to check")
    start_time: Optional[str] = Field(
        None, 
        description="Start time in ISO 8601 format (e.g., '2025-01-23T09:00:00Z' or '2025-01-23T09:00:00+05:30'). Defaults to now if not provided."
    )
    end_time: Optional[str] = Field(
        None, 
        description="End time in ISO 8601 format (e.g., '2025-01-23T17:00:00Z' or '2025-01-23T17:00:00+05:30'). Defaults to 1 week from now if not provided."
    )
    max_results: int = Field(50, description="Maximum number of events to return")
    
    @validator('start_time', 'end_time', pre=True)
    def normalize_datetime(cls, v):
        """Normalize datetime strings for Google Calendar API."""
        if v is not None:
            return normalize_datetime_for_google_api(v)
        return v


class GetEventArgs(BaseModel):
    """Arguments for getting a specific calendar event."""
    user_id: str = Field(..., description="User ID whose calendar to check")
    event_id: str = Field(..., description="Google Calendar event ID")


class CreateEventArgs(BaseModel):
    """Arguments for creating a calendar event in Eva's calendar."""
    user_id: str = Field(..., description="User ID who initiated the meeting (will be set as organizer)")
    title: str = Field(..., description="Meeting title")
    start: str = Field(
        ..., 
        description="Start time in ISO 8601 format (e.g., '2025-01-23T09:00:00Z' or '2025-01-23T09:00:00+05:30'). MUST include timezone information."
    )
    end: str = Field(
        ..., 
        description="End time in ISO 8601 format (e.g., '2025-01-23T17:00:00Z' or '2025-01-23T17:00:00+05:30'). MUST include timezone information."
    )
    attendees: List[str] = Field(default_factory=list, description="List of attendee email addresses")
    description: str = Field(default="", description="Meeting description")
    location: str = Field(default="", description="Meeting location or video link")
    
    @validator('start', 'end', pre=True)
    def normalize_datetime(cls, v):
        """Normalize datetime strings for Google Calendar API."""
        return normalize_datetime_for_google_api(v)


# Note: Update and Delete event tools removed to maintain user calendar read-only access
# Eva creates events in her own calendar and sends invites to users


class CheckAvailabilityArgs(BaseModel):
    """Arguments for checking calendar availability."""
    user_id: str = Field(..., description="User ID whose calendar to check")
    date: str = Field(
        ..., 
        description="Date to check availability in YYYY-MM-DD format (e.g., '2025-01-23')"
    )
    duration_minutes: int = Field(30, description="Duration of meeting in minutes")
    max_suggestions: int = Field(10, description="Maximum number of free slot suggestions")
    
    @validator('date', pre=True)
    def validate_date(cls, v):
        """Validate date format."""
        try:
            from datetime import datetime
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")


# Calendar Tools Implementation

class GetAllEventsTool(ToolABC):
    """Get all calendar events for a user within a time range."""
    
    name = "get_all_calendar_events"
    description = "Get all calendar events for a user within a specified time range. Use ISO 8601 datetime format with timezone (e.g., '2025-01-23T09:00:00Z')."
    schema = GetAllEventsArgs
    returns = lambda events: f"Found {len(events.get('events', []))} events"
    
    async def run(self, args: GetAllEventsArgs) -> Dict[str, Any]:
        """Get all calendar events for the specified user and time range."""
        # Log input parameters
        logger.info(f"=== GetAllEventsTool INPUT ===")
        logger.info(f"user_id: {args.user_id}")
        logger.info(f"start_time: {args.start_time}")
        logger.info(f"end_time: {args.end_time}")
        logger.info(f"max_results: {args.max_results}")
        
        try:
            # Use user auth manager for reading user calendars (read-only access)
            user_auth = UserAuthManager()
            
            # Get user's timezone preference
            user_timezone = user_auth.get_user_timezone(args.user_id)
            logger.info(f"User {args.user_id} timezone: {user_timezone}")
            
            service = await user_auth.get_user_calendar_service(args.user_id)
            
            # Set default time range if not provided (already normalized by validator)
            if not args.start_time:
                start_time = datetime.utcnow().isoformat() + 'Z'
            else:
                start_time = args.start_time
                
            if not args.end_time:
                end_time = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'
            else:
                end_time = args.end_time
            
            # Convert input times from user timezone to UTC if needed
            start_time_utc = start_time
            end_time_utc = end_time
            
            # Check if input times need timezone conversion (not already in UTC)
            if start_time and not (start_time.endswith('Z') or '+' in start_time or start_time.count('-') > 2):
                logger.info(f"Converting input start_time from user timezone {user_timezone} to UTC")
                start_time_utc = convert_datetime_from_user_timezone(start_time, user_timezone)
                logger.info(f"Converted start_time: {start_time} -> {start_time_utc}")
                
            if end_time and not (end_time.endswith('Z') or '+' in end_time or end_time.count('-') > 2):
                logger.info(f"Converting input end_time from user timezone {user_timezone} to UTC")
                end_time_utc = convert_datetime_from_user_timezone(end_time, user_timezone)
                logger.info(f"Converted end_time: {end_time} -> {end_time_utc}")
            
            # Get user's selected calendars
            # Wrap blocking API call in asyncio.to_thread()
            calendar_list = await asyncio.to_thread(
                service.calendarList().list().execute
            )
            all_calendars = calendar_list.get('items', [])
            
            # Get user's selected calendar IDs
            selected_calendar_ids = user_auth.get_user_selected_calendars(args.user_id)
            
            # Filter to only selected calendars (fallback to owned calendars if no selection)
            if selected_calendar_ids:
                user_calendars = [
                    cal for cal in all_calendars
                    if cal.get('id') in selected_calendar_ids
                ]
                logger.info(f"Using {len(user_calendars)} selected calendars for user {args.user_id}")
            else:
                # Fallback to owned calendars if no selection exists
                user_calendars = [
                    cal for cal in all_calendars
                    if cal.get('accessRole') == 'owner'
                ]
                logger.warning(f"No calendar selection found for user {args.user_id}, using {len(user_calendars)} owned calendars")
            
            if not user_calendars:
                logger.warning(f"No usable calendars found for user {args.user_id}")
                return {
                    'success': False,
                    'error': 'No calendars available. Please connect and select calendars first.',
                    'events': [],
                    'user_timezone': user_timezone
                }
            
            # Collect events from all calendars using UTC times
            all_events = []
            for calendar in user_calendars:
                calendar_id = calendar.get('id')
                calendar_name = calendar.get('summary', calendar_id)
                
                try:
                    # Wrap blocking API call in asyncio.to_thread()
                    events_result = await asyncio.to_thread(
                        service.events().list(
                            calendarId=calendar_id,
                            timeMin=start_time_utc,
                            timeMax=end_time_utc,
                            maxResults=args.max_results,
                            singleEvents=True,
                            orderBy='startTime'
                        ).execute
                    )
                    
                    calendar_events = events_result.get('items', [])
                    
                    # Add calendar info to each event
                    for event in calendar_events:
                        event['source_calendar'] = calendar_name
                        all_events.append(event)
                        
                except Exception as e:
                    logger.warning(f"Failed to get events from calendar '{calendar_name}' for user {args.user_id}: {e}")
                    continue
            
            # Sort events by start time and limit results
            all_events.sort(key=lambda x: x.get('start', {}).get('dateTime', x.get('start', {}).get('date', '')))
            events = all_events[:args.max_results]
            
            # Format events for easier consumption with timezone conversion
            formatted_events = []
            for event in events:
                # Get event times
                event_start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
                event_end = event.get('end', {}).get('dateTime', event.get('end', {}).get('date'))
                
                # Convert to user timezone
                event_start_user_tz = None
                event_end_user_tz = None
                
                if event_start:
                    event_start_user_tz = convert_datetime_to_user_timezone(event_start, user_timezone)
                if event_end:
                    event_end_user_tz = convert_datetime_to_user_timezone(event_end, user_timezone)
                
                formatted_event = {
                    'id': event.get('id'),
                    'title': event.get('summary', 'No Title'),
                    'start': event_start_user_tz,
                    'end': event_end_user_tz,
                    'start_utc': event_start,  # Keep UTC for reference
                    'end_utc': event_end,      # Keep UTC for reference
                    'attendees': [attendee.get('email') for attendee in event.get('attendees', [])],
                    'location': event.get('location', ''),
                    'description': event.get('description', ''),
                    'calendar': event.get('source_calendar', 'Unknown'),
                    'timezone': user_timezone
                }
                formatted_events.append(formatted_event)
            
            logger.info(f"Retrieved {len(formatted_events)} events across {len(user_calendars)} calendars for user {args.user_id}")
            
            result = {
                'success': True,
                'events': formatted_events,
                'count': len(formatted_events),
                'calendars_checked': len(user_calendars),
                'user_timezone': user_timezone,
                'time_range': {
                    'start': convert_datetime_to_user_timezone(start_time_utc, user_timezone),
                    'end': convert_datetime_to_user_timezone(end_time_utc, user_timezone),
                    'start_utc': start_time_utc,
                    'end_utc': end_time_utc,
                    'timezone': user_timezone
                }
            }
            
            # Log output
            logger.info(f"=== GetAllEventsTool OUTPUT ===")
            logger.info(f"success: {result['success']}")
            logger.info(f"count: {result['count']}")
            logger.info(f"calendars_checked: {result['calendars_checked']}")
            logger.info(f"user_timezone: {result['user_timezone']}")
            logger.info(f"time_range: {result['time_range']}")
            logger.info(f"events sample: {[e.get('title', 'No title') for e in formatted_events[:3]]}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get calendar events for user {args.user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'events': [],
                'user_timezone': user_auth.get_user_timezone(args.user_id) if 'user_auth' in locals() else 'UTC'
            }


class GetEventTool(ToolABC):
    """Get a specific calendar event by ID."""
    
    name = "get_calendar_event"
    description = "Get details of a specific calendar event by ID from user's selected calendars"
    schema = GetEventArgs
    returns = lambda event: f"Event: {event.get('title', 'Unknown')}"
    
    async def run(self, args: GetEventArgs) -> Dict[str, Any]:
        """Get specific calendar event details across all user calendars."""
        try:
            # Use user auth manager for reading user calendars (read-only access)
            user_auth = UserAuthManager()
            service = await user_auth.get_user_calendar_service(args.user_id)
            
            # Get user's selected calendars
            # Wrap blocking API call in asyncio.to_thread()
            calendar_list = await asyncio.to_thread(
                service.calendarList().list().execute
            )
            all_calendars = calendar_list.get('items', [])
            
            # Get user's selected calendar IDs
            selected_calendar_ids = user_auth.get_user_selected_calendars(args.user_id)
            
            # Filter to only selected calendars (fallback to owned calendars if no selection)
            if selected_calendar_ids:
                user_calendars = [
                    cal for cal in all_calendars
                    if cal.get('id') in selected_calendar_ids
                ]
                logger.info(f"Using {len(user_calendars)} selected calendars for user {args.user_id}")
            else:
                # Fallback to owned calendars if no selection exists
                user_calendars = [
                    cal for cal in all_calendars
                    if cal.get('accessRole') == 'owner'
                ]
                logger.warning(f"No calendar selection found for user {args.user_id}, using {len(user_calendars)} owned calendars")
            
            if not user_calendars:
                logger.warning(f"No usable calendars found for user {args.user_id}")
                return {
                    'success': False,
                    'error': 'No calendars available. Please connect and select calendars first.',
                    'event': None
                }
            
            # Search for the event across all calendars
            event = None
            source_calendar = None
            
            for calendar in user_calendars:
                calendar_id = calendar.get('id')
                calendar_name = calendar.get('summary', calendar_id)
                
                try:
                    # Try to get the event from this calendar
                    # Wrap blocking API call in asyncio.to_thread()
                    event = await asyncio.to_thread(
                        service.events().get(
                            calendarId=calendar_id,
                            eventId=args.event_id
                        ).execute
                    )
                    
                    source_calendar = calendar_name
                    break  # Found the event, stop searching
                    
                except Exception as e:
                    # Event not found in this calendar, try next one
                    logger.debug(f"Event {args.event_id} not found in calendar '{calendar_name}' for user {args.user_id}: {e}")
                    continue
            
            if not event:
                logger.warning(f"Event {args.event_id} not found in any calendar for user {args.user_id}")
                return {
                    'success': False,
                    'error': f"Event {args.event_id} not found",
                    'event': None
                }
            
            # Format event for easier consumption
            formatted_event = {
                'id': event.get('id'),
                'title': event.get('summary', 'No Title'),
                'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date')),
                'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date')),
                'attendees': [attendee.get('email') for attendee in event.get('attendees', [])],
                'location': event.get('location', ''),
                'description': event.get('description', ''),
                'status': event.get('status'),
                'created': event.get('created'),
                'updated': event.get('updated'),
                'creator': event.get('creator', {}).get('email'),
                'organizer': event.get('organizer', {}).get('email'),
                'calendar': source_calendar,
                'htmlLink': event.get('htmlLink')
            }
            
            logger.info(f"Retrieved event {args.event_id} from calendar '{source_calendar}' for user {args.user_id}")
            
            return {
                'success': True,
                'event': formatted_event
            }
            
        except Exception as e:
            logger.error(f"Failed to get event {args.event_id} for user {args.user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'event': None
            }


class CreateEventTool(ToolABC):
    """Create a new calendar event using Eva's calendar service."""
    
    name = "create_calendar_event"
    description = "Create a new calendar event with attendees and details using Eva's calendar. Requires ISO 8601 datetime format with timezone (e.g., '2025-01-23T09:00:00Z')."
    schema = CreateEventArgs
    returns = lambda result: f"Event created: {result.get('event', {}).get('htmlLink', 'No link')}"
    
    async def run(self, args: CreateEventArgs) -> Dict[str, Any]:
        """Create a calendar event in Eva's calendar with user as organizer."""
        # Log input parameters
        logger.info(f"=== CreateEventTool INPUT ===")
        logger.info(f"user_id: {args.user_id}")
        logger.info(f"title: {args.title}")
        logger.info(f"start: {args.start}")
        logger.info(f"end: {args.end}")
        logger.info(f"attendees: {args.attendees}")
        logger.info(f"description: {args.description[:100]}..." if len(args.description) > 100 else f"description: {args.description}")
        logger.info(f"location: {args.location}")
        
        try:
            # Get user's timezone preference
            user_auth = UserAuthManager()
            user_timezone = user_auth.get_user_timezone(args.user_id)
            logger.info(f"User {args.user_id} timezone: {user_timezone}")
            
            # Convert event times from user timezone to UTC if needed
            start_time_utc = args.start
            end_time_utc = args.end
            
            # Check if input times need timezone conversion (not already in UTC)
            if not (args.start.endswith('Z') or '+' in args.start or args.start.count('-') > 2):
                logger.info(f"Converting event start time from user timezone {user_timezone} to UTC")
                start_time_utc = convert_datetime_from_user_timezone(args.start, user_timezone)
                logger.info(f"Converted start: {args.start} -> {start_time_utc}")
                
            if not (args.end.endswith('Z') or '+' in args.end or args.end.count('-') > 2):
                logger.info(f"Converting event end time from user timezone {user_timezone} to UTC")
                end_time_utc = convert_datetime_from_user_timezone(args.end, user_timezone)
                logger.info(f"Converted end: {args.end} -> {end_time_utc}")
            
            # Use Eva's auth manager for creating events (full access)
            eva_auth = EvaAuthManager()
            eva_service = await eva_auth.get_calendar_service()
            
            # Get user's email to set as organizer
            user_email = await self._get_user_email(user_auth, args.user_id)
            
            # Prepare event data using UTC times
            event_body = {
                'summary': args.title,
                'description': args.description,
                'location': args.location,
                'start': {
                    'dateTime': start_time_utc,
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': end_time_utc,
                    'timeZone': 'UTC'
                },
                'attendees': [{'email': email} for email in args.attendees],
                'organizer': {
                    'email': user_email,
                    'displayName': args.user_id
                },
                'reminders': {
                    'useDefault': True
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"meet_{args.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                }
            }
            
            # Create the event in Eva's calendar
            # Wrap blocking API call in asyncio.to_thread()
            event = await asyncio.to_thread(
                eva_service.events().insert(
                    calendarId='primary',
                    body=event_body,
                    conferenceDataVersion=1,
                    sendUpdates='all'  # Send invites to attendees
                ).execute
            )
            
            # Convert event times back to user timezone for response
            created_start_user_tz = convert_datetime_to_user_timezone(event.get('start', {}).get('dateTime', start_time_utc), user_timezone)
            created_end_user_tz = convert_datetime_to_user_timezone(event.get('end', {}).get('dateTime', end_time_utc), user_timezone)
            
            # Format response with timezone information
            created_event = {
                'id': event.get('id'),
                'title': event.get('summary'),
                'start': created_start_user_tz,
                'end': created_end_user_tz,
                'start_utc': event.get('start', {}).get('dateTime', start_time_utc),
                'end_utc': event.get('end', {}).get('dateTime', end_time_utc),
                'attendees': args.attendees,
                'location': event.get('location', ''),
                'htmlLink': event.get('htmlLink'),
                'hangoutLink': event.get('hangoutLink'),
                'status': event.get('status'),
                'timezone': user_timezone
            }
            
            logger.info(f"Created event {event.get('id')} for user {args.user_id}")
            
            result = {
                'success': True,
                'event': created_event,
                'user_timezone': user_timezone,
                'message': f"Event '{args.title}' created successfully in {user_timezone} timezone"
            }
            
            # Log output
            logger.info(f"=== CreateEventTool OUTPUT ===")
            logger.info(f"success: {result['success']}")
            logger.info(f"event_id: {created_event.get('id')}")
            logger.info(f"event_title: {created_event.get('title')}")
            logger.info(f"event_start (user_tz): {created_event.get('start')}")
            logger.info(f"event_end (user_tz): {created_event.get('end')}")
            logger.info(f"event_start_utc: {created_event.get('start_utc')}")
            logger.info(f"event_end_utc: {created_event.get('end_utc')}")
            logger.info(f"user_timezone: {result['user_timezone']}")
            logger.info(f"html_link: {created_event.get('htmlLink')}")
            logger.info(f"hangout_link: {created_event.get('hangoutLink')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create event for user {args.user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'event': None,
                'user_timezone': user_auth.get_user_timezone(args.user_id) if 'user_auth' in locals() else 'UTC'
            }
    
    async def _get_user_email(self, user_auth: UserAuthManager, user_id: str) -> str:
        """Get user's email address from their calendar connection."""
        try:
            service = await user_auth.get_user_calendar_service(user_id)
            
            # Get user's calendar list to find primary calendar (which has their email)
            # Wrap blocking API call in asyncio.to_thread()
            calendar_list = await asyncio.to_thread(
                service.calendarList().list().execute
            )
            calendars = calendar_list.get('items', [])
            
            # Find primary calendar to get user's email
            primary_calendar = next((cal for cal in calendars if cal.get('primary')), None)
            if primary_calendar:
                return primary_calendar.get('id', user_id)  # Calendar ID is the email for primary
            
            # Fallback to user_id if we can't get email
            logger.warning(f"Could not determine email for user {user_id}, using user_id")
            return user_id
            
        except Exception as e:
            logger.error(f"Failed to get email for user {user_id}: {e}")
            return user_id  # Fallback to user_id


# Update and Delete event tools removed to maintain read-only access to user calendars
# Eva only creates events in her own calendar and invites users


class CheckAvailabilityTool(ToolABC):
    """Check calendar availability and suggest free time slots based on user's working hours."""
    
    name = "check_calendar_availability"
    description = "Check availability and find free time slots for a specific date based on user's working hours configuration. Uses user's predefined working hours (default: 9 AM - 5 PM, Monday-Friday)."
    schema = CheckAvailabilityArgs
    returns = lambda result: f"Found {len(result.get('free_slots', []))} free slots"
    
    async def run(self, args: CheckAvailabilityArgs) -> Dict[str, Any]:
        """Check availability using user's working hours configuration."""
        # Log input parameters
        logger.info(f"=== CheckAvailabilityTool INPUT ===")
        logger.info(f"user_id: {args.user_id}")
        logger.info(f"date: {args.date}")
        logger.info(f"duration_minutes: {args.duration_minutes}")
        logger.info(f"max_suggestions: {args.max_suggestions}")
        
        try:
            # Use user auth manager for reading user calendars (read-only access)
            logger.info(f"Initializing UserAuthManager for user {args.user_id}")
            user_auth = UserAuthManager()
            
            # Get user's availability for the specified date
            availability = user_auth.get_user_availability_for_date(args.user_id, args.date)
            user_timezone = availability.get('timezone', 'UTC')
            
            logger.info(f"User {args.user_id} timezone: {user_timezone}")
            logger.info(f"Date {args.date} availability: {availability}")
            
            # Check if user is available on this date
            if not availability.get('available', False):
                return {
                    'success': True,
                    'free_slots': [],
                    'busy_times': [],
                    'calendars_checked': 0,
                    'requested_duration': args.duration_minutes,
                    'user_timezone': user_timezone,
                    'date': args.date,
                    'working_day': False,
                    'reason': availability.get('reason', 'Not available'),
                    'message': f"User is not available on {args.date} ({availability.get('reason', 'Not available')})"
                }
            
            # Get working hours for this date
            start_time = availability['start_time']  # Full datetime in user timezone
            end_time = availability['end_time']      # Full datetime in user timezone
            
            logger.info(f"Working hours for {args.date}: {start_time} - {end_time}")
            
            # Convert to UTC for Google Calendar API calls
            import pytz
            from dateutil.parser import parse
            
            start_dt = parse(start_time)
            end_dt = parse(end_time)
            
            # Convert to UTC for API
            start_time_utc = start_dt.astimezone(pytz.UTC).isoformat().replace('+00:00', 'Z')
            end_time_utc = end_dt.astimezone(pytz.UTC).isoformat().replace('+00:00', 'Z')
            
            logger.info(f"UTC times for API: {start_time_utc} - {end_time_utc}")
            
            # Get calendar service and fetch events
            logger.info(f"Getting calendar service for user {args.user_id}")
            service = await user_auth.get_user_calendar_service(args.user_id)
            logger.info(f"Successfully obtained calendar service for user {args.user_id}")
            
            # Get user's selected calendars
            logger.info(f"Getting calendar list for user {args.user_id}")
            calendar_list = await asyncio.to_thread(
                service.calendarList().list().execute
            )
            all_calendars = calendar_list.get('items', [])
            logger.info(f"Retrieved {len(all_calendars)} total calendars for user {args.user_id}")
            
            # Get user's selected calendar IDs
            selected_calendar_ids = user_auth.get_user_selected_calendars(args.user_id)
            logger.info(f"User {args.user_id} has {len(selected_calendar_ids)} selected calendars: {list(selected_calendar_ids)}")
            
            # Filter to only selected calendars (fallback to owned calendars if no selection)
            if selected_calendar_ids:
                user_calendars = [
                    cal for cal in all_calendars
                    if cal.get('id') in selected_calendar_ids
                ]
                logger.info(f"Using {len(user_calendars)} selected calendars for user {args.user_id}")
            else:
                # Fallback to owned calendars if no selection exists
                user_calendars = [
                    cal for cal in all_calendars
                    if cal.get('accessRole') == 'owner'
                ]
                logger.warning(f"No calendar selection found for user {args.user_id}, using {len(user_calendars)} owned calendars")
            
            if not user_calendars:
                logger.error(f"No usable calendars found for user {args.user_id}")
                return {
                    'success': False,
                    'error': 'No calendars available. Please connect and select calendars first.',
                    'free_slots': [],
                    'user_timezone': user_timezone,
                    'date': args.date
                }
            
            logger.info(f"Checking availability across {len(user_calendars)} calendars for user {args.user_id}")
            
            # Collect busy times from all calendars during working hours
            all_busy_times = []
            
            for calendar in user_calendars:
                calendar_id = calendar.get('id')
                calendar_name = calendar.get('summary', calendar_id)
                
                try:
                    logger.debug(f"Fetching events from calendar '{calendar_name}' for user {args.user_id}")
                    events_result = await asyncio.to_thread(
                        service.events().list(
                            calendarId=calendar_id,
                            timeMin=start_time_utc,
                            timeMax=end_time_utc,
                            singleEvents=True,
                            orderBy='startTime'
                        ).execute
                    )
                    
                    events = events_result.get('items', [])
                    
                    # Extract busy times and keep them in user timezone
                    for event in events:
                        event_start = event.get('start', {}).get('dateTime')
                        event_end = event.get('end', {}).get('dateTime')
                        if event_start and event_end:
                            # Convert event times to user timezone
                            start_user_tz = convert_datetime_to_user_timezone(event_start, user_timezone)
                            end_user_tz = convert_datetime_to_user_timezone(event_end, user_timezone)
                            
                            all_busy_times.append({
                                'start': start_user_tz,
                                'end': end_user_tz,
                                'start_utc': event_start,
                                'end_utc': event_end,
                                'title': event.get('summary', 'Busy'),
                                'calendar': calendar_name
                            })
                            
                    logger.debug(f"Found {len(events)} events in calendar '{calendar_name}' for user {args.user_id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to check calendar '{calendar_name}' for user {args.user_id}: {e}")
                    continue
            
            # Sort all busy times by start time (in user timezone)
            busy_times = sorted(all_busy_times, key=lambda x: x['start'])
            logger.info(f"Found {len(busy_times)} total busy periods during working hours for user {args.user_id}")
            
            # Find free slots using working hours (already in user timezone)
            logger.info(f"Finding free slots for user {args.user_id} with {args.duration_minutes}min duration in {user_timezone}")
            free_slots_user_tz = self._find_free_slots(
                start_time,  # Working hours start in user timezone
                end_time,    # Working hours end in user timezone
                args.duration_minutes,
                busy_times,  # Busy times already in user timezone
                args.max_suggestions
            )
            
            # Convert free slots to include UTC times for reference
            enhanced_free_slots = []
            for slot in free_slots_user_tz:
                # Convert back to UTC for reference
                slot_start_utc = convert_datetime_from_user_timezone(slot['start'], user_timezone)
                slot_end_utc = convert_datetime_from_user_timezone(slot['end'], user_timezone)
                
                enhanced_free_slots.append({
                    'start': slot['start'],          # Already in user timezone
                    'end': slot['end'],              # Already in user timezone
                    'start_utc': slot_start_utc,     # UTC for reference
                    'end_utc': slot_end_utc,         # UTC for reference
                    'duration_minutes': slot['duration_minutes'],
                    'timezone': user_timezone
                })
            
            # Busy times are already in user timezone, just add timezone field
            enhanced_busy_times = []
            for busy in busy_times:
                enhanced_busy_times.append({
                    'start': busy['start'],          # Already in user timezone
                    'end': busy['end'],              # Already in user timezone
                    'start_utc': busy['start_utc'],  # UTC for reference
                    'end_utc': busy['end_utc'],      # UTC for reference
                    'title': busy['title'],
                    'calendar': busy['calendar'],
                    'timezone': user_timezone
                })
            
            logger.info(f"Found {len(enhanced_free_slots)} free slots across {len(user_calendars)} calendars for user {args.user_id}")
            
            result = {
                'success': True,
                'free_slots': enhanced_free_slots,
                'busy_times': enhanced_busy_times,
                'calendars_checked': len(user_calendars),
                'requested_duration': args.duration_minutes,
                'user_timezone': user_timezone,
                'date': args.date,
                'working_day': True,
                'working_hours': {
                    'start': availability['start_time_local'],  # e.g., "09:00"
                    'end': availability['end_time_local'],      # e.g., "17:00"
                    'start_full': start_time,                   # Full datetime
                    'end_full': end_time,                       # Full datetime
                    'timezone': user_timezone
                },
                'message': f"Found {len(enhanced_free_slots)} available slots on {args.date}"
            }
            
            # Log output
            logger.info(f"=== CheckAvailabilityTool OUTPUT ===")
            logger.info(f"success: {result['success']}")
            logger.info(f"date: {result['date']}")
            logger.info(f"working_day: {result['working_day']}")
            logger.info(f"working_hours: {result['working_hours']['start']} - {result['working_hours']['end']}")
            logger.info(f"free_slots_count: {len(enhanced_free_slots)}")
            logger.info(f"busy_times_count: {len(enhanced_busy_times)}")
            logger.info(f"calendars_checked: {result['calendars_checked']}")
            logger.info(f"requested_duration: {result['requested_duration']}")
            logger.info(f"user_timezone: {result['user_timezone']}")
            if enhanced_free_slots:
                logger.info(f"first_free_slot (user_tz): {enhanced_free_slots[0]['start']} - {enhanced_free_slots[0]['end']}")
                logger.info(f"first_free_slot (utc): {enhanced_free_slots[0]['start_utc']} - {enhanced_free_slots[0]['end_utc']}")
            if enhanced_busy_times:
                logger.info(f"busy_times_sample: {[bt.get('title', 'No title') for bt in enhanced_busy_times[:3]]}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check availability for user {args.user_id} on {args.date}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception details: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'free_slots': [],
                'user_timezone': user_auth.get_user_timezone(args.user_id) if 'user_auth' in locals() else 'UTC',
                'date': args.date
            }
    
    def _find_free_slots(self, start_time: str, end_time: str, duration_minutes: int, 
                        busy_times: List[Dict], max_suggestions: int) -> List[Dict]:
        """Find free time slots between busy periods."""
        try:
            from dateutil.parser import parse
            
            start_dt = parse(start_time)
            end_dt = parse(end_time)
            duration = timedelta(minutes=duration_minutes)
            
            logger.info(f"=== FIND_FREE_SLOTS DEBUG ===")
            logger.info(f"Time range: {start_dt} to {end_dt}")
            logger.info(f"Duration: {duration_minutes} minutes")
            logger.info(f"Busy periods: {len(busy_times)}")
            logger.info(f"Max suggestions: {max_suggestions}")
            
            # Sort busy times by start time
            busy_times.sort(key=lambda x: parse(x['start']))
            
            free_slots = []
            current_time = start_dt
            
            # Process each busy period and find free slots before them
            for busy in busy_times:
                busy_start = parse(busy['start'])
                logger.debug(f"Processing busy period: {busy_start} - checking for free slots before it")
                
                # Generate multiple free slots before this busy time
                while current_time + duration <= busy_start and len(free_slots) < max_suggestions:
                    slot_end = current_time + duration
                    free_slots.append({
                        'start': current_time.isoformat(),
                        'end': slot_end.isoformat(),
                        'duration_minutes': duration_minutes
                    })
                    logger.debug(f"Added free slot: {current_time.isoformat()} - {slot_end.isoformat()}")
                    
                    # Move to next potential slot
                    current_time = slot_end
                    
                    if len(free_slots) >= max_suggestions:
                        break
                
                if len(free_slots) >= max_suggestions:
                    break
                
                # Move current time to end of busy period
                busy_end = parse(busy['end'])
                current_time = max(current_time, busy_end)
                logger.debug(f"Moved current time to end of busy period: {current_time.isoformat()}")
            
            # Generate free slots after all busy times (or for the entire period if no busy times)
            logger.info(f"Generating free slots from {current_time.isoformat()} to {end_dt.isoformat()}")
            while current_time + duration <= end_dt and len(free_slots) < max_suggestions:
                slot_end = current_time + duration
                free_slots.append({
                    'start': current_time.isoformat(),
                    'end': slot_end.isoformat(),
                    'duration_minutes': duration_minutes
                })
                logger.debug(f"Added free slot: {current_time.isoformat()} - {slot_end.isoformat()}")
                
                # Move to next potential slot
                current_time = slot_end
            
            logger.info(f"=== FIND_FREE_SLOTS RESULT ===")
            logger.info(f"Generated {len(free_slots)} free slots")
            for i, slot in enumerate(free_slots):
                logger.info(f"  Slot {i+1}: {slot['start']} - {slot['end']}")
            
            return free_slots
            
        except Exception as e:
            logger.error(f"Error finding free slots: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [] 