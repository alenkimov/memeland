import aiohttp
from better_automation.http import BetterHTTPClient
from yarl import URL


class MemelandAPIError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"(code={self.code}) {self.message}")


class MemelandAPI(BetterHTTPClient):
    DEFAULT_HEADERS = {
        'origin': 'https://www.memecoin.org',
        'referer': 'https://www.memecoin.org/',
    }

    def __init__(self, session: aiohttp.ClientSession, auth_token: str = None, **kwargs):
        super().__init__(session, headers=self.DEFAULT_HEADERS, **kwargs)
        self._auth_token = None
        if auth_token:
            self.set_auth_token(auth_token)

    @property
    def auth_token(self) -> str | None:
        return self._auth_token

    def set_auth_token(self, auth_token: str):
        self._auth_token = auth_token
        self._headers.update({'authorization': f"Bearer {auth_token}"})

    async def request(self, method: str, url, **kwargs):
        response = await super().request(method, url, **kwargs)

        if response.status in (409, 401, 429):
            response_json = await response.json()
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

    async def request_auth_token(self, bind_code: str) -> str:
        url = "https://memefarm-api.memecoin.org/user/twitter-auth"
        payload = {
            "code": bind_code,
            "redirectUri": "https://www.memecoin.org/farming"
        }
        response = await self.request("POST", url, json=payload)
        response_json = await response.json()
        return response_json["accessToken"]

    async def perform_task(self, endpoint: str, payload: dict = None) -> dict:
        url = f'https://memefarm-api.memecoin.org/user/verify/{endpoint}'
        response = await self.request("POST", url, json=payload)
        response_json = await response.json()
        return response_json

