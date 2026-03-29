import json
import threading
from pathlib import Path
from logs.logger import log_error

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

class StorageManager:
    """Thread-safe low-level JSON storage operations."""
    _lock = threading.Lock()

    @staticmethod
    def _read_json(filepath: Path) -> list | dict:
        is_dict = filepath.name == "session.json"
        empty_val = {} if is_dict else []
        
        if not filepath.exists():
            return empty_val
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            log_error(f"Failed to read {filepath.name}: {e}. Initializing clean file.")
            return empty_val

    @staticmethod
    def _write_json(filepath: Path, data):
        with StorageManager._lock:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                log_error(f"Critcal error writing to {filepath.name}: {e}")

    @staticmethod
    def load_applied_jobs() -> list:
        return StorageManager._read_json(STORAGE_DIR / "applied_jobs.json")

    @staticmethod
    def load_failed_jobs() -> list:
        return StorageManager._read_json(STORAGE_DIR / "failed_jobs.json")

    @staticmethod
    def load_session() -> dict:
        session = StorageManager._read_json(STORAGE_DIR / "session.json")
        if not session:
            session = {
                "last_run_time": None,
                "total_applied": 0,
                "total_failed": 0
            }
        return session
        
    @staticmethod
    def save_applied_jobs(data: list):
        StorageManager._write_json(STORAGE_DIR / "applied_jobs.json", data)

    @staticmethod
    def save_failed_jobs(data: list):
        StorageManager._write_json(STORAGE_DIR / "failed_jobs.json", data)

    @staticmethod
    def save_session(data: dict):
        StorageManager._write_json(STORAGE_DIR / "session.json", data)
