import asyncio, re, ast, math, logging, pyrogram, io
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
from utils import get_shortlink 
from info import AUTH_USERS, AUTH_CHANNEL, PM_IMDB, SINGLE_BUTTON, PROTECT_CONTENT, SPELL_CHECK_REPLY, IMDB_TEMPLATE, IMDB_DELET_TIME, PMFILTER, G_FILTER, SHORT_URL, SHORT_API
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import Client, filters, enums 
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from utils import get_size, is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings
from database.users_chats_db import db
from database.simple_db import get_file_details, get_search_results, MediaDocument
from plugins.group_filter import global_filters
from plugins.subtitle_handler import SubtitleHandler

def extract_clean_title(filename: str) -> str:
    """Extract clean movie title from filename for subtitle naming"""
    try:
        import re
        
        # Remove file extension
        clean_name = re.sub(r'\.[a-zA-Z0-9]+$', '', filename)
        
        # Remove quality indicators and technical terms
        quality_patterns = [
            r'\b(480p|720p|1080p|2160p|4K)\b',
            r'\b(HD|FHD|UHD|WEB|WEB-DL|BluRay|BDRip|DVDRip|CAM|TS|R5)\b',
            r'\b(x264|x265|H264|H265|HEVC|AVC)\b',
            r'\b(AAC|AC3|DTS|mp3|FLAC)\b',
            r'\b\d+MB\b',
            r'\b\d+GB\b',
            r'\bmkv\b',
            r'\bmp4\b'
        ]
        
        for pattern in quality_patterns:
            clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)
        
        # Clean up separators and extra spaces
        clean_name = re.sub(r'[._-]+', ' ', clean_name)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        
        return clean_name if clean_name else filename
        
    except Exception as e:
        print(f"[EXTRACT_TITLE] Error: {e}")
        return filename

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


@Client.on_message(filters.private & filters.text)
async def auto_pm_fill(client, message):
    print(f"[PM_FILTER] Received: '{message.text}' from user {message.from_user.id}")
    
    # Check if user is subscribed to required channels
    if AUTH_CHANNEL:
        is_subscribed_result = await is_subscribed(client, message)
        if not is_subscribed_result:
            return  # is_subscribed function handles the subscription prompt
    
    if PMFILTER:
        print(f"[PM_FILTER] Processing movie search for: '{message.text}'")
        # Send immediate feedback to user
        status_msg = await message.reply("🔍 **Searching for movies...** Please wait.", quote=True)
        try:
            await pm_AutoFilter(client, message, status_msg)
        except Exception as e:
            await status_msg.edit_text("❌ **Error occurred during search.** Please try again.")
            logger.error(f"Error in pm_AutoFilter: {e}")
            import traceback
            traceback.print_exc()
    else: 
        print("[PM_FILTER] PMFILTER is disabled")
        return 

