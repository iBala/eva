# Eva Assistant V1 - Complete Setup Guide

This guide walks you through setting up Eva Assistant from scratch, including all OAuth configurations and testing.

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] Python 3.11 or higher installed
- [ ] uv package manager installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [ ] Google account for Eva (create a test Gmail account)
- [ ] Google Cloud project for OAuth setup
- [ ] OpenAI API key
- [ ] Git installed

## 🛠️ Step-by-Step Setup

### Step 1: Project Installation

```bash
# Clone and enter project directory
git clone <your-repo-url>
cd eva

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# For development (optional)
uv pip install -r requirements-dev.txt

# Copy environment template
cp env.example .env
```

### Step 2: Google Cloud Console Setup

#### 2.1 Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name: "Eva Assistant" (or your preference)
4. Click "Create"
5. Wait for project creation, then select it

#### 2.2 Enable Required APIs

1. Navigate to "APIs & Services" → "Library"
2. Search and enable these APIs:
   - **Gmail API** (click "Enable")
   - **Google Calendar API** (click "Enable")

#### 2.3 Create OAuth Credentials

**You need TWO separate OAuth 2.0 Client IDs:**

##### OAuth Client #1: Eva's Gmail Account
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. If prompted, configure OAuth consent screen:
   - User Type: "External" (for testing)
   - App name: "Eva Assistant - Gmail"
   - User support email: Your email
   - Developer contact: Your email
   - Add scopes: `../auth/gmail.readonly`, `../auth/gmail.send`, `../auth/calendar`, `../auth/calendar.events`
   - Add test users: Include Eva's test Gmail address
4. Application type: "Desktop application"
5. Name: "Eva Gmail Client"
6. Click "Create"
7. **Download JSON file** → Rename to `eva_gmail_credentials.json`

##### OAuth Client #2: User Calendar Connections
1. Click "Create Credentials" → "OAuth 2.0 Client ID" (again)
2. Application type: "Desktop application"  
3. Name: "User Calendar Connections Client"
4. Click "Create"
5. **Download JSON file** → Rename to `user_calendar_connections_credentials.json`

### Step 3: Extract OAuth Credentials

From your downloaded JSON files, extract the client ID and secret:

**eva_gmail_credentials.json:**
```json
{
  "installed": {
    "client_id": "123456789-abcdef.apps.googleusercontent.com",
    "client_secret": "GOCSPX-your_secret_here"
  }
}
```

**user_calendar_connections_credentials.json:**
```json
{
  "installed": {
    "client_id": "987654321-ghijkl.apps.googleusercontent.com", 
    "client_secret": "GOCSPX-another_secret_here"
  }
}
```

### Step 4: Configure Environment Variables

Edit your `.env` file:

```bash
# Eva's Gmail Account OAuth
EVA_GMAIL_CLIENT_ID=123456789-abcdef.apps.googleusercontent.com
EVA_GMAIL_CLIENT_SECRET=GOCSPX-your_secret_here

# User Calendar Connections OAuth (for dynamic user connections)
GOOGLE_OAUTH_CLIENT_ID=987654321-ghijkl.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-another_secret_here

# OpenAI Configuration
OPENAI_API_KEY=sk-your_openai_api_key_here

# Application Configuration
SECRET_KEY=your_random_secret_key_minimum_32_characters_long

# Optional: Customize other settings
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=development
```

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 5: Run OAuth Setup

Now configure authentication for both accounts:

```bash
# Set up Eva's OAuth and test connection
python scripts/setup_oauth.py --all
```

**What happens during setup:**

1. **Eva's Gmail OAuth:**
   - Browser opens to Gmail login
   - **Log in with Eva's test Gmail account**
   - Grant permissions for Gmail + Calendar access
   - Credentials saved to `oauth/tokens/eva_gmail_token.json`

2. **Connection Test:**
   - Verifies Eva can access her Gmail
   - Shows success/failure for Eva's authentication

3. **User Calendar Info:**
   - Displays information about dynamic user calendar connections
   - Shows how users will connect their calendars through the app

### Step 6: Verify Setup

After OAuth setup, you should see:

```
✅ Eva's Gmail OAuth setup completed successfully!
✅ Connected to Eva's Gmail: eva.test@gmail.com

==================================================
EVA AUTHENTICATION TEST RESULTS
==================================================
✅ Eva's Gmail: Eva Gmail authentication successful
   Email: eva.test@gmail.com
==================================================
🎉 Eva's authentication successful! Ready for user calendar connections.
💡 Users can now connect their calendars through the app interface.

============================================================
USER CALENDAR CONNECTION DEMO
============================================================
📅 User calendar connections are now handled dynamically!

How it works:
1. User visits the Eva app interface
2. User clicks 'Connect Calendar'
3. OAuth flow opens in browser
4. User grants calendar READ-ONLY permissions
5. Eva can now access that user's calendar for scheduling

Benefits:
✅ No manual OAuth setup required for users
✅ Each user has their own secure token
✅ Easy to connect multiple users
✅ Users can disconnect anytime
============================================================
```

## 🔍 Testing Your Setup

### Test Individual Components

```bash
# Test only Eva's Gmail OAuth
python scripts/setup_oauth.py --eva

# Test Eva's authentication without re-running OAuth
python scripts/setup_oauth.py --test

# Show user calendar connection information
python scripts/setup_oauth.py --demo
```

## ✅ Setup Complete!

If you've successfully completed all steps and see the success messages, Eva Assistant V1 is ready for the next development phase! 🎉

The project structure and OAuth authentication are now properly configured with:

- ✅ **Dual-account OAuth setup** (Eva's Gmail + Your Calendar)
- ✅ **Environment configuration** with secure credential storage
- ✅ **Project structure** ready for LangGraph agent development
- ✅ **Authentication testing** to verify all connections work

## 📁 Current Project Structure

```
eva/
├── eva_assistant/           # Main package
│   ├── auth/               # OAuth management ✅
│   │   ├── __init__.py
│   │   └── oauth_manager.py
│   ├── config.py           # Environment configuration ✅
│   ├── app/                # FastAPI interface (ready)
│   ├── agent/              # LangGraph workflow (ready)
│   ├── tools/              # Google API tools (ready)
│   └── memory/             # Learning & storage (ready)
├── scripts/                # Setup utilities ✅
│   ├── __init__.py
│   └── setup_oauth.py
├── oauth/                  # OAuth tokens (auto-created) ✅
│   └── tokens/
│       ├── eva_gmail_token.json
│       └── user_calendar_token.json
├── pyproject.toml          # Project configuration ✅
├── requirements.txt        # Main dependencies ✅
├── requirements-dev.txt    # Development dependencies ✅
├── env.example             # Environment template ✅
├── README.md               # Main documentation ✅
└── SETUP.md                # This setup guide ✅
```

## 🚀 Next Development Steps

The foundation is complete! Next steps for Eva V1:

1. **LangGraph Agent Implementation** - Build the triage → plan → act → reflect workflow
2. **Google Calendar/Gmail Tools** - Create the tool implementations
3. **Email Processing** - Build email parsing and response generation
4. **Preference Learning** - Implement SQLite-based learning system
5. **Testing & Integration** - End-to-end testing with real email scenarios

Ready to proceed with the core agent development! 🤖📅 