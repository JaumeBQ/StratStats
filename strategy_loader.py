"""
strategy_loader.py
==================
Carga de estrategias de Backtrader a partir de un fichero ``.py`` subido por
el usuario.

Localiza las clases que heredan de ``bt.Strategy`` y devuelve la clase real
para poder ejecutarla.

.. warning::
    Ejecutar código de terceros es intrínsecamente peligroso. Esta aplicación
    está pensada para un entorno de confianza (uso académico / personal). Como
    salvaguarda *ligera* se ofrece :func:`scan_for_risky_imports`, que avisa de
    importaciones potencialmente peligrosas (``os``, ``sys``, ``subprocess``,
    ``socket``...). No constituye un aislamiento real; un *sandbox* completo
    queda propuesto como trabajo futuro.
"""

from __future__ import annotations

import ast

#: Módulos cuya importación se considera sospechosa en una estrategia.
RISKY_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "requests",
    "urllib", "pickle", "ctypes", "multiprocessing", "threading",
}


class StrategyLoadError(Exception):
    """Error controlado al cargar o analizar el fichero de estrategias."""


def _inherits_strategy(node: ast.ClassDef) -> bool:
    """Comprueba si una clase hereda de algo llamado ``Strategy``."""
    for base in node.bases:
        # bt.Strategy  -> Attribute(attr="Strategy")
        if isinstance(base, ast.Attribute) and base.attr == "Strategy":
            return True
        # from backtrader import Strategy ; class X(Strategy)
        if isinstance(base, ast.Name) and base.id == "Strategy":
            return True
    return False


def scan_for_risky_imports(code: str) -> list[str]:
    """
    Devuelve la lista de módulos potencialmente peligrosos importados en el
    código. Lista vacía si no se detecta ninguno.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in RISKY_MODULES:
                    found.add(root)
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in RISKY_MODULES:
                found.add(root)
    return sorted(found)


def find_strategies_in_code(code: str) -> dict[str, type]:
    """
    Localiza y devuelve las clases de estrategia definidas en *code*.

    Returns
    -------
    dict[str, type]
        Diccionario ``{nombre_clase: clase}`` con las subclases de
        ``bt.Strategy`` encontradas.

    Raises
    ------
    StrategyLoadError
        Si el código tiene errores de sintaxis o no puede ejecutarse.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise StrategyLoadError(f"El fichero tiene un error de sintaxis: {exc}") from exc

    names = [n.name for n in tree.body
             if isinstance(n, ast.ClassDef) and _inherits_strategy(n)]
    if not names:
        raise StrategyLoadError(
            "No se encontró ninguna clase que herede de bt.Strategy en el fichero."
        )

    namespace: dict[str, object] = {}
    try:
        # La ejecución es necesaria para obtener las clases reales (indicadores,
        # parámetros, etc.). Ver la advertencia de seguridad del módulo.
        exec(compile(tree, "<estrategia_usuario>", "exec"), namespace)  # noqa: S102
    except Exception as exc:  # noqa: BLE001
        raise StrategyLoadError(f"No se pudo cargar la estrategia: {exc}") from exc

    strategies = {name: namespace[name] for name in names if name in namespace}
    if not strategies:
        raise StrategyLoadError("Las estrategias declaradas no se pudieron instanciar.")
    return strategies
