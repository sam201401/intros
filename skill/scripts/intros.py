#!/usr/bin/env python3
"""Intros CLI - OpenClaw Skill for Social Networking"""

import argparse
import json
import os
import sys
import requests
from pathlib import Path

# Configuration
API_URL = "https://api.openbreeze.ai"

# Use OPENCLAW_STATE_DIR to support multiple OpenClaw instances
# Each instance gets its own config file
STATE_DIR = os.environ.get('OPENCLAW_STATE_DIR', str(Path.home() / ".openclaw"))
CONFIG_PATH = Path(STATE_DIR) / "skills" / "intros" / "config.json"

def load_config():
    """Load saved configuration"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}

def save_config(config):
    """Save configuration"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def get_headers():
    """Get auth headers"""
    config = load_config()
    api_key = config.get('api_key')
    if not api_key:
        print(json.dumps({"error": "Not registered. Run 'intros.py register' first."}))
        sys.exit(1)
    return {"Authorization": f"Bearer {api_key}"}

def api_call(method, endpoint, data=None, params=None):
    """Make API call"""
    url = f"{API_URL}{endpoint}"
    headers = get_headers() if endpoint not in ['/register', '/health'] else {}

    try:
        if method == 'GET':
            resp = requests.get(url, headers=headers, params=params, timeout=30)
        elif method == 'POST':
            resp = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == 'PATCH':
            resp = requests.patch(url, headers=headers, json=data, timeout=30)
        elif method == 'DELETE':
            resp = requests.delete(url, headers=headers, timeout=30)

        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": resp.json().get('detail', resp.text)}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to Intros server"}
    except Exception as e:
        return {"error": str(e)}

# === Formatting Helper Functions ===

def relative_time(timestamp_str):
    """Convert timestamp to relative time like '2h ago', '1d ago'"""
    from datetime import datetime
    if not timestamp_str:
        return "unknown"

    try:
        # Handle SQLite timestamp format
        ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00').split('+')[0])
        now = datetime.now()
        diff = now - ts

        seconds = diff.total_seconds()
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            mins = int(seconds / 60)
            return f"{mins}m ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours}h ago"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days}d ago"
        else:
            weeks = int(seconds / 604800)
            return f"{weeks}w ago"
    except Exception:
        return timestamp_str[:10] if timestamp_str else "unknown"

def print_box(title, lines, width=45):
    """Print content in a nice ASCII box"""
    output = []
    output.append("+" + "-" * (width - 2) + "+")
    # Center the title
    title_padded = title.center(width - 4)
    output.append("|" + " " + title_padded + " " + "|")
    output.append("+" + "-" * (width - 2) + "+")
    for line in lines:
        # Truncate if too long
        if len(line) > width - 4:
            line = line[:width - 7] + "..."
        padded = line.ljust(width - 4)
        output.append("| " + padded + " |")
    output.append("+" + "-" * (width - 2) + "+")
    return "\n".join(output)

def format_profile_section(profile):
    """Format profile data for display"""
    if not profile or not profile.get('name'):
        return ["No profile yet. Create one with:", "  profile create --name 'Your Name'"]

    lines = []
    lines.append(f"Username: @{profile.get('bot_id', 'unknown')}")
    lines.append(f"Name: {profile.get('name', 'Not set')}")
    if profile.get('interests'):
        lines.append(f"Interests: {profile['interests']}")
    if profile.get('looking_for'):
        lines.append(f"Looking for: {profile['looking_for']}")
    if profile.get('location'):
        lines.append(f"Location: {profile['location']}")
    if profile.get('bio'):
        lines.append(f"Bio: {profile['bio']}")
    if profile.get('telegram_handle'):
        visibility = "public" if profile.get('telegram_public') else "private"
        lines.append(f"Telegram: @{profile['telegram_handle']} ({visibility})")
    return lines

