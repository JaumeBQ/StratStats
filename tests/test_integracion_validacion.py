"""
test_integracion_validacion.py
==============================
Pruebas de INTEGRACION y de VALIDACION DE LA CORRECCION de los resultados.

A diferencia de las unitarias, aqui se ejercita el motor real de Backtrader de
extremo a extremo. Se cubren tres aspectos:

  1. Integracion: cargar una estrategia, ejecutar un backtest y un barrido de
     optimizacion completos sin errores.
  2. Validacion por oraculo: una estrategia de compra-y-mantener debe producir
     un valor final coherente con la variacion de precio del activo, calculado
     de forma independiente al motor.
  3. Regresion del "broker compartido": el barrido de optimizacion debe
     reportar valores DISTINTOS por combinacion (protege frente al bug
     documentado en el apartado de implementacion).

Requiere Backtrader instalado; si no lo esta, las pruebas se omiten (skip).
"""

from __future__ import annotations

import pandas as pd
import pytest

bt = pytest.importorskip("backtrader")  # omite el modulo si no hay Backtrader

from data_loader import make_feed
from optimization import run_optimization
from estrategia_ejemplo import CruceMedias


# --------------------------------------------------------------------------- #
# Estrategia auxiliar de compra-y-mantener (oraculo)
# --------------------------------------------------------------------------- #
class CompraYMantiene(bt.Strategy):
    """Compra una cantidad fija en la primera barra util y no vende nunca."""

    params = (("size", 10),)

    def __init__(self):
        self.precio_compra = None

    def next(self):
        if not self.position and len(self) == 1:
            self.buy(size=self.p.size)

    def notify_order(self, order):
        if order.status == order.Completed and order.isbuy():
            self.precio_compra = order.executed.price


# --------------------------------------------------------------------------- #
# 1) Integracion de extremo a extremo
# --------------------------------------------------------------------------- #
def test_backtest_extremo_a_extremo(serie_precios):
    """Ejecutar la estrategia de ejemplo no debe lanzar excepciones."""
    cerebro = bt.Cerebro()
    cerebro.addstrategy(CruceMedias)
    cerebro.adddata(make_feed(serie_precios))
    cerebro.broker.set_cash(100_000.0)
    resultados = cerebro.run()
    assert resultados  # devuelve al menos un strat
    assert cerebro.broker.getvalue() > 0


def test_barrido_optimizacion_produce_tabla(serie_precios):
    """run_optimization devuelve una fila por combinacion con sus metricas."""
    grid = {"sma_rapida": [5, 10, 15]}
    tabla = run_optimization(CruceMedias, make_feed(serie_precios), grid,
                             cash=100_000.0)
    assert isinstance(tabla, pd.DataFrame)
    assert len(tabla) == 3  # tres valores -> tres backtests
    for col in ("valor_final", "rentabilidad_pct", "sharpe",
                "max_drawdown_pct", "sqn"):
        assert col in tabla.columns


# --------------------------------------------------------------------------- #
# 2) Validacion por oraculo analitico
# --------------------------------------------------------------------------- #
def test_oraculo_compra_y_mantener(serie_precios):
    """
    El valor final de una cartera de compra-y-mantener debe coincidir con:

        capital_inicial + size * (precio_ultimo_cierre - precio_de_compra)

    calculado de forma independiente al motor. Se admite una tolerancia minima
    por el redondeo interno de Backtrader.
    """
    capital = 100_000.0
    size = 10

    cerebro = bt.Cerebro()
    cerebro.addstrategy(CompraYMantiene, size=size)
    cerebro.adddata(make_feed(serie_precios))
    cerebro.broker.set_cash(capital)
    strat = cerebro.run()[0]

    valor_final_motor = cerebro.broker.getvalue()
    precio_ultimo = float(serie_precios["Close"].iloc[-1])
    precio_compra = float(strat.precio_compra)

    valor_esperado = capital + size * (precio_ultimo - precio_compra)

    assert valor_final_motor == pytest.approx(valor_esperado, rel=1e-6)


# --------------------------------------------------------------------------- #
# 3) Regresion del bug del "broker compartido"
# --------------------------------------------------------------------------- #
def test_optimizacion_no_devuelve_curva_plana(serie_precios):
    """
    Con optstrategy, los strats devueltos comparten broker; si el valor final
    se leyera del broker tras run(), todas las combinaciones darian el mismo
    numero (curva plana). El analyzer 'value' captura el valor durante la
    ejecucion, asi que las combinaciones deben diferir.
    """
    grid = {"sma_rapida": [5, 10, 20, 40]}
    tabla = run_optimization(CruceMedias, make_feed(serie_precios), grid,
                             cash=100_000.0)
    valores = tabla["valor_final"].round(2).unique()
    assert len(valores) > 1, (
        "Todas las combinaciones devuelven el mismo valor final: "
        "posible regresion del bug del broker compartido."
    )
