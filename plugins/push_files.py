# Push files from database to channel
import asyncio
from pyrogram import Client, filters
from pyrogram import errors
from motor.motor_asyncio import AsyncIOMotorClient
from info import ADMINS, TARGET_CHANNEL, DATABASE_URI, DATABASE_NAME

# Database Connection
db_client = AsyncIOMotorClient(DATABASE_URI)
db = db_client[DATABASE_NAME]
collection = db['Files']

@Client.on_message(filters.command("pushall") & filters.user(ADMINS))
async def push_all_files(bot, message):
    sts = await message.reply_text('Checking files to push...')
    
    try:
        # Count files that haven't been pushed
        query = {"pushed_to_channel": {"$ne": True}}
        total_files = await collection.count_documents(query)
        
        if total_files == 0:
            await sts.edit("All files are already synced!\n\nNo new files to push.")
            return
        
        await sts.edit(f"Found {total_files} files to push.\n\nStarting push to channel {TARGET_CHANNEL}...")
        
        sent = 0
        failed = 0
        skipped = 0
        
        async for file_doc in collection.find(query):
            try:
                file_id = file_doc.get('file_id')
                file_type = file_doc.get('file_type', 'document')
                caption = file_doc.get('caption') or file_doc.get('file_name', '')
                
                if not file_id:
                    skipped += 1
                    continue
                
                # Send file based on type
                if file_type == 'video':
                    await bot.send_video(
                        chat_id=TARGET_CHANNEL,
                        video=file_id,
                        caption=caption[:1024] if caption else None
                    )
                elif file_type == 'audio':
                    await bot.send_audio(
                        chat_id=TARGET_CHANNEL,
                        audio=file_id,
                        caption=caption[:1024] if caption else None
                    )
                elif file_type == 'photo':
                    await bot.send_photo(
                        chat_id=TARGET_CHANNEL,
                        photo=file_id,
                        caption=caption[:1024] if caption else None
                    )
                else:
                    await bot.send_document(
                        chat_id=TARGET_CHANNEL,
                        document=file_id,
                        caption=caption[:1024] if caption else None
                    )
                
                # Mark as pushed
                await collection.update_one(
                    {'_id': file_doc['_id']},
                    {'$set': {'pushed_to_channel': True}}
                )
                
                sent += 1
                
                # Update status every 10 files
                if sent % 10 == 0:
                    await sts.edit(
                        f"Pushing files...\n\n"
                        f"Total: {total_files}\n"
                        f"Sent: {sent}\n"
                        f"Failed: {failed}\n"
                        f"Skipped: {skipped}"
                    )
                
                await asyncio.sleep(3)
                
            except errors.FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                failed += 1
                print(f"Error pushing file: {e}")
        
        await sts.edit(
            f"Push Completed!\n\n"
            f"Total Files: {total_files}\n"
            f"Successfully Sent: {sent}\n"
            f"Failed: {failed}\n"
            f"Skipped: {skipped}"
        )
        
    except Exception as e:
        await sts.edit(f"Error: {e}")
        print(f"Push error: {e}")

@Client.on_message(filters.command("resetpush") & filters.user(ADMINS))
async def reset_push(bot, message):
    sts = await message.reply_text('Resetting push status...')
    try:
        result = await collection.update_many(
            {"pushed_to_channel": True},
            {"$unset": {"pushed_to_channel": ""}}
        )
        await sts.edit(f"Reset Complete!\n\nCleared push status for {result.modified_count} files.")
    except Exception as e:
        await sts.edit(f"Error: {e}")

@Client.on_message(filters.command("pushstatus") & filters.user(ADMINS))
async def push_status(bot, message):
    try:
        total = await collection.count_documents({})
        pushed = await collection.count_documents({"pushed_to_channel": True})
        pending = total - pushed
        
        await message.reply_text(
            f"Push Status:\n\n"
            f"Total Files: {total}\n"
            f"Already Pushed: {pushed}\n"
            f"Pending: {pending}"
        )
    except Exception as e:
        await message.reply_text(f"Error: {e}")
