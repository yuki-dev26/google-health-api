"""Gemini API 用の健康データコンテキストを生成する。"""

import asyncio
import json
from datetime import date, datetime, timedelta, timezone

from demo.health_client import (
    HealthClient,
    dedupe_sleep_points,
    format_civil_datetime,
    format_duration_hm,
    format_sleep_interval,
    sleep_sort_key,
)


def default_date_range(days: int = 7) -> tuple[date, date]:
    """返り値: (start, end) — end は API 用の排他的上限（翌日）。"""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days)
    return start, today


def parse_inclusive_range(start_str: str, end_str: str) -> tuple[date, date]:
    start = date.fromisoformat(start_str)
    end_inclusive = date.fromisoformat(end_str)
    if start > end_inclusive:
        raise ValueError("開始日は終了日以前にしてください。")
    return start, end_inclusive + timedelta(days=1)


async def fetch_health_snapshot(
    access_token: str,
    start: date,
    end_exclusive: date,
) -> dict:
    client = HealthClient(access_token)

    profile_data, steps, distance, sleep_points = await asyncio.gather(
        client.get_profile(),
        client.daily_steps(start, end_exclusive),
        client.daily_distance(start, end_exclusive),
        client.list_sleep(start, end_exclusive),
    )

    profile = profile_data.get("profile", {})
    identity = profile_data.get("identity", {})

    daily_steps = []
    for point in sorted(
        steps, key=lambda p: format_civil_datetime(p.get("civilStartTime"))
    ):
        daily_steps.append(
            {
                "date": format_civil_datetime(point.get("civilStartTime")),
                "steps": point.get("steps", {}).get("countSum"),
            }
        )

    daily_distance = []
    for point in sorted(
        distance, key=lambda p: format_civil_datetime(p.get("civilStartTime"))
    ):
        dist = point.get("distance", {})
        mm = dist.get("millimetersSum") or dist.get("millimeters_sum")
        km = round(int(mm) / 1_000_000, 2) if mm is not None else None
        daily_distance.append(
            {
                "date": format_civil_datetime(point.get("civilStartTime")),
                "distance_km": km,
            }
        )

    sleep_sessions = []
    for point in sorted(
        dedupe_sleep_points(sleep_points), key=sleep_sort_key, reverse=True
    ):
        sleep = point.get("sleep", {})
        interval = sleep.get("interval", {})
        summary = sleep.get("summary", {})
        bed, wake = format_sleep_interval(interval)
        sleep_sessions.append(
            {
                "bedtime_jst": bed,
                "wake_jst": wake,
                "sleep_duration": format_duration_hm(summary.get("minutesAsleep")),
            }
        )

    end_inclusive = end_exclusive - timedelta(days=1)
    return {
        "period": {
            "start": str(start),
            "end": str(end_inclusive),
        },
        "profile": {
            "health_user_id": identity.get("healthUserId"),
            "age": profile.get("age"),
        },
        "daily_steps": daily_steps,
        "daily_distance_km": daily_distance,
        "sleep_sessions": sleep_sessions,
    }


def format_health_context(snapshot: dict) -> str:
    period = snapshot.get("period", {})
    label = f"{period.get('start', '?')} 〜 {period.get('end', '?')}"
    return (
        f"## ユーザーの健康データ（{label}）\n\n"
        "以下は Google Health API から取得した健康データです。"
        "回答ではこの数値を根拠にしてください。\n\n"
        f"```json\n{json.dumps(snapshot, ensure_ascii=False, indent=2)}\n```"
    )
