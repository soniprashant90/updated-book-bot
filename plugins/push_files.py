from pyrogram import Client, filters

print("🔴 push_files.py: Starting to load...")

# Try importing from info.py
try:
    from info import ADMINS, TARGET_CHANNEL, DATABASE_URI, DATABASE_NAME
    print(f"✅ Imports successful!")
    print(f"   ADMINS: {ADMINS}")
    print(f"   TARGET_CHANNEL: {TARGET_CHANNEL}")
    print(f"   TARGET_CHANNEL type: {type(TARGET_CHANNEL)}")
except Exception as e:
    print(f"❌ Import error: {e}")
    ADMINS = []
    TARGET_CHANNEL = 0

# Simple test command
@Client.on_message(filters.command("pushall"))
async def test_pushall(client, message):
    print(f"🔴 PUSHALL TRIGGERED by user {message.from_user.id}")
    
    try:
        await message.reply_text(
            f"✅ **Command Working!**\n\n"
            f"👤 Your ID: `{message.from_user.id}`\n"
            f"🔑 ADMINS: `{ADMINS}`\n"
            f"📢 TARGET_CHANNEL: `{TARGET_CHANNEL}`\n"
            f"✓ You are admin: `{message.from_user.id in ADMINS}`"
        )
        print("✅ Reply sent successfully")
    except Exception as e:
        print(f"❌ Error in command: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

print("✅ push_files.py loaded successfully!")
