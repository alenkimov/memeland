from better_automation import TwitterAPI
from better_automation.twitter.errors import HTTPException as TwitterException

from bot.account import Account
from bot.api import MemelandAPI
from bot.logger import logger, LoggingLevel
from bot.paths import ACCOUNTS_JSON


ELON_MUSK_ID = 44196397


async def update_twitter_status(
        twitter: TwitterAPI,
        account: Account,
        logging_level: LoggingLevel = "DEBUG",
):
    try:
        await twitter.follow(ELON_MUSK_ID)
        account.twitter_status = "GOOD"
        account.save(ACCOUNTS_JSON)
    except TwitterException as e:
        if any(code in e.api_codes for code in (32, )):
            account.twitter_status = "BAD_TOKEN"
            account.save(ACCOUNTS_JSON)
        if any(code in e.api_codes for code in (64, )):
            account.twitter_status = "BANNED"
            account.save(ACCOUNTS_JSON)
        if any(code in e.api_codes for code in (326, )):
            account.twitter_status = "LOCKED"
            account.save(ACCOUNTS_JSON)

    logger.log(logging_level, f"{account} Статус Твиттер аккаунта: {account.twitter_status}")


async def update_twitter_info(
        twitter: TwitterAPI,
        account: Account,
        logging_level: LoggingLevel = "DEBUG",
):
    twitter_username = await twitter.request_username()
    account.twitter_info = await twitter.request_user_info(twitter_username)
    account.save(ACCOUNTS_JSON)
    logger.log(logging_level, f"{account} Информация о Твиттер аккаунте успешно запрошена")


async def update_memeland_info(
        memeland: MemelandAPI,
        account: Account,
        logging_level: LoggingLevel = "DEBUG",
):
    account.memeland_info = await memeland.request_info()
    account.tasks = await memeland.request_tasks()
    account.save(ACCOUNTS_JSON)
    logger.log(logging_level, f"{account} Информация об аккаунте Memeland и тасках успешно запрошена")
