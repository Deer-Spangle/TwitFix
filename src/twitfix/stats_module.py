from contextlib import suppress
from datetime import date
from typing import Any

from sanic.log import logger

with suppress(ImportError):
    import pymongo

with suppress(ImportError):
    import google.cloud.firestore


class StatsBase:
    def __init__(self, config) -> None:
        pass

    async def add_to_stat(self, metric: str) -> None:
        pass

    async def get_stats(self, day: str) -> Any:
        pass


class MongoStats(StatsBase):
    def __init__(self, config) -> None:
        self.client = pymongo.MongoClient(config.MONGO_DB, connect=False)
        table = config.MONGO_DB_TABLE
        self.db = self.client[table]

    async def add_to_stat(self, metric: str):
        today = str(date.today())
        try:
            collection = self.db.stats.find_one({"date": today})
            query = {"date": today}
            change = {"$inc": {metric: 1}}
            out = self.db.stats.update_one(query, change)
        except:
            collection = self.db.stats.insert_one(
                {"date": today, "embeds": 1, "linksCached": 1, "api": 1, "downloads": 1}
            )

    async def get_stats(self, day: str):
        collection = self.db.stats.find_one({"date": day})
        return collection


class FirestoreStats(StatsBase):
    def __init__(self, config) -> None:
        self.fire = google.cloud.firestore.AsyncClient()
        self.stats = self.fire.collection("statistics")

    async def add_to_stat(self, metric: str):
        today = str(date.today())
        update = {
            "date": today,
            "embeds": google.cloud.firestore.Increment(0),
            "linksCached": google.cloud.firestore.Increment(0),
            "api": google.cloud.firestore.Increment(0),
            "downloads": google.cloud.firestore.Increment(0),
        }
        update[metric] = google.cloud.firestore.Increment(1)
        await self.stats.document(today).set(update, merge=True)

    async def get_stats(self, day: str):
        doc = await self.stats.document(day).get()
        return {
            "date": day,
            "embeds": 0,
            "linksCached": 0,
            "api": 0,
            "downloads": 0,
            **doc.to_dict(),
        }


class NoStats(StatsBase):
    def __init__(self, config) -> None:
        pass

    async def add_to_stat(self, metric: str):
        pass

    async def get_stats(self, day: str):
        return {"date": day, "embeds": 0, "linksCached": 0, "api": 0, "downloads": 0}


def initialize_stats(stat_module: str, config) -> StatsBase:
    if stat_module == "db":
        if not globals().get("pymongo"):
            raise LookupError("the pymongo library was not included during build.")
        return MongoStats(config)

    if stat_module == "firestore":
        if not globals().get("google"):
            raise LookupError("the firestore library was not included during build.")
        logger.info(" ➤ [ ✔ ] Stats module backed by Firestore")
        return FirestoreStats(config)

    if stat_module in ["none", "json"]:
        logger.info(" ➤ [ X ] Stats module disabled")
        return NoStats(config)

    raise LookupError(f"Stat module not recognized. {stat_module}")
