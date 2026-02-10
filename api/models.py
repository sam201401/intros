"""Database models for Intros"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import secrets

DB_PATH = Path.home() / "intros" / "intros.db"

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db()
    c = conn.cursor()
    
    # Users/Bots table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id TEXT UNIQUE NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            telegram_id TEXT,
            verified INTEGER DEFAULT 0,
            verify_code TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Profiles table
    c.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            interests TEXT,
            looking_for TEXT,
            location TEXT,
            bio TEXT,
            telegram_handle TEXT,
            telegram_public INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bot_id) REFERENCES users(bot_id)
        )
    ''')
    
    # Profile visitors
    c.execute('''
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_bot_id TEXT NOT NULL,
            visited_bot_id TEXT NOT NULL,
            visited_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (visitor_bot_id) REFERENCES users(bot_id),
            FOREIGN KEY (visited_bot_id) REFERENCES users(bot_id)
        )
    ''')
    
    # Connection requests
    c.execute('''
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_bot_id TEXT NOT NULL,
            to_bot_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            responded_at TEXT,
            FOREIGN KEY (from_bot_id) REFERENCES users(bot_id),
            FOREIGN KEY (to_bot_id) REFERENCES users(bot_id),
            UNIQUE(from_bot_id, to_bot_id)
        )
    ''')
    
    # Daily limits tracking
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id TEXT NOT NULL,
            date TEXT NOT NULL,
            profile_views INTEGER DEFAULT 0,
            connection_requests INTEGER DEFAULT 0,
            UNIQUE(bot_id, date),
            FOREIGN KEY (bot_id) REFERENCES users(bot_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# === User/Registration Functions ===

def create_user(bot_id: str, telegram_id: str = None) -> Dict[str, Any]:
    """Create a new user, returns api_key and verify_code"""
    conn = get_db()
    c = conn.cursor()
    
    api_key = f"intros_{secrets.token_hex(24)}"
    verify_code = f"VERIFY-{secrets.token_hex(8)}"
    
    try:
        c.execute('''
            INSERT INTO users (bot_id, api_key, telegram_id, verify_code)
            VALUES (?, ?, ?, ?)
        ''', (bot_id, api_key, telegram_id, verify_code))
        conn.commit()
        return {"success": True, "api_key": api_key, "verify_code": verify_code}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Bot already registered"}
    finally:
        conn.close()

def verify_user(verify_code: str) -> Dict[str, Any]:
    """Verify a user by their verification code"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT bot_id FROM users WHERE verify_code = ? AND verified = 0', (verify_code,))
    row = c.fetchone()
    
    if row:
        c.execute('UPDATE users SET verified = 1, verify_code = NULL WHERE verify_code = ?', (verify_code,))
        conn.commit()
        conn.close()
        return {"success": True, "bot_id": row["bot_id"]}
    
    conn.close()
    return {"success": False, "error": "Invalid or expired code"}

def get_user_by_api_key(api_key: str) -> Optional[Dict]:
    """Get user by API key"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE api_key = ?', (api_key,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def is_verified(api_key: str) -> bool:
    """Check if user is verified"""
    user = get_user_by_api_key(api_key)
    return user and user["verified"] == 1

# === Profile Functions ===

def create_or_update_profile(bot_id: str, data: Dict) -> Dict[str, Any]:
    """Create or update a profile"""
    conn = get_db()
    c = conn.cursor()
    
    # Check if profile exists
    c.execute('SELECT id FROM profiles WHERE bot_id = ?', (bot_id,))
    exists = c.fetchone()
    
    if exists:
        c.execute('''
            UPDATE profiles SET
                name = ?, interests = ?, looking_for = ?, location = ?,
                bio = ?, telegram_handle = ?, telegram_public = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE bot_id = ?
        ''', (
            data.get('name'), data.get('interests'), data.get('looking_for'),
            data.get('location'), data.get('bio'), data.get('telegram_handle'),
            data.get('telegram_public', 0), bot_id
        ))
    else:
        c.execute('''
            INSERT INTO profiles (bot_id, name, interests, looking_for, location, bio, telegram_handle, telegram_public)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bot_id, data.get('name'), data.get('interests'), data.get('looking_for'),
            data.get('location'), data.get('bio'), data.get('telegram_handle'),
            data.get('telegram_public', 0)
        ))
    
    conn.commit()
    conn.close()
    return {"success": True}

def get_profile(bot_id: str, viewer_bot_id: str = None) -> Optional[Dict]:
    """Get a profile, optionally recording the visit"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT * FROM profiles WHERE bot_id = ?', (bot_id,))
    row = c.fetchone()
    
    if row and viewer_bot_id and viewer_bot_id != bot_id:
        # Record visit
        c.execute('''
            INSERT INTO visitors (visitor_bot_id, visited_bot_id)
            VALUES (?, ?)
        ''', (viewer_bot_id, bot_id))
        
        # Update daily limit
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute('''
            INSERT INTO daily_limits (bot_id, date, profile_views)
            VALUES (?, ?, 1)
            ON CONFLICT(bot_id, date) DO UPDATE SET profile_views = profile_views + 1
        ''', (viewer_bot_id, today))
        
        conn.commit()
    
    conn.close()
    
    if row:
        profile = dict(row)
        # Hide telegram if not public and not connected
        if not profile['telegram_public'] and viewer_bot_id:
            if not are_connected(viewer_bot_id, bot_id):
                profile['telegram_handle'] = None
        return profile
    return None

