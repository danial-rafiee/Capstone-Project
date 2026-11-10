"""Explicit local weekly opening hours, translated into UTC measurement windows.

There is no default production calendar. Local intervals must stay within a
calendar day; use two entries on adjacent days for overnight opening hours.
Ambiguous/nonexistent DST boundary times are rejected rather than guessed.
"""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .time_window import TimeWindow, duration_seconds


class OperatingSchedule:
    def __init__(self, timezone_name: str, weekly_hours: dict, closed_dates=()):
        if not isinstance(timezone_name, str) or not timezone_name:
            raise TypeError("A named building timezone is required.")
        try:
            self._timezone = ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError("Unknown building timezone or unavailable IANA timezone data.") from error
        self._timezone_name = timezone_name
        if not isinstance(weekly_hours, dict):
            raise TypeError("Weekly hours must be a dictionary keyed by weekday 0 to 6.")
        normalized = {}
        for weekday, intervals in weekly_hours.items():
            if type(weekday) is not int or not 0 <= weekday <= 6:
                raise ValueError("Weekday must be an integer from Monday=0 to Sunday=6.")
            if not isinstance(intervals, (list, tuple)):
                raise TypeError("Each weekday must contain a list of local time pairs.")
            pairs = []
            for interval in intervals:
                if not isinstance(interval, (tuple, list)) or len(interval) != 2:
                    raise ValueError("An opening interval requires a start and end time.")
                start = self._minutes(interval[0])
                end = self._minutes(interval[1])
                if not 0 <= start < end <= 1440:
                    raise ValueError("Opening intervals must increase within one local day.")
                pairs.append((start, end))
            pairs.sort()
            if any(left[1] > right[0] for left, right in zip(pairs, pairs[1:])):
                raise ValueError("Opening intervals must not overlap.")
            normalized[weekday] = tuple(pairs)
        self._weekly_hours = normalized
        self._closed_dates = frozenset(closed_dates)
        if any(type(day) is not date for day in self._closed_dates):
            raise TypeError("Closed dates must be date objects, not datetime values.")

    @staticmethod
    def _minutes(value: str) -> int:
        if not isinstance(value, str):
            raise TypeError("Opening times must be HH:MM strings.")
        pieces = value.split(':')
        if len(pieces) != 2 or any(len(piece) != 2 or not piece.isascii() or not piece.isdigit()
                                   for piece in pieces):
            raise ValueError("Opening times must use HH:MM format.")
        hours, minutes = map(int, pieces)
        if not 0 <= hours <= 24 or not 0 <= minutes < 60 or (hours == 24 and minutes != 0):
            raise ValueError("Opening times must be between 00:00 and 24:00.")
        return hours * 60 + minutes

    def get_timezone(self) -> str:
        return self._timezone_name

    def to_dict(self) -> dict:
        def clock(minutes):
            return f'{minutes // 60:02}:{minutes % 60:02}'
        return {
            "timezone": self._timezone_name,
            "weekly_hours": {str(day): [[clock(a), clock(b)] for a, b in pairs]
                             for day, pairs in sorted(self._weekly_hours.items())},
            "closed_dates": [day.isoformat() for day in sorted(self._closed_dates)],
        }

    def _utc_boundary(self, local: datetime) -> datetime:
        candidates = set()
        for fold in (0, 1):
            candidate = local.replace(tzinfo=self._timezone, fold=fold).astimezone(timezone.utc)
            if candidate.astimezone(self._timezone).replace(tzinfo=None) == local:
                candidates.add(candidate)
        if len(candidates) != 1:
            raise ValueError("Opening boundary is ambiguous or nonexistent due to a timezone transition.")
        return candidates.pop()

    def occupied_intervals(self, window: TimeWindow) -> list[tuple[datetime, datetime]]:
        if not isinstance(window, TimeWindow):
            raise TypeError("A TimeWindow is required.")
        day = window.start.astimezone(self._timezone).date()
        last_day = (window.end - timedelta(microseconds=1)).astimezone(self._timezone).date()
        result = []
        while day <= last_day:
            if day not in self._closed_dates:
                for start_minutes, end_minutes in self._weekly_hours.get(day.weekday(), ()):
                    midnight = datetime(day.year, day.month, day.day)
                    start = max(window.start, self._utc_boundary(midnight + timedelta(minutes=start_minutes)))
                    end = min(window.end, self._utc_boundary(midnight + timedelta(minutes=end_minutes)))
                    if end > start:
                        if result and start <= result[-1][1]:
                            result[-1] = (result[-1][0], max(result[-1][1], end))
                        else:
                            result.append((start, end))
            if day == last_day:
                break
            day += timedelta(days=1)
        return result

    def occupied_seconds(self, window: TimeWindow):
        return sum((duration_seconds(start, end) for start, end in self.occupied_intervals(window)),
                   duration_seconds(window.start, window.start))
