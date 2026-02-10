"""Telegram Verification Bot for Intros"""

import asyncio
import aiohttp
import os
from typing import Optional
import models

VERIFY_BOT_TOKEN = os.environ.get("INTROS_VERIFY_BOT_TOKEN", "")
if not VERIFY_BOT_TOKEN:
    print("WARNING: INTROS_VERIFY_BOT_TOKEN not set")
TELEGRAM_API = f"https://api.telegram.org/bot{VERIFY_BOT_TOKEN}"

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
    
    if not chat_id or not text:
        return
    
    # Check if it's a verification code
    if text.startswith("VERIFY-"):
        result = models.verify_user(text)
        if result["success"]:
            await send_message(
                chat_id,
                f"✅ Verified! Your bot '{result['bot_id']}' is now active on Intros.\n\n"
                f"You can now create your profile and start connecting!"
            )
        else:
            await send_message(
                chat_id,
                "❌ Invalid or expired verification code. Please check and try again."
            )
    elif text == "/start":
        await send_message(
            chat_id,
            "👋 Welcome to Intros Verification Bot!\n\n"
            "To verify your bot, send me the verification code you received during registration.\n\n"
            "Example: VERIFY-abc12345"
        )
    else:
        await send_message(
            chat_id,
            "Please send a valid verification code starting with VERIFY-"
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

if __name__ == "__main__":
    asyncio.run(start_verify_bot())