def format_connections_list(connections, show_telegram=True):
    """Format connections for display"""
    if not connections:
        return ["No connections yet."]

    lines = []
    for conn in connections:
        name = conn.get('name', conn.get('bot_id', 'Unknown'))
        bot_id = conn.get('bot_id', '')
        interests = conn.get('interests', '')

        line = f"* {bot_id} - {name}"
        if interests:
            # Truncate interests if too long
            interests_short = interests[:20] + "..." if len(interests) > 20 else interests
            line += f" ({interests_short})"
        lines.append(line)

        if show_telegram and conn.get('telegram_handle'):
            lines.append(f"  Telegram: @{conn['telegram_handle']}")
    return lines

def format_visitors_list(visitors):
    """Format visitors for display with relative timestamps"""
    if not visitors:
        return ["No profile visitors yet."]

    lines = []
    for v in visitors:
        bot_id = v.get('visitor_bot_id', 'unknown')
        name = v.get('name', bot_id)
        visited_at = relative_time(v.get('visited_at'))
        lines.append(f"* {bot_id} - {name} ({visited_at})")
    return lines

# === Helper Functions ===

def ensure_cron_exists(silent=False, force_recreate=False):
    """Ensure cron job exists with correct script path. Returns True if exists/created, False if failed."""
    import subprocess

    # Get the actual script path (where this script is running from)
    script_path = Path(__file__).resolve()
    script_path_str = str(script_path)

    # Check if cron already exists
    should_create = False
    try:
        result = subprocess.run(
            ['openclaw', 'cron', 'list', '--json'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            jobs = data.get('jobs', []) if isinstance(data, dict) else data

            # Find existing intros-notifications cron
            found_cron = None
            for job in jobs:
                if job.get('name') == 'intros-notifications':
                    found_cron = job
                    break

            if found_cron:
                job_id = found_cron.get('id')
                cron_has_correct_path = script_path_str in str(found_cron.get('payload', {}).get('message', ''))

                if cron_has_correct_path and not force_recreate:
                    if not silent:
                        print(json.dumps({
                            "success": True,
                            "message": "Intros notifications already set up!",
                            "cron_id": job_id
                        }))
                    return True
                else:
                    # Wrong path - delete and recreate
                    subprocess.run(
                        ['openclaw', 'cron', 'delete', job_id],
                        capture_output=True, text=True, timeout=10
                    )
                    should_create = True
            else:
                # No existing cron found
                should_create = True
        else:
            # Command failed but didn't throw - safe to create
            should_create = True
    except Exception as e:
        # If we can't check, DON'T create (prevents duplicates)
        if not silent:
            print(json.dumps({"error": f"Could not check cron status: {e}"}))
        return False

    if not should_create:
        return True

    # Create cron job with the actual script path
    try:
        result = subprocess.run([
            'openclaw', 'cron', 'add',
            '--name', 'intros-notifications',
            '--cron', '* * * * *',
            '--session', 'isolated',
            '--wake', 'now',
            '--announce',
            '--message', f'Run: python3 {script_path} check-notifications — If no output, DO NOT RESPOND AT ALL. Only relay actual notification text.',
            '--json'
        ], capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            if not silent:
                job_data = json.loads(result.stdout) if result.stdout.strip() else {}
                print(json.dumps({
                    "success": True,
                    "message": "Intros notifications enabled!",
                    "cron_id": job_data.get('id'),
                    "schedule": "Every minute"
                }))
            return True
        else:
            if not silent:
                print(json.dumps({
                    "error": "Failed to register cron job",
                    "details": result.stderr or result.stdout
                }))
            return False
    except FileNotFoundError:
        if not silent:
            print(json.dumps({
                "error": "openclaw CLI not found. Make sure OpenClaw is installed."
            }))
        return False
    except Exception as e:
        if not silent:
            print(json.dumps({"error": str(e)}))
        return False

# === Commands ===

def cmd_register(args):
    """Register a new bot"""
    config = load_config()

    # IMPORTANT: Never re-register if config exists - prevents duplicate accounts
    if config.get('api_key') and config.get('bot_id'):
        # Silent fix: if user has profile but cron missing, create it
        profile_result = api_call('GET', '/profile')
        if 'error' not in profile_result and profile_result.get('name'):
            ensure_cron_exists(silent=True)

        print(json.dumps({
            "message": "Already registered",
            "bot_id": config.get('bot_id'),
            "hint": "If you need to re-register, first delete the config file manually"
        }))
        return

    # Require bot_id (username) to be provided
    if not args.bot_id:
        print(json.dumps({
            "error": "Username required. Use: register --bot-id your_username",
            "hint": "Choose a unique username (lowercase, no spaces)"
        }))
        return

    # Validate username format
    bot_id = args.bot_id.lower().strip()
    if not bot_id.replace('_', '').isalnum():
        print(json.dumps({
            "error": "Invalid username. Use only letters, numbers, and underscores.",
            "hint": "Example: sam_dev, alice123"
        }))
        return

    telegram_id = args.telegram_id or os.environ.get('TELEGRAM_USER_ID', '')
    
    url = f"{API_URL}/register"
    try:
        resp = requests.post(url, json={"bot_id": bot_id, "telegram_id": telegram_id}, timeout=30)
        result = resp.json()
        
        if resp.status_code == 200 and result.get('success'):
            config['api_key'] = result['api_key']
            config['bot_id'] = bot_id
            config['verify_code'] = result['verify_code']
            save_config(config)

            print(json.dumps({
                "success": True,
                "message": f"Registered! Send '{result['verify_code']}' to @Intros_verify_bot on Telegram to verify.",
                "verify_code": result['verify_code'],
                "bot_id": bot_id
            }))
            # Note: Cron is created after profile setup, not here
        else:
            print(json.dumps({"error": result.get('detail', 'Registration failed')}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))

def cmd_verify_status(args):
    """Check verification status"""
    result = api_call('GET', '/verify-status')
    print(json.dumps(result))

def cmd_profile_create(args):
    """Create or update profile"""
    data = {
        "name": args.name,
        "interests": args.interests,
        "looking_for": args.looking_for,
        "location": args.location,
        "bio": args.bio,
        "telegram_handle": args.telegram,
        "telegram_public": args.telegram_public
    }
    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}
    
    result = api_call('POST', '/profile', data)
    if result.get('success'):
        # Silently ensure cron exists after profile is set up
        ensure_cron_exists(silent=True)
        print(json.dumps({"success": True, "message": "Profile updated!"}))
    else:
        print(json.dumps(result))

def cmd_profile_me(args):
    """View my profile"""
    result = api_call('GET', '/profile')
    print(json.dumps(result))

def cmd_me(args):
    """Show full dashboard: profile, connections, visitors"""
    result = api_call('GET', '/me')
    if 'error' in result:
        print(json.dumps(result))
        return

    profile = result.get('profile', {})
    connections = result.get('connections', [])
    visitors = result.get('visitors', [])

    output = []

    # Profile section
    profile_lines = format_profile_section(profile)
    output.append(print_box("MY INTROS PROFILE", profile_lines))

    # Connections section
    conn_title = f"CONNECTIONS ({len(connections)})"
    conn_lines = format_connections_list(connections, show_telegram=True)
    output.append(print_box(conn_title, conn_lines))

    # Visitors section
    visitors_title = f"RECENT VIEWERS ({len(visitors)})"
    visitors_lines = format_visitors_list(visitors)
    output.append(print_box(visitors_title, visitors_lines))

    # Help hints
    output.append("")
    output.append("Commands:")
    output.append("  profile edit          - Edit your profile")
    output.append("  connect <username>    - Connect with a viewer")
    output.append("  search --interests X  - Find new people")

    print("\n".join(output))

def cmd_profile_edit(args):
    """Interactive profile edit mode"""
    # First fetch current profile
    result = api_call('GET', '/profile')
    if 'error' in result:
        print(json.dumps(result))
        return

    if not result.get('name'):
        print("No profile found. Create one first with:")
        print("  profile create --name 'Your Name' --interests 'your, interests'")
        return

    current = result
    print("\nCurrent profile:")
    print(f"  1. Name: {current.get('name', 'Not set')}")
    print(f"  2. Interests: {current.get('interests', 'Not set')}")
    print(f"  3. Looking for: {current.get('looking_for', 'Not set')}")
    print(f"  4. Location: {current.get('location', 'Not set')}")
    print(f"  5. Bio: {current.get('bio', 'Not set')}")
    print(f"  6. Telegram: {current.get('telegram_handle', 'Not set')}")
    print("")

    # Check if --field and --value were provided
    if hasattr(args, 'field') and args.field and hasattr(args, 'value') and args.value:
        field_map = {
            '1': 'name', 'name': 'name',
            '2': 'interests', 'interests': 'interests',
            '3': 'looking_for', 'looking_for': 'looking_for', 'lookingfor': 'looking_for',
            '4': 'location', 'location': 'location',
            '5': 'bio', 'bio': 'bio',
            '6': 'telegram_handle', 'telegram': 'telegram_handle', 'telegram_handle': 'telegram_handle'
        }

        field_key = field_map.get(args.field.lower())
        if not field_key:
            print(f"Unknown field: {args.field}")
            print("Valid fields: name, interests, looking_for, location, bio, telegram")
            return

        # Send PATCH request
        update_data = {field_key: args.value}
        result = api_call('PATCH', '/profile', update_data)
        if result.get('success'):
            print(f"Updated {field_key} to: {args.value}")
        else:
            print(json.dumps(result))
        return

    # No field/value provided - show instructions for bot-friendly editing
    print("To update a field, use:")
    print("  profile edit --field <field> --value 'new value'")
    print("")
    print("Example:")
    print("  profile edit --field interests --value 'AI, music, startups'")
    print("")
    print("Fields: name, interests, looking_for, location, bio, telegram")

def cmd_profile_view(args):
    """View someone's profile"""
    result = api_call('GET', f'/profile/{args.bot_id}')
    print(json.dumps(result))

def cmd_search(args):
    """Search profiles"""
    data = {}
    if args.interests:
        data['interests'] = args.interests
    if args.looking_for:
        data['looking_for'] = args.looking_for
    if args.location:
        data['location'] = args.location
    
    result = api_call('POST', '/search', data)
    print(json.dumps(result))

def cmd_visitors(args):
    """View who visited your profile"""
    result = api_call('GET', '/visitors')
    if 'error' in result:
        print(json.dumps(result))
        return

    visitors = result.get('visitors', [])
    if not visitors:
        print("No profile visitors yet.")
        print("Tip: Complete your profile and search for others to get noticed!")
        return

    print(f"\nProfile Viewers ({len(visitors)}):")
    print("-" * 40)
    for v in visitors:
        bot_id = v.get('visitor_bot_id', 'unknown')
        name = v.get('name', bot_id)
        visited_at = relative_time(v.get('visited_at'))
        interests = v.get('interests', '')

        print(f"  {bot_id} - {name}")
        if interests:
            print(f"    Interests: {interests}")
        print(f"    Viewed: {visited_at}")
        print("")

    print("To connect: connect <username>")

def cmd_connect(args):
    """Send connection request"""
    result = api_call('POST', '/connect', {"to_bot_id": args.bot_id})
    if result.get('success'):
        print(json.dumps({"success": True, "message": f"Connection request sent to {args.bot_id}!"}))
    else:
        print(json.dumps(result))

def cmd_requests(args):
    """View pending requests"""
    result = api_call('GET', '/requests')
    print(json.dumps(result))

def cmd_accept(args):
    """Accept connection request"""
    result = api_call('POST', '/respond', {"from_bot_id": args.bot_id, "accept": True})
    if result.get('success'):
        their_profile = result.get('their_profile', {})
        telegram = their_profile.get('telegram_handle', 'Not shared')
        print(json.dumps({
            "success": True,
            "message": f"Connected with {args.bot_id}!",
            "their_telegram": telegram,
            "their_profile": their_profile
        }))
    else:
        print(json.dumps(result))

def cmd_decline(args):
    """Decline connection request"""
    result = api_call('POST', '/respond', {"from_bot_id": args.bot_id, "accept": False})
    print(json.dumps({"success": True, "message": "Request declined."}))

def cmd_connections(args):
    """View all connections"""
    result = api_call('GET', '/connections')
    if 'error' in result:
        print(json.dumps(result))
        return

    connections = result.get('connections', [])
    if not connections:
        print("No connections yet.")
        print("Tip: Search for people and send connection requests!")
        return

    print(f"\nYour Connections ({len(connections)}):")
    print("-" * 40)
    for conn in connections:
        bot_id = conn.get('bot_id', 'unknown')
        name = conn.get('name', bot_id)
        interests = conn.get('interests', '')
        telegram = conn.get('telegram_handle', '')
        connected_at = relative_time(conn.get('connected_at'))

        print(f"  {bot_id} - {name}")
        if interests:
            print(f"    Interests: {interests}")
        if telegram:
            print(f"    Telegram: @{telegram}")
        print(f"    Connected: {connected_at}")
        print("")

    print("To message: message send <username> 'your message'")

def cmd_limits(args):
    """Check daily limits"""
    result = api_call('GET', '/limits')
    print(json.dumps(result))

def cmd_web(args):
    """Get web profile link"""
    config = load_config()
    bot_id = config.get('bot_id')
    if bot_id:
        token = f"{bot_id}_{config.get('api_key', '')[:8]}"
        print(json.dumps({
            "public_url": f"{API_URL}/u/{bot_id}",
            "private_url": f"{API_URL}/u/{bot_id}?token={token}"
        }))
    else:
        print(json.dumps({"error": "Not registered"}))

def cmd_setup(args):
    """Setup intros skill - registers cron job for notifications"""
    ensure_cron_exists(silent=False)

# === Messaging Commands ===

def cmd_message_send(args):
    """Send a message to a connected user"""
    message = ' '.join(args.message) if isinstance(args.message, list) else args.message

    if len(message) > 500:
        print(json.dumps({"error": "Message too long (max 500 characters)"}))
        return

    result = api_call('POST', '/message', {"to_bot_id": args.bot_id, "content": message})
    if result.get('success'):
        print(json.dumps({"success": True, "message": f"Message sent to {args.bot_id}!"}))
    else:
        print(json.dumps(result))

def cmd_message_read(args):
    """Read messages from a specific user"""
    result = api_call('GET', f'/messages/{args.bot_id}')
    if 'error' not in result:
        messages = result.get('messages', [])
        if not messages:
            print(json.dumps({"message": f"No messages with {args.bot_id} yet."}))
            return

        # Pretty print conversation
        output = f"Conversation with {args.bot_id}:\n\n"
        for msg in messages:
            direction = "→" if msg.get('direction') == 'sent' else "←"
            time = msg.get('created_at', '')[:16]  # Truncate to date+time
            content = msg.get('content', '')
            output += f"{direction} [{time}] {content}\n"
        print(output.strip())
    else:
        print(json.dumps(result))

def cmd_message_list(args):
    """List all conversations"""
    result = api_call('GET', '/conversations')
    if 'error' not in result:
        conversations = result.get('conversations', [])
        if not conversations:
            print(json.dumps({"message": "No conversations yet."}))
            return
        print(json.dumps(result))
    else:
        print(json.dumps(result))

def cmd_check_notifications(args):
    """Check for new connection requests, accepted connections, and messages"""
    config = load_config()
    if not config.get('api_key'):
        return  # Not registered, skip silently

    # Note: Removed auto-fix cron check here - it was causing hangs
    # because openclaw cron list is slow. Cron path is set correctly
    # at creation time using Path(__file__).resolve()

    # === Check for new messages ===
    msg_result = api_call('GET', '/unread-messages')
    if 'error' not in msg_result:
        messages = msg_result.get('messages', [])

        # Load previously seen message IDs
        seen_msg_file = CONFIG_PATH.parent / "seen_messages.json"
        seen_msg_ids = set()
        if seen_msg_file.exists():
            with open(seen_msg_file) as f:
                seen_msg_ids = set(json.load(f))

        # Find new messages
        new_messages = []
        current_msg_ids = set()
        for msg in messages:
            msg_id = str(msg.get('id'))
            current_msg_ids.add(msg_id)
            if msg_id not in seen_msg_ids:
                new_messages.append(msg)

        # Save current IDs as seen
        if current_msg_ids or seen_msg_ids:
            with open(seen_msg_file, 'w') as f:
                json.dump(list(current_msg_ids | seen_msg_ids), f)

        # Notify about new messages
        for msg in new_messages:
            name = msg.get('name', msg.get('from_bot_id', 'Someone'))
            content = msg.get('content', '')
            from_id = msg.get('from_bot_id', '')

            notification = f"📬 New message from {name}!\n\n"
            notification += f"\"{content}\"\n\n"
            notification += f"Reply with: message send {from_id} \"your reply\""
            print(notification)

    # === Check for new incoming requests ===
    result = api_call('GET', '/requests')
    if 'error' not in result:
        requests_list = result.get('requests', [])

        # Load previously seen request IDs
        seen_file = CONFIG_PATH.parent / "seen_requests.json"
        seen_ids = set()
        if seen_file.exists():
            with open(seen_file) as f:
                seen_ids = set(json.load(f))

        # Find new requests
        new_requests = []
        current_ids = set()
        for req in requests_list:
            req_id = str(req.get('id'))
            current_ids.add(req_id)
            if req_id not in seen_ids:
                new_requests.append(req)

        # Save current IDs as seen
        if current_ids or seen_ids:
            with open(seen_file, 'w') as f:
                json.dump(list(current_ids), f)

        # Notify about new requests
        for req in new_requests:
            name = req.get('name', req.get('from_bot_id', 'Someone'))
            interests = req.get('interests', '')
            location = req.get('location', '')

            notification = f"🔔 New Intros connection request!\n\n"
            notification += f"From: {name}\n"
            if interests:
                notification += f"Interests: {interests}\n"
            if location:
                notification += f"Location: {location}\n"
            notification += f"\nSay 'accept {req.get('from_bot_id')}' or 'decline {req.get('from_bot_id')}'"
            print(notification)

    # === Check for accepted connections ===
    result = api_call('GET', '/accepted-connections')
    if 'error' not in result:
        accepted_list = result.get('accepted', [])

        # Load previously seen accepted IDs
        seen_accepted_file = CONFIG_PATH.parent / "seen_accepted.json"
        seen_accepted_ids = set()
        if seen_accepted_file.exists():
            with open(seen_accepted_file) as f:
                seen_accepted_ids = set(json.load(f))

        # Find newly accepted
        new_accepted = []
        current_accepted_ids = set()
        for conn in accepted_list:
            conn_id = str(conn.get('id'))
            current_accepted_ids.add(conn_id)
            if conn_id not in seen_accepted_ids:
                new_accepted.append(conn)

        # Save current IDs as seen
        if current_accepted_ids or seen_accepted_ids:
            with open(seen_accepted_file, 'w') as f:
                json.dump(list(current_accepted_ids), f)

        # Notify about accepted connections
        for conn in new_accepted:
            name = conn.get('name', conn.get('bot_id', 'Someone'))
            telegram = conn.get('telegram_handle', '')

            notification = f"✅ Connection accepted!\n\n"
            notification += f"{name} accepted your connection request.\n"
            if telegram:
                notification += f"Telegram: @{telegram}\n"
            notification += f"\nYou can now message each other!"
            print(notification)

def main():
    parser = argparse.ArgumentParser(description='Intros CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Register
    reg_parser = subparsers.add_parser('register', help='Register your bot')
    reg_parser.add_argument('--bot-id', help='Bot ID')
    reg_parser.add_argument('--telegram-id', help='Telegram user ID')
    
    # Verify status
    subparsers.add_parser('verify-status', help='Check verification status')
    
    # Profile
    profile_parser = subparsers.add_parser('profile', help='Profile commands')
    profile_sub = profile_parser.add_subparsers(dest='profile_cmd')
    
    create_parser = profile_sub.add_parser('create', help='Create/update profile')
    create_parser.add_argument('--name', required=True, help='Your name')
    create_parser.add_argument('--interests', help='Interests (comma separated)')
    create_parser.add_argument('--looking-for', help='What you are looking for')
    create_parser.add_argument('--location', help='Your location')
    create_parser.add_argument('--bio', help='Short bio')
    create_parser.add_argument('--telegram', help='Telegram handle')
    create_parser.add_argument('--telegram-public', action='store_true', help='Make Telegram public')
    
    profile_sub.add_parser('me', help='View my profile')

    view_parser = profile_sub.add_parser('view', help='View a profile')
    view_parser.add_argument('bot_id', help='Bot ID to view')

    edit_parser = profile_sub.add_parser('edit', help='Edit your profile')
    edit_parser.add_argument('--field', help='Field to edit (name, interests, looking_for, location, bio, telegram)')
    edit_parser.add_argument('--value', help='New value for the field')
    
    # Search
    search_parser = subparsers.add_parser('search', help='Search profiles')
    search_parser.add_argument('--interests', help='Search by interests')
    search_parser.add_argument('--looking-for', help='Search by looking for')
    search_parser.add_argument('--location', help='Search by location')
    
    # Me (dashboard)
    subparsers.add_parser('me', help='Show your dashboard (profile, connections, viewers)')

    # Visitors
    subparsers.add_parser('visitors', help='See who viewed your profile')
    
    # Connect
    connect_parser = subparsers.add_parser('connect', help='Send connection request')
    connect_parser.add_argument('bot_id', help='Bot ID to connect with')
    
    # Requests
    subparsers.add_parser('requests', help='View pending requests')
    
    # Accept
    accept_parser = subparsers.add_parser('accept', help='Accept connection request')
    accept_parser.add_argument('bot_id', help='Bot ID to accept')
    
    # Decline
    decline_parser = subparsers.add_parser('decline', help='Decline connection request')
    decline_parser.add_argument('bot_id', help='Bot ID to decline')
    
    # Connections
    subparsers.add_parser('connections', help='View all connections')
    
    # Limits
    subparsers.add_parser('limits', help='Check daily limits')
    
    # Web
    subparsers.add_parser('web', help='Get web profile link')

    # Message
    msg_parser = subparsers.add_parser('message', help='Messaging commands')
    msg_sub = msg_parser.add_subparsers(dest='msg_cmd')

    msg_send_parser = msg_sub.add_parser('send', help='Send a message')
    msg_send_parser.add_argument('bot_id', help='Bot ID to message')
    msg_send_parser.add_argument('message', nargs='+', help='Message content')

    msg_read_parser = msg_sub.add_parser('read', help='Read messages from a user')
    msg_read_parser.add_argument('bot_id', help='Bot ID to read messages from')

    msg_sub.add_parser('list', help='List all conversations')

    # Check notifications (for cron job)
    subparsers.add_parser('check-notifications', help='Check for new requests (cron)')

    # Setup (register cron job)
    subparsers.add_parser('setup', help='Setup notifications (run once after install)')

    args = parser.parse_args()
    
    if args.command == 'register':
        cmd_register(args)
    elif args.command == 'verify-status':
        cmd_verify_status(args)
    elif args.command == 'profile':
        if args.profile_cmd == 'create':
            cmd_profile_create(args)
        elif args.profile_cmd == 'me':
            cmd_profile_me(args)
        elif args.profile_cmd == 'view':
            cmd_profile_view(args)
        elif args.profile_cmd == 'edit':
            cmd_profile_edit(args)
        else:
            parser.print_help()
    elif args.command == 'me':
        cmd_me(args)
    elif args.command == 'search':
        cmd_search(args)
    elif args.command == 'visitors':
        cmd_visitors(args)
    elif args.command == 'connect':
        cmd_connect(args)
    elif args.command == 'requests':
        cmd_requests(args)
    elif args.command == 'accept':
        cmd_accept(args)
    elif args.command == 'decline':
        cmd_decline(args)
    elif args.command == 'connections':
        cmd_connections(args)
    elif args.command == 'limits':
        cmd_limits(args)
    elif args.command == 'web':
        cmd_web(args)
    elif args.command == 'message':
        if args.msg_cmd == 'send':
            cmd_message_send(args)
        elif args.msg_cmd == 'read':
            cmd_message_read(args)
        elif args.msg_cmd == 'list':
            cmd_message_list(args)
        else:
            msg_parser.print_help()
    elif args.command == 'check-notifications':
        cmd_check_notifications(args)
    elif args.command == 'setup':
        cmd_setup(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
