# Handles time window settings

from datetime import datetime, timedelta, timezone

class TimeRange:

    def __init__(self, preset: str = "24h", start: datetime | None = None,
                 end: datetime | None = None):
        self.configure(preset, start, end)

    def configure(self, preset: str = "24h", start: datetime | None = None,
                  end: datetime | None = None) -> None:

        if not isinstance(preset, str):
            raise TypeError("Preset must be text.")
        if preset not in ("24h", "7d", "30d", "custom"):
            raise ValueError("Use 24h, 7d, 30d or custom.")
        end = self._utc(datetime.now(timezone.utc) if end is None else end)
        if start is not None:
            start = self._utc(start)
            preset = "custom"
        elif preset == "custom":
            raise ValueError("A custom window requires a start timestamp.")
        else:
            days = {"24h": 1, "7d": 7, "30d": 30}[preset]
            start = end - timedelta(days=days)
        if start >= end:
            raise ValueError("Start must be earlier than end.")
        self._preset, self._start, self._end = preset, start, end

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError("Timestamps must be datetime objects.")
        if value.utcoffset() is None:
            raise ValueError("Timestamps must include a timezone.")
        return value.astimezone(timezone.utc)

    def get_preset(self) -> str:
        return self._preset

    def set_preset(self, value: str) -> None:
        self.configure(value, end=self._end)

    def get_start(self) -> datetime:
        return self._start

    def set_start(self, value: datetime) -> None:
        self.configure("custom", value, self._end)

    def get_end(self) -> datetime:
        return self._end

    def set_end(self, value: datetime) -> None:
        start = self._start if self._preset == "custom" else None
        self.configure(self._preset, start, value)

    preset = property(get_preset, set_preset)
    start = property(get_start, set_start)
    end = property(get_end, set_end)

    def to_dict(self) -> dict:
        return {"preset": self._preset, "start": self._start.isoformat(),
                "end": self._end.isoformat()}
