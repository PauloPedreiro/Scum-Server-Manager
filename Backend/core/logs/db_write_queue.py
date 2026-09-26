import queue
import threading
from typing import Any, Callable, Optional, Tuple


class _Job:
    __slots__ = ("fn", "args", "kwargs", "done", "result", "error")

    def __init__(
        self,
        fn: Callable[..., Any],
        args: Tuple[Any, ...],
        kwargs: dict,
    ):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.done = threading.Event()
        self.result: Any = None
        self.error: Optional[BaseException] = None


class DBWriteQueue:
    def __init__(self):
        self._queue: "queue.Queue[_Job]" = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        self._queue.put(_Job(lambda: None, (), {}))
        if self._thread:
            self._thread.join(timeout=timeout)

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        job = _Job(fn, args, kwargs)
        self._queue.put(job)
        job.done.wait()
        if job.error:
            raise job.error
        return job.result

    def _run(self) -> None:
        while not self._stop_event.is_set():
            job = self._queue.get()
            try:
                job.result = job.fn(*job.args, **job.kwargs)
            except BaseException as e:
                job.error = e
            finally:
                job.done.set()


class QueuedDatabaseManager:
    def __init__(self, inner: Any, write_queue: DBWriteQueue):
        self._inner = inner
        self._queue = write_queue

    @property
    def db_path(self) -> str:
        return self._inner.db_path

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._inner, name)
        if not callable(attr):
            return attr

        if name.startswith("_"):
            return attr

        if name.startswith("get_"):
            return attr
        if name.startswith("fetch_"):
            return attr
        if name.startswith("list_"):
            return attr

        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            return self._queue.submit(attr, *args, **kwargs)

        return _wrapped
