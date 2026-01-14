import asyncio
from pyrogram import Client, filters, errors
from pyrogram.types import Message
from motor.motor_asyncio import AsyncIOMotorClient
from info import ADMINS, TARGET_CHANNEL, DATABASE_URI, DATABASE_NAME
import traceback

print("Starting push_files.py loading...")

# Database Connection
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
print(f"   TARGET_CHANNEL type: {type(TARGET_CHANNEL)}")

# -------------------------------------------------------------------------------------
# COMMAND: /checkenv - Check environment variables
# -------------------------------------------------------------------------------------
@Client.on_message(filters.command("checkenv") & filters.private)
async def check_environment(client, message):
    """Check if environment variables are loaded correctly"""
    print(f"[checkenv] Command from user {message.from_user.id}")
    
    await message.reply_text(
        f"🔍 **Environment Check:**\n\n"
        f"**Your User ID:** `{message.from_user.id}`\n"
        f"**ADMINS List:** `{ADMINS}`\n"
        f"**Is Admin?** `{message.from_user.id in ADMINS}`\n\n"
        f"**TARGET_CHANNEL:** `{TARGET_CHANNEL}`\n"
        f"**DATABASE_NAME:** `{DATABASE_NAME}`\n"
        f"**DATABASE_URI:** `{DATABASE_URI[:30]}...`\n\n"
        f"ℹ️ If your ID is not in ADMINS list, add it to environment variables."
    )

