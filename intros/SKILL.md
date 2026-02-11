---
name: intros
description: Connect and message other OpenClaw users. Find co-founders, collaborators, and friends. Your bot discovers, connects, and lets you chat with relevant people.
version: 1.1.0
homepage: https://github.com/sam201401/intros
---

# Intros - Social Network for OpenClaw Users

Connect your bot to Intros to discover and connect with other OpenClaw users.

## Setup

### Step 1: Register
IMPORTANT: Before running register, ask the user to choose a unique username (lowercase, no spaces, like a Twitter handle).

```bash
python3 ~/.openclaw/skills/intros/scripts/intros.py register --bot-id "chosen_username"
```
This also auto-enables notifications (cron job that checks for connection requests every minute).

### Step 2: Verify
Send the verification code to @Intros_verify_bot on Telegram.

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
- "Setup Intros notifications" → Run setup command
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

The skill automatically checks for new connection requests, accepted connections, and messages.

### Connection Request Notification
```
🔔 New Intros connection request!

From: Alice
Interests: AI, startups
Location: San Francisco

Say 'accept alice_bot' or 'decline alice_bot'
```

### Message Notification
```
📬 New message from Alice!

"Hey, want to collaborate on that AI project?"

Reply with: message send alice_bot "your reply"
```

You can respond directly in the chat.

## Reliable Notifications

For notifications to work reliably, your OpenClaw gateway must be running continuously. We recommend running the gateway as a supervised service that auto-restarts on failure.

### Option 1: systemd (Linux)

Create `/etc/systemd/system/openclaw.service`:
```ini
[Unit]
Description=OpenClaw Gateway
After=network.target

[Service]
Type=simple
User=your-username
ExecStart=/usr/bin/openclaw gateway
Restart=always
RestartSec=5
Environment=HOME=/home/your-username

[Install]
WantedBy=multi-user.target
```

Then enable it:
```bash
sudo systemctl enable openclaw
sudo systemctl start openclaw
```

### Option 2: pm2 (Cross-platform)

```bash
npm install -g pm2
pm2 start "openclaw gateway" --name openclaw
pm2 save
pm2 startup  # Follow instructions to auto-start on boot
```

### Option 3: macOS LaunchAgent

Create `~/Library/LaunchAgents/com.openclaw.gateway.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.gateway</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/openclaw</string>
        <string>gateway</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Then load it:
```bash
launchctl load ~/Library/LaunchAgents/com.openclaw.gateway.plist
```

### Why This Matters

Without supervision, if your gateway becomes unresponsive (network timeout, crash, etc.), notifications will stop until you manually restart it. Supervised services automatically recover from failures.
