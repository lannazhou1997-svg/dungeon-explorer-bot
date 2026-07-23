from __future__ import annotations

import os
import random
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands
from dotenv import load_dotenv

from game.engine import GameEngine, GameResult
from game.models import Player
from game.shop import RARITY_EMOJI, ShopItem, daily_stock, purchase
from game.storage import PlayerStore

load_dotenv()
engine, store = GameEngine(), PlayerStore()
TAVERN_IMAGE = Path(__file__).parent / "assets" / "adventurer-tavern-chibi-hq.jpg"
CAVE_IMAGE = Path(__file__).parent / "assets" / "youden-cave-chibi.jpg"
CAVE_THUMBNAIL = Path(__file__).parent / "assets" / "youden-cave-square.jpg"
FLOOR_SCENE_DIR = Path(__file__).parent / "assets" / "floors"
GOLD_SHOP_IMAGE = Path(__file__).parent / "assets" / "gold-shop-banner.jpg"
views_added = False


def bar(value: int, maximum: int, width: int = 10) -> str:
    filled = round(width * value / maximum) if maximum else 0
    return "▰" * filled + "▱" * (width - filled)


def today_key() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()


def floor_scene_filename(floor: int) -> str:
    zone = min(9, max(0, (floor - 1) // 10))
    return f"floor-zone-{zone + 1:02d}-banner.jpg"


def floor_scene_file(floor: int) -> discord.File:
    filename = floor_scene_filename(floor)
    return discord.File(FLOOR_SCENE_DIR / filename, filename=filename)


def inventory_embed(player: Player) -> discord.Embed:
    engine.ensure_floor(player)
    items = "\n".join(
        f"• {name} × **{count}**" for name, count in player.consumables.items() if count
    ) or "空空如也"
    embed = discord.Embed(
        title=f"🎒 {player.name} 的冒险者档案",
        description=(
            f"**Lv.{player.level}**　EXP **{player.exp}/{player.exp_required}**\n"
            f"当前位于 **第 {player.floor} 层**　探索 **{player.steps}/{player.required_steps}**"
        ),
        color=0xD89A5B,
    )
    embed.add_field(
        name="📊 当前状态",
        value=(
            f"❤️ `{bar(player.hp, player.max_hp)}` {player.hp}/{player.max_hp}\n"
            f"💧 `{bar(player.mp, player.max_mp)}` {player.mp}/{player.max_mp}\n"
            f"⚡ `{bar(player.energy, player.max_energy)}` {player.energy}/{player.max_energy}"
        ),
        inline=False,
    )
    embed.add_field(
        name="⚔️ 当前装备",
        value=(
            f"武器：**{player.weapon}**（攻击 +{player.weapon_attack}）\n"
            f"服装：**{player.clothing}**（防御 +{player.defense}）\n"
            f"敏捷 **{player.agility}**｜幸运 **{player.luck}**"
        ),
        inline=True,
    )
    embed.add_field(name="🎒 道具栏", value=items, inline=True)
    embed.add_field(
        name="💰 钱袋",
        value=f"🪙 金币 **{player.gold}**\n🔮 魔法水晶 **{player.crystals}**",
        inline=True,
    )
    embed.set_footer(text="购买装备或道具后，重新点击“我的情况”即可查看。")
    return embed


def event_section(title: str, has_enemy: bool) -> str:
    if has_enemy:
        return "👾 敌影出现"
    if "宝箱" in title:
        return "📦 宝藏出现"
    if "泉水" in title:
        return "⛲ 奇遇出现"
    if "商人" in title:
        return "🧳 商人出现"
    if "精灵" in title:
        return "🧚 精灵出现"
    if "石像" in title:
        return "🗿 神秘物体出现"
    if "藏宝图" in title or "地图" in title:
        return "🗺️ 隐藏路线出现"
    if "妖兽" in title:
        return "🐺 受困生物出现"
    if "许愿井" in title or "愿望" in title:
        return "🪙 许愿事件出现"
    if any(word in title for word in ("陷阱", "落石", "偷袭", "背包")):
        return "🪤 意外发生"
    return "🧭 探索记录"


def player_panel_text(player: Player, result: GameResult | None) -> tuple[str, str]:
    title = result.title if result else "🧭 正在探索"
    message = result.message if result else "你小心翼翼地观察着四周……"
    event = f"# {title}\n{message}"
    if player.enemy:
        enemy = player.enemy
        event += (
            f"\n\n## {event_section(title, True)}\n"
            f"### {enemy.boss_kind}｜{enemy.name}\n> “{enemy.catchphrase}”\n"
            f"❤️ 生命　`{bar(enemy.hp, enemy.max_hp)}` **{enemy.hp}/{enemy.max_hp}**\n"
            f"⚔️ 攻击　`{bar(enemy.attack, max(1, enemy.attack + 10))}` **{enemy.attack}**\n"
            f"☠️ 等级　`{bar(enemy.level, max(10, player.floor + 10))}` **Lv.{enemy.level}**"
        )
    else:
        event += f"\n\n## {event_section(title, False)}"
    status = (
        f"## 🧙 冒险者｜{player.name}\n"
        f"**Lv.{player.level}**　EXP **{player.exp}/{player.exp_required}**　"
        f"🗡️ 攻击 **{8 + player.level * 2}～{12 + player.level * 3} + {player.weapon_attack}**\n"
        "🔮 星火弹 **×1.20/6MP**　月辉矢 **×1.50/12MP**　奥术流星 **×1.85/22MP**\n"
        f"❤️ `{bar(player.hp, player.max_hp)}` **{player.hp}/{player.max_hp}**\n"
        f"💧 `{bar(player.mp, player.max_mp)}` **{player.mp}/{player.max_mp}**\n"
        f"⚡ `{bar(player.energy, player.max_energy)}` **{player.energy}/{player.max_energy}**\n\n"
        f"## 🎒 行囊\n"
        f"🪙 **{player.gold}**　🔮 **{player.crystals}**　"
        f"⚔️ **{player.weapon} +{player.weapon_attack}**　👕 **{player.clothing}**\n"
        f"🛡️ 防御 **{player.defense}**　💨 敏捷 **{player.agility}**　🍀 幸运 **{player.luck}**\n"
        f"🧪 治疗 **×{player.consumables.get('治疗药水', 0)}**　"
        f"💧 魔力 **×{player.consumables.get('魔力药水', 0)}**　"
        f"⚡ 精力 **×{player.consumables.get('精力药水', 0)}**\n"
        f"👣 探索 **{player.steps}/{player.required_steps}**\n"
        "-# 探索消耗 3 精力｜互动消耗 2 精力｜超常发挥 ×1.5"
    )
    return event, status


class DungeonActionButton(discord.ui.Button):
    def __init__(self, action: str, label: str, emoji: str, style: discord.ButtonStyle):
        super().__init__(label=label, emoji=emoji, style=style)
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        panel = self.view
        if isinstance(panel, DungeonPanel):
            await panel.run_action(interaction, self.action)


class DungeonActions(discord.ui.ActionRow):
    def __init__(self, player: Player):
        buttons: list[discord.ui.Button] = []
        if player.enemy:
            buttons.extend([
                DungeonActionButton("attack", "普通攻击", "⚔️", discord.ButtonStyle.danger),
                DungeonActionButton("skill_minor", "星火弹·6MP", "✨", discord.ButtonStyle.primary),
                DungeonActionButton("skill_medium", "月辉矢·12MP", "🔷", discord.ButtonStyle.primary),
                DungeonActionButton("skill_major", "奥术流星·22MP", "🌠", discord.ButtonStyle.danger),
            ])
        elif not player.pending_event:
            buttons.append(DungeonActionButton("explore", "继续探索", "👣", discord.ButtonStyle.primary))
        pending_buttons = {
            "chest": ("interact_event", "打开宝箱", "📦"),
            "mimic": ("interact_event", "打开宝箱", "📦"),
            "fountain": ("interact_event", "汲取泉水", "⛲"),
            "merchant": ("merchant_menu", "查看商品", "🧳"),
            "fairy": ("interact_event", "帮助精灵", "🧚"),
            "mystery": ("interact_event", "摸一下", "🗿"),
            "treasure_map": ("interact_event", "按图寻宝", "🗺️"),
            "trapped_beast": ("interact_event", "解救妖兽", "🐺"),
            "wishing_well": ("interact_event", "投入金币", "🪙"),
        }
        if player.pending_event in pending_buttons:
            action, label, emoji = pending_buttons[player.pending_event]
            buttons.append(DungeonActionButton(action, label, emoji, discord.ButtonStyle.success))
        if player.pending_event in {
            "merchant", "fairy", "mystery", "treasure_map", "trapped_beast", "wishing_well"
        }:
            buttons.append(DungeonActionButton("decline_event", "婉拒／离开", "🚶", discord.ButtonStyle.secondary))
        super().__init__(*buttons[:5])


class DungeonUtilities(discord.ui.ActionRow):
    def __init__(self):
        super().__init__(
            DungeonActionButton("use_potion", "治疗药水", "🧪", discord.ButtonStyle.success),
            DungeonActionButton("use_mana_potion", "魔力药水", "💧", discord.ButtonStyle.success),
            DungeonActionButton("use_energy_potion", "精力药水", "⚡", discord.ButtonStyle.success),
            DungeonActionButton("refresh", "刷新", "🔄", discord.ButtonStyle.secondary),
        )


class ReturnTavernButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="返回冒险者酒馆", emoji="🍺", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction) -> None:
        tavern_image = discord.File(TAVERN_IMAGE, filename="adventurer-tavern-chibi-hq.jpg")
        await interaction.response.edit_message(
            view=EntrancePanel(bot.user),
            attachments=[tavern_image],
        )


class DungeonPanel(discord.ui.LayoutView):
    def __init__(self, owner_id: int, player: Player, result: GameResult | None = None):
        super().__init__(timeout=900)
        self.owner_id = owner_id
        engine.ensure_floor(player)
        if result and result.death:
            container = discord.ui.Container(accent_colour=0x9B2C2C)
            avatar_url = bot.user.display_avatar.url if bot.user else ""
            container.add_item(discord.ui.Section(
                "# 💀 你死了",
                "### 啧，冒险结束了。你连自己都照顾不好吗？喝了这个……"
                "本来是要卖10000金币的，但是送给你好了\n"
                "——by **酒馆老板小小秦**",
                accessory=discord.ui.Thumbnail(
                    avatar_url,
                    description="酒馆老板小小秦",
                ),
            ))
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.TextDisplay(result.message))
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.ActionRow(
                ReturnTavernButton()
            ))
            self.add_item(container)
            return
        event, status = player_panel_text(player, result)
        container = discord.ui.Container(accent_colour=0x6554A6)
        container.add_item(discord.ui.TextDisplay(f"# 🏰 幽灯岩窟｜第 {player.floor} / 100 层"))
        gallery = discord.ui.MediaGallery()
        gallery.add_item(
            media=f"attachment://{floor_scene_filename(player.floor)}",
            description=f"幽灯岩窟第 {player.floor} 层",
        )
        container.add_item(gallery)
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(event))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(status))
        container.add_item(discord.ui.Separator())
        container.add_item(DungeonActions(player))
        container.add_item(DungeonUtilities())
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("这不是你的面板，请使用 `/地下城`。", ephemeral=True)
        return False

    async def run_action(self, interaction: discord.Interaction, action: str) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        if action == "merchant_menu":
            await interaction.response.edit_message(view=MerchantPanel(self.owner_id, player))
            return
        if action.startswith("skill_"):
            result = engine.attack(player, skill_tier=action.removeprefix("skill_"))
        elif action == "refresh":
            result = None
        else:
            result = getattr(engine, action)(player)
        store.save(player)
        await interaction.response.edit_message(
            view=DungeonPanel(self.owner_id, player, result),
            attachments=[] if result and result.death else [floor_scene_file(player.floor)],
        )


