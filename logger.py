import logging


def setup():
    FORMAT = r"[%(asctime)-15s - %(levelname)s] %(message)s"
    DATE_FORMAT = r"%Y-%m-%d %H:%M:%S"
    logging.basicConfig(level=logging.WARNING, format=FORMAT, datefmt=DATE_FORMAT)
    get().setLevel(logging.INFO)


def get():
    return logging.getLogger("scraper")
