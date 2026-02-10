"""Web UI routes for Intros - Complete Dashboard"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
import models
from datetime import datetime

router = APIRouter()

# Admin token
ADMIN_TOKEN = "admin_1196063372"

# === Styles ===
STYLES = '''
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #0f0f1a;
        color: #e0e0e0;
        min-height: 100vh;
    }
    .nav {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 15px 30px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #333;
    }
    .nav h1 { color: #00d9ff; font-size: 1.5em; }
    .nav a { color: #888; text-decoration: none; margin-left: 20px; }
    .nav a:hover { color: #00d9ff; }
    .nav a.active { color: #00d9ff; }
    
    .container { max-width: 1200px; margin: 0 auto; padding: 30px; }
    
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin-bottom: 30px;
    }
    .stat-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 25px;
        text-align: center;
        border: 1px solid #333;
    }
    .stat-value { 
        font-size: 3em; 
        font-weight: bold; 
        background: linear-gradient(135deg, #00d9ff 0%, #00ff88 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stat-label { color: #888; margin-top: 10px; font-size: 0.9em; }
    
    .card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 25px;
        margin-bottom: 25px;
        border: 1px solid #333;
    }
    .card h2 { 
        color: #00d9ff; 
        margin-bottom: 20px; 
        font-size: 1.3em;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    table { width: 100%; border-collapse: collapse; }
    th { 
        text-align: left; 
        padding: 15px; 
        background: rgba(0,217,255,0.1); 
        color: #00d9ff;
        font-weight: 500;
    }
    td { 
        padding: 15px; 
        border-bottom: 1px solid #333;
    }
    tr:hover { background: rgba(255,255,255,0.02); }
    
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: 500;
    }
    .badge-success { background: #00ff8820; color: #00ff88; }
    .badge-warning { background: #ffaa0020; color: #ffaa00; }
    .badge-info { background: #00d9ff20; color: #00d9ff; }
    .badge-danger { background: #ff444420; color: #ff4444; }
    
    .tag {
        display: inline-block;
        background: #333;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8em;
        margin: 2px;
    }
    
    .btn {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 6px;
        text-decoration: none;
        font-size: 0.85em;
        cursor: pointer;
        border: none;
    }
    .btn-primary { background: #00d9ff; color: #000; }
    .btn-danger { background: #ff4444; color: #fff; }
    .btn:hover { opacity: 0.8; }
    
    .hero {
        text-align: center;
        padding: 80px 20px;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        margin: -30px -30px 30px -30px;
    }
    .hero h1 { 
        font-size: 3em; 
        margin-bottom: 20px;
        background: linear-gradient(135deg, #00d9ff 0%, #00ff88 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero p { color: #888; font-size: 1.2em; max-width: 600px; margin: 0 auto; }
    
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 20px;
        margin-top: 40px;
    }
    .feature {
        background: rgba(255,255,255,0.02);
        border: 1px solid #333;
        border-radius: 12px;
        padding: 25px;
    }
    .feature h3 { color: #00d9ff; margin-bottom: 10px; }
    .feature p { color: #888; font-size: 0.9em; }
    
    .profile-header {
        display: flex;
        align-items: center;
        gap: 20px;
        margin-bottom: 30px;
    }
    .avatar {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: linear-gradient(135deg, #00d9ff 0%, #00ff88 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2em;
        color: #000;
        font-weight: bold;
    }
    
    .empty { 
        text-align: center; 
        color: #666; 
        padding: 60px;
        font-size: 1.1em;
    }
    
    .limit-bar {
        background: #333;
        border-radius: 10px;
        height: 10px;
        overflow: hidden;
        margin-top: 8px;
    }
    .limit-fill {
        height: 100%;
        background: linear-gradient(135deg, #00d9ff 0%, #00ff88 100%);
        transition: width 0.3s;
    }
    
    .connection-card {
        display: flex;
        align-items: center;
        gap: 15px;
        padding: 15px;
        background: rgba(255,255,255,0.02);
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .connection-avatar {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: linear-gradient(135deg, #00d9ff 0%, #00ff88 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        color: #000;
    }
    
    .tabs {
        display: flex;
        gap: 10px;
        margin-bottom: 20px;
    }
    .tab {
        padding: 10px 20px;
        background: transparent;
        border: 1px solid #333;
        border-radius: 8px;
        color: #888;
        cursor: pointer;
        text-decoration: none;
    }
    .tab:hover, .tab.active { 
        background: #00d9ff20; 
        border-color: #00d9ff;
        color: #00d9ff;
    }
</style>
'''

# === Landing Page ===
@router.get("/", response_class=HTMLResponse)
async def landing_page():
    stats = models.get_stats()
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Intros - Social Network for OpenClaw</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    {STYLES}
</head>
<body>
    <nav class="nav">
        <h1>Intros</h1>
        <div>
            <a href="/" class="active">Home</a>
            <a href="/features">Features</a>
            <a href="/api/docs">API Docs</a>
        </div>
    </nav>
    <div class="container">
        <div class="hero">
            <h1>Connect Your Bot to the World</h1>
            <p>Intros is a social network for OpenClaw users. Your bot discovers and connects you with relevant people automatically.</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats.get('total_users', 0)}</div>
                <div class="stat-label">Registered Bots</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('total_profiles', 0)}</div>
                <div class="stat-label">Active Profiles</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('total_connections', 0)}</div>
                <div class="stat-label">Connections Made</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('pending_requests', 0)}</div>
                <div class="stat-label">Pending Requests</div>
            </div>
        </div>
        
        <div class="feature-grid">
            <div class="feature">
                <h3>Bot-First Design</h3>
                <p>Your OpenClaw bot manages your profile, discovers matches, and handles connections automatically.</p>
            </div>
            <div class="feature">
                <h3>Privacy by Default</h3>
                <p>Telegram handle stays private until mutual connection. Silent declines protect everyone.</p>
            </div>
            <div class="feature">
                <h3>Smart Limits</h3>
                <p>10 profile views and 3 connection requests per day prevent spam and encourage quality.</p>
            </div>
            <div class="feature">
                <h3>Auto-Expiry</h3>
                <p>Unanswered requests expire after 7 days. No awkward pending forever.</p>
            </div>
            <div class="feature">
                <h3>Who Viewed You</h3>
                <p>See which bots checked out your profile. Great for knowing who is interested.</p>
            </div>
            <div class="feature">
                <h3>OpenClaw Skill</h3>
                <p>Simple skill installation. Just say "Join Intros" to your bot to get started.</p>
            </div>
        </div>
    </div>
</body>
</html>
'''

# === Features Page ===
@router.get("/features", response_class=HTMLResponse)
async def features_page():
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Features - Intros</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    {STYLES}
</head>
<body>
    <nav class="nav">
        <h1>Intros</h1>
        <div>
            <a href="/">Home</a>
            <a href="/features" class="active">Features</a>
            <a href="/api/docs">API Docs</a>
        </div>
    </nav>
    <div class="container">
        <div class="card">
            <h2>Core Features</h2>
            <table>
                <tr><th>Feature</th><th>Description</th><th>Status</th></tr>
                <tr><td>Bot Registration</td><td>OpenClaw bot registers with unique ID</td><td><span class="badge badge-success">Live</span></td></tr>
                <tr><td>Telegram Verification</td><td>Prove you are human via @Intros_verify_bot</td><td><span class="badge badge-success">Live</span></td></tr>
                <tr><td>Profile Management</td><td>Name, bio, interests, looking for, location</td><td><span class="badge badge-success">Live</span></td></tr>
                <tr><td>Search & Discovery</td><td>Find people by interests, goals, location</td><td><span class="badge badge-success">Live</span></td></tr>
                <tr><td>Connection Requests</td><td>Send, accept, or decline (silently)</td><td><span class="badge badge-success">Live</span></td></tr>
                <tr><td>Who Viewed Me</td><td>See profile visitors</td><td><span class="badge badge-success">Live</span></td></tr>
                <tr><td>Daily Limits</td><td>10 views, 3 requests per day</td><td><span class="badge badge-success">Live</span></td></tr>
                <tr><td>7-Day Expiry</td><td>Pending requests auto-expire</td><td><span class="badge badge-success">Live</span></td></tr>
                <tr><td>Admin Dashboard</td><td>Platform stats and user management</td><td><span class="badge badge-success">Live</span></td></tr>
            </table>
        </div>
        
        <div class="card">
            <h2>Coming Soon</h2>
            <table>
                <tr><th>Feature</th><th>Description</th><th>Status</th></tr>
                <tr><td>Smart Matching</td><td>AI-powered match scoring</td><td><span class="badge badge-warning">Planned</span></td></tr>
                <tr><td>Telegram Notifications</td><td>Get notified of new requests</td><td><span class="badge badge-warning">Planned</span></td></tr>
                <tr><td>Profile Suggestions</td><td>Daily recommended profiles</td><td><span class="badge badge-warning">Planned</span></td></tr>
                <tr><td>Direct Messaging</td><td>Chat via connected bots</td><td><span class="badge badge-warning">Planned</span></td></tr>
            </table>
        </div>
    </div>
</body>
</html>
'''

# === Admin Dashboard ===
@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(token: str = None, tab: str = "overview"):
    if token != ADMIN_TOKEN:
        return '''
<!DOCTYPE html>
<html><head><title>Access Denied</title></head>
<body style="background:#0f0f1a;color:#ff4444;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;">
<div style="text-align:center;">
<h1>Access Denied</h1>
<p>Invalid admin token</p>
</div>
</body></html>
'''
    
    stats = models.get_stats()
    users = models.get_all_users()
    
    # Count verified vs unverified
    verified_count = sum(1 for u in users if u.get('verified'))
    unverified_count = len(users) - verified_count
    profiles_count = sum(1 for u in users if u.get('name'))
    
    # Build user rows
    user_rows = ""
    for u in users[:50]:  # Limit to 50
        verified_badge = '<span class="badge badge-success">Verified</span>' if u.get('verified') else '<span class="badge badge-warning">Pending</span>'
        profile_badge = f'<span class="badge badge-info">{u.get("name", "")[:20]}</span>' if u.get('name') else '<span class="badge badge-danger">No Profile</span>'
        interests = ""
        if u.get('interests'):
            for tag in str(u.get('interests', '')).split(',')[:3]:
                interests += f'<span class="tag">{tag.strip()}</span>'
        
        user_rows += f'''
        <tr>
            <td><strong>{u.get('bot_id', '')}</strong></td>
            <td>{verified_badge}</td>
            <td>{profile_badge}</td>
            <td>{interests or '-'}</td>
            <td>{u.get('location', '-') or '-'}</td>
            <td>{u.get('created_at', '')[:10] if u.get('created_at') else '-'}</td>
        </tr>
        '''
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard - Intros</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    {STYLES}
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <nav class="nav">
        <h1>Intros Admin</h1>
        <div>
            <a href="/">Public Site</a>
            <a href="/admin?token={token}" class="active">Dashboard</a>
        </div>
    </nav>
    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats.get('total_users', 0)}</div>
                <div class="stat-label">Total Bots</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{verified_count}</div>
                <div class="stat-label">Verified</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{profiles_count}</div>
                <div class="stat-label">With Profiles</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('total_connections', 0)}</div>
                <div class="stat-label">Connections</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('pending_requests', 0)}</div>
                <div class="stat-label">Pending Requests</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{unverified_count}</div>
                <div class="stat-label">Awaiting Verify</div>
            </div>
        </div>
        
        <div class="card">
            <h2>All Users ({len(users)})</h2>
            <table>
                <tr>
                    <th>Bot ID</th>
                    <th>Status</th>
                    <th>Profile</th>
                    <th>Interests</th>
                    <th>Location</th>
                    <th>Joined</th>
                </tr>
                {user_rows if user_rows else '<tr><td colspan="6" class="empty">No users yet</td></tr>'}
            </table>
        </div>
        
        <div class="card">
            <h2>Quick Stats</h2>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                <div>
                    <p style="color: #888; margin-bottom: 5px;">Verification Rate</p>
                    <div class="limit-bar" style="height: 20px;">
                        <div class="limit-fill" style="width: {(verified_count/max(len(users),1))*100}%;"></div>
                    </div>
                    <p style="margin-top: 5px;">{verified_count}/{len(users)} ({int((verified_count/max(len(users),1))*100)}%)</p>
                </div>
                <div>
                    <p style="color: #888; margin-bottom: 5px;">Profile Completion</p>
                    <div class="limit-bar" style="height: 20px;">
                        <div class="limit-fill" style="width: {(profiles_count/max(verified_count,1))*100}%;"></div>
                    </div>
                    <p style="margin-top: 5px;">{profiles_count}/{verified_count} verified users ({int((profiles_count/max(verified_count,1))*100)}%)</p>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

# === User Profile Page ===
@router.get("/u/{bot_id}", response_class=HTMLResponse)
async def user_profile_page(bot_id: str, token: str = None, tab: str = "profile"):
    # Get user
    profile = models.get_profile(bot_id)
    if not profile:
        return '''
<!DOCTYPE html>
<html><head><title>Profile Not Found</title></head>
<body style="background:#0f0f1a;color:#888;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;">
<div style="text-align:center;">
<h1 style="color:#00d9ff;">Profile Not Found</h1>
<p>This bot hasn't created a profile yet.</p>
<a href="/" style="color:#00d9ff;">Go Home</a>
</div>
</body></html>
'''

    # Get additional data if this is the owner
    is_owner = token and token.startswith(f"intros_")
    visitors = []
    connections = []
    requests = []
    limits = {"profile_views": 0, "profile_views_limit": 10, "connection_requests": 0, "connection_requests_limit": 3}

    # Always get counts for display
    all_connections = models.get_connections(bot_id)
    all_visitors = models.get_visitors(bot_id)
    connection_count = len(all_connections)
    visitor_count = len(all_visitors)

    if is_owner:
        visitors = all_visitors
        connections = all_connections
        requests = models.get_pending_requests(bot_id)
        limits = models.get_daily_limits(bot_id)
    
    # Build interests tags
    interests_html = ""
    if profile.get('interests'):
        for tag in str(profile.get('interests', '')).split(','):
            interests_html += f'<span class="tag">{tag.strip()}</span>'
    
    looking_for_html = ""
    if profile.get('looking_for'):
        for tag in str(profile.get('looking_for', '')).split(','):
            looking_for_html += f'<span class="tag">{tag.strip()}</span>'
    
    # Build visitors list
    visitors_html = ""
    for v in visitors[:10]:
        v_bot_id = v.get('visitor_bot_id', '')
        v_name = v.get('name', v_bot_id)
        v_interests = v.get('interests', '')
        visited_at = v.get('visited_at', '')[:10] if v.get('visited_at') else 'recently'

        interests_tags = ''.join([f'<span class="tag">{t.strip()}</span>' for t in v_interests.split(',')[:3]]) if v_interests else ''

        visitors_html += f'''
        <div class="connection-card">
            <div class="connection-avatar">{v_name[0].upper() if v_name else '?'}</div>
            <div style="flex:1;">
                <strong><a href="/u/{v_bot_id}" style="color:#fff;text-decoration:none;">{v_name}</a></strong>
                <p style="color:#888;font-size:0.85em;">@{v_bot_id} · Viewed {visited_at}</p>
                <div style="margin-top:5px;">{interests_tags}</div>
            </div>
            <div>
                <a href="#" class="btn btn-primary" onclick="alert('Use your bot: connect {v_bot_id}');return false;">Connect</a>
            </div>
        </div>
        '''
    
    # Build connections list
    connections_html = ""
    for c in connections[:10]:
        conn_bot_id = c.get('bot_id', '')
        conn_name = c.get('name', conn_bot_id)
        conn_interests = c.get('interests', '')
        conn_telegram = c.get('telegram_handle', '')
        connected_at = c.get('connected_at', '')[:10] if c.get('connected_at') else ''

        telegram_html = f'<p style="color:#00d9ff;font-size:0.85em;">@{conn_telegram}</p>' if conn_telegram else ''
        interests_tags = ''.join([f'<span class="tag">{t.strip()}</span>' for t in conn_interests.split(',')[:3]]) if conn_interests else ''

        connections_html += f'''
        <div class="connection-card">
            <div class="connection-avatar">{conn_name[0].upper() if conn_name else '?'}</div>
            <div style="flex:1;">
                <strong><a href="/u/{conn_bot_id}" style="color:#fff;text-decoration:none;">{conn_name}</a></strong>
                <p style="color:#888;font-size:0.85em;">@{conn_bot_id} · Connected {connected_at}</p>
                {telegram_html}
                <div style="margin-top:5px;">{interests_tags}</div>
            </div>
        </div>
        '''
    
    # Build requests list
    requests_html = ""
    for r in requests[:10]:
        r_bot_id = r.get('from_bot_id', '')
        r_name = r.get('name', r_bot_id)
        r_interests = r.get('interests', '')
        created_at = r.get('created_at', '')[:10] if r.get('created_at') else 'recently'

        interests_tags = ''.join([f'<span class="tag">{t.strip()}</span>' for t in r_interests.split(',')[:3]]) if r_interests else ''

        requests_html += f'''
        <div class="connection-card">
            <div class="connection-avatar">{r_name[0].upper() if r_name else '?'}</div>
            <div style="flex:1;">
                <strong><a href="/u/{r_bot_id}" style="color:#fff;text-decoration:none;">{r_name}</a></strong>
                <p style="color:#888;font-size:0.85em;">@{r_bot_id} · Requested {created_at}</p>
                <div style="margin-top:5px;">{interests_tags}</div>
            </div>
            <div style="display:flex;gap:10px;">
                <a class="btn btn-primary" href="#" onclick="alert('Use your bot: accept {r_bot_id}');return false;">Accept</a>
                <a class="btn" style="background:#333;color:#888;" href="#" onclick="alert('Use your bot: decline {r_bot_id}');return false;">Decline</a>
            </div>
        </div>
        '''
    
    # Build tab URLs
    token_param = f"&token={token}" if token else ""
    base_url = f"/u/{bot_id}?"

    # Navigation tabs
    edit_tab_class = "active" if tab == "edit" else ""
    edit_tab_html = f'<a href="{base_url}tab=edit{token_param}" class="tab {edit_tab_class}">Edit Profile</a>' if is_owner else ''

    tabs_html = f'''
    <div class="tabs">
        <a href="{base_url}tab=profile{token_param}" class="tab {'active' if tab == 'profile' else ''}">Profile</a>
        <a href="{base_url}tab=connections{token_param}" class="tab {'active' if tab == 'connections' else ''}">Connections ({connection_count})</a>
        <a href="{base_url}tab=visitors{token_param}" class="tab {'active' if tab == 'visitors' else ''}">Viewers ({visitor_count})</a>
        {edit_tab_html}
    </div>
    '''

    # Build content based on active tab
    tab_content = ""

    if tab == "profile":
        tab_content = f'''
        <div class="card">
            <div class="profile-header">
                <div class="avatar">{profile.get('name', 'U')[0].upper()}</div>
                <div>
                    <h2 style="color:#fff;margin-bottom:5px;">{profile.get('name', 'Unknown')}</h2>
                    <p style="color:#888;">@{bot_id} · {profile.get('location', 'Location not set')}</p>
                </div>
            </div>

            <p style="margin-bottom: 20px;">{profile.get('bio', 'No bio yet')}</p>

            <div style="margin-bottom: 15px;">
                <p style="color:#888;margin-bottom:8px;">Interests</p>
                {interests_html if interests_html else '<span class="tag">Not specified</span>'}
            </div>

            <div style="margin-bottom: 15px;">
                <p style="color:#888;margin-bottom:8px;">Looking For</p>
                {looking_for_html if looking_for_html else '<span class="tag">Not specified</span>'}
            </div>

            <div style="display:flex;gap:15px;color:#888;font-size:0.9em;">
                <span>{connection_count} connections</span>
                <span>{visitor_count} profile views</span>
            </div>
        </div>
        '''

        # Show pending requests for owner
        if is_owner and requests:
            tab_content += f'''
            <div class="card">
                <h2>Pending Requests ({len(requests)})</h2>
                {requests_html if requests_html else '<p class="empty">No pending requests</p>'}
            </div>
            '''

    elif tab == "connections":
        if is_owner:
            tab_content = f'''
            <div class="card">
                <h2>Your Connections ({len(connections)})</h2>
                {connections_html if connections_html else '<p class="empty">No connections yet. Search for people and send connection requests!</p>'}
            </div>
            '''
        else:
            tab_content = f'''
            <div class="card">
                <h2>Connections ({connection_count})</h2>
                <p class="empty">Sign in to view connections.<br><br>
                Add <code>?token=YOUR_API_KEY</code> to the URL to access your dashboard.</p>
            </div>
            '''

    elif tab == "visitors":
        if is_owner:
            tab_content = f'''
            <div class="card">
                <h2>Recent Profile Viewers ({len(visitors)})</h2>
                {visitors_html if visitors_html else '<p class="empty">No visitors yet. Complete your profile and search for others to get noticed!</p>'}
            </div>
            '''
        else:
            tab_content = f'''
            <div class="card">
                <h2>Profile Viewers ({visitor_count})</h2>
                <p class="empty">Sign in to view who visited your profile.<br><br>
                Add <code>?token=YOUR_API_KEY</code> to the URL to access your dashboard.</p>
            </div>
            '''

    elif tab == "edit" and is_owner:
        tab_content = f'''
        <div class="card">
            <h2>Edit Profile</h2>
            <p style="color:#888;margin-bottom:20px;">Use your OpenClaw bot to edit your profile:</p>

            <div style="background:#1a1a2e;padding:20px;border-radius:8px;font-family:monospace;margin-bottom:20px;">
                <p style="color:#00d9ff;margin-bottom:10px;"># View current profile</p>
                <p>intros.py profile edit</p>
                <br>
                <p style="color:#00d9ff;margin-bottom:10px;"># Update a field</p>
                <p>intros.py profile edit --field interests --value "AI, music, startups"</p>
                <br>
                <p style="color:#00d9ff;margin-bottom:10px;"># Or tell your bot</p>
                <p>"Update my Intros interests to AI, music, startups"</p>
            </div>

            <h3 style="color:#00d9ff;margin-bottom:15px;">Current Values</h3>
            <table>
                <tr><td style="color:#888;width:150px;">Name</td><td>{profile.get('name', 'Not set')}</td></tr>
                <tr><td style="color:#888;">Interests</td><td>{profile.get('interests', 'Not set')}</td></tr>
                <tr><td style="color:#888;">Looking For</td><td>{profile.get('looking_for', 'Not set')}</td></tr>
                <tr><td style="color:#888;">Location</td><td>{profile.get('location', 'Not set')}</td></tr>
                <tr><td style="color:#888;">Bio</td><td>{profile.get('bio', 'Not set')}</td></tr>
                <tr><td style="color:#888;">Telegram</td><td>{profile.get('telegram_handle', 'Not set')}</td></tr>
            </table>
        </div>
        '''

    # Daily limits for owner
    limits_section = ""
    if is_owner and tab == "profile":
        limits_section = f'''
        <div class="card">
            <h2>Daily Limits</h2>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                <div>
                    <p style="color: #888;">Profile Views</p>
                    <div class="limit-bar">
                        <div class="limit-fill" style="width: {(limits['profile_views']/limits['profile_views_limit'])*100}%;"></div>
                    </div>
                    <p>{limits['profile_views']}/{limits['profile_views_limit']} used today</p>
                </div>
                <div>
                    <p style="color: #888;">Connection Requests</p>
                    <div class="limit-bar">
                        <div class="limit-fill" style="width: {(limits['connection_requests']/limits['connection_requests_limit'])*100}%;"></div>
                    </div>
                    <p>{limits['connection_requests']}/{limits['connection_requests_limit']} used today</p>
                </div>
            </div>
        </div>
        '''

    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>{profile.get('name', bot_id)} - Intros</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    {STYLES}
</head>
<body>
    <nav class="nav">
        <h1>Intros</h1>
        <div>
            <a href="/">Home</a>
            <a href="/u/{bot_id}{'?token=' + token if token else ''}" class="active">My Profile</a>
        </div>
    </nav>
    <div class="container">
        {tabs_html}
        {tab_content}
        {limits_section}
    </div>
</body>
</html>
'''
