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
            telegram_chat_id INTEGER,
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

    # Messages table
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_bot_id TEXT NOT NULL,
            to_bot_id TEXT NOT NULL,
            content TEXT NOT NULL,
            read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_bot_id) REFERENCES users(bot_id),
            FOREIGN KEY (to_bot_id) REFERENCES users(bot_id)
        )
    ''')

    # Add indexes for performance
    c.execute('CREATE INDEX IF NOT EXISTS idx_messages_to_unread ON messages(to_bot_id, read)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_messages_from ON messages(from_bot_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_connections_to_status ON connections(to_bot_id, status)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_connections_from_status ON connections(from_bot_id, status)')

    # FTS5 full-text search index for profiles
    c.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS profiles_fts USING fts5(
            name, interests, looking_for, location, bio,
            content=profiles, content_rowid=id
        )
    ''')

    # Triggers to keep FTS in sync with profiles table
    for trigger_sql in [
        '''CREATE TRIGGER profiles_ai AFTER INSERT ON profiles BEGIN
            INSERT INTO profiles_fts(rowid, name, interests, looking_for, location, bio)
            VALUES (new.id, new.name, new.interests, new.looking_for, new.location, new.bio);
        END''',
        '''CREATE TRIGGER profiles_ad AFTER DELETE ON profiles BEGIN
            INSERT INTO profiles_fts(profiles_fts, rowid, name, interests, looking_for, location, bio)
            VALUES ('delete', old.id, old.name, old.interests, old.looking_for, old.location, old.bio);
        END''',
        '''CREATE TRIGGER profiles_au AFTER UPDATE ON profiles BEGIN
            INSERT INTO profiles_fts(profiles_fts, rowid, name, interests, looking_for, location, bio)
            VALUES ('delete', old.id, old.name, old.interests, old.looking_for, old.location, old.bio);
            INSERT INTO profiles_fts(rowid, name, interests, looking_for, location, bio)
            VALUES (new.id, new.name, new.interests, new.looking_for, new.location, new.bio);
        END''',
    ]:
        try:
            c.execute(trigger_sql)
        except sqlite3.OperationalError:
            pass  # Trigger already exists

    conn.commit()

    # Rebuild FTS index from existing data (idempotent, fast for <1000 rows)
    c.execute("INSERT INTO profiles_fts(profiles_fts) VALUES('rebuild')")
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

def verify_user(verify_code: str, chat_id: int = None) -> Dict[str, Any]:
    """Verify a user by their verification code and store telegram chat_id"""
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT bot_id FROM users WHERE verify_code = ? AND verified = 0', (verify_code,))
    row = c.fetchone()

    if row:
        if chat_id:
            c.execute('UPDATE users SET verified = 1, verify_code = NULL, telegram_chat_id = ? WHERE verify_code = ?', (chat_id, verify_code))
        else:
            c.execute('UPDATE users SET verified = 1, verify_code = NULL WHERE verify_code = ?', (verify_code,))
        conn.commit()
        conn.close()
        return {"success": True, "bot_id": row["bot_id"]}

    conn.close()
    return {"success": False, "error": "Invalid or expired code"}

def get_user_by_chat_id(chat_id: int) -> Optional[Dict]:
    """Get user by Telegram chat ID"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE telegram_chat_id = ?', (chat_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_bot_id(bot_id: str) -> Optional[Dict]:
    """Get user by bot ID"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE bot_id = ?', (bot_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

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

def _sanitize_fts_query(text: str) -> str:
    """Build an OR query from text, stripping FTS5 special chars"""
    terms = text.replace(',', ' ').split()
    safe = []
    for t in terms:
        cleaned = ''.join(ch for ch in t if ch.isalnum() or ch == '_')
        if cleaned:
            safe.append(cleaned)
    return ' OR '.join(safe) if safe else ''

def _clean_results(rows, viewer_bot_id: str = None, seen_bot_ids: set = None) -> List[Dict]:
    """Clean profile rows: hide telegram, add seen flag, remove rank"""
    results = []
    for row in rows:
        profile = dict(row)
        profile.pop('rank', None)
        profile.pop('seen_flag', None)
        if not profile.get('telegram_public'):
            profile['telegram_handle'] = None
        if seen_bot_ids is not None:
            profile['seen'] = profile['bot_id'] in seen_bot_ids
        results.append(profile)
    return results

def _get_seen_bot_ids(viewer_bot_id: str) -> set:
    """Get set of bot_ids the viewer has already visited"""
    if not viewer_bot_id:
        return set()
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT DISTINCT visited_bot_id FROM visitors WHERE visitor_bot_id = ?',
              (viewer_bot_id,))
    ids = {row[0] for row in c.fetchall()}
    conn.close()
    return ids

