# The claim under review: "this is thread-safe because the counter is a local variable."
import threading


class RequestCounter:
    _shared = {"count": 0}

    def bump(self):
        count = self._shared["count"]     # local name, shared object
        count += 1
        self._shared["count"] = count
        return count


def run(n_threads=8, per_thread=1000):
    c = RequestCounter()
    threads = [threading.Thread(target=lambda: [c.bump() for _ in range(per_thread)])
               for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return c._shared["count"]           # expected n_threads * per_thread; is not
