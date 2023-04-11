import os
import time
import logging
from datetime import datetime
import asyncio
from functools import partial
import random

import requests
from bs4 import BeautifulSoup
import telegram

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

bot_api_key = os.getenv("BOT_API_KEY")
chat_id = os.getenv("CHAT_ID")

bot = telegram.Bot(bot_api_key)
send_message = partial(bot.send_message, chat_id=chat_id)


def get_url_and_cookies():
    r = requests.get("https://service.berlin.de/dienstleistung/120686/")
    r.raise_for_status()

    if r.status_code == 200:
        soup = BeautifulSoup(r.text, features="html.parser")
        for link in soup.find_all("a"):
            if link.text == "Termin berlinweit suchen":
                return link.get("href"), r.cookies

    raise RefreshCookieException(f"unexpected error {r.status_code}")


class RefreshCookieException(Exception):
    pass


async def check_booking_availability(url, cookies):
    r = requests.get(url, cookies=cookies)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, features="html.parser")

    for buchbar in soup.select("td.buchbar > a"):
        label = buchbar.get("aria-label")
        href = buchbar.get("href")

        await send_message(text=f"{label} https://service.berlin.de{href}")

        logger.info(f"buchbar: {buchbar}")

    nicht_count = len(soup.select("td.nichtbuchbar"))
    if nicht_count == 0:
        raise RefreshCookieException

    logger.info(nicht_count)

    if random.randint(0, 100) in range(10, 30):
        logger.error(soup.prettify())

    logger.info(datetime.now())


async def main():
    await send_message(text=f"bang! {datetime.now()}")

    (url, cookies) = get_url_and_cookies()

    while True:
        await check_booking_availability(url, cookies)
        time.sleep(60)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()

    while True:
        try:
            loop.run_until_complete(main())
        except RefreshCookieException as ex:
            logger.info(f"Got exception: {ex}. Refreshing cookies")
        except requests.exceptions.HTTPError as ex:
            logger.info(f"Got http exception: {ex}. Refreshing cookies")
        finally:
            loop.close()
