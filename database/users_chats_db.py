import motor.motor_asyncio
from info import DATABASE_NAME, DATABASE_URL, DATABASE_URL_FALLBACK, IMDB, IMDB_TEMPLATE, MELCOW_NEW_USERS, P_TTI_SHOW_OFF, SINGLE_BUTTON, SPELL_CHECK_REPLY, PROTECT_CONTENT, MAX_RIST_BTNS, IMDB_DELET_TIME                  

class Database:
    
    def __init__(self, uri, database_name, fallback_uri=None):
        # Configure reasonable timeouts with proper pool size
        self.uri = uri
        self.fallback_uri = fallback_uri or DATABASE_URL_FALLBACK
        self.database_name = database_name
        
        # Try primary connection first
        try:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=10000,
                socketTimeoutMS=10000,
                connectTimeoutMS=10000,
                maxPoolSize=10,     # Allow 10 concurrent DB operations
                minPoolSize=2,      # Keep 2 connections ready
                maxIdleTimeMS=300000,
                retryWrites=True,
                retryReads=True
            )
            print("Using primary MongoDB connection")
        except Exception as e:
            print(f"Primary MongoDB connection failed: {e}")
            print("Trying fallback MongoDB connection...")
            
            # Use fallback connection
            self._client = motor.motor_asyncio.AsyncIOMotorClient(
                self.fallback_uri,
                serverSelectionTimeoutMS=10000,
                socketTimeoutMS=10000,
                connectTimeoutMS=10000,
                maxPoolSize=10,
                minPoolSize=2,
                maxIdleTimeMS=300000,
                retryWrites=True,
                retryReads=True
            )
            print("Using fallback MongoDB connection")
        
        self.db = self._client[database_name]
        self.col = self.db.users
        self.grp = self.db.groups


    def new_user(self, id, name):
        return dict(
            id = id,
            name = name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
        )


    def new_group(self, id, title, username):
        return dict(
            id = id,
            title = title,
            username = username,
            chat_status=dict(
                is_disabled=False,
                reason="",
            ),
        )
    
    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)
    
    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)
    
    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count
    
    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})
    
    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id':int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return self.col.find({})
    

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    async def delete_chat(self, chat_id):
        await self.grp.delete_many({'id': int(chat_id)})

    async def get_banned(self):
        try:
            users = self.col.find({'ban_status.is_banned': True})
            chats = self.grp.find({'chat_status.is_disabled': True})
            b_chats = [chat['id'] async for chat in chats]
            b_users = [user['id'] async for user in users]
            return b_users, b_chats
        except Exception as e:
            print(f"MongoDB connection error in get_banned: {e}")
            # Return empty lists if DB is unavailable
            return [], []
    


    async def add_chat(self, chat, title, username):
        chat = self.new_group(chat, title, username)
        await self.grp.insert_one(chat)
    

    async def get_chat(self, chat):
        chat = await self.grp.find_one({'id':int(chat)})
        return False if not chat else chat.get('chat_status')
    

    async def re_enable_chat(self, id):
        chat_status=dict(
            is_disabled=False,
            reason="",
            )
        await self.grp.update_one({'id': int(id)}, {'$set': {'chat_status': chat_status}})
        
    async def update_settings(self, id, settings):
        await self.grp.update_one({'id': int(id)}, {'$set': {'settings': settings}})
        
    
    async def get_settings(self, id):       
        default = {
            'button': SINGLE_BUTTON,
            'botpm': P_TTI_SHOW_OFF,
            'file_secure': PROTECT_CONTENT,
            'imdb': IMDB,
            'spell_check': SPELL_CHECK_REPLY,
            'welcome': MELCOW_NEW_USERS,
            'template': IMDB_TEMPLATE            
        }
        chat = await self.grp.find_one({'id':int(id)})
        if chat:
            return chat.get('settings', default)
        return default


    async def disable_chat(self, chat, reason="No Reason"):
        chat_status=dict(
            is_disabled=True,
            reason=reason,
            )
        await self.grp.update_one({'id': int(chat)}, {'$set': {'chat_status': chat_status}})
    

    async def total_chat_count(self):
        count = await self.grp.count_documents({})
        return count
    

    async def get_all_chats(self):
        return self.grp.find({})


    async def get_db_size(self):
        return (await self.db.command("dbstats"))['dataSize']


db = Database(DATABASE_URL, DATABASE_NAME)
