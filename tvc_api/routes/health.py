from ..context import AppContext


def live(_: AppContext) -> tuple[int, dict[str, object]]:
    return 200, {"status": "live"}


def ready(context: AppContext) -> tuple[int, dict[str, object]]:
    gpu = context.gpu_probe(context.settings.gpu_index)
    return 200, {
        "status": "ready",
        "queue": {"mode": "sequential", "max_concurrent_gpu_tasks": 1},
        "registry_models": len(context.registry.models),
        "gpu": {"available": gpu.available, "index": gpu.index,
                "total_vram_gb": round(gpu.total_vram_gb, 2),
                "free_vram_gb": round(gpu.free_vram_gb, 2), "reason": gpu.reason},
    }

