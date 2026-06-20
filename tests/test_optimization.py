"""
test_optimization.py
====================
Pruebas unitarias de las funciones puras del modulo de optimizacion
(optimization.py): generacion de valores de un parametro, conteo de
combinaciones, seleccion del optimo y construccion de curva y mapa de calor.

Estas pruebas NO necesitan Backtrader: trabajan sobre tablas de resultados
sinteticas, lo que permite validar la logica de agregacion y seleccion de
forma aislada y muy rapida.
"""

from __future__ import annotations

import pandas as pd
import pytest

from optimization import (
    OptimizationError,
    MAX_VALUES_PER_PARAM,
    build_param_values,
    count_combinations,
    best_row,
    marginal_curve,
    heatmap_pivot,
)


# --------------------------------------------------------------------------- #
# build_param_values - modo absoluto
# --------------------------------------------------------------------------- #
def test_valores_absolutos_basico():
    assert build_param_values(10, 14, 2, "abs") == [10, 12, 14]


def test_valores_absolutos_incluye_extremos():
    vals = build_param_values(5, 20, 5, "abs")
    assert vals[0] == 5 and vals[-1] == 20


def test_devuelve_enteros_cuando_procede():
    vals = build_param_values(1, 3, 1, "abs")
    assert all(isinstance(v, int) for v in vals)


def test_devuelve_flotantes_cuando_procede():
    vals = build_param_values(0.5, 1.5, 0.5, "abs")
    assert any(isinstance(v, float) for v in vals)


# --------------------------------------------------------------------------- #
# build_param_values - modo porcentual
# --------------------------------------------------------------------------- #
def test_valores_porcentuales_crecen():
    vals = build_param_values(100, 121, 10, "pct")
    assert vals[0] == 100
    assert vals[-1] <= 121
    assert all(b > a for a, b in zip(vals, vals[1:]))  # estrictamente crecientes


def test_porcentual_con_inicio_no_positivo_falla():
    with pytest.raises(OptimizationError):
        build_param_values(0, 10, 10, "pct")


# --------------------------------------------------------------------------- #
# build_param_values - validacion de configuracion
# --------------------------------------------------------------------------- #
def test_salto_no_positivo_falla():
    with pytest.raises(OptimizationError):
        build_param_values(0, 10, 0, "abs")
    with pytest.raises(OptimizationError):
        build_param_values(0, 10, -2, "abs")


def test_stop_menor_que_start_falla():
    with pytest.raises(OptimizationError):
        build_param_values(10, 5, 1, "abs")


def test_valores_no_numericos_fallan():
    with pytest.raises(OptimizationError):
        build_param_values("a", 10, 1, "abs")


def test_tipo_de_salto_desconocido_falla():
    with pytest.raises(OptimizationError):
        build_param_values(0, 10, 1, "exponencial")


def test_respeta_tope_de_valores():
    """Un rango enorme debe rechazarse antes de generar la lista."""
    with pytest.raises(OptimizationError):
        build_param_values(0, MAX_VALUES_PER_PARAM * 10, 1, "abs")


# --------------------------------------------------------------------------- #
# count_combinations
# --------------------------------------------------------------------------- #
def test_conteo_de_combinaciones():
    grid = {"a": [1, 2, 3], "b": [10, 20]}
    assert count_combinations(grid) == 6


def test_conteo_un_solo_parametro():
    assert count_combinations({"a": [1, 2, 3, 4]}) == 4


# --------------------------------------------------------------------------- #
# best_row - seleccion del optimo segun el sentido de la metrica
# --------------------------------------------------------------------------- #
@pytest.fixture
def tabla_resultados() -> pd.DataFrame:
    """Tabla de barrido sintetica con dos parametros y metricas conocidas."""
    return pd.DataFrame(
        {
            "sma_rapida": [5, 5, 10, 10],
            "sma_lenta": [20, 30, 20, 30],
            "valor_final": [110.0, 90.0, 130.0, 105.0],
            "rentabilidad_pct": [10.0, -10.0, 30.0, 5.0],
            "sharpe": [0.5, -0.2, 1.5, 0.8],
            "max_drawdown_pct": [12.0, 25.0, 8.0, 15.0],
            "sqn": [1.0, 0.3, 2.5, 1.2],
        }
    )


def test_optimo_maximiza_metrica_creciente(tabla_resultados):
    fila = best_row(tabla_resultados, "Ratio de Sharpe")
    assert fila["sharpe"] == 1.5  # el maximo


def test_optimo_minimiza_drawdown(tabla_resultados):
    """El drawdown es 'mejor cuanto menor': el optimo es el minimo."""
    fila = best_row(tabla_resultados, "Máximo drawdown (%)")
    assert fila["max_drawdown_pct"] == 8.0  # el minimo


# --------------------------------------------------------------------------- #
# marginal_curve y heatmap_pivot
# --------------------------------------------------------------------------- #
def test_curva_marginal_agrega_el_resto(tabla_resultados):
    curva = marginal_curve(tabla_resultados, "sma_rapida",
                           "Rentabilidad total (%)", agg="mejor")
    # para sma_rapida=10 el mejor de {30, 5} es 30
    fila10 = curva[curva["sma_rapida"] == 10]
    assert fila10["rentabilidad_pct"].iloc[0] == 30.0


def test_heatmap_pivot_dimensiones(tabla_resultados):
    pivot = heatmap_pivot(tabla_resultados, "sma_rapida", "sma_lenta",
                          "Ratio de Sharpe")
    assert pivot.shape == (2, 2)  # 2 valores de cada parametro


def test_heatmap_mismos_parametros_falla(tabla_resultados):
    with pytest.raises(OptimizationError):
        heatmap_pivot(tabla_resultados, "sma_rapida", "sma_rapida",
                      "Ratio de Sharpe")
