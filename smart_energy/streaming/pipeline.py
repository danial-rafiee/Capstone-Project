"""
Pipeline for real-time stream processing.
"""

from typing import Any, Iterator, Optional
from smart_energy.streaming.source.meter_stream import MeterStream


class Pipeline:
    """
    Chains multiple processing stages together and lets you use
    operators like | or + to pass events sequentially.
    """

    def __init__(self, stages=None):
        self.stages = list(stages) if stages else []

    def __or__(self, other) -> "Pipeline":
        # Support piping processors or other pipelines together
        if isinstance(other, Pipeline):
            return Pipeline(self.stages + other.stages)
        elif hasattr(other, "process"):
            return Pipeline(self.stages + [other])
        raise TypeError("Unsupported type for pipeline operator")

    def __add__(self, other) -> "Pipeline":
        # Allow using + as an alternative to |
        return self.__or__(other)

    def __iter__(self) -> "Pipeline":
        return self

    def process(self, event: Any) -> Optional[Any]:
        # Pass the event through each stage one by one.
        # If any stage drops it (returns None), we stop right here.
        current_data = event
        for stage in self.stages:
            if current_data is None:
                return None
            current_data = stage.process(current_data)
        return current_data

    def run(self, stream: MeterStream) -> Iterator[Any]:
        # Pull items from the stream generator, push them through the pipeline,
        # and yield whatever makes it to the end.
        for event in stream:
            result = self.process(event)
            if result is not None:
                yield result