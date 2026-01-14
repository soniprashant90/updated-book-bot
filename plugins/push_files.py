import asyncio
from pyrogram import Client, filters, errors
from info import ADMINS, TARGET_CHANNEL
from database.ia_filterdb import Media

# -------------------------------------------------------------------------------------
# COMMAND: /pushall
# PURPOSE: Syncs files from Database to Target Channel.
# -------------------------------------------------------------------------------------

@Client.on_message(filters.command("pushall") & filters.user(ADMINS))
async def push_to_channel(client, message):
    
    # Check if Target Channel is set
    if not TARGET_CHANNEL or TARGET_CHANNEL == 0:
        await message.reply_text("❌ **Configuration Error:**\n`TARGET_CHANNEL` ID is missing in your settings.\nPlease add it to your Environment Variables.")
        return

    status_msg = await message.reply_text(f"🔄 **Connecting to Database...**\nTarget Channel: `{TARGET_CHANNEL}`")
    
    collection = Media.col 
    
    # Find unsent files
    query = {"pushed_to_channel": {"$ne": True}}
    total_files = await collection.count_documents(query)
    
    if total_files == 0:
        await status_msg.edit("✅ **All files are already synced!**\nNo new files found to push.")
        return

    await status_msg.edit(f"📂 Found **{total_files}** new files.\n🚀 Starting push to channel...\n\n**⚠️ DO NOT RESTART THE BOT**")

    sent_count = 0
    error_count = 0
    skipped_count = 0

    # Start Loop
    async for file_doc in collection.find(query):
        try:
            file_id = file_doc.get('file_id')
            caption = file_doc.get('caption', None)
            
            if not caption:
                caption = file_doc.get('file_name', '')

            if not file_id:
                skipped_count += 1
                continue

            # Send File
            await client.send_cached_media(
                chat_id=TARGET_CHANNEL,
                file_id=file_id,
                caption=caption
            )

            # Mark as Sent
            await collection.update_one(
                {'_id': file_doc['_id']},
                {'$set': {'pushed_to_channel': True}}
            )

            sent_count += 1
            
            # Status Update
            if sent_count % 50 == 0:
                await status_msg.edit(
                    f"🔄 **Syncing Files...**\n"
                    f"✅ Sent: {sent_count}\n"
                    f"📂 Total New: {total_files}\n"
                    f"❌ Errors: {error_count}"
                )

            # Sleep
            await asyncio.sleep(3) 

        except errors.FloodWait as e:
            print(f"⚠️ FloodWait: Sleeping for {e.value} seconds")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            print(f"❌ Error sending file: {e}")
            error_count += 1

    await status_msg.edit(
        f"✅ **Sync Complete!**\n\n"
        f"📤 Successfully Sent: `{sent_count}`\n"
        f"❌ Failed: `{error_count}`\n"
        f"⏩ Skipped: `{skipped_count}`"
    )

@Client.on_message(filters.command("resetpush") & filters.user(ADMINS))
async def reset_push_status(client, message):
    processing_msg = await message.reply_text("🔄 **Resetting Database Status...**")
    collection = Media.col 
    result = await collection.update_many(
        {"pushed_to_channel": True}, 
        {"$unset": {"pushed_to_channel": ""}}
    )
    if result.modified_count == 0:
        await processing_msg.edit("⚠️ **Nothing to reset.**")
    else:
        await processing_msg.edit(f"✅ **Reset Complete!**\nMark removed from **{result.modified_count}** files.")