def _browse_profiles(limit: int = 10, offset: int = 0,
                     viewer_bot_id: str = None) -> Dict[str, Any]:
    """Browse all profiles, unseen first then newest"""
    seen_ids = _get_seen_bot_ids(viewer_bot_id)
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM profiles')
    total = c.fetchone()[0]
    if viewer_bot_id and seen_ids:
        # Sort unseen first, then by recency
        placeholders = ','.join('?' for _ in seen_ids)
        c.execute(f'''
            SELECT *, CASE WHEN bot_id IN ({placeholders}) THEN 1 ELSE 0 END as seen_flag
            FROM profiles
            ORDER BY seen_flag ASC, updated_at DESC
            LIMIT ? OFFSET ?
        ''', (*seen_ids, limit, offset))
    else:
        c.execute('SELECT * FROM profiles ORDER BY updated_at DESC LIMIT ? OFFSET ?',
                  (limit, offset))
    rows = c.fetchall()
    conn.close()
    return {"results": _clean_results(rows, viewer_bot_id, seen_ids), "total": total}

def _fts_search(fts_query: str, limit: int = 10, offset: int = 0,
                viewer_bot_id: str = None) -> Dict[str, Any]:
    """Run FTS5 search with BM25 ranking, unseen profiles first"""
    seen_ids = _get_seen_bot_ids(viewer_bot_id)
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM profiles_fts WHERE profiles_fts MATCH ?', (fts_query,))
    total = c.fetchone()[0]

    # No match fallback: show browse results instead of empty
    if total == 0:
        conn.close()
        return _browse_profiles(limit, offset, viewer_bot_id)

    if viewer_bot_id and seen_ids:
        placeholders = ','.join('?' for _ in seen_ids)
        c.execute(f'''
            SELECT p.*,
                   bm25(profiles_fts) as rank,
                   CASE WHEN p.bot_id IN ({placeholders}) THEN 1 ELSE 0 END as seen_flag
            FROM profiles_fts
            JOIN profiles p ON p.id = profiles_fts.rowid
            WHERE profiles_fts MATCH ?
            ORDER BY seen_flag ASC, rank
            LIMIT ? OFFSET ?
        ''', (*seen_ids, fts_query, limit, offset))
    else:
        c.execute('''
            SELECT p.*, bm25(profiles_fts) as rank
            FROM profiles_fts
            JOIN profiles p ON p.id = profiles_fts.rowid
            WHERE profiles_fts MATCH ?
            ORDER BY rank
            LIMIT ? OFFSET ?
        ''', (fts_query, limit, offset))
    rows = c.fetchall()
    conn.close()
    return {"results": _clean_results(rows, viewer_bot_id, seen_ids), "total": total}

def search_profiles(query: str = None, interests: str = None, looking_for: str = None,
                    location: str = None, limit: int = 10, offset: int = 0,
                    viewer_bot_id: str = None) -> Dict[str, Any]:
    """Search profiles using FTS5 or browse all. Unseen profiles ranked first."""
    if query:
        fts_query = _sanitize_fts_query(query)
        if fts_query:
            return _fts_search(fts_query, limit, offset, viewer_bot_id)
    elif interests or looking_for or location:
        parts = ' '.join(filter(None, [interests, looking_for, location]))
        fts_query = _sanitize_fts_query(parts)
        if fts_query:
            return _fts_search(fts_query, limit, offset, viewer_bot_id)
    return _browse_profiles(limit, offset, viewer_bot_id)

