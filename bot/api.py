import aiohttp
from better_automation.http import BetterHTTPClient
from multidict import MultiDict
from yarl import URL
from bot.logger import logger
import tls_client


class MemelandAPIError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"(code={self.code}) {self.message}")


class MaxAttemptsReached(Exception):
    pass


class MemelandAPI(BetterHTTPClient):
    DEFAULT_HEADERS = {
        'origin': 'https://www.memecoin.org',
        'referer': 'https://www.memecoin.org/',
    }

    def __init__(self, session: aiohttp.ClientSession, auth_token: str = None, **kwargs):
        self._useragent = None
        self._tls_session = tls_client.Session(
            client_identifier="chrome112",
            random_tls_extension_order=True,
        )
        self._tls_session.headers.update(self.DEFAULT_HEADERS)
        super().__init__(session, headers=self.DEFAULT_HEADERS, **kwargs)
        self._auth_token = None
        if auth_token:
            self.set_auth_token(auth_token)

    @property
    def useragent(self) -> str | None:
        return self._useragent

    def set_useragent(self, useragent: str):
        self._useragent = useragent
        self._tls_session.headers.update({'user-agent': useragent})
        super().set_useragent(useragent)

    @property
    def auth_token(self) -> str | None:
        return self._auth_token

    def set_auth_token(self, auth_token: str):
        self._auth_token = auth_token
        self._headers.update({'authorization': f"Bearer {auth_token}"})

    async def request(self, method: str, url, **kwargs):
        response = await super().request(method, url, **kwargs)

        if response.status in (409, ):
            response_json = await response.json()
            code = response_json["status"]
            message = response_json["error"]
            raise MemelandAPIError(code, message)

        return response

    def tls_request(self, method: str, url, **kwargs):
        response = self._tls_session.execute_request(method, url, **kwargs)

        if response.status_code in (409, ):
            response_json = response.json()
            code = response_json["status"]
            message = response_json["error"]
            raise MemelandAPIError(code, message)

        return response

    async def request_tasks(self) -> dict:
        url = "https://memefarm-api.memecoin.org/user/tasks"
        response = await self.request("GET", url)
        response_json = await response.json()
        return response_json

    async def request_info(self) -> dict:
        url = "https://memefarm-api.memecoin.org/user/info"
        response = await self.request("GET", url)
        response_json = await response.json()
        return response_json

    async def link_wallet(self, address: str, message: str, signed_message: str):
        url = "https://memefarm-api.memecoin.org/user/verify/link-wallet"
        payload = {
            'address': address,
            'delegate': address,
            'message': message,
            'signature': signed_message,
        }
        response = await self.request("POST", url, json=payload)
        response_json = await response.json()
        return response_json

    async def request_oauth_url(self) -> URL:
        url = "https://memefarm-api.memecoin.org/user/twitter-auth"
        params = {'callback': 'https://www.memecoin.org/farming'}
        response = await self.request("GET", url, params=params, allow_redirects=False)
        return URL(response.headers['location'])

    async def request_bind_data(self, max_attempts: int = 50) -> MultiDict | None:
        attempt = 1
        while attempt < max_attempts:
            logger.debug(f"Запрашиваю ссылку для привязки Твиттера (попытка {attempt})...")
            url = await self.request_oauth_url()
            if "client_id" in url.query:
                return url.query
            attempt += 1
        raise MaxAttemptsReached(f"Не удалось запросить ссылку для привязки твиттер-аккаунта:"
                                 f" достигнуто максимальное количество попыток ({max_attempts})."
                                 f" Попробуйте позже")

    async def request_auth_token(self, bind_code: str) -> str:
        url = "https://memefarm-api.memecoin.org/user/twitter-auth"
        payload = {
            "code": bind_code,
            "redirectUri": "https://www.memecoin.org/farming"
        }
        response = await self.request("POST", url, json=payload)
        response_json = await response.json()
        return response_json["accessToken"]

        # response = self.tls_request("POST", url, json=payload)
        # return response.json()["accessToken"]

    async def auth(self, bind_code: str):
        auth_token = await self.request_auth_token(bind_code)
        self.set_auth_token(auth_token)
