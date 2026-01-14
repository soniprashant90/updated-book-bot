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
# COMMAND: /pushall (FIXED VERSION)
# -------------------------------------------------------------------------------------

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
            file_type = file_doc.get('file_type', 'document')  # Get file type
            caption = file_doc.get('caption', None)
            
            if not caption:
                caption = file_doc.get('file_name', '')

            if not file_id:
                skipped_count += 1
                continue

            # Send File Based on Type (FIXED: Use correct Pyrogram methods)
            try:
                if file_type == 'video':
                    await client.send_video(
                        chat_id=TARGET_CHANNEL,
                        video=file_id,
                        caption=caption
                    )
                elif file_type == 'audio':
                    await client.send_audio(
                        chat_id=TARGET_CHANNEL,
                        audio=file_id,
                        caption=caption
                    )
                elif file_type == 'photo':
                    await client.send_photo(
                        chat_id=TARGET_CHANNEL,
                        photo=file_id,
                        caption=caption
                    )
                elif file_type == 'voice':
                    await client.send_voice(
                        chat_id=TARGET_CHANNEL,
                        voice=file_id,
                        caption=caption
                    )
                elif file_type == 'video_note':
                    await client.send_video_note(
                        chat_id=TARGET_CHANNEL,
                        video_note=file_id
                    )
                elif file_type == 'animation':
                    await client.send_animation(
                        chat_id=TARGET_CHANNEL,
                        animation=file_id,
                        caption=caption
                    )
                else:  # Default to document
                    await client.send_document(
                        chat_id=TARGET_CHANNEL,
                        document=file_id,
                        caption=caption
                    )

                # Mark as Sent in Database
                await collection.update_one(
                    {'_id': file_doc['_id']},
                    {'$set': {'pushed_to_channel': True}}
                )

                sent_count += 1
                
                if sent_count % 50 == 0:
                    await status_msg.edit(
                        f"🔄 **Syncing Files...**\n"
                        f"✅ Sent: {sent_count}\n"
                        f"❌ Errors: {error_count}\n"
                        f"⏭️ Skipped: {skipped_count}\n"
                        f"📂 Total New: {total_files}"
                    )

            except Exception as send_error:
                print(f"❌ Error sending file {file_id}: {send_error}")
                error_count += 1
                # Don't mark as pushed if sending failed
                continue

            await asyncio.sleep(3) 

        except errors.FloodWait as e:
            print(f"⚠️ FloodWait: Sleeping for {e.value} seconds")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            print(f"❌ Error processing file: {e}")
            error_count += 1

    # Final Summary
    await status_msg.edit(
        f"✅ **Sync Complete!**\n\n"
        f"📤 **Sent:** `{sent_count}`\n"
        f"❌ **Errors:** `{error_count}`\n"
        f"⏭️ **Skipped:** `{skipped_count}`\n"
        f"📊 **Total Processed:** `{total_files}`"
    )

# -------------------------------------------------------------------------------------
# COMMAND: /resetpush
# -------------------------------------------------------------------------------------
@Client.on_message(filters.command("resetpush"))
async def reset_push_status(client, message):
    if message.from_user.id not in ADMINS:
        return # Silent ignore for safety
        
    processing_msg = await message.reply_text("🔄 **Resetting Database Status...**")
    result = await collection.update_many(
        {"pushed_to_channel": True}, 
        {"$unset": {"pushed_to_channel": ""}}
    )
    await processing_msg.edit(
        f"✅ **Reset Complete!**\n"
        f"History cleared for **{result.modified_count}** files.\n\n"
        f"You can now run `/pushall` again to resend all files."
    )
