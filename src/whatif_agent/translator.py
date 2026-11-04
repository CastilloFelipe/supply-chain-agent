"""Traductor: pregunta en lenguaje natural -> lista de operaciones what-if.

Flujo (loop manual de tool use):
  1. Claude recibe la descripcion de la red y la pregunta.
  2. Invoca herramientas (una por cambio). Cada llamada se aplica sobre una
     copia de los datos; si falla (p.ej. factor negativo), el error vuelve a
     Claude como tool_result con is_error=True para que corrija.
  3. Termina llamando finish_scenario con su interpretacion y supuestos.

El resultado es un JSON auditable: se guarda junto al reporte y se puede
re-ejecutar sin volver a llamar al LLM.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import anthropic

from network_opt.data import NetworkData
from network_opt.scenario import apply_operations

from .tools import FINISH_TOOL, build_tools, tool_call_to_operation

MODEL = "claude-opus-5-5"
MAX_TURNS = 6

SYSTEM_PROMPT = """Eres el traductor de un simulador what-if de una red logistica.
Tu trabajo es convertir la pregunta de negocio del usuario en cambios sobre los
parametros del modelo de optimizacion, usando exclusivamente las herramientas.

Reglas:
- Una llamada por cada cambio. Todos los factores son multiplicativos sobre el
  caso base ("a la mitad" = 0.5, "sube 20%" = 1.2, "baja 15%" = 0.85).
- No resuelvas el problema ni estimes resultados: el optimizador lo hara.
- Si un termino es ambiguo (p.ej. "la fabrica de Santiago" cuando hay una planta
  y un CD en Santiago), elige la lectura mas razonable y registrala en assumptions.
- Si algo no se puede expresar con las herramientas, no lo aproximes: explicalo
  en `unsupported`.
- Termina siempre con finish_scenario."""


class TranslationError(RuntimeError):
    pass


@dataclass
class TranslatedScenario:
    question: str
    operations: list[dict]
    interpretation: str = ""
    assumptions: list[str] = field(default_factory=list)
    unsupported: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def describe_network(data: NetworkData) -> str:
    """Contexto estable de la red (va en el system prompt -> cacheable)."""
    lines = ["Red actual:", "Plantas:"]
    lines += [f"- {n} (region {a['region']}, capacidad {a['capacity']})" for n, a in data.factories.items()]
    lines.append("Centros de distribucion:")
    lines += [f"- {n} (region {a['region']}, capacidad {a['capacity']})" for n, a in data.depots.items()]
    lines.append("Clientes:")
    lines += [f"- {n} (region {a['region']}, demanda {a['demand']})" for n, a in data.customers.items()]
    return "\n".join(lines)


def translate(
    question: str,
    data: NetworkData,
    client: anthropic.Anthropic | None = None,
    model: str = MODEL,
) -> TranslatedScenario:
    client = client or anthropic.Anthropic()
    tools = build_tools(data)
    system = [{
        "type": "text",
        "text": f"{SYSTEM_PROMPT}\n\n{describe_network(data)}",
        "cache_control": {"type": "ephemeral"},
    }]
    messages: list[dict] = [{"role": "user", "content": question}]
    operations: list[dict] = []

    for _ in range(MAX_TURNS):
        response = client.beta.messages.create(
            model=model,
            max_tokens=16000,
            system=system,
            tools=tools,
            tool_choice={"type": "auto"},
            output_config={"effort": "medium"},
            # Si un clasificador de seguridad rechaza la solicitud, el servidor
            # la reintenta en el modelo de respaldo recomendado.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=messages,
        )

        if response.stop_reason == "refusal":
            raise TranslationError("El modelo rechazo la solicitud.")
        if response.stop_reason == "max_tokens":
            raise TranslationError("Respuesta truncada (max_tokens).")

        # Append-only: se devuelve el contenido completo (incluye bloques de thinking).
        messages.append({"role": "assistant", "content": response.content})

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            raise TranslationError(
                "El modelo termino sin llamar finish_scenario: "
                + " ".join(b.text for b in response.content if b.type == "text")
            )

        results = []
        finish_args = None
        for block in tool_uses:
            if block.name == FINISH_TOOL:
                finish_args = block.input
                results.append(_result(block.id, "ok"))
                continue
            op = tool_call_to_operation(block.name, block.input)
            try:
                apply_operations(data, [*operations, op])  # valida contra la copia acumulada
            except (ValueError, TypeError) as e:
                results.append(_result(block.id, f"Error: {e}", is_error=True))
                continue
            operations.append(op)
            results.append(_result(block.id, f"Aplicado: {json.dumps(op, ensure_ascii=False)}"))

        if finish_args is not None and not any(r.get("is_error") for r in results):
            return TranslatedScenario(
                question=question,
                operations=operations,
                interpretation=finish_args["interpretation"],
                assumptions=finish_args["assumptions"],
                unsupported=finish_args["unsupported"],
            )
        messages.append({"role": "user", "content": results})

    raise TranslationError(f"No se completo la traduccion en {MAX_TURNS} turnos.")


def _result(tool_use_id: str, content: str, is_error: bool = False) -> dict:
    r = {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}
    if is_error:
        r["is_error"] = True
    return r