def merchant_table(player: Player) -> str:
    rows = engine.merchant_offers(player.floor)
    lines = ["物品　　　　　｜属性　　　　　　　　　｜价格"]
    for _, name, effect, price in rows:
        lines.append(f"{name:<8}｜{effect:<12}｜{price} 金币")
    return "```text\n" + "\n".join(lines) + "```"


class MerchantSelect(discord.ui.Select):
    def __init__(self, player: Player):
        options = [
            discord.SelectOption(label=name, value=key, description=f"{effect}｜{price} 金币")
            for key, name, effect, price in engine.merchant_offers(player.floor)
        ]
        super().__init__(placeholder="选择要购买的商品（可重复购买）", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        result = engine.buy_merchant_item(player, self.values[0])
        store.save(player)
        await interaction.response.edit_message(view=MerchantPanel(interaction.user.id, player, result))


class MerchantFinishButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="结束交易", emoji="✅", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        result = engine.decline_event(player)
        store.save(player)
        await interaction.response.edit_message(
            view=DungeonPanel(interaction.user.id, player, result),
            attachments=[floor_scene_file(player.floor)],
        )


class MerchantMenuActions(discord.ui.ActionRow):
    def __init__(self):
        super().__init__(MerchantFinishButton())


class MerchantPanel(discord.ui.LayoutView):
    def __init__(self, owner_id: int, player: Player, result: GameResult | None = None):
        super().__init__(timeout=600)
        self.owner_id = owner_id
        container = discord.ui.Container(accent_colour=0xD89A5B)
        message = f"\n\n> {result.message}" if result else ""
        container.add_item(discord.ui.TextDisplay(
            f"# 🧳 旅行商人的移动商店\n"
            f"当前金币：**{player.gold}**{message}\n\n{merchant_table(player)}"
        ))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.ActionRow(MerchantSelect(player)))
        container.add_item(MerchantMenuActions())
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("这不是你的商店菜单。", ephemeral=True)
        return False


class CaveSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="选择要进入的洞窟……",
            custom_id="dungeon:cave_select",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(
                label="幽灯岩窟",
                value="youden_cave",
                description="幽蓝提灯照亮的古老岩窟 · 推荐 Lv.1",
                emoji="🕯️",
            )],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        engine.ensure_floor(player)
        player.in_adventure = True
        store.save(player)
        result = GameResult("🕯️ 幽灯岩窟", "你站在潮湿的石阶前，岩窟深处传来微弱的铃声……")
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=DungeonPanel(interaction.user.id, player, result),
            attachments=[floor_scene_file(player.floor)],
        )


class CaveSelectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(CaveSelect())


class ExploreEntranceButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="探索", emoji="🧭", style=discord.ButtonStyle.primary,
            custom_id="dungeon:open_explore",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        engine.ensure_floor(player)
        store.save(player)
        embed = discord.Embed(
            title="🕯️ 幽灯岩窟",
            description=(
                "笑脸幽火在洞口晃来晃去，一只史莱姆正努力躲在石头后面。\n"
                "据说这里的宝箱都很有礼貌——至少打开之前是这样。\n\n"
                "### 要进入洞窟探索吗？"
            ),
            color=0x8B8FE8,
        )
        embed.set_image(url="attachment://youden-cave-chibi.jpg")
        cave_image = discord.File(CAVE_IMAGE, filename="youden-cave-chibi.jpg")
        await interaction.response.send_message(
            embed=embed, file=cave_image, view=CaveSelectionView(), ephemeral=True,
        )


