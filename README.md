# Eva Assistant V1

An AI-powered executive assistant that automates meeting scheduling and calendar management. Eva operates as a "remote employee" with her own email and calendar, handling scheduling requests with minimal human intervention.

## 🎯 What Eva Does

- **Autonomous Scheduling**: Handles meeting requests from external parties
- **Calendar Intelligence**: Reads your calendar to find optimal meeting times
- **Professional Communication**: Responds with direct, calm, professional tone
- **Learning & Adaptation**: Learns your preferences and attendee patterns over time
- **Confirmation-Based**: Only asks for confirmation before sending final calendar invites

## 🏗️ Architecture

Eva V1 uses a flexible OAuth setup:
- **Eva's Account**: Dedicated Gmail + Calendar for sending emails and invites
- **User Calendars**: Dynamic connections via OAuth flow (READ-ONLY access)
- **LangGraph**: Deterministic AI workflow (triage → plan → act → reflect)
- **SQLite**: Preference learning and attendee context storage

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- uv (for dependency management) - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Google Cloud Project with Gmail + Calendar APIs enabled
- OpenAI API key

### 2. Installation

#### Option A: Automated Installation (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd eva

# Run the automated installer
chmod +x install.sh && ./install.sh
```

#### Option B: Manual Installation

```bash
# Clone the repository
git clone <repository-url>
cd eva

# Install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# For development (optional)
uv pip install -r requirements-dev.txt

# Copy environment template
cp env.example .env
```

### 3. Google Cloud Setup

#### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API and Calendar API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Choose "Desktop Application" type
6. Download the client configuration JSON

#### Step 2: Set Up OAuth Applications

You need **one OAuth client for Eva and one for user connections**:

**Eva's Gmail Account OAuth:**
- For Eva's test Gmail account
- Needs: Gmail + Calendar full access
- Scopes: `gmail.readonly`, `gmail.send`, `calendar`, `calendar.events`

**User Calendar Connections OAuth:**
- For connecting user calendars dynamically
- Needs: Calendar READ-ONLY access
- Scopes: `calendar.readonly`

### 4. Environment Configuration

Edit `.env` file with your credentials:

```bash
# Eva's Gmail Account (create a test Gmail account for Eva)
EVA_GMAIL_CLIENT_ID=your_eva_oauth_client_id
EVA_GMAIL_CLIENT_SECRET=your_eva_oauth_client_secret

# User Calendar Connections (for dynamic user calendar connections)
GOOGLE_OAUTH_CLIENT_ID=your_google_oauth_client_id_for_user_connections
GOOGLE_OAUTH_CLIENT_SECRET=your_google_oauth_client_secret_for_user_connections

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Security
SECRET_KEY=your_random_secret_key
```

### 5. OAuth Setup

Run the setup script to configure authentication:

```bash
# Set up Eva's OAuth and test connection
python scripts/setup_oauth.py --all

# Or set up individually:
python scripts/setup_oauth.py --eva    # Eva's Gmail OAuth only
python scripts/setup_oauth.py --test   # Test Eva's authentication
python scripts/setup_oauth.py --demo   # Show user calendar connection info
```

This will:
1. Open browser windows for OAuth flows
2. Save credentials securely in `oauth/tokens/`
3. Test both connections
4. Confirm Eva can access Gmail and your calendar

### 6. Verify Setup

```bash
# Test authentication
python scripts/setup_oauth.py --test
```

You should see:
```
✅ Eva's Gmail: Eva Gmail authentication successful
   Email: eva.test@gmail.com
🎉 Eva's authentication successful! Ready for user calendar connections.
💡 Users can now connect their calendars through the app interface.
```

## 📧 How to Use Eva

### Email Workflow

1. **Connect Calendar**: User connects their calendar through Eva's web interface
2. **Receive Meeting Request**: Someone emails the user requesting a meeting
3. **Forward to Eva**: Forward the email to Eva's Gmail account
4. **Eva Processes**: Eva analyzes the request and checks the user's calendar
5. **Eva Responds**: Eva sends professional response from her account
6. **Final Confirmation**: Eva asks user "Proposing Tuesday 2-2:30pm with John. Confirm to send invite?"
7. **Calendar Invite**: After confirmation, Eva sends calendar invite

### Example Interaction

**External Request** (forwarded to Eva):
```
From: john@company.com
To: you@domain.com
Subject: Meeting Request