# -------------------------------------------------------------------------------------
# COMMAND: /pushall - Push all files to target channel
# -------------------------------------------------------------------------------------
@Client.on_message(filters.command("pushall") & filters.private)
async def push_to_channel(client: Client, message: Message):
    """Push all unpushed files from database to target channel"""
    
    print("=" * 70)
    print("[PUSHALL] COMMAND TRIGGERED!")
    print(f"   User ID: {message.from_user.id}")
    print(f"   User Name: {message.from_user.first_name}")
    print(f"   Chat ID: {message.chat.id}")
    print(f"   ADMINS list: {ADMINS}")
    print(f"   Is user in ADMINS? {message.from_user.id in ADMINS}")
    print("=" * 70)
    
    # Send immediate response
    try:
        status_msg = await message.reply_text("🔄 **Processing your request...**")
        print("SUCCESS: Bot can send messages")
    except Exception as e:
        print(f"ERROR: Cannot send message: {e}")
        traceback.print_exc()
        return
    
    # Admin Check
    user_id = message.from_user.id
    if user_id not in ADMINS:
        print(f"ERROR: Access denied for user {user_id}")
        await status_msg.edit_text(
            f"❌ **Access Denied!**\n\n"
            f"👤 **Your User ID:** `{user_id}`\n"
            f"🔑 **Authorized Admins:** `{ADMINS}`\n\n"
            f"⚠️ **Action Required:**\n"
            f"1. Copy your User ID: `{user_id}`\n"
            f"2. Add it to ADMINS environment variable\n"
            f"3. Restart the bot\n\n"
            f"💡 Use @userinfobot to verify your ID"
        )
        return
    
    print(f"SUCCESS: Admin verified: {user_id}")
    await status_msg.edit_text("✅ **Admin verified!**\n🔄 Checking configuration...")
    
    # Configuration Check
    print(f"   TARGET_CHANNEL: {TARGET_CHANNEL} (type: {type(TARGET_CHANNEL)})")
    
    if not TARGET_CHANNEL or TARGET_CHANNEL == 0:
        print("ERROR: TARGET_CHANNEL not configured")
        await status_msg.edit_text(
            "❌ **Configuration Error!**\n\n"
            "`TARGET_CHANNEL` is not set in environment variables.\n\n"
            "**Setup Instructions:**\n"
            "1. Get your channel ID (use @userinfobot)\n"
            "2. Set TARGET_CHANNEL in environment variables\n"
            "3. Restart the bot"
        )
        return
    
    print("SUCCESS: Configuration check passed")
    await status_msg.edit_text(
        f"✅ **Configuration OK!**\n\n"
        f"📡 **Target Channel:** `{TARGET_CHANNEL}`\n"
        f"🔄 **Connecting to database...**"
    )
    
    # Database Query
    try:
        print("Querying database for unpushed files...")
        query = {"pushed_to_channel": {"$ne": True}}
        total_files = await collection.count_documents(query)
        print(f"Found {total_files} files to push")
    except Exception as e:
        print(f"ERROR: Database query error: {e}")
        traceback.print_exc()
        await status_msg.edit_text(
            f"❌ **Database Error!**\n\n"
            f"Could not query the Files collection.\n\n"
            f"**Error:** `{str(e)[:100]}`"
        )
        return
    
    if total_files == 0:
        print("WARNING: No new files found to push")
        await status_msg.edit_text(
            "✅ **All Files Synced!**\n\n"
            "No new files found in database.\n"
            "All existing files have already been pushed to the channel.\n\n"
            "💡 Use `/resetpush` to clear history and push again."
        )
        return
    
    # Start pushing files
    await status_msg.edit_text(
        f"🚀 **Starting File Push!**\n\n"
        f"📂 **Total Files:** `{total_files}`\n"
        f"📡 **Target:** `{TARGET_CHANNEL}`\n\n"
        f"⚠️ **DO NOT RESTART THE BOT**\n"
        f"⏳ This may take a while..."
    )
    
    sent_count = 0
    error_count = 0
    skipped_count = 0
    last_update = 0
    
    print(f"Starting to push {total_files} files...")
    print("-" * 70)
    
    # Process each file
    async for file_doc in collection.find(query):
        try:
            file_id = file_doc.get('file_id')
            file_type = file_doc.get('file_type', 'document')
            caption = file_doc.get('caption') or file_doc.get('file_name', '')
            
            if not file_id:
                print(f"WARNING: Skipped - No file_id for: {caption[:50]}")
                skipped_count += 1
                continue
            
            print(f"Sending: {caption[:60]}... ({file_type})")
            
            # Send file based on type
            try:
                if file_type == 'video':
                    await client.send_video(
                        chat_id=TARGET_CHANNEL,
                        video=file_id,
                        caption=caption[:1024] if caption else None
                    )
                elif file_type == 'audio':
                    await client.send_audio(
                        chat_id=TARGET_CHANNEL,
                        audio=file_id,
                        caption=caption[:1024] if caption else None
                    )
                elif file_type == 'photo':
                    await client.send_photo(
                        chat_id=TARGET_CHANNEL,
                        photo=file_id,
                        caption=caption[:1024] if caption else None
                    )
                elif file_type == 'voice':
                    await client.send_voice(
                        chat_id=TARGET_CHANNEL,
                        voice=file_id,
                        caption=caption[:1024] if caption else None
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
                        caption=caption[:1024] if caption else None
                    )
                else:  # Default: document
                    await client.send_document(
                        chat_id=TARGET_CHANNEL,
                        document=file_id,
                        caption=caption[:1024] if caption else None
                    )
                
                # Mark as pushed in database
                await collection.update_one(
                    {'_id': file_doc['_id']},
                    {'$set': {'pushed_to_channel': True}}
                )
                
                sent_count += 1
                print(f"   SUCCESS: Sent successfully ({sent_count}/{total_files})")
                
                # Update status message every 10 files
                if sent_count - last_update >= 10:
                    last_update = sent_count
                    try:
                        await status_msg.edit_text(
                            f"🔄 **Pushing Files...**\n\n"
                            f"✅ **Sent:** `{sent_count}/{total_files}`\n"
                            f"❌ **Errors:** `{error_count}`\n"
                            f"⏭️ **Skipped:** `{skipped_count}`\n\n"
                            f"⏳ Please wait..."
                        )
                    except Exception:
                        pass  # Ignore message edit errors
                
            except errors.FloodWait as e:
                print(f"WARNING: FloodWait - Sleeping for {e.value} seconds")
                await asyncio.sleep(e.value + 5)
                continue
                
            except Exception as send_error:
                print(f"   ERROR: Send error: {send_error}")
                error_count += 1
                continue
            
            # Sleep to avoid flooding
            await asyncio.sleep(3)
            
        except Exception as e:
            print(f"ERROR: Error processing file: {e}")
            traceback.print_exc()
            error_count += 1
            continue
    
    # Final summary
    print("=" * 70)
    print("PUSH COMPLETE!")
    print(f"   Sent: {sent_count}")
    print(f"   Errors: {error_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total: {total_files}")
    print("=" * 70)
    
    await status_msg.edit_text(
        f"✅ **Push Complete!**\n\n"
        f"📤 **Successfully Sent:** `{sent_count}`\n"
        f"❌ **Errors:** `{error_count}`\n"
        f"⏭️ **Skipped:** `{skipped_count}`\n"
        f"📊 **Total Processed:** `{total_files}`\n\n"
        f"🎉 All files have been pushed to the channel!"
    )

