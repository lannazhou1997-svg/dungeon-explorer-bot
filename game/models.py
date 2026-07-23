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
    level: int = 1
    catchphrase: str = "它正不怀好意地盯着你的行囊。"

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
    weapon_attack: int = 4
    weapon_agility: int = 0
    weapon_luck: int = 0
    clothing: str = "布衣"
    clothing_defense: int = 1
    clothing_agility: int = 0
    clothing_luck: int = 0
    consumables: dict[str, int] = field(default_factory=lambda: {"治疗药水": 2})
    enemy: Enemy | None = None
    pending_event: str | None = None
    in_adventure: bool = False

    @property
    def defense(self) -> int:
        return self.clothing_defense

    @property
    def agility(self) -> int:
        return self.weapon_agility + self.clothing_agility

    @property
    def luck(self) -> int:
        return self.weapon_luck + self.clothing_luck

    @property
    def is_adventuring(self) -> bool:
        """兼容旧存档：只要仍有探索进度或事件，就视为正在冒险。"""
        return bool(
            self.in_adventure
            or self.floor > 1
            or self.steps > 0
            or self.enemy is not None
            or self.pending_event is not None
        )

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
