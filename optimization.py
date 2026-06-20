"""
optimization.py
===============
Lógica del módulo de optimización y análisis de sensibilidad de StratStats.

Modelo de trabajo:
    1. El usuario elige qué parámetros optimizar (1..N) y el rango/salto de cada
       uno; los no seleccionados quedan en su valor por defecto.
    2. Se ejecuta UN barrido sobre todas las combinaciones (``optstrategy``),
       recopilando varias métricas por combinación.
    3. En la fase de visualización, el usuario elige qué parámetro ver en la
       curva y qué pareja en el mapa de calor. Los demás parámetros se
       *agregan* eligiendo, para cada punto, el mejor resultado ("mejor") o la
       media ("media").

La parte de cálculo no depende de Streamlit; Backtrader y Plotly se importan
de forma diferida.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

#: Tope de combinaciones del barrido (protege frente a explosiones combinatorias).
MAX_COMBINATIONS = 5000
#: Tope de valores por parámetro.
MAX_VALUES_PER_PARAM = 200

#: Modos de agregación de los parámetros NO representados.
AGG_BEST = "mejor"
AGG_MEAN = "media"
AGGREGATIONS = (AGG_BEST, AGG_MEAN)


class OptimizationError(Exception):
    """Error controlado en la configuración o ejecución de una optimización."""


# --------------------------------------------------------------------------- #
# Métricas objetivo
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Objective:
    """Describe una métrica objetivo del barrido."""

    label: str
    column: str
    higher_is_better: bool
    extractor: Callable[["object"], float]


def _safe(value) -> float:
    try:
        if value is None:
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _final_value(strat) -> float:
    # IMPORTANTE: con optstrategy, los strats devueltos comparten el broker, por
    # lo que strat.broker.getvalue() daría el mismo valor (el de la última
    # ejecución) para todas las combinaciones. El valor real de cada combinación
    # se captura DURANTE la ejecución con el analyzer 'value' (ver run_optimization).
    try:
        return _safe(strat.analyzers.value.get_analysis()["final"])
    except Exception:  # noqa: BLE001 - respaldo
        return _safe(strat.broker.getvalue())


def _total_return_pct(strat) -> float:
    try:
        data = strat.analyzers.value.get_analysis()
        start, final = _safe(data["start"]), _safe(data["final"])
    except Exception:  # noqa: BLE001 - respaldo
        start, final = _safe(strat.broker.startingcash), _safe(strat.broker.getvalue())
    if not start:
        return float("nan")
    return (final / start - 1.0) * 100.0


def _sharpe(strat) -> float:
    try:
        return _safe(strat.analyzers.sharpe.get_analysis().get("sharperatio"))
    except Exception:  # noqa: BLE001
        return float("nan")


def _max_drawdown_pct(strat) -> float:
    try:
        return _safe(strat.analyzers.drawdown.get_analysis()["max"]["drawdown"])
    except Exception:  # noqa: BLE001
        return float("nan")


def _sqn(strat) -> float:
    try:
        return _safe(strat.analyzers.sqn.get_analysis().get("sqn"))
    except Exception:  # noqa: BLE001
        return float("nan")


OBJECTIVES: dict[str, Objective] = {
    "Valor final de la cartera": Objective(
        "Valor final de la cartera", "valor_final", True, _final_value),
    "Rentabilidad total (%)": Objective(
        "Rentabilidad total (%)", "rentabilidad_pct", True, _total_return_pct),
    "Ratio de Sharpe": Objective(
        "Ratio de Sharpe", "sharpe", True, _sharpe),
    "Máximo drawdown (%)": Objective(
        "Máximo drawdown (%)", "max_drawdown_pct", False, _max_drawdown_pct),
    "SQN (System Quality Number)": Objective(
        "SQN (System Quality Number)", "sqn", True, _sqn),
}

_ALWAYS = ("valor_final", "rentabilidad_pct", "sharpe", "max_drawdown_pct", "sqn")
_EXTRACTORS = {obj.column: obj.extractor for obj in OBJECTIVES.values()}


# --------------------------------------------------------------------------- #
# Generación de valores de un parámetro
# --------------------------------------------------------------------------- #
def build_param_values(start, stop, step, step_type: str = "abs") -> list:
    """
    Genera la lista de valores de un parámetro a partir de un rango y un salto
    (aditivo en modo ``"abs"`` o porcentual en modo ``"pct"``).

    Devuelve ``int`` si todos los valores son enteros. Lanza
    :class:`OptimizationError` si la configuración no es coherente o excesiva.
    """
    try:
        start, stop, step = float(start), float(stop), float(step)
    except (TypeError, ValueError) as exc:
        raise OptimizationError("Los valores de rango y salto deben ser numéricos.") from exc

    if step <= 0:
        raise OptimizationError("El salto debe ser un número positivo.")
    if stop < start:
        raise OptimizationError("El valor final no puede ser menor que el inicial.")

    values: list[float] = []
    if step_type == "abs":
        n = int(round((stop - start) / step)) + 1
        if n > MAX_VALUES_PER_PARAM:
            raise OptimizationError(
                f"El rango genera {n} valores (máximo {MAX_VALUES_PER_PARAM}). "
                "Aumenta el salto o reduce el rango.")
        values = [round(start + i * step, 10) for i in range(n)]
    elif step_type == "pct":
        if start <= 0:
            raise OptimizationError(
                "Con salto porcentual el valor inicial debe ser mayor que cero.")
        current = start
        while current <= stop * (1 + 1e-9):
            values.append(round(current, 10))
            current *= 1 + step / 100.0
            if len(values) > MAX_VALUES_PER_PARAM:
                raise OptimizationError(
                    f"El rango genera más de {MAX_VALUES_PER_PARAM} valores. "
                    "Aumenta el salto porcentual o reduce el rango.")
    else:
        raise OptimizationError(f"Tipo de salto no admitido: {step_type!r}.")

    if not values:
        raise OptimizationError("El rango indicado no genera ningún valor.")
    if all(float(v).is_integer() for v in values):
        values = [int(v) for v in values]
    return values


# --------------------------------------------------------------------------- #
# Parámetros de la estrategia
# --------------------------------------------------------------------------- #
def get_param_names(strategy_class) -> list[str]:
    """Devuelve los nombres de los parámetros declarados por la estrategia."""
    try:
        return list(strategy_class.params._getkeys())
    except Exception as exc:  # noqa: BLE001
        raise OptimizationError(
            "No se pudieron leer los parámetros de la estrategia.") from exc


def default_param_value(strategy_class, name: str):
    """Valor por defecto de un parámetro de la estrategia."""
    return getattr(strategy_class.params, name)


def count_combinations(param_grid: dict[str, list]) -> int:
    """Número de combinaciones (backtests) que generará un barrido."""
    n = 1
    for values in param_grid.values():
        n *= max(len(values), 1)
    return n


# --------------------------------------------------------------------------- #
# Ejecución del barrido
# --------------------------------------------------------------------------- #
def run_optimization(
    strategy_class,
    data_feed,
    param_grid: dict[str, list],
    cash: float = 100_000.0,
    commission: float = 0.0,
    slippage: float = 0.0,
    maxcpus: int = 1,
) -> pd.DataFrame:
    """
    Ejecuta el barrido sobre TODAS las combinaciones de ``param_grid`` (1..N
    parámetros) y devuelve una tabla con una fila por combinación: una columna
    por parámetro optimizado más las columnas de métricas.

    La métrica objetivo ya no se fija aquí: se calculan todas y la selección se
    hace en la fase de visualización, de modo que un único barrido sirve para
    explorar cualquier métrica y cualquier combinación de gráficos.
    """
    import backtrader as bt

    class _ValueRecorder(bt.Analyzer):
        """Captura el valor final y el capital inicial DURANTE la ejecución.

        Necesario porque, con optstrategy, leer el broker tras cerebro.run()
        devuelve el mismo valor para todas las combinaciones (broker compartido).
        """

        def stop(self):
            self.rets["final"] = self.strategy.broker.getvalue()
            self.rets["start"] = self.strategy.broker.startingcash

    if not param_grid:
        raise OptimizationError("Debes seleccionar al menos un parámetro a optimizar.")
    for name, values in param_grid.items():
        if not values:
            raise OptimizationError(f"El parámetro '{name}' no tiene valores.")

    n_comb = count_combinations(param_grid)
    if n_comb > MAX_COMBINATIONS:
        raise OptimizationError(
            f"La combinación de parámetros genera {n_comb} backtests "
            f"(máximo {MAX_COMBINATIONS}). Reduce el rango, aumenta el salto o "
            "optimiza menos parámetros a la vez.")

    cerebro = bt.Cerebro(optreturn=False, maxcpus=maxcpus or 1)
    cerebro.optstrategy(strategy_class, **param_grid)
    cerebro.adddata(data_feed)
    cerebro.broker.set_cash(float(cash))
    if commission:
        cerebro.broker.setcommission(commission=float(commission))
    if slippage:
        cerebro.broker.set_slippage_perc(perc=float(slippage))
    cerebro.addanalyzer(_ValueRecorder, _name="value")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")

    try:
        runs = cerebro.run()
    except Exception as exc:  # noqa: BLE001
        raise OptimizationError(f"Error durante la ejecución del barrido: {exc}") from exc

    names = list(param_grid.keys())
    rows: list[dict] = []
    for run in runs:
        for strat in run:  # con optstrategy cada elemento es una lista de strats
            row: dict[str, object] = {n: getattr(strat.params, n) for n in names}
            for col in _ALWAYS:
                row[col] = _EXTRACTORS[col](strat)
            rows.append(row)

    if not rows:
        raise OptimizationError("El barrido no produjo resultados.")
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Selección del óptimo global
# --------------------------------------------------------------------------- #
def best_row(results: pd.DataFrame, objective: str) -> pd.Series:
    """Fila con la mejor métrica objetivo en todo el barrido."""
    obj = OBJECTIVES[objective]
    valid = results.dropna(subset=[obj.column])
    if valid.empty:
        raise OptimizationError(
            f"No hay valores válidos de '{obj.label}' para elegir un óptimo.")
    idx = valid[obj.column].idxmax() if obj.higher_is_better else valid[obj.column].idxmin()
    return results.loc[idx]


# --------------------------------------------------------------------------- #
# Agregación de los parámetros no representados
# --------------------------------------------------------------------------- #
def _aggfunc(objective: str, agg: str) -> str:
    """Traduce (objetivo, modo) al ``aggfunc`` de pandas."""
    if agg == AGG_MEAN:
        return "mean"
    if agg == AGG_BEST:
        return "max" if OBJECTIVES[objective].higher_is_better else "min"
    raise OptimizationError(f"Modo de agregación no admitido: {agg!r}.")


def marginal_curve(results: pd.DataFrame, pname: str, objective: str,
                   agg: str = AGG_BEST) -> pd.DataFrame:
    """
    Devuelve, para cada valor del parámetro *pname*, el valor agregado de la
    métrica objetivo sobre el resto de parámetros (mejor o media).
    """
    obj = OBJECTIVES[objective]
    if pname not in results.columns:
        raise OptimizationError(f"El parámetro '{pname}' no está en los resultados.")
    data = results[[pname, obj.column]].dropna()
    if data.empty:
        raise OptimizationError("No hay datos válidos para representar la curva.")
    grouped = data.groupby(pname)[obj.column].agg(_aggfunc(objective, agg))
    return grouped.reset_index().sort_values(pname)


def heatmap_pivot(results: pd.DataFrame, p1: str, p2: str, objective: str,
                  agg: str = AGG_BEST) -> pd.DataFrame:
    """Tabla pivote (p2 x p1) con la métrica agregada sobre el resto."""
    obj = OBJECTIVES[objective]
    for p in (p1, p2):
        if p not in results.columns:
            raise OptimizationError(f"El parámetro '{p}' no está en los resultados.")
    if p1 == p2:
        raise OptimizationError("Elige dos parámetros distintos para el mapa de calor.")
    data = results[[p1, p2, obj.column]].dropna()
    if data.empty:
        raise OptimizationError("No hay datos válidos para representar el mapa de calor.")
    pivot = data.pivot_table(index=p2, columns=p1, values=obj.column,
                             aggfunc=_aggfunc(objective, agg))
    return pivot.sort_index().sort_index(axis=1)


# --------------------------------------------------------------------------- #
# Visualizaciones
# --------------------------------------------------------------------------- #
def make_curve_figure(results: pd.DataFrame, pname: str, objective: str,
                      agg: str = AGG_BEST):
    """Curva de la métrica objetivo frente a un parámetro (resto agregado)."""
    import plotly.graph_objects as go

    obj = OBJECTIVES[objective]
    curve = marginal_curve(results, pname, objective, agg)
    opt_idx = (curve[obj.column].idxmax() if obj.higher_is_better
               else curve[obj.column].idxmin())
    opt = curve.loc[opt_idx]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=curve[pname], y=curve[obj.column], mode="lines+markers",
        name=obj.label, line=dict(color="#4F81BD")))
    fig.add_trace(go.Scatter(
        x=[opt[pname]], y=[opt[obj.column]], mode="markers",
        name="Óptimo", marker=dict(color="#C0504D", size=12, symbol="star")))
    fig.update_layout(
        title=f"{obj.label} en función de «{pname}» (agregación: {agg})",
        xaxis_title=pname, yaxis_title=obj.label, template="plotly_white")
    return fig


def make_heatmap_figure(results: pd.DataFrame, p1: str, p2: str, objective: str,
                        agg: str = AGG_BEST):
    """Mapa de calor de la métrica frente a dos parámetros (resto agregado)."""
    import plotly.graph_objects as go

    obj = OBJECTIVES[objective]
    pivot = heatmap_pivot(results, p1, p2, objective, agg)
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[str(c) for c in pivot.columns],
        y=[str(i) for i in pivot.index],
        colorbar=dict(title=obj.label),
        colorscale="RdYlGn" if obj.higher_is_better else "RdYlGn_r"))
    stacked = pivot.stack()
    best_idx = stacked.idxmax() if obj.higher_is_better else stacked.idxmin()
    fig.add_trace(go.Scatter(
        x=[str(best_idx[1])], y=[str(best_idx[0])], mode="markers",
        name="Óptimo", marker=dict(color="#000000", size=14, symbol="star")))
    fig.update_layout(
        title=f"{obj.label} según «{p1}» y «{p2}» (agregación: {agg})",
        xaxis_title=p1, yaxis_title=p2, template="plotly_white")
    return fig
