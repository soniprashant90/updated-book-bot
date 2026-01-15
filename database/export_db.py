import time
from database.connections_mdb import db

class ExportDB:
    def __init__(self):
        self.col = db.export_state

    async def get(self):
        return await self.col.find_one({"_id": "media_export"})

    async def set_running(self, value: bool):
        await self.col.update_one(
            {"_id": "media_export"},
            {"$set": {
                "is_running": value,
                "updated_at": int(time.time())
            }},
            upsert=True
        )

    async def update(self, last_id, sent):
        await self.col.update_one(
            {"_id": "media_export"},
            {"$set": {
                "last_sent_id": last_id,
                "sent_count": sent,
                "updated_at": int(time.time())
            }},
            upsert=True
        )

    async def reset(self):
        await self.col.delete_one({"_id": "media_export"})


export_db = ExportDB()
