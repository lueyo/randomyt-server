import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from common.ioc import get_video_service, get_task_service
from models.controller.input.publish_video_request import PublishVideoRequest


def extract_video_id(url: str) -> Optional[str]:
    regex = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=|shorts\/|live\/)|youtu\.be\/)([^"&?\/\s]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None


async def get_random_video(
    start_day: Optional[str] = None,
    end_day: Optional[str] = None,
):
    video_service = get_video_service()
    if start_day and end_day:
        video = await video_service.get_random_video_by_interval(start_day, end_day)
    elif start_day:
        video = await video_service.get_random_video_by_day(start_day)
    else:
        video = await video_service.get_random_video()
    return video


async def publish_video(video_id: str):
    video_service = get_video_service()
    await video_service.publish_video(PublishVideoRequest(video_id=video_id))


async def add_search_task(search: str):
    task_service = get_task_service()
    task_id = await task_service.add_task(search)
    return task_id


class LueyoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="ryt ", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.tree.sync(guild=None)
        print(f"Bot conectado como {self.user}")
        print("Sincronización completada: Comandos de barra (/) listos.")
        await self._setup_commands()

    async def _setup_commands(self):
        @self.tree.command(name="random", description="Get a random YouTube video")
        @app_commands.describe(start_day="Start date in format dd/MM/YYYY")
        @app_commands.describe(end_day="End date in format dd/MM/YYYY")
        async def random_cmd(
            interaction: discord.Interaction,
            start_day: Optional[str] = None,
            end_day: Optional[str] = None,
        ):
            try:
                video = await get_random_video(start_day, end_day)
                if video:
                    await interaction.response.send_message(f"https://youtu.be/{video.id}")
                else:
                    await interaction.response.send_message("No videos found.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

        @self.tree.command(
            name="randomyt", description="Get a random YouTube video (alias for /random)"
        )
        @app_commands.describe(start_day="Start date in format dd/MM/YYYY")
        @app_commands.describe(end_day="End date in format dd/MM/YYYY")
        async def randomyt_cmd(
            interaction: discord.Interaction,
            start_day: Optional[str] = None,
            end_day: Optional[str] = None,
        ):
            await random_cmd(interaction, start_day, end_day)

        @self.tree.command(
            name="publish", description="Publish a YouTube video to the database"
        )
        @app_commands.describe(url="YouTube video URL")
        async def publish_cmd(interaction: discord.Interaction, url: str):
            await interaction.response.defer(ephemeral=True)

            video_id = extract_video_id(url)
            if not video_id:
                await interaction.followup.send(
                    "Could not extract video ID from URL.", ephemeral=True
                )
                return

            try:
                await publish_video(video_id)
                await interaction.followup.send(
                    f"Video published successfully!\nhttps://randomyt.lueyo.es/?id={video_id}",
                    ephemeral=True,
                )
            except ValueError as e:
                if "Video is in database" in str(e):
                    await interaction.followup.send(
                        f"Video is already in database!\nhttps://randomyt.lueyo.es/?id={video_id}",
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

        @self.tree.command(
            name="massinsert", description="Insert a new search task"
        )
        @app_commands.describe(search="Search term to insert as task")
        async def massinsert_cmd(interaction: discord.Interaction, search: str):
            await interaction.response.defer(ephemeral=True)

            try:
                task_id = await add_search_task(search)
                await interaction.followup.send(
                    f"Task inserted successfully! Task ID: {task_id}",
                    ephemeral=True,
                )
            except Exception as e:
                await interaction.followup.send("Error: An error occurred while processing your request.", ephemeral=True)


def run_bot(token: str):
    bot = LueyoBot()

    @bot.command(name="random")
    async def prefix_random(ctx, start_day: Optional[str] = None, end_day: Optional[str] = None):
        try:
            video = await get_random_video(start_day, end_day)
            if video:
                await ctx.send(f"https://youtu.be/{video.id}")
            else:
                await ctx.send("No videos found.")
        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

    @bot.command(name="randomyt")
    async def prefix_randomyt(ctx, start_day: Optional[str] = None, end_day: Optional[str] = None):
        await prefix_random(ctx, start_day, end_day)

    @bot.command(name="publish")
    async def prefix_publish(ctx, url: str):
        video_id = extract_video_id(url)
        if not video_id:
            await ctx.send("Could not extract video ID from URL.")
            return

        try:
            await publish_video(video_id)
            await ctx.send(f"Video published successfully!\nhttps://randomyt.lueyo.es/?id={video_id}")
        except ValueError as e:
            if "Video is in database" in str(e):
                await ctx.send(f"Video is already in database!\nhttps://randomyt.lueyo.es/?id={video_id}")
            else:
                await ctx.send(f"Error: {str(e)}")
        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

    @bot.command(name="massinsert")
    async def prefix_massinsert(ctx, *, search: str):
        try:
            task_id = await add_search_task(search)
            await ctx.send(f"Task inserted successfully! Task ID: {task_id}")
        except Exception as e:
            await ctx.send("Error: An error occurred while processing your request.")

    @bot.command(name="help")
    async def prefix_help(ctx):
        embed = discord.Embed(
            title="📚 Randomyt Bot - Comandos",
            description="Usa los siguientes comandos con el prefijo `ryt `",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🎲 random",
            value="Obtiene un video aleatorio de YouTube",
            inline=False
        )
        embed.add_field(
            name="📅 random <fecha>",
            value="Obtiene un video aleatorio de una fecha específica (dd/MM/YYYY)",
            inline=False
        )
        embed.add_field(
            name="📅 random <inicio> <fin>",
            value="Obtiene un video aleatorio en un intervalo de fechas",
            inline=False
        )
        embed.add_field(
            name="📤 publish <url>",
            value="Publica un video de YouTube en la base de datos",
            inline=False
        )
        embed.add_field(
            name="🔍 massinsert <busqueda>",
            value="Inserta una tarea de búsqueda",
            inline=False
        )
        embed.add_field(
            name="❓ help",
            value="Muestra este mensaje de ayuda",
            inline=False
        )
        await ctx.send(embed=embed)

    bot.run(token)


class DiscordBot:
    def __init__(self):
        self.bot = None

    async def start(self, token: str):
        if not token:
            print("Discord bot token not configured. Bot will not start.")
            return
        
        async def run_async():
            bot_instance = LueyoBot()
            self.bot = bot_instance
            await bot_instance.start(token)
        
        await run_async()
