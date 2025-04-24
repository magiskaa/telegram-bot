import json
import os

PROFILE_FILE = "data/user_profiles.json"

def load_profiles():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_profiles():
    with open(PROFILE_FILE, "w") as f:
        json.dump(user_profiles, f, ensure_ascii=False, indent=4)

user_profiles = load_profiles()