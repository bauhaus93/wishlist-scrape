#!/bin/env python

import os

from dotenv import load_dotenv
from pymongo import MongoClient

import logger
from scrape_task import update_wishlist_db

if __name__ == "__main__":
    logger.setup()
    load_dotenv()
    log = logger.get()

    scrape_urls = list(
        map(
            lambda name_url: tuple(name_url.split(" ")),
            os.getenv("WISHLIST_SOURCES").split("|"),
        )
    )
    client = MongoClient(os.getenv("DB_URL"))
    db = client.wishlist
    update_wishlist_db(db, scrape_urls)
