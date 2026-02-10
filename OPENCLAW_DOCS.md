# OpenClaw Documentation Reference

## What is OpenClaw?

OpenClaw is a **self-hosted gateway** that connects messaging apps (Telegram, WhatsApp, Discord, iMessage) to AI agents. It runs on your own hardware and provides an always-available AI assistant.

---

## Skills System

### What are Skills?

Skills are modular packages that extend the agent's capabilities. They provide:
- Specialized workflows
- Tool integrations
- Domain expertise
- Bundled resources (scripts, references, assets)

### Skill Structure

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description)
│   └── Markdown instructions
└── Optional resources
    ├── scripts/      - Executable code (Python/Bash)
    ├── references/   - Documentation loaded on demand
    └── assets/       - Files used in output (templates, icons)
```

### Skill Loading Locations (Priority Order)

1. **Bundled skills** - Shipped with OpenClaw installation
2. **Managed skills** - `~/.openclaw/skills/` (shared across agents)
3. **Workspace skills** - `<workspace>/skills/` (highest priority, agent-specific)

When conflicts occur, workspace > managed > bundled.

### SKILL.md Frontmatter Fields

```yaml
---
name: skill-name              # Required
description: What it does     # Required
homepage: https://...         # Optional
user-invocable: true/false    # Expose as slash command (default: true)
disable-model-invocation: true/false  # Exclude from model prompts
command-dispatch: tool        # Direct dispatch without model interpretation
metadata: {...}               # Gating and configuration
---
```

---

## Installing Skills

### From ClawHub Registry

```bash
# Search
clawhub search "postgres backups"

# Install
clawhub install my-skill
clawhub install my-skill --version 1.2.3

# Update
clawhub update my-skill
clawhub update --all
```

### From GitHub (Natural Language)

Users can tell their OpenClaw bot:
> "Install github.com/user/repo"

The agent interprets this and:
1. Clones the repository
2. Copies the skill folder to `~/.openclaw/skills/`
3. Skill becomes available immediately

### Manual Installation

```bash
# Clone repo
git clone https://github.com/user/skill-repo.git

# Copy to skills directory
cp -r skill-repo/skill ~/.openclaw/skills/skill-name
```

---

## Cron Jobs (Scheduled Tasks)

### Overview

Cron jobs are scheduled tasks managed by the Gateway. They:
- Persist automatically (survive restarts)
- Stored in `~/.openclaw/cron/jobs.json`

### Two Execution Modes

1. **Main Session Jobs**
   - Enqueue during heartbeat cycles
   - Integrated with main chat history
   - Good for tasks that should be part of conversation

2. **Isolated Jobs**
   - Run in dedicated session (`cron:<jobId>`)
   - Keep noisy tasks separate from main chat
   - Can deliver results to external channels

### Scheduling Options

- **At**: One-shot timestamp (`--at "2026-02-07T10:00:00"` or `--at "+20m"`)
- **Every**: Fixed intervals (`--every 10m`, `--every 1h`)
- **Cron**: 5-field expressions (`--cron "*/5 * * * *"`)

### CLI Commands

```bash
# List cron jobs
openclaw cron list

# Add a cron job
openclaw cron add \
  --name "my-job" \
  --cron "* * * * *" \
  --session isolated \
  --message "Run: python3 script.py" \
  --deliver

# Run a job now (for testing)
openclaw cron run <job-id>

# Remove a job
openclaw cron rm <job-id>

# Check status
openclaw cron status
```

### Important: SKILL.md cron blocks DON'T auto-register

The `cron:` block in SKILL.md frontmatter is **NOT automatically registered**. Skills that need cron must:
1. Provide a `setup` command that registers the cron via `openclaw cron add`
2. Document this as a post-install step

---

## Gateway Management

### Installation

```bash
# Install as supervised service (auto-restarts)
openclaw gateway install --port 18801

# With custom state directory
OPENCLAW_STATE_DIR=~/.openclaw-custom openclaw gateway install --port 18802
```

### Commands

```bash
# Check status
openclaw gateway status

# Restart
openclaw gateway restart

# Stop
openclaw gateway stop

# View logs
openclaw gateway logs
```

### Supervision

The gateway should run as a supervised service:
- **macOS**: LaunchAgent
- **Linux**: systemd
- **Cross-platform**: pm2

This ensures auto-restart on failure.

---

## Skills CLI

```bash
# List all skills
openclaw skills list

# List only eligible skills
openclaw skills list --eligible

# Get skill info
openclaw skills info <skill-name>

# Check skill requirements
openclaw skills check
```

---

## Publishing Skills to ClawHub

```bash
# Login
clawhub login

# Publish
clawhub publish ./my-skill

# Sync all local skills
clawhub sync
```

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENCLAW_STATE_DIR` | Custom state directory (for multiple instances) |
| `OPENCLAW_BOT_ID` | Bot identifier (set dynamically from Telegram) |
| `OPENCLAW_GATEWAY_PORT` | Gateway port |
| `CLAWHUB_REGISTRY` | Custom ClawHub registry URL |

---

## Key Takeaways for Skill Developers

1. **Keep SKILL.md concise** - Context window is shared; only add what the model doesn't know
2. **Cron needs manual setup** - Provide a `setup` command for users
3. **Test on real gateway** - Skills load from `~/.openclaw/skills/`
4. **Use scripts for deterministic tasks** - Don't make the model rewrite code each time
5. **Gate skills appropriately** - Use metadata to require binaries/env vars
