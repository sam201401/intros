#!/bin/bash

echo "=== Deploying Intros from GitHub ==="

cd /root/intros

# Load env vars
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Pull latest code (reset local changes so pull never fails)
git fetch origin main
git reset --hard origin/main
echo "✅ Code updated"

# Sync skill to OpenClaw
cp skill/scripts/intros.py /root/.openclaw/skills/intros/scripts/intros.py
echo "✅ Skill synced"

# Restart API
lsof -i :8080 2>/dev/null | awk "NR>1 {print \$2}" | xargs -r kill 2>/dev/null || true
sleep 2
cd /root/intros/api
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 > /tmp/intros.log 2>&1 &

# Wait for API to be ready (up to 15s)
for i in $(seq 1 15); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null)
    if [ "$STATUS" = "200" ]; then
        echo "✅ API restarted (ready in ${i}s)"
        break
    fi
    sleep 1
done
if [ "$STATUS" != "200" ]; then
    echo "❌ API may have failed (HTTP $STATUS)"
    echo "Check logs: tail /tmp/intros.log"
fi

echo "=== Deploy complete ==="
