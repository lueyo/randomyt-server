import asyncio
import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
import threading

from common.ioc import get_video_service, get_task_service
from models.controller.input.publish_video_request import PublishVideoRequest


def extract_video_id(url: str) -> Optional[str]:
    regex = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=|shorts\/|live\/)|youtu\.be\/)([^"&?\/\s]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None


class DiscordBot:
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(intents=intents, command_prefix="/")
        self._setup_commands()

    def _setup_commands(self):
        @self.bot.tree.command(name="random", description="Get a random YouTube video")
        @app_commands.describe(start_day="Start date in format dd/MM/YYYY")
        @app_commands.describe(end_day="End date in format dd/MM/YYYY")
        async def random_cmd(
            interaction: discord.Interaction,
            start_day: Optional[str] = None,
            end_day: Optional[str] = None,
        ):
            try:
                video_service = get_video_service()
                if start_day and end_day:
                    video = await video_service.get_random_video_by_interval(
                        start_day, end_day
                    )
                elif start_day:
                    video = await video_service.get_random_video_by_day(start_day)
                else:
                    video = await video_service.get_random_video()

                if video:
                    await interaction.response.send_message(
                        f"https://randomyt.lueyo.es/?id={video.id}"
                    )
                else:
                    await interaction.response.send_message(
                        "No videos found.", ephemeral=True
                    )
            except Exception as e:
                await interaction.response.send_message(
                    f"Error: {str(e)}", ephemeral=True
                )

        @self.bot.tree.command(
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

        @self.bot.tree.command(
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
                video_service = get_video_service()
                await video_service.publish_video(PublishVideoRequest(video_id=video_id))

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

        @self.bot.tree.command(
            name="searchinsert", description="Insert a new search task"
        )
        @app_commands.describe(search="Search term to insert as task")
        async def searchinsert_cmd(interaction: discord.Interaction, search: str):
            await interaction.response.defer(ephemeral=True)

            try:
                task_service = get_task_service()
                task_id = await task_service.add_task(search)

                await interaction.followup.send(
                    f"Task inserted successfully! Task ID: {task_id}",
                    ephemeral=True,
                )
            except Exception as e:
                await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

    async def start(self, token: str):
        if not token:
            print("Discord bot token not configured. Bot will not start.")
            return
        try:
            print("Starting Discord bot in background thread...")
            def run_bot():
                asyncio.run(self._run_bot(token))
            thread = threading.Thread(target=run_bot, daemon=True)
            thread.start()
        except Exception as e:
            print(f"Failed to start Discord bot: {e}")

    async def _run_bot(self, token: str):
        try:
            print("Discord bot: logging in...")
            await self.bot.login(token)
            print("Discord bot: connecting...")
            await self.bot.connect()
            print("Discord bot: connected and running")
        except Exception as e:
            print(f"Discord bot error: {e}")
            import traceback
            traceback.print_exc()

    def run(self, token: str):
        if not token:
            print("Discord bot token not configured. Bot will not run.")
            return
        self.bot.run(token)
