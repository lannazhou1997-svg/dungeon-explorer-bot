from __future__ import annotations

import os
import random
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from game.engine import GameEngine, GameResult
from game.models import Player
from game.storage import PlayerStore

load_dotenv()
engine, store = GameEngine(), PlayerStore()
TAVERN_IMAGE = Path(__file__).parent / "assets" / "adventurer-tavern-chibi-hq.jpg"
CAVE_IMAGE = Path(__file__).parent / "assets" / "youden-cave-chibi.jpg"
CAVE_THUMBNAIL = Path(__file__).parent / "assets" / "youden-cave-square.jpg"
views_added = False


def bar(value: int, maximum: int, width: int = 10) -> str:
    filled = round(width * value / maximum) if maximum else 0
    return "▰" * filled + "▱" * (width - filled)


def player_embed(player: Player, result: GameResult | None = None) -> discord.Embed:
    engine.ensure_floor(player)
    color = discord.Color.red() if result and result.danger else discord.Color.dark_teal()
    title = result.title if result else "🧭 正在探索"
    message = result.message if result else "你小心翼翼地观察着四周……"
    embed = discord.Embed(
        title=f"🏰 第 {player.floor} / 100 层",
        description=f"# {title}\n{message}",
        color=color,
    )
    embed.set_thumbnail(url="attachment://youden-cave-square.jpg")
    if player.enemy:
        enemy = player.enemy
        embed.add_field(
            name="━━━━━━━━━━　👾 敌影出现　━━━━━━━━━━",
            value=f"### {enemy.boss_kind}｜{enemy.name}\n> “{enemy.catchphrase}”",
            inline=False,
        )
    else:
        section = "🧭 探索记录"
        if "宝箱" in title:
            section = "📦 宝藏出现"
        elif "泉水" in title:
            section = "⛲ 奇遇出现"
        elif "商人" in title or "交易" in title:
            section = "🧳 商人出现"
        elif "陷阱" in title:
            section = "🪤 机关出现"
        embed.add_field(
            name=f"━━━━━━━━━━　{section}　━━━━━━━━━━",
            value="\u200b",
            inline=False,
        )
        embed.add_field(
            name="怪物状态",
            value=(
                f"❤️ 生命　`{bar(enemy.hp, enemy.max_hp)}` **{enemy.hp}/{enemy.max_hp}**\n"
                f"⚔️ 攻击　`{bar(enemy.attack, max(1, enemy.attack + 10))}` **{enemy.attack}**\n"
                f"☠️ 等级　`{bar(enemy.level, max(10, player.floor + 10))}` **Lv.{enemy.level}**"
            ),
            inline=False,
        )
    embed.add_field(
        name="━━━━━━━━━━　🧙 冒险者　━━━━━━━━━━",
        value="\u200b",
        inline=False,
    )
    embed.add_field(
        name=f"🧙 冒险者｜{player.name}",
        value=f"**Lv.{player.level}**　EXP {player.exp}/{player.exp_required}\n"
              f"🗡️ 基础攻击 {8 + player.level * 2}～{12 + player.level * 3}"
              f"　+ 武器 **{player.weapon_attack}**",
        inline=True,
    )
    embed.add_field(
        name="📊 冒险者状态",
        value=(
            f"❤️ 体力　`{bar(player.hp, player.max_hp)}` **{player.hp}/{player.max_hp}**\n"
            f"💧 魔力　`{bar(player.mp, player.max_mp)}` **{player.mp}/{player.max_mp}**\n"
            f"⚡ 精力　`{bar(player.energy, player.max_energy)}` **{player.energy}/{player.max_energy}**"
        ),
        inline=True,
    )
    embed.add_field(name="━━━━━━━━━━　行囊　━━━━━━━━━━", value="\u200b", inline=False)
    embed.add_field(
        name="💰 货币",
        value=f"🪙 金币 **{player.gold}**\n🔮 水晶 **{player.crystals}**",
        inline=True,
    )
    embed.add_field(
        name="⚔️ 装备",
        value=f"武器：**{player.weapon}**（+{player.weapon_attack}）\n服装：**{player.clothing}**",
        inline=True,
    )
    embed.add_field(
        name="🎒 道具与进度",
        value=f"🧪 治疗药水 × **{player.consumables.get('治疗药水', 0)}**\n"
              f"👣 探索进度 **{player.steps}/{player.required_steps}**",
        inline=True,
    )
    embed.set_footer(text="探索消耗 3 精力｜互动消耗 2 精力｜15% 概率超常发挥（×1.5）")
    return embed


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
        value=f"武器：**{player.weapon}**（攻击 +{player.weapon_attack}）\n服装：**{player.clothing}**",
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


