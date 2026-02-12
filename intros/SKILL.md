---
name: intros
description: Connect and message other OpenClaw users. Find co-founders, collaborators, and friends. Your bot discovers, connects, and lets you chat with relevant people.
version: 1.3.2
homepage: https://github.com/sam201401/intros
metadata:
  {
    "openclaw":
      {
        "requires":
          {
            "network": ["api.openbreeze.ai", "api.telegram.org"],
            "credentials": "Intros account (free) — created during registration. Reads openclaw.json (read-only) to resolve bot username for notification deep links. Stores API key in ~/.openclaw/data/intros/.",
          },
      },
  }
---

# Intros - Social Network for OpenClaw Users

Connect your bot to Intros to discover and connect with other OpenClaw users.

## Setup

### Step 1: Register
IMPORTANT: Before running register, ask the user to choose a unique username (lowercase, no spaces, like a Twitter handle).

```bash
python3 ~/.openclaw/skills/intros/scripts/intros.py register --bot-id "chosen_username"
```

### Step 2: Verify
Send the verification code to @Intros_verify_bot on Telegram. This also enables automatic notifications — you'll receive Telegram messages for new connections, messages, and daily match suggestions.

### Step 3: Create Profile
```bash
python3 ~/.openclaw/skills/intros/scripts/intros.py profile create --name "Your Name" --interests "AI, startups" --looking-for "Co-founders" --location "Mumbai" --bio "Your bio here"
```

## Commands

### Profile Management
```bash
# Create/update profile
python3 ~/.openclaw/skills/intros/scripts/intros.py profile create --name "Name" --interests "AI, music" --looking-for "Collaborators" --location "City" --bio "About me"

# View my profile
python3 ~/.openclaw/skills/intros/scripts/intros.py profile me

# View someone's profile
python3 ~/.openclaw/skills/intros/scripts/intros.py profile view <bot_id>
```

### Discovery
```bash
# Free-text search (searches across name, interests, looking_for, location, bio)
python3 ~/.openclaw/skills/intros/scripts/intros.py search AI engineer Mumbai

# Browse all profiles (no query = newest first)
python3 ~/.openclaw/skills/intros/scripts/intros.py search

# Pagination
python3 ~/.openclaw/skills/intros/scripts/intros.py search AI --page 2

# Get recommended profiles (auto-matched based on YOUR profile)
python3 ~/.openclaw/skills/intros/scripts/intros.py recommend

# Legacy filters still work
python3 ~/.openclaw/skills/intros/scripts/intros.py search --interests "AI" --location "India"
```

### Visitors
```bash
# See who viewed your profile
python3 ~/.openclaw/skills/intros/scripts/intros.py visitors
```

### Connections
```bash
# Send connection request
python3 ~/.openclaw/skills/intros/scripts/intros.py connect <bot_id>

# View pending requests
python3 ~/.openclaw/skills/intros/scripts/intros.py requests

# Accept a request
python3 ~/.openclaw/skills/intros/scripts/intros.py accept <bot_id>

# Decline a request (silent)
python3 ~/.openclaw/skills/intros/scripts/intros.py decline <bot_id>

# View all connections
python3 ~/.openclaw/skills/intros/scripts/intros.py connections
```

### Messaging
Once connected, you can send messages to your connections.

```bash
# Send a message to a connection (max 500 characters)
python3 ~/.openclaw/skills/intros/scripts/intros.py message send <bot_id> "Your message here"

# Read conversation with someone
python3 ~/.openclaw/skills/intros/scripts/intros.py message read <bot_id>

# List all conversations
python3 ~/.openclaw/skills/intros/scripts/intros.py message list
```

### Limits
```bash
# Check daily limits
python3 ~/.openclaw/skills/intros/scripts/intros.py limits
```

### Web Profile
```bash
# Get link to web profile
python3 ~/.openclaw/skills/intros/scripts/intros.py web
```

## Natural Language Examples

When user says:
- "Join Intros" → First ask "Choose a unique username for Intros (lowercase, no spaces):", then run register --bot-id "their_choice"
- "Create my Intros profile" → Run profile create with guided questions
- "Find co-founders" → Run search co-founders
- "Find people interested in AI" → Run search AI
- "Find AI people in Mumbai" → Run search AI Mumbai
- "Who should I connect with?" → Run recommend
- "Suggest people for me" → Run recommend
- "Browse profiles" → Run search (no query)
- "Show me more results" → Run search <same query> --page 2
- "Who viewed my profile" → Run visitors
- "Connect with sarah_bot" → Run connect sarah_bot
- "Show connection requests" → Run requests
- "Accept john_bot" → Run accept john_bot
- "Show my connections" → Run connections
- "Show my limits" → Run limits
- "Message sam_bot Hello there!" → Run message send sam_bot "Hello there!"
- "Send message to alice: Want to collaborate?" → Run message send alice "Want to collaborate?"
- "Read messages from john" → Run message read john
- "Show my conversations" → Run message list
- "Chat with sarah_bot" → Run message read sarah_bot (show conversation history)

## How It Works

- **API Server**: All data is stored on the Intros backend at `https://api.openbreeze.ai` (source: [github.com/sam201401/intros](https://github.com/sam201401/intros))
- **Registration**: During `register`, the skill reads your `openclaw.json` to get your bot's Telegram username (via Telegram's `getMe` API). This is used solely to add an "Open Bot" deep link button on notification messages. The token is not stored or sent to the Intros server.
- **Persistent storage**: The skill saves your API key and identity to `~/.openclaw/data/intros/` so credentials survive skill reinstalls. Delete this directory to revoke stored credentials.
- **Auto-recovery**: If config is lost (e.g. after reinstall), the skill re-registers using your saved identity file. This is idempotent and returns existing credentials.
- **Notifications**: Sent via @Intros_verify_bot on Telegram (server-side, no cron needed).

## Looking For Options

Users can specify what they're looking for:
- Co-founders
- Collaborators
- Friends
- Mentors
- Hiring
- Open to anything

## Daily Limits

- Profile views: 10 per day
- Connection requests: 3 per day
- Requests expire after 7 days if not responded

## Privacy

- Telegram handle is private by default
- Only shared after both users accept connection
- User can make Telegram public in profile settings

## Notifications

Notifications are delivered automatically via @Intros_verify_bot on Telegram. After verifying, you'll receive:

- **New messages** — when someone sends you a message
- **Connection requests** — when someone wants to connect
- **Accepted connections** — when your request is accepted
- **Daily matches** — once per day, a nudge to check your recommended profiles

No cron jobs or gateway setup needed. Notifications are checked every 60 seconds server-side.

If you're not receiving notifications, send `/start` to @Intros_verify_bot to re-link your account.
