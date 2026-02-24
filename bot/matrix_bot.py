import re
import asyncio
import aiohttp
from typing import Optional
from nio import AsyncClient, MatrixRoom, RoomMessageText

API_BASE_URL = "https://randomyt-server.vps.lueyo.es"

COMMAND_PREFIX = "ryt "

global_client = None
sync_token = None


def extract_video_id(url: str) -> Optional[str]:
    regex = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=|shorts\/|live\/)|youtu\.be\/)([^"&?\/\s]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None


async def api_get_random_video(session: aiohttp.ClientSession, start_day: Optional[str] = None, end_day: Optional[str] = None):
    params = {}
    if start_day:
        params["startDay"] = start_day
    if end_day:
        params["endDay"] = end_day
    async with session.get(f"{API_BASE_URL}/random", params=params) as response:
        if response.status == 404:
            return None
        response.raise_for_status()
        return await response.json()


async def api_publish_video(session: aiohttp.ClientSession, url: str):
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Could not extract video ID from URL.")
    
    async with session.post(f"{API_BASE_URL}/publish", json={"video_id": video_id}) as response:
        response.raise_for_status()
        return await response.json()


async def api_add_search_task(session: aiohttp.ClientSession, search: str):
    async with session.post(f"{API_BASE_URL}/task-search", json={"search_term": search}) as response:
        response.raise_for_status()
        return await response.json()


async def send_message(client: AsyncClient, room_id: str, message: str):
    await client.room_send(
        room_id=room_id,
        message_type="m.room.message",
        content={
            "msgtype": "m.text",
            "body": message
        }
    )


async def process_command(client: AsyncClient, room: MatrixRoom, command: str, args: list, http_session: aiohttp.ClientSession):
    command = command.lower()
    
    if command in ("random", "randomyt"):
        start_day = args[0] if len(args) > 0 else None
        end_day = args[1] if len(args) > 1 else None
        
        try:
            video = await api_get_random_video(http_session, start_day, end_day)
            if video:
                await send_message(client, room.room_id, f"https://youtu.be/{video['id']}")
            else:
                await send_message(client, room.room_id, "No videos found.")
        except Exception as e:
            await send_message(client, room.room_id, "Error: An error occurred while processing your request.")
    
    elif command == "publish":
        if not args:
            await send_message(client, room.room_id, "Usage: ryt publish <youtube_url>")
            return
        
        url = " ".join(args)
        video_id = extract_video_id(url)
        
        if not video_id:
            await send_message(client, room.room_id, "Could not extract video ID from URL.")
            return
        
        try:
            await api_publish_video(http_session, url)
            await send_message(client, room.room_id, f"Video published successfully!\nhttps://randomyt.lueyo.es/?id={video_id}")
        except Exception as e:
            if "Video is in database" in str(e):
                await send_message(client, room.room_id, f"Video is already in database!\nhttps://randomyt.lueyo.es/?id={video_id}")
            else:
                await send_message(client, room.room_id, "Error: An error occurred while processing your request.")
    
    elif command == "massinsert":
        if not args:
            await send_message(client, room.room_id, "Usage: ryt massinsert <search_term>")
            return
        
        search = " ".join(args)
        
        try:
            result = await api_add_search_task(http_session, search)
            await send_message(client, room.room_id, f"Task inserted successfully! Task Name: {result['search_term']}")
        except Exception as e:
            await send_message(client, room.room_id, "Error: An error occurred while processing your request.")
    
    elif command == "invite":
        await send_message(client, room.room_id, "https://discord.com/oauth2/authorize?client_id=1474853531457683629&permissions=0&integration_type=0&scope=bot")
    
    elif command == "support":
        await send_message(client, room.room_id, "https://ko-fi.com/lueyo")
    
    elif command == "help":
        help_text = """📚 Randomyt Bot - Comandos

Usa los siguientes comandos con el prefijo `ryt `

🎲 random - Obtiene un video aleatorio de YouTube
📅 random <fecha> - Obtiene un video aleatorio de una fecha específica (dd/MM/YYYY)
📅 random <inicio> <fin> - Obtiene un video aleatorio en un intervalo de fechas
📤 publish <url> - Publica un video de YouTube en la base de datos
🔍 massinsert <busqueda> - Inserta una tarea de búsqueda
🔗 invite - Obtiene el enlace de invitación del bot (Discord)
💝 support - Apoya el proyecto en Ko-fi
❓ help - Muestra este mensaje de ayuda"""
        await send_message(client, room.room_id, help_text)
    
    else:
        await send_message(client, room.room_id, f"Unknown command: {command}. Use 'ryt help' for available commands.")


async def message_callback(room: MatrixRoom, event: RoomMessageText):
    if sync_token is None:
        return
    
    if not event.body.startswith(COMMAND_PREFIX):
        return
    
    message = event.body[len(COMMAND_PREFIX):].strip()
    parts = message.split()
    
    if not parts:
        return
    
    command = parts[0]
    args = parts[1:]
    
    await process_command(global_client, room, command, args, global_client.http_session)


_global_client = None

def set_global_client(client):
    global _global_client
    _global_client = client


async def matrix_bot_main(homeserver: str, user_id: str, access_token: str):
    global global_client, sync_token
    
    client = AsyncClient(homeserver, user_id)
    client.http_session = aiohttp.ClientSession()
    
    client.access_token = access_token
    
    set_global_client(client)
    global_client = client
    
    client.add_event_callback(message_callback, RoomMessageText)
    
    print(f"Connecting to Matrix as {user_id}...")
    await client.sync()
    sync_token = "initialized"
    
    print("Matrix bot ready!")
    
    while True:
        await client.sync_forever(timeout=30000)


class MatrixBot:
    def __init__(self):
        self.task = None

    async def start(self, access_token: str, homeserver: str, user_id: str):
        if not access_token:
            print("Matrix bot token not configured. Bot will not start.")
            return
        print("Starting Matrix bot...")
        self.task = asyncio.create_task(matrix_bot_main(homeserver, user_id, access_token))
