"""Definicion de herramientas (tool use) que Claude puede invocar.

Cada herramienta corresponde 1:1 a una operacion de network_opt.scenario.
Los nombres de plantas, CDs, clientes y regiones se inyectan como `enum`
desde los datos reales, y `strict: true` obliga a que los argumentos
respeten el esquema: Claude no puede inventar "Planta Valdivia" si no existe.
"""

from __future__ import annotations

from network_opt.data import NetworkData

ALL = "*"  # comodin para "todos" en enums (se traduce a None)
FINISH_TOOL = "finish_scenario"


def _factor(desc: str) -> dict:
    return {
        "type": "number",
        "description": f"Factor multiplicativo. {desc} Ej.: -50% -> 0.5, +20% -> 1.2, duplicar -> 2.0.",
    }


def _tool(name: str, description: str, properties: dict) -> dict:
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
    }


def build_tools(data: NetworkData) -> list[dict]:
    factories = sorted(data.factories)
    depots = sorted(data.depots)
    customers = sorted(data.customers)
    regions = sorted({a["region"] for a in data.customers.values()})
    origins = sorted({i for i, _ in data.arcs})
    destinations = sorted({j for _, j in data.arcs})

    return [
        _tool(
            "scale_factory_capacity",
            "Multiplica la capacidad de produccion de una planta.",
            {"factory": {"type": "string", "enum": factories}, "factor": _factor("Capacidad nueva / actual.")},
        ),
        _tool(
            "scale_depot_capacity",
            "Multiplica la capacidad de throughput de un centro de distribucion (CD).",
            {"depot": {"type": "string", "enum": depots}, "factor": _factor("Capacidad nueva / actual.")},
        ),
        _tool(
            "close_depot",
            "Cierra un CD por completo (capacidad 0): huelga, siniestro, fin de contrato.",
            {"depot": {"type": "string", "enum": depots}},
        ),
        _tool(
            "scale_demand",
            "Multiplica la demanda de todos los clientes de una region, o de toda la red con '*'.",
            {"region": {"type": "string", "enum": [ALL, *regions]}, "factor": _factor("Demanda nueva / actual.")},
        ),
        _tool(
            "scale_customer_demand",
            "Multiplica la demanda de un cliente especifico.",
            {"customer": {"type": "string", "enum": customers}, "factor": _factor("Demanda nueva / actual.")},
        ),
        _tool(
            "scale_arc_costs",
            "Multiplica costos de transporte. Use '*' en origen y/o destino para abarcar todos "
            "(ej. alza del diesel: origin='*', destination='*').",
            {
                "origin": {"type": "string", "enum": [ALL, *origins]},
                "destination": {"type": "string", "enum": [ALL, *destinations]},
                "factor": _factor("Costo nuevo / actual."),
            },
        ),
        _tool(
            "scale_depot_fixed_cost",
            "Multiplica el costo fijo de operar un CD (arriendo, personal), o de todos con '*'.",
            {"depot": {"type": "string", "enum": [ALL, *depots]}, "factor": _factor("Costo nuevo / actual.")},
        ),
        _tool(
            "set_max_open_depots",
            "Limita cuantos CDs pueden operar a la vez (politica de consolidacion).",
            {"n": {"type": "integer", "description": f"Maximo de CDs abiertos (hoy existen {len(depots)})."}},
        ),
        _tool(
            "force_open_depot",
            "Obliga a mantener un CD operando (p.ej. contrato vigente), aunque no convenga.",
            {"depot": {"type": "string", "enum": depots}},
        ),
        _tool(
            "block_route",
            "Prohibe rutas de transporte (corte de carretera, puerto cerrado). Use '*' en origen o "
            "destino para bloquear todas las rutas que salen de / llegan a un nodo.",
            {
                "origin": {"type": "string", "enum": [ALL, *origins]},
                "destination": {"type": "string", "enum": [ALL, *destinations]},
            },
        ),
        _tool(
            FINISH_TOOL,
            "Llamar UNA vez, al final, cuando todas las operaciones del escenario ya fueron aplicadas.",
            {
                "interpretation": {
                    "type": "string",
                    "description": "Una frase: como se interpreto la pregunta en terminos del modelo.",
                },
                "assumptions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Supuestos hechos por ambiguedad (lista vacia si no hubo).",
                },
                "unsupported": {
                    "type": "string",
                    "description": "Parte de la pregunta que NO se pudo expresar con las herramientas "
                                   "(cadena vacia si todo se pudo expresar).",
                },
            },
        ),
    ]


def tool_call_to_operation(name: str, args: dict) -> dict:
    """Convierte una llamada de herramienta al formato de scenario.apply_operations."""
    if name == "scale_demand":
        region = None if args["region"] == ALL else args["region"]
        return {"op": "scale_demand", "factor": args["factor"], "region": region}
    if name == "scale_customer_demand":
        return {"op": "scale_demand", "factor": args["factor"], "customer": args["customer"]}
    if name == "scale_arc_costs":
        return {
            "op": "scale_arc_costs",
            "factor": args["factor"],
            "origin": None if args["origin"] == ALL else args["origin"],
            "destination": None if args["destination"] == ALL else args["destination"],
        }
    if name == "scale_depot_fixed_cost":
        depot = None if args["depot"] == ALL else args["depot"]
        return {"op": name, "factor": args["factor"], "depot": depot}
    if name == "block_route":
        return {
            "op": name,
            "origin": None if args["origin"] == ALL else args["origin"],
            "destination": None if args["destination"] == ALL else args["destination"],
        }
    return {"op": name, **args}
