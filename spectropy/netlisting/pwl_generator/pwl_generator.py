# imports<<<
from __future__ import annotations

from .waveforms import (
    DelaySegment,
    PulseSegment,
    SawtoothSegment,
    SquareSegment,
    StepSegment,
    TriangleSegment,
    WaveformSegment,
)
# >>>

class WaveformGenerator:
    """Build a PWL waveform by composing typed segments.

    scale:
        Time unit suffix appended to each time point, for example ``"n"`` or ``"u"``.
    transition_time:
        Default edge duration used by step-like segments. This is convenient
        when several segments share the same rise/fall time.
    dc_baseline:
        Constant offset added to every output value.
    """

    def __init__(
        self,
        scale: str = "n",
        transition_time: float = 0.0,
        dc_baseline: float = 0.0,
    ) -> None:
        self.scale = scale
        self.transition_time = self._edge_time(transition_time)
        self.dc_baseline = dc_baseline
        self.segments: list[WaveformSegment] = []

    def _edge_time(self, transition_time: float | None) -> float:
        edge_time = self.transition_time if transition_time is None else transition_time
        if edge_time <= 0.0:
            raise ValueError("transition_time must be greater than zero.")
        return edge_time

    def delay(self, duration: float) -> None:
        """Hold the current level for the given duration."""
        self.segments.append(DelaySegment(duration))

    def step(
        self,
        duration: float,
        delta: float,
        transition_time: float | None = None,
    ) -> None:
        """Apply a step of ``delta`` and then hold for ``duration``."""
        self.segments.append(
            StepSegment(duration, delta, self._edge_time(transition_time))
        )

    def pulse(
        self,
        duration: float,
        pulse_value: float,
        delay_before: float = 0.0,
        delay_after: float = 0.0,
        cycles: int = 1,
        transition_time: float | None = None,
    ) -> None:
        """Add a pulse segment that returns to its starting level."""
        self.segments.append(
            PulseSegment(
                duration,
                pulse_value,
                delay_before,
                delay_after,
                self._edge_time(transition_time),
                cycles,
            )
        )

    def square(
        self,
        duration: float,
        start_value: float,
        end_value: float,
        delay_before: float = 0.0,
        delay_after: float = 0.0,
        cycles: int = 1,
        transition_time: float | None = None,
    ) -> None:
        """Add a square waveform between two levels."""
        self.segments.append(
            SquareSegment(
                duration,
                start_value,
                end_value,
                delay_before,
                delay_after,
                self._edge_time(transition_time),
                cycles,
            )
        )

    def triangle(
        self,
        duration: float,
        peak_value: float,
        delay_before: float = 0.0,
        delay_after: float = 0.0,
        cycles: int = 1,
    ) -> None:
        """Add a triangle waveform with a single rise and fall."""
        self.segments.append(
            TriangleSegment(duration, peak_value, delay_before, delay_after, cycles)
        )

    def sawtooth(
        self,
        duration: float,
        start_value: float,
        end_value: float,
        delay_before: float = 0.0,
        delay_after: float = 0.0,
        cycles: int = 1,
        transition_time: float | None = None,
    ) -> None:
        """Add a sawtooth waveform with a default edge time."""
        self.segments.append(
            SawtoothSegment(
                duration,
                start_value,
                end_value,
                delay_before,
                delay_after,
                self._edge_time(transition_time),
                cycles,
            )
        )

    def generate(self) -> list[tuple[str, str]]:
        """Return the waveform as a fresh list of ``(time, voltage)`` pairs."""
        points: list[tuple[float, float]] = [(0.0, 0.0)]
        last_time = 0.0
        last_value = 0.0

        for segment in self.segments:
            segment_points = segment.generate(last_time, last_value)
            if not segment_points:
                continue
            points.extend(segment_points)
            last_time, last_value = segment_points[-1]

        return [
            (
                f"{time:.15f}".rstrip("0").rstrip(".") + self.scale,
                f"{value + self.dc_baseline:.15f}".rstrip("0").rstrip("."),
            )
            for time, value in points
        ]
