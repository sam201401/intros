# Intros Skill - Development Memory

**Status: WORKING** (Tested 2026-02-09)
**Version: 1.0.6** (Messaging feature added)

## Architecture

### Server (VPS: 139.84.137.213)
- **API**: FastAPI at `http://139.84.137.213:8080`
- **Database**: SQLite at `/root/intros/intros.db`
- **Code**: `/root/intros/api/main.py` and `models.py`
- Centralized - changes apply to all users automatically

### Client Skill (GitHub: sam201401/intros)
- **Repo**: `https://github.com/sam201401/intros`
- **Install location**: `~/.openclaw/skills/intros/` (or custom STATE_DIR)
- Users update via: `curl -s https://raw.githubusercontent.com/sam201401/intros/main/skill/scripts/intros.py > ~/.openclaw/skills/intros/scripts/intros.py`

## Current Working Flow

### Registration
1. User says "Join Intros"
2. Bot asks for unique username
3. `register --bot-id <username>` creates account
4. User gets verification code
5. **NO cron created yet** (only after profile)

### Profile Setup
1. User creates profile
2. `cmd_profile_create` calls `ensure_cron_exists(silent=True)`
3. Cron job created with correct script path

### Notifications (Cron)
- Runs every minute in isolated session
- Uses `--announce` for delivery
- **Auto-fixes cron path** if script was updated (no manual intervention needed)
- Checks for:
  - New incoming connection requests → notifies user
  - Newly accepted connections → notifies sender
  - **New messages** → notifies recipient
- Uses `seen_requests.json`, `seen_accepted.json`, and `seen_messages.json` to track notified items

### Messaging (v1.0.6)
Connected users can send messages to each other:
```bash
# Send message (max 500 chars)
python3 ~/.openclaw/skills/intros/scripts/intros.py message send <bot_id> "Hello!"

# Read conversation
python3 ~/.openclaw/skills/intros/scripts/intros.py message read <bot_id>

# List all conversations
python3 ~/.openclaw/skills/intros/scripts/intros.py message list
```

### Silent Fix
- If user already registered + has profile but cron missing
- Running "Join Intros" again silently creates cron
- No extra messages shown to user

## Key Files

### Client (GitHub)
```
skill/
├── SKILL.md              # Agent instructions
└── scripts/
    └── intros.py         # CLI script
```

### Config per user
```
~/.openclaw/skills/intros/
├── config.json           # API key, bot_id
├── seen_requests.json    # Notified request IDs
├── seen_accepted.json    # Notified acceptance IDs
└── seen_messages.json    # Notified message IDs
```

## Fixes (All Complete)

### 1. Dynamic Script Path
- **Problem**: Cron hardcoded `~/.openclaw/` path
- **Fix**: Use `Path(__file__).resolve()` for actual script location
- **Commit**: `40b155f`
- **Note**: Existing crons need to be deleted and recreated to pick up new path

### 2. Cron After Profile Only
- **Problem**: Cron created at registration, failed if OpenClaw old version
- **Fix**: Create cron only after profile setup
- **Commit**: `a192485`

### 3. Silent Cron Fix
- **Problem**: If cron missing, user had to manually setup
- **Fix**: Silently ensure cron exists when user has profile
- No extra messages to user

### 4. Username Required
- **Problem**: Bot ID was "unknown_bot" if env vars not set
- **Fix**: User must choose unique username at registration
- **Commit**: `0e92f0f`

### 5. Acceptance Notifications
- **Problem**: Sender not notified when request accepted
- **Fix**: Added `/accepted-connections` API + check in cron
- **Commit**: `cd6bbbf`

### 6. Messaging Feature (v1.0.6)
- **Feature**: Connected users can send messages to each other
- **API**: `/message`, `/messages/{bot_id}`, `/conversations`, `/unread-messages`
- **Client**: `message send`, `message read`, `message list` commands
- **Limit**: 500 characters per message
- **Commit**: `300a6b3`

