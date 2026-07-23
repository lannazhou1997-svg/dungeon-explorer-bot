
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Player


class PlayerStore:
    def __init__(self, path: str | Path = "data/dungeon.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS players (user_id INTEGER PRIMARY KEY, state TEXT NOT NULL)")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def get(self, user_id: int, name: str) -> Player:
        with self._connect() as conn:
            row = conn.execute("SELECT state FROM players WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return Player(user_id=user_id, name=name)
        player = Player.from_dict(json.loads(row[0]))
        player.name = name
        return player

    def save(self, player: Player) -> None:
        payload = json.dumps(player.to_dict(), ensure_ascii=False)
        with self._connect() as conn:
            conn.execute("INSERT INTO players(user_id, state) VALUES(?, ?) "
                         "ON CONFLICT(user_id) DO UPDATE SET state = excluded.state", (player.user_id, payload))
