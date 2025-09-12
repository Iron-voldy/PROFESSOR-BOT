import asyncio, re, ast, time, math, logging, random, pyrogram, shutil, psutil 

# Pyrogram Functions
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram import Client, filters, enums 
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid

# Helper Function
from Script import script
from utils import get_size, is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings, get_shortlink, get_time, humanbytes 
from .ExtraMods.carbon import make_carbon

# Subtitle Handler
from .subtitle_handler import SubtitleHandler, LANGUAGE_MAPPING, create_language_selection_keyboard, create_more_languages_keyboard, create_subtitle_results_keyboard

# Database Function 
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, make_inactive
from database.simple_db import get_file_details, get_search_results, MediaDocument
from database.filters_mdb import del_all, find_filter, get_filters
from database.gfilters_mdb import find_gfilter, get_gfilters
from database.users_chats_db import db

# Image Editor Function
from image.edit_1 import bright, mix, black_white, g_blur, normal_blur, box_blur
from image.edit_2 import circle_with_bg, circle_without_bg, sticker, edge_curved, contrast, sepia_mode, pencil, cartoon                             
from image.edit_3 import green_border, blue_border, black_border, red_border
from image.edit_4 import rotate_90, rotate_180, rotate_270, inverted, round_sticker, removebg_white, removebg_plain, removebg_sticker
from image.edit_5 import normalglitch_1, normalglitch_2, normalglitch_3, normalglitch_4, normalglitch_5, scanlineglitch_1, scanlineglitch_2, scanlineglitch_3, scanlineglitch_4, scanlineglitch_5

# Configuration
from info import ADMINS, AUTH_CHANNEL, AUTH_USERS, CUSTOM_FILE_CAPTION, AUTH_GROUPS, P_TTI_SHOW_OFF, PICS, IMDB, PM_IMDB, SINGLE_BUTTON, PROTECT_CONTENT, \
    SPELL_CHECK_REPLY, IMDB_TEMPLATE, IMDB_DELET_TIME, START_MESSAGE, PMFILTER, G_FILTER, BUTTON_LOCK, BUTTON_LOCK_TEXT, SHORT_URL, SHORT_API


logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)