class ComingSoonButton(discord.ui.Button):
    def __init__(self, label: str, emoji: str, custom_id: str, currency: str):
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.secondary, custom_id=custom_id)
        self.currency = currency

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"{self.currency}功能将在下一阶段开放。", ephemeral=True
        )


def gold_shop_products_text(stock: list[ShopItem]) -> str:
    equipment = [item for item in stock if item.category in {"武器", "护具"}]
    consumables = [item for item in stock if item.category == "道具"]

    def line(item: ShopItem) -> str:
        rarity = f"{RARITY_EMOJI[item.rarity]} **[{item.rarity}] {item.name}**"
        return f"{rarity}\n> {item.stat_text}｜🪙 **{item.price}**"

    return (
        "## ⚔️ 今日装备\n"
        + "\n".join(line(item) for item in equipment)
        + "\n\n## 🧪 今日道具\n"
        + "\n".join(line(item) for item in consumables)
    )


class GoldShopSelect(discord.ui.Select):
    def __init__(self, stock: list[ShopItem]):
        super().__init__(
            placeholder="选择要购买的商品……",
            options=[
                discord.SelectOption(
                    label=f"[{item.rarity}] {item.name}",
                    value=item.key,
                    description=f"{item.stat_text}｜{item.price} 金币",
                    emoji=RARITY_EMOJI[item.rarity],
                )
                for item in stock
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        stock = daily_stock(today_key())
        item = next((entry for entry in stock if entry.key == self.values[0]), None)
        if not item:
            result = "商城已经跨日刷新，请重新打开金币商城。"
        else:
            _, result = purchase(player, item)
            store.save(player)
        await interaction.response.edit_message(
            view=GoldShopPanel(interaction.user.id, player, result)
        )


class GoldShopPanel(discord.ui.LayoutView):
    def __init__(self, owner_id: int, player: Player, result: str | None = None):
        super().__init__(timeout=900)
        self.owner_id = owner_id
        stock = daily_stock(today_key())
        container = discord.ui.Container(accent_colour=0xE0A12B)
        container.add_item(discord.ui.Section(
            "# 🪙 金币商城开张！",
            "### 只收金币，不收眼泪；买完不退，哭也没用。\n——by **酒馆老板小小秦**",
            accessory=discord.ui.Thumbnail(
                bot.user.display_avatar.url,
                description="地下城探索 Bot",
            ),
        ))
        container.add_item(discord.ui.Separator())
        gallery = discord.ui.MediaGallery()
        gallery.add_item(
            media="attachment://gold-shop-banner.jpg",
            description="今日金币商城",
        )
        container.add_item(gallery)
        container.add_item(discord.ui.Separator())
        result_text = f"\n\n> {result}" if result else ""
        container.add_item(discord.ui.TextDisplay(
            "## 📖 属性说明\n"
            "**攻击**提高普通攻击与魔法伤害；**防御**减少战斗和陷阱伤害；"
            "**敏捷**进一步降低陷阱伤害；**幸运**提高宝箱金币和额外道具概率。\n"
            f"当前金币：🪙 **{player.gold}**｜今日日期：**{today_key()}**{result_text}"
        ))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(gold_shop_products_text(stock)))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.ActionRow(GoldShopSelect(stock)))
        container.add_item(discord.ui.ActionRow(ReturnTavernButton()))
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("这不是你的金币商城面板。", ephemeral=True)
        return False


class GoldShopButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="金币商店", emoji="🪙", style=discord.ButtonStyle.secondary,
            custom_id="dungeon:coin_shop",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        if player.is_adventuring:
            await interaction.response.send_message(
                "⚔️ 冒险途中无法使用金币商城。死亡并返回酒馆后才能再次购买。",
                ephemeral=True,
            )
            return
        shop_image = discord.File(GOLD_SHOP_IMAGE, filename="gold-shop-banner.jpg")
        await interaction.response.send_message(
            view=GoldShopPanel(interaction.user.id, player),
            file=shop_image,
            ephemeral=True,
        )


class MyStatusButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="我的情况", emoji="🎒", style=discord.ButtonStyle.success,
            custom_id="dungeon:my_status",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        engine.ensure_floor(player)
        store.save(player)
        await interaction.response.send_message(embed=inventory_embed(player), ephemeral=True)


class EntranceButtons(discord.ui.ActionRow):
    def __init__(self):
        super().__init__(
            ExploreEntranceButton(),
            GoldShopButton(),
            ComingSoonButton("水晶兑换", "🔮", "dungeon:crystal_shop", "水晶兑换"),
            MyStatusButton(),
        )


class EntrancePanel(discord.ui.LayoutView):
    def __init__(self, client_user: discord.ClientUser):
        super().__init__(timeout=None)
        container = discord.ui.Container(accent_colour=0x48B8C7)
        container.add_item(discord.ui.Section(
            "# 🍺 冒险者酒馆",
            "### **欢迎回来勇者，接取委托、整理行囊，然后从这里滚去你的冒险。——by 酒馆老板小小秦**",
            accessory=discord.ui.Thumbnail(
                client_user.display_avatar.url,
                description="地下城探索 Bot",
            ),
        ))
        container.add_item(discord.ui.Separator())
        gallery = discord.ui.MediaGallery()
        gallery.add_item(
            media="attachment://adventurer-tavern-chibi-hq.jpg",
            description="热闹又温暖的冒险者酒馆",
        )
        container.add_item(gallery)
        container.add_item(discord.ui.Separator())
        quest_rng = random.Random(f"dungeon-daily-quests:{today_key()}:v1")
        quest_pool = [
            "🟢 **黏液灾害清扫令**｜击杀 35 只史莱姆，本日战斗经验 **+15%**",
            "🏰 **深入幽灯岩窟**｜单日向下推进 10 层，奖励 **金币 ×180**",
            "📦 **资深宝箱观察员**｜开启 12 个宝箱，奖励 **金币 ×160**",
            "👾 **守层者连战**｜击败 5 只小 Boss，奖励 **经验 ×150**",
            "🧪 **无伤补给挑战**｜不使用药水完成 20 次探索，奖励 **金币 ×200**",
            "🪙 **地下淘金者**｜单日获得 1,000 金币，额外奖励 **金币 ×120**",
            "🔮 **稀有水晶委托**｜击败 3 只大 Boss，奖励 **魔法水晶 ×1**",
            "💯 **百层远征记录**｜单次冒险抵达第 50 层，奖励 **魔法水晶 ×1**",
        ]
        quests = quest_rng.sample(quest_pool, k=quest_rng.randint(2, 3))
        container.add_item(discord.ui.TextDisplay(
            "## 📜 今日冒险委托\n"
            + "\n".join(f"> {quest}" for quest in quests)
            + f"\n-# 委托按北京时间每日刷新｜{today_key()}｜奖励结算将在任务系统阶段接入。"
        ))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(
            "## 👤 当前冒险者情况\n"
            "点击 **我的情况**，随时查看个人等级、状态、装备、道具和货币。\n"
            "-# 个人数据仅自己可见，不会与其他冒险者混淆。"
        ))
        container.add_item(discord.ui.Separator())
        container.add_item(EntranceButtons())
        self.add_item(container)