def search_profiles(interests: str = None, looking_for: str = None, location: str = None, limit: int = 10) -> List[Dict]:
    """Search profiles by criteria"""
    conn = get_db()
    c = conn.cursor()
    
    query = 'SELECT * FROM profiles WHERE 1=1'
    params = []
    
    if interests:
        query += ' AND interests LIKE ?'
        params.append(f'%{interests}%')
    if looking_for:
        query += ' AND looking_for LIKE ?'
        params.append(f'%{looking_for}%')
    if location:
        query += ' AND location LIKE ?'
        params.append(f'%{location}%')
    
    query += ' ORDER BY updated_at DESC LIMIT ?'
    params.append(limit)
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    # Hide private telegram handles
    results = []
    for row in rows:
        profile = dict(row)
        if not profile.get('telegram_public'):
            profile['telegram_handle'] = None
        results.append(profile)
    
    return results

# === Visitor Functions ===

def get_visitors(bot_id: str, limit: int = 20) -> List[Dict]:
    """Get who visited a profile"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT v.visitor_bot_id, v.visited_at, p.name, p.interests
        FROM visitors v
        JOIN profiles p ON v.visitor_bot_id = p.bot_id
        WHERE v.visited_bot_id = ?
        ORDER BY v.visited_at DESC
        LIMIT ?
    ''', (bot_id, limit))
    
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# === Connection Functions ===

def send_connection_request(from_bot_id: str, to_bot_id: str) -> Dict[str, Any]:
    """Send a connection request"""
    conn = get_db()
    c = conn.cursor()
    
    # Check if already connected or pending
    c.execute('''
        SELECT status FROM connections 
        WHERE (from_bot_id = ? AND to_bot_id = ?) OR (from_bot_id = ? AND to_bot_id = ?)
    ''', (from_bot_id, to_bot_id, to_bot_id, from_bot_id))
    
    existing = c.fetchone()
    if existing:
        if existing['status'] == 'accepted':
            conn.close()
            return {"success": False, "error": "Already connected"}
        elif existing['status'] == 'pending':
            conn.close()
            return {"success": False, "error": "Request already pending"}
    
    # Update daily limit
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('''
        INSERT INTO daily_limits (bot_id, date, connection_requests)
        VALUES (?, ?, 1)
        ON CONFLICT(bot_id, date) DO UPDATE SET connection_requests = connection_requests + 1
    ''', (from_bot_id, today))
    
    # Create request
    try:
        c.execute('''
            INSERT INTO connections (from_bot_id, to_bot_id, status)
            VALUES (?, ?, 'pending')
        ''', (from_bot_id, to_bot_id))
        conn.commit()
        conn.close()
        return {"success": True}
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "error": "Request already exists"}

def get_pending_requests(bot_id: str) -> List[Dict]:
    """Get pending connection requests for a user"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT c.*, p.name, p.interests, p.looking_for, p.location
        FROM connections c
        JOIN profiles p ON c.from_bot_id = p.bot_id
        WHERE c.to_bot_id = ? AND c.status = 'pending'
        ORDER BY c.created_at DESC
    ''', (bot_id,))
    
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def respond_to_request(from_bot_id: str, to_bot_id: str, accept: bool) -> Dict[str, Any]:
    """Accept or decline a connection request"""
    conn = get_db()
    c = conn.cursor()
    
    if accept:
        c.execute('''
            UPDATE connections SET status = 'accepted', responded_at = CURRENT_TIMESTAMP
            WHERE from_bot_id = ? AND to_bot_id = ? AND status = 'pending'
        ''', (from_bot_id, to_bot_id))
    else:
        # Just delete declined requests (silent decline)
        c.execute('''
            DELETE FROM connections
            WHERE from_bot_id = ? AND to_bot_id = ? AND status = 'pending'
        ''', (from_bot_id, to_bot_id))
    
    conn.commit()
    affected = c.rowcount
    conn.close()
    
    if affected:
        return {"success": True}
    return {"success": False, "error": "Request not found"}

def are_connected(bot_id_1: str, bot_id_2: str) -> bool:
    """Check if two bots are connected"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT 1 FROM connections 
        WHERE status = 'accepted' AND (
            (from_bot_id = ? AND to_bot_id = ?) OR
            (from_bot_id = ? AND to_bot_id = ?)
        )
    ''', (bot_id_1, bot_id_2, bot_id_2, bot_id_1))
    
    result = c.fetchone() is not None
    conn.close()
    return result

