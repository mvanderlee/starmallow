import typing
from logging import getLogger

from starlette.background import BackgroundTask as StarletteBackgroundTask
from starlette.background import BackgroundTasks as StarletteBackgroundTasks
from starlette.background import P
from starlette.concurrency import run_in_threadpool

logger = getLogger(__name__)


class BackgroundTask(StarletteBackgroundTask):

    async def __call__(self) -> None:
        try:
            if self.is_async:
                await self.func(*self.args, **self.kwargs)
            else:
                await run_in_threadpool(self.func, *self.args, **self.kwargs)
        except BaseException as e:
            logger.exception(f'Background Task {self.func.__module__}.{self.func.__name__} failed: {e}')


class BackgroundTasks(StarletteBackgroundTasks):
    def add_task(
        self, func: typing.Callable[P, typing.Any], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        task = BackgroundTask(func, *args, **kwargs)
        self.tasks.append(task)
