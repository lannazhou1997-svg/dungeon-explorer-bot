
from __future__ import annotations

import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from game.engine import GameEngine, GameResult
from game.models import Player
from game.storage import PlayerStore

load_dotenv()
engine, store = GameEngine(), PlayerStore()


def bar(value: int, maximum: int, width: int = 8) -> str:
    filled = round(width * value / maximum) if maximum else 0
    return "█" * filled + "░" * (width - filled)


def player_embed(player: Player, result: GameResult | None = None) -> discord.Embed:
    engine.ensure_floor(player)
    color = discord.Color.red() if result and result.danger else discord.Color.dark_teal()
    embed = discord.Embed(title=result.title if result else "🏰 地下城探索",
                          description=result.message if result else "未知的地下城正在等待你。", color=color)
    embed.add_field(name="🧙 冒险者", value=f"**{player.name}**\nLv.{player.level} · EXP {player.exp}/{player.exp_required}", inline=True)
    embed.add_field(
        name="❤️ 体力　💧 魔力　⚡ 精力",
        value=(f"**{player.hp}/{player.max_hp}**　　"
               f"**{player.mp}/{player.max_mp}**　　"
               f"**{player.energy}/{player.max_energy}**"),
        inline=True,
    )
    embed.add_field(name="🏰 当前进度", value=f"第 **{player.floor}** / 100 层\n👣 {player.steps}/{player.required_steps}", inline=True)
    embed.add_field(name="💰 货币", value=f"金币 {player.gold}\n水晶 {player.crystals}", inline=True)
    embed.add_field(name="⚔️ 装备", value=f"武器：{player.weapon}\n服装：{player.clothing}", inline=True)
    embed.add_field(name="🎒 道具", value=f"治疗药水 × {player.consumables.get('治疗药水', 0)}", inline=True)
    if player.enemy:
        embed.add_field(name=f"👹 {player.enemy.boss_kind}：{player.enemy.name}",
                        value=f"体力 {player.enemy.hp}/{player.enemy.max_hp}", inline=False)
    embed.set_footer(text="探索消耗 3 精力；开宝箱额外消耗 2 精力")
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


bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())


@bot.event
async def on_ready() -> None:
    guild_id = os.getenv("GUILD_ID")
    if guild_id:
        guild = discord.Object(id=int(guild_id))
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    else:
        await bot.tree.sync()
    print(f"已登录：{bot.user}")


@bot.tree.command(name="地下城", description="打开你的地下城探索面板")
async def dungeon(interaction: discord.Interaction) -> None:
    player = store.get(interaction.user.id, interaction.user.display_name)
    engine.ensure_floor(player)
    store.save(player)
    await interaction.response.send_message(embed=player_embed(player), view=DungeonView(interaction.user.id))


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("请在 .env 中设置 DISCORD_TOKEN")
    bot.run(token)
