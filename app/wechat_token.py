import os, time
import httpx

APPID = os.getenv("WECHAT_APPID", "")
SECRET = os.getenv("WECHAT_SECRET", "")

_token = None
_expire_at = 0

async def get_access_token() -> str:
    global _token, _expire_at

    now = int(time.time())
    if _token and now < _expire_at - 120:
        return _token

    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"grant_type": "client_credential", "appid": APPID, "secret": SECRET}

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    if "access_token" not in data:
        raise RuntimeError(f"get_access_token failed: {data}")

    _token = data["access_token"]
    _expire_at = now + int(data.get("expires_in", 7200))
    return _token