class DungeonView(discord.ui.View):
    def __init__(self, owner_id: int, player: Player):
        super().__init__(timeout=900)
        self.owner_id = owner_id
        if not player.enemy:
            self.remove_item(self.attack)
            self.remove_item(self.skill)
        else:
            self.remove_item(self.explore)
        if player.pending_event not in {"chest", "mimic", "fountain", "merchant"}:
            self.remove_item(self.interact)
        elif player.pending_event in {"chest", "mimic"}:
            self.interact.label = "打开宝箱"
            self.interact.emoji = "📦"
        elif player.pending_event == "fountain":
            self.interact.label = "汲取泉水"
            self.interact.emoji = "⛲"
        else:
            self.interact.label = "与商人交易"
            self.interact.emoji = "🤝"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("这不是你的面板，请使用 `/地下城`。", ephemeral=True)
        return False

    async def update(self, interaction: discord.Interaction, action: str) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        result = getattr(engine, action)(player)
        store.save(player)
        await interaction.response.edit_message(
            embed=player_embed(player, result),
            view=DungeonView(self.owner_id, player),
        )

    @discord.ui.button(label="继续探索", emoji="👣", style=discord.ButtonStyle.primary)
    async def explore(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.update(interaction, "explore")

    @discord.ui.button(label="普通攻击", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def attack(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.update(interaction, "attack")

    @discord.ui.button(label="技能", emoji="✨", style=discord.ButtonStyle.danger)
    async def skill(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        result = engine.attack(player, use_skill=True)
        store.save(player)
        await interaction.response.edit_message(
            embed=player_embed(player, result),
            view=DungeonView(self.owner_id, player),
        )

    @discord.ui.button(label="治疗药水", emoji="🧪", style=discord.ButtonStyle.success)
    async def potion(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.update(interaction, "use_potion")

    @discord.ui.button(label="刷新面板", emoji="🔄", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        engine.ensure_floor(player)
        store.save(player)
        await interaction.response.edit_message(
            embed=player_embed(player),
            view=DungeonView(self.owner_id, player),
        )

    @discord.ui.button(label="互动／交易", emoji="🤝", style=discord.ButtonStyle.success, row=1)
    async def interact(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.update(interaction, "interact_event")


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
        store.save(player)
        result = GameResult("🕯️ 幽灯岩窟", "你站在潮湿的石阶前，岩窟深处传来微弱的铃声……")
        thumbnail = discord.File(CAVE_THUMBNAIL, filename="youden-cave-square.jpg")
        await interaction.response.edit_message(
            embed=player_embed(player, result),
            view=DungeonView(interaction.user.id, player),
            attachments=[thumbnail],
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
            ComingSoonButton("金币商店", "🪙", "dungeon:coin_shop", "金币商店"),
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
        quests = random.sample([
            "🟢 **黏液灾害清扫令**｜击杀 35 只史莱姆，本日战斗经验 **+15%**",
            "🏰 **深入幽灯岩窟**｜单日向下推进 10 层，奖励 **金币 ×180**",
            "📦 **资深宝箱观察员**｜开启 12 个宝箱，奖励 **金币 ×160**",
            "👾 **守层者连战**｜击败 5 只小 Boss，奖励 **经验 ×150**",
            "🧪 **无伤补给挑战**｜不使用药水完成 20 次探索，奖励 **金币 ×200**",
            "🪙 **地下淘金者**｜单日获得 1,000 金币，额外奖励 **金币 ×120**",
            "🔮 **稀有水晶委托**｜击败 3 只大 Boss，奖励 **魔法水晶 ×1**",
            "💯 **百层远征记录**｜单次冒险抵达第 50 层，奖励 **魔法水晶 ×1**",
        ], k=random.randint(2, 3))
        container.add_item(discord.ui.TextDisplay(
            "## 📜 今日冒险委托\n"
            + "\n".join(f"> {quest}" for quest in quests)
            + "\n-# 委托内容会在酒馆面板刷新时随机更换；奖励结算将在任务系统阶段接入。"
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
    thumbnail = discord.File(CAVE_THUMBNAIL, filename="youden-cave-square.jpg")
    await interaction.response.send_message(
        content=f"🛠️ 管理员测试事件：**{event.name}**",
        embed=player_embed(player, result),
        view=DungeonView(interaction.user.id, player),
        file=thumbnail,
        ephemeral=True,
    )


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("请在 .env 中设置 DISCORD_TOKEN")
    bot.run(token)
