
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from shared.http.client import HttpClient


@pytest.mark.asyncio
async def test_http_get():
    client = HttpClient("https://example.com")

    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "success"}

    with patch.object(
        client.client,
        "get",
        new_callable=AsyncMock,
        return_value=mock_response
    ) as mock_get:

        result = await client.get("/users")

        mock_get.assert_awaited_once_with(
            "/users",
            params=None
        )

        assert result == {"status": "success"}

    await client.close()


@pytest.mark.asyncio
async def test_http_post():
    client = HttpClient("https://example.com")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": 101,
        "message": "Profile created"
    }

    request_data = {
        "name": "Harsha",
        "age": 24
    }

    with patch.object(
        client.client,
        "post",
        new_callable=AsyncMock,
        return_value=mock_response
    ) as mock_post:

        result = await client.post("/users", request_data)

        mock_post.assert_awaited_once_with(
            "/users",
            json=request_data
        )

        assert result == {
            "id": 101,
            "message": "Profile created"
        }

    await client.close()

    
@pytest.mark.asyncio
async def test_http_get_handles_404():
    client = HttpClient("https://example.com")

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = (
        __import__("httpx").HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock()
        )
    )

    with patch.object(
        client.client,
        "get",
        new_callable=AsyncMock,
        return_value=mock_response
    ):
        with pytest.raises(__import__("httpx").HTTPStatusError):
            await client.get("/missing-user")

    await client.close()


@pytest.mark.asyncio
async def test_http_get_handles_connection_failure():
    client = HttpClient("https://example.com")

    with patch.object(
        client.client,
        "get",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("Connection failed")
    ):
        with pytest.raises(httpx.ConnectError):
            await client.get("/users")

    await client.close()


@pytest.mark.asyncio
async def test_http_get_handles_timeout():
    client = HttpClient("https://example.com")

    with patch.object(
        client.client,
        "get",
        new_callable=AsyncMock,
        side_effect=httpx.TimeoutException("Request timed out")
    ):
        with pytest.raises(httpx.TimeoutException):
            await client.get("/users")

    await client.close()
    
@pytest.mark.asyncio
async def test_http_client_closes_connection():
    client = HttpClient("https://example.com")

    with patch.object(
        client.client,
        "aclose",
        new_callable=AsyncMock
    ) as mock_close:

        await client.close()

        mock_close.assert_awaited_once()
        
@pytest.mark.asyncio
async def test_http_client_context_manager_closes_connection():
    client = HttpClient("https://example.com")

    with patch.object(
        client.client,
        "aclose",
        new_callable=AsyncMock
    ) as mock_close:

        async with client as active_client:
            assert active_client is client

        mock_close.assert_awaited_once()

def test_http_client_rejects_empty_base_url():
    with pytest.raises(ValueError):
        HttpClient("")


def test_http_client_rejects_invalid_timeout():
    with pytest.raises(ValueError):
        HttpClient("https://example.com", timeout=0)



