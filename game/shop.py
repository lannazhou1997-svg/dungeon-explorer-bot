from __future__ import annotations

import random
from dataclasses import dataclass

from .models import Player


@dataclass(frozen=True)
class ShopItem:
    key: str
    name: str
    category: str
    rarity: str
    price: int
    attack: int = 0
    defense: int = 0
    agility: int = 0
    luck: int = 0
    effect: str = ""

    @property
    def stat_text(self) -> str:
        if self.category == "武器":
            return f"攻击 +{self.attack}｜敏捷 +{self.agility}｜幸运 +{self.luck}"
        if self.category == "护具":
            return f"防御 +{self.defense}｜敏捷 +{self.agility}｜幸运 +{self.luck}"
        return self.effect


RARITY_EMOJI = {
    "普通": "⚪",
    "优良": "🟢",
    "稀有": "🔵",
    "黄金": "🟡",
    "传说": "🟣",
}


WEAPONS = [
    ShopItem("w_iron", "铁制短剑", "武器", "普通", 180, attack=7),
    ShopItem("w_hunter", "猎风弯刀", "武器", "优良", 420, attack=10, agility=2),
    ShopItem("w_crystal", "蓝晶法刃", "武器", "稀有", 850, attack=15, luck=2),
    ShopItem("w_gold", "黄金狮心剑", "武器", "黄金", 1650, attack=21, agility=2, luck=3),
    ShopItem("w_moon", "月蚀星辉刃", "武器", "传说", 3600, attack=30, agility=4, luck=5),
    ShopItem("w_pan", "老板娘的平底锅", "武器", "稀有", 980, attack=17, agility=1, luck=4),
]

ARMORS = [
    ShopItem("a_leather", "加厚皮甲", "护具", "普通", 160, defense=3, agility=1),
    ShopItem("a_scout", "轻羽旅装", "护具", "优良", 390, defense=4, agility=4),
    ShopItem("a_crystal", "晶纹长袍", "护具", "稀有", 820, defense=7, luck=3),
    ShopItem("a_gold", "黄金守卫甲", "护具", "黄金", 1550, defense=12, agility=1, luck=2),
    ShopItem("a_dragon", "幼龙鳞披风", "护具", "传说", 3400, defense=17, agility=4, luck=4),
    ShopItem("a_apron", "小小秦的围裙", "护具", "稀有", 920, defense=8, agility=2, luck=5),
]

CONSUMABLES = [
    ShopItem("c_heal", "治疗药水", "道具", "普通", 45, effect="恢复 35 点体力"),
    ShopItem("c_mana", "魔力药水", "道具", "普通", 55, effect="恢复 25 点魔力"),
    ShopItem("c_energy", "精力药水", "道具", "优良", 70, effect="恢复 30 点精力"),
    ShopItem("c_charm", "幸运护符", "道具", "稀有", 180, effect="用于稀有事件与委托"),
    ShopItem("c_map", "空白藏宝图", "道具", "优良", 130, effect="可供部分随机事件使用"),
]


def daily_stock(date_key: str) -> list[ShopItem]:
    rng = random.Random(f"dungeon-gold-shop:{date_key}:v1")
    return rng.sample(WEAPONS, 3) + rng.sample(ARMORS, 3) + rng.sample(CONSUMABLES, 4)


def purchase(player: Player, item: ShopItem) -> tuple[bool, str]:
    if player.is_adventuring:
        return False, "冒险途中无法使用金币商城。请先结束本次冒险。"
    if player.gold < item.price:
        return False, f"金币不足：**{item.name}** 需要 {item.price} 金币，你只有 {player.gold}。"
    player.gold -= item.price
    if item.category == "武器":
        player.weapon = item.name
        player.weapon_attack = item.attack
        player.weapon_agility = item.agility
        player.weapon_luck = item.luck
        return True, f"购买并装备 **{item.name}**！{item.stat_text}"
    if item.category == "护具":
        player.clothing = item.name
        player.clothing_defense = item.defense
        player.clothing_agility = item.agility
        player.clothing_luck = item.luck
        return True, f"购买并穿上 **{item.name}**！{item.stat_text}"
    player.consumables[item.name] = player.consumables.get(item.name, 0) + 1
    return True, f"购买 **{item.name} ×1**！{item.effect}"
