import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

from config import EXPORT_CHANNEL_ID
from database import media_db, export_db
from utils import admin_filter   # already used in your bot

DELAY = 2  # seconds


@Client.on_message(filters.command("export_media") & admin_filter)
async def export_media(client, message):
    state = await export_db.get()

    if state and state.get("is_running"):
        await message.reply("⚠ Export already running")
        return

    await export_db.set_running(True)

    last_id = state.get("last_sent_id") if state else None
    sent = state.get("sent_count", 0) if state else 0

    query = {"_id": {"$gt": last_id}} if last_id else {}
    cursor = media_db.col.find(query).sort("_id", 1)

    await message.reply("📤 Export started / resumed")

    try:
        async for doc in cursor:
            try:
                await client.send_cached_media(
                    chat_id=EXPORT_CHANNEL_ID,
                    file_id=doc["file_ref"],
                    caption=doc.get("caption")
                )
                sent += 1
                await export_db.update(doc["_id"], sent)
                await asyncio.sleep(DELAY)

            except FloodWait as e:
                await asyncio.sleep(e.value)

    finally:
        await export_db.set_running(False)

    await message.reply(f"✅ Export completed\nTotal sent: {sent}")


@Client.on_message(filters.command("export_status") & admin_filter)
async def export_status(_, message):
    state = await export_db.get()
    total = await media_db.col.count_documents({})

    if not state:
        await message.reply("No export started yet.")
        return

    await message.reply(
        f"📊 Export Status\n"
        f"Sent: {state.get('sent_count', 0)}\n"
        f"Total: {total}\n"
        f"Remaining: {total - state.get('sent_count', 0)}"
    )


@Client.on_message(filters.command("export_reset") & admin_filter)
async def export_reset(_, message):
    await export_db.reset()
    await message.reply("♻ Export progress reset.\nRun /export_media again.")
