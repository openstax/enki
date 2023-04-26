import asyncio


class AsyncJobQueue:
    def __init__(self, worker_count, qsize=None):
        self.worker_count = worker_count
        self.queue = (asyncio.Queue(qsize) if qsize is not None
                      else asyncio.Queue())
        self.workers = []
        self.errors = []

    async def __aenter__(self):
        async def worker(queue):
            while True:
                job = await queue.get()
                try:
                    await job
                except Exception as e:  # pragma: no cover
                    # Append errors to the list
                    self.errors.append(e)
                queue.task_done()
        self.workers = [asyncio.create_task(worker(self.queue))
                        for _ in range(self.worker_count)]
        return self.queue

    async def __aexit__(self, *_):
        await self.queue.join()
        for worker in self.workers:
            worker.cancel()
