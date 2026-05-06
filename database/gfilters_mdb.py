import motor.motor_asyncio
import time
from info import DATABASE_URL, DATABASE_NAME
from pyrogram import enums
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# In-memory cache for global filter keywords
_gfilter_cache = {}  # {gfilters_key: (keywords_list, timestamp)}
_GFILTER_CACHE_TTL = 120  # Cache for 2 minutes

# Use async motor client instead of blocking pymongo
myclient = motor.motor_asyncio.AsyncIOMotorClient(
    DATABASE_URL,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=10000,
    maxPoolSize=10,
    minPoolSize=1,
    retryWrites=True,
    retryReads=True
)
mydb = myclient["GlobalFilters"]



async def add_gfilter(gfilters, text, reply_text, btn, file, alert):
    mycol = mydb[str(gfilters)]
    data = {
        'text':str(text),
        'reply':str(reply_text),
        'btn':str(btn),
        'file':str(file),
        'alert':str(alert)
    }
    try:
        await mycol.update_one({'text': str(text)},  {"$set": data}, upsert=True)
        # Invalidate cache after adding
        _gfilter_cache.pop(gfilters, None)
    except:
        logger.exception('Some error occured!', exc_info=True)
             
     
async def find_gfilter(gfilters, name):
    mycol = mydb[str(gfilters)]
    
    query = mycol.find( {"text":name})
    try:
        async for file in query:
            reply_text = file['reply']
            btn = file['btn']
            fileid = file['file']
            try:
                alert = file['alert']
            except:
                alert = None
        return reply_text, btn, alert, fileid
    except:
        return None, None, None, None


async def get_gfilters(gfilters):
    # Check cache first
    cached = _gfilter_cache.get(gfilters)
    if cached and (time.time() - cached[1]) < _GFILTER_CACHE_TTL:
        return cached[0]
    
    mycol = mydb[str(gfilters)]

    texts = []
    query = mycol.find()
    try:
        async for file in query:
            text = file['text']
            texts.append(text)
    except:
        pass
    
    # Update cache
    _gfilter_cache[gfilters] = (texts, time.time())
    return texts


async def delete_gfilter(message, text, gfilters):
    mycol = mydb[str(gfilters)]
    
    myquery = {'text':text }
    query = await mycol.count_documents(myquery)
    if query == 1:
        await mycol.delete_one(myquery)
        await message.reply_text(
            f"'`{text}`'  deleted. I'll not respond to that gfilter anymore.",
            quote=True,
            parse_mode=enums.ParseMode.MARKDOWN
        )
    else:
        await message.reply_text("Couldn't find that gfilter!", quote=True)

async def del_allg(message, gfilters):
    if str(gfilters) not in await mydb.list_collection_names():
        await message.edit_text("Nothin!")
        return

    mycol = mydb[str(gfilters)]
    try:
        await mycol.drop()
        await message.edit_text(f"All filters has been removed")
    except:
        await message.edit_text("Couldn't remove all filters!")
        return

async def count_gfilters(gfilters):
    mycol = mydb[str(gfilters)]

    count = await mycol.count_documents({})
    return False if count == 0 else count


async def gfilter_stats():
    collections = await mydb.list_collection_names()

    if "CONNECTION" in collections:
        collections.remove("CONNECTION")

    totalcount = 0
    for collection in collections:
        mycol = mydb[collection]
        count = await mycol.count_documents({})
        totalcount += count

    totalcollections = len(collections)

    return totalcollections, totalcount
