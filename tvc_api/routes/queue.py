from ..context import AppContext


def get_queue(context: AppContext) -> tuple[int, dict[str, object]]:
    return 200, context.queue.snapshot()

