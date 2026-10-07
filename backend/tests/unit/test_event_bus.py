from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import uuid4

from backend.app.events.bus import EventBus
from backend.app.events.types import FaceObserved, ObservationKind


def make_event() -> FaceObserved:
    return FaceObserved(
        camera_id=uuid4(),
        kind=ObservationKind.UNKNOWN,
        occurred_at=datetime.now(timezone.utc),
    )


def test_publish_delivers_to_all_subscribers() -> None:
    bus = EventBus(max_queue_size=10)
    seen_a: list[FaceObserved] = []
    seen_b: list[FaceObserved] = []
    bus.subscribe(FaceObserved, seen_a.append)
    bus.subscribe(FaceObserved, seen_b.append)
    bus.start()
    event = make_event()
    assert bus.publish(event) is True
    bus.stop(drain=True)
    assert seen_a == [event]
    assert seen_b == [event]


def test_failing_handler_does_not_stop_other_handlers() -> None:
    bus = EventBus(max_queue_size=10)
    seen: list[FaceObserved] = []

    def broken(_: FaceObserved) -> None:
        raise RuntimeError("boom")

    bus.subscribe(FaceObserved, broken)
    bus.subscribe(FaceObserved, seen.append)
    bus.start()
    event = make_event()
    assert bus.publish(event) is True
    bus.stop(drain=True)
    assert seen == [event]


def test_queue_overflow_drops_oldest_and_counts() -> None:
    bus = EventBus(max_queue_size=1)
    bus._accepting = True
    first = make_event()
    second = make_event()
    assert bus.publish(first) is True
    assert bus.publish(second) is True
    assert bus.overflow_count == 1
    assert bus._queue.get_nowait() is second
    bus._queue.task_done()


def test_shutdown_drains_queue() -> None:
    bus = EventBus(max_queue_size=10)
    seen: list[FaceObserved] = []

    def slow_handler(event: FaceObserved) -> None:
        time.sleep(0.02)
        seen.append(event)

    bus.subscribe(FaceObserved, slow_handler)
    bus.start()
    events = [make_event() for _ in range(4)]
    for event in events:
        assert bus.publish(event) is True
    bus.stop(drain=True, timeout=2.0)
    assert seen == events
