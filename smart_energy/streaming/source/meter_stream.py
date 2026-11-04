"""Consume meter events one at a time."""

from collections.abc import Iterable, Iterator

from .meter_event import MeterEvent


class MeterStream(Iterator[MeterEvent]):
    def __init__(self, events: Iterable[MeterEvent]):
        self._iterator = iter(events)

    def __iter__(self) -> "MeterStream":
        return self

    def __next__(self) -> MeterEvent:
        event = next(self._iterator)

        if not isinstance(event, MeterEvent):
            raise TypeError("Every stream item must be a MeterEvent.")

        return event