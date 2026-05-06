import motor.motor_asyncio
import time
from pyrogram import enums 
from info import DATABASE_URL, DATABASE_NAME
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# In-memory cache for filter keywords to avoid DB hit on every message
_filter_cache = {}  # {group_id: (keywords_list, timestamp)}
_FILTER_CACHE_TTL = 120  # Cache for 2 minutes

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
mydb = myclient["ManualFilters"]



async def add_filter(grp_id, text, reply_text, btn, file, alert):
    mycol = mydb[str(grp_id)]

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
        _filter_cache.pop(grp_id, None)
    except:
        logger.exception('Some error occured!', exc_info=True)
             
     
async def find_filter(group_id, name):
    mycol = mydb[str(group_id)]
    
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


async def get_filters(group_id):
    # Check cache first
    cached = _filter_cache.get(group_id)
    if cached and (time.time() - cached[1]) < _FILTER_CACHE_TTL:
        return cached[0]
    
    mycol = mydb[str(group_id)]

    texts = []
    query = mycol.find()
    try:
        async for file in query:
            text = file['text']
            texts.append(text)
    except:
        pass
    
    # Update cache
    _filter_cache[group_id] = (texts, time.time())
    return texts


async def delete_filter(message, text, group_id):
    mycol = mydb[str(group_id)]
    
    myquery = {'text':text }
    query = await mycol.count_documents(myquery)
    if query == 1:
        await mycol.delete_one(myquery)
        # Invalidate cache after deletion
        _filter_cache.pop(group_id, None)
        await message.reply_text(
            f"'`{text}`'  deleted. I'll not respond to that filter anymore.",
            quote=True,
            parse_mode=enums.ParseMode.MARKDOWN
        )
    else:
        await message.reply_text("Couldn't find that filter!", quote=True)


async def del_all(message, group_id, title):
    if str(group_id) not in await mydb.list_collection_names():
        await message.edit_text(f"Nothing to remove in {title}!")
        return

    mycol = mydb[str(group_id)]
    try:
        await mycol.drop()
        await message.edit_text(f"All filters from {title} has been removed")
    except:
        await message.edit_text("Couldn't remove all filters from group!")
        return


async def count_filters(group_id):
    mycol = mydb[str(group_id)]

    count = await mycol.count_documents({})
    if count == 0:
        return False
    else:
        return count


async def filter_stats():
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
