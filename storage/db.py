import sqlite3
import json
from pathlib import Path
from datetime import datetime
from config.settings import DB_PATH

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applied_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE,
                job_title TEXT,
                company TEXT,
                location TEXT,
                applied_date TEXT,
                status TEXT,
                job_url TEXT
            )
        ''')
        conn.commit()

def add_job(job_id: str, job_title: str, company: str, location: str, job_url: str, status: str = "APPLIED"):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO applied_jobs (job_id, job_title, company, location, applied_date, status, job_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (job_id, job_title, company, location, datetime.utcnow().isoformat(), status, job_url))
            conn.commit()
    except sqlite3.IntegrityError:
        pass # Job already recorded

def is_applied(job_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM applied_jobs WHERE job_id = ?', (job_id,))
        return cursor.fetchone() is not None
