# OpenClaw Missing Features / PR Ideas

Issues discovered while building the Intros skill. Each could be a PR or feature request for [openclaw/openclaw](https://github.com/openclaw/openclaw).

---

## 1. Skill Post-Install Hook

**Problem:** When a skill is installed or reinstalled (via `clawhub install`, GitHub, or manual copy), only the files are replaced. There's no way to run setup code automatically. Skills that need cron jobs, config migration, or dependency checks have to rely on the user manually running a setup command.

**Impact:** After reinstalling Intros, the old cron job keeps running with the old schedule. Users don't know they need to run `setup` again.

**Proposed Solution:** Add a `post-install` field to SKILL.md frontmatter, or look for a `scripts/setup.sh` file and execute it after install:
```yaml
---
name: my-skill
post-install: "python3 scripts/setup.py"
---
```

**Workaround (current):** Self-healing logic in the cron script — detects stale schedule and recreates the cron on next run.

---

## 2. Isolated Session Cleanup

**Problem:** Cron jobs running in `isolated` mode create a new session file (`~/.openclaw/agents/main/sessions/*.jsonl`) every run. These files are never cleaned up. Over hours/days, hundreds of session files pile up, causing the gateway to use excessive memory (595MB+ observed on a 2GB VPS).

**Impact:** Gateway becomes slow and unresponsive. CLI commands like `openclaw cron list` start timing out. The bot becomes noticeably laggy for the user.

**Proposed Solution:**
- Auto-delete isolated cron session files after the run completes
- Or add a `sessionRetention` option per cron job (e.g., `--retain none`)
- Or add a global setting: `cron.sessionCleanupAfter: "1h"`

**Workaround (current):** Skill script manually deletes old `.jsonl` files from the sessions directory at the start of each cron run.

---

## 3. Cron Declaration in SKILL.md

**Problem:** Skills cannot declare cron jobs in SKILL.md frontmatter. Every skill that needs scheduled tasks must programmatically call `openclaw cron add` via subprocess, which is fragile and depends on the CLI being available.

**Impact:** Cron setup is a manual step that users forget. If the gateway restarts or cron gets deleted, there's no declarative source to recreate it from.

**Proposed Solution:** Allow cron declaration in SKILL.md frontmatter:
```yaml
---
name: my-skill
cron:
  - name: my-notifications
    schedule: "*/10 * * * *"
    session: isolated
    message: "Run: python3 scripts/check.py"
    announce: true
---
```

OpenClaw would auto-register these crons when the skill is loaded, and remove them when uninstalled.

---

## 4. Lightweight Cron Execution (No AI Agent)

**Problem:** Every isolated cron run launches a full AI agent session — sends the message to Claude API, waits for the LLM to interpret it, then the LLM decides to run the script. A simple "run this Python script" takes 30-40 seconds of LLM inference instead of 1 second of direct execution.

**Impact:** At 1000 users each with a notification cron, that's 1000 LLM API calls every 10 minutes just for notification checks. Expensive and slow.

**Proposed Solution:** Add a `direct` execution mode for cron that runs the command directly without AI interpretation:
```bash
openclaw cron add --name "my-check" --cron "*/10 * * * *" --exec "python3 scripts/check.py" --announce
```

The `--exec` flag would run the command directly and pipe stdout to the announce channel. No LLM involved.

---

## 5. Skill Version Tracking

**Problem:** After a skill is installed, there's no record of which version is installed. When a new version is published to ClawHub, there's no way to know if the local copy is outdated. The lock file only records the slug, not the version.

**Impact:** Users don't know they're running an old version. No way to prompt for updates.

**Proposed Solution:** Store installed version in `.clawhub/lock.json` and compare against registry on `clawhub list` or a new `clawhub outdated` command.

---

## References

- [Skills Documentation](https://docs.openclaw.ai/tools/skills)
- [Cron Documentation](https://docs.openclaw.ai/automation/cron-jobs)
- [Hooks Documentation](https://docs.openclaw.ai/automation/hooks)
- [ClawHub Documentation](https://docs.openclaw.ai/tools/clawhub)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
