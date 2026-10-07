"""Small in-process, non-blocking event bus used by the application."""
from __future__ import annotations

import logging
import queue
import threading
from collections import defaultdict
from typing import Any, Callable, DefaultDict, Type

logger = logging.getLogger(__name__)
EventHandler = Callable[[Any], None]


class EventBus:
    """Threaded FIFO event bus with isolated handlers and bounded memory."""

    def __init__(self, max_queue_size: int = 1000) -> None:
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be >= 1")
        self.max_queue_size = max_queue_size
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=max_queue_size)
        self._subscribers: DefaultDict[Type[Any], list[EventHandler]] = defaultdict(list)
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._started = False
        self._accepting = False
        self._overflow_count = 0

    @property
    def overflow_count(self) -> int:
        with self._lock:
            return self._overflow_count

    def subscribe(self, event_type: Type[Any], handler: EventHandler) -> None:
        with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: Type[Any], handler: EventHandler) -> None:
        with self._lock:
            handlers = self._subscribers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._accepting = True
            self._thread = threading.Thread(
                target=self._dispatch_loop,
                name="event-bus-dispatcher",
                daemon=True,
            )
            self._thread.start()

    def publish(self, event: Any) -> bool:
        """Enqueue without blocking; on overflow drop the oldest event."""
        with self._lock:
            if not self._accepting:
                return False
            try:
                self._queue.put_nowait(event)
                return True
            except queue.Full:
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except queue.Empty:
                    pass
                self._overflow_count += 1
                try:
                    self._queue.put_nowait(event)
                    return True
                except queue.Full:
                    return False

    def stop(self, *, drain: bool = True, timeout: float = 5.0) -> None:
        with self._lock:
            if not self._started:
                return
            self._accepting = False
            thread = self._thread

        if drain:
            done = threading.Event()

            def waiter() -> None:
                self._queue.join()
                done.set()

            threading.Thread(target=waiter, daemon=True).start()
            done.wait(timeout=max(timeout, 0.0))
        else:
            while True:
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except queue.Empty:
                    break

        try:
            self._queue.put_nowait(_STOP)
        except queue.Full:
            try:
                self._queue.put(_STOP, timeout=max(timeout, 0.0))
            except queue.Full:
                pass

        if thread is not None:
            thread.join(timeout=max(timeout, 0.0))

        with self._lock:
            self._started = False
            self._accepting = False
            self._thread = None

    def _dispatch_loop(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is _STOP:
                    return
                self._dispatch_one(item)
            finally:
                self._queue.task_done()

    def _dispatch_one(self, event: Any) -> None:
        with self._lock:
            handlers = list(self._subscribers.get(type(event), ()))

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Event handler failed for event_type=%s handler=%r",
                    type(event).__name__,
                    handler,
                )


class _StopSentinel:
    pass


_STOP = _StopSentinel()
event_bus = EventBus()
