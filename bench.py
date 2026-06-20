"""
bench.py
========
Mide el tiempo de ejecucion de un backtest individual y de un barrido de
optimizacion sobre datos sinteticos. Ejecutar en el entorno cuyo rendimiento se
quiera documentar (local y/o Streamlit Cloud):

    python bench.py

Los resultados se imprimen por pantalla para trasladarlos a la tabla 7.3 de la
memoria. Las cifras dependen de la maquina; sirven como orden de magnitud.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd

from data_loader import make_feed
from optimization import run_optimization
from estrategia_ejemplo import CruceMedias
import backtrader as bt


def serie(n: int) -> pd.DataFrame:
    idx = pd.date_range("2015-01-01", periods=n, freq="D")
    rng = np.random.default_rng(7)
    close = 100.0 + np.cumsum(rng.normal(0.05, 1.0, size=n))
    return pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99,
         "Close": close, "Volume": 1000.0},
        index=idx,
    )


def cronometra(descr: str, fn) -> None:
    t0 = time.perf_counter()
    fn()
    print(f"{descr:<55} {time.perf_counter() - t0:6.3f} s")


if __name__ == "__main__":
    df = serie(2520)  # ~10 anios de datos diarios

    def un_backtest():
        c = bt.Cerebro()
        c.addstrategy(CruceMedias)
        c.adddata(make_feed(df))
        c.broker.set_cash(100_000.0)
        c.run()

    def barrido(n):
        grid = {"sma_rapida": list(range(5, 5 + n))}
        run_optimization(CruceMedias, make_feed(df), grid, cash=100_000.0)

    print("Rendimiento (datos sinteticos, ~10 anios diarios)\n" + "-" * 65)
    cronometra("Backtest individual", un_backtest)
    cronometra("Barrido de optimizacion (10 combinaciones)", lambda: barrido(10))
    cronometra("Barrido de optimizacion (50 combinaciones)", lambda: barrido(50))