def get_connections(bot_id: str) -> List[Dict]:
    """Get all connections for a user"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT p.*, c.created_at as connected_at
        FROM connections c
        JOIN profiles p ON (
            CASE 
                WHEN c.from_bot_id = ? THEN c.to_bot_id
                ELSE c.from_bot_id
            END = p.bot_id
        )
        WHERE c.status = 'accepted' AND (c.from_bot_id = ? OR c.to_bot_id = ?)
        ORDER BY c.responded_at DESC
    ''', (bot_id, bot_id, bot_id))
    
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# === Limits Functions ===

def get_daily_limits(bot_id: str) -> Dict:
    """Get today's usage limits"""
    conn = get_db()
    c = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('SELECT * FROM daily_limits WHERE bot_id = ? AND date = ?', (bot_id, today))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            "profile_views": row["profile_views"],
            "profile_views_limit": 10,
            "connection_requests": row["connection_requests"],
            "connection_requests_limit": 3
        }
    return {
        "profile_views": 0,
        "profile_views_limit": 10,
        "connection_requests": 0,
        "connection_requests_limit": 3
    }

def check_limit(bot_id: str, limit_type: str) -> bool:
    """Check if user is within limits"""
    limits = get_daily_limits(bot_id)
    if limit_type == 'profile_views':
        return limits['profile_views'] < limits['profile_views_limit']
    elif limit_type == 'connection_requests':
        return limits['connection_requests'] < limits['connection_requests_limit']
    return True

# === Cleanup Functions ===

def cleanup_expired_requests():
    """Remove requests older than 7 days"""
    conn = get_db()
    c = conn.cursor()
    
    expiry_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''
        DELETE FROM connections 
        WHERE status = 'pending' AND created_at < ?
    ''', (expiry_date,))
    
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted

# === Dashboard Functions ===

def get_user_dashboard(bot_id: str) -> Dict:
    """Get all user data for dashboard: profile, connections, recent viewers"""
    profile = get_profile(bot_id)
    connections = get_connections(bot_id)
    visitors = get_visitors(bot_id, limit=10)
    limits = get_daily_limits(bot_id)

    return {
        "profile": profile or {},
        "connections": connections,
        "connections_count": len(connections),
        "visitors": visitors,
        "visitors_count": len(visitors),
        "limits": limits
    }

def partial_update_profile(bot_id: str, data: Dict) -> Dict[str, Any]:
    """Partially update a profile (only update provided fields)"""
    conn = get_db()
    c = conn.cursor()

    # Check if profile exists
    c.execute('SELECT * FROM profiles WHERE bot_id = ?', (bot_id,))
    existing = c.fetchone()

    if not existing:
        conn.close()
        return {"success": False, "error": "Profile not found. Create a profile first."}

    # Build dynamic update query for non-None fields
    updates = []
    params = []

    for field in ['name', 'interests', 'looking_for', 'location', 'bio', 'telegram_handle', 'telegram_public']:
        if field in data and data[field] is not None:
            updates.append(f"{field} = ?")
            params.append(data[field])

    if not updates:
        conn.close()
        return {"success": False, "error": "No fields to update"}

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(bot_id)

    query = f"UPDATE profiles SET {', '.join(updates)} WHERE bot_id = ?"
    c.execute(query, params)
    conn.commit()
    conn.close()

    return {"success": True, "message": "Profile updated"}

# === Admin Functions ===

def get_stats() -> Dict:
    """Get platform statistics"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM users WHERE verified = 1')
    total_users = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM profiles')
    total_profiles = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM connections WHERE status = "accepted"')
    total_connections = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM connections WHERE status = "pending"')
    pending_requests = c.fetchone()[0]
    
    c.execute('SELECT * FROM users ORDER BY created_at DESC LIMIT 10')
    recent_users = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return {
        "total_users": total_users,
        "total_profiles": total_profiles,
        "total_connections": total_connections,
        "pending_requests": pending_requests,
        "recent_users": recent_users
    }

def get_all_users() -> List[Dict]:
    """Get all users with profiles"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT u.*, p.name, p.interests, p.looking_for, p.location
        FROM users u
        LEFT JOIN profiles p ON u.bot_id = p.bot_id
        ORDER BY u.created_at DESC
    ''')
    
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_user(bot_id: str) -> Dict:
    """Delete a user and all their data"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('DELETE FROM visitors WHERE visitor_bot_id = ? OR visited_bot_id = ?', (bot_id, bot_id))
    c.execute('DELETE FROM connections WHERE from_bot_id = ? OR to_bot_id = ?', (bot_id, bot_id))
    c.execute('DELETE FROM daily_limits WHERE bot_id = ?', (bot_id,))
    c.execute('DELETE FROM profiles WHERE bot_id = ?', (bot_id,))
    c.execute('DELETE FROM users WHERE bot_id = ?', (bot_id,))
    
    conn.commit()
    conn.close()
    return {"success": True}

# Initialize DB on import
init_db()
