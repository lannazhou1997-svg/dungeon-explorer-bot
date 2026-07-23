
from __future__ import annotations

import random
from dataclasses import dataclass

from .models import Enemy, Player


@dataclass
class GameResult:
    title: str
    message: str
    danger: bool = False
    death: bool = False


class GameEngine:
    EVENTS = (["monster"] * 30 + ["chest"] * 15 + ["mimic"] * 9 +
              ["trap"] * 12 + ["recovery"] * 9 + ["shop"] * 7 +
              ["fairy"] * 5 + ["mystery"] * 6 + ["treasure_map"] * 5 +
              ["trapped_beast"] * 5 + ["wishing_well"] * 4 + ["empty"] * 8)
    MAGIC_SKILLS = {
        "minor": ("✨ 星火弹", 6, 1.20),
        "medium": ("🔷 月辉矢", 12, 1.50),
        "major": ("🌠 奥术流星", 22, 1.85),
    }
    MAJOR_BOSS_NAMES = {
        10: "黏液大公·噗叽伯爵",
        20: "晶甲女王·辉钻",
        30: "万菌之母·绵绵菇",
        40: "潮汐圣兽·波波鲁",
        50: "熔炉总管·赤锤",
        60: "禁书馆长·墨菲斯",
        70: "永动机皇·咔嗒三世",
        80: "极星冰帝·企鹅诺尔",
        90: "月庭守护者·露娜兔",
        100: "幽灯王座·小小暗王",
    }
    MERCHANT_ITEMS = {
        "healing_potion": ("治疗药水", "恢复 35 点体力", 25),
        "mana_potion": ("魔力药水", "恢复 25 点魔力", 30),
        "energy_potion": ("精力药水", "恢复 30 点精力", 35),
        "lucky_charm": ("幸运护符", "珍贵的任务与事件道具", 90),
    }

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()

    def required_steps(self, floor: int) -> int:
        bonus = min(12, (floor - 1) // 10 * 2)
        return self.rng.randint(12 + bonus, 24 + bonus)

    def ensure_floor(self, player: Player) -> None:
        if player.required_steps <= 0:
            player.required_steps = self.required_steps(player.floor)
        if player.enemy and player.enemy.boss_kind == "大 Boss":
            if player.enemy.name in self.MAJOR_BOSS_NAMES.values():
                return
            if player.floor % 10 != 0:
                player.enemy = self._make_boss(player.floor)
            else:
                expected = self._make_boss(player.floor)
                if player.enemy.name != expected.name:
                    player.enemy.name = expected.name
                    player.enemy.catchphrase = expected.catchphrase
                    player.enemy.level = expected.level

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
            position = player.floor % 10
            if position == 0:
                player.enemy = self._make_boss(player.floor)
                return GameResult("🔥 大 Boss 降临！", f"固定守层者 **{player.enemy.name}** 挡住了通往下一区域的道路！", True)
            if position in {5, 6, 7, 8} and self.rng.random() < 0.45:
                player.enemy = self._make_boss(player.floor)
                return GameResult("⚠️ 小 Boss 随机出现！", f"**{player.enemy.name}** 闻讯赶来，决定亲自阻止你！", True)
            cleared = player.floor
            player.floor += 1
            player.steps = 0
            player.required_steps = self.required_steps(player.floor)
            return GameResult("🚪 找到下层入口", f"第 **{cleared} 层**探索完成，没有 Boss 出现。你进入了第 **{player.floor} 层**。")
        return getattr(self, f"_event_{self.rng.choice(self.EVENTS)}")(player)

    def attack(
        self,
        player: Player,
        use_skill: bool = False,
        skill_tier: str | None = None,
    ) -> GameResult:
        enemy = player.enemy
        if not enemy:
            return GameResult("没有敌人", "当前没有可以攻击的目标。")
        if use_skill and skill_tier is None:
            skill_tier = "medium"
        skill = self.MAGIC_SKILLS.get(skill_tier) if skill_tier else None
        if skill and player.mp < skill[1]:
            return GameResult("魔力不足", f"释放 **{skill[0]}** 需要 {skill[1]} 点魔力。")
        base_min = 8 + player.level * 2
        base_max = 12 + player.level * 3
        base_damage = self.rng.randint(base_min, base_max)
        exceptional = self.rng.random() < (0.08 if skill else 0.15)
        if exceptional:
            base_damage = round(base_damage * 1.5)
        damage = base_damage + player.weapon_attack
        label = skill[0] if skill else "普通攻击"
        if skill:
            player.mp -= skill[1]
            damage = int(damage * skill[2])
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
        if event == "merchant":
            return GameResult("🧳 旅行商人的菜单", "请从商品下拉菜单中选择要购买的物品。")
        if player.energy < 2:
            return GameResult("精力不足", "打开宝箱需要 2 点精力。")
        player.energy -= 2
        if event == "mimic":
            player.pending_event = None
            player.enemy = self._make_monster(player.floor, mimic=True)
            return GameResult(
                "😈 你遇到了宝箱怪！",
                f"宝箱突然长出牙齿！**{player.enemy.name}** 扑了过来！",
                True,
            )
        if event == "fountain":
            player.pending_event = None
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
        if event == "fairy":
            player.pending_event = None
            item = "治疗药水"
            if player.consumables.get(item, 0) <= 0:
                return GameResult(
                    "🧚 精灵有点失望",
                    "你翻遍行囊也没有找到她需要的治疗药水。她挥挥手飞走了。",
                )
            player.consumables[item] -= 1
            reward_roll = self.rng.random()
            if reward_roll < 0.08:
                player.crystals += 1
                reward = "极其稀有的 **魔法水晶 ×1**"
            elif reward_roll < 0.55:
                exp = 35 + player.floor * 3
                reward = f"**{exp} 经验**"
                reward += self._gain_exp(player, exp)
            else:
                gold = 45 + player.floor * 8
                player.gold += gold
                reward = f"**{gold} 金币**"
            return GameResult("🧚 精灵的谢礼", f"交出 **治疗药水 ×1**，获得{reward}。")
        if event == "mystery":
            player.pending_event = None
            outcome = self.rng.choice(("heal", "hurt", "battle", "gold"))
            if outcome == "heal":
                healed = min(30 + player.floor, player.max_hp - player.hp)
                player.hp += healed
                return GameResult("✨ 石像发出暖光", f"摸起来意外柔软，恢复 **{healed} 点体力**。")
            if outcome == "gold":
                gold = 20 + player.floor * 5
                player.gold += gold
                return GameResult("🪙 石像吐出金币", f"它打了个嗝，掉出 **{gold} 金币**。")
            if outcome == "battle":
                player.enemy = self._make_monster(player.floor)
                return GameResult("👾 石像叫来了守卫！", f"**{player.enemy.name}** 从暗门里冲了出来！", True)
            damage = 12 + player.floor // 2
            player.hp = max(0, player.hp - damage)
            if not player.is_alive:
                return self._die(player, f"神秘石像咬了你一口，造成 {damage} 点伤害。")
            return GameResult("💥 石像咬了你一口", f"失去 **{damage} 点体力**。谁让你乱摸呢？", True)
        if event == "treasure_map":
            player.pending_event = None
            roll = self.rng.random()
            if roll < 0.03:
                player.crystals += 1
                return GameResult("🔮 地图尽头的秘宝", "你找到了极其稀有的 **魔法水晶 ×1**！")
            if roll < 0.28:
                player.enemy = self._make_monster(player.floor, mimic=True)
                return GameResult("😈 地图是宝箱怪的外卖单！", f"**{player.enemy.name}** 已经等候多时！", True)
            gold = self.rng.randint(25, 55) * max(1, player.floor)
            player.gold += gold
            return GameResult("🗺️ 找到地图宝藏！", f"绕了一点远路，最终挖出 **{gold} 金币**。")
        if event == "trapped_beast":
            player.pending_event = None
            roll = self.rng.random()
            if roll < 0.22:
                damage = 8 + player.floor // 2
                player.hp = max(0, player.hp - damage)
                if not player.is_alive:
                    return self._die(player, f"受困妖兽惊慌反咬，造成 {damage} 点伤害。")
                return GameResult("🐾 妖兽受惊了！", f"它误咬了你一口，失去 **{damage} 点体力**，随后逃进黑暗。", True)
            if roll < 0.35:
                player.enemy = self._make_monster(player.floor)
                return GameResult("👾 捕兽夹的主人回来了！", f"**{player.enemy.name}** 把你当成了偷猎者！", True)
            item = self.rng.choice(("治疗药水", "魔力药水", "精力药水"))
            player.consumables[item] = player.consumables.get(item, 0) + 1
            return GameResult("🐺 妖兽记住了你的气味", f"它叼来 **{item} ×1** 作为谢礼，然后摇着尾巴离开了。")
        if event == "wishing_well":
            player.pending_event = None
            cost = 15 + player.floor * 2
            if player.gold < cost:
                return GameResult("🪙 愿望没有回音", f"许愿需要投入 **{cost} 金币**，你的钱袋不够沉。")
            player.gold -= cost
            roll = self.rng.random()
            if roll < 0.12:
                player.consumables["幸运护符"] = player.consumables.get("幸运护符", 0) + 1
                return GameResult("🌟 愿望成真！", f"投入 {cost} 金币，井底浮出 **幸运护符 ×1**。")
            if roll < 0.62:
                exp = 25 + player.floor * 4
                level_text = self._gain_exp(player, exp)
                return GameResult("✨ 井水闪闪发光", f"投入 {cost} 金币，获得 **{exp} 经验**。{level_text}")
            return GameResult("🐸 井里只有青蛙", f"投入 {cost} 金币，一只青蛙认真地对你说了声“呱”。")
        player.pending_event = None
        gold = self.rng.randint(8, 20) * max(1, player.floor)
        player.gold += gold
        extra = ""
        if self.rng.random() < 0.25:
            player.consumables["治疗药水"] = player.consumables.get("治疗药水", 0) + 1
            extra = "，以及一瓶治疗药水"
        return GameResult("🎁 宝箱开启！", f"消耗 2 点精力，获得 **{gold} 金币**{extra}。")

    def decline_event(self, player: Player) -> GameResult:
        event = player.pending_event
        player.pending_event = None
        if event == "fairy":
            return GameResult("👋 你婉拒了精灵", "精灵理解地点点头，留下几粒亮晶晶的粉末后飞走了。")
        if event == "mystery":
            return GameResult("🚶 你忍住了好奇心", "你没有乱摸来历不明的东西。今天也很稳健。")
        if event == "treasure_map":
            return GameResult("🗺️ 你收起了藏宝图", "这条岔路看起来不太可靠，你决定继续原本的路线。")
        if event == "trapped_beast":
            return GameResult("🐾 你没有靠近妖兽", "谨慎也许不够英雄，但通常比较长寿。")
        if event == "wishing_well":
            return GameResult("🪙 你保住了金币", "你没有向陌生的井投入辛苦赚来的钱。")
        if event == "merchant":
            return GameResult("🧳 离开旅行商店", "商人继续数着金币，目送你走远。")
        return GameResult("继续前进", "你没有与眼前的事物互动。")

    def merchant_offers(self, floor: int) -> list[tuple[str, str, str, int]]:
        scale = 1 + (floor - 1) // 10
        return [
            (key, name, effect, base_price + scale * 5)
            for key, (name, effect, base_price) in self.MERCHANT_ITEMS.items()
        ]

    def buy_merchant_item(self, player: Player, item_key: str) -> GameResult:
        offers = {key: (name, effect, price) for key, name, effect, price in self.merchant_offers(player.floor)}
        if player.pending_event != "merchant":
            return GameResult("商人已经离开", "当前没有可以交易的旅行商人。")
        if item_key not in offers:
            return GameResult("商品不存在", "旅行商人翻了翻箱子，没有找到这件商品。")
        name, effect, price = offers[item_key]
        if player.gold < price:
            return GameResult("金币不足", f"**{name}** 需要 {price} 金币，你目前只有 {player.gold}。")
        player.gold -= price
        player.consumables[name] = player.consumables.get(name, 0) + 1
        return GameResult("🛍️ 购买成功", f"获得 **{name} ×1**（{effect}），花费 **{price} 金币**。")

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

    def use_mana_potion(self, player: Player) -> GameResult:
        count = player.consumables.get("魔力药水", 0)
        if count <= 0:
            return GameResult("没有魔力药水", "你的道具栏中没有魔力药水。")
        if player.mp >= player.max_mp:
            return GameResult("魔力已满", "你现在不需要使用魔力药水。")
        restored = min(25, player.max_mp - player.mp)
        player.mp += restored
        player.consumables["魔力药水"] = count - 1
        return GameResult("💧 使用魔力药水", f"恢复了 **{restored} 点魔力**。")

    def use_energy_potion(self, player: Player) -> GameResult:
        count = player.consumables.get("精力药水", 0)
        if count <= 0:
            return GameResult("没有精力药水", "你的道具栏中没有精力药水。")
        if player.energy >= player.max_energy:
            return GameResult("精力已满", "你现在不需要使用精力药水。")
        restored = min(30, player.max_energy - player.energy)
        player.energy += restored
        player.consumables["精力药水"] = count - 1
        return GameResult("⚡ 使用精力药水", f"恢复了 **{restored} 点精力**。")

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
        item_pool = [
            name
            for name, count in player.consumables.items()
            for _ in range(max(0, count))
        ]
        kept_items = self.rng.sample(item_pool, k=min(2, len(item_pool)))
        player.consumables = {}
        for name in kept_items:
            player.consumables[name] = player.consumables.get(name, 0) + 1
        original_gold = player.gold
        player.gold //= 2
        player.level, player.exp = 1, 0
        player.max_hp, player.hp = 100, 100
        player.max_mp, player.mp = 50, 50
        player.max_energy, player.energy = 100, 100
        player.floor, player.steps = 1, 0
        player.required_steps = self.required_steps(1)
        player.enemy, player.pending_event = None, None
        kept_text = "、".join(
            f"{name} ×{count}" for name, count in player.consumables.items()
        ) if player.consumables else "无"
        return GameResult(
            "💀 你死了",
            f"{prefix}\n等级、经验和层数已重置；普通道具只保留：**{kept_text}**。"
            f"金币由 **{original_gold}** 减少为 **{player.gold}**；装备和魔法水晶保留。",
            True,
            True,
        )

    def _make_monster(self, floor: int, mimic: bool = False) -> Enemy:
        scale = 1 + floor * 0.10
        zone = min(9, (floor - 1) // 10)
        zone_monsters = [
            ["洞穴史莱姆", "提灯蝙蝠", "苔藓团子"],
            ["水晶甲虫", "矿车史莱姆", "宝石蜥蜴"],
            ["蘑菇拳手", "孢子团子", "菌帽术士"],
            ["泡泡水灵", "蝾螈卫兵", "贝壳寄居蟹"],
            ["熔岩团子", "扳手魔像", "火花小鬼"],
            ["困倦书灵", "幽灵馆员", "墨水史莱姆"],
            ["发条骑士", "齿轮仓鼠", "钟摆魔偶"],
            ["企鹅卫兵", "雪绒精", "冰晶狐狸"],
            ["月兔星灵", "花园守卫", "极光飞蛾"],
            ["王座影卫", "皇冠史莱姆", "月晶魔偶"],
        ]
        name = "贪婪宝箱怪" if mimic else self.rng.choice(zone_monsters[zone])
        lines = {
            "贪婪宝箱怪": "我不是宝箱，我只是长得比较富有！",
            "洞穴史莱姆": "噗叽！这条路已经被本史莱姆承包啦！",
            "提灯蝙蝠": "吱——你的发型看起来很好抓！",
            "苔藓团子": "别踩我，我只是长得很像地毯！",
        }
        lines.setdefault(name, f"{name}摆出了自认为非常帅气的战斗姿势！")
        hp = int((48 if mimic else 38) * scale)
        level = max(1, floor + self.rng.randint(-1, 1))
        return Enemy(name, hp, hp, max(5, int(7 * scale)), 18 + floor * 3,
                     "宝箱怪" if mimic else "普通怪物", level, lines[name])

    def _make_boss(self, floor: int) -> Enemy:
        major = floor % 10 == 0
        scale = 1 + floor * 0.12
        hp = int((115 if major else 78) * scale)
        zone_small_names = [
            ["提灯石像", "苔冠骑士"], ["晶矿监督", "宝石巨钳"],
            ["菌环祭司", "孢子巨人"], ["水殿门卫", "泡沫骑士"],
            ["熔炉魔像", "火花工头"], ["索引幽灵", "禁书守卫"],
            ["齿轮将军", "钟塔卫士"], ["冰门企鹅", "霜晶巨兽"],
            ["星庭园丁", "月花守卫"], ["王座近卫", "月晶执事"],
        ]
        zone = min(9, (floor - 1) // 10)
        name = self.MAJOR_BOSS_NAMES.get(floor, f"异界领主·第{floor}层") if major else self.rng.choice(zone_small_names[zone])
        lines: dict[str, str] = {}
        lines.setdefault(name, f"我是 **{name}**，这层的通行证可没那么好拿！")
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
        return GameResult("📦 你遇到了宝箱", "里面传来金币轻轻碰撞的声音。互动打开后，可能获得金币、药水或其他物品。")

    def _event_chest(self, player: Player) -> GameResult:
        player.pending_event = "chest"
        return GameResult("📦 你遇到了宝箱", "里面传来金币轻轻碰撞的声音。互动打开后，可能获得金币、药水或其他物品。")

    def _event_trap(self, player: Player) -> GameResult:
        damage = self.rng.randint(5, 12) + player.floor // 3
        trap = self.rng.choice(("rock", "ambush", "rune", "thief", "snatcher"))
        if trap == "rock":
            player.hp = max(0, player.hp - damage)
            if not player.is_alive:
                return self._die(player, f"你遭遇落石并失去 {damage} 点体力。")
            return GameResult("🪨 你遇到了落石！", f"巨石从头顶滚落，失去 **{damage} 点体力**。", True)
        if trap == "ambush":
            player.enemy = self._make_monster(player.floor)
            player.hp = max(0, player.hp - max(3, damage // 2))
            if not player.is_alive:
                return self._die(player, "你遭到藏在暗处的怪物偷袭。")
            return GameResult("⚔️ 你遭遇到了偷袭！", f"失去 **{max(3, damage // 2)} 点体力**，**{player.enemy.name}** 拦住了去路！", True)
        if trap == "rune":
            player.mp = max(0, player.mp - damage)
            return GameResult("🔮 魔力陷阱发动！", f"符文抽走力量，失去 **{damage} 点魔力**。", True)
        if trap == "thief":
            lost = min(player.gold, self.rng.randint(8, 20) * max(1, player.floor))
            player.gold -= lost
            return GameResult("🦝 钱袋被偷袭了！", f"一只蒙面浣熊抢走 **{lost} 金币**，还回头对你做了个鬼脸。", True)
        available = [name for name, count in player.consumables.items() if count > 0]
        if not available:
            return GameResult("🎒 背包撕裂陷阱！", "背包被钩子划开了，好在里面没有可以掉落的道具。", True)
        lost_item = self.rng.choice(available)
        player.consumables[lost_item] -= 1
        return GameResult("🎒 背包撕裂陷阱！", f"你慌乱中遗失了 **{lost_item} ×1**。", True)

    def _event_recovery(self, player: Player) -> GameResult:
        player.pending_event = "fountain"
        return GameResult(
            "⛲ 你遇到了宁静泉水！",
            f"清澈泉水散发着柔光。互动后最多恢复 **{20 + player.floor // 2} 体力、"
            f"{12 + player.floor // 4} 魔力、14 精力**。",
        )

    def _event_shop(self, player: Player) -> GameResult:
        player.pending_event = "merchant"
        return GameResult(
            "🧳 你遇到了旅行商人！",
            "商人的推车里摆着恢复药水和稀有护符。互动后可打开商品菜单，并能连续购买。",
        )

    def _event_fairy(self, player: Player) -> GameResult:
        player.pending_event = "fairy"
        return GameResult(
            "🧚 你遇到了受伤的精灵！",
            "她希望得到 **治疗药水 ×1**。帮助她可能获得金币、经验，极低概率获得魔法水晶。",
        )

    def _event_mystery(self, player: Player) -> GameResult:
        player.pending_event = "mystery"
        return GameResult(
            "🗿 你遇到了柔软的神秘石像",
            "它看起来很想被摸一下。摸了以后可能恢复体力、掉落金币、受到伤害，甚至引来怪物。",
        )

    def _event_treasure_map(self, player: Player) -> GameResult:
        player.pending_event = "treasure_map"
        return GameResult(
            "🗺️ 你捡到了一张藏宝图！",
            "地图指向一条偏离当前路线的岔路。前往后可能找到大量金币或稀有水晶，也可能是陷阱。",
        )

    def _event_trapped_beast(self, player: Player) -> GameResult:
        player.pending_event = "trapped_beast"
        return GameResult(
            "🐺 你遇到了被困住的妖兽",
            "它的脚被古老捕兽夹卡住了。解救它可能获得谢礼，但惊慌的妖兽也可能反咬或引来敌人。",
        )

    def _event_wishing_well(self, player: Player) -> GameResult:
        player.pending_event = "wishing_well"
        cost = 15 + player.floor * 2
        return GameResult(
            "🪙 你遇到了地下许愿井",
            f"井壁写着模糊的古代符号。投入 **{cost} 金币**许愿，可能获得经验或幸运护符。",
        )

    def _event_empty(self, player: Player) -> GameResult:
        return GameResult("🌙 你遇到了寂静长廊", "这里暂时没有危险，你安全地向前推进。")

    def force_event(self, player: Player, event: str) -> GameResult:
        """管理员测试入口：不消耗探索步数和精力，直接生成指定事件。"""
        player.enemy = None
        player.pending_event = None
        if event == "small_boss":
            floor = player.floor if player.floor % 10 else max(1, player.floor - 1)
            player.enemy = self._make_boss(floor)
            return GameResult("⚠️ 你遇到了守层者！", f"**{player.enemy.name}** 前来接受测试！", True)
        if event == "major_boss":
            floor = player.floor if player.floor % 10 == 0 else player.floor + (10 - player.floor % 10)
            player.enemy = self._make_boss(floor)
            return GameResult("🔥 你遇到了大 Boss！", f"**{player.enemy.name}** 前来接受测试！", True)
        handlers = {
            "monster": self._event_monster,
            "chest": self._event_chest,
            "mimic": self._event_mimic,
            "trap": self._event_trap,
            "fountain": self._event_recovery,
            "merchant": self._event_shop,
            "fairy": self._event_fairy,
            "mystery": self._event_mystery,
            "treasure_map": self._event_treasure_map,
            "trapped_beast": self._event_trapped_beast,
            "wishing_well": self._event_wishing_well,
            "empty": self._event_empty,
        }
        return handlers[event](player)
