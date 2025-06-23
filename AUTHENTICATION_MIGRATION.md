# Authentication Architecture Migration

## Overview

Eva Assistant has been migrated from a single OAuth manager to a dual authentication architecture that separates Eva's account from user accounts. This provides better security, clearer separation of concerns, and improved maintainability.

## New Architecture

### 1. Eva Authentication Manager (`EvaAuthManager`)
- **Purpose**: Handles Eva's personal Gmail and Calendar accounts
- **Permissions**: Full access (read/write/send/create/delete)
- **Usage**: 
  - Sending emails on behalf of users
  - Creating calendar events in Eva's calendar
  - Managing Eva's own schedule
- **Token Storage**: `data/eva_tokens/eva_gmail_calendar_token.json`
- **Singleton**: Yes (one instance per application)

### 2. User Authentication Manager (`UserAuthManager`)
- **Purpose**: Handles user calendar connections
- **Permissions**: Read-only calendar access
- **Usage**:
  - Reading user calendar events
  - Checking user availability
  - Finding free time slots
- **Token Storage**: `data/user_tokens/user_{user_id}_calendar_token.json`
- **Multi-user**: Yes (one token per user)

## OAuth Redirect URI Configuration

### **Standardized Setup**

Both Eva and User OAuth flows now use the same redirect URI pattern:

```
Port: 8080 (configurable via oauth_port in settings)
Redirect URI: http://localhost:8080/
```

### **Google Cloud Console Configuration**

Add this single redirect URI to your OAuth client:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Credentials** → **Credentials**
3. Edit your OAuth 2.0 Client ID
4. In **"Authorized redirect URIs"**, add:
   ```
   http://localhost:8080/
   ```
5. Save changes

### **Port Conflict Handling**

If port 8080 is in use during OAuth flow:
1. **Check what's using the port:**
   ```bash
   lsof -ti:8080
   ps aux | grep <pid>
   ```

2. **Stop conflicting services temporarily:**
   ```bash
   # If it's your FastAPI app
   pkill -f uvicorn
   
   # Then run OAuth flow, restart app after
   ```

3. **Or configure a different port:**
   ```bash
   # Set in environment
   export OAUTH_PORT=8081
   
   # Update Google Console with: http://localhost:8081/
   ```

## OAuth Flow Timeout & Cancellation Handling

### **Problem Fixed**
The OAuth flow could hang indefinitely if users cancelled authentication (closed browser, clicked cancel, etc.). This was caused by Google's `run_local_server()` blocking without timeout.

### **Solution Implemented**
1. **Timeout Protection**: OAuth flows now timeout after 5 minutes (configurable)
2. **Async Execution**: OAuth runs in thread pool to prevent blocking
3. **Graceful Error Handling**: Clear error messages for timeouts and cancellations
4. **Configurable Timeout**: Set via `OAUTH_TIMEOUT` environment variable

### **Configuration**
```bash
# .env file
OAUTH_TIMEOUT=300  # 5 minutes in seconds
```

### **Behavior**
- **Timeout**: OAuth flow automatically cancels after configured time
- **Cancellation**: User closing browser triggers proper error handling
- **Logging**: Clear logs for timeout/cancellation events
- **Error Messages**: User-friendly error messages with retry instructions

### **Testing Timeout**
```bash
# Test with short timeout
OAUTH_TIMEOUT=10 python -c "
import asyncio
from eva_assistant.auth.user_auth import UserAuthManager
asyncio.run(UserAuthManager().connect_user_calendar('test_user'))
"
```

## Migration Summary

The migration completed the following changes:

### ✅ Completed Changes

1. **Created Separate Auth Managers**
   - `eva_assistant/auth/eva_auth.py` - Eva's authentication
   - `eva_assistant/auth/user_auth.py` - User calendar authentication

2. **Updated Configuration**
   - Added `eva_tokens_dir` configuration
   - Maintained backward compatibility with existing settings

3. **Updated Tools**
   - Email tools now use `EvaAuthManager`
   - Calendar tools use `EvaAuthManager` for creating events, `UserAuthManager` for reading

