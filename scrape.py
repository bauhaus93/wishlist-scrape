#!/bin/env python

import os
import time
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

import logger

log = logger.get()


def scrape_wishlists(name_url_pairs):
    if name_url_pairs is None:
        log.error("Received no name/urls pairs for scraping!")
        return []
    wishlists = []
    for (name, url) in name_url_pairs:
        wishlist = scrape_wishlist(url, name)
        if wishlist is None or len(wishlist) == 0:
            return []
        else:
            wishlists.extend(wishlist)
    return wishlists


def get_page_content(url):
    # USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36/8mqQhSuL-09 "
    USER_AGENT = (
        "Mozilla/5.0 (compatible; Googlebot/2.1; startmebot/1.0; +https://start.me/bot)"
    )
    TRIES = 5
    TRY_TIMOUT_INCREMENT = 5.0
    timeout = 5.0
    for i in range(TRIES):
        response = requests.get(url, headers={"User-Agent": USER_AGENT})
        if response.status_code == 200:
            return response.text
        log.warning("Received http %d, try %d/%d", response.status_code, i + 1, TRIES)
        time.sleep(timeout)
        timeout += TRY_TIMOUT_INCREMENT
    log.error("Couldn't retrieve url after %d tries!", TRIES)
    return None


def scrape_wishlist(url, wishlist_name):
    log.info("Scraping for wishlist '%s' at '%s'", wishlist_name, url)
    parsed_url = urlparse(url)

    content = get_page_content(url)
    if not content:
        return None

    soup = BeautifulSoup(content, "html.parser")

    try:
        list_items = soup.html.find("ul", id="g-items")
    except AttributeError:
        try:
            list_items = soup.find("ul", id="g-items")
        except AttributeError:
            list_items = None
    if list_items is None:
        log.error("Wishlist parsing error: Couldn't find listing with id 'g-items'")
        return []

    products = []
    for item in list_items.find_all("li"):
        product = collect_product_info(item)
        if not product:
            log.error("Wishlist parsing error: Couldn't parse product info for item")
            return []
        product = {
            **product,
            "source": url,
            "source_name": wishlist_name,
            "url": urlunparse((*parsed_url[:2], *urlparse(product["link"])[2:])),
            "url_img": urlunparse(
                (*parsed_url[:1], *urlparse(product["img_link"])[1:])
            ),
        }
        products.append(product)

    next_path = get_next_page_path(list_items)
    if next_path:
        parsed_next = urlparse(next_path)
        next_url = urlunparse((*parsed_url[:2], *parsed_next[2:]))
        next_products = scrape_wishlist(next_url, wishlist_name)
        if next_products is None:
            return None
        else:
            products.extend(next_products)

    return products


def alternative(soup):
    list_items = soup.find("ul", id="g-items")
    for item in list_items.find_all("li"):
        print("ITEM")


def collect_product_info(item):
    product = {
        "name": get_item_name(item),
        "price": get_item_price(item),
        "quantity": get_item_request_quantity(item),
        "stars": get_item_stars(item),
        "link": get_item_link_path(item),
        "img_link": get_item_image_path(item),
        "item_id": get_item_id(item),
    }
    if any(map(lambda v: v is None, product.values())):
        return None
    return product


def get_next_page_path(item_list):
    next_page_tag = item_list.find(
        lambda tag: tag.name == "a"
        and "g-visible-no-js" in tag.get("class", "")
        and "wl-see-more" in tag.get("class", "")
        and tag.get("href")
    )
    if not next_page_tag:
        return None
    return next_page_tag.get("href")


def get_item_id(item):
    item_id = item.get("data-itemid", None)
    if not item_id:
        log.error("Could not get id for item")
        return None
    return item_id


def get_item_name(item):
    item_name_tag = item.find(
        lambda tag: tag.name == "a" and "itemName" in tag.get("id", "")
    )
    if not item_name_tag:
        log.error("Could not find item name tag")
        return None
    try:
        return item_name_tag.contents[0].strip()
    except IndexError:
        log.error("Item name tag has no content, full tag is '%s'", item_name_tag)
        return None


def get_item_link_path(item):
    item_name_tag = item.find(
        lambda tag: tag.name == "a" and "itemName" in tag.get("id", "")
    )
    if not item_name_tag:
        log.error("Could not find item name tag")
        return None
    return item_name_tag.get("href")


def get_item_image_path(item):
    img_tag = item.find(lambda tag: tag.name == "img" and tag.get("src"))
    if not img_tag:
        log.error("Could not find img tag for item")
        return None
    return img_tag.get("src")


def get_item_request_quantity(item):
    span_requested = item.find(
        lambda tag: tag.name == "span" and "itemRequested_" in tag.get("id", "")
    )
    if not span_requested:
        log.error("Could not find span for item quantity")
        return None
    try:
        return int(span_requested.contents[0])
    except ValueError:
        log.error(
            "Could not convert item quantity to int, string was '%s'",
            span_requested.contents[0],
        )
        return None
    except IndexError:
        log.error("Request span has no content, string was '%s'", span_requested)
        return None


def get_item_stars(item):
    star_link_tag = item.find(
        lambda tag: tag.name == "a"
        and "reviewStarsPopoverLink" in tag.get("class", "")
        and tag.get("aria-label")
    )
    if not star_link_tag:
        return 0.0
    star_string = star_link_tag.get("aria-label")
    try:
        return float(star_string.split(" ")[0])
    except ValueError:
        log.error("Could not convert stars to float, full field was '%s' % star_string")
        return None


def get_item_price(item):
    price_div = item.find(
        lambda tag: tag.name == "div" and "price-section" in tag.get("class", "")
    )
    if price_div is None:
        log.warn("Could not find price div in item")
        return 0.0
    span_whole = price_div.find(
        lambda tag: tag.name == "span" and "a-price-whole" in tag.get("class", "")
    )
    span_fraction = price_div.find(
        lambda tag: tag.name == "span" and "a-price-fraction" in tag.get("class", "")
    )
    if span_whole is None:
        log.warn("Could not find span of whole price in price section")
        return 0.0
    if span_fraction is None:
        log.warn("Could not find span of fractional price in price section")
        return 0.0
    try:
        price_whole = int(span_whole.contents[0])
    except ValueError:
        log.error(
            "Could not convert price whole to integer, string was '%s'",
            span_fraction.string,
        )
        return 0.0
    try:
        price_fraction = int(span_fraction.contents[0])
    except ValueError:
        log.error(
            "Could not convert price fraction to integer, string was '%s'",
            span_fraction.string,
        )
        return 0.0
    return price_whole + price_fraction / 100.0
