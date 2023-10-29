from contextlib import asynccontextmanager

import aiohttp
from better_automation import TwitterAPI

from bot.api import MemelandAPI

from bot.account import Account
from bot.logger import LoggingLevel, logger
from bot.paths import ACCOUNTS_JSON


@asynccontextmanager
async def authenticated_twitter(
        session: aiohttp.ClientSession,
        account: Account,
) -> TwitterAPI:
    twitter = TwitterAPI(session, auth_token=account.auth_tokens["twitter"], useragent=account.useragent)
    if "twitter_ct0" in account.auth_tokens:
        twitter.set_ct0(account.auth_tokens["twitter_ct0"])
    yield twitter
    account.auth_tokens["twitter_ct0"] = twitter.ct0


async def auth_memeland(
        session: aiohttp.ClientSession,
        twitter: TwitterAPI,
        account: Account,
        logging_level: LoggingLevel = "DEBUG"
) -> MemelandAPI:
    memeland = MemelandAPI(session, useragent=account.useragent)

    if "memeland" not in account.auth_tokens:
        bind_data = {
            'response_type': 'code',
            'client_id': 'ZXh0SU5iS1pwTE5xclJtaVNNSjk6MTpjaQ',
            'redirect_uri': 'https://www.memecoin.org/farming',
            'scope': 'users.read tweet.read offline.access',
            'state': 'state',
            'code_challenge': 'challenge',
            'code_challenge_method': 'plain'
        }

        bind_code = await twitter.bind_app(**bind_data)
        auth_token = await memeland.request_auth_token(bind_code)
        account.auth_tokens["memeland"] = auth_token
        account.save(ACCOUNTS_JSON)
        logger.log(logging_level, f"{account} Успешная авторизация")

    memeland.set_auth_token(account.auth_tokens["memeland"])
    return memeland


@asynccontextmanager
async def authenticated_memeland(
        session: aiohttp.ClientSession,
        account: Account,
        logging_level: LoggingLevel = "DEBUG"
) -> MemelandAPI:
    async with authenticated_twitter(session, account) as twitter:
        yield await auth_memeland(session, twitter, account, logging_level)
