from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

from demo.config import HEALTH_API_BASE

JST = ZoneInfo("Asia/Tokyo")


def _civil_date(d: date) -> dict:
    return {"date": {"year": d.year, "month": d.month, "day": d.day}}


def _week_range() -> tuple[date, date]:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=7)
    return start, today


class HealthClient:
    def __init__(self, access_token: str) -> None:
        self._headers = {"Authorization": f"Bearer {access_token}"}

    async def get_profile(self) -> dict:
        async with httpx.AsyncClient() as client:
            profile_resp = await client.get(
                f"{HEALTH_API_BASE}/users/me/profile",
                headers=self._headers,
            )
            profile_resp.raise_for_status()
            identity_resp = await client.get(
                f"{HEALTH_API_BASE}/users/me/identity",
                headers=self._headers,
            )
            identity_resp.raise_for_status()
            return {
                "profile": profile_resp.json(),
                "identity": identity_resp.json(),
            }

    async def daily_steps(self, start: date, end: date) -> list[dict]:
        body = {
            "range": {
                "start": _civil_date(start),
                "end": _civil_date(end),
            },
            "windowSizeDays": 1,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HEALTH_API_BASE}/users/me/dataTypes/steps/dataPoints:dailyRollUp",
                headers=self._headers,
                json=body,
            )
            response.raise_for_status()
            return response.json().get("rollupDataPoints", [])

    async def daily_distance(self, start: date, end: date) -> list[dict]:
        body = {
            "range": {
                "start": _civil_date(start),
                "end": _civil_date(end),
            },
            "windowSizeDays": 1,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HEALTH_API_BASE}/users/me/dataTypes/distance/dataPoints:dailyRollUp",
                headers=self._headers,
                json=body,
            )
            response.raise_for_status()
            return response.json().get("rollupDataPoints", [])

    async def list_sleep(self, start: date, end: date) -> list[dict]:
        start_ts = (
            datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        end_ts = (
            datetime.combine(end, datetime.min.time(), tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        filter_expr = (
            f'sleep.interval.end_time >= "{start_ts}" '
            f'AND sleep.interval.end_time < "{end_ts}"'
        )
        points: list[dict] = []
        page_token: str | None = None

        async with httpx.AsyncClient() as client:
            while True:
                params: dict[str, str | int] = {"filter": filter_expr, "pageSize": 25}
                if page_token:
                    params["pageToken"] = page_token
                response = await client.get(
                    f"{HEALTH_API_BASE}/users/me/dataTypes/sleep/dataPoints",
                    headers=self._headers,
                    params=params,
                )
                response.raise_for_status()
                body = response.json()
                points.extend(body.get("dataPoints", []))
                page_token = body.get("nextPageToken")
                if not page_token:
                    break
        return points


def format_civil_datetime(civil: dict | None) -> str:
    if not civil:
        return "-"
    d = civil.get("date", {})
    t = civil.get("time", {})
    date_str = f"{d.get('year', '?')}-{d.get('month', 0):02d}-{d.get('day', 0):02d}"
    if t:
        return f"{date_str} {t.get('hours', 0):02d}:{t.get('minutes', 0):02d}"
    return date_str


def format_jst(iso: str) -> str:
    if not iso or iso == "-":
        return "-"
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.astimezone(JST).strftime("%Y/%m/%d %H:%M")


def format_civil_jst(civil: dict) -> str:
    d = civil.get("date", {})
    t = civil.get("time", {}) or {}
    return (
        f"{d.get('year', '?')}/{d.get('month', 0):02d}/{d.get('day', 0):02d} "
        f"{t.get('hours', 0):02d}:{t.get('minutes', 0):02d}"
    )


def format_sleep_interval(interval: dict) -> tuple[str, str]:
    civil_start = interval.get("civilStartTime")
    civil_end = interval.get("civilEndTime")
    if civil_start and civil_end:
        return format_civil_jst(civil_start), format_civil_jst(civil_end)
    return (
        format_jst(interval.get("startTime", "-")),
        format_jst(interval.get("endTime", "-")),
    )


def format_duration_hm(minutes_value: str | int | None) -> str:
    if minutes_value is None:
        return "-"
    hours, minutes = divmod(int(minutes_value), 60)
    if hours:
        return f"{hours}時間{minutes}分"
    return f"{minutes}分"


def sleep_sort_key(point: dict) -> str:
    interval = point.get("sleep", {}).get("interval", {})
    return interval.get("endTime") or interval.get("startTime") or ""


def dedupe_sleep_points(sleep_points: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict] = []
    for point in sleep_points:
        interval = point.get("sleep", {}).get("interval", {})
        key = (interval.get("startTime", ""), interval.get("endTime", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(point)
    return unique


def build_sleep_lines(sleep_points: list[dict]) -> list[str]:
    sessions = dedupe_sleep_points(sleep_points)
    if not sessions:
        return ["  データなし"]

    lines = [
        f"  {'就寝 (JST)':<18} {'起床 (JST)':<18} 睡眠時間",
        f"  {'-' * 18} {'-' * 18} {'-' * 8}",
    ]
    for point in sorted(sessions, key=sleep_sort_key, reverse=True):
        sleep = point.get("sleep", {})
        interval = sleep.get("interval", {})
        summary = sleep.get("summary", {})
        start_str, end_str = format_sleep_interval(interval)
        duration = format_duration_hm(summary.get("minutesAsleep"))
        lines.append(f"  {start_str:<18} {end_str:<18} {duration}")
    return lines


def print_health_summary(
    profile_data: dict,
    steps: list[dict],
    distance: list[dict],
    sleep_points: list[dict],
) -> None:
    start, end = _week_range()
    lines: list[str] = [
        "",
        "=" * 62,
        "Google Health API — 直近1週間の健康データ",
        f"期間: {start} 〜 {end - timedelta(days=1)}",
        "=" * 62,
    ]

    profile = profile_data.get("profile", {})
    identity = profile_data.get("identity", {})
    user_id = identity.get("healthUserId", "-")
    age = profile.get("age")
    age_str = f"{age} 歳" if age is not None else "不明"
    lines.append(f"\nユーザー ID: {user_id} / 年齢: {age_str}")

    lines.append("\n[ 日別歩数 ]")
    if not steps:
        lines.append("  データなし")
    else:
        for point in sorted(
            steps, key=lambda p: format_civil_datetime(p.get("civilStartTime"))
        ):
            day = format_civil_datetime(point.get("civilStartTime"))
            count = point.get("steps", {}).get("countSum", "-")
            lines.append(f"  {day}  {count:>6} 歩")

    lines.append("\n[ 日別距離 ]")
    if not distance:
        lines.append("  データなし")
    else:
        for point in sorted(
            distance, key=lambda p: format_civil_datetime(p.get("civilStartTime"))
        ):
            day = format_civil_datetime(point.get("civilStartTime"))
            dist = point.get("distance", {})
            mm = dist.get("millimetersSum") or dist.get("millimeters_sum")
            if mm is not None:
                km = int(mm) / 1_000_000
                lines.append(f"  {day}  {km:>6.2f} km")
            else:
                lines.append(f"  {day}  -")

    lines.append("\n[ 睡眠 ]")
    lines.extend(build_sleep_lines(sleep_points))
    lines.append("\n" + "=" * 62)

    print("\n".join(lines), flush=True)
