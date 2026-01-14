import asyncio
from pyrogram import Client, filters, errors
from motor.motor_asyncio import AsyncIOMotorClient
from info import ADMINS, TARGET_CHANNEL, DATABASE_URI, DATABASE_NAME

# Database Connection
try:
    db_client = AsyncIOMotorClient(DATABASE_URI)
    db = db_client[DATABASE_NAME]
    collection = db['Files'] 
except Exception as e:
    print(f"❌ Database Connection Error: {e}")

# -------------------------------------------------------------------------------------
# COMMAND: /pushall (DEBUG VERSION)
# -------------------------------------------------------------------------------------

# REMOVED "filters.user(ADMINS)" to allow the bot to reply with an error
@Client.on_message(filters.command("pushall"))
async def push_to_channel(client, message):
    
    # 1. DEBUG CHECK: Are you an Admin?
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.reply_text(
            f"❌ **Access Denied**\n\n"
            f"👤 **Your ID:** `{user_id}`\n"
            f"🔑 **Allowed Admins:** `{ADMINS}`\n\n"
            f"⚠️ *Please copy your ID and add it to the ADMINS variable in your settings.*"
        )
        return

    # 2. Configuration Check
    if not TARGET_CHANNEL or TARGET_CHANNEL == 0:
        await message.reply_text("❌ **Configuration Error:**\n`TARGET_CHANNEL` ID is missing in your settings (Env Variables).")
        return

    status_msg = await message.reply_text(f"🔄 **Connecting to Database...**\nTarget Channel: `{TARGET_CHANNEL}`")
    
    # 3. Find files that do NOT have the 'pushed_to_channel' flag
    try:
        query = {"pushed_to_channel": {"$ne": True}}
        total_files = await collection.count_documents(query)
    except Exception as e:
        await status_msg.edit(f"❌ **DB Error:** Could not access the 'Files' collection.\nError: {e}")
        return
    
    if total_files == 0:
        await status_msg.edit("✅ **All files are already synced!**\nNo new files found to push.")
        return

    await status_msg.edit(f"📂 Found **{total_files}** new files.\n🚀 Starting push to channel...\n\n**⚠️ DO NOT RESTART THE BOT**")

    sent_count = 0
    error_count = 0
    skipped_count = 0

    # 4. Start Loop
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

            # Mark as Sent in Database
            await collection.update_one(
                {'_id': file_doc['_id']},
                {'$set': {'pushed_to_channel': True}}
            )

            sent_count += 1
            
            if sent_count % 50 == 0:
                await status_msg.edit(f"🔄 **Syncing Files...**\n✅ Sent: {sent_count}\n📂 Total New: {total_files}")

            await asyncio.sleep(3) 

        except errors.FloodWait as e:
            print(f"⚠️ FloodWait: Sleeping for {e.value} seconds")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            print(f"❌ Error sending file: {e}")
            error_count += 1

    await status_msg.edit(f"✅ **Sync Complete!**\nSent: `{sent_count}`")

# -------------------------------------------------------------------------------------
# COMMAND: /resetpush
# -------------------------------------------------------------------------------------
@Client.on_message(filters.command("resetpush"))
async def reset_push_status(client, message):
    if message.from_user.id not in ADMINS:
        return # Silent ignore for safety
        
    processing_msg = await message.reply_text("🔄 **Resetting Database Status...**")
    result = await collection.update_many({"pushed_to_channel": True}, {"$unset": {"pushed_to_channel": ""}})
    await processing_msg.edit(f"✅ **Reset Complete!**\nHistory cleared for **{result.modified_count}** files.")
