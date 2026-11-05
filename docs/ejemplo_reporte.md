# Reporte what-if

**Pregunta:** ¿Qué pasa si cerramos el CD de La Serena y el diésel sube 15%?

## Resumen

Cerrar el CD La Serena con un diésel 15% más caro **no es conveniente**. El costo total
sube de USD 28.630 a USD 39.842 (+39,2%) y el nivel de servicio cae de 100% a 90,9%. Quedan
20 pallets/semana sin atender en el extremo norte. Además, el cierre no ahorra costo fijo:
obliga a abrir el CD Santiago y el costo fijo de la red sube de USD 22.000 a USD 24.000 (+9,1%).

## Qué cambia en la red

- **Se reorganizan los CDs.** Cierra La Serena y abre el CD Santiago, que pasa a abastecer
  al cliente La Serena (20 pallets/semana). Antofagasta y Temuco siguen operando.
- **Toda la carga del norte pasa por Antofagasta.** Calama, que antes se atendía desde La
  Serena, ahora sale de Antofagasta (25 pallets/semana). La Planta Santiago aumenta sus
  envíos a Antofagasta de 50 a 70 pallets/semana. Los 15 pallets que la Planta Concepción
  enviaba al norte desaparecen.
- **El cuello de botella se traslada.** En el caso base la restricción era la Planta
  Santiago (100%). En el escenario es el **CD Antofagasta, al 100% de su capacidad**,
  mientras la Planta Concepción queda al 55%. Sobra producción, pero no hay por dónde
  llevarla al norte.
- **Quiebres de stock:** Arica no recibe nada (15 de 15 pallets) e Iquique recibe 15 de
  20 (faltan 5).

## Riesgos y lectura correcta de las cifras

- **El costo de transporte baja 11,9% aunque el diésel sube 15%.** No es una eficiencia:
  baja porque se dejan de despachar 20 pallets a los destinos más lejanos (Arica e
  Iquique). Por unidad servida el transporte solo baja 3,1%. El costo operacional por
  unidad servida, en cambio, sube 14,7% (de USD 130,14 a USD 149,21).
- **Los USD 10.000 de penalización no son un gasto contable.** Son la forma en que el
  modelo valora la demanda perdida. En la práctica significan ventas perdidas o quiebres
  de stock en Arica e Iquique, y su impacto real depende del margen y de la relación con
  esos clientes.
- **Supuesto:** el alza del diésel se traslada completa (15%) a todas las rutas. Si parte
  del alza se negocia con los transportistas, el impacto en transporte sería menor, pero
  el problema de capacidad en el norte no cambia.

## Recomendaciones

1. **No cerrar La Serena** mientras el CD Antofagasta sea la única puerta de entrada al
   norte. El ahorro esperado no aparece, porque hay que abrir el CD Santiago.
2. Si el cierre es inevitable (fin de contrato, por ejemplo), **ampliar antes la capacidad
   del CD Antofagasta** en al menos 20 pallets/semana. Conviene simular esa ampliación
   como siguiente escenario.
3. **Evaluar despachos directos desde las plantas a clientes del norte**, sin pasar por el
   CD Antofagasta, para usar la capacidad ociosa de la Planta Concepción (55% de
   utilización). Hoy esa ruta no existe en la red, así que habría que agregarla a los datos.
4. Ante el alza del diésel, **priorizar la renegociación de tarifas en los tramos largos**
   (Santiago y Concepción hacia Antofagasta), que concentran el volumen del norte.

## Cifras (calculadas por el optimizador)

| Indicador (USD) | Base | Escenario | Variación |
|---|---:|---:|---:|
| Costo total | 28,630 | 39,842 | +39.2% |
| Transporte | 6,630 | 5,842 | -11.9% |
| Costo fijo CDs | 22,000 | 24,000 | +9.1% |
| Penalización demanda no servida | 0 | 10,000 | nuevo |
| Demanda servida (pallets/semana) | 220.0 | 200.0 | -9.1% |
| Demanda no servida (pallets/semana) | 0.0 | 20.0 | nuevo |
| Nivel de servicio | 100.0% | 90.9% | -9.1 pp |
| Transporte por unidad servida | 30.14 | 29.21 | -3.1% |
| Costo operacional por unidad servida | 130.14 | 149.21 | +14.7% |
