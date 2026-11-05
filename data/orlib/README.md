# Instancias OR-Library

Instancias *Capacitated Warehouse Location* de la OR-Library de J.E. Beasley,
convertidas al formato de este proyecto con `scripts/import_orlib.py`.

- Fuente: http://people.brunel.ac.uk/~mastjjb/jeb/orlib/capinfo.html
- Referencia: J.E. Beasley, "OR-Library: distributing test problems by electronic
  mail", *Journal of the Operational Research Society* 41(11) (1990), 1069–1072.
- Los óptimos publicados (`capopt.txt`) quedan en `meta.known_optimum` de cada JSON y
  `tests/test_orlib_benchmark.py` los verifica.

Los datos pertenecen a sus autores. Aquí se redistribuyen convertidos, solo con
fines de investigación y validación, citando la fuente.
