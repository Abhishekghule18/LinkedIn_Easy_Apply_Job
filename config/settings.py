import json
import logging
from pathlib import Path
from typing import Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent
REQUIREMENTS_DIR = BASE_DIR / "requirements"
DB_PATH = BASE_DIR / "applied_jobs.sqlite"

# Ensure requirements exists
REQUIREMENTS_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(BASE_DIR / "agent.log"),
            logging.StreamHandler()
        ]
    )

def load_json(filepath: Path) -> Dict[str, Any]:
    if not filepath.exists():
        logging.warning(f"File not found: {filepath}")
        return {}
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_profile() -> Dict[str, Any]:
    return load_json(REQUIREMENTS_DIR / "profile.json")

def get_preferences() -> Dict[str, Any]:
    return load_json(REQUIREMENTS_DIR / "preferences.json")

def get_resume_path() -> Path:
    return REQUIREMENTS_DIR / "resume.pdf"
