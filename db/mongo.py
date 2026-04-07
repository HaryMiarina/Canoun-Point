from datetime import datetime, timezone

from pymongo import DESCENDING, MongoClient

MONGO_URI = "mongodb://user_db:password_user_db@localhost:27017/db_name"
DATABASE_NAME = "db_name"
SAVED_GAMES_COLLECTION = "saved_games"

_client = MongoClient(MONGO_URI)
_db = _client[DATABASE_NAME]
_collection = _db[SAVED_GAMES_COLLECTION]


def list_saved_game_names() -> list[str]:
    cursor = _collection.find({}, {"_id": 0, "name": 1}).sort("updated_at", DESCENDING)
    return [doc["name"] for doc in cursor if "name" in doc]


def list_saved_games() -> list[dict[str, str]]:
    cursor = _collection.find({}, {"_id": 0, "name": 1, "updated_at": 1}).sort("updated_at", DESCENDING)
    games = []
    for doc in cursor:
        name = doc.get("name")
        if not name:
            continue

        updated_at = doc.get("updated_at")
        if hasattr(updated_at, "strftime"):
            updated_text = updated_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            updated_text = "date inconnue"

        games.append({"name": name, "updated_at": updated_text})

    return games


def save_game(name: str, payload: dict) -> None:
    document = dict(payload)
    document["name"] = name
    document["updated_at"] = datetime.now(timezone.utc)
    _collection.update_one({"name": name}, {"$set": document}, upsert=True)


def load_game(name: str) -> dict | None:
    return _collection.find_one({"name": name}, {"_id": 0})