@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
        
    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type
        if chat_type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    return await query.message.edit_text("Make Sure I'm Present In Your Group!!", quote=True)
            else:
                return await query.message.edit_text("I'm Not Connected To Any Groups!\ncheck /Connections Or Connect To Any Groups", quote=True)
        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            title = query.message.chat.title
        else: return
        st = await client.get_chat_member(grp_id, userid)
        if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS): await del_all(query.message, grp_id, title)
        else: await query.answer("You Need To Be Group Owner Or An Auth User To Do That!", show_alert=True)
        
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type
        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()
        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try: await query.message.reply_to_message.delete()
                except: pass
            else: await query.answer("Buddy Don't Touch Others Property 😁", show_alert=True)
            
    elif "groupcb" in query.data:
        group_id = query.data.split(":")[1]
        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id
        if act == "":
            stat = "Connect"
            cb = "connectcb"
        else:
            stat = "Disconnect"
            cb = "disconnect"
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
            InlineKeyboardButton("Delete", callback_data=f"deletecb:{group_id}")
            ],[
            InlineKeyboardButton("Back", callback_data="backcb")]
        ])
        await query.message.edit_text(f"Group Name:- **{title}**\nGroup Id:- `{group_id}`", reply_markup=keyboard, parse_mode=enums.ParseMode.MARKDOWN)
      
    elif "connectcb" in query.data:
        group_id = query.data.split(":")[1]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id
        mkact = await make_active(str(user_id), str(group_id))
        if mkact: await query.message.edit_text(f"Connected To: **{title}**", parse_mode=enums.ParseMode.MARKDOWN,)
        else: await query.message.edit_text('Some Error Occurred!!', parse_mode="md")
       
    elif "disconnect" in query.data:
        group_id = query.data.split(":")[1]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id
        mkinact = await make_inactive(str(user_id))
        if mkinact: await query.message.edit_text(f"Disconnected From **{title}**", parse_mode=enums.ParseMode.MARKDOWN)
        else: await query.message.edit_text(f"Some Error Occurred!!", parse_mode=enums.ParseMode.MARKDOWN)
      
    elif "deletecb" in query.data:
        user_id = query.from_user.id
        group_id = query.data.split(":")[1]
        delcon = await delete_connection(str(user_id), str(group_id))
        if delcon: await query.message.edit_text("Successfully Deleted Connection")
        else: await query.message.edit_text(f"Some Error Occurred!!", parse_mode=enums.ParseMode.MARKDOWN)
       
    elif query.data == "backcb":
        userid = query.from_user.id
        groupids = await all_connections(str(userid))
        if groupids is None:
            return await query.message.edit_text("There Are No Active Connections!! Connect To Some Groups First.")
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append([InlineKeyboardButton(f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}")])
            except: pass
        if buttons: await query.message.edit_text("Your Connected Group Details ;\n\n", reply_markup=InlineKeyboardMarkup(buttons))
            
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]        
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)       
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
            
    elif "galert" in query.data:
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]             
        reply_text, btn, alerts, fileid = await find_gfilter("gfilters", keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    
    if query.data.startswith("pmfile"):
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_: return await query.answer('No Such File Exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = f_caption = f"{title}"
        if CUSTOM_FILE_CAPTION:
            try: f_caption = CUSTOM_FILE_CAPTION.format(mention=query.from_user.mention, file_name='' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)                                                                                                      
            except Exception as e: logger.exception(e)
        try:                  
            if AUTH_CHANNEL and not await is_subscribed(client, query):
                return await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
            else:
                await client.send_cached_media(chat_id=query.from_user.id, file_id=file_id, caption=f_caption, protect_content=True if ident == "pmfilep" else False)                       
        except Exception as e:
            await query.answer(f"⚠️ Eʀʀᴏʀ {e}", show_alert=True)
        
    if query.data.startswith("file"):        
        ident, req, file_id = query.data.split("#")
        if BUTTON_LOCK:
            if int(req) not in [query.from_user.id, 0]:
                return await query.answer(BUTTON_LOCK_TEXT.format(query=query.from_user.first_name), show_alert=True)
        files_ = await get_file_details(file_id)
        if not files_: return await query.answer('No Such File Exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        
        # Show subtitle selection before sending file
        try:
            movie_name = title.replace('.', ' ').replace('_', ' ')
            movie_name = re.sub(r'\b(1080p|720p|480p|HDTV|DVDRip|BRRip|x264|x265|HEVC|AAC|MP3|WEB-DL|BluRay)\b', '', movie_name, flags=re.IGNORECASE)
            movie_name = re.sub(r'\s+', ' ', movie_name).strip()
            
            keyboard = create_language_selection_keyboard(query.from_user.id, file_id, movie_name)
            await query.message.edit_text(
                f"🎬 **{title}**\n📁 **Size:** {size}\n\n"
                f"🔤 **Select subtitle language:**\n\n"
                f"Choose your preferred subtitle language or select 'No Subtitles' to get the file directly.",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error showing subtitle selection: {e}")
            # Fallback to original behavior
            f_caption = f"{title}"
            settings = await get_settings(query.message.chat.id)
            if CUSTOM_FILE_CAPTION:
                try: f_caption = CUSTOM_FILE_CAPTION.format(mention=query.from_user.mention, file_name='' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)                               
                except Exception as e: logger.exception(e)
            try:
                if AUTH_CHANNEL and not await is_subscribed(client, query):
                    return await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                elif settings['botpm']:
                    return await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                else:
                    await client.send_cached_media(chat_id=query.from_user.id, file_id=file_id, caption=f_caption, protect_content=True if ident == "filep" else False)
                    await query.answer('Cʜᴇᴄᴋ PM, I Hᴀᴠᴇ Sᴇɴᴛ Fɪʟᴇs Iɴ Pᴍ', show_alert=True)
            except UserIsBlocked:
                await query.answer('Uɴʙʟᴏᴄᴋ Tʜᴇ Bᴏᴛ Mᴀʜɴ !', show_alert=True)
            except PeerIdInvalid:
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
            except Exception as e:
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
     
    elif query.data.startswith("checksub"):
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            return await query.answer("I Lɪᴋᴇ Yᴏᴜʀ Sᴍᴀʀᴛɴᴇss, Bᴜᴛ Dᴏɴ'ᴛ Bᴇ Oᴠᴇʀsᴍᴀʀᴛ Oᴋᴀʏ 😏", show_alert=True)
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_: return await query.answer('NO SUCH FILE EXIST....')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = f_caption = f"{title}"
        if CUSTOM_FILE_CAPTION:
            try: f_caption = CUSTOM_FILE_CAPTION.format(mention=query.from_user.mention, file_name='' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)  
            except Exception as e: logger.exception(e)
        await client.send_cached_media(chat_id=query.from_user.id, file_id=file_id, caption=f_caption, protect_content=True if ident == 'checksubp' else False)

    elif query.data == "removebg":
        buttons = [[
            InlineKeyboardButton(text="𝖶𝗂𝗍𝗁 𝖶𝗁𝗂𝗍𝖾 𝖡𝖦", callback_data="rmbgwhite"),
            InlineKeyboardButton(text="𝖶𝗂𝗍𝗁𝗈𝗎𝗍 𝖡𝖦", callback_data="rmbgplain"),
            ],[
            InlineKeyboardButton(text="𝖲𝗍𝗂𝖼𝗄𝖾𝗋", callback_data="rmbgsticker"),
            ],[
            InlineKeyboardButton('𝙱𝙰𝙲𝙺', callback_data='photo')
        ]]
        await query.message.edit_text("**Select Required Mode**", reply_markup=InlineKeyboardMarkup(buttons))
            
    elif query.data == "stick":
        buttons = [[
            InlineKeyboardButton(text="𝖭𝗈𝗋𝗆𝖺𝗅", callback_data="stkr"),
            InlineKeyboardButton(text="𝖤𝖽𝗀𝖾 𝖢𝗎𝗋𝗏𝖾𝖽", callback_data="cur_ved"),
            ],[                    
            InlineKeyboardButton(text="𝖢𝗂𝗋𝖼𝗅𝖾", callback_data="circle_sticker")
            ],[
            InlineKeyboardButton('𝙱𝙰𝙲𝙺', callback_data='photo')
        ]]              
        await query.message.edit("**Select A Type**", reply_markup=InlineKeyboardMarkup(buttons))          
            
    elif query.data == "rotate":
        buttons = [[
            InlineKeyboardButton(text="180", callback_data="180"),
            InlineKeyboardButton(text="90", callback_data="90")
            ],[
            InlineKeyboardButton(text="270", callback_data="270")
            ],[
            InlineKeyboardButton('𝙱𝙰𝙲𝙺', callback_data='photo')
        ]]
        await query.message.edit_text("**Select The Degree**", reply_markup=InlineKeyboardMarkup(buttons))
            
    elif query.data == "glitch":
        buttons = [[
            InlineKeyboardButton(text="𝖭𝗈𝗋𝗆𝖺𝗅", callback_data="normalglitch"),
            InlineKeyboardButton(text="𝖲𝖼𝖺𝗇 𝖫𝖺𝗂𝗇𝗌", callback_data="scanlineglitch")
            ],[
            InlineKeyboardButton('𝙱𝙰𝙲𝙺', callback_data='photo')
        ]]
        await query.message.edit_text("**Select Required Mode**", reply_markup=InlineKeyboardMarkup(buttons))
            
    elif query.data == "normalglitch":
        buttons = [[
            InlineKeyboardButton(text="1", callback_data="normalglitch1"),
            InlineKeyboardButton(text="2", callback_data="normalglitch2"),
            InlineKeyboardButton(text="3", callback_data="normalglitch3"),
            ],[
            InlineKeyboardButton(text="4", callback_data="normalglitch4"),
            InlineKeyboardButton(text="5", callback_data="normalglitch5"),
            ],[
            InlineKeyboardButton('𝙱𝙰𝙲𝙺', callback_data='glitch')
            ]]
        await query.message.edit_text(text="**Select Glitch Power Level**", reply_markup=InlineKeyboardMarkup(buttons))
           
    elif query.data == "scanlineglitch":
        buttons = [[
            InlineKeyboardButton(text="1", callback_data="scanlineglitch1"),
            InlineKeyboardButton(text="2", callback_data="scanlineglitch2"),
            InlineKeyboardButton(text="3", callback_data="scanlineglitch3"),
            ],[
            InlineKeyboardButton(text="4", callback_data="scanlineglitch4"),
            InlineKeyboardButton(text="5", callback_data="scanlineglitch5"),
            ],[
            InlineKeyboardButton('𝙱𝙰𝙲𝙺', callback_data='glitch')
        ]]
        await query.message.edit_text("**Select Glitch Power Level**", reply_markup=InlineKeyboardMarkup(buttons))
            
    elif query.data == "blur":
        buttons = [[
            InlineKeyboardButton(text="𝖡𝗈𝗑", callback_data="box"),
            InlineKeyboardButton(text="𝖭𝗈𝗋𝗆𝖺𝗅", callback_data="normal"),
            ],[
            InlineKeyboardButton(text="𝖦𝖺𝗎𝗌𝗌𝗂𝖺𝗇", callback_data="gas")
            ],[
            InlineKeyboardButton('𝙱𝙰𝙲𝙺', callback_data='photo')
        ]]
        await query.message.edit("**Select A Type**", reply_markup=InlineKeyboardMarkup(buttons))
            
    elif query.data == "circle":
        buttons = [[
            InlineKeyboardButton(text="𝖶𝗂𝗍𝗁 𝖡𝖦", callback_data="circlewithbg"),
            InlineKeyboardButton(text="𝖶𝗂𝗍𝗁𝗈𝗎𝗍 𝖡𝖦", callback_data="circlewithoutbg"),
            ],[
            InlineKeyboardButton('𝙱𝙰𝙲𝙺', callback_data='photo')
        ]]
        await query.message.edit_text("**Select Required Mode**", reply_markup=InlineKeyboardMarkup(buttons))
            
    elif query.data == "border":
        buttons = [[
            InlineKeyboardButton(text="𝖱𝖾𝖽", callback_data="red"),
            InlineKeyboardButton(text="𝖦𝗋𝖾𝖾𝗇", callback_data="green"),
            ],[
            InlineKeyboardButton(text="𝖡𝗅𝖺𝖼𝗄", callback_data="black"),
            InlineKeyboardButton(text="𝖡𝗅𝗎𝖾", callback_data="blue"),
            ],[                    
            InlineKeyboardButton('𝙱𝙰𝙲𝙺', callback_data='photo')   
        ]]           
        await query.message.edit("**Select Border**", reply_markup=InlineKeyboardMarkup(buttons))
   
    elif query.data == "photo":
        buttons = [[
            InlineKeyboardButton(text="𝖡𝗋𝗂𝗀𝗍𝗁", callback_data="bright"),
            InlineKeyboardButton(text="𝖬𝗂𝗑𝖾𝖽", callback_data="mix"),
            InlineKeyboardButton(text="𝖡 & 𝖶", callback_data="b|w"),
            ],[
            InlineKeyboardButton(text="𝖢𝗂𝗋𝖼𝗅𝖾", callback_data="circle"),
            InlineKeyboardButton(text="𝖡𝗅𝗎𝗋", callback_data="blur"),
            InlineKeyboardButton(text="𝖡𝗈𝗋𝖽𝖾𝗋", callback_data="border"),
            ],[
            InlineKeyboardButton(text="𝖲𝗍𝗂𝖼𝗄𝖾𝗋", callback_data="stick"),
            InlineKeyboardButton(text="𝖱𝗈𝗍𝖺𝗍𝖾", callback_data="rotate"),
            InlineKeyboardButton(text="𝖢𝗈𝗇𝗍𝗋𝖺𝗌𝗍", callback_data="contrast"),
            ],[
            InlineKeyboardButton(text="𝖲𝖾𝗉𝗂𝖺", callback_data="sepia"),
            InlineKeyboardButton(text="𝖯𝖾𝗇𝖼𝗂𝗅", callback_data="pencil"),
            InlineKeyboardButton(text="𝖢𝖺𝗋𝗍𝗈𝗈𝗇", callback_data="cartoon"),
            ],[
            InlineKeyboardButton(text="𝖨𝗇𝗏𝖾𝗋𝗍", callback_data="inverted"),
            InlineKeyboardButton(text="𝖦𝗅𝗂𝗍𝖼𝗁", callback_data="glitch"),
            InlineKeyboardButton(text="𝖱𝖾𝗆𝗈𝗏𝖾 𝖡𝖦", callback_data="removebg")
            ],[
            InlineKeyboardButton(text="𝖢𝗅𝗈𝗌𝖾", callback_data="close_data")
        ]]
        await query.message.edit_text("Sᴇʟᴇᴄᴛ Yᴏᴜʀ Rᴇǫᴜɪʀᴇᴅ Mᴏᴅᴇ Fʀᴏᴍ Bᴇʟᴏᴡ!", reply_markup=InlineKeyboardMarkup(buttons))
               
    elif query.data == "bright":
        await bright(client, query.message)
    elif query.data == "mix":
        await mix(client, query.message)
    elif query.data == "b|w":
        await black_white(client, query.message)
    elif query.data == "circlewithbg":
        await circle_with_bg(client, query.message)
    elif query.data == "circlewithoutbg":
        await circle_without_bg(client, query.message)
    elif query.data == "green":
        await green_border(client, query.message)
    elif query.data == "blue":
        await blue_border(client, query.message)
    elif query.data == "red":
        await red_border(client, query.message)
    elif query.data == "black":
        await black_border(client, query.message)
    elif query.data == "circle_sticker":
        await round_sticker(client, query.message)
    elif query.data == "inverted":
        await inverted(client, query.message)
    elif query.data == "stkr":
        await sticker(client, query.message)
    elif query.data == "cur_ved":
        await edge_curved(client, query.message)
    elif query.data == "90":
        await rotate_90(client, query.message)
    elif query.data == "180":
        await rotate_180(client, query.message)
    elif query.data == "270":
        await rotate_270(client, query.message)
    elif query.data == "contrast":
        await contrast(client, query.message)
    elif query.data == "box":
        await box_blur(client, query.message)
    elif query.data == "gas":
        await g_blur(client, query.message)
    elif query.data == "normal":
        await normal_blur(client, query.message)
    elif query.data == "sepia":
        await sepia_mode(client, query.message)
    elif query.data == "pencil":
        await pencil(client, query.message)
    elif query.data == "cartoon":
        await cartoon(client, query.message)
    elif query.data == "normalglitch1":
        await normalglitch_1(client, query.message)
    elif query.data == "normalglitch2":
        await normalglitch_2(client, query.message)
    elif query.data == "normalglitch3":
        await normalglitch_3(client, query.message)
    elif query.data == "normalglitch4":
        await normalglitch_4(client, query.message)
    elif query.data == "normalglitch5":
        await normalglitch_5(client, query.message)
    elif query.data == "scanlineglitch1":
        await scanlineglitch_1(client, query.message)
    elif query.data == "scanlineglitch2":
        await scanlineglitch_2(client, query.message)
    elif query.data == "scanlineglitch3":
        await scanlineglitch_3(client, query.message)
    elif query.data == "scanlineglitch4":
        await scanlineglitch_4(client, query.message)
    elif query.data == "scanlineglitch5":
        await scanlineglitch_5(client, query.message)
    elif query.data == "rmbgwhite":
        await removebg_white(client, query.message)
    elif query.data == "rmbgplain":
        await removebg_plain(client, query.message)
    elif query.data == "rmbgsticker":
        await removebg_sticker(client, query.message)
    elif query.data == "pages":
        await query.answer("🤨 Cᴜʀɪᴏsɪᴛʏ Is A Lɪᴛᴛʟᴇ Mᴏʀᴇ, Isɴ'ᴛ Iᴛ? 😁", show_alert=True)
    elif query.data == "howdl":
        try: await query.answer(script.HOW_TO_DOWNLOAD.format(query.from_user.first_name), show_alert=True)
        except: await query.message.edit(script.HOW_TO_DOWNLOAD.format(query.from_user.first_name))

    elif query.data == "start":                        
        buttons = [[
            InlineKeyboardButton("➕️ Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Cʜᴀᴛ ➕", url=f"http://t.me/{temp.U_NAME}?startgroup=true")
            ],[
            InlineKeyboardButton("Sᴇᴀʀᴄʜ 🔎", switch_inline_query_current_chat=''), 
            InlineKeyboardButton("Cʜᴀɴɴᴇʟ 🔈", url="https://t.me/mkn_bots_updates")
            ],[      
            InlineKeyboardButton("Hᴇʟᴩ 🕸️", callback_data="help"),
            InlineKeyboardButton("Aʙᴏᴜᴛ ✨", callback_data="about")
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), START_MESSAGE.format(user=query.from_user.mention, bot=client.mention), enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))
       
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('⚙️ Aᴅᴍɪɴ Pᴀɴᴇʟ ⚙️', 'admin')            
            ],[
            InlineKeyboardButton('Fɪʟᴛᴇʀꜱ', 'openfilter'),
            InlineKeyboardButton('Cᴏɴɴᴇᴄᴛ', 'coct')
            ],[                       
            InlineKeyboardButton('Fɪʟᴇ Sᴛᴏʀᴇ', 'newdata'),
            InlineKeyboardButton('Exᴛʀᴀ Mᴏᴅᴇ', 'extmod')
            ],[           
            InlineKeyboardButton('Gʀᴏᴜᴩ Mᴀɴᴀɢᴇʀ', 'gpmanager'), 
            InlineKeyboardButton('Bᴏᴛ Sᴛᴀᴛᴜꜱ ❄️', 'stats')
            ],[
            InlineKeyboardButton('🎬 Sᴜʙᴛɪᴛʟᴇꜱ', 'subtitle_help')
            ],[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'start')           
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.HELP_TXT.format(query.from_user.mention), enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))     
        
    elif query.data == "about":
        buttons= [[
            InlineKeyboardButton('Sᴏᴜʀᴄᴇ Cᴏᴅᴇ 📜', 'source')
            ],[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'start')          
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.ABOUT_TXT.format(temp.B_NAME), enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))
        
    elif query.data == "source":
        buttons = [[
            InlineKeyboardButton('ꜱᴏᴜʀᴄᴇ ᴄᴏᴅᴇ', url='https://github.com/MrMKN/PROFESSOR-BOT')
            ],[
            InlineKeyboardButton('‹ Bᴀᴄᴋ', 'about')
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.SOURCE_TXT, enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))
      
    elif query.data == "admin":
        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'help')           
        ]]
        if query.from_user.id not in ADMINS:
            return await query.answer("Sᴏʀʀʏ Tʜɪs Mᴇɴᴜ Oɴʟʏ Fᴏʀ Mʏ Aᴅᴍɪɴs ⚒️", show_alert=True)
        await query.message.edit("Pʀᴏᴄᴇꜱꜱɪɴɢ Wᴀɪᴛ Fᴏʀ 15 ꜱᴇᴄ...")
        total, used, free = shutil.disk_usage(".")
        stats = script.SERVER_STATS.format(get_time(time.time() - client.uptime), psutil.cpu_percent(), psutil.virtual_memory().percent, humanbytes(total), humanbytes(used), psutil.disk_usage('/').percent, humanbytes(free))            
        stats_pic = await make_carbon(stats, True)
        await query.edit_message_media(InputMediaPhoto(stats_pic, script.ADMIN_TXT, enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))
        
    elif query.data == "openfilter":
        buttons = [[
            InlineKeyboardButton('AᴜᴛᴏFɪʟᴛᴇʀ', 'autofilter'),
            InlineKeyboardButton('MᴀɴᴜᴀʟFɪʟᴛᴇʀ', 'manuelfilter')
            ],[
            InlineKeyboardButton('GʟᴏʙᴀʟFɪʟᴛᴇʀ', 'globalfilter')
            ],[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'help')           
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.FILTER_TXT, enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))
        
    elif query.data == "autofilter":
        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'openfilter')           
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.AUTOFILTER_TXT, enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))
        
    elif query.data == "manuelfilter":
        buttons = [[
            InlineKeyboardButton('Bᴜᴛᴛᴏɴ Fᴏʀᴍᴀᴛ', 'button')
            ],[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'openfilter')           
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.MANUELFILTER_TXT, enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))
        
    elif query.data == "globalfilter":
        buttons = [[
            InlineKeyboardButton('Bᴜᴛᴛᴏɴ Fᴏʀᴍᴀᴛ', 'buttong')
            ],[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'openfilter')           
        ]]
        if query.from_user.id not in ADMINS:
            return await query.answer("Sᴏʀʀʏ Tʜɪs Mᴇɴᴜ Oɴʟʏ Fᴏʀ Mʏ Aᴅᴍɪɴs ⚒️", show_alert=True)
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.GLOBALFILTER_TXT, enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))
        
    elif query.data.startswith("button"):
        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', f"{'manuelfilter' if query.data == 'button' else 'globalfilter'}")           
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.BUTTON_TXT, enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))
   
    elif query.data == "coct":
        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'help')           
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.CONNECTION_TXT, enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))
         
    elif query.data == "newdata":
        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'help')           
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.FILE_TXT, enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))
        
    elif query.data == "extmod":
        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'help')           
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.EXTRAMOD_TXT, enums.ParseMode.HTML),             reply_markup=InlineKeyboardMarkup(buttons))
        
    elif query.data == "gpmanager":
        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'help')           
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.GROUPMANAGER_TXT, enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))           
        
    elif query.data == "stats":
        buttons = [[
            InlineKeyboardButton('⟳ Rᴇꜰʀᴇꜱʜ', 'stats'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'help')           
        ]]
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit('ʟᴏᴀᴅɪɴɢ....')
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), script.STATUS_TXT.format(total, users, chats, monsize, free), enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))
    
    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))
        if str(grp_id) != str(grpid):
            return await query.message.edit("Yᴏᴜʀ Aᴄᴛɪᴠᴇ Cᴏɴɴᴇᴄᴛɪᴏɴ Hᴀs Bᴇᴇɴ Cʜᴀɴɢᴇᴅ. Gᴏ Tᴏ /settings")
        if status == "True": await save_group_settings(grpid, set_type, False)
        else: await save_group_settings(grpid, set_type, True)
        settings = await get_settings(grpid)
        if settings is not None:
            buttons = [[
                InlineKeyboardButton(f"ꜰɪʟᴛᴇʀ ʙᴜᴛᴛᴏɴ : {'sɪɴɢʟᴇ' if settings['button'] else 'ᴅᴏᴜʙʟᴇ'}", f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],[
                InlineKeyboardButton(f"ꜰɪʟᴇ ɪɴ ᴩᴍ ꜱᴛᴀʀᴛ: {'ᴏɴ' if settings['botpm'] else 'ᴏꜰꜰ'}", f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
                ],[                
                InlineKeyboardButton(f"ʀᴇꜱᴛʀɪᴄᴛ ᴄᴏɴᴛᴇɴᴛ : {'ᴏɴ' if settings['file_secure'] else 'ᴏꜰꜰ'}", f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],[
                InlineKeyboardButton(f"ɪᴍᴅʙ ɪɴ ꜰɪʟᴛᴇʀ : {'ᴏɴ' if settings['imdb'] else 'ᴏꜰꜰ'}", f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],[
                InlineKeyboardButton(f"ꜱᴩᴇʟʟɪɴɢ ᴄʜᴇᴄᴋ : {'ᴏɴ' if settings['spell_check'] else 'ᴏꜰꜰ'}", f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],[
                InlineKeyboardButton(f"ᴡᴇʟᴄᴏᴍᴇ ᴍᴇꜱꜱᴀɢᴇ : {'ᴏɴ' if settings['welcome'] else 'ᴏꜰꜰ'}", f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
            ]]
            await query.message.edit_reply_markup(InlineKeyboardMarkup(buttons))

    # Subtitle Selection Handlers
    elif query.data.startswith("subtitle#"):
        try:
            _, user_id, file_id, language, movie_name = query.data.split("#", 4)
            if int(user_id) != query.from_user.id:
                return await query.answer("This is not for you!", show_alert=True)
            
            await query.message.edit_text("🔍 **Searching for subtitles...**\n\nPlease wait while I search for subtitles in your selected language.")
            
            subtitle_handler = SubtitleHandler()
            try:
                subtitles = await subtitle_handler.search_all_sources(movie_name, language=language)
                
                if not subtitles:
                    keyboard = create_language_selection_keyboard(user_id, file_id, movie_name)
                    await query.message.edit_text(
                        f"❌ **No subtitles found**\n\n"
                        f"Sorry, I couldn't find subtitles for '{movie_name}' in {LANGUAGE_MAPPING.get(language, {}).get('name', language)}.\n\n"
                        f"Try selecting a different language or choose 'No Subtitles'.",
                        reply_markup=keyboard
                    )
                else:
                    # Store subtitles in temp for later use
                    temp.SUBTITLE_RESULTS = temp.SUBTITLE_RESULTS or {}
                    temp.SUBTITLE_RESULTS[f"{user_id}_{file_id}_{language}"] = subtitles
                    
                    keyboard = create_subtitle_results_keyboard(subtitles, user_id, file_id, language, movie_name)
                    lang_info = LANGUAGE_MAPPING.get(language, {'name': language, 'flag': '🏳️'})
                    await query.message.edit_text(
                        f"🎯 **Found {len(subtitles)} subtitles**\n\n"
                        f"🎬 **Movie:** {movie_name}\n"
                        f"🌐 **Language:** {lang_info['flag']} {lang_info['name']}\n\n"
                        f"Select a subtitle to download:",
                        reply_markup=keyboard
                    )
            finally:
                await subtitle_handler.close_session()
                
        except Exception as e:
            logger.error(f"Error in subtitle selection: {e}")
            await query.answer("An error occurred while searching for subtitles. Please try again.", show_alert=True)
    
    elif query.data.startswith("more_langs#"):
        try:
            _, user_id, file_id, movie_name = query.data.split("#", 3)
            if int(user_id) != query.from_user.id:
                return await query.answer("This is not for you!", show_alert=True)
            
            keyboard = create_more_languages_keyboard(user_id, file_id, movie_name)
            await query.message.edit_reply_markup(reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error showing more languages: {e}")
    
    elif query.data.startswith("back_langs#"):
        try:
            _, user_id, file_id, movie_name = query.data.split("#", 3)
            if int(user_id) != query.from_user.id:
                return await query.answer("This is not for you!", show_alert=True)
            
            keyboard = create_language_selection_keyboard(user_id, file_id, movie_name)
            files_ = await get_file_details(file_id)
            if files_:
                title = files_[0].file_name
                size = get_size(files_[0].file_size)
                await query.message.edit_text(
                    f"🎬 **{title}**\n📁 **Size:** {size}\n\n"
                    f"🔤 **Select subtitle language:**\n\n"
                    f"Choose your preferred subtitle language or select 'No Subtitles' to get the file directly.",
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"Error going back to languages: {e}")
    
    elif query.data.startswith("no_subs#"):
        try:
            _, user_id, file_id = query.data.split("#")
            if int(user_id) != query.from_user.id:
                return await query.answer("This is not for you!", show_alert=True)
            
            # Send file without subtitles
            files_ = await get_file_details(file_id)
            if not files_:
                return await query.answer('No Such File Exist.')
            
            files = files_[0]
            title = files.file_name
            size = get_size(files.file_size)
            f_caption = f"{title}"
            
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption = CUSTOM_FILE_CAPTION.format(
                        mention=query.from_user.mention, 
                        file_name=title or '', 
                        file_size=size or '', 
                        file_caption=f_caption or ''
                    )
                except Exception as e:
                    logger.exception(e)
            
            await query.message.edit_text("📤 **Sending file...**\n\nYour movie file is being sent to your PM.")
            
            try:
                if AUTH_CHANNEL and not await is_subscribed(client, query):
                    return await query.answer(url=f"https://t.me/{temp.U_NAME}?start=files_{file_id}")
                else:
                    await client.send_cached_media(
                        chat_id=query.from_user.id, 
                        file_id=file_id, 
                        caption=f_caption, 
                        protect_content=False
                    )
                    await query.message.edit_text("✅ **File sent successfully!**\n\nCheck your PM for the movie file.")
            except UserIsBlocked:
                await query.message.edit_text("❌ **Can't send file**\n\nPlease start the bot in PM first.")
            except Exception as e:
                logger.error(f"Error sending file: {e}")
                await query.message.edit_text("❌ **Error sending file**\n\nPlease try again later.")
                
        except Exception as e:
            logger.error(f"Error in no_subs handler: {e}")
    
    elif query.data.startswith("dl_sub#"):
        try:
            _, user_id, file_id, subtitle_index, language, movie_name = query.data.split("#", 5)
            if int(user_id) != query.from_user.id:
                return await query.answer("This is not for you!", show_alert=True)
            
            subtitle_index = int(subtitle_index)
            
            # Get stored subtitles
            subtitles = temp.SUBTITLE_RESULTS.get(f"{user_id}_{file_id}_{language}", [])
            if not subtitles or subtitle_index >= len(subtitles):
                return await query.answer("Subtitle not found. Please search again.", show_alert=True)
            
            selected_subtitle = subtitles[subtitle_index]
            
            await query.message.edit_text(
                "📥 **Downloading subtitle...**\n\n"
                f"🎬 **Movie:** {movie_name}\n"
                f"📄 **Subtitle:** {selected_subtitle['title']}\n"
                f"🌐 **Language:** {LANGUAGE_MAPPING.get(language, {}).get('name', language)}\n"
                f"🔗 **Source:** {selected_subtitle['source']}"
            )
            
            subtitle_handler = SubtitleHandler()
            subtitle_content = None
            tried_sources = []
            
            # Try the selected subtitle first
            try:
                subtitle_content = await subtitle_handler.download_subtitle(
                    selected_subtitle['download_url'], 
                    selected_subtitle['source'],
                    selected_subtitle,
                    language,
                    movie_name
                )
                tried_sources.append(selected_subtitle['source'])
            except Exception as e:
                print(f"[DOWNLOAD] Failed to download from {selected_subtitle['source']}: {e}")
            
            # If first subtitle failed, try other available subtitles
            if not subtitle_content and len(subtitles) > 1:
                print(f"[DOWNLOAD] First subtitle failed, trying {len(subtitles)-1} other sources...")
                for i, subtitle in enumerate(subtitles):
                    if i == subtitle_index or subtitle['source'] in tried_sources:
                        continue  # Skip the already tried subtitle
                    
                    try:
                        print(f"[DOWNLOAD] Trying subtitle from {subtitle['source']}: {subtitle['title']}")
                        subtitle_content = await subtitle_handler.download_subtitle(
                            subtitle['download_url'], 
                            subtitle['source'],
                            subtitle,
                            language,
                            movie_name
                        )
                        if subtitle_content:
                            print(f"[DOWNLOAD] Successfully downloaded from {subtitle['source']}")
                            # Update the selected subtitle info for display
                            selected_subtitle = subtitle
                            break
                        tried_sources.append(subtitle['source'])
                    except Exception as e:
                        print(f"[DOWNLOAD] Failed to download from {subtitle['source']}: {e}")
                        tried_sources.append(subtitle['source'])
            
            try:
                if subtitle_content:
                    # Create subtitle file
                    import tempfile
                    import os
                    
                    subtitle_filename = f"{movie_name}_{language}.srt"
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as temp_file:
                        temp_file.write(subtitle_content)
                        temp_subtitle_path = temp_file.name
                    
                    try:
                        # Send subtitle file
                        await client.send_document(
                            chat_id=query.from_user.id,
                            document=temp_subtitle_path,
                            file_name=subtitle_filename,
                            caption=f"📄 **Subtitle File**\n\n"
                                   f"🎬 **Movie:** {movie_name}\n"
                                   f"🌐 **Language:** {LANGUAGE_MAPPING.get(language, {}).get('flag', '🏳️')} {LANGUAGE_MAPPING.get(language, {}).get('name', language)}\n"
                                   f"🔗 **Source:** {selected_subtitle['source']}"
                        )
                        
                        # Now send the movie file
                        files_ = await get_file_details(file_id)
                        if files_:
                            files = files_[0]
                            title = files.file_name
                            f_caption = f"{title}"
                            
                            if CUSTOM_FILE_CAPTION:
                                try:
                                    f_caption = CUSTOM_FILE_CAPTION.format(
                                        mention=query.from_user.mention, 
                                        file_name=title or '', 
                                        file_size=get_size(files.file_size) or '', 
                                        file_caption=f_caption or ''
                                    )
                                except Exception as e:
                                    logger.exception(e)
                            
                            await client.send_cached_media(
                                chat_id=query.from_user.id, 
                                file_id=file_id, 
                                caption=f_caption, 
                                protect_content=False
                            )
                            
                            await query.message.edit_text(
                                "✅ **Download Complete!**\n\n"
                                f"🎬 **Movie:** {movie_name}\n"
                                f"📄 **Subtitle:** Downloaded and sent\n"
                                f"🎥 **Movie File:** Sent to your PM\n\n"
                                f"Enjoy watching with subtitles! 🍿"
                            )
                    finally:
                        # Clean up temp file
                        try:
                            os.unlink(temp_subtitle_path)
                        except:
                            pass
                            
                else:
                    if len(tried_sources) > 1:
                        await query.message.edit_text(
                            "❌ **All Downloads Failed**\n\n"
                            f"Sorry, I tried downloading from {len(tried_sources)} sources but all failed:\n"
                            f"• {', '.join(tried_sources)}\n\n"
                            f"The subtitle sources might be temporarily unavailable."
                        )
                    else:
                        await query.message.edit_text(
                            "❌ **Download Failed**\n\n"
                            f"Sorry, I couldn't download the subtitle file from {tried_sources[0] if tried_sources else 'unknown source'}.\n\n"
                            f"The source might be unavailable."
                        )
                    
            finally:
                await subtitle_handler.close_session()
                
        except Exception as e:
            logger.error(f"Error downloading subtitle: {e}")
            await query.message.edit_text(
                "❌ **Error occurred**\n\n"
                f"Sorry, there was an error downloading the subtitle. Please try again."
            )
    
    elif query.data == "subtitle_help":
        subtitle_help_text = """
🎬 **Subtitle Bot Features**

**Commands:**
• `/subtitle movie name` - Search for movie subtitles
• `/subtitle_help` - Show this help

**How to use:**
1. Send `/subtitle movie name`
2. Select the correct movie from the list
3. Choose your preferred language
4. Download the subtitle file

**Supported Languages:**
🇺🇸 English | 🇪🇸 Spanish | 🇫🇷 French | 🇩🇪 German
🇮🇹 Italian | 🇵🇹 Portuguese | 🇷🇺 Russian | 🇯🇵 Japanese
🇰🇷 Korean | 🇨🇳 Chinese | 🇦🇷 Arabic | 🇮🇳 Hindi
🇮🇳 Tamil | 🇱🇰 Sinhala

**Features:**
✅ 100% Free - No daily limits
✅ Multiple subtitle sources
✅ Automatic fallback
✅ Proper SRT format
✅ Multiple languages

**Example:**
`/subtitle Inception 2010`
`/subtitle The Dark Knight`
`/subtitle Avatar 2009`
"""
        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', 'close_data'),
            InlineKeyboardButton('« Bᴀᴄᴋ', 'help')           
        ]]
        await query.edit_message_media(InputMediaPhoto(random.choice(PICS), subtitle_help_text, enums.ParseMode.HTML), reply_markup=InlineKeyboardMarkup(buttons))