# -------------------------------------------------------------------------------------
# COMMAND: /resetpush - Reset push status for all files
# -------------------------------------------------------------------------------------
@Client.on_message(filters.command("resetpush") & filters.private)
async def reset_push_status(client: Client, message: Message):
    """Reset pushed_to_channel flag for all files"""
    
    print(f"[resetpush] Command from user {message.from_user.id}")
    
    # Admin check
    if message.from_user.id not in ADMINS:
        print(f"ERROR: Access denied for user {message.from_user.id}")
        await message.reply_text("❌ **Access Denied!** You are not authorized to use this command.")
        return
    
    processing_msg = await message.reply_text("🔄 **Resetting push status...**")
    
    try:
        # Remove pushed_to_channel flag from all documents
        result = await collection.update_many(
            {"pushed_to_channel": True}, 
            {"$unset": {"pushed_to_channel": ""}}
        )
        
        print(f"SUCCESS: Reset complete - Modified {result.modified_count} documents")
        
        await processing_msg.edit_text(
            f"✅ **Reset Complete!**\n\n"
            f"📝 **Files Reset:** `{result.modified_count}`\n\n"
            f"You can now use `/pushall` to push all files again."
        )
    except Exception as e:
        print(f"ERROR: Reset error: {e}")
        traceback.print_exc()
        await processing_msg.edit_text(f"❌ **Error:** `{str(e)[:100]}`")

# -------------------------------------------------------------------------------------
# COMMAND: /pushstatus - Check how many files are pending
# -------------------------------------------------------------------------------------
@Client.on_message(filters.command("pushstatus") & filters.private)
async def push_status(client: Client, message: Message):
    """Check push status statistics"""
    
    print(f"[pushstatus] Command from user {message.from_user.id}")
    
    if message.from_user.id not in ADMINS:
        return
    
    try:
        total = await collection.count_documents({})
        pushed = await collection.count_documents({"pushed_to_channel": True})
        pending = total - pushed
        
        await message.reply_text(
            f"📊 **Push Status:**\n\n"
            f"📂 **Total Files:** `{total}`\n"
            f"✅ **Already Pushed:** `{pushed}`\n"
            f"⏳ **Pending:** `{pending}`\n\n"
            f"💡 Use `/pushall` to push pending files."
        )
    except Exception as e:
        print(f"ERROR: Status check error: {e}")
        await message.reply_text(f"❌ **Error:** `{str(e)[:100]}`")

# Plugin loaded confirmation
print("=" * 70)
print("SUCCESS: push_files.py loaded successfully!")
print("   Registered commands:")
print("   - /pushall (Push all files to channel)")
print("   - /resetpush (Reset push status)")
print("   - /pushstatus (Check pending files)")
print("   - /checkenv (Check environment variables)")
print(f"   ADMINS: {ADMINS}")
print(f"   TARGET_CHANNEL: {TARGET_CHANNEL}")
print("=" * 70)
```

## Key Changes Made:

1. ✅ **Removed all emojis from print statements** - replaced with text like "SUCCESS:", "ERROR:", "WARNING:"
2. ✅ **Kept emojis ONLY inside f-strings and quotes** where they're safe
3. ✅ **Added proper separators** with `"=" * 70` for better log readability
4. ✅ **All print statements are now plain ASCII**

## Now:

1. **Replace your `plugins/push_files.py`** with this corrected code
2. **Save the file**
3. **Restart your bot completely**
4. **Check the logs** - you should see:
```
======================================================================
SUCCESS: push_files.py loaded successfully!
   Registered commands:
   - /pushall (Push all files to channel)
   - /resetpush (Reset push status)
   - /pushstatus (Check pending files)
   - /checkenv (Check environment variables)
   ADMINS: [915392007]
   TARGET_CHANNEL: -1003641067210
======================================================================
