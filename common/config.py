from dotenv import load_dotenv
import os

load_dotenv()

# Example configuration variables
DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017/")

LIMIT_VIEWS = int(os.getenv("LIMIT_VIEWS", 2000))

# si no se puede conectar al bot no pasa nada pijes, se intentó
DISCORD_YT_RAMDOM = os.getenv("DISCORD_YT_RAMDOM_TOKEN", "")

MATRIX_YT_RANDOM_TOKEN = os.getenv("MATRIX_YT_RANDOM_TOKEN", "")
MATRIX_HOMESERVER = os.getenv("MATRIX_HOMESERVER", "https://matrix.org")
MATRIX_USER_ID = os.getenv("MATRIX_USER_ID", "@lueyobot:matrix.org")

SEARCH_NUMBER = int(os.getenv("SEARCH_NUMBER", 300))