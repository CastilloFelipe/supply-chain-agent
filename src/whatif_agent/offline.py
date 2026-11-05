"""Escenarios traducidos fuera del programa (sin API key).

Permite que la traduccion la haga Claude Code (o una persona) escribiendo un
archivo JSON con las mismas llamadas de herramienta que haria el traductor:

    {
      "question": "...",
      "interpretation": "...",
      "assumptions": [],
      "unsupported": "",
      "calls": [{"name": "scale_demand", "input": {"region": "norte", "factor": 1.2}}]
    }

Las llamadas se validan contra el mismo esquema (enums incluidos) que recibe
Claude por la API, asi ambos caminos son equivalentes.
"""

from __future__ import annotations

import json
from pathlib import Path

from network_opt.data import NetworkData
from network_opt.scenario import apply_operations

from .tools import FINISH_TOOL, build_tools, tool_call_to_operation
from .translator import TranslatedScenario

TYPES = {"string": str, "number": (int, float), "integer": int, "array": list}


def catalog(data: NetworkData) -> list[dict]:
    """Herramientas disponibles (sin la de cierre), para mostrarselas a quien traduce."""
    return [
        {"name": t["name"], "description": t["description"], "input": t["input_schema"]["properties"]}
        for t in build_tools(data) if t["name"] != FINISH_TOOL
    ]


def validate_call(call: dict, schemas: dict[str, dict]) -> None:
    name, args = call.get("name"), call.get("input")
    if name not in schemas:
        raise ValueError(f"Herramienta desconocida '{name}'. Opciones: {sorted(schemas)}")
    if not isinstance(args, dict):
        raise ValueError(f"{name}: 'input' debe ser un objeto")
    props = schemas[name]["input_schema"]["properties"]
    if set(args) != set(props):
        raise ValueError(f"{name}: se esperaban los campos {sorted(props)}, llegaron {sorted(args)}")
    for key, spec in props.items():
        value = args[key]
        expected = TYPES[spec["type"]]
        if isinstance(value, bool) or not isinstance(value, expected):
            raise ValueError(f"{name}.{key}: se esperaba {spec['type']}, llego {value!r}")
        if "enum" in spec and value not in spec["enum"]:
            raise ValueError(f"{name}.{key}: '{value}' no existe. Opciones: {spec['enum']}")


def load_scenario(path: str | Path, data: NetworkData) -> TranslatedScenario:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    schemas = {t["name"]: t for t in build_tools(data) if t["name"] != FINISH_TOOL}
    operations = []
    for call in raw.get("calls", []):
        validate_call(call, schemas)
        operations.append(tool_call_to_operation(call["name"], call["input"]))
    apply_operations(data, operations)  # valida el escenario completo (contradicciones, etc.)
    return TranslatedScenario(
        question=raw.get("question", ""),
        operations=operations,
        interpretation=raw.get("interpretation", ""),
        assumptions=raw.get("assumptions", []),
        unsupported=raw.get("unsupported", ""),
    )
