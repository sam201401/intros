"""Telegram Verification Bot + Notification Loop for Intros"""

import asyncio
import aiohttp
import os
from datetime import date
from typing import Optional
import models

VERIFY_BOT_TOKEN = os.environ.get("INTROS_VERIFY_BOT_TOKEN", "")
if not VERIFY_BOT_TOKEN:
    print("WARNING: INTROS_VERIFY_BOT_TOKEN not set")
TELEGRAM_API = f"https://api.telegram.org/bot{VERIFY_BOT_TOKEN}"

NOTIFICATION_INTERVAL = int(os.environ.get("INTROS_NOTIFY_INTERVAL", "60"))

last_update_id = 0

async def get_updates(offset: int = 0) -> list:
    """Get updates from Telegram"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{TELEGRAM_API}/getUpdates",
                params={"offset": offset, "timeout": 30}
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data.get("result", [])
        except Exception as e:
            print(f"Error getting updates: {e}")
    return []

async def send_message(chat_id: int, text: str):
    """Send message to Telegram user"""
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": chat_id, "text": text}
            )
        except Exception as e:
            print(f"Error sending message: {e}")

async def process_message(message: dict):
    """Process incoming message"""
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    telegram_user_id = str(message.get("from", {}).get("id", ""))

    if not chat_id or not text:
        return

    # Check if it's a verification code
    if text.startswith("VERIFY-"):
        result = models.verify_user(text, chat_id=chat_id)
        if result["success"]:
            await send_message(
                chat_id,
                f"Verified! Your bot '{result['bot_id']}' is now active on Intros.\n\n"
                f"You can now create your profile and start connecting!\n"
                f"You'll receive notifications for new messages and connection requests here."
            )
        else:
            await send_message(
                chat_id,
                "Invalid or expired verification code. Please check and try again."
            )
    elif text == "/start":
        # Capture chat_id for existing users who message the bot
        if telegram_user_id:
            models.update_user_chat_id(telegram_user_id, chat_id)
        await send_message(
            chat_id,
            "Welcome to Intros!\n\n"
            "To verify your bot, send me the verification code you received during registration.\n\n"
            "Example: VERIFY-abc12345\n\n"
            "Once verified, you'll receive notifications for new messages and connection requests here."
        )
    else:
        # Capture chat_id for existing users who send any message
        if telegram_user_id:
            models.update_user_chat_id(telegram_user_id, chat_id)
        await send_message(
            chat_id,
            "Please send a valid verification code starting with VERIFY-\n\n"
            "If you're already verified, you'll receive notifications here automatically."
        )

async def start_verify_bot():
    """Start the verification bot polling loop"""
    global last_update_id
    print("Starting Intros Verify Bot...")

    while True:
        try:
            updates = await get_updates(last_update_id + 1)

            for update in updates:
                last_update_id = update.get("update_id", last_update_id)

                if "message" in update:
                    await process_message(update["message"])

            await asyncio.sleep(1)
        except Exception as e:
            print(f"Verify bot error: {e}")
            await asyncio.sleep(5)

# === Notification Loop ===

# Track daily nudge per user (in-memory, resets on restart which is fine)
_daily_nudge_sent = {}

async def check_and_send_notifications():
    """Check all users for new notifications and send via Telegram"""
    users = models.get_notifiable_users()

    for user in users:
        bot_id = user["bot_id"]
        chat_id = user["telegram_chat_id"]

        try:
            # 1. New unread messages
            messages = models.get_unread_messages(bot_id)
            for msg in messages:
                msg_id = msg.get("id")
                if not msg_id:
                    continue
                if models.is_notification_sent(bot_id, "message", msg_id):
                    continue
                name = msg.get("from_name", msg.get("from_bot_id", "Someone"))
                content = msg.get("content", "")
                text = (
                    f"📬 New message from {name}\n\n"
                    f"\"{content}\"\n\n"
                    f"Open your OpenClaw bot to reply."
                )
                await send_message(chat_id, text)
                models.mark_notification_sent(bot_id, "message", msg_id)

            # 2. New pending connection requests
            requests = models.get_pending_requests(bot_id)
            for req in requests:
                req_id = req.get("id")
                if not req_id:
                    continue
                if models.is_notification_sent(bot_id, "request", req_id):
                    continue
                name = req.get("name", req.get("from_bot_id", "Someone"))
                interests = req.get("interests", "")
                location = req.get("location", "")
                text = f"🔔 New connection request\n\nFrom: {name}\n"
                if interests:
                    text += f"Interests: {interests}\n"
                if location:
                    text += f"Location: {location}\n"
                text += f"\nOpen your OpenClaw bot to accept or decline."
                await send_message(chat_id, text)
                models.mark_notification_sent(bot_id, "request", req_id)

            # 3. Newly accepted connections
            accepted = models.get_accepted_connections(bot_id)
            for conn in accepted:
                conn_id = conn.get("id")
                if not conn_id:
                    continue
                if models.is_notification_sent(bot_id, "accepted", conn_id):
                    continue
                name = conn.get("name", "Someone")
                telegram = conn.get("telegram_handle", "")
                text = f"✅ Connection accepted!\n\n{name} accepted your connection request.\n"
                if telegram:
                    text += f"Telegram: @{telegram}\n"
                text += "\nOpen your OpenClaw bot to start chatting."
                await send_message(chat_id, text)
                models.mark_notification_sent(bot_id, "accepted", conn_id)

            # 4. Daily matches nudge (once per day)
            today = date.today().isoformat()
            if _daily_nudge_sent.get(bot_id) != today:
                remaining = models.remaining_profile_views(bot_id)
                if remaining > 0:
                    text = f"🌟 Your daily matches are ready! You have {remaining} profile views today.\n\nOpen your OpenClaw bot and say 'recommend' to discover new people."
                    await send_message(chat_id, text)
                    _daily_nudge_sent[bot_id] = today

        except Exception as e:
            print(f"Notification error for {bot_id}: {e}")

async def start_notification_loop():
    """Run notification checks on a timer"""
    print(f"Starting notification loop (every {NOTIFICATION_INTERVAL}s)...")
    # Brief delay to let the API finish starting
    await asyncio.sleep(5)

    while True:
        try:
            await check_and_send_notifications()
        except Exception as e:
            print(f"Notification loop error: {e}")
        await asyncio.sleep(NOTIFICATION_INTERVAL)

if __name__ == "__main__":
    asyncio.run(start_verify_bot())
