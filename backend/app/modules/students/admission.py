from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import HTTPException

from app.core.database import get_pool

DEFAULTS = {
    "admission_number_prefix": "ADM",
    "admission_number_separator": "-",
    "admission_number_include_year": "true",
    "admission_number_year_format": "YYYY",
    "admission_number_padding": "4",
    "admission_number_start": "1",
    "admission_number_reset_yearly": "true",
}


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def format_admission_number(prefix: str, separator: str, include_year: bool, year_format: str, sequence: int, padding: int, admission_date: date) -> str:
    year = str(admission_date.year) if year_format == "YYYY" else str(admission_date.year)[-2:]
    parts: list[str] = []
    if prefix:
        parts.append(prefix.strip())
    if include_year:
        parts.append(year)
    parts.append(str(sequence).zfill(padding))
    return (separator or "").join(parts)


async def get_admission_number_settings(tenant_id: UUID) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT setting_key, setting_value FROM school_settings WHERE tenant_id=%s AND setting_key LIKE 'admission_number_%'",
                (str(tenant_id),),
            )
            rows = await cur.fetchall()
    values = DEFAULTS.copy()
    values.update({row[0]: row[1] for row in rows})
    return {
        "prefix": values["admission_number_prefix"] or "",
        "separator": values["admission_number_separator"] or "",
        "include_year": _as_bool(values["admission_number_include_year"], True),
        "year_format": values["admission_number_year_format"] if values["admission_number_year_format"] in {"YYYY", "YY"} else "YYYY",
        "padding": _as_int(values["admission_number_padding"], 4, 1, 10),
        "start": _as_int(values["admission_number_start"], 1, 1, 1_000_000_000),
        "reset_yearly": _as_bool(values["admission_number_reset_yearly"], True),
    }


async def save_admission_number_settings(tenant_id: UUID, payload: dict, user_id: UUID) -> dict:
    prefix = (payload.get("prefix") or "").strip().upper()
    separator = payload.get("separator") or ""
    year_format = payload.get("year_format") or "YYYY"
    if year_format not in {"YYYY", "YY"}:
        raise HTTPException(422, "year_format must be YYYY or YY")
    if len(prefix) > 30 or len(separator) > 5:
        raise HTTPException(422, "Admission number prefix or separator is too long")
    padding = _as_int(str(payload.get("padding")), 4, 1, 10)
    start = _as_int(str(payload.get("start")), 1, 1, 1_000_000_000)
    include_year = bool(payload.get("include_year", True))
    reset_yearly = bool(payload.get("reset_yearly", True))

    values = {
        "admission_number_prefix": prefix,
        "admission_number_separator": separator,
        "admission_number_include_year": "true" if include_year else "false",
        "admission_number_year_format": year_format,
        "admission_number_padding": str(padding),
        "admission_number_start": str(start),
        "admission_number_reset_yearly": "true" if reset_yearly else "false",
    }
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for key, value in values.items():
                value_type = "boolean" if key in {"admission_number_include_year", "admission_number_reset_yearly"} else ("integer" if key in {"admission_number_padding", "admission_number_start"} else "string")
                await cur.execute(
                    """INSERT INTO school_settings (id,tenant_id,setting_key,setting_value,value_type,updated_by)
                       VALUES (UUID(),%s,%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value),value_type=VALUES(value_type),updated_by=VALUES(updated_by)""",
                    (str(tenant_id), key, value, value_type, str(user_id)),
                )
    return await get_admission_number_settings(tenant_id)


async def next_admission_number(tenant_id: UUID, admission_date: date | None = None) -> str:
    settings = await get_admission_number_settings(tenant_id)
    effective_date = admission_date or date.today()
    sequence_key = str(effective_date.year) if settings["reset_yearly"] else "global"
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT IGNORE INTO admission_number_sequences (tenant_id,sequence_key,current_number) VALUES (%s,%s,%s)",
                    (str(tenant_id), sequence_key, settings["start"] - 1),
                )
                await cur.execute(
                    "SELECT current_number FROM admission_number_sequences WHERE tenant_id=%s AND sequence_key=%s FOR UPDATE",
                    (str(tenant_id), sequence_key),
                )
                row = await cur.fetchone()
                if row is None:
                    raise HTTPException(500, "Admission number sequence could not be initialized")
                current = int(row[0])

                for _ in range(10000):
                    current += 1
                    candidate = format_admission_number(
                        settings["prefix"], settings["separator"], settings["include_year"],
                        settings["year_format"], current, settings["padding"], effective_date,
                    )
                    await cur.execute(
                        "SELECT 1 FROM students WHERE tenant_id=%s AND admission_number=%s LIMIT 1",
                        (str(tenant_id), candidate),
                    )
                    if not await cur.fetchone():
                        await cur.execute(
                            "UPDATE admission_number_sequences SET current_number=%s WHERE tenant_id=%s AND sequence_key=%s",
                            (current, str(tenant_id), sequence_key),
                        )
                        await conn.commit()
                        return candidate
            raise HTTPException(409, "Unable to generate a unique admission number")
        except Exception:
            await conn.rollback()
            raise