Hi, can we schedule 30 minutes next week to discuss the project?
```

**Eva's Response** (from Eva's account):
```
From: eva@testaccount.com
To: john@company.com
Subject: Re: Meeting Request

Hi John,

I'm Eva, [Founder's name]'s assistant. I'd be happy to help schedule your meeting.

I have the following times available next week for a 30-minute meeting:
- Tuesday, March 12, 2:00-2:30 PM
- Wednesday, March 13, 10:00-10:30 AM
- Thursday, March 14, 3:00-3:30 PM

Please let me know which works best for you.

Best regards,
Eva
```

**Eva to You** (confirmation):
```
John Smith (company.com) requested 30 mins next week. 
Proposing Tuesday 2-2:30pm. Confirm to send invite?
```

## 🧠 How Eva Learns

Eva continuously learns from your interactions:

- **Meeting Patterns**: Preferred times, durations, buffer periods
- **Attendee Context**: Names, roles, companies, preferences  
- **Decision Patterns**: What meetings you approve/decline
- **Communication Style**: Your preferences for tone and formality

All learning happens passively - Eva never asks proactive questions.

## 🔒 Security & Privacy

- **READ-ONLY Calendar Access**: Eva can only view user calendars, not modify them
- **Per-User Security**: Each user has their own secure OAuth tokens
- **Local Data Storage**: SQLite database stored locally
- **OAuth Security**: Industry-standard Google OAuth implementation
- **User Control**: Users can connect/disconnect calendars anytime
- **Audit Logging**: All actions logged for transparency

## 📁 Project Structure

```
eva/
├── eva_assistant/           # Main package
│   ├── auth/               # OAuth and authentication
│   ├── agent/              # LangGraph AI workflow  
│   ├── tools/              # Google Calendar/Gmail tools
│   ├── memory/             # Preference and context storage
│   └── app/                # FastAPI web interface
├── scripts/                # Setup and utility scripts
├── tests/                  # Test suite
├── data/                   # SQLite database and logs
├── oauth/                  # OAuth tokens (auto-created)
├── pyproject.toml          # Project configuration
├── requirements.txt        # Main dependencies
├── requirements-dev.txt    # Development dependencies
├── install.sh              # Automated installer
└── env.example             # Environment template
```

## 🛠️ Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black eva_assistant/

# Sort imports  
isort eva_assistant/

# Type checking
mypy eva_assistant/
```

### Running the Application

```bash
# Start FastAPI development server
uvicorn eva_assistant.app.main:app --reload
```

## 🚧 Current Limitations (V1)

- Manual email forwarding to Eva
- Google Calendar/Gmail only
- Basic preference learning
- Single calendar per user connection

## 🗺️ Roadmap

### V2: Multi-Tenancy
- User-specific EA aliases (alice@domain.com, mike@domain.com) 
- Cal.com integration for virtual calendars
- Automated email routing

### V3: Advanced Features
- Email management and follow-ups
- Task management integration
- Travel planning capabilities
- Advanced preference prediction

## 🐛 Troubleshooting

### OAuth Issues
```bash
# Re-run OAuth setup
python scripts/setup_oauth.py --all

# Check token files exist
ls oauth/tokens/
```

### Permission Errors
- Ensure Gmail API and Calendar API are enabled in Google Cloud Console
- Verify OAuth scopes match the configuration
- Check that both accounts have appropriate permissions

### Environment Issues
```bash
# Verify environment variables
python scripts/setup_oauth.py --test
```

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the setup steps carefully
3. Ensure all OAuth scopes are correctly configured
4. Verify both Gmail accounts are accessible

---

**Eva V1** - The beginning of autonomous executive assistance 🤖✉️📅 