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
        if player.pending_event:
            return GameResult("等待交互", "请先处理眼前的事件。")
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
        base_min = 8 + player.level * 2
        base_max = 12 + player.level * 3
        base_damage = self.rng.randint(base_min, base_max)
        exceptional = self.rng.random() < 0.15
        if exceptional:
            base_damage = round(base_damage * 1.5)
        damage = base_damage + player.weapon_attack
        label = "奥术斩击" if use_skill else "普通攻击"
        if use_skill:
            player.mp -= 10
            damage = int(damage * 1.8)
        performance = "，触发 **超常发挥！**" if exceptional else ""
        formula = f"（基础 {base_damage} + 武器 {player.weapon_attack}）"
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
            return GameResult("🎉 战斗胜利", f"你以{label}造成 **{damage}** 点伤害{performance} {formula}，击败 **{enemy.name}**！"
                              f"\n获得 {exp} 经验和 {reward_gold} 金币。{level_text}{progress}")
        incoming = self.rng.randint(max(1, enemy.attack - 3), enemy.attack + 3)
        player.hp = max(0, player.hp - incoming)
        if not player.is_alive:
            return self._die(player, f"你造成 {damage} 点伤害，但被 **{enemy.name}** 击败。")
        return GameResult("⚔️ 激烈战斗", f"你以{label}造成 **{damage}** 点伤害{performance} {formula}；"
                          f"{enemy.name} 反击造成 **{incoming}** 点伤害。", True)

    def interact_event(self, player: Player) -> GameResult:
        event = player.pending_event
        if not event:
            return GameResult("没有可交互事件", "眼前没有需要处理的物品。")
        if player.energy < 2:
            return GameResult("精力不足", "打开宝箱需要 2 点精力。")
        player.energy -= 2
        player.pending_event = None
        if event == "mimic":
            player.enemy = self._make_monster(player.floor, mimic=True)
            return GameResult(
                "😈 你遇到了宝箱怪！",
                f"宝箱突然长出牙齿！**{player.enemy.name}** 扑了过来！",
                True,
            )
        if event == "merchant":
            price = 25 + player.floor * 2
            if player.gold < price:
                return GameResult(
                    "🧳 旅行商人的摊位",
                    f"商人拿出一瓶治疗药水，要价 **{price} 金币**。\n"
                    f"你摸了摸钱袋，只有 **{player.gold} 金币**。商人遗憾地收起了药水。",
                )
            player.gold -= price
            player.consumables["治疗药水"] = player.consumables.get("治疗药水", 0) + 1
            return GameResult(
                "🤝 交易完成！",
                f"支付 **{price} 金币**，获得 **治疗药水 ×1**。\n"
                "> “多谢惠顾！活着回来才能继续花钱哦。”",
            )
        if event == "fountain":
            hp = min(20 + player.floor // 2, player.max_hp - player.hp)
            mp = min(12 + player.floor // 4, player.max_mp - player.mp)
            energy = min(14, player.max_energy - player.energy)
            player.hp += hp
            player.mp += mp
            player.energy += energy
            return GameResult(
                "⛲ 泉水回应了你！",
                f"恢复 **{hp} 体力、{mp} 魔力、{energy} 精力**。",
            )
        gold = self.rng.randint(8, 20) * max(1, player.floor)
        player.gold += gold
        extra = ""
        if self.rng.random() < 0.25:
            player.consumables["治疗药水"] = player.consumables.get("治疗药水", 0) + 1
            extra = "，以及一瓶治疗药水"
        return GameResult("🎁 宝箱开启！", f"消耗 2 点精力，获得 **{gold} 金币**{extra}。")

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
        player.consumables, player.enemy, player.pending_event = {}, None, None
        return GameResult("冒险失败", prefix + "\n等级、经验、层数和普通道具已重置；装备及剩余货币得以保留。", True)

    def _make_monster(self, floor: int, mimic: bool = False) -> Enemy:
        scale = 1 + floor * 0.10
        name = "贪婪宝箱怪" if mimic else self.rng.choice(
            ["洞穴史莱姆", "骸骨卫兵", "暗影蝙蝠", "地穴蜘蛛"]
        )
        lines = {
            "贪婪宝箱怪": "我不是宝箱，我只是长得比较富有！",
            "洞穴史莱姆": "噗叽！这条路已经被本史莱姆承包啦！",
            "骸骨卫兵": "站住！虽然我忘了在守什么，但你不能过去！",
            "暗影蝙蝠": "吱——你的发型看起来很好抓！",
            "地穴蜘蛛": "八条腿赶路，当然比你先到。",
        }
        hp = int((48 if mimic else 38) * scale)
        level = max(1, floor + self.rng.randint(-1, 1))
        return Enemy(name, hp, hp, max(5, int(7 * scale)), 18 + floor * 3,
                     "宝箱怪" if mimic else "普通怪物", level, lines[name])

    def _make_boss(self, floor: int) -> Enemy:
        major = floor % 5 == 0
        scale = 1 + floor * 0.12
        hp = int((115 if major else 78) * scale)
        names = ["深渊领主", "噬魂魔像", "猩红女王"] if major else ["守门石像", "地穴骑士", "腐化祭司"]
        name = self.rng.choice(names)
        lines = {
            "深渊领主": "凡人，报上名来——算了，墓碑上再写也一样。",
            "噬魂魔像": "检测到入侵者。启动：非常用力地揍人。",
            "猩红女王": "弄脏我的裙摆，你就留下来洗一百年吧。",
            "守门石像": "口令错误。其实你说什么我都会判错。",
            "地穴骑士": "剑可以生锈，骑士的架势绝不能垮。",
            "腐化祭司": "安静！我刚把邪恶咒语背到最难的一段。",
        }
        return Enemy(name, hp, hp, int((13 if major else 10) * scale),
                     80 + floor * (10 if major else 6), "大 Boss" if major else "小 Boss",
                     floor + (3 if major else 1), lines[name])

    def _event_monster(self, player: Player) -> GameResult:
        player.enemy = self._make_monster(player.floor)
        return GameResult(
            "⚠️ 你遇到了怪物！",
            f"**{player.enemy.name}** 挡住了去路！",
            True,
        )

    def _event_mimic(self, player: Player) -> GameResult:
        player.pending_event = "mimic"
        return GameResult("📦 你遇到了宝箱？", "一个宝箱安静地摆在路中央。要打开看看吗？")

    def _event_chest(self, player: Player) -> GameResult:
        player.pending_event = "chest"
        return GameResult("📦 你遇到了宝箱？", "一个宝箱安静地摆在路中央。要打开看看吗？")

    def _event_trap(self, player: Player) -> GameResult:
        damage = self.rng.randint(5, 12) + player.floor // 3
        if self.rng.random() < 0.7:
            player.hp = max(0, player.hp - damage)
            if not player.is_alive:
                return self._die(player, f"你触发尖刺陷阱并失去 {damage} 点体力。")
            return GameResult(
                "🪤 陷阱突然发动！",
                f"尖刺从地面弹出，你直接失去 **{damage} 点体力**。",
                True,
            )
        player.mp = max(0, player.mp - damage)
        return GameResult(
            "🔮 魔力陷阱发动！",
            f"符文抽走了你的力量，你直接失去 **{damage} 点魔力**。",
            True,
        )

    def _event_recovery(self, player: Player) -> GameResult:
        player.pending_event = "fountain"
        return GameResult(
            "⛲ 你遇到了宁静泉水！",
            "清澈泉水散发着柔光。点击 **汲取泉水** 才能接受它的祝福。",
        )

    def _event_shop(self, player: Player) -> GameResult:
        player.pending_event = "merchant"
        price = 25 + player.floor * 2
        return GameResult(
            "🧳 你遇到了旅行商人！",
            f"商人向你招手，今天出售 **治疗药水 ×1（{price} 金币）**。\n"
            "点击 **互动／交易** 即可购买；离开前必须决定是否交易。",
        )

    def _event_empty(self, player: Player) -> GameResult:
        return GameResult("🌙 你遇到了寂静长廊", "这里暂时没有危险，你安全地向前推进。")

    def force_event(self, player: Player, event: str) -> GameResult:
        """管理员测试入口：不消耗探索步数和精力，直接生成指定事件。"""
        player.enemy = None
        player.pending_event = None
        if event == "small_boss":
            floor = player.floor if player.floor % 5 else max(1, player.floor - 1)
            player.enemy = self._make_boss(floor)
            return GameResult("⚠️ 你遇到了守层者！", f"**{player.enemy.name}** 前来接受测试！", True)
        if event == "major_boss":
            floor = player.floor if player.floor % 5 == 0 else player.floor + (5 - player.floor % 5)
            player.enemy = self._make_boss(floor)
            return GameResult("🔥 你遇到了大 Boss！", f"**{player.enemy.name}** 前来接受测试！", True)
        handlers = {
            "monster": self._event_monster,
            "chest": self._event_chest,
            "mimic": self._event_mimic,
            "trap": self._event_trap,
            "fountain": self._event_recovery,
            "merchant": self._event_shop,
            "empty": self._event_empty,
        }
        return handlers[event](player)
