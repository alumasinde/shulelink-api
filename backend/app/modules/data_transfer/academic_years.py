from __future__ import annotations

from datetime import date
from uuid import UUID


async def resolve_import_academic_year(cur, tenant_id: UUID, value: object) -> str | None:
    """Resolve an import academic-year value to the stored academic-year name.

    Exact names remain the primary key. A four-digit year such as ``2026`` is
    also accepted when it unambiguously identifies an academic year whose
    calendar dates fall in that year (for example 2026-01-01 through
    2026-11-30). This keeps spreadsheets human-friendly without creating
    duplicate academic-year records.
    """
    raw = "" if value is None else str(value).strip()
    if not raw:
        return None

    await cur.execute(
        "SELECT name FROM academic_years WHERE tenant_id=%s AND name=%s",
        (str(tenant_id), raw),
    )
    exact = await cur.fetchone()
    if exact:
        return str(exact[0])

    if not (len(raw) == 4 and raw.isdigit()):
        return None

    year = int(raw)
    start = date(year, 1, 1)
    next_year = date(year + 1, 1, 1)

    # Preferred match: the academic year starts and ends in the supplied
    # calendar year. This covers the common Jan-Nov/Jan-Dec school calendar.
    await cur.execute(
        """
        SELECT name
        FROM academic_years
        WHERE tenant_id=%s
          AND start_date >= %s
          AND start_date < %s
          AND end_date >= %s
          AND end_date < %s
        ORDER BY is_current DESC, start_date, id
        """,
        (str(tenant_id), start, next_year, start, next_year),
    )
    candidates = await cur.fetchall()
    if len(candidates) == 1:
        return str(candidates[0][0])
    if len(candidates) > 1:
        names = ", ".join(str(row[0]) for row in candidates[:10])
        raise ValueError(
            f"Academic year '{raw}' is ambiguous. Matching academic years: {names}"
        )

    return None
