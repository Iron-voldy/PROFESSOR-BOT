import os, math, logging, datetime, pytz, logging.config, warnings

# Suppress deprecation warnings for cleaner output
warnings.filterwarnings('ignore', message='pkg_resources is deprecated', category=UserWarning)

from aiohttp import web
from pyrogram import Client, types
from database.users_chats_db import db
from database.simple_db import ensure_indexes
from typing import Union, Optional, AsyncGenerator
from utils import temp, __repo__, __license__, __copyright__, __version__
from info import API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL, UPTIME, WEB_SUPPORT, LOG_MSG

# Get logging configurations with better Unicode handling
import sys
try:
    # Set console encoding to UTF-8 if possible
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except:
    pass

try:
    logging.config.fileConfig("logging.conf")
except Exception as e:
    # Fallback logging configuration if file config fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(lineno)d - %(name)s - %(module)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('BotLog.txt', 'w', encoding='utf-8')
        ]
    )
    print(f"Logging config file failed, using basic config: {e}")

logging.getLogger(__name__).setLevel(logging.INFO)
logging.getLogger("cinemagoer").setLevel(logging.ERROR)


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Professor-Bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="plugins")
        )

    async def start(self):
        # Handle MongoDB connection gracefully with multiple retry strategies
        mongodb_connected = False
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"Attempting MongoDB connection... (attempt {attempt + 1}/{max_retries})")
                
                # Try to connect with shorter timeout for faster failure detection
                import asyncio
                
                # Use asyncio.wait_for to add an overall timeout to the operation
                b_users, b_chats = await asyncio.wait_for(
                    db.get_banned(),
                    timeout=10.0  # 10 second total timeout
                )
                
                temp.BANNED_USERS = b_users
                temp.BANNED_CHATS = b_chats
                print("SUCCESS: MongoDB connection successful")
                mongodb_connected = True
                break
                
            except asyncio.TimeoutError:
                print(f"ERROR: MongoDB connection timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                
            except Exception as e:
                print(f"ERROR: MongoDB connection error on attempt {attempt + 1}: {e}")
                if "DNS" in str(e).upper() or "RESOLUTION" in str(e).upper():
                    print("INFO: DNS resolution issue detected. This might be a network connectivity problem.")
                    print("SUGGESTIONS:")
                    print("  - Check your internet connection")
                    print("  - Try using a different DNS server (8.8.8.8, 1.1.1.1)")
                    print("  - Check if MongoDB cluster is accessible")
                
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
        
        if not mongodb_connected:
            print("WARNING: MongoDB connection failed after all retries")
            print("INFO: Bot will continue with limited functionality (local mode)...")
            print("NOTE: User management and ban lists will not be available")
            temp.BANNED_USERS = []
            temp.BANNED_CHATS = []
        
        await super().start()
        
        # Only attempt to create indexes if MongoDB is connected
        if mongodb_connected:
            try:
                await ensure_indexes()
                print("SUCCESS: Database indexes ensured")
            except Exception as e:
                print(f"ERROR: Index creation failed: {e}")
                print("INFO: Bot will continue without database optimization...")
        else:
            print("INFO: Skipping database index creation (MongoDB unavailable)")
        me = await self.get_me()
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        self.id = me.id
        self.name = me.first_name
        self.mention = me.mention
        self.username = me.username
        self.log_channel = LOG_CHANNEL
        self.uptime = UPTIME
        curr = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        date = curr.strftime('%d %B, %Y')
        tame = curr.strftime('%I:%M:%S %p')
        try:
            log_message = LOG_MSG.format(me.first_name, date, tame, __repo__, __version__, __license__, __copyright__)
            # Handle Unicode encoding issues on Windows
            if hasattr(log_message, 'encode'):
                log_message = log_message.encode('utf-8', errors='ignore').decode('utf-8')
            logging.info(log_message)
        except (UnicodeEncodeError, UnicodeDecodeError):
            logging.info("Bot Started Successfully - Unicode display issue bypassed")
            try:
                print(LOG_MSG.format(me.first_name, date, tame, __repo__, __version__, __license__, __copyright__))
            except (UnicodeEncodeError, UnicodeDecodeError):
                print("Bot Started Successfully")
        
        try: await self.send_message(LOG_CHANNEL, text=LOG_MSG.format(me.first_name, date, tame, __repo__, __version__, __license__, __copyright__), disable_web_page_preview=True)   
        except Exception as e: logging.warning(f"Bot Isn't Able To Send Message To LOG_CHANNEL \n{e}")
        
        if bool(WEB_SUPPORT) is True:
            app = web.AppRunner(web.Application(client_max_size=30000000))
            await app.setup()
            
            # Try multiple ports in case 8080 is occupied
            ports_to_try = [8080, 8081, 8082, 8083, 8084]
            web_server_started = False
            
            for port in ports_to_try:
                try:
                    await web.TCPSite(app, "0.0.0.0", port).start()
                    web_server_started = True
                    try:
                        logging.info(f"Web Response Is Running on port {port}......🕸️")
                    except UnicodeEncodeError:
                        logging.info(f"Web Response Is Running on port {port}...")
                        print(f"Web Response Is Running on port {port}......🕸️")
                    break
                except OSError as e:
                    if e.errno == 10048:  # Port already in use
                        logging.warning(f"Port {port} is already in use, trying next port...")
                        continue
                    else:
                        raise e
            
            if not web_server_started:
                logging.error("Could not start web server on any available port")
                print("Could not start web server on any available port")
            
    async def stop(self, *args):
        await super().stop()
        try:
            logging.info("Bot Is Restarting ⟳...")
        except UnicodeEncodeError:
            logging.info("Bot Is Restarting...")
            try:
                print("Bot Is Restarting ⟳...")
            except UnicodeEncodeError:
                print("Bot Is Restarting...")

    async def iter_messages(self, chat_id: Union[int, str], limit: int, offset: int = 0) -> Optional[AsyncGenerator["types.Message", None]]:                       
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1


        
Bot().run()





