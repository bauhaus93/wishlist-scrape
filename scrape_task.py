import time

import pymongo

import logger
from scrape import scrape_wishlists

log = logger.get()


def update_wishlist_db(db, url_pairs):
    log.info("Start scraping of wishlists...")
    wishlist = scrape_wishlists(url_pairs)
    if len(wishlist) == 0:
        log.error("Couldn't scrape wishlists!")
        return
    log.info("Wishlists successfully scraped, found %d products!", len(wishlist))
    if need_wishlist_update(wishlist, db):
        log.info("Wishlist changed, add new one")
        add_wishlist_to_db(wishlist, db)
    else:
        log.info("Wishlist didn't change, only check for product updates")
        update_products(wishlist, db)
        log.info("Updated products!")


def need_wishlist_update(wishlist, db):
    last_wishlist = db.wishlist.find_one(sort=[("timestamp", pymongo.DESCENDING)])
    if last_wishlist is None:
        return True
    last_products = set(
        map(
            lambda p: p["item_id"],
            db.product.find(
                {"_id": {"$in": last_wishlist["products"]}},
                {"item_id": True},
            ),
        )
    )
    new_products = set(map(lambda p: p["item_id"], wishlist))

    return last_products != new_products


def add_wishlist_to_db(wishlist_list, db):
    log.info("Adding wishlist to database...")

    wishlist_timestamp = int(time.time())
    wishlist_id = db.wishlist.insert_one(
        {"timestamp": wishlist_timestamp, "products": []}
    ).inserted_id
    product_ids = []
    for entry in wishlist_list:
        product = db.product.find_one({"item_id": entry["item_id"]})
        source = db.source.find_one({"name": entry["source_name"]})
        if source is None:
            source_id = db.source.insert_one(
                {"name": entry["source_name"], "url": entry["source"]}
            ).inserted_id
            source = db.source.find_one({"_id": source_id})
        if product is None:
            log.info(
                "Adding product %s, price = %.02f", entry["name"][:20], entry["price"]
            )
            product_id = db.product.insert_one(
                {
                    "name": entry["name"],
                    "price": int(100.0 * entry["price"]),
                    "quantity": entry["quantity"],
                    "stars": int(10.0 * entry["stars"]),
                    "url": entry["url"],
                    "url_img": entry["url_img"],
                    "item_id": entry["item_id"],
                    "source": source["_id"],
                    "first_seen": wishlist_timestamp,
                    "last_seen": wishlist_timestamp,
                }
            ).inserted_id
        else:
            entry["source"] = source["_id"]
            entry["last_seen"] = wishlist_timestamp
            update_product(product, entry, db)
            product_id = product["_id"]
        product_ids.append(product_id)

    db.wishlist.update_one({"_id": wishlist_id}, {"$set": {"products": product_ids}})
    log.info("Added wishlist to database")


def update_products(products_scraped, db):
    curr_time = int(time.time())
    for product_scraped in products_scraped:
        product = db.product.find_one({"item_id": product_scraped["item_id"]})
        if product is None:
            log.warning(
                "Wanted to update product, but product isn't present in db: '%s[..]'",
                product_scraped["name"][:20],
            )
            continue
        source = db.source.find_one({"name": product_scraped["source_name"]})
        if source is None:
            source_id = db.source.insert_one(
                {
                    "name": product_scraped["source_name"],
                    "url": product_scraped["source"],
                }
            ).inserted_id
        else:
            source_id = source["_id"]
        product_scraped["source"] = source_id
        product_scraped["last_seen"] = curr_time
        update_product(product, product_scraped, db)


def update_product(product_db, product_scraped, db):
    product_updated = {}

    if product_db.get("first_seen", None) is None:
        product_updated["first_seen"] = int(time.time())
    scraped_price = int(product_scraped["price"] * 100)
    if product_db["price"] != scraped_price and scraped_price > 0:
        product_updated["price"] = scraped_price
    if int(product_db["stars"] * 10) != int(product_scraped["stars"] * 10):
        product_updated["stars"] = product_scraped["stars"]
    string_fields = ["quantity", "url", "url_img", "item_id", "source", "last_seen"]
    for field in string_fields:
        if product_db.get(field, None) != product_scraped[field]:
            product_updated[field] = product_scraped[field]
    if len(product_updated) > 0:
        for key in product_updated:
            if key != "last_seen":
                log.info(
                    "Value '%s' of '%s[..]' changed: %s -> %s",
                    key,
                    product_db["name"][:20],
                    product_db.get(key, "None"),
                    product_scraped.get(key, "None"),
                )
        db.product.update_one({"_id": product_db["_id"]}, {"$set": product_updated})
