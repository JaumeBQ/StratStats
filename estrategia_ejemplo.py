"""
Estrategia de ejemplo para StratStats: cruce de medias móviles.

Pensada para PROBAR la optimización y el análisis de sensibilidad: sus
parámetros cambian mucho el resultado.

Parámetros optimizables:
    sma_rapida : periodo de la media móvil rápida
    sma_lenta  : periodo de la media móvil lenta
    stop_loss  : stop loss en % (0 = desactivado)

Notas de diseño importantes (las dos causas típicas de que "no varíe"):
    * Se dimensiona la posición con el CAPITAL disponible (no compra 1 acción),
      por lo que cambiar los parámetros cambia de verdad el resultado.
    * Se deja un 5 % de margen al comprar para poder pagar comisión y slippage.
      Si se invirtiera el 100 % del capital y hubiese comisión, Backtrader
      rechazaría la orden por fondos insuficientes y no se operaría.

Compatible con las dos páginas de la app:
    * Optimización: declara `params` (lo que barre el optimizador).
    * Backtesting: mantiene `self.trade_log` con 'buyprice'/'sellprice', que es
      lo que espera tu analyzer TradeAnalyzer1.
"""

import backtrader as bt


class CruceMedias(bt.Strategy):
    params = (
        ("sma_rapida", 10),
        ("sma_lenta", 30),
        ("stop_loss", 0.0),
    )

    def __init__(self):
        self.trade_log = []
        self.sma_fast = bt.ind.SMA(period=self.p.sma_rapida)
        self.sma_slow = bt.ind.SMA(period=self.p.sma_lenta)
        self.crossover = bt.ind.CrossOver(self.sma_fast, self.sma_slow)
        self.precio_entrada = None

    def next(self):
        price = self.data.close[0]

        if not self.position:
            if self.crossover > 0:  # media rápida cruza al alza
                # 95 % del capital, dejando margen para comisión/slippage
                size = int((self.broker.getcash() * 0.95) // price)
                if size > 0:
                    self.buy(size=size)
        else:
            stop_hit = (
                self.p.stop_loss > 0
                and self.precio_entrada is not None
                and price <= self.precio_entrada * (1 - self.p.stop_loss / 100.0)
            )
            if self.crossover < 0 or stop_hit:  # cruce a la baja o stop
                self.close()

    def notify_order(self, order):
        if order.status == order.Completed:
            if order.isbuy():
                self.precio_entrada = order.executed.price
            elif order.issell():
                self.trade_log.append({
                    "buyprice": self.precio_entrada,
                    "sellprice": order.executed.price,
                })
