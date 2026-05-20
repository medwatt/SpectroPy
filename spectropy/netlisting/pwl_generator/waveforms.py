# imports<<<
from __future__ import annotations

from abc import ABC, abstractmethod
# >>>


def _append_delay(
    points: list[tuple[float, float]],
    last_time: float,
    last_value: float,
    delay: float,
) -> float:
    if delay > 0:
        last_time += delay
        points.append((last_time, last_value))
    return last_time


def _append_transition(
    points: list[tuple[float, float]],
    last_time: float,
    last_value: float,
    transition_time: float,
    delta: float,
) -> tuple[float, float]:
    if transition_time <= 0:
        raise ValueError("transition_time must be greater than zero.")
    last_time += transition_time
    last_value += delta
    points.append((last_time, last_value))
    return last_time, last_value


class WaveformSegment(ABC):
    """Abstract base class for waveform segments."""

    @abstractmethod
    def generate(
        self, last_time: float, last_value: float
    ) -> list[tuple[float, float]]:
        """Generate points for this segment."""


class DelaySegment(WaveformSegment):
    """Hold the current value for a fixed duration."""

    def __init__(self, duration: float):
        self.duration = duration

    def generate(
        self, last_time: float, last_value: float
    ) -> list[tuple[float, float]]:
        return [(last_time + self.duration, last_value)]


class StepSegment(WaveformSegment):
    """Ramp by delta over transition_time, then hold at the new level."""

    def __init__(self, duration: float, delta: float, transition_time: float):
        self.duration = duration
        self.delta = delta
        self.transition_time = transition_time

    def generate(
        self, last_time: float, last_value: float
    ) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        last_time, last_value = _append_transition(
            points, last_time, last_value, self.transition_time, self.delta
        )
        last_time += self.duration
        points.append((last_time, last_value))
        return points


class PulseSegment(WaveformSegment):
    """Rise by pulse_value, hold, then return to the previous level."""

    def __init__(
        self,
        duration: float,
        pulse_value: float,
        delay_before: float = 0.0,
        delay_after: float = 0.0,
        transition_time: float = 0.0,
        cycles: int = 1,
    ):
        self.duration = duration
        self.pulse_value = pulse_value
        self.delay_before = delay_before
        self.delay_after = delay_after
        self.transition_time = transition_time
        self.cycles = cycles

    def generate(
        self, last_time: float, last_value: float
    ) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for _ in range(self.cycles):
            last_time = _append_delay(points, last_time, last_value, self.delay_before)
            last_time, last_value = _append_transition(
                points, last_time, last_value, self.transition_time, self.pulse_value
            )
            last_time += self.duration
            points.append((last_time, last_value))
            last_time, last_value = _append_transition(
                points, last_time, last_value, self.transition_time, -self.pulse_value
            )
            last_time = _append_delay(points, last_time, last_value, self.delay_after)
        return points


class SquareSegment(WaveformSegment):
    """Alternate between start_value and end_value for the given duration."""

    def __init__(
        self,
        duration: float,
        start_value: float,
        end_value: float,
        delay_before: float = 0.0,
        delay_after: float = 0.0,
        transition_time: float = 0.0,
        cycles: int = 1,
    ):
        self.duration = duration
        self.start_value = start_value
        self.end_value = end_value
        self.delay_before = delay_before
        self.delay_after = delay_after
        self.transition_time = transition_time
        self.cycles = cycles

    def generate(
        self, last_time: float, last_value: float
    ) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        half_duration = self.duration / 2
        for _ in range(self.cycles):
            last_time = _append_delay(points, last_time, last_value, self.delay_before)
            last_time, last_value = _append_transition(
                points, last_time, last_value, self.transition_time, self.start_value
            )
            last_time += half_duration
            points.append((last_time, last_value))
            last_time, last_value = _append_transition(
                points,
                last_time,
                last_value,
                self.transition_time,
                self.end_value - self.start_value,
            )
            last_time += half_duration
            points.append((last_time, last_value))
            last_time, last_value = _append_transition(
                points, last_time, last_value, self.transition_time, -self.end_value
            )
            last_time = _append_delay(points, last_time, last_value, self.delay_after)
        return points


class TriangleSegment(WaveformSegment):
    """Ramp up to peak_value and then back down."""

    def __init__(
        self,
        duration: float,
        peak_value: float,
        delay_before: float = 0.0,
        delay_after: float = 0.0,
        cycles: int = 1,
    ):
        self.duration = duration
        self.peak_value = peak_value
        self.delay_before = delay_before
        self.delay_after = delay_after
        self.cycles = cycles

    def generate(
        self, last_time: float, last_value: float
    ) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        half_duration = self.duration / 2
        for _ in range(self.cycles):
            last_time = _append_delay(points, last_time, last_value, self.delay_before)
            last_time += half_duration
            last_value += self.peak_value
            points.append((last_time, last_value))
            last_time += half_duration
            last_value -= self.peak_value
            points.append((last_time, last_value))
            last_time = _append_delay(points, last_time, last_value, self.delay_after)
        return points


class SawtoothSegment(WaveformSegment):
    """Snap to start_value, ramp to end_value, then return to baseline."""

    def __init__(
        self,
        duration: float,
        start_value: float,
        end_value: float,
        delay_before: float = 0.0,
        delay_after: float = 0.0,
        transition_time: float = 0.0,
        cycles: int = 1,
    ):
        self.duration = duration
        self.start_value = start_value
        self.end_value = end_value
        self.delay_before = delay_before
        self.delay_after = delay_after
        self.transition_time = transition_time
        self.cycles = cycles

    def generate(
        self, last_time: float, last_value: float
    ) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for _ in range(self.cycles):
            last_time = _append_delay(points, last_time, last_value, self.delay_before)
            last_time, last_value = _append_transition(
                points, last_time, last_value, self.transition_time, self.start_value
            )
            last_time, last_value = _append_transition(
                points,
                last_time,
                last_value,
                self.duration,
                self.end_value - self.start_value,
            )
            last_time, last_value = _append_transition(
                points, last_time, last_value, self.transition_time, -self.end_value
            )
            last_time = _append_delay(points, last_time, last_value, self.delay_after)
        return points
