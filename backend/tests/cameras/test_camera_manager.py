"""
CameraManager worker-control unit tests.

No real cameras, threads that open sources, or database access: worker threads
are replaced by fakes and _set_status/_get_camera are patched.
"""
import threading
import uuid
from unittest.mock import MagicMock

import pytest

from backend.app.cameras.manager import CameraManager


class FakeWorker:
    def __init__(self):
        self.join_timeout = None
        self.alive = True

    def is_alive(self):
        return self.alive

    def join(self, timeout=None):
        self.join_timeout = timeout
        self.alive = False


@pytest.fixture
def mgr(monkeypatch):
    manager = CameraManager()
    monkeypatch.setattr(manager, "_set_status", MagicMock(name="_set_status"))
    return manager


def register(manager, camera_id):
    event, worker = threading.Event(), FakeWorker()
    manager._stop_events[camera_id] = event
    manager._workers[camera_id] = worker
    return event, worker


def test_start_camera_is_noop_when_manager_not_running(mgr, monkeypatch):
    thread_cls = MagicMock()
    monkeypatch.setattr(threading, "Thread", thread_cls)

    assert mgr.start_camera(uuid.uuid4()) is False
    thread_cls.assert_not_called()
    assert mgr._workers == {}


def test_start_camera_registers_worker_when_running(mgr, monkeypatch):
    thread_cls = MagicMock()
    monkeypatch.setattr(threading, "Thread", thread_cls)
    mgr._running = True
    camera_id = uuid.uuid4()

    assert mgr.start_camera(camera_id) is True
    thread_cls.return_value.start.assert_called_once()
    assert camera_id in mgr._workers and camera_id in mgr._stop_events


def test_stop_camera_unknown_is_noop(mgr):
    assert mgr.stop_camera(uuid.uuid4()) is False
    mgr._set_status.assert_not_called()


def test_stop_camera_signals_joins_unregisters_and_marks_disabled(mgr):
    camera_id = uuid.uuid4()
    event, worker = register(mgr, camera_id)

    assert mgr.stop_camera(camera_id) is True
    assert event.is_set()
    assert worker.join_timeout == 3
    assert camera_id not in mgr._workers and camera_id not in mgr._stop_events
    mgr._set_status.assert_called_once_with(camera_id, "DISABLED", heartbeat=False)


def test_stop_camera_without_mark_disabled_keeps_status(mgr):
    camera_id = uuid.uuid4()
    register(mgr, camera_id)

    assert mgr.stop_camera(camera_id, mark_disabled=False) is True
    mgr._set_status.assert_not_called()


def test_restart_camera_stops_without_disabling_then_starts(mgr, monkeypatch):
    calls = []
    monkeypatch.setattr(mgr, "stop_camera", lambda cid, mark_disabled=True: calls.append(("stop", cid, mark_disabled)))
    monkeypatch.setattr(mgr, "start_camera", lambda cid: calls.append(("start", cid)) or True)
    camera_id = uuid.uuid4()

    assert mgr.restart_camera(camera_id) is True
    assert calls == [("stop", camera_id, False), ("start", camera_id)]


def test_finished_old_worker_does_not_unregister_replacement(mgr, monkeypatch):
    """An old worker exiting after a restart must not remove the new worker's entries."""
    camera_id = uuid.uuid4()
    old_event = threading.Event()
    new_event, new_worker = register(mgr, camera_id)  # replacement already registered
    monkeypatch.setattr(mgr, "_get_camera", lambda cid: None)  # old loop exits immediately

    mgr._worker_loop(camera_id, old_event)

    assert mgr._stop_events[camera_id] is new_event
    assert mgr._workers[camera_id] is new_worker


def test_finished_worker_unregisters_itself(mgr, monkeypatch):
    camera_id = uuid.uuid4()
    event, _ = register(mgr, camera_id)
    monkeypatch.setattr(mgr, "_get_camera", lambda cid: None)

    mgr._worker_loop(camera_id, event)

    assert camera_id not in mgr._workers and camera_id not in mgr._stop_events
