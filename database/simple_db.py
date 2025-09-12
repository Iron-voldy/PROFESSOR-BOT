"""
Simplified database module using direct Motor/PyMongo
"""
import logging
import re
import time
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError, AutoReconnect, NetworkTimeout, ServerSelectionTimeoutError
from info import FILE_DB_URL, FILE_DB_NAME, COLLECTION_NAME, MAX_RIST_BTNS

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Simple in-memory cache for search results
search_cache = {}
CACHE_EXPIRY = 300  # 5 minutes cache

# Configure MongoDB client
client = AsyncIOMotorClient(
    FILE_DB_URL,
    serverSelectionTimeoutMS=30000,
    connectTimeoutMS=30000,
    socketTimeoutMS=60000,
    maxPoolSize=10,
    minPoolSize=2,
    maxIdleTimeMS=300000,
    retryWrites=True,
    retryReads=True
)
db = client[FILE_DB_NAME]
collection = db[COLLECTION_NAME]

async def get_search_results(query, file_type=None, max_results=MAX_RIST_BTNS, offset=0, filter=False):
    """Search for movies in the database"""
    start_time = time.time()
    query = query.strip()
    
    # Create cache key
    cache_key = f"{query}:{file_type}:{max_results}:{offset}:{filter}"
    current_time = time.time()
    
    # Check cache first
    if cache_key in search_cache:
        cached_data, cached_time = search_cache[cache_key]
        if current_time - cached_time < CACHE_EXPIRY:
            logger.info(f"Cache hit for query '{query}' - returned in {time.time() - start_time:.2f}s")
            return cached_data
    
    # Build search pattern
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + re.escape(query) + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = re.escape(query).replace(r'\ ', r'.*[\s\.\+\-_]')
    
    try:
        regex = {"$regex": raw_pattern, "$options": "i"}
        logger.info(f"Search pattern for '{query}': {raw_pattern}")
    except Exception as e:
        logger.error(f"Regex compilation failed for '{query}': {e}")
        return [], '', 0
        
    # Build filter
    filter_dict = {'file_name': regex}
    if file_type:
        filter_dict['file_type'] = file_type
    
    logger.info(f"Search filter: {filter_dict}")

    # Retry logic for database operations
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # Get total count first
            total_results = await collection.count_documents(filter_dict)
            logger.info(f"Found {total_results} total documents matching '{query}'")
            
            if total_results == 0:
                logger.info(f"No results found for query: '{query}' with strict pattern. Trying fallback search...")
                
                # Try a more lenient search pattern
                fallback_pattern = {"$regex": re.escape(query), "$options": "i"}
                fallback_filter = {'file_name': fallback_pattern}
                if file_type:
                    fallback_filter['file_type'] = file_type
                
                total_results = await collection.count_documents(fallback_filter)
                logger.info(f"Fallback search found {total_results} results")
                
                if total_results == 0:
                    return [], '', 0
                    
                # Update filter for the actual search
                filter_dict = fallback_filter
            
            next_offset = offset + max_results
            if next_offset > total_results:
                next_offset = ''

            # Get the files
            cursor = collection.find(filter_dict).sort('_id', -1).skip(offset).limit(max_results)
            files = await cursor.to_list(length=max_results)
            
            # Cache the results
            cache_data = (files, next_offset, total_results)
            search_cache[cache_key] = (cache_data, current_time)
            
            # Clean old cache entries periodically
            if len(search_cache) > 1000:
                expired_keys = [k for k, (_, t) in search_cache.items() if current_time - t > CACHE_EXPIRY]
                for k in expired_keys:
                    del search_cache[k]
            
            logger.info(f"Database search for '{query}' completed in {time.time() - start_time:.2f}s - found {total_results} results, returned {len(files)} files")
            return files, next_offset, total_results
            
        except (AutoReconnect, NetworkTimeout, ServerSelectionTimeoutError) as e:
            logger.warning(f"Database connection error on search attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = 1
                await asyncio.sleep(wait_time)
                continue
            else:
                logger.error(f"Failed to search after {max_retries} attempts")
                return [], '', 0
        except Exception as e:
            logger.exception(f'Unexpected error during search: {e}')
            return [], '', 0

async def get_file_details(query):
    """Get file details by file_id"""
    filter_dict = {'_id': query}
    
    # Retry logic for database operations
    max_retries = 3
    for attempt in range(max_retries):
        try:
            cursor = collection.find(filter_dict)
            filedetails = await cursor.to_list(length=1)
            return filedetails
        except (AutoReconnect, NetworkTimeout, ServerSelectionTimeoutError) as e:
            logger.warning(f"Database connection error on file details attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
                continue
            else:
                logger.error(f"Failed to get file details after {max_retries} attempts")
                return []
        except Exception as e:
            logger.exception(f'Unexpected error getting file details: {e}')
            return []

# For backward compatibility, create a simple Media-like object
class MediaDocument:
    def __init__(self, data):
        for key, value in data.items():
            if key == '_id':
                self.file_id = value
            else:
                setattr(self, key, value)

def encode_file_id(s: bytes) -> str:
    """Encode file_id for Telegram"""
    import base64
    from struct import pack
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def encode_file_ref(file_ref: bytes) -> str:
    """Encode file_ref for Telegram"""
    import base64
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    from pyrogram.file_id import FileId
    from struct import pack
    
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref

async def save_file(media):
    """Save file to database"""
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name))
    try:
        file_data = {
            "_id": file_id,
            "file_ref": file_ref,
            "file_name": file_name,
            "file_size": media.file_size,
            "file_type": media.mime_type.split("/")[0],
            "mime_type": media.mime_type
        }
        
        await collection.replace_one({"_id": file_id}, file_data, upsert=True)
        logger.info(f"File saved: {file_name}")
        return True, 0
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return False, 2

async def ensure_indexes():
    """Ensure database indexes are created for better performance"""
    try:
        # Create text index on file_name for better search performance
        await collection.create_index("file_name")
        logger.info("Database indexes ensured successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to ensure indexes: {e}")
        return False