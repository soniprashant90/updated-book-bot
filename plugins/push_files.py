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
    
    # 1. Configuration Check
    if not TARGET_CHANNEL or TARGET_CHANNEL == 0:
        await message.reply_text("❌ **Configuration Error:**\n`TARGET_CHANNEL` ID is missing in your settings (Env Variables).\nPlease add it to your Deploy Config.")
        return

    status_msg = await message.reply_text(f"🔄 **Connecting to Database...**\nTarget Channel: `{TARGET_CHANNEL}`")
    
    # Access the database collection directly
    collection = Media.col 
    
    # 2. Find files that do NOT have the 'pushed_to_channel' flag
    query = {"pushed_to_channel": {"$ne": True}}
    
    total_files = await collection.count_documents(query)
    
    if total_files == 0:
        await status_msg.edit("✅ **All files are already synced!**\nNo new files found to push.")
        return

    await status_msg.edit(f"📂 Found **{total_files}** new files.\n🚀 Starting push to channel...\n\n**⚠️ DO NOT RESTART THE BOT**")

    sent_count = 0
    error_count = 0
    skipped_count = 0

    # 3. Start Loop
    async for file_doc in collection.find(query):
        try:
            file_id = file_doc.get('file_id')
            caption = file_doc.get('caption', None)
            
            # Use filename if caption is missing
            if not caption:
                caption = file_doc.get('file_name', '')

            if not file_id:
                skipped_count += 1
                continue

            # Send File using Cached ID (Fast & Efficient)
            await client.send_cached_media(
                chat_id=TARGET_CHANNEL,
                file_id=file_id,
                caption=caption
            )

            # Mark as Sent in Database
            await collection.update_one(
                {'_id': file_doc['_id']},
                {'$set': {'pushed_to_channel': True}}
            )

            sent_count += 1
            
            # Update Status every 50 files
            if sent_count % 50 == 0:
                await status_msg.edit(
                    f"🔄 **Syncing Files...**\n"
                    f"✅ Sent: {sent_count}\n"
                    f"📂 Total New: {total_files}\n"
                    f"❌ Errors: {error_count}"
                )

            # Sleep to prevent FloodWait (REQUIRED)
            await asyncio.sleep(3) 

        except errors.FloodWait as e:
            print(f"⚠️ FloodWait: Sleeping for {e.value} seconds")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            print(f"❌ Error sending file: {e}")
            error_count += 1

    # Final Report
    await status_msg.edit(
        f"✅ **Sync Complete!**\n\n"
        f"📤 Successfully Sent: `{sent_count}`\n"
        f"❌ Failed: `{error_count}`\n"
        f"⏩ Skipped: `{skipped_count}`"
    )


# -------------------------------------------------------------------------------------
# COMMAND: /resetpush
# PURPOSE: Resets the history so you can send ALL files again.
# -------------------------------------------------------------------------------------

@Client.on_message(filters.command("resetpush") & filters.user(ADMINS))
async def reset_push_status(client, message):
    
    processing_msg = await message.reply_text("🔄 **Resetting Database Status...**\nThis might take a moment.")
    
    collection = Media.col 
    
    # Remove the 'pushed_to_channel' field from all documents
    result = await collection.update_many(
        {"pushed_to_channel": True}, 
        {"$unset": {"pushed_to_channel": ""}}
    )
    
    if result.modified_count == 0:
        await processing_msg.edit("⚠️ **Nothing to reset.**\nNo files are marked as sent.")
    else:
        await processing_msg.edit(f"✅ **Reset Complete!**\n\nForgetting history for **{result.modified_count}** files.\nNext `/pushall` will resend everything.")
