
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Enemy:
    name: str
    hp: int
    max_hp: int
    attack: int
    exp_reward: int
    boss_kind: str = "普通怪物"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Enemy":
        return cls(**data)


@dataclass
class Player:
    user_id: int
    name: str
    level: int = 1
    exp: int = 0
    hp: int = 100
    max_hp: int = 100
    mp: int = 50
    max_mp: int = 50
    energy: int = 100
    max_energy: int = 100
    floor: int = 1
    steps: int = 0
    required_steps: int = 0
    gold: int = 0
    crystals: int = 0
    weapon: str = "新手短剑"
    clothing: str = "布衣"
    consumables: dict[str, int] = field(default_factory=lambda: {"治疗药水": 2})
    enemy: Enemy | None = None

    @property
    def exp_required(self) -> int:
        return 100 + (self.level - 1) * 50

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["enemy"] = self.enemy.to_dict() if self.enemy else None
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Player":
        values = dict(data)
        enemy = values.pop("enemy", None)
        player = cls(**values)
        player.enemy = Enemy.from_dict(enemy) if enemy else None
        return player