### 7. Auto-Fix Cron Path
- **Problem**: Cron path gets stale when script is updated
- **Fix**: `check-notifications` auto-detects and fixes wrong cron path
- **How**: Every cron run checks if path is correct, recreates if not
- **Commit**: `4aebb68`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/register` | POST | Register new user |
| `/verify-status` | GET | Check verification |
| `/profile` | POST | Create/update profile |
| `/profile` | GET | Get own profile |
| `/profile/{bot_id}` | GET | View someone's profile |
| `/search` | POST | Search profiles |
| `/connect` | POST | Send connection request |
| `/requests` | GET | Get pending requests |
| `/respond` | POST | Accept/decline request |
| `/connections` | GET | Get all connections |
| `/accepted-connections` | GET | Get accepted connections (for notifications) |
| `/check-username/{username}` | GET | Check username availability |
| `/visitors` | GET | See who viewed profile |
| `/limits` | GET | Check daily limits |
| `/message` | POST | Send message to connection |
| `/messages/{bot_id}` | GET | Get conversation with user |
| `/conversations` | GET | List all conversations |
| `/unread-messages` | GET | Get unread messages (for notifications) |

## Testing Checklist (All Passed 2026-02-09)

- [x] Fresh registration asks for username
- [x] No cron until profile created
- [x] Profile creation silently creates cron
- [x] Incoming request triggers notification
- [x] Accepted connection triggers notification to sender
- [x] "Join Intros" when already registered silently fixes missing cron
- [x] Send message to connection works
- [x] Message notification delivered via cron
- [x] Auto-fix cron path works when script updated

## Important Notes

### Cron Path Issue (Permanently Solved)
- Cron message is **baked in at creation time** into `~/.openclaw/cron/jobs.json`
- Updating script does NOT update existing crons
- **Old Fix**: Delete old cron + recreate to get new path
- **Permanent Fix**: `check-notifications` auto-detects wrong path and recreates cron silently
- Script uses `Path(__file__).resolve()` for dynamic path
- No manual intervention needed when updating script

### Clearing for Fresh Test
To reset everything for testing:
```bash
# DB
ssh root@139.84.137.213 "sqlite3 /root/intros/intros.db 'DELETE FROM connections; DELETE FROM profiles; DELETE FROM users; DELETE FROM visitors; DELETE FROM daily_limits;'"

# Config + seen files
rm -f ~/.openclaw/skills/intros/config.json ~/.openclaw/skills/intros/seen_*.json

# Session memory
rm -rf ~/.openclaw/agents/main/sessions/*.jsonl ~/.openclaw/agents/main/sessions/sessions.json

# Cron (delete by ID from `openclaw cron list`)
openclaw cron delete <cron-id>
```

### OpenClaw Version
- Requires OpenClaw 2026.2.6+ for `--announce` flag support
- VPS updated from 2026.2.2-3 to 2026.2.6-3

### Database Indexes (Added for Performance)
Indexes speed up queries by jumping directly to matching rows instead of scanning all rows.

```sql
-- Find unread messages for notifications (runs every minute per user)
idx_messages_to_unread ON messages(to_bot_id, read)

-- Find messages sent by user
idx_messages_from ON messages(from_bot_id)

-- Find pending connection requests
idx_connections_to_status ON connections(to_bot_id, status)

-- Find accepted connections for notifications
idx_connections_from_status ON connections(from_bot_id, status)

-- Profile lookups
idx_profiles_bot_id ON profiles(bot_id)
```

**Impact:**
- Without index: Scans ALL rows (slow as data grows)
- With index: Jumps to exact rows (stays fast)
- 10,000 messages: ~200ms → ~2ms

### Scalability
Current system can handle:
- 1000 registered users with ~100-200 concurrent active: ✅
- 1000 simultaneous active users: ⚠️ Needs PostgreSQL

**Scaling path when needed:**
1. Add more uvicorn workers (use multiple CPU cores)
2. Add Redis cache for frequent reads
3. Migrate SQLite → PostgreSQL
4. Load balancer + multiple API instances
