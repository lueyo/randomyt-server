from dotenv import load_dotenv
import os

load_dotenv()

# Example configuration variables
DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017/")

LIMIT_VIEWS = int(os.getenv("LIMIT_VIEWS", 2000))