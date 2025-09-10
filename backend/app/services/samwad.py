from typing import Dict, Any, Optional, Tuple
import httpx
from ..config import get_settings


settings = get_settings()


async def send_via_samwad(
    phone_number: str,
    body: str,
    *,
    image: Optional[Tuple[str, bytes, str]] = None,  # (filename, bytes, mime)
) -> Dict[str, Any]:
    """Send a message via Samwad API.

    Posts multipart/form-data to settings.SAMWAD_SEND_URL with fields:
    - phone: recipient number
    - token: API token
    - message/text: message body (send both for compatibility)
    - image: optional binary file (if provided)
    """
    url = settings.SAMWAD_SEND_URL

    data = {
        "phone": str(phone_number),
        "token": settings.SAMWAD_TOKEN,
        # send both keys to be tolerant of API variants
        "message": body,
        "text": body,
    }

    files = None
    if image is not None:
        fname, content, mime = image
        files = {"image": (fname, content, mime or "application/octet-stream")}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, data=data, files=files)
            # Try to parse JSON; if not JSON, return text
            try:
                out = resp.json()
            except Exception:
                out = {"status_code": resp.status_code, "text": resp.text[:2000]}
            out.setdefault("status_code", resp.status_code)
            if resp.is_success:
                out.setdefault("status", "ok")
            else:
                out.setdefault("status", "error")
            return out
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def send_location_pin(
    phone_number: str,
    latitude: float,
    longitude: float,
    *,
    name: Optional[str] = None,
    address: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a WhatsApp location pin via Samwad WPBOX API."""
    url = settings.SAMWAD_LOCATION_URL
    data = {
        "phone": str(phone_number),
        "token": settings.SAMWAD_TOKEN,
        "latitude": str(latitude),
        "longitude": str(longitude),
    }
    if name:
        data["name"] = name
    if address:
        data["address"] = address
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, data=data)
            try:
                out = resp.json()
            except Exception:
                out = {"status_code": resp.status_code, "text": resp.text[:2000]}
            out.setdefault("status_code", resp.status_code)
            out.setdefault("status", "ok" if resp.is_success else "error")
            return out
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def request_location(
    phone_number: str,
    body: str = "Please share your location",
) -> Dict[str, Any]:
    """Send a WhatsApp interactive location request via WPBOX API."""
    url = settings.SAMWAD_LOCATION_REQUEST_URL
    payload = {"token": settings.SAMWAD_TOKEN, "phone": str(phone_number), "body": body}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, json=payload)
            try:
                out = resp.json()
            except Exception:
                out = {"status_code": resp.status_code, "text": resp.text[:2000]}
            out.setdefault("status_code", resp.status_code)
            out.setdefault("status", "ok" if resp.is_success else "error")
            return out
    except Exception as e:
        return {"status": "error", "error": str(e)}
