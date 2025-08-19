import logging

from awsl.awsl import WbAwsl
from awsl.config import settings


logging.basicConfig(
    format="%(asctime)s: %(levelname)s: %(name)s: %(message)s",
    level=logging.INFO
)
logging.info(f"Starting Weibo AWSL with settings: {settings.headers}")

WbAwsl.start()
