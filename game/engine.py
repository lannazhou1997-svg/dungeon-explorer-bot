
from __future__ import annotations

import random
from dataclasses import dataclass

from .models import Enemy, Player


@dataclass
class GameResult:
    title: str
    message: str
    danger: bool = False


class GameEngine:
    EVENTS = (["monster"] * 30 + ["chest"] * 15 + ["mimic"] * 9 +
              ["trap"] * 10 + ["recovery"] * 10 + ["shop"] * 8 + ["empty"] * 18)

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()

    def required_steps(self, floor: int) -> int:
        bonus = min(12, (floor - 1) // 10 * 2)
        return self.rng.randint(12 + bonus, 24 + bonus)

    def ensure_floor(self, player: Player) -> None:
        if player.required_steps <= 0:
            player.required_steps = self.required_steps(player.floor)

    def explore(self, player: Player) -> GameResult:
        self.ensure_floor(player)
        if player.enemy:
            return GameResult("无法继续", "必须先结束当前战斗。", True)
        if player.energy < 3:
            return GameResult("精力不足", "探索需要 3 点精力，请使用恢复道具。")
        player.energy -= 3
        player.steps += 1
        if player.steps >= player.required_steps:
            player.enemy = self._make_boss(player.floor)
            return GameResult("守层者出现！", f"你完成了本层探索，遭遇 **{player.enemy.name}**！", True)
        return getattr(self, f"_event_{self.rng.choice(self.EVENTS)}")(player)

    def attack(self, player: Player, use_skill: bool = False) -> GameResult:
        enemy = player.enemy
        if not enemy:
            return GameResult("没有敌人", "当前没有可以攻击的目标。")
        if use_skill and player.mp < 10:
            return GameResult("魔力不足", "释放技能需要 10 点魔力。")
        damage = self.rng.randint(12, 20) + (player.level - 1) * 2
        label = "奥术斩击" if use_skill else "普通攻击"
        if use_skill:
            player.mp -= 10
            damage = int(damage * 1.8)
        enemy.hp = max(0, enemy.hp - damage)
        if enemy.hp == 0:
            reward_gold = self.rng.randint(6, 12) * max(1, player.floor)
            player.gold += reward_gold
            exp = enemy.exp_reward
            player.enemy = None
            level_text = self._gain_exp(player, exp)
            progress = ""
            if enemy.boss_kind in {"小 Boss", "大 Boss"}:
                if player.floor < 100:
                    player.floor += 1
                    player.steps = 0
                    player.required_steps = self.required_steps(player.floor)
                    progress = f"\n通往第 {player.floor} 层的道路开启了。"
                else:
                    progress = "\n你征服了地下城第 100 层！"
            return GameResult("战斗胜利", f"你以{label}造成 {damage} 点伤害并击败 **{enemy.name}**！"
                              f"\n获得 {exp} 经验和 {reward_gold} 金币。{level_text}{progress}")
        incoming = self.rng.randint(max(1, enemy.attack - 3), enemy.attack + 3)
        player.hp = max(0, player.hp - incoming)
        if not player.is_alive:
            return self._die(player, f"你造成 {damage} 点伤害，但被 **{enemy.name}** 击败。")
        return GameResult("战斗中", f"你以{label}造成 {damage} 点伤害；{enemy.name} 反击造成 {incoming} 点伤害。", True)

    def use_potion(self, player: Player) -> GameResult:
        count = player.consumables.get("治疗药水", 0)
        if count <= 0:
            return GameResult("没有药水", "你的道具栏中没有治疗药水。")
        if player.hp >= player.max_hp:
            return GameResult("无需治疗", "你的体力已经全满。")
        healed = min(35, player.max_hp - player.hp)
        player.hp += healed
        player.consumables["治疗药水"] = count - 1
        return GameResult("使用道具", f"恢复了 {healed} 点体力。")

    def _gain_exp(self, player: Player, amount: int) -> str:
        player.exp += amount
        levels = 0
        while player.exp >= player.exp_required:
            player.exp -= player.exp_required
            player.level += 1
            player.max_hp += 12
            player.max_mp += 6
            player.max_energy += 5
            player.hp, player.mp, player.energy = player.max_hp, player.max_mp, player.max_energy
            levels += 1
        return f"\n提升了 {levels} 级，三项资源已恢复！" if levels else ""

    def _die(self, player: Player, prefix: str) -> GameResult:
        player.level, player.exp = 1, 0
        player.max_hp, player.hp = 100, 100
        player.max_mp, player.mp = 50, 50
        player.max_energy, player.energy = 100, 100
        player.floor, player.steps = 1, 0
        player.required_steps = self.required_steps(1)
        player.consumables, player.enemy = {}, None
        return GameResult("冒险失败", prefix + "\n等级、经验、层数和普通道具已重置；装备及剩余货币得以保留。", True)

    def _make_monster(self, floor: int, mimic: bool = False) -> Enemy:
        scale = 1 + floor * 0.10
        name = "贪婪宝箱怪" if mimic else self.rng.choice(["洞穴史莱姆", "骸骨卫兵", "暗影蝙蝠", "地穴蜘蛛"])
        hp = int((48 if mimic else 38) * scale)
        return Enemy(name, hp, hp, max(5, int(7 * scale)), 18 + floor * 3, "宝箱怪" if mimic else "普通怪物")

    def _make_boss(self, floor: int) -> Enemy:
        major = floor % 5 == 0
        scale = 1 + floor * 0.12
        hp = int((115 if major else 78) * scale)
        names = ["深渊领主", "噬魂魔像", "猩红女王"] if major else ["守门石像", "地穴骑士", "腐化祭司"]
        return Enemy(self.rng.choice(names), hp, hp, int((13 if major else 10) * scale),
                     80 + floor * (10 if major else 6), "大 Boss" if major else "小 Boss")

    def _event_monster(self, player: Player) -> GameResult:
        player.enemy = self._make_monster(player.floor)
        return GameResult("遭遇怪物", f"**{player.enemy.name}** 挡住了去路！", True)

    def _event_mimic(self, player: Player) -> GameResult:
        player.energy = max(0, player.energy - 2)
        player.enemy = self._make_monster(player.floor, True)
        return GameResult("宝箱怪！", "宝箱突然张开獠牙，额外消耗 2 点精力！", True)

    def _event_chest(self, player: Player) -> GameResult:
        if player.energy < 2:
            return GameResult("发现宝箱", "你没有足够精力打开它，只能遗憾离开。")
        player.energy -= 2
        gold = self.rng.randint(8, 20) * max(1, player.floor)
        player.gold += gold
        extra = ""
        if self.rng.random() < 0.25:
            player.consumables["治疗药水"] = player.consumables.get("治疗药水", 0) + 1
            extra = "，以及一瓶治疗药水"
        return GameResult("发现宝箱", f"消耗 2 点精力，获得 {gold} 金币{extra}。")

    def _event_trap(self, player: Player) -> GameResult:
        damage = self.rng.randint(5, 12) + player.floor // 3
        player.hp = max(0, player.hp - damage)
        return self._die(player, f"你触发陷阱并受到 {damage} 点伤害。") if not player.is_alive else GameResult("触发陷阱", f"你受到 {damage} 点伤害。", True)

    def _event_recovery(self, player: Player) -> GameResult:
        hp, mp, energy = min(20, player.max_hp-player.hp), min(12, player.max_mp-player.mp), min(10, player.max_energy-player.energy)
        player.hp += hp; player.mp += mp; player.energy += energy
        return GameResult("宁静泉水", f"恢复体力 {hp}、魔力 {mp}、精力 {energy}。")

    def _event_shop(self, player: Player) -> GameResult:
        return GameResult("流浪商店", "商人向你招手。购买功能将在下一阶段开放。")

    def _event_empty(self, player: Player) -> GameResult:
        return GameResult("寂静长廊", "这里暂时没有危险，你安全地向前推进。")
