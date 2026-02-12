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

## 2. Isolated Session Cleanup (Zombie Sessions)

**Problem:** Cron jobs running in `isolated` mode create a new session each run. These sessions persist as **zombies** in the gateway's memory — they finish execution but never properly terminate. The `.jsonl` files also pile up on disk. Over hours/days, this causes the gateway to use excessive memory (595MB+ observed on a 2GB VPS with 367 session files).

**Root Cause:** The gateway holds active session state in memory. Isolated cron sessions don't get cleaned up after completion, so they stay resident consuming tokens. A race condition ([#12158](https://github.com/openclaw/openclaw/issues/12158)) also causes cron sessions to fall back to 200k default context window instead of the configured limit.

**Impact:** Gateway becomes slow and unresponsive. CLI commands like `openclaw cron list` start timing out. The bot becomes noticeably laggy for the user.

**Related GitHub Issues:**
- [#12297](https://github.com/openclaw/openclaw/issues/12297) — Feature request for `sessions_kill` and `sessions_cleanup` tools (23+ zombie cron sessions, ~250k wasted tokens)
- [#11665](https://github.com/openclaw/openclaw/issues/11665) — 319 orphaned session files accumulated in 2 days from webhook sessions
- [#12158](https://github.com/openclaw/openclaw/issues/12158) — `lookupContextTokens()` race condition causes cron sessions to use 200k default context

**Proposed Solution:**
- Auto-terminate isolated cron sessions after the run completes (clear from memory + delete file)
- Or add `sessions_kill` / `sessions_cleanup` tools as proposed in #12297
- Or add a `sessionRetention` option per cron job (e.g., `--retain none`)

**Workaround (current):** Skill script deletes `.jsonl` files older than 30 minutes at the start of each cron run. This helps with disk but doesn't clear zombie sessions from gateway memory — only a gateway restart does that.

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

## 5. Persistent Session Mode for Scheduled Cron

**Problem:** Scheduled cron jobs can only use `isolated` session mode, which creates a new session every run and causes zombie session buildup (#12297). The `main` session mode reuses an existing session but requires `--system-event` — it cannot be used with a cron schedule.

There's no way to say "run this on a schedule AND reuse the same session."

**Impact:** Every skill with a scheduled cron is forced into `isolated` mode, which means every user accumulates zombie sessions in gateway RAM over time. The only fix is periodic gateway restarts.

**Proposed Solution:** Allow `main` (or a new `persistent`) session mode for scheduled cron:
```bash
openclaw cron add --name "my-check" --cron "*/10 * * * *" --session persistent --message "Run: python3 scripts/check.py"
```

This would reuse the same session across runs. Compaction handles growing context automatically.

**Workaround (current):** Use `isolated` + delete old `.jsonl` session files from the script. Disk stays clean but RAM zombies remain until gateway restart.

---

## 6. Skill Version Tracking

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
