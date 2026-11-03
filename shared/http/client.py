

import httpx


class HttpClient:

    def __init__(
        self,
        base_url: str,
        timeout: float = 15.0
    ):
        if not base_url:
            raise ValueError("base_url must not be empty")

        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    async def get(self, path: str, params: dict | None = None):
        response = await self.client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, data: dict):
        response = await self.client.post(path, json=data)
        response.raise_for_status()
        return response.json()

    async def close(self):
        if not self.client.is_closed:
            await self.client.aclose()