def get_recommendations(bot_id: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    """Recommend profiles similar to the user's own profile. Unseen first."""
    profile = get_profile(bot_id)
    if not profile:
        return {"results": [], "total": 0}

    # Build query from user's own profile fields
    parts = ' '.join(filter(None, [
        profile.get('interests', ''),
        profile.get('looking_for', ''),
        profile.get('location', ''),
    ]))
    fts_query = _sanitize_fts_query(parts)
    if not fts_query:
        return _browse_profiles(limit, offset, bot_id)

    seen_ids = _get_seen_bot_ids(bot_id)
    conn = get_db()
    c = conn.cursor()

    # Count total (excluding self)
    c.execute('''
        SELECT COUNT(*) FROM profiles_fts
        JOIN profiles p ON p.id = profiles_fts.rowid
        WHERE profiles_fts MATCH ? AND p.bot_id != ?
    ''', (fts_query, bot_id))
    total = c.fetchone()[0]

    # No match fallback
    if total == 0:
        conn.close()
        result = _browse_profiles(limit, offset, bot_id)
        result["results"] = [p for p in result["results"] if p["bot_id"] != bot_id]
        return result

    # Get ranked results excluding self, unseen first
    if seen_ids:
        placeholders = ','.join('?' for _ in seen_ids)
        c.execute(f'''
            SELECT p.*,
                   bm25(profiles_fts) as rank,
                   CASE WHEN p.bot_id IN ({placeholders}) THEN 1 ELSE 0 END as seen_flag
            FROM profiles_fts
            JOIN profiles p ON p.id = profiles_fts.rowid
            WHERE profiles_fts MATCH ? AND p.bot_id != ?
            ORDER BY seen_flag ASC, rank
            LIMIT ? OFFSET ?
        ''', (*seen_ids, fts_query, bot_id, limit, offset))
    else:
        c.execute('''
            SELECT p.*, bm25(profiles_fts) as rank
            FROM profiles_fts
            JOIN profiles p ON p.id = profiles_fts.rowid
            WHERE profiles_fts MATCH ? AND p.bot_id != ?
            ORDER BY rank
            LIMIT ? OFFSET ?
        ''', (fts_query, bot_id, limit, offset))
    rows = c.fetchall()
    conn.close()

    return {"results": _clean_results(rows, bot_id, seen_ids), "total": total}

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

# === Messaging Functions ===

def send_message(from_bot_id: str, to_bot_id: str, content: str) -> Dict[str, Any]:
    """Send a message to a connected user"""
    # Check if connected
    if not are_connected(from_bot_id, to_bot_id):
        return {"success": False, "error": "You must be connected to send messages"}

    # Check content length
    if len(content) > 500:
        return {"success": False, "error": "Message too long (max 500 characters)"}

    conn = get_db()
    c = conn.cursor()

    c.execute('''
        INSERT INTO messages (from_bot_id, to_bot_id, content)
        VALUES (?, ?, ?)
    ''', (from_bot_id, to_bot_id, content))

    message_id = c.lastrowid
    conn.commit()
    conn.close()

    return {"success": True, "message_id": message_id}

def get_messages(bot_id: str, other_bot_id: str, limit: int = 50) -> List[Dict]:
    """Get conversation between two users"""
    # Check if connected
    if not are_connected(bot_id, other_bot_id):
        return []

    conn = get_db()
    c = conn.cursor()

    # Get messages in both directions
    c.execute('''
        SELECT * FROM messages
        WHERE (from_bot_id = ? AND to_bot_id = ?)
           OR (from_bot_id = ? AND to_bot_id = ?)
        ORDER BY created_at DESC
        LIMIT ?
    ''', (bot_id, other_bot_id, other_bot_id, bot_id, limit))

    rows = c.fetchall()

    # Mark messages as read
    c.execute('''
        UPDATE messages SET read = 1
        WHERE to_bot_id = ? AND from_bot_id = ? AND read = 0
    ''', (bot_id, other_bot_id))

    conn.commit()
    conn.close()

    return [dict(row) for row in rows]

def get_conversations(bot_id: str) -> List[Dict]:
    """Get list of all conversations with latest message"""
    conn = get_db()
    c = conn.cursor()

    # Get unique conversation partners with latest message
    c.execute('''
        SELECT
            CASE
                WHEN from_bot_id = ? THEN to_bot_id
                ELSE from_bot_id
            END as other_bot_id,
            content as last_message,
            created_at as last_message_at,
            CASE WHEN to_bot_id = ? AND read = 0 THEN 1 ELSE 0 END as unread
        FROM messages
        WHERE from_bot_id = ? OR to_bot_id = ?
        ORDER BY created_at DESC
    ''', (bot_id, bot_id, bot_id, bot_id))

    rows = c.fetchall()
    conn.close()

    # Deduplicate to get latest per conversation
    seen = set()
    conversations = []
    for row in rows:
        other_id = row['other_bot_id']
        if other_id not in seen:
            seen.add(other_id)
            conversations.append(dict(row))

    return conversations

def get_unread_messages(bot_id: str) -> List[Dict]:
    """Get unread messages for notifications"""
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT m.*, p.name as from_name
        FROM messages m
        JOIN profiles p ON m.from_bot_id = p.bot_id
        WHERE m.to_bot_id = ? AND m.read = 0
        ORDER BY m.created_at DESC
    ''', (bot_id,))

    rows = c.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def get_accepted_connections(bot_id: str) -> List[Dict]:
    """Get connections that were accepted (for notifying the sender)"""
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT c.*, p.name, p.interests, p.telegram_handle
        FROM connections c
        JOIN profiles p ON c.to_bot_id = p.bot_id
        WHERE c.from_bot_id = ? AND c.status = 'accepted'
        ORDER BY c.responded_at DESC
    ''', (bot_id,))

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
