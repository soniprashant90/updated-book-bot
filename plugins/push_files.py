import asyncio
from pyrogram import Client, filters, errors
from pyrogram.types import Message
from motor.motor_asyncio import AsyncIOMotorClient
from info import ADMINS, TARGET_CHANNEL, DATABASE_URI, DATABASE_NAME
import traceback

print("Starting push_files.py loading...")

try:
    db_client = AsyncIOMotorClient(DATABASE_URI)
    db = db_client[DATABASE_NAME]
    collection = db['Files'] 
    print("SUCCESS: Database connected in push_files.py")
except Exception as e:
    print(f"ERROR: Database Connection Error: {e}")
    traceback.print_exc()

print("SUCCESS: Imports successful!")
print(f"   ADMINS: {ADMINS}")
print(f"   TARGET_CHANNEL: {TARGET_CHANNEL}")

@Client.on_message(filters.command("checkenv") & filters.private)
async def check_environment(client, message):
    print(f"checkenv command from user {message.from_user.id}")
    try:
        await message.reply_text(
            f"Environment Check\n\n"
            f"Your User ID: {message.from_user.id}\n"
            f"ADMINS List: {ADMINS}\n"
            f"Is Admin: {message.from_user.id in ADMINS}\n\n"
            f"TARGET_CHANNEL: {TARGET_CHANNEL}\n"
            f"DATABASE_NAME: {DATABASE_NAME}\n"
        )
    except Exception as e:
        print(f"checkenv ERROR: {e}")

@Client.on_message(filters.command("test") & filters.private)
async def test_command(client, message):
    print(f"test command from {message.from_user.id}")
    await message.reply_text(f"Bot is working!\nYour ID: {message.from_user.id}")

@Client.on_message(filters.command("pushall") & filters.private)
async def push_to_channel(client, message):
    print("=" * 70)
    print("PUSHALL COMMAND TRIGGERED")
    print(f"   User ID: {message.from_user.id}")
    print(f"   ADMINS list: {ADMINS}")
    print("=" * 70)
    
    try:
        status_msg = await message.reply_text("Processing your request...")
    except Exception as e:
        print(f"ERROR: Cannot send message: {e}")
        return
    
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await status_msg.edit_text(
            f"Access Denied\n\n"
            f"Your User ID: {user_id}\n"
            f"Authorized Admins: {ADMINS}\n\n"
            f"Add your ID to ADMINS environment variable"
        )
        return
    
    await status_msg.edit_text("Admin verified\nChecking configuration...")
    
    if not TARGET_CHANNEL or TARGET_CHANNEL == 0:
        await status_msg.edit_text("TARGET_CHANNEL is not configured")
        return
    
    await status_msg.edit_text(f"Configuration OK\nTarget: {TARGET_CHANNEL}\nConnecting to database...")
    
    try:
        query = {"pushed_to_channel": {"$ne": True}}
        total_files = await collection.count_documents(query)
        print(f"Found {total_files} files to push")
    except Exception as e:
        await status_msg.edit_text(f"Database Error: {str(e)[:100]}")
        return
    
    if total_files == 0:
        await status_msg.edit_text("All Files Synced\n\nNo new files found\nUse /resetpush to clear history")
        return
    
    await status_msg.edit_text(f"Starting File Push\n\nTotal Files: {total_files}\nTarget: {TARGET_CHANNEL}\n\nDO NOT RESTART THE BOT")
    
    sent_count = 0
    error_count = 0
    skipped_count = 0
    last_update = 0
    
    async for file_doc in collection.find(query):
        try:
            file_id = file_doc.get('file_id')
            file_type = file_doc.get('file_type', 'document')
            caption = file_doc.get('caption') or file_doc.get('file_name', '')
            
            if not file_id:
                skipped_count += 1
                continue
            
            try:
                if file_type == 'video':
                    await client.send_video(chat_id=TARGET_CHANNEL, video=file_id, caption=caption[:1024] if caption else None)
                elif file_type == 'audio':
                    await client.send_audio(chat_id=TARGET_CHANNEL, audio=file_id, caption=caption[:1024] if caption else None)
                elif file_type == 'photo':
                    await client.send_photo(chat_id=TARGET_CHANNEL, photo=file_id, caption=caption[:1024] if caption else None)
                elif file_type == 'voice':
                    await client.send_voice(chat_id=TARGET_CHANNEL, voice=file_id, caption=caption[:1024] if caption else None)
                elif file_type == 'video_note':
                    await client.send_video_note(chat_id=TARGET_CHANNEL, video_note=file_id)
                elif file_type == 'animation':
                    await client.send_animation(chat_id=TARGET_CHANNEL, animation=file_id, caption=caption[:1024] if caption else None)
                else:
                    await client.send_document(chat_id=TARGET_CHANNEL, document=file_id, caption=caption[:1024] if caption else None)
                
                await collection.update_one({'_id': file_doc['_id']}, {'$set': {'pushed_to_channel': True}})
                sent_count += 1
                
                if sent_count - last_update >= 10:
                    last_update = sent_count
                    try:
                        await status_msg.edit_text(f"Pushing Files\n\nSent: {sent_count}/{total_files}\nErrors: {error_count}\nSkipped: {skipped_count}")
                    except:
                        pass
                
            except errors.FloodWait as e:
                await asyncio.sleep(e.value + 5)
                continue
            except Exception as send_error:
                error_count += 1
                continue
            
            await asyncio.sleep(3)
            
        except Exception as e:
            error_count += 1
            continue
    
    await status_msg.edit_text(f"Push Complete\n\nSuccessfully Sent: {sent_count}\nErrors: {error_count}\nSkipped: {skipped_count}\nTotal: {total_files}")

@Client.on_message(filters.command("resetpush") & filters.private)
async def reset_push_status(client, message):
    if message.from_user.id not in ADMINS:
        return
    
    processing_msg = await message.reply_text("Resetting push status...")
    
    try:
        result = await collection.update_many({"pushed_to_channel": True}, {"$unset": {"pushed_to_channel": ""}})
        await processing_msg.edit_text(f"Reset Complete\n\nFiles Reset: {result.modified_count}\n\nUse /pushall to push files again")
    except Exception as e:
        await processing_msg.edit_text(f"Error: {str(e)[:100]}")

@Client.on_message(filters.command("pushstatus") & filters.private)
async def push_status(client, message):
    if message.from_user.id not in ADMINS:
        return
    
    try:
        total = await collection.count_documents({})
        pushed = await collection.count_documents({"pushed_to_channel": True})
        pending = total - pushed
        await message.reply_text(f"Push Status\n\nTotal Files: {total}\nAlready Pushed: {pushed}\nPending: {pending}\n\nUse /pushall to push pending files")
    except Exception as e:
        await message.reply_text(f"Error: {str(e)[:100]}")

print("push_files.py loaded successfully")
print(f"ADMINS: {ADMINS}")
print(f"TARGET_CHANNEL: {TARGET_CHANNEL}")