async def ensure_entrance_panel() -> None:
    channel_id = os.getenv("DUNGEON_CHANNEL_ID")
    if not channel_id or not bot.user:
        print("未设置 DUNGEON_CHANNEL_ID，暂不发布地下城入口面板。")
        return
    try:
        channel = bot.get_channel(int(channel_id)) or await bot.fetch_channel(int(channel_id))
        message_id = store.get_setting("entrance_panel_message_id")
        image = discord.File(TAVERN_IMAGE, filename="adventurer-tavern-chibi-hq.jpg")
        if message_id:
            try:
                message = await channel.fetch_message(int(message_id))
                await message.edit(
                    content=None, embed=None, view=EntrancePanel(bot.user), attachments=[image]
                )
                return
            except (discord.NotFound, discord.Forbidden):
                pass
        message = await channel.send(view=EntrancePanel(bot.user), file=image)
        store.set_setting("entrance_panel_message_id", message.id)
        print(f"已发布地下城入口面板：频道 {channel.id}")
    except (ValueError, OSError, discord.HTTPException) as error:
        print(f"地下城入口面板发布失败：{error}")


bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())


@bot.event
async def on_ready() -> None:
    global views_added
    if not views_added:
        bot.add_view(EntrancePanel(bot.user))
        views_added = True
    guild_id = os.getenv("TEST_GUILD_ID") or os.getenv("GUILD_ID")
    if guild_id:
        guild = discord.Object(id=int(guild_id))
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    else:
        await bot.tree.sync()
    await ensure_entrance_panel()
    print(f"已登录：{bot.user}")


@bot.tree.command(name="地下城", description="打开你的地下城探索面板")
async def dungeon(interaction: discord.Interaction) -> None:
    channel_id = os.getenv("DUNGEON_CHANNEL_ID")
    if channel_id and interaction.channel_id != int(channel_id):
        channel = bot.get_channel(int(channel_id))
        mention = channel.mention if channel else f"频道 `{channel_id}`"
        await interaction.response.send_message(
            f"请前往 {mention} 使用地下城。", ephemeral=True
        )
        return
    await interaction.response.send_message(
        "请选择要进入的洞窟：", view=CaveSelectionView(), ephemeral=True
    )


@bot.tree.command(name="地下城测试", description="管理员指定下一刻出现的地下城事件")
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.choices(event=[
    discord.app_commands.Choice(name="普通怪物", value="monster"),
    discord.app_commands.Choice(name="普通宝箱", value="chest"),
    discord.app_commands.Choice(name="宝箱怪（先伪装）", value="mimic"),
    discord.app_commands.Choice(name="宁静泉水", value="fountain"),
    discord.app_commands.Choice(name="旅行商人", value="merchant"),
    discord.app_commands.Choice(name="受伤的精灵", value="fairy"),
    discord.app_commands.Choice(name="神秘石像", value="mystery"),
    discord.app_commands.Choice(name="藏宝图", value="treasure_map"),
    discord.app_commands.Choice(name="受困妖兽", value="trapped_beast"),
    discord.app_commands.Choice(name="地下许愿井", value="wishing_well"),
    discord.app_commands.Choice(name="随机陷阱", value="trap"),
    discord.app_commands.Choice(name="寂静长廊", value="empty"),
    discord.app_commands.Choice(name="小 Boss", value="small_boss"),
    discord.app_commands.Choice(name="大 Boss", value="major_boss"),
])
async def dungeon_test(
    interaction: discord.Interaction,
    event: discord.app_commands.Choice[str],
) -> None:
    permissions = getattr(interaction.user, "guild_permissions", None)
    if not permissions or not permissions.administrator:
        await interaction.response.send_message("只有服务器管理员可以使用测试指令。", ephemeral=True)
        return
    player = store.get(interaction.user.id, interaction.user.display_name)
    engine.ensure_floor(player)
    result = engine.force_event(player, event.value)
    store.save(player)
    await interaction.response.send_message(
        view=DungeonPanel(interaction.user.id, player, result),
        file=floor_scene_file(player.floor),
        ephemeral=True,
    )


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("请在 .env 中设置 DISCORD_TOKEN")
    bot.run(token)
