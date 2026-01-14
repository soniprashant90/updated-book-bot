import asyncio
from pyrogram import Client, filters, errors
from motor.motor_asyncio import AsyncIOMotorClient
from info import ADMINS, TARGET_CHANNEL, DATABASE_URI, DATABASE_NAME

# Database Connection
try:
    db_client = AsyncIOMotorClient(DATABASE_URI)
    db = db_client[DATABASE_NAME]
    collection = db['Files'] 
    print("✅ Database connected successfully in push_files.py")
except Exception as e:
    print(f"❌ Database Connection Error: {e}")

# -------------------------------------------------------------------------------------
# COMMAND: /pushall (DEBUG VERSION WITH EXTENSIVE LOGGING)
# -------------------------------------------------------------------------------------

@Client.on_message(filters.command("pushall"))
async def push_to_channel(client, message):
    print("=" * 50)
    print("🔴 PUSHALL COMMAND TRIGGERED!")
    print(f"User ID: {message.from_user.id}")
    print(f"Chat ID: {message.chat.id}")
    print(f"ADMINS list: {ADMINS}")
    print(f"Is user in ADMINS? {message.from_user.id in ADMINS}")
    print("=" * 50)
    
    # Send immediate response to confirm command is received
    try:
        test_msg = await message.reply_text("🔴 DEBUG: Command received!")
        print("✅ Bot can send messages")
    except Exception as e:
        print(f"❌ Cannot send message: {e}")
        return
    
    # 1. DEBUG CHECK: Are you an Admin?
    user_id = message.from_user.id
    if user_id not in ADMINS:
        print(f"❌ User {user_id} is NOT in ADMINS list")
        await test_msg.edit(
            f"❌ **Access Denied**\n\n"
            f"👤 **Your ID:** `{user_id}`\n"
            f"🔑 **Allowed Admins:** `{ADMINS}`\n\n"
            f"⚠️ *Please copy your ID and add it to the ADMINS variable in your settings.*"
        )
        return
    
    print("✅ User is admin, continuing...")
    await test_msg.edit("✅ Admin verified, checking configuration...")

    # 2. Configuration Check
    print(f"TARGET_CHANNEL value: {TARGET_CHANNEL}")
    print(f"TARGET_CHANNEL type: {type(TARGET_CHANNEL)}")
    
    if not TARGET_CHANNEL or TARGET_CHANNEL == 0:
        print("❌ TARGET_CHANNEL not configured")
        await test_msg.edit("❌ **Configuration Error:**\n`TARGET_CHANNEL` ID is missing in your settings (Env Variables).")
        return

    print("✅ TARGET_CHANNEL configured")
    await test_msg.edit(f"🔄 **Connecting to Database...**\nTarget Channel: `{TARGET_CHANNEL}`")
    
    # 3. Find files that do NOT have the 'pushed_to_channel' flag
    try:
        print("🔍 Querying database...")
        query = {"pushed_to_channel": {"$ne": True}}
        total_files = await collection.count_documents(query)
        print(f"📊 Found {total_files} files to push")
    except Exception as e:
        print(f"❌ Database query error: {e}")
        await test_msg.edit(f"❌ **DB Error:** Could not access the 'Files' collection.\nError: {e}")
        return
    
    if total_files == 0:
        print("⚠️ No files to push")
        await test_msg.edit("✅ **All files are already synced!**\nNo new files found to push.")
        return

    await test_msg.edit(
        f"📂 Found **{total_files}** new files.\n"
        f"🚀 Starting push to channel...\n\n"
        f"**⚠️ DO NOT RESTART THE BOT**"
    )

    sent_count = 0
    error_count = 0
    skipped_count = 0

    # 4. Start Loop
    print("🚀 Starting file push loop...")
    async for file_doc in collection.find(query):
        try:
            file_id = file_doc.get('file_id')
            file_type = file_doc.get('file_type', 'document')
            caption = file_doc.get('caption', None)
            
            if not caption:
                caption = file_doc.get('file_name', '')

            print(f"Processing: {caption[:50]}... (Type: {file_type})")

            if not file_id:
                print(f"⚠️ Skipped - No file_id")
                skipped_count += 1
                continue

            # Send File Based on Type
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

                print(f"✅ Sent successfully: {caption[:50]}")

                # Mark as Sent in Database
                await collection.update_one(
                    {'_id': file_doc['_id']},
                    {'$set': {'pushed_to_channel': True}}
                )

                sent_count += 1
                
                if sent_count % 10 == 0:  # Update every 10 files for debugging
                    print(f"📊 Progress: {sent_count}/{total_files}")
                    await test_msg.edit(
                        f"🔄 **Syncing Files...**\n"
                        f"✅ Sent: {sent_count}\n"
                        f"❌ Errors: {error_count}\n"
                        f"⏭️ Skipped: {skipped_count}\n"
                        f"📂 Total New: {total_files}"
                    )

            except Exception as send_error:
                print(f"❌ Error sending file: {send_error}")
                error_count += 1
                continue

            await asyncio.sleep(3) 

        except errors.FloodWait as e:
            print(f"⚠️ FloodWait: Sleeping for {e.value} seconds")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            print(f"❌ Error processing file: {e}")
            error_count += 1

    # Final Summary
    print("=" * 50)
    print(f"✅ Push complete - Sent: {sent_count}, Errors: {error_count}, Skipped: {skipped_count}")
    print("=" * 50)
    
    await test_msg.edit(
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
    print(f"🔴 RESETPUSH command triggered by user {message.from_user.id}")
    
    if message.from_user.id not in ADMINS:
        print(f"❌ User {message.from_user.id} is not admin")
        return
        
    processing_msg = await message.reply_text("🔄 **Resetting Database Status...**")
    result = await collection.update_many(
        {"pushed_to_channel": True}, 
        {"$unset": {"pushed_to_channel": ""}}
    )
    
    print(f"✅ Reset complete - Modified {result.modified_count} documents")
    
    await processing_msg.edit(
        f"✅ **Reset Complete!**\n"
        f"History cleared for **{result.modified_count}** files.\n\n"
        f"You can now run `/pushall` again to resend all files."
    )

# Add this at the very end of the file
print("✅ push_files.py plugin loaded successfully!")
