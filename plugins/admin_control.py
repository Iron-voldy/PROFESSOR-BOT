from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong, PeerIdInvalid, UserNotParticipant, MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty

from info import ADMINS, LOG_CHANNEL, SUPPORT_CHAT, WELCOM_PIC, WELCOM_TEXT, IMDB_TEMPLATE
from utils import get_size, temp, extract_user, get_file_id, get_poster, humanbytes
from database.users_chats_db import db
from database.simple_db import MediaDocument, collection
from datetime import datetime
from Script import script
import logging, re, asyncio, time, shutil, psutil, os, sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


@Client.on_message(filters.new_chat_members & filters.group)
async def savegroup_and_welcome(bot, message):
    r_j_check = [u.id for u in message.new_chat_members]
    if bot.id in r_j_check:
        if not await db.get_chat(message.chat.id):
            total=await bot.get_chat_members_count(message.chat.id)
            r_j = message.from_user.mention if message.from_user else "Anonymous" 
            await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(a=message.chat.title, b=message.chat.id, c=message.chat.username, d=total, e=r_j, f=bot.mention))       
            await db.add_chat(message.chat.id, message.chat.title, message.chat.username)
        if message.chat.id in temp.BANNED_CHATS:
            buttons = [[InlineKeyboardButton('Sᴜᴩᴩᴏʀᴛ', url=f'https://t.me/{SUPPORT_CHAT}')]]
            k = await message.reply("CHAT NOT ALLOWED 🐞\n\nMʏ Aᴅᴍɪɴs Hᴀs Rᴇsᴛʀɪᴄᴛᴇᴅ Mᴇ Fʀᴏᴍ Wᴏʀᴋɪɴɢ Hᴇʀᴇ ! Iғ Yᴏᴜ Wᴀɴᴛ Tᴏ Kɴᴏᴡ Mᴏʀᴇ Aʙᴏᴜᴛ Iᴛ Cᴏɴᴛᴀᴄᴛ Sᴜᴘᴘᴏʀᴛ", reply_markup=InlineKeyboardMarkup(buttons))
            try: await k.pin()
            except: pass
            return await bot.leave_chat(message.chat.id)
           
        buttons = [[InlineKeyboardButton('Hᴇʟᴩ', url=f"https://t.me/{temp.U_NAME}?start=help")]]
        await message.reply(text="❤️ Tʜᴀɴᴋs Tᴏ Aᴅᴅ Mᴇ Tᴏ Yᴏᴜ'ʀ Gʀᴏᴜᴘ.\n» Dᴏɴ'ᴛ Fᴏʀɢᴇᴛ Tᴏ Mᴀᴋᴇ Mᴇ Aᴅᴍɪɴ.\n» Is Aɴʏ Dᴏᴜʙᴛ's Aʙᴏᴜᴛ Usɪɴɢ Mᴇ Cʟɪᴄᴋ Bᴇʟᴏᴡ Bᴜᴛᴛᴏɴ...✨", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        for u in message.new_chat_members:
            if (temp.MELCOW).get('welcome') is not None:
                try: await (temp.MELCOW['welcome']).delete()
                except: pass
            if WELCOM_PIC: temp.MELCOW['welcome'] = await message.reply_photo(photo=WELCOM_PIC, caption=WELCOM_TEXT.format(user=u.mention, chat=message.chat.title))
            else: temp.MELCOW['welcome'] = await message.reply_text(text=WELCOM_TEXT.format(user=u.mention, chat=message.chat.title))


@Client.on_message(filters.command('leave') & filters.user(ADMINS))
async def leave_a_chat(bot, message):
    if len(message.command) == 1: return await message.reply('Gɪᴠᴇ Mᴇ A Cʜᴀᴛ Iᴅ')
    chat = message.command[1]
    try: chat = int(chat)
    except: chat = chat
    try:
        buttons = [[InlineKeyboardButton('Sᴜᴩᴩᴏʀᴛ', url=f'https://t.me/{SUPPORT_CHAT}')]]
        await bot.send_message(chat_id=chat, text='<b>Hᴇʟʟᴏ Fʀɪᴇɴᴅs, \nMʏ Aᴅᴍɪɴ Hᴀs Tᴏʟᴅ Mᴇ Tᴏ Lᴇᴀᴠᴇ Fʀᴏᴍ Gʀᴏᴜᴘ Sᴏ I Gᴏ! Iғ Yᴏᴜ Wᴀɴɴᴀ Aᴅᴅ Mᴇ Aɢᴀɪɴ Cᴏɴᴛᴀᴄᴛ Mʏ Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ</b>', reply_markup=InlineKeyboardMarkup(buttons))
        await bot.leave_chat(chat)
    except Exception as e:
        await message.reply(f'Eʀʀᴏʀ: {e}')

@Client.on_message(filters.command('disable') & filters.user(ADMINS))
async def disable_chat(bot, message):
    if len(message.command) == 1: return await message.reply('Gɪᴠᴇ Mᴇ A Cʜᴀᴛ Iᴅ')
    r = message.text.split(None)
    if len(r) > 2:
        reason = message.text.split(None, 2)[2]
        chat = message.text.split(None, 2)[1]
    else:
        chat = message.command[1]
        reason = "No Reason Provided"
    try:
        chat_ = int(chat)
    except:
        return await message.reply('Gɪᴠᴇ Mᴇ A Vᴀʟɪᴅ Cʜᴀᴛ ID')
    cha_t = await db.get_chat(int(chat_))
    if not cha_t:
        return await message.reply("Cʜᴀᴛ Nᴏᴛ Fᴏᴜɴᴅ Iɴ DB")
    if cha_t['is_disabled']:
        return await message.reply(f"Tʜɪꜱ Cʜᴀᴛ Is Aʟʀᴇᴅʏ  Dɪꜱᴀʙʟᴇᴅ:\nRᴇᴀꜱᴏɴ: <code> {cha_t['reason']} </code>")
    await db.disable_chat(int(chat_), reason)
    temp.BANNED_CHATS.append(int(chat_))
    await message.reply('Cʜᴀᴛ Sᴜᴄᴄᴇꜱꜰᴜʟʟʏ Dɪꜱᴀʙʟᴇᴅ')
    try:
        buttons = [[InlineKeyboardButton('Sᴜᴩᴩᴏʀᴛ', url=f'https://t.me/{SUPPORT_CHAT}')]]
        await bot.send_message(chat_id=chat_,  text=f'<b>Hᴇʟʟᴏ Fʀɪᴇɴᴅs, \nᴍʏ Aᴅᴍɪɴ Hᴀs Tᴏʟᴅ Mᴇ Tᴏ Lᴇᴀᴠᴇ Fʀᴏᴍ Gʀᴏᴜᴘ Sᴏ I Gᴏ! Iғ Yᴏᴜ Wᴀɴɴᴀ Aᴅᴅ Mᴇ Aɢᴀɪɴ Cᴏɴᴛᴀᴄᴛ Mʏ Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ.</b> \nRᴇᴀꜱᴏɴ : <code>{reason}</code>', reply_markup=InlineKeyboardMarkup(buttons))
        await bot.leave_chat(chat_)
    except Exception as e:
        await message.reply(f"Eʀʀᴏʀ: {e}")


@Client.on_message(filters.command('enable') & filters.user(ADMINS))
async def re_enable_chat(bot, message):
    if len(message.command) == 1: return await message.reply('Gɪᴠᴇ Mᴇ A Cʜᴀᴛ Iᴅ')
    chat = message.command[1]
    try: chat_ = int(chat)
    except: return await message.reply('Gɪᴠᴇ Mᴇ A Vᴀʟɪᴅ Cʜᴀᴛ ID')
    sts = await db.get_chat(int(chat))
    if not sts: return await message.reply("Cʜᴀᴛ Nᴏᴛ Fᴏᴜɴᴅ Iɴ DB")
    if not sts.get('is_disabled'):
        return await message.reply('Tʜɪꜱ Cʜᴀᴛ Iꜱ Nᴏᴛ Yᴇᴛ Dɪꜱᴀʙʟᴇᴅ')
    await db.re_enable_chat(int(chat_))
    temp.BANNED_CHATS.remove(int(chat_))
    await message.reply("Cʜᴀᴛ Sᴜᴄᴄᴇꜱꜰᴜʟʟʏ Rᴇ-Eɴᴀʙʟᴇᴅ")


@Client.on_message(filters.command('stats') & filters.incoming)
async def get_ststs(bot, message):
    rju = await message.reply('<b>Pʟᴇᴀꜱᴇ Wᴀɪᴛ...</b>')
    total_users = await db.total_users_count()
    totl_chats = await db.total_chat_count()
    files = await Media.count_documents()
    size = await db.get_db_size()
    free = 536870912 - size
    size = get_size(size)
    free = get_size(free)
    await rju.edit(script.STATUS_TXT.format(files, total_users, totl_chats, size, free))


@Client.on_message(filters.command('invite') & filters.user(ADMINS))
async def gen_invite(bot, message):
    if len(message.command) == 1: return await message.reply('Gɪᴠᴇ Mᴇ A Cʜᴀᴛ Iᴅ')
    chat = message.command[1]
    try: chat = int(chat)
    except: return await message.reply('Gɪᴠᴇ Mᴇ A Vᴀʟɪᴅ Cʜᴀᴛ ID')
    try:
        link = await bot.create_chat_invite_link(chat)
    except ChatAdminRequired:
        return await message.reply("Iɴᴠɪᴛᴇ Lɪɴᴋ Gᴇɴᴇʀᴀᴛɪᴏɴ Fᴀɪʟᴇᴅ, Iᴀᴍ Nᴏᴛ Hᴀᴠɪɴɢ Sᴜғғɪᴄɪᴇɴᴛ Rɪɢʜᴛs")
    except Exception as e:
        return await message.reply(f'Eʀʀᴏʀ: {e}')
    await message.reply(f'Hᴇʀᴇ Iꜱ Yᴏᴜʀ Iɴᴠɪᴛᴇ Lɪɴᴋ: {link.invite_link}')

@Client.on_message(filters.command('ban_user') & filters.user(ADMINS))
async def ban_a_user(bot, message):
    if len(message.command) == 1: return await message.reply('Gɪᴠᴇ Mᴇ A Uꜱᴇʀ Iᴅ / Uꜱᴇʀɴᴀᴍᴇ')
    r = message.text.split(None)
    if len(r) > 2:
        reason = message.text.split(None, 2)[2]
        chat = message.text.split(None, 2)[1]
    else:
        chat = message.command[1]
        reason = "No reason Provided"
    try: chat = int(chat)
    except: pass
    try: k = await bot.get_users(chat)
    except PeerIdInvalid: return await message.reply("Tʜɪs Is Aɴ Iɴᴠᴀʟɪᴅ Usᴇʀ, Mᴀᴋᴇ Sᴜʀᴇ Iᴀ Hᴀᴠᴇ Mᴇᴛ Hɪᴍ Bᴇғᴏʀᴇ")
    except IndexError: return await message.reply("Tʜɪs Mɪɢʜᴛ Bᴇ A Cʜᴀɴɴᴇʟ, Mᴀᴋᴇ Sᴜʀᴇ Iᴛs A Usᴇʀ.")
    except Exception as e: return await message.reply(f'Eʀʀᴏʀ: {e}')
    else:
        jar = await db.get_ban_status(k.id)
        if jar['is_banned']: return await message.reply(f"{k.mention} Iꜱ Aʟʀᴇᴅʏ Bᴀɴɴᴇᴅ\nRᴇᴀꜱᴏɴ: {jar['ban_reason']}")
        await db.ban_user(k.id, reason)
        temp.BANNED_USERS.append(k.id)
        await message.reply(f"Sᴜᴄᴄᴇꜱꜰᴜʟʟʏ Bᴀɴɴᴇᴅ {k.mention}")


    
@Client.on_message(filters.command('unban_user') & filters.user(ADMINS))
async def unban_a_user(bot, message):
    if len(message.command) == 1: return await message.reply('Gɪᴠᴇ Mᴇ A Uꜱᴇʀ Iᴅ / Uꜱᴇʀɴᴀᴍᴇ')
    r = message.text.split(None)
    if len(r) > 2:
        reason = message.text.split(None, 2)[2]
        chat = message.text.split(None, 2)[1]
    else:
        chat = message.command[1]
        reason = "No reason Provided"
    try: chat = int(chat)
    except: pass
    try: k = await bot.get_users(chat)
    except PeerIdInvalid: return await message.reply("Tʜɪs Is Aɴ Iɴᴠᴀʟɪᴅ Usᴇʀ, Mᴀᴋᴇ Sᴜʀᴇ Iᴀ Hᴀᴠᴇ Mᴇᴛ Hɪᴍ Bᴇғᴏʀᴇ")
    except IndexError: return await message.reply("Tʜɪs Mɪɢʜᴛ Bᴇ A Cʜᴀɴɴᴇʟ, Mᴀᴋᴇ Sᴜʀᴇ Iᴛs A Usᴇʀ.")
    except Exception as e: return await message.reply(f'Eʀʀᴏʀ: {e}')
    else:
        jar = await db.get_ban_status(k.id)
        if not jar['is_banned']: return await message.reply(f"{k.mention} Iꜱ Nᴏᴛ Yᴇᴛ Bᴀɴɴᴇᴅ")
        await db.remove_ban(k.id)
        temp.BANNED_USERS.remove(k.id)
        await message.reply(f"Sᴜᴄᴄᴇꜱꜰᴜʟʟʏ Uɴʙᴀɴɴᴇᴅ {k.mention}")


    
@Client.on_message(filters.command('users') & filters.user(ADMINS))
async def list_users(bot, message):
    sps = await message.reply('Gᴇᴛᴛɪɴɢ Lɪꜱᴛ Oꜰ Uꜱᴇʀꜱ')
    users = await db.get_all_users()
    out = "Uꜱᴇʀꜱ Sᴀᴠᴇᴅ Iɴ DB Aʀᴇ:\n\n"
    async for user in users:
        out += f"<a href=tg://user?id={user['id']}>{user['name']}</a>\n"
    try:
        await sps.edit_text(out)
    except MessageTooLong:
        with open('users.txt', 'w+') as outfile:
            outfile.write(out)
        await message.reply_document('users.txt', caption="Lɪꜱᴛ Oꜰ Uꜱᴇʀꜱ")

@Client.on_message(filters.command('chats') & filters.user(ADMINS))
async def list_chats(bot, message):
    sps = await message.reply('Gᴇᴛᴛɪɴɢ Lɪꜱᴛ Oꜰ Cʜᴀᴛꜱ')
    chats = await db.get_all_chats()
    out = "Cʜᴀᴛꜱ Sᴀᴠᴇᴅ Iɴ DB Aʀᴇ:\n\n"
    async for chat in chats:
        username = chat['username']
        username = "private" if not username else "@" + username
        out += f"**- Tɪᴛʟᴇ:** `{chat['title']}`\n**- ID:** `{chat['id']}`\n**Uꜱᴇʀɴᴀᴍᴇ:** {username}\n"
    try:
        await sps.edit_text(out)
    except MessageTooLong:
        with open('chats.txt', 'w+') as outfile:
            outfile.write(out)
        await message.reply_document('chats.txt', caption="Lɪꜱᴛ Oꜰ Cʜᴀᴛꜱ")



@Client.on_message(filters.command('id'))
async def show_id(client, message):
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        user_id = message.chat.id
        first = message.from_user.first_name
        last = message.from_user.last_name or ""
        username = message.from_user.username
        dc_id = message.from_user.dc_id or ""
        await message.reply_text(f"<b>➲ ꜰɪʀꜱᴛ ɴᴀᴍᴇ:</b> {first}\n<b>➲ ʟᴀꜱᴛ ɴᴀᴍᴇ:</b> {last}\n<b>➲ ᴜꜱᴇʀɴᴀᴍᴇ:</b> {username}\n<b>➲ ᴛᴇʟᴇɢʀᴀᴍ ɪᴅ:</b> <code>{user_id}</code>\n<b>➲ ᴅᴄ ɪᴅ:</b> <code>{dc_id}</code>", quote=True)

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        _id = ""
        _id += f"<b>➲ ᴄʜᴀᴛ ɪᴅ</b>: <code>{message.chat.id}</code>\n"
        
        if message.reply_to_message:
            _id += (
                "<b>➲ ᴜꜱᴇʀ ɪᴅ</b>: "
                f"<code>{message.from_user.id if message.from_user else 'Anonymous'}</code>\n"
                "<b>➲ ʀᴇᴩʟɪᴇᴅ ᴜꜱᴇʀ ɪᴅ</b>: "
                f"<code>{message.reply_to_message.from_user.id if message.reply_to_message.from_user else 'Anonymous'}</code>\n"
            )
            file_info = get_file_id(message.reply_to_message)
        else:
            _id += (
                "<b>➲ ᴜꜱᴇʀ ɪᴅ</b>: "
                f"<code>{message.from_user.id if message.from_user else 'Anonymous'}</code>\n"
            )
            file_info = get_file_id(message)
        if file_info:
            _id += (
                f"<b>{file_info.message_type}</b>: "
                f"<code>{file_info.file_id}</code>\n"
            )
        await message.reply_text(_id, quote=True)
            

@Client.on_message(filters.command(["info"]))
async def user_info(client, message):
    status_message = await message.reply_text("`ᴩʟᴇᴀꜱᴇ ᴡᴀɪᴛ....`")
    from_user = None
    from_user_id, _ = extract_user(message)
    try:
        from_user = await client.get_users(from_user_id)
    except Exception as error:
        return await status_message.edit(str(error))
    if from_user is None:
        return await status_message.edit("ɴᴏ ᴠᴀʟɪᴅ ᴜsᴇʀ_ɪᴅ / ᴍᴇssᴀɢᴇ sᴘᴇᴄɪғɪᴇᴅ")
    message_out_str = ""
    message_out_str += f"<b>➲ꜰɪʀꜱᴛ ɴᴀᴍᴇ:</b> {from_user.first_name}\n"
    last_name = from_user.last_name or "<b>ɴᴏɴᴇ</b>"
    message_out_str += f"<b>➲ʟᴀꜱᴛ ɴᴀᴍᴇ:</b> {last_name}\n"
    message_out_str += f"<b>➲ᴛɢ-ɪᴅ:</b> <code>{from_user.id}</code>\n"
    username = from_user.username or "<b>ɴᴏɴᴇ</b>"
    dc_id = from_user.dc_id or "[ᴜꜱᴇʀ ᴅᴏꜱᴇ'ᴛ ʜᴀᴠᴇ ᴀ ᴠᴀʟɪᴅ ᴅᴩ]"
    message_out_str += f"<b>➲ᴅᴄ-ɪᴅ:</b> <code>{dc_id}</code>\n"
    message_out_str += f"<b>➲ᴜꜱᴇʀɴᴀᴍᴇ:</b> @{username}\n"
    message_out_str += f"<b>➲ᴜꜱᴇʀ ʟɪɴᴋ:</b> <a href='tg://user?id={from_user.id}'><b>ᴄʟɪᴄᴋ ʜᴇʀᴇ</b></a>\n"
    if message.chat.type in ((enums.ChatType.SUPERGROUP, enums.ChatType.CHANNEL)):
        try:
            chat_member_p = await message.chat.get_member(from_user.id)
            joined_date = (chat_member_p.joined_date or datetime.now()).strftime("%Y.%m.%d %H:%M:%S")
            message_out_str += f"<b>➲ᴊᴏɪɴᴇᴅ ᴛʜɪꜱ ᴄʜᴀᴛ ᴏɴ:</b> <code>{joined_date}</code>\n"
        except UserNotParticipant: pass
    chat_photo = from_user.photo
    if chat_photo:
        local_user_photo = await client.download_media(message=chat_photo.big_file_id)
        buttons = [[InlineKeyboardButton('ᴄʟᴏꜱᴇ ✘', callback_data='close_data')]]
        await message.reply_photo(
            photo=local_user_photo,
            quote=True,
            reply_markup=InlineKeyboardMarkup(buttons),
            caption=message_out_str,
            parse_mode=enums.ParseMode.HTML,
            disable_notification=True
        )
        os.remove(local_user_photo)
    else:
        buttons = [[InlineKeyboardButton('ᴄʟᴏꜱᴇ ✘', callback_data='close_data')]]
        await message.reply_text(
            text=message_out_str,
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True,
            parse_mode=enums.ParseMode.HTML,
            disable_notification=True
        )
    await status_message.delete()

@Client.on_message(filters.command(["imdb", 'search']))
async def imdb_search(client, message):
    if ' ' in message.text:
        k = await message.reply('ꜱᴇᴀʀᴄʜɪɴɢ ɪᴍᴅʙ..')
        r, title = message.text.split(None, 1)
        movies = await get_poster(title, bulk=True)
        if not movies:
            return await message.reply("ɴᴏ ʀᴇꜱᴜʟᴛ ꜰᴏᴜɴᴅ")
        btn = [[InlineKeyboardButton(f"{movie.get('title')} - {movie.get('year')}", callback_data=f"imdb#{movie.movieID}")] for movie in movies ]
        await k.edit('Hᴇʀᴇ Is Wʜᴀᴛ I Fᴏᴜɴᴅ Oɴ Iᴍᴅʙ', reply_markup=InlineKeyboardMarkup(btn))
    else:
        await message.reply('Gɪᴠᴇ Mᴇ A Mᴏᴠɪᴇ / Sᴇʀɪᴇs Nᴀᴍᴇ')


@Client.on_callback_query(filters.regex('^imdb'))
async def imdb_callback(bot: Client, quer_y: CallbackQuery):
    i, movie = quer_y.data.split('#')
    imdb = await get_poster(query=movie, id=True)
    btn = [[InlineKeyboardButton(f"{imdb.get('title')}", url=imdb['url'])]]
    message = quer_y.message.reply_to_message or quer_y.message
    if imdb:
        caption = IMDB_TEMPLATE.format(
            query = imdb['title'],
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
        caption = "ɴᴏ ʀᴇꜱᴜʟᴛꜱ"
    if imdb.get('poster'):
        try:
            await quer_y.message.reply_photo(photo=imdb['poster'], caption=caption, reply_markup=InlineKeyboardMarkup(btn))
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            await quer_y.message.reply_photo(photo=poster, caption=caption, reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            logger.exception(e)
            await quer_y.message.reply(caption, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=False)
        await quer_y.message.delete()
    else:
        await quer_y.message.edit(caption, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=False)
   
 
@Client.on_message(filters.command('log') & filters.user(ADMINS))
async def log_file_sned(client, message):
    try: await message.reply_document('log.txt')
    except Exception as e: await message.reply(str(e))

@Client.on_message(filters.command("restart") & filters.user(ADMINS))
async def restart_bot(client, message):
    await message.reply("Rᴇꜱᴛᴀᴛɪɴɢ........")
    try: os.remove('log.txt')
    except: pass 
    os.execl(sys.executable, sys.executable, *sys.argv)

@Client.on_message(filters.command("update") & filters.user(ADMINS))
async def update_gitpull(client, message):
    try:
        os.system("git pull")
        await message.reply_text("ᴜᴩᴅᴀᴛᴇᴅ & ʀᴇꜱᴛᴀʀᴛɪɴɢ...")
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        await message.reply(e)

        



