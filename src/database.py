"""SQLite persistence for completed workouts and set-level history."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import threading
from datetime import datetime, timezone

@dataclass(frozen=True)
class SetLog:
    workout_id: int
    exercise: str
    set_number: int
    reps: int
    duration_seconds: int | None

class WorkoutDatabase:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else Path.home() / ".voice_workout" / "workouts.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock(); self._initialize()
    def _connect(self):
        conn=sqlite3.connect(self.path, check_same_thread=False); conn.row_factory=sqlite3.Row; return conn
    def _initialize(self):
        with self._connect() as c:
            c.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS workouts(id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, notes TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS sets(id INTEGER PRIMARY KEY, workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE, exercise TEXT NOT NULL, set_number INTEGER NOT NULL, reps INTEGER NOT NULL, duration_seconds INTEGER);
            CREATE INDEX IF NOT EXISTS idx_sets_workout ON sets(workout_id);
            """)
    def start_workout(self) -> int:
        with self._lock, self._connect() as c:
            cur=c.execute("INSERT INTO workouts(started_at) VALUES (?)", (datetime.now(timezone.utc).isoformat(),)); return int(cur.lastrowid)
    def log_set(self, workout_id:int, exercise:str, set_number:int, reps:int, duration_seconds:int|None=None):
        with self._lock, self._connect() as c:
            c.execute("INSERT INTO sets(workout_id,exercise,set_number,reps,duration_seconds) VALUES (?,?,?,?,?)",(workout_id,exercise,set_number,reps,duration_seconds))
    def finish_workout(self, workout_id:int, notes:str=""):
        with self._lock, self._connect() as c: c.execute("UPDATE workouts SET finished_at=?,notes=? WHERE id=?",(datetime.now(timezone.utc).isoformat(),notes,workout_id))
    def recent_workouts(self, limit:int=20):
        with self._connect() as c: return [dict(r) for r in c.execute("SELECT * FROM workouts ORDER BY id DESC LIMIT ?",(limit,))]
    def workout_sets(self, workout_id:int):
        with self._connect() as c: return [dict(r) for r in c.execute("SELECT * FROM sets WHERE workout_id=? ORDER BY id",(workout_id,))]
