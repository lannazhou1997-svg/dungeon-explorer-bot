
from __future__ import annotations

import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from game.engine import GameEngine, GameResult
from game.models import Player
from game.storage import PlayerStore

load_dotenv()
engine, store = GameEngine(), PlayerStore()
TAVERN_IMAGE = Path(__file__).parent / "assets" / "adventurer-tavern-chibi.jpg"
CAVE_IMAGE = Path(__file__).parent / "assets" / "youden-cave-chibi.jpg"
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
        title=title,
        description=f"## 🏰 第 {player.floor} / 100 层\n{message}",
        color=color,
    )
    if player.enemy:
        enemy = player.enemy
        embed.add_field(
            name=f"👾 {enemy.boss_kind}｜{enemy.name}",
            value=(
                f"❤️ 生命　`{bar(enemy.hp, enemy.max_hp)}` **{enemy.hp}/{enemy.max_hp}**\n"
                f"⚔️ 攻击　`{bar(enemy.attack, max(1, enemy.attack + 10))}` **{enemy.attack}**\n"
                f"☠️ 等级　`{bar(enemy.level, max(10, player.floor + 10))}` **Lv.{enemy.level}**"
            ),
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
    embed.set_footer(text="探索消耗 3 精力｜开宝箱消耗 2 精力｜15% 概率超常发挥")
    return embed


class DungeonView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=900)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("这不是你的面板，请使用 `/地下城`。", ephemeral=True)
        return False

    async def update(self, interaction: discord.Interaction, action: str) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        result = getattr(engine, action)(player)
        store.save(player)
        await interaction.response.edit_message(embed=player_embed(player, result), view=self)

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
        await interaction.response.edit_message(embed=player_embed(player, result), view=self)

    @discord.ui.button(label="治疗药水", emoji="🧪", style=discord.ButtonStyle.success)
    async def potion(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.update(interaction, "use_potion")

    @discord.ui.button(label="刷新面板", emoji="🔄", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        player = store.get(interaction.user.id, interaction.user.display_name)
        engine.ensure_floor(player)
        store.save(player)
        await interaction.response.edit_message(embed=player_embed(player), view=self)

    @discord.ui.button(label="互动／打开", emoji="📦", style=discord.ButtonStyle.success, row=1)
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
        await interaction.response.edit_message(
            embed=player_embed(player, result),
            view=DungeonView(interaction.user.id),
            attachments=[],
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


class EntranceButtons(discord.ui.ActionRow):
    def __init__(self):
        super().__init__(
            ExploreEntranceButton(),
            ComingSoonButton("金币商店", "🪙", "dungeon:coin_shop", "金币商店"),
            ComingSoonButton("水晶兑换", "🔮", "dungeon:crystal_shop", "水晶兑换"),
        )


class EntrancePanel(discord.ui.LayoutView):
    def __init__(self, client_user: discord.ClientUser):
        super().__init__(timeout=None)
        container = discord.ui.Container(accent_colour=0x48B8C7)
        container.add_item(discord.ui.Section(
            "# 🍺 冒险者酒馆",
            "### 欢迎回来！接取委托、整理行囊，然后从这里踏上新的冒险。",
            accessory=discord.ui.Thumbnail(
                client_user.display_avatar.url,
                description="地下城探索 Bot",
            ),
        ))
        container.add_item(discord.ui.Separator())
        gallery = discord.ui.MediaGallery()
        gallery.add_item(
            media="attachment://adventurer-tavern-chibi.jpg",
            description="热闹又温暖的冒险者酒馆",
        )
        container.add_item(gallery)
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(
            "## 📜 今日冒险委托\n"
            "> 前往未知洞窟进行探索，收集金币、装备与奇怪的宝物。\n"
            "> 注意：某些宝箱可能只是演技特别好的怪物。"
        ))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(
            "## 👤 当前冒险者情况\n"
            "点击 **探索** 后，将显示你个人的等级、经验、体力、魔力、精力、装备与层数。\n"
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
        image = discord.File(TAVERN_IMAGE, filename="adventurer-tavern-chibi.jpg")
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


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("请在 .env 中设置 DISCORD_TOKEN")
    bot.run(token)
