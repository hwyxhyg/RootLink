"""Minimal Supabase REST helpers used by the FastAPI service."""

import logging
import os
from typing import Any, Optional

import httpx
from fastapi import HTTPException, Request


logger = logging.getLogger(__name__)


def _settings() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not service_key:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured on the backend.",
        )
    return url, service_key


async def authenticated_user(request: Request) -> dict[str, Any]:
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")

    url, service_key = _settings()
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{url}/auth/v1/user",
            headers={
                "apikey": service_key,
                "Authorization": authorization,
            },
        )
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return response.json()


async def save_archive(user_id: str, data: dict[str, Any]) -> None:
    url, service_key = _settings()
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{url}/rest/v1/archives",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            json={"user_id": user_id, "data": data},
        )
    if response.status_code >= 300:
        logger.error("Supabase archive save failed: %s", response.text)
        raise HTTPException(status_code=502, detail="Archive save failed.")


async def load_archive(user_id: str) -> Optional[dict[str, Any]]:
    url, service_key = _settings()
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{url}/rest/v1/archives",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
            },
            params={"user_id": f"eq.{user_id}", "select": "data", "limit": "1"},
        )
    if response.status_code >= 300:
        logger.error("Supabase archive load failed: %s", response.text)
        raise HTTPException(status_code=502, detail="Archive load failed.")
    rows = response.json()
    return rows[0].get("data") if rows else None


async def record_visit(ip: str, session_id: str) -> None:
    try:
        url, service_key = _settings()
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{url}/rest/v1/visits",
                headers={
                    "apikey": service_key,
                    "Authorization": f"Bearer {service_key}",
                    "Content-Type": "application/json",
                },
                json={"ip": ip, "session_id": session_id},
            )
    except Exception:
        logger.debug("Visit logging skipped.", exc_info=True)
