"""
Abstract base processor and pipeline orchestration for Subsystem C.
Implements:
- Abstract Base Classes (BaseStreamProcessor with @abstractmethod)
- Operator Overloading (__or__) for chaining stream filters and transformers
"""
from abc import ABC, abstractmethod
from typing import Iterator, List, Optional
from smart_energy.streaming.source.meter_event import MeterEvent


class BaseStreamProcessor(ABC):
    """Abstract interface defining the event-processing contract."""

    @abstractmethod
    def process(self, event: MeterEvent) -> Optional[MeterEvent]:
        """
        Processes a single MeterEvent.
        Returns the processed event (or augmented event), or None to drop it.
        """
        pass

    def __or__(self, other: "BaseStreamProcessor") -> "Pipeline":
        """Overload `|` operator to compose processing stages sequentially."""
        if not isinstance(other, BaseStreamProcessor):
            return NotImplemented
        return Pipeline([self, other])


class Pipeline(BaseStreamProcessor):
    """Composed pipeline chaining multiple BaseStreamProcessors."""

    def __init__(self, stages: List[BaseStreamProcessor]):
        self.stages: List[BaseStreamProcessor] = []
        for stage in stages:
            if isinstance(stage, Pipeline):
                self.stages.extend(stage.stages)
            else:
                self.stages.append(stage)

    def process(self, event: MeterEvent) -> Optional[MeterEvent]:
        current: Optional[MeterEvent] = event
        for stage in self.stages:
            if current is None:
                return None
            current = stage.process(current)
        return current

    def __or__(self, other: BaseStreamProcessor) -> "Pipeline":
        if not isinstance(other, BaseStreamProcessor):
            return NotImplemented
        if isinstance(other, Pipeline):
            return Pipeline(self.stages + other.stages)
        return Pipeline(self.stages + [other])

    def run(self, stream: Iterator[MeterEvent]) -> Iterator[dict]:
        """Consumes a stream iterator and yields final evaluated payloads."""
        for raw_event in stream:
            processed = self.process(raw_event)
            if processed is not None:
                yield processed