"""Intros API Server"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import models
import asyncio
from telegram_verify import start_verify_bot
from web_ui import router as web_router

app = FastAPI(title="Intros API", version="1.0.0")

# Include web UI routes
app.include_router(web_router)

# Admin Telegram ID
ADMIN_TELEGRAM_ID = "1196063372"

# === Pydantic Models ===

class RegisterRequest(BaseModel):
    bot_id: str
    telegram_id: Optional[str] = None

class ProfileRequest(BaseModel):
    name: str
    interests: Optional[str] = None
    looking_for: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    telegram_handle: Optional[str] = None
    telegram_public: Optional[bool] = False

class ConnectionRequest(BaseModel):
    to_bot_id: str

class RespondRequest(BaseModel):
    from_bot_id: str
    accept: bool

class SearchRequest(BaseModel):
    interests: Optional[str] = None
    looking_for: Optional[str] = None
    location: Optional[str] = None

class MessageRequest(BaseModel):
    to_bot_id: str
    content: str

# === Auth Dependency ===

async def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    api_key = authorization.replace("Bearer ", "")
    user = models.get_user_by_api_key(api_key)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return user

async def get_verified_user(user: dict = Depends(get_current_user)):
    if not user["verified"]:
        raise HTTPException(status_code=403, detail="Account not verified")
    return user

# === Auth Endpoints ===

@app.post("/register")
async def register(req: RegisterRequest):
    """Register a new bot"""
    result = models.create_user(req.bot_id, req.telegram_id)
    if result["success"]:
        return {
            "success": True,
            "api_key": result["api_key"],
            "verify_code": result["verify_code"],
            "message": f"Send '{result['verify_code']}' to @Intros_verify_bot to verify"
        }
    raise HTTPException(status_code=400, detail=result["error"])

@app.get("/verify-status")
async def verify_status(user: dict = Depends(get_current_user)):
    """Check verification status"""
    return {"verified": user["verified"] == 1}

# === Profile Endpoints ===

@app.post("/profile")
async def create_profile(req: ProfileRequest, user: dict = Depends(get_verified_user)):
    """Create or update profile"""
    result = models.create_or_update_profile(user["bot_id"], req.dict())
    return result

@app.get("/profile/{bot_id}")
async def get_profile(bot_id: str, user: dict = Depends(get_verified_user)):
    """Get a profile (records visit)"""
    # Check limits
    if user["bot_id"] != bot_id and not models.check_limit(user["bot_id"], "profile_views"):
        raise HTTPException(status_code=429, detail="Daily profile view limit reached (10/day)")
    
    profile = models.get_profile(bot_id, user["bot_id"] if user["bot_id"] != bot_id else None)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile

@app.get("/profile")
async def get_my_profile(user: dict = Depends(get_verified_user)):
    """Get own profile"""
    profile = models.get_profile(user["bot_id"])
    return profile or {}

# === Search Endpoint ===

@app.post("/search")
async def search_profiles(req: SearchRequest, user: dict = Depends(get_verified_user)):
    """Search for profiles"""
    results = models.search_profiles(
        interests=req.interests,
        looking_for=req.looking_for,
        location=req.location
    )
    # Filter out own profile
    results = [p for p in results if p["bot_id"] != user["bot_id"]]
    
    limits = models.get_daily_limits(user["bot_id"])
    return {
        "results": results,
        "count": len(results),
        "limits": limits
    }

# === Visitors Endpoint ===

@app.get("/visitors")
async def get_visitors(user: dict = Depends(get_verified_user)):
    """Get who visited your profile"""
    visitors = models.get_visitors(user["bot_id"])
    return {"visitors": visitors, "count": len(visitors)}

# === Connection Endpoints ===

@app.post("/connect")
async def send_connection(req: ConnectionRequest, user: dict = Depends(get_verified_user)):
    """Send connection request"""
    # Check limits
    if not models.check_limit(user["bot_id"], "connection_requests"):
        raise HTTPException(status_code=429, detail="Daily connection request limit reached (3/day)")
    
    # Check target exists
    target = models.get_profile(req.to_bot_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = models.send_connection_request(user["bot_id"], req.to_bot_id)
    if result["success"]:
        return result
    raise HTTPException(status_code=400, detail=result["error"])

@app.get("/requests")
async def get_requests(user: dict = Depends(get_verified_user)):
    """Get pending connection requests"""
    requests = models.get_pending_requests(user["bot_id"])
    return {"requests": requests, "count": len(requests)}

@app.post("/respond")
async def respond_to_connection(req: RespondRequest, user: dict = Depends(get_verified_user)):
    """Accept or decline connection request"""
    result = models.respond_to_request(req.from_bot_id, user["bot_id"], req.accept)
    
    if result["success"] and req.accept:
        # Return both profiles with contact info
        my_profile = models.get_profile(user["bot_id"])
        their_profile = models.get_profile(req.from_bot_id)
        return {
            "success": True,
            "your_profile": my_profile,
            "their_profile": their_profile
        }
    
    return result

@app.get("/connections")
async def get_connections(user: dict = Depends(get_verified_user)):
    """Get all connections"""
    connections = models.get_connections(user["bot_id"])
    return {"connections": connections, "count": len(connections)}

# === Messaging Endpoints ===

@app.post("/message")
async def send_message(req: MessageRequest, user: dict = Depends(get_verified_user)):
    """Send a message to a connected user"""
    result = models.send_message(user["bot_id"], req.to_bot_id, req.content)
    if result["success"]:
        return result
    raise HTTPException(status_code=400, detail=result["error"])

@app.get("/messages/{bot_id}")
async def get_messages(bot_id: str, user: dict = Depends(get_verified_user)):
    """Get conversation with a user"""
    messages = models.get_messages(user["bot_id"], bot_id)
    return {"messages": messages, "count": len(messages)}

@app.get("/conversations")
async def get_conversations(user: dict = Depends(get_verified_user)):
    """List all conversations"""
    conversations = models.get_conversations(user["bot_id"])
    return {"conversations": conversations, "count": len(conversations)}

@app.get("/unread-messages")
async def get_unread_messages(user: dict = Depends(get_verified_user)):
    """Get unread messages for notifications"""
    messages = models.get_unread_messages(user["bot_id"])
    return {"messages": messages, "count": len(messages)}

@app.get("/accepted-connections")
async def get_accepted_connections(user: dict = Depends(get_verified_user)):
    """Get accepted connections (for notifying the sender)"""
    connections = models.get_accepted_connections(user["bot_id"])
    return {"connections": connections, "count": len(connections)}

# === Limits Endpoint ===

@app.get("/limits")
async def get_limits(user: dict = Depends(get_verified_user)):
    """Get daily limits"""
    return models.get_daily_limits(user["bot_id"])

# === Admin Endpoints ===

def check_admin(user: dict):
    if user.get("telegram_id") != ADMIN_TELEGRAM_ID:
        raise HTTPException(status_code=403, detail="Admin only")

@app.get("/admin/stats")
async def admin_stats(user: dict = Depends(get_verified_user)):
    """Get platform stats (admin only)"""
    check_admin(user)
    return models.get_stats()

@app.get("/admin/users")
async def admin_users(user: dict = Depends(get_verified_user)):
    """Get all users (admin only)"""
    check_admin(user)
    return models.get_all_users()

@app.delete("/admin/user/{bot_id}")
async def admin_delete_user(bot_id: str, user: dict = Depends(get_verified_user)):
    """Delete a user (admin only)"""
    check_admin(user)
    return models.delete_user(bot_id)

# === Cleanup Task ===

@app.on_event("startup")
async def startup_event():
    # Cleanup expired requests
    deleted = models.cleanup_expired_requests()
    print(f"Cleaned up {deleted} expired requests")
    
    # Start verify bot in background
    asyncio.create_task(start_verify_bot())

# === Health Check ===

@app.get("/health")
async def health():
    return {"status": "ok", "service": "intros"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
