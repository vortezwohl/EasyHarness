"""Private signal types for the streaming event boundary.

This module isolates Strands, tool, and compression source formats. The runtime
projector consumes RuntimeSignal values and assigns public event order and
phase identity.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from .types import EventKind, EventOperation

SignalSource = Literal["strands", "tool", "compress", "runtime"]


@dataclass(frozen=True, slots=True)
class RuntimeSignal:
    """Describe one internal streaming fact before public projection.

    Args:
        source: Internal source that produced the signal.
        kind: Target lifecycle phase category.
        operation: Lifecycle operation.
        phase_key: Stable private key that relates one internal phase.
        delta: New text used only by delta operations.
        error: Error detail used only by failed operations.
        started_at: Upstream phase start timestamp.
        duration_ms: Upstream or runtime terminal duration.
        data: Auxiliary data exposed through the public data field.
    """

    source: SignalSource
    kind: EventKind
    operation: EventOperation
    phase_key: str | None = None
    delta: str | None = None
    error: str | None = None
    started_at: str | None = None
    duration_ms: int | None = None
    data: Mapping[str, object] | None = None
