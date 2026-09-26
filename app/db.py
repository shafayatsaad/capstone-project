"""Small SQLite repository; all writes use transactions and parameterized SQL."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.config import settings


class Database:
    def __init__(self, path: str | None = None):
        self.path = path or settings.database_path
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def migrate(self):
        migrations = Path(__file__).resolve().parent.parent / "migrations"
        db = self.connect()
        try:
            db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            applied = {row[0] for row in db.execute("SELECT version FROM schema_migrations")}
            for migration in sorted(migrations.glob("*.sql")):
                version = migration.stem
                if version in applied:
                    continue
                db.executescript(migration.read_text(encoding="utf-8"))
                db.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
                db.commit()
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def rows(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        db = self.connect()
        try:
            return [dict(row) for row in db.execute(sql, params).fetchall()]
        finally:
            db.close()

    def row(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        rows = self.rows(sql, params)
        return rows[0] if rows else None

    @staticmethod
    def decode(row: dict | None, fields: tuple[str, ...]) -> dict | None:
        if row:
            for field in fields:
                if row.get(field) is not None:
                    row[field.removesuffix("_json")] = json.loads(row.pop(field))
        return row


db = Database()
