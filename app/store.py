"""Serialized SQLite transactions keep confirmation, depth and event writes atomic."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Store:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, owner TEXT NOT NULL, state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS requests(run TEXT, key TEXT, result TEXT, PRIMARY KEY(run,key));
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def load(db, run, owner):
        row = db.execute('SELECT state FROM runs WHERE id=? AND owner=?', (run, owner)).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def save(db, state):
        db.execute('UPDATE runs SET state=? WHERE id=?', (json.dumps(state), state['id']))
