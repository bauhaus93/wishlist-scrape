import time

import pymongo

import logger

log = logger.get()


def apply_fixes(db):
    fix_missing_last_seen(db)


def fix_missing_last_seen(db):
    product_ids = db.product.find({"last_seen": None}, {"_id": True})
    for product in product_ids:
        product_id = product["_id"]
        last_wishlist = db.wishlist.find_one(
            {"products": product_id},
            {"timestamp": True},
            sort=[("timestamp", pymongo.DESCENDING)],
        )
        log.info(
            "Fixing missing field 'last_seen' of %s: Set to %d",
            product_id,
            last_wishlist["timestamp"],
        )
        db.product.update_one(
            {"_id": product_id}, {"$set": {"last_seen": last_wishlist["timestamp"]}}
        )
