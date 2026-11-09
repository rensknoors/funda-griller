"""Which step each running capture is at, so the view can show progress while the capture's own
request is still open. Held in memory: a restart ends every running capture anyway."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from threading import Lock

# The steps of a capture, in the order they run.
CAPTURE_STEPS = ("listing", "photos", "sources", "observations", "brochure")


class CaptureProgress:
    def __init__(self) -> None:
        self._lock = Lock()
        self._running: dict[str, dict] = {}

    @contextmanager
    def track(self, funda_id: str, url: str) -> Iterator[Callable[[str], None]]:
        """Report the capture of `funda_id` as running until the block ends; the yielded callback
        moves it to the next step."""

        def step(name: str) -> None:
            with self._lock:
                self._running[funda_id] = {"funda_id": funda_id, "url": url, "step": name}

        step(CAPTURE_STEPS[0])
        try:
            yield step
        finally:
            with self._lock:
                self._running.pop(funda_id, None)

    def running(self) -> list[dict]:
        with self._lock:
            return [dict(capture) for capture in self._running.values()]
