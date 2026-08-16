#!/usr/bin/env python3
"""Validate checked-in ComfyUI workflow contracts without loading models."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tvc_api.workflows import WorkflowRegistry


result = WorkflowRegistry(Path(__file__).resolve().parents[1]).validate_all()
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["ready"] else 1)