4. **Token Migration**
   - Migrated Eva's token from `oauth/tokens/` to `data/eva_tokens/`
   - Created backup of original token
   - Validated new token structure

5. **Documentation**
   - Updated auth module `__init__.py` with usage examples
   - Added migration utility with comprehensive logging

### 📁 Directory Structure After Migration

```
data/
├── eva_tokens/                    # Eva's personal tokens
│   └── eva_gmail_calendar_token.json
├── user_tokens/                   # User calendar tokens
│   └── user_{user_id}_calendar_token.json
└── token_backups/                 # Migration backups
    └── eva_gmail_token_backup_{timestamp}.json

eva_assistant/
└── auth/
    ├── eva_auth.py               # Eva's auth manager
    ├── user_auth.py              # User auth manager
    └── oauth_manager.py          # Legacy (deprecated)
```

## Usage Examples

### Eva Operations (Full Access)

```python
from eva_assistant.auth.eva_auth import EvaAuthManager

# Send email
eva_auth = EvaAuthManager()
gmail_service = await eva_auth.get_gmail_service()

# Create calendar event
calendar_service = await eva_auth.get_calendar_service()
```

### User Operations (Read-Only)

```python
from eva_assistant.auth.user_auth import UserAuthManager

# Read user calendar
user_auth = UserAuthManager()
calendar_service = await user_auth.get_user_calendar_service("user123")

# Connect new user
user_info = await user_auth.connect_user_calendar("user456")
```

## Security Benefits

1. **Principle of Least Privilege**: Users only grant read-only calendar access
2. **Clear Separation**: Eva's credentials are isolated from user credentials
3. **Individual Revocation**: Users can disconnect their calendars independently
4. **Audit Trail**: Separate logging for Eva vs user operations

## OAuth Flows

### Eva Setup (One-time)
1. Admin runs Eva's OAuth flow to grant full Gmail/Calendar access
2. Token stored in `data/eva_tokens/`
3. Used throughout application lifetime

### User Connection (Per-user)
1. User initiates calendar connection
2. OAuth flow requests only read-only calendar access
3. Token stored in `data/user_tokens/user_{user_id}_calendar_token.json`
4. User can revoke access anytime

## Migration Status

- ✅ Authentication managers implemented
- ✅ Tools updated to use appropriate managers
- ✅ Legacy tokens migrated
- ✅ Backward compatibility maintained
- ⚠️ Eva needs to re-authenticate (token expired)

## Next Steps

1. **Re-authenticate Eva**: Run OAuth flow for Eva's account since the migrated token needs refresh
2. **Test User Connections**: Verify user calendar OAuth flows work correctly
3. **Update Documentation**: Add API documentation for new auth managers
4. **Remove Legacy Code**: After testing, remove deprecated `OAuthManager`

## Troubleshooting

### Eva Token Issues
If Eva's authentication fails:
```bash
# Check status
python -c "from eva_assistant.auth.eva_auth import EvaAuthManager; print(EvaAuthManager().get_auth_status())"

# Re-authenticate Eva
# This will trigger OAuth flow if token is invalid
python -c "import asyncio; from eva_assistant.auth.eva_auth import EvaAuthManager; asyncio.run(EvaAuthManager().get_credentials())"
```

### User Token Issues
If user authentication fails:
```bash
# Check specific user
python -c "from eva_assistant.auth.user_auth import UserAuthManager; print(UserAuthManager().get_user_auth_status('user_id'))"

# List all connected users
python -c "from eva_assistant.auth.user_auth import UserAuthManager; print(UserAuthManager().list_connected_users())"
```

## Migration Utility

The migration script (`scripts/migrate_tokens.py`) provides:
- Dry-run mode for testing
- Automatic backups
- Token validation
- Comprehensive logging

```bash
# Check migration status
python scripts/migrate_tokens.py --status

# Run migration (with backup)
python scripts/migrate_tokens.py

# Dry run (no changes)
python scripts/migrate_tokens.py --dry-run
``` 