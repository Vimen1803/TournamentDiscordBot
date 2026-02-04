import os
from dotenv import load_dotenv

load_dotenv()

#BASES DE DATOS
URL_BASE_1: str = os.getenv("URL_BASE_1")

#TOKEN
BOT: str = os.getenv("DISCORD_BOT_TOKEN")
PREFIX: str = os.getenv("BOT_PREFIX")
BOT_LINK: str = os.getenv("BOT_LINK")

#CANALES
ERROR_CHANNEL: int = int(os.getenv("ERROR_CHANNEL_ID"))
LOG_CHANNEL: int = int(os.getenv("LOG_CHANNEL_ID"))
BUG_CHANNEL: int = int(os.getenv("BUG_CHANNEL_ID"))
SERVER_LOG_CHANNEL: int = int(os.getenv("SERVER_LOG_CHANNEL_ID"))

#DOCUMENTACION
DOC_URL: str = os.getenv("DOC_URL")
OWNER = [int(os.getenv("OWNER_ID"))]
