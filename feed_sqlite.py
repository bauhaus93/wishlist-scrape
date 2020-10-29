import sqlite3
import time

import pymongo

import logger

log = logger.get()


def feed(mongo_db, sqlite_file):
    conn = sqlite3.connect(sqlite_file)
    c = conn.cursor()

    feed_missing_products(mongo_db, c)
    feed_old_wishlists(mongo_db, c)


def feed_old_wishlists(mongo_db, sqlite_db):
    mongo_min_ts = mongo_db.wishlist.find_one(
        {}, {"timestamp": True}, sort=[("timestamp", pymongo.ASCENDING)]
    )["timestamp"]
    log.info("MIN_TS = %d", mongo_min_ts)

    sqlite_db.execute("SELECT * FROM wishlist WHERE timestamp < ?", (mongo_min_ts,))

    for old_wl in sqlite_db.fetchall():
        sqlite_db.execute(
            "SELECT product.item_id FROM wishlist INNER JOIN wishlist_product ON wishlist.id=wishlist_product.whishlist_id INNER JOIN product ON wishlist_product.product_id=product.id  WHERE wishlist.id=?",
            (old_wl[0],),
        )
        item_ids = list(map(lambda res: res[0], sqlite_db.fetchall()))
        if len(item_ids) >= 25:
            mongo_product_ids = list(
                map(
                    lambda res: res["_id"],
                    mongo_db.product.find(
                        {"item_id": {"$in": item_ids}}, {"_id": True}
                    ),
                )
            )
            if len(item_ids) == len(mongo_product_ids):
                mongo_wishlist = {
                    "timestamp": old_wl[1],
                    "value": int(100 * old_wl[2]),
                    "products": mongo_product_ids,
                }
                mongo_db.wishlist.insert_one(mongo_wishlist)
                log.info(
                    "Inserted old wishlist with timestamp = %d, value = %d, products = %d",
                    mongo_wishlist["timestamp"],
                    mongo_wishlist["value"],
                    len(mongo_wishlist["products"]),
                )
            else:
                log.warn("Could not match count of products for wishlist")


def feed_missing_products(mongo_db, sqlite_db):
    mongo_products = set(
        map(lambda prod: prod["item_id"], mongo_db.product.find({}, {"item_id": True}))
    )

    sqlite_db.execute("SELECT * FROM product")
    for product in sqlite_db.fetchall():
        if not product[-2] in mongo_products:
            source = sqlite_db.execute(
                "SELECT name FROM source WHERE id=?", (product[6],)
            )
            source_name = sqlite_db.fetchone()[0]

            mongo_source = mongo_db.source.find_one({"name": source_name})

            sqlite_db.execute(
                "SELECT * FROM wishlist INNER JOIN wishlist_product ON wishlist.id=wishlist_product.whishlist_id INNER JOIN product ON wishlist_product.product_id=product.id  WHERE product.id=?",
                (product[0],),
            )
            timestamps = list(map(lambda res: res[1], sqlite_db.fetchall()))
            first_seen = min(timestamps)
            last_seen = max(timestamps)
            mongo_product = {
                "name": product[1],
                "price": int(100 * product[2]),
                "quantity": product[-1],
                "stars": int(10 * product[3]),
                "url": product[4],
                "url_img": product[5],
                "item_id": product[-2],
                "source": mongo_source["_id"],
                "first_seen": first_seen,
                "last_seen": last_seen,
            }
            mongo_db.product.insert_one(mongo_product)
            log.info("Added missing product: %s", mongo_product["name"])
