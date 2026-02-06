import os
import time

import httpx

_token = None
_expire_at = 0


def _get_wechat_credentials() -> tuple[str, str]:
    appid = os.getenv("WECHAT_APPID", "").strip()
    secret = os.getenv("WECHAT_SECRET", "").strip()
    if not appid or not secret:
        raise RuntimeError("WECHAT_APPID or WECHAT_SECRET is not set")
    return appid, secret


async def get_access_token() -> str:
    global _token, _expire_at

    now = int(time.time())
    if _token and now < _expire_at - 120:
        return _token

    appid, secret = _get_wechat_credentials()
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"grant_type": "client_credential", "appid": appid, "secret": secret}

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    if "access_token" not in data:
        raise RuntimeError(f"get_access_token failed: {data}")

    _token = data["access_token"]
    _expire_at = now + int(data.get("expires_in", 7200))
    return _token