@Client.on_callback_query(filters.create(lambda _, __, query: query.data.startswith("pmnext")))
async def pm_next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    try: offset = int(offset)
    except: offset = 0
    search = temp.PM_BUTTONS.get(str(key))
    if not search: return await query.answer("Yᴏᴜ Aʀᴇ Usɪɴɢ Oɴᴇ Oғ Mʏ Oʟᴅ Mᴇssᴀɢᴇs, Pʟᴇᴀsᴇ Sᴇɴᴅ Tʜᴇ Rᴇǫᴜᴇsᴛ Aɢᴀɪɴ", show_alert=True)

    files, n_offset, total = await get_search_results(search.lower(), offset=offset, filter=True)
    try: n_offset = int(n_offset)
    except: n_offset = 0
    if not files: return
    
    if SHORT_URL and SHORT_API:          
        btn = []
        for file in files:
            try:
                # Files are always dictionaries based on debug output
                file_name = file.get('file_name', 'Unknown')
                file_size = file.get('file_size', 0)
                file_id = file.get('_id', '')  # Note: _id instead of file_id
                
                if SINGLE_BUTTON:
                    btn.append([InlineKeyboardButton(text=f"[{get_size(file_size)}] {file_name}", url=await get_shortlink(f"https://telegram.dog/{temp.U_NAME}?start=files_{file_id}"))])
                else:
                    btn.append([InlineKeyboardButton(text=f"{file_name}", url=await get_shortlink(f"https://telegram.dog/{temp.U_NAME}?start=files_{file_id}")),
                               InlineKeyboardButton(text=f"{get_size(file_size)}", url=await get_shortlink(f"https://telegram.dog/{temp.U_NAME}?start=files_{file_id}"))])
            except Exception as e:
                print(f"[PM_FILTER] Error processing file for SHORT_URL: {e}")
                continue
    else:        
        btn = []
        for file in files:
            try:
                # Files are always dictionaries based on debug output
                file_name = file.get('file_name', 'Unknown')
                file_size = file.get('file_size', 0)
                file_id = file.get('_id', '')  # Note: _id instead of file_id
                
                if SINGLE_BUTTON:
                    btn.append([InlineKeyboardButton(text=f"[{get_size(file_size)}] {file_name}", callback_data=f'pmfile#{file_id}')])
                else:
                    btn.append([InlineKeyboardButton(text=f"{file_name}", callback_data=f'pmfile#{file_id}'),
                               InlineKeyboardButton(text=f"{get_size(file_size)}", callback_data=f'pmfile#{file_id}')])
            except Exception as e:
                print(f"[PM_FILTER] Error processing file for callback: {e}")
                continue

    btn.insert(0, [InlineKeyboardButton("🔗 ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ 🔗", "howdl")])
    if 0 < offset <= 10: off_set = 0
    elif offset == 0: off_set = None
    else: off_set = offset - 10
    if n_offset == 0:
        btn.append(
            [InlineKeyboardButton("⬅️ ʙᴀᴄᴋ", callback_data=f"pmnext_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f"❄️ ᴩᴀɢᴇꜱ {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages")]                                  
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton(f"❄️ {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
             InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"pmnext_{req}_{key}_{n_offset}")])
    else:
        btn.append([
            InlineKeyboardButton("⬅️ ʙᴀᴄᴋ", callback_data=f"pmnext_{req}_{key}_{off_set}"),
            InlineKeyboardButton(f"❄️ {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
            InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"pmnext_{req}_{key}_{n_offset}")
        ])
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass
    await query.answer()


@Client.on_callback_query(filters.create(lambda _, __, query: query.data.startswith("pmspolling")))
async def pm_spoll_tester(bot, query):
    _, user, movie_ = query.data.split('#')
    if movie_ == "close_spellcheck":
        return await query.message.delete()
    movies = temp.PM_SPELL.get(str(query.message.reply_to_message.id))
    if not movies:
        return await query.answer("Yᴏᴜ Aʀᴇ Usɪɴɢ Oɴᴇ Oғ Mʏ Oʟᴅ Mᴇssᴀɢᴇs, Pʟᴇᴀsᴇ Sᴇɴᴅ Tʜᴇ Rᴇǫᴜᴇsᴛ Aɢᴀɪɴ", show_alert=True)
    movie = movies[(int(movie_))]
    await query.answer('Cʜᴇᴄᴋɪɴɢ Fᴏʀ Mᴏᴠɪᴇ Iɴ Dᴀᴛᴀʙᴀsᴇ...')
    files, offset, total_results = await get_search_results(movie, offset=0, filter=True)
    if files:
        k = (movie, files, offset, total_results)
        await pm_AutoFilter(bot, query, k)
    else:
        k = await query.message.edit('Tʜɪs Mᴏᴠɪᴇ Nᴏᴛ Fᴏᴜɴᴅ Iɴ Dᴀᴛᴀʙᴀsᴇ')
        await asyncio.sleep(10)
        await k.delete()


async def pm_AutoFilter(client, msg, status_msg=None, pmspoll=False):    
    if not pmspoll:
        message = msg
        if message.text.startswith("/"): 
            if status_msg:
                await status_msg.delete()
            return  # ignore commands
        if re.findall(r"((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text): 
            if status_msg:
                await status_msg.delete()
            return
        if 2 < len(message.text) < 100:
            search = message.text
            print(f"[PM_FILTER] Searching database for: '{search}'")
            import time
            search_start = time.time()
            files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
            search_duration = time.time() - search_start
            print(f"[PM_FILTER] Search completed in {search_duration:.2f}s - found {total_results} results")
            
            if not files: 
                print(f"[PM_FILTER] No files found for '{search}', initiating spell check")
                if status_msg:
                    await status_msg.edit_text("🔍 **No direct matches found.** Checking for similar titles...")
                return await pm_spoll_choker(msg, status_msg)
            else:
                print(f"[PM_FILTER] Found {len(files)} files, preparing response")
                
                # Debug button generation
                print(f"[PM_FILTER] SHORT_URL: {SHORT_URL}, SHORT_API: {bool(SHORT_API)}")
                print(f"[PM_FILTER] SINGLE_BUTTON: {SINGLE_BUTTON}")
                # Get first file name safely
                first_file_name = files[0].get('file_name', 'Unknown') if files else 'None'
                print(f"[PM_FILTER] First file: {first_file_name}")              
        else: 
            if status_msg:
                await status_msg.delete()
            return 
    else:
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = pmspoll
    pre = 'pmfilep' if PROTECT_CONTENT else 'pmfile'

    if SHORT_URL and SHORT_API:          
        btn = []
        for file in files:
            try:
                # Files are always dictionaries based on debug output
                file_name = file.get('file_name', 'Unknown')
                file_size = file.get('file_size', 0)
                file_id = file.get('_id', '')  # Note: _id instead of file_id
                
                if SINGLE_BUTTON:
                    btn.append([InlineKeyboardButton(text=f"[{get_size(file_size)}] {file_name}", url=await get_shortlink(f"https://telegram.dog/{temp.U_NAME}?start=pre_{file_id}"))])
                else:
                    btn.append([InlineKeyboardButton(text=f"{file_name}", url=await get_shortlink(f"https://telegram.dog/{temp.U_NAME}?start=pre_{file_id}")),
                               InlineKeyboardButton(text=f"{get_size(file_size)}", url=await get_shortlink(f"https://telegram.dog/{temp.U_NAME}?start=pre_{file_id}"))])
            except Exception as e:
                print(f"[PM_FILTER] Error processing file for SHORT_URL (main): {e}")
                continue
    else:        
        btn = []
        # Store search results in temp storage with shorter keys
        key = f"{message.from_user.id if message.from_user else 0}_{message.id}"
        temp.PM_SEARCH_RESULTS = getattr(temp, 'PM_SEARCH_RESULTS', {})
        temp.PM_SEARCH_RESULTS[key] = {'search': search, 'files': files}
        
        for i, file in enumerate(files):
            # Movie selection button - just show title and size
            try:
                # Files are always dictionaries based on debug output
                file_name = file.get('file_name', 'Unknown')
                file_size = file.get('file_size', 0)
                    
                btn.append([InlineKeyboardButton(
                    text=f"🎬 {file_name} [{get_size(file_size)}]", 
                    callback_data=f'select_movie#{key}#{i}'
                )])
            except Exception as e:
                print(f"[PM_FILTER] Error processing file {i}: {e}")
                continue        

    print(f"[PM_FILTER] Generated {len(btn)} movie buttons")
    btn.insert(0, [InlineKeyboardButton("🔗 ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ 🔗", "howdl")])
    print(f"[PM_FILTER] Added download help button, total buttons: {len(btn)}")
    if offset != "":
        key = f"{message.id}"
        temp.PM_BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [InlineKeyboardButton(text=f"❄️ ᴩᴀɢᴇꜱ 1/{math.ceil(int(total_results) / 6)}", callback_data="pages"),
            InlineKeyboardButton(text="ɴᴇxᴛ ➡️", callback_data=f"pmnext_{req}_{key}_{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton(text="❄️ ᴩᴀɢᴇꜱ 1/1", callback_data="pages")]
        )
    # Skip IMDB fetching for faster response - can be re-enabled if needed
    imdb = None
    TEMPLATE = IMDB_TEMPLATE
    if imdb:
        cap = TEMPLATE.format(
            group = message.chat.title,
            requested = message.from_user.mention,
            query = search,
            title = imdb['title'],
            votes = imdb['votes'],
            aka = imdb["aka"],
            seasons = imdb["seasons"],
            box_office = imdb['box_office'],
            localized_title = imdb['localized_title'],
            kind = imdb['kind'],
            imdb_id = imdb["imdb_id"],
            cast = imdb["cast"],
            runtime = imdb["runtime"],
            countries = imdb["countries"],
            certificates = imdb["certificates"],
            languages = imdb["languages"],
            director = imdb["director"],
            writer = imdb["writer"],
            producer = imdb["producer"],
            composer = imdb["composer"],
            cinematographer = imdb["cinematographer"],
            music_team = imdb["music_team"],
            distributors = imdb["distributors"],
            release_date = imdb['release_date'],
            year = imdb['year'],
            genres = imdb['genres'],
            poster = imdb['poster'],
            plot = imdb['plot'],
            rating = imdb['rating'],
            url = imdb['url'],
            **locals()
        )
    else:
        cap = f"🎬 **Found {len(files)} movies matching:** `{search}`\n\n📋 **Select a movie to see subtitle options:**"
        
    # Update status message with results (but don't show movie buttons yet)
    if status_msg and not pmspoll:
        print(f"[PM_FILTER] Updating status message with {len(files)} movies found")
        await status_msg.edit_text(f"✅ **Search completed!** Found {len(files)} movies.")
        print(f"[PM_FILTER] Status message updated successfully")
    
    print(f"[PM_FILTER] Preparing to send movie list, imdb: {bool(imdb)}")
    print(f"[PM_FILTER] Button count: {len(btn)}, Cap length: {len(cap) if cap else 0}")
    if imdb and imdb.get('poster'):
        try:
            hehe = await message.reply_photo(photo=imdb.get('poster'), caption=cap, quote=True, reply_markup=InlineKeyboardMarkup(btn))
            await asyncio.sleep(IMDB_DELET_TIME)
            await hehe.delete()            
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            hmm = await message.reply_photo(photo=poster, caption=cap, quote=True, reply_markup=InlineKeyboardMarkup(btn))           
            await asyncio.sleep(IMDB_DELET_TIME)
            await hmm.delete()            
        except Exception as e:
            logger.exception(e)
            cdp = await message.reply_text(cap, quote=True, reply_markup=InlineKeyboardMarkup(btn))
            await asyncio.sleep(IMDB_DELET_TIME)
            await cdp.delete()
    else:
        print(f"[PM_FILTER] No IMDB poster, sending text message")
        if status_msg and not pmspoll:
            print(f"[PM_FILTER] Editing status message with movie list")
            print(f"[PM_FILTER] Status_msg exists: {bool(status_msg)}, pmspoll: {pmspoll}")
            try:
                # Edit the status message to show results instead of creating new message
                print(f"[PM_FILTER] About to edit status message with {len(btn)} buttons")
                await status_msg.edit_text(cap, reply_markup=InlineKeyboardMarkup(btn))
                print(f"[PM_FILTER] Movie list sent successfully")
                # Don't auto-delete - let users interact with the buttons
                # await asyncio.sleep(IMDB_DELET_TIME)
                # await status_msg.delete()
                # print(f"[PM_FILTER] Status message deleted")
            except Exception as e:
                print(f"[PM_FILTER] Error updating status message: {e}")
                logger.error(f"PM_FILTER status update error: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[PM_FILTER] Creating new reply message")
            try:
                abc = await message.reply_text(cap, quote=True, reply_markup=InlineKeyboardMarkup(btn))
                print(f"[PM_FILTER] New message created successfully")
            except Exception as e:
                print(f"[PM_FILTER] Error creating new message: {e}")
                logger.error(f"PM_FILTER new message error: {e}")
            await asyncio.sleep(IMDB_DELET_TIME)
            await abc.delete()        
    if pmspoll:
        await msg.message.delete()


async def pm_spoll_choker(msg, status_msg=None):
    query = re.sub(r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)", "", msg.text, flags=re.IGNORECASE)  # plis contribute some common words
    query = query.strip() + " movie"
    g_s = await search_gagala(query)
    g_s += await search_gagala(msg.text)
    gs_parsed = []
    if not g_s:
        if status_msg:
            await status_msg.edit_text("❌ **I couldn't find any movie with that name.** Please check your spelling and try again.")
            await asyncio.sleep(10)
            return await status_msg.delete()
        else:
            k = await msg.reply("I Cᴏᴜʟᴅɴ'ᴛ Fɪɴᴅ Aɴʏ Mᴏᴠɪᴇ Iɴ Tʜᴀᴛ Nᴀᴍᴇ", quote=True)
            await asyncio.sleep(10)
            return await k.delete()
    regex = re.compile(r".*(imdb|wikipedia).*", re.IGNORECASE)  # look for imdb / wiki results
    gs = list(filter(regex.match, g_s))
    gs_parsed = [re.sub(r'\b(\-([a-zA-Z-\s])\-\simdb|(\-\s)?imdb|(\-\s)?wikipedia|\(|\)|\-|reviews|full|all|episode(s)?|film|movie|series)', '', i, flags=re.IGNORECASE) for i in gs]
    if not gs_parsed:
        reg = re.compile(r"watch(\s[a-zA-Z0-9_\s\-\(\)]*)*\|.*", re.IGNORECASE)  # match something like Watch Niram | Amazon Prime
        for mv in g_s:
            match = reg.match(mv)
            if match: gs_parsed.append(match.group(1))
    user = msg.from_user.id if msg.from_user else 0
    movielist = []
    gs_parsed = list(dict.fromkeys(gs_parsed))  # removing duplicates https://stackoverflow.com/a/7961425
    if len(gs_parsed) > 3: gs_parsed = gs_parsed[:3]
    # Skip IMDB calls for faster spell check response
    # if gs_parsed:
    #     for mov in gs_parsed:
    #         imdb_s = await get_poster(mov.strip(), bulk=True)  # searching each keyword in imdb
    #         if imdb_s: movielist += [movie.get('title') for movie in imdb_s]
    movielist += [(re.sub(r'(\-|\(|\)|_)', '', i, flags=re.IGNORECASE)).strip() for i in gs_parsed]
    movielist = list(dict.fromkeys(movielist))  # removing duplicates
    if not movielist:
        if status_msg:
            await status_msg.edit_text("❌ **I couldn't find anything related to that.** Please check your spelling and try again.")
            await asyncio.sleep(10)
            return await status_msg.delete()
        else:
            k = await msg.reply("I Cᴏᴜʟᴅɴ'ᴛ Fɪɴᴅ Aɴʏᴛʜɪɴɢ Rᴇʟᴀᴛᴇᴅ Tᴏ Tʜᴀᴛ. Cʜᴇᴄᴋ Yᴏᴜʀ Sᴘᴇʟʟɪɴɢ", quote=True)
            await asyncio.sleep(10)
            return await k.delete()
    temp.PM_SPELL[str(msg.id)] = movielist
    btn = [[InlineKeyboardButton(text=movie.strip(), callback_data=f"pmspolling#{user}#{k}")] for k, movie in enumerate(movielist)]
    btn.append([InlineKeyboardButton(text="Close", callback_data=f'pmspolling#{user}#close_spellcheck')])
    
    if status_msg:
        await status_msg.edit_text("🤔 **I couldn't find exact matches.** Did you mean any of these?", reply_markup=InlineKeyboardMarkup(btn))
    else:
        await msg.reply("I Cᴏᴜʟᴅɴ'ᴛ Fɪɴᴅ Aɴʏᴛʜɪɴɢ Rᴇʟᴀᴛᴇᴅ Tᴏ Tʜᴀᴛ. Dɪᴅ Yᴏᴜ Mᴇᴀɴ Aɴʏ Oɴᴇ Oғ Tʜᴇsᴇ?", reply_markup=InlineKeyboardMarkup(btn), quote=True)


# Initialize subtitle handler
subtitle_handler = SubtitleHandler()

# Movie selection callback handler  
@Client.on_callback_query(filters.regex(r'^select_movie#'))
async def movie_selected(client, callback_query):
    """Handle movie selection - show subtitle options"""
    try:
        print(f"[SELECT_MOVIE] Movie selected callback: {callback_query.data}")
        await callback_query.answer("Loading subtitle options...")  # Acknowledge button click

        _, key, file_index = callback_query.data.split('#')
        file_index = int(file_index)
        print(f"[SELECT_MOVIE] Key: {key}, File index: {file_index}")

        # Get stored search results
        if key not in temp.PM_SEARCH_RESULTS:
            return await callback_query.answer("❌ Search results expired. Please search again.", show_alert=True)
            
        search_data = temp.PM_SEARCH_RESULTS[key]
        files = search_data['files']
        search_query = search_data['search']
        
        if file_index >= len(files):
            return await callback_query.answer("❌ Invalid movie selection!", show_alert=True)
            
        selected_file = files[file_index]
        
        # Show subtitle language options
        # selected_file is a dictionary, not an object
        movie_name = selected_file.get('file_name', 'Unknown')
        movie_size = selected_file.get('file_size', 0) 
        movie_id = selected_file.get('_id', '')
        
        movie_info = (
            f"🎬 **Selected Movie**\n\n"
            f"📁 **Name:** `{movie_name}`\n"
            f"📊 **Size:** `{get_size(movie_size)}`\n\n"
            f"🌐 **Choose subtitle language or download without subtitles:**"
        )
        
        # Store file info in temp storage to avoid long callback data
        file_key = f"file_{movie_id}"
        temp.PM_SEARCH_RESULTS[file_key] = {'search': search_query, 'file': selected_file}
        
        # Create subtitle language buttons with short callback data
        btn = [
            [InlineKeyboardButton("🇬🇧 English", callback_data=f'download_with_sub#{file_key}#en')],
            [InlineKeyboardButton("🇪🇸 Spanish", callback_data=f'download_with_sub#{file_key}#es')], 
            [InlineKeyboardButton("🇫🇷 French", callback_data=f'download_with_sub#{file_key}#fr')],
            [InlineKeyboardButton("🇩🇪 German", callback_data=f'download_with_sub#{file_key}#de')],
            [InlineKeyboardButton("🇮🇳 Hindi", callback_data=f'download_with_sub#{file_key}#hi')],
            [InlineKeyboardButton("🇱🇰 Sinhala", callback_data=f'download_with_sub#{file_key}#si')],
            [InlineKeyboardButton("🌐 More Languages", callback_data=f'more_languages#{file_key}')],
            [InlineKeyboardButton("❌ No Subtitles Needed", callback_data=f'download_only#{movie_id}')],
            [InlineKeyboardButton("◀️ Back to Movies", callback_data=f'back_to_movies#{key}')]
        ]
        
        await callback_query.message.edit_text(movie_info, reply_markup=InlineKeyboardMarkup(btn))
        
    except Exception as e:
        logger.error(f"Error in movie selection: {e}")
        await callback_query.answer("❌ Error occurred. Please try again.", show_alert=True)

# Back to movie list handler
@Client.on_callback_query(filters.regex(r'^back_to_movies#'))
async def back_to_movies(client, callback_query):
    """Go back to movie list"""
    try:
        _, key = callback_query.data.split('#', 1)
        
        if key not in temp.PM_SEARCH_RESULTS:
            return await callback_query.answer("❌ Search results expired. Please search again.", show_alert=True)
            
        search_data = temp.PM_SEARCH_RESULTS[key]
        files = search_data['files']
        search_query = search_data['search']
        
        # Recreate the movie list
        btn = []
        for i, file in enumerate(files):
            # file is a dictionary
            file_name = file.get('file_name', 'Unknown')
            file_size = file.get('file_size', 0)
            btn.append([InlineKeyboardButton(
                text=f"🎬 {file_name} [{get_size(file_size)}]", 
                callback_data=f'select_movie#{key}#{i}'
            )])
            
        btn.insert(0, [InlineKeyboardButton("🔗 ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ 🔗", "howdl")])
        
        cap = f"🎬 **Found {len(files)} movies matching:** `{search_query}`\n\n📋 **Select a movie to see subtitle options:**"
        
        await callback_query.message.edit_text(cap, reply_markup=InlineKeyboardMarkup(btn))
        
    except Exception as e:
        logger.error(f"Error going back to movies: {e}")
        await callback_query.answer("❌ Error occurred. Please try again.", show_alert=True)

# Download only (no subtitles) handler
@Client.on_callback_query(filters.regex(r'^download_only#'))
async def download_movie_only(client, callback_query):
    """Download movie without subtitles"""
    try:
        print(f"[DOWNLOAD_ONLY] Starting download for callback: {callback_query.data}")
        _, file_id = callback_query.data.split('#', 1)
        print(f"[DOWNLOAD_ONLY] File ID: {file_id}")
        
        # Get file details and send directly
        file_details = await get_file_details(file_id)
        print(f"[DOWNLOAD_ONLY] File details retrieved: {len(file_details) if file_details else 0} files")
        
        if file_details and len(file_details) > 0:
            file = file_details[0]
            # Handle both dict and object formats for file from get_file_details
            file_name = getattr(file, 'file_name', file.get('file_name', 'Unknown')) if isinstance(file, dict) else file.file_name
            file_size = getattr(file, 'file_size', file.get('file_size', 0)) if isinstance(file, dict) else file.file_size
            
            print(f"[DOWNLOAD_ONLY] File info: {file_name} - {get_size(file_size)}")
            
            await callback_query.message.edit_text(
                f"📥 **Downloading movie...**\n\n"
                f"🎬 **Movie:** `{file_name}`\n"
                f"📊 **Size:** `{get_size(file_size)}`\n\n"
                f"⬇️ **Your download is starting...**"
            )
            
            # Send the movie file directly using the same logic as pmfile handler
            title = file_name
            size = get_size(file_size)
            f_caption = title
            
            try:
                if AUTH_CHANNEL:
                    is_sub = await is_subscribed(client, callback_query)
                    if not is_sub:
                        print(f"[DOWNLOAD_ONLY] User not subscribed, redirecting...")
                        return await callback_query.answer(url=f"https://t.me/{temp.U_NAME}?start=pmfile_{file_id}")
                
                print(f"[DOWNLOAD_ONLY] Sending movie: {title}")
                # Use the actual file_id from the file object, not the callback data
                actual_file_id = getattr(file, 'file_id', file.get('_id', '')) if isinstance(file, dict) else file.file_id
                print(f"[DOWNLOAD_ONLY] Using actual file_id: {actual_file_id}")
                
                await client.send_cached_media(
                    chat_id=callback_query.from_user.id, 
                    file_id=actual_file_id, 
                    caption=f_caption, 
                    protect_content=PROTECT_CONTENT
                )
                print(f"[DOWNLOAD] Movie sent successfully: {title}")
                    
            except Exception as e:
                print(f"[ERROR] Failed to send movie: {e}")
                print(f"[ERROR] Exception type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                await callback_query.answer(f"⚠️ Error sending movie: {e}", show_alert=True)
            
        else:
            await callback_query.answer("❌ Movie file not found!", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error in download only: {e}")
        await callback_query.answer("❌ Error occurred. Please try again.", show_alert=True)

# Download with subtitles handler
@Client.on_callback_query(filters.regex(r'^download_with_sub#'))
async def download_movie_with_subtitles(client, callback_query):
    """Download movie with selected subtitle language"""
    try:
        print(f"[DOWNLOAD_WITH_SUB] Starting download for callback: {callback_query.data}")
        _, file_key, language = callback_query.data.split('#', 2)
        print(f"[DOWNLOAD_WITH_SUB] File key: {file_key}, Language: {language}")
        
        # Get file info from temp storage
        if file_key not in temp.PM_SEARCH_RESULTS:
            return await callback_query.answer("❌ File data expired. Please search again.", show_alert=True)
            
        file_data = temp.PM_SEARCH_RESULTS[file_key]
        search_query = file_data['search']
        selected_file = file_data['file']
        print(f"[DOWNLOAD_WITH_SUB] Retrieved: Search={search_query}, File={selected_file.get('file_name', 'Unknown')}")
        
        # Show searching message
        await callback_query.message.edit_text(
            f"🔍 **Searching for {language.upper()} subtitles...**\n\n"
            f"🎬 **Movie:** Preparing download...\n"
            f"🌐 **Language:** `{language.upper()}`\n\n"
            f"⏱️ This usually takes 5-10 seconds..."
        )
        
        # Search for subtitles using hybrid approach for best accuracy
        movie_filename = selected_file.get('file_name', 'Unknown')
        print(f"[DOWNLOAD_WITH_SUB] Using movie filename for subtitle search: {movie_filename}")
        
        # Try with movie filename first (enhanced Subliminal will clean it properly)
        subtitles = await subtitle_handler.search_all_sources(movie_filename, language=language)
        
        # If no results with filename, try with cleaned movie title for fallback sources
        if not subtitles:
            cleaned_title = extract_clean_title(movie_filename)
            print(f"[DOWNLOAD_WITH_SUB] No subtitles found with filename, trying cleaned title: {cleaned_title}")
            subtitles = await subtitle_handler.search_all_sources(cleaned_title, language=language)
        
        # Final fallback to original search query  
        if not subtitles:
            print(f"[DOWNLOAD_WITH_SUB] No subtitles found with cleaned title, trying search query: {search_query}")
            subtitles = await subtitle_handler.search_all_sources(search_query, language=language)
        
        if subtitles:
            await callback_query.message.edit_text(
                f"📥 **Downloading subtitle...**\n\n"
                f"🎬 **Movie:** Preparing...\n"
                f"🌐 **Language:** `{language.upper()}`\n\n"
                f"⏱️ Trying {len(subtitles)} subtitle sources... (5-15 seconds)"
            )
            
            # Try downloading from multiple subtitle sources
            subtitle_content = None
            selected_subtitle = None
            tried_sources = []
            
            for subtitle in subtitles:
                try:
                    print(f"[DOWNLOAD_WITH_SUB] Trying subtitle from {subtitle['source']}: {subtitle['title']}")
                    subtitle_content = await subtitle_handler.download_subtitle(subtitle['download_url'], subtitle['source'], subtitle, language, search_query)
                    if subtitle_content:
                        print(f"[DOWNLOAD_WITH_SUB] Successfully downloaded from {subtitle['source']}")
                        selected_subtitle = subtitle
                        break
                    tried_sources.append(subtitle['source'])
                except Exception as e:
                    print(f"[DOWNLOAD_WITH_SUB] Failed to download from {subtitle['source']}: {e}")
                    tried_sources.append(subtitle['source'])
            
            if subtitle_content and selected_subtitle:
                # Create subtitle file with proper naming
                movie_title = extract_clean_title(selected_file.get('file_name', 'Unknown'))
                subtitle_filename = f"{movie_title}_{language}.srt"
                subtitle_file = io.BytesIO(subtitle_content.encode('utf-8'))
                subtitle_file.name = subtitle_filename

                await callback_query.message.reply_document(
                    subtitle_file,
                    caption=f"🎬📄 **Subtitle File**\n\n"
                           f"📄 **Movie:** `{selected_file.get('file_name', 'Unknown')}`\n"
                           f"🌐 **Language:** `{language.upper()}`\n"
                           f"🔗 **Source:** `{selected_subtitle['source']}`"
                )

                # Now send the movie file
                await callback_query.message.edit_text(
                    f"✅ **Subtitle sent! Now sending movie...**\n\n"
                    f"🎬 **Movie:** `{selected_file.get('file_name', 'Unknown')}`\n"
                    f"📊 **Size:** `{get_size(selected_file.get('file_size', 0))}`\n"
                    f"🌐 **Subtitle:** `{language.upper()}`\n\n"
                    f"⬇️ **Movie download starting...**"
                )

                # Send movie file using the same logic as pmfile handler
                title = selected_file.get('file_name', 'Unknown')
                f_caption = title

                try:
                    if AUTH_CHANNEL and not await is_subscribed(client, callback_query):
                        return await callback_query.answer(url=f"https://t.me/{temp.U_NAME}?start=pmfile_{selected_file.get('_id', '')}")
                    else:
                        # Use the actual file_id from the file object
                        actual_file_id = selected_file.get('_id', '')
                        print(f"[DOWNLOAD_WITH_SUB] Using actual file_id: {actual_file_id}")

                        await client.send_cached_media(
                            chat_id=callback_query.from_user.id,
                            file_id=actual_file_id,
                            caption=f_caption,
                            protect_content=PROTECT_CONTENT
                        )
                        print(f"[DOWNLOAD] Movie with subtitle sent successfully: {title}")

                except Exception as e:
                    await callback_query.answer(f"⚠️ Error sending movie: {e}", show_alert=True)
                    print(f"[ERROR] Failed to send movie: {e}")
            else:
                # Subtitles were found but all downloads failed - provide web links
                sources_tried = ", ".join(tried_sources) if tried_sources else "unknown sources"
                print(f"[SUBTITLE] All {len(tried_sources)} subtitle downloads failed - providing web links")

                # Get web links for manual download
                web_links = subtitle_handler.get_subtitle_web_links(movie_filename, language)

                # Extract file_id before using in f-string to avoid syntax error
                file_id_val = selected_file.get('_id', '')

                # Create buttons for web links
                web_link_buttons = [
                    [InlineKeyboardButton("🔗 OpenSubtitles.org", url=web_links['opensubtitles'])],
                    [InlineKeyboardButton("🔗 Subdl.com", url=web_links['subdl'])],
                    [InlineKeyboardButton("🔗 Subscene.com", url=web_links['subscene'])],
                    [InlineKeyboardButton("🔗 YifySubtitles.ch", url=web_links['yifysubtitles'])],
                    [InlineKeyboardButton("─────────────────", callback_data='separator')],
                    [InlineKeyboardButton("🇬🇧 Try English Instead", callback_data=f'download_with_sub#{file_key}#en')],
                    [InlineKeyboardButton("📥 Download Movie Only", callback_data=f'download_only#{file_id_val}')],
                    [InlineKeyboardButton("◀️ Back to Languages", callback_data=f'select_movie#{file_key.replace("file_", "")}')],
                    [InlineKeyboardButton("❌ Cancel", callback_data='cancel_download')]
                ]

                await callback_query.message.edit_text(
                    f"❌ **Automatic Download Failed**\n\n"
                    f"🎬 **Movie:** `{selected_file.get('file_name', 'Unknown')}`\n"
                    f"🌐 **Language:** `{language.upper()}`\n"
                    f"📊 **Sources tried:** {len(tried_sources)}\n\n"
                    f"**We tried:** {sources_tried}\n\n"
                    f"🔗 **Manual Download Links:**\n"
                    f"Click any link below to search and download subtitles manually:\n\n"
                    f"✅ All links open the search for your movie in **{language.upper()}** language.\n"
                    f"✅ Choose the subtitle that matches your movie version.\n"
                    f"✅ Download and sync with your video player.\n\n"
                    f"**Or try another option below:**",
                    reply_markup=InlineKeyboardMarkup(web_link_buttons)
                )
                    
        else:
            # No subtitles found in any API - provide web links for manual search
            print(f"[SUBTITLE] No subtitles found in any API - providing web links")

            # Get web links for manual download
            web_links = subtitle_handler.get_subtitle_web_links(movie_filename, language)

            # Extract file_id before using in f-string to avoid syntax error
            file_id_val = selected_file.get('_id', '')

            if language == 'si':
                message = (
                    f"❌ **No Sinhala Subtitles Found Automatically**\n\n"
                    f"🎬 **Movie:** `{selected_file.get('file_name', 'Unknown')}`\n\n"
                    f"🇱🇰 **Sinhala subtitles are rare** for some movies.\n\n"
                    f"🔗 **Try These Websites:**\n"
                    f"Click the links below to search manually. You might find subtitles that our bot couldn't auto-download:\n\n"
                    f"💡 **Tip:** Try English subtitles - they're more commonly available."
                )
            else:
                message = (
                    f"❌ **No {language.upper()} Subtitles Found Automatically**\n\n"
                    f"🎬 **Movie:** `{selected_file.get('file_name', 'Unknown')}`\n"
                    f"🌐 **Language:** `{language.upper()}`\n\n"
                    f"🔗 **Search These Subtitle Websites:**\n"
                    f"Click any link below to search manually. Sometimes subtitles exist but can't be auto-downloaded:\n\n"
                    f"✅ All links pre-search for your movie in **{language.upper()}**."
                )

            # Create buttons with web links first, then options
            btn = [
                [InlineKeyboardButton("🔗 OpenSubtitles.org", url=web_links['opensubtitles'])],
                [InlineKeyboardButton("🔗 Subdl.com", url=web_links['subdl'])],
                [InlineKeyboardButton("🔗 Subscene.com", url=web_links['subscene'])],
                [InlineKeyboardButton("🔗 YifySubtitles.ch", url=web_links['yifysubtitles'])],
                [InlineKeyboardButton("─────────────────", callback_data='separator')],
                [InlineKeyboardButton("🇬🇧 Try English Instead", callback_data=f'download_with_sub#{file_key}#en')],
                [InlineKeyboardButton("📥 Download Movie Only", callback_data=f'download_only#{file_id_val}')],
                [InlineKeyboardButton("◀️ Back to Languages", callback_data=f'select_movie#{file_key.replace("file_", "")}')],
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel_download')]
            ]

            await callback_query.message.edit_text(message, reply_markup=InlineKeyboardMarkup(btn))
        
    except Exception as e:
        logger.error(f"Error in download with subtitles: {e}")
        await callback_query.answer("❌ Error occurred while processing subtitles.", show_alert=True)

# More languages handler
@Client.on_callback_query(filters.regex(r'^more_languages#'))
async def show_more_languages(client, callback_query):
    """Show more language options"""
    try:
        _, file_key = callback_query.data.split('#', 1)
        
        # Extended language options
        btn = [
            [InlineKeyboardButton("🇯🇵 Japanese", callback_data=f'download_with_sub#{file_key}#ja')],
            [InlineKeyboardButton("🇰🇷 Korean", callback_data=f'download_with_sub#{file_key}#ko')],
            [InlineKeyboardButton("🇮🇹 Italian", callback_data=f'download_with_sub#{file_key}#it')],
            [InlineKeyboardButton("🇵🇹 Portuguese", callback_data=f'download_with_sub#{file_key}#pt')],
            [InlineKeyboardButton("🇷🇺 Russian", callback_data=f'download_with_sub#{file_key}#ru')],
            [InlineKeyboardButton("🇨🇳 Chinese", callback_data=f'download_with_sub#{file_key}#zh')],
            [InlineKeyboardButton("🇦🇷 Arabic", callback_data=f'download_with_sub#{file_key}#ar')],
            [InlineKeyboardButton("◀️ Back to Main", callback_data=f'back_to_main_langs#{file_key}')],
            [InlineKeyboardButton("❌ No Subtitles", callback_data=f'back_to_movies#{file_key}')]
        ]
        
        await callback_query.message.edit_text(
            f"🌐 **More Subtitle Languages**\n\n"
            f"Choose your preferred language:",
            reply_markup=InlineKeyboardMarkup(btn)
        )
        
    except Exception as e:
        logger.error(f"Error in more languages: {e}")
        await callback_query.answer("❌ Error occurred. Please try again.", show_alert=True)

# Back to main languages
@Client.on_callback_query(filters.regex(r'^back_to_main_langs#'))
async def back_to_main_languages(client, callback_query):
    """Go back to main language selection"""
    try:
        _, file_key = callback_query.data.split('#', 1)
        
        # Get file info from temp storage
        if file_key not in temp.PM_SEARCH_RESULTS:
            return await callback_query.answer("❌ File data expired. Please search again.", show_alert=True)
            
        file_data = temp.PM_SEARCH_RESULTS[file_key]
        selected_file = file_data['file']
            
        movie_info = (
            f"🎬 **Selected Movie**\n\n"
            f"📁 **Name:** `{selected_file.get('file_name', 'Unknown')}`\n"
            f"📊 **Size:** `{get_size(selected_file.get('file_size', 0))}`\n\n"
            f"🌐 **Choose subtitle language or download without subtitles:**"
        )

        # Extract file_id before using in f-string to avoid syntax error
        file_id_val = selected_file.get('_id', '')
        # Main language buttons
        btn = [
            [InlineKeyboardButton("🇬🇧 English", callback_data=f'download_with_sub#{file_key}#en')],
            [InlineKeyboardButton("🇪🇸 Spanish", callback_data=f'download_with_sub#{file_key}#es')],
            [InlineKeyboardButton("🇫🇷 French", callback_data=f'download_with_sub#{file_key}#fr')],
            [InlineKeyboardButton("🇩🇪 German", callback_data=f'download_with_sub#{file_key}#de')],
            [InlineKeyboardButton("🇮🇳 Hindi", callback_data=f'download_with_sub#{file_key}#hi')],
            [InlineKeyboardButton("🇱🇰 Sinhala", callback_data=f'download_with_sub#{file_key}#si')],
            [InlineKeyboardButton("🌐 More Languages", callback_data=f'more_languages#{file_key}')],
            [InlineKeyboardButton("❌ No Subtitles", callback_data=f'download_only#{file_id_val}')],
            [InlineKeyboardButton("◀️ Back to Movies", callback_data=f'back_to_movies#{file_key}')]
        ]
        
        await callback_query.message.edit_text(movie_info, reply_markup=InlineKeyboardMarkup(btn))
            
    except Exception as e:
        logger.error(f"Error in back to main languages: {e}")
        await callback_query.answer("❌ Error occurred. Please try again.", show_alert=True)

# Cancel download handler
@Client.on_callback_query(filters.regex(r'^cancel_download$'))
async def cancel_download(client, callback_query):
    """Cancel download operation"""
    await callback_query.message.edit_text(
        "❌ **Download cancelled by user.**\n\n"
        "You can start a new search anytime by sending a movie name."
    )

# Separator handler (for UI separators - just acknowledge)
@Client.on_callback_query(filters.regex(r'^separator$'))
async def separator_handler(client, callback_query):
    """Handle separator button clicks"""
    await callback_query.answer("This is just a separator", show_alert=False)




