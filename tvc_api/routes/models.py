from ..context import AppContext
from ..errors import UNAVAILABLE_GPU


def model_payload(context: AppContext, model_id: str) -> dict[str, object]:
    spec = context.registry.get(model_id)
    adapter = context.adapters.get(model_id)
    readiness = adapter.readiness() if adapter else None
    value = spec.public()
    value["ready"] = bool(readiness and readiness.ready)
    value["checks"] = readiness.checks if readiness else {"adapter": False}
    return value


def list_models(context: AppContext) -> tuple[int, dict[str, object]]:
    return 200, {"models": [model_payload(context, spec.id) for spec in context.registry.list()]}


def get_model(context: AppContext, model_id: str) -> tuple[int, dict[str, object]]:
    return 200, model_payload(context, model_id)

def health_model(context: AppContext, model_id: str) -> tuple[int, dict[str, object]]:
    payload = model_payload(context, model_id)
    spec = context.registry.get(model_id)
    gpu = context.gpu_probe(context.settings.gpu_index)
    if not gpu.sufficient(float(spec.data["min_vram_gb"])):
        payload["status"] = UNAVAILABLE_GPU
    elif payload["ready"]:
        payload["status"] = "ready"
    else:
        payload["status"] = "installed_not_ready"
    return 200, payload

