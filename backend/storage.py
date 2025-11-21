import json
from pathlib import Path
from typing import List, Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent
INBOX_PATH = BASE_DIR / "inbox" / "emails.json"
PROMPTS_PATH = Path(__file__).resolve().parent / "prompts.json"

# In-memory state (for demo)
EMAILS: List[Dict[str, Any]] = []
PROCESSED_EMAILS: Dict[int, Dict[str, Any]] = {}
DRAFTS: List[Dict[str, Any]] = []


def load_prompts() -> Dict[str, str]:
    if not PROMPTS_PATH.exists():
        return {
            "categorization_prompt": "",
            "action_item_prompt": "",
            "auto_reply_prompt": ""
        }
    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_prompts(prompts: Dict[str, str]) -> None:
    with open(PROMPTS_PATH, "w", encoding="utf-8") as f:
        json.dump(prompts, f, indent=2)


def load_inbox() -> List[Dict[str, Any]]:
    with open(INBOX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
