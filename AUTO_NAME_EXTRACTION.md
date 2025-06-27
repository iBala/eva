# Automatic Name Extraction During Calendar Connection

Eva Assistant now automatically extracts and populates user names during the Google Calendar connection process. This eliminates the need for separate name setup steps and provides a seamless onboarding experience.

## How It Works

### 🔄 During Calendar Connection
When users connect their Google Calendar via OAuth, the system automatically:

1. **Retrieves calendar information** - Gets the user's calendar list and primary email
2. **Attempts name extraction** using multiple strategies:
   - **Email-based extraction**: `john.doe@gmail.com` → `John Doe`
   - **Calendar name extraction**: Personal calendars named "John Smith" → `John Smith`
3. **Only populates if no existing name** - Preserves user preferences
4. **Stores extracted information** in the user profile

### 📧 Email-Based Extraction Examples
- `john.doe@gmail.com` → First: "John", Last: "Doe", Display: "John Doe"
- `sarah.smith@company.com` → First: "Sarah", Last: "Smith", Display: "Sarah Smith"  
- `mike@domain.com` → First: "Mike", Display: "Mike"

### 📅 Calendar-Based Extraction
- Looks for owned calendars with person-like names
- Extracts names from calendar summaries like "John Smith"
- Only considers calendars where user has owner access

## Benefits

✅ **Seamless Onboarding**: No separate name setup step required  
✅ **Automatic Population**: Names extracted during calendar connection  
✅ **Preserves Preferences**: Never overwrites existing user names  
✅ **Fallback Handling**: Uses user_id if extraction fails  
✅ **Manual Override**: Users can always update names via API  

## API Response

The calendar connection response now includes extracted name information:

```json
{
  "user_id": "user123",
  "email": "john.doe@gmail.com",
  "name": {
    "first_name": "John",
    "last_name": "Doe", 
    "display_name": "John Doe"
  },
  "auto_populated": true,
  "timezone": "America/New_York",
  "selected_calendars": [...],
  "connected_at": "..."
}
```

## Manual Name Management

Users can still manage names manually:

### Set Name
```bash
POST /user/name
{
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "John Doe"
}
```

### Get Name
```bash
GET /user/{user_id}/name
GET /user/{user_id}/profile
```

## Implementation Details

### Protection Logic
- ✅ **Existing names are never overwritten**
- ✅ **Only populates empty name fields**
- ✅ **Extraction errors don't fail calendar connection**
- ✅ **Comprehensive logging for debugging**

### Extraction Priority
1. **Email local part analysis** (highest priority)
2. **Calendar summary parsing** (secondary)
3. **Fallback to user_id** (if extraction fails)

### Code Location
- **Main logic**: `eva_assistant/auth/user_auth.py`
- **Method**: `_auto_populate_user_info_from_calendar()`
- **Called from**: `connect_user_calendar()`

## Testing

Run the test script to see automatic extraction in action:

```bash
python scripts/test_auto_name_extraction.py
```

This will:
- Connect a test user's calendar
- Show extracted name information
- Demonstrate the complete flow

## Migration

Existing users are unaffected:
- ✅ Current names are preserved
- ✅ No data loss or overwrites
- ✅ Backward compatibility maintained
- ✅ Optional feature enhancement

## Summary

**Before**: Users had to set names separately after connecting calendar  
**After**: Names are automatically extracted and populated during calendar connection  

This improvement streamlines the user onboarding process while maintaining full control and flexibility for manual name management. 