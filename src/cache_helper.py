import os
import json
import hashlib
from datetime import datetime, timedelta

CACHE_FILE = "ai_audit_cache.json"

def get_logs_hash(target_name, logs_notes_only):
    """
    Generates a unique SHA-256 hash strictly based on the subject name 
    and core notes content, completely ignoring timestamps so the cache 
    doesn't miss due to time changes.
    """
    raw_str = f"{target_name}_{logs_notes_only}"
    normalized = "".join(raw_str.split())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache_data):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=4)
    except Exception:
        pass

def get_cached_audit(target_name, logs_notes_only):
    cache = load_cache()
    log_hash = get_logs_hash(target_name, logs_notes_only)
    
    if log_hash in cache:
        entry = cache[log_hash]
        cached_time = datetime.fromisoformat(entry["timestamp"])
        # Check if within 24 hours TTL
        if datetime.now() - cached_time < timedelta(hours=24):
            return entry["response"]
            
    return None

def set_cached_audit(target_name, logs_notes_only, ai_response):
    cache = load_cache()
    log_hash = get_logs_hash(target_name, logs_notes_only)
    
    cache[log_hash] = {
        "timestamp": datetime.now().isoformat(),
        "response": ai_response
    }
    save_cache(cache)