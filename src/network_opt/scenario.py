"""Operaciones what-if sobre los datos de la red.

======================================================================
PUNTO DE INYECCION #1 (parametros) -- aqui se conectara el LLM
======================================================================
Recomendacion de arquitectura: en vez de dejar que el LLM escriba Python
arbitrario, estas funciones se expondran como *herramientas* (tool use).
El LLM traduce "la planta de Santiago reduce su capacidad a la mitad y la
demanda del norte sube 20%" a una lista de llamadas estructuradas:

    [{"op": "scale_factory_capacity", "factory": "Planta Santiago", "factor": 0.5},
     {"op": "scale_demand", "factor": 1.2, "region": "norte"}]

y apply_operations() las ejecuta. Ventajas: es seguro (no hay exec), se
puede validar y auditar, y es reproducible (el JSON se guarda con el reporte).
Para cambios que no se pueden expresar como parametros, ver el punto de
inyeccion #2 en model.py.
"""

from __future__ import annotations

from .data import NetworkData


def scale_factory_capacity(data: NetworkData, factory: str, factor: float) -> None:
    _require(factory, data.factories, "planta")
    data.factories[factory]["capacity"] *= factor


def scale_depot_capacity(data: NetworkData, depot: str, factor: float) -> None:
    _require(depot, data.depots, "CD")
    data.depots[depot]["capacity"] *= factor


def scale_demand(
    data: NetworkData, factor: float, region: str | None = None, customer: str | None = None
) -> None:
    """Escala la demanda de un cliente, de una region, o de toda la red."""
    if customer is not None:
        _require(customer, data.customers, "cliente")
        targets = [customer]
    else:
        targets = [c for c, a in data.customers.items() if region is None or a["region"] == region]
        if not targets:
            raise ValueError(f"No hay clientes en la region '{region}'")
    for c in targets:
        data.customers[c]["demand"] *= factor


def scale_arc_costs(
    data: NetworkData, factor: float, origin: str | None = None, destination: str | None = None
) -> None:
    """Ej.: alza del diesel (todos los arcos) o un peaje nuevo (un arco especifico)."""
    hits = [
        arc for arc in data.arcs
        if (origin is None or arc[0] == origin) and (destination is None or arc[1] == destination)
    ]
    if not hits:
        raise ValueError(f"No hay arcos que coincidan con origen={origin}, destino={destination}")
    for arc in hits:
        data.arcs[arc] *= factor


def close_depot(data: NetworkData, depot: str) -> None:
    """Fuerza el cierre de un CD (huelga, incendio, fin de contrato)."""
    scale_depot_capacity(data, depot, 0.0)


# Registro de operaciones permitidas: es la "lista blanca" que vera el LLM.
OPERATIONS = {
    "scale_factory_capacity": scale_factory_capacity,
    "scale_depot_capacity": scale_depot_capacity,
    "scale_demand": scale_demand,
    "scale_arc_costs": scale_arc_costs,
    "close_depot": close_depot,
}


def apply_operations(base: NetworkData, operations: list[dict]) -> NetworkData:
    """Aplica una lista de operaciones sobre una COPIA del caso base."""
    data = base.copy()
    for op in operations:
        op = dict(op)
        name = op.pop("op")
        if name not in OPERATIONS:
            raise ValueError(f"Operacion desconocida '{name}'. Permitidas: {sorted(OPERATIONS)}")
        OPERATIONS[name](data, **op)
    data.validate()
    return data


def _require(name: str, nodes: dict, kind: str) -> None:
    if name not in nodes:
        raise ValueError(f"{kind} '{name}' no existe. Opciones: {sorted(nodes)}")
