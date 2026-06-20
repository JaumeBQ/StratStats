#version acabada de backtesting (cogido del codigo backtest_acabado.py pero limpio)
#autor Jaume Busquets Quilis
#backtestea con quantstats los retornos de la estrategia y con un analizer modificado los trades individuales

#faltaria por implementar el mfa, mae, etc en el analizer de trades


#solucionado:
#analyzador de trades no coge correctamente el precio de cierre de cada trade 
# y se coge el precio de cierre de la vela->solucionado pero no depurado->solucionado solo para el trade que se esta cerrando
#solucionado con max y min de la vela


#en el trade analyzer se podria incorporar que algunas metricas como el sharperatio se guarden todos los valores
#y no solo obtener el ultimo, para ver la evolucion de esta metrica y no solo el valor final, ya ocurre gracias a quantstats



from pprint import pprint
import backtrader as bt
import quantstats as qs
import pandas as pd
import yfinance as yf
import webbrowser
import os
import tempfile
import time
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import plotly.figure_factory as ff

from datetime import datetime, timedelta

import warnings

#hay un warning en el uso interno de pandas por quantstats, para que este no salte ponemos estas lineas de codigo
#si en futuras versiones da error deberiamos actualizar las librerias a versiones donde este error no se produzca
#resultado = tu_dataframe.prod(axis=0), actualmente seria resultado = tu_dataframe.prod()
#warnings.filterwarnings("ignore", message="The behavior of DataFrame.prod with axis=None is deprecated")

class TradeAnalyzer1(bt.Analyzer):
    
    def __init__(self):
        self.trades = []
        #self.provisional = []
        self.current_trade = None

        self.trade_log = []
        self.i=0

        
    
    def start(self):
        self.strategy = self.strategy
        # print('start')
        # print(self.strategy.trade_log)
        # print('end')
    def stop(self):
        self.trade_log = self.strategy.trade_log
        #print('start')
        #print(self.trade_log)
        #print('stop')



    def notify_trade(self, trade):
        if trade.justopened:
            self.current_trade = {
                'max_pnl': 0,
                'max_drawdown': 0,
                'price_open': trade.price,
                'size': trade.size,
            }
        #no se si este metodo esta del todo correcto
        if trade.isopen and self.current_trade is not None:
            max_current_pnl = (self.data_high[0] - self.current_trade['price_open']) * self.current_trade['size']
            min_current_pnl = (self.data_low[0] - self.current_trade['price_open']) * self.current_trade['size']
            current_pnl = (self.data_close[0]-trade.price) * self.current_trade['size']
            #self.provisional.append(current_pnl)
            #print('current pnl:', current_pnl)
            #print('trade pnl:',trade.pnl)
            self.current_trade['max_pnl'] = max(self.current_trade['max_pnl'], max_current_pnl)
            # El drawdown se calcula como la diferencia entre el máximo pnl y el pnl actual
            current_drawdown = self.current_trade['max_pnl'] - min_current_pnl
            self.current_trade['max_drawdown'] = -1*max(abs(self.current_trade['max_drawdown']), abs(current_drawdown))
       
        if trade.isclosed:
           
            self.i
            PCierre = self.strategy.trade_log[self.i]['sellprice'] 

            pnl = (PCierre-trade.price) * self.current_trade['size']
            print('pnl manual:',pnl)
            print('pnl por el programa:',trade.pnl)
         
            trade_initial_capital = self.current_trade['price_open'] * self.current_trade['size']
            pnl_final_pct = (trade.pnlcomm / trade_initial_capital) * 100
            pnl_max_pct = (self.current_trade['max_pnl'] / trade_initial_capital) * 100
            drawdown_max_pct = (self.current_trade['max_drawdown'] / trade_initial_capital) * 100

            trade_data = {
                'price_open': self.current_trade['price_open'],
                'price_close': PCierre,
                #el precio de cierre no es exactamente self.data_close[0] (porque se ejecuta en el siguiente paso?), el precio de cierre real es PCierre

                'pnl_max': self.current_trade['max_pnl'],
                'drawdown_max': self.current_trade['max_drawdown'],
                'pnl_final_comm': trade.pnlcomm,
                'pnl_final': trade.pnl,

                'pnl_final_pct': pnl_final_pct,
                'pnl_max_pct': pnl_max_pct,
                'drawdown_max_pct': drawdown_max_pct,

                'datetime_open': bt.num2date(trade.dtopen),
                'datetime_close': bt.num2date(trade.dtclose),
                'duration': trade.barlen,
            
            }
            self.trades.append(trade_data)
            trade.current_trade = None
            self.i+=1

    def next(self):
        if self.current_trade is not None:
            #print('precio de cierre definitivo', self.data_close[0])
            #current_pnl es en el cierre del trade pero calculamos el max y min 
            #current_pnl = (self.data_close[0] - self.current_trade['price_open']) * self.current_trade['size']
            max_current_pnl = (self.data_high[0] - self.current_trade['price_open']) * self.current_trade['size']
            min_current_pnl = (self.data_low[0] - self.current_trade['price_open']) * self.current_trade['size']
            self.current_trade['max_pnl'] = max(self.current_trade['max_pnl'], max_current_pnl)
            self.current_trade['max_drawdown'] = -1*max(abs(self.current_trade['max_drawdown']),abs( min_current_pnl))
            # Opcional: imprimir para depuración
            #print(f"Current PnL: {current_pnl}, Max PnL: {self.current_trade['max_pnl']}, max_drawdown: {self.current_trade['max_drawdown']}")
        

    def get_analysis(self):
        #print('trades:')
        #print(self.trades)
        #print('acaban los trades')
        return self.trades
    
#analizadores modificados arriba
#------------------------------------#estrategias abajo
class Jaime(bt.Strategy):
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.sellprice = None
        self.trade_log = []
        self.capital_en_uso = 0
        self.RSI = bt.indicators.RSI(self.data.close, period=14)
        self.SC = bt.indicators.Stochastic(self.data, period=14, safediv=True)
        self.SL = 0.03

    def next(self):
        if not self.position:
            if self.RSI <30 and self.SC<15:
                size = self.broker.get_cash() // self.dataclose[0]
                self.buy(size=size)
        else:
            stop_loss_price = self.buyprice * (1 - self.SL)
            if self.SC>85 or self.dataclose[0] < stop_loss_price:
                self.sell(size = self.position.size)
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        # Comprobar si una orden ha sido completada y guardar su precio de apertura
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                print('Compra ejecutada,', order.executed.price)
            elif order.issell():
                self.sellprice = order.executed.price
                print('Venta ejecutada,', order.executed.price)
            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print('Orden Cancelada/Rechazada')
        self.order = None
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        pnl = trade.pnl
        print(f'precio apertura new: {self.buyprice}')
        print(f'precio de cierre new: {self.sellprice}')
        print(f'pnl manual new: {pnl}')
        self.trade_log.append({
            'buyprice': self.buyprice,
            'sellprice': self.sellprice,
            'pnl': pnl
        })
            

        
class CruceMediasMoviles(bt.Strategy):
    params = (
        ('media_corta', 30),
        ('media_larga', 50),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.sma_corta = bt.indicators.SimpleMovingAverage(self.datas[0], period=self.params.media_corta)
        self.sma_larga = bt.indicators.SimpleMovingAverage(self.datas[0], period=self.params.media_larga)
        self.cruce_al_alza = bt.indicators.CrossOver(self.sma_corta, self.sma_larga)
        self.cruce_a_la_baja = bt.indicators.CrossOver(self.sma_larga, self.sma_corta)
        self.capital_en_uso = 0
        #3 lineas para logear cada trade
        self.buyprice = None
        self.sellprice = None
        self.trade_log = []

    def next(self):
        if self.order:
            return
        
        # precio_actual = self.data.close[0]
        # capital_disponible = self.broker.get_cash()
        # size_disp = capital_disponible / precio_actual

        if not self.position:

            precio_actual = self.data.close[0]
            capital_disponible = self.broker.get_cash()
            size_disp = int((capital_disponible / precio_actual)/2)
            
            if self.cruce_al_alza > 0:
                self.order = self.buy(size= size_disp)
                self.capital_en_uso = size_disp
        else:
            if self.cruce_a_la_baja > 0:
                self.order = self.sell(size = self.capital_en_uso)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        # Comprobar si una orden ha sido completada y guardar su precio de apertura
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                print('Compra ejecutada,', order.executed.price)
            elif order.issell():
                self.sellprice = order.executed.price
                print('Venta ejecutada,', order.executed.price)
            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print('Orden Cancelada/Rechazada')
        self.order = None
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        pnl = trade.pnl
        print(f'precio apertura new: {self.buyprice}')
        print(f'precio de cierre new: {self.sellprice}')
        print(f'pnl manual new: {pnl}')
        self.trade_log.append({
            'buyprice': self.buyprice,
            'sellprice': self.sellprice,
            'pnl': pnl
        })
        

class MyStrategy(bt.Strategy):
    def __init__(self):
        self.dataclose = self.datas[0].close

    def next(self):
        if not self.position:
            if self.dataclose[0] > self.dataclose[-1]:
                self.buy(size=10)
        else:
            if self.dataclose[0] < self.dataclose[-1]:
                self.sell(size=10)




class EmaCrossStrategy(bt.Strategy):
    params = (
        ('ema_fast_period', 50),  # Período para la EMA rápida
        ('ema_slow_period', 200),  # Período para la EMA lenta
    )

    def __init__(self):
        # Inicializar las EMAs
        self.ema_fast = bt.indicators.EMA(self.data.close, period=self.params.ema_fast_period,plotname='EMA Fast')
        self.ema_slow = bt.indicators.EMA(self.data.close, period=self.params.ema_slow_period,plotname='EMA Slow')
        self.stocastic = bt.indicators.Stochastic(self.data, period=14, safediv=True)
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        

        # Indicador para el cruce de EMAs
        self.crossover = bt.indicators.CrossOver(self.ema_fast, self.ema_slow)

    def next(self):
        # Si ya hay una posición abierta, no hacer nada
        if self.position:
            # Si estamos en largo y el cruce es negativo, cerrar la posición larga
            if self.position.size > 0 and self.crossover < 0:
                self.close()
            # Si estamos en corto y el cruce es positivo, cerrar la posición corta
            elif self.position.size < 0 and self.crossover > 0:
                self.close()

        # Si no hay posición abierta, verificar si debemos entrar
        else:
            if self.crossover > 0:  # Cruce ascendente, ir en largo
                self.buy()
            elif self.crossover < 0:  # Cruce descendente, ir en corto
                self.sell()




#------------------------------------#estrategias arriba

# 2. Función para Obtener Datos
def obtener_datos(simbolo, fecha_inicio, fecha_fin, temporalidad):
    data_df = yf.download(simbolo, start=fecha_inicio, end=fecha_fin, interval = temporalidad)
    data_df['OpenInterest'] = 0  # Añadir una columna de OpenInterest
    data = bt.feeds.PandasData(dataname=data_df)
    return data

def obtener_datos_csv(ruta_archivo):
    data = bt.feeds.GenericCSVData(dataname=ruta_archivo, dtformat=('%Y-%m-%d'), datetime=0, high=2, low=3, open=1, close=4, volume=5, openinterest=-1)
    return data


# 3. Función para Configurar y Ejecutar Backtrader
def ejecutar_backtrader(estrategia, datos, slipagge, comision):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(estrategia)
    #si el csv estaba en formato de 1minuto datos ya esta en 1 minuto 
    cerebro.adddata(datos)


    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    #analyzador personalizado
    cerebro.addanalyzer(TradeAnalyzer1, _name='trade_analyzer1')
    #slipage y comisiones
    cerebro.broker.set_slippage_perc(perc = slipagge)
    cerebro.broker.setcommission(commission=comision )

    resultados = cerebro.run()
    #cerebro.plot()
    fig = cerebro.plot()[0][0]
    #fig.savefig('backtest_plot.png')
    
    #return resultados[0]
    return resultados, fig

#no se para que es esta funcion
def obtener_trades(estrategia_resultado):
    trades = estrategia_resultado.analyzers.trade_analyzer.get_analysis()
    return trades

#crea el html completo de quantstats basandose en los retornos pyfolio
def obtener_resultados2(estrategia_resultado, simbolo):
    #EXPLICAICION DEL METODO:
    #   para crear el html le debemos dar los retornos de la estrategia en formato diario, para eso usaremos 
    #   el analuzador de pyfolio que nos da un diccionario con los retornos, posiciones, transacciones y gross_lev
    #   creamos un file temporal para no ocupar espacio inecesario en el ordenador cada vez que se crea un html
    #   hacemos un debuger para ver si el formato de los retornos esta en el formato correcto que queremos
    # Aquí es donde integras el código para procesar los resultados
        portfolio_stats = estrategia_resultado.analyzers.pyfolio.get_analysis()
        
        returns_data = portfolio_stats['returns']

        if not isinstance(returns_data, (pd.Series, pd.DataFrame)):
            returns = pd.Series(returns_data)
            #print('retornos:', returns)
        else:
            returns = returns_data
        

        returns.index = pd.to_datetime(returns.index)
        
        nombre_archivo = f"Análisis_de_{simbolo}_vs_SPY.html"
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, nombre_archivo)
    

        qs.reports.html(returns, benchmark="SPY", output=temp_file_path)


        
        webbrowser.open('file://' + os.path.realpath(temp_file_path))
        # Espera un tiempo antes de borrar el archivo, por ejemplo, 60 segundos
        time.sleep(10)  # Ajusta el tiempo según lo necesites
    
        # Elimina el archivo HTML
        os.remove(temp_file_path)






        

#metodo que dado mi analyzer personalizado de trades me los plotea con su maximo, minimo y pnl. 
#se podria implementar el MFE, MAE etc
def graficar_trades(trade_analyzer):
    #se ha llamado a: graficar_trades(estrategia_resultado.analyzers.trade_analyzer1.get_analysis())
    
    # Extraer datos
    pnl_final = [trade['pnl_final'] for trade in trade_analyzer]
    pnl_max = [trade['pnl_max'] for trade in trade_analyzer]
    drawdown_max = [trade['drawdown_max'] for trade in trade_analyzer]
    pnl_final_pct = [trade['pnl_final_pct'] for trade in trade_analyzer]
    pnl_max_pct = [trade['pnl_max_pct'] for trade in trade_analyzer]
    drawdown_max_pct = [trade['drawdown_max_pct'] for trade in trade_analyzer]
    x = range(len(pnl_final))
    n_trades = len(pnl_final)


    # Configurar gráfica de valores absolutos
    plt.figure(figsize=(14, 6))
    plt.subplot(1, 2, 1)  # 1 fila, 2 columnas, primer gráfico
    plt.bar(x, pnl_final, label='PnL Final')
    plt.plot(x, pnl_max, color='green', linestyle='--', label='PnL Máximo')
    plt.plot(x, drawdown_max, color='red', linestyle='--', label='Drawdown Máximo')
    plt.xlabel('Trade')
    plt.ylabel('Valor')
    plt.title('Resultados de Trades (Valor Absoluto)')
    plt.legend()
    #pone los numeros de cada trade debajo de estos empezando por el trade 0
    plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=n_trades))

    # Configurar gráfica de valores en porcentaje
    plt.subplot(1, 2, 2)  # 1 fila, 2 columnas, segundo gráfico
    plt.bar(x, pnl_final_pct, label='PnL Final (%)')
    plt.plot(x, pnl_max_pct, color='green', linestyle='--', label='PnL Máximo (%)')
    plt.plot(x, drawdown_max_pct, color='red', linestyle='--', label='Drawdown Máximo (%)')
    plt.xlabel('Trade')
    plt.ylabel('Porcentaje')
    plt.title('Resultados de Trades (%)')
    plt.legend()
    plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=n_trades))

    # Mostrar gráfica
    plt.tight_layout()
    return plt.show()
    # return plt


def graficar_trades2(analysis):
    # Crear una figura y un conjunto de ejes
    fig, ax = plt.subplots(1, 2, figsize=(14, 6))  # 1 fila, 2 columnas

    pnl_final = [trade['pnl_final'] for trade in analysis]
    pnl_max = [trade['pnl_max'] for trade in analysis]
    drawdown_max = [trade['drawdown_max'] for trade in analysis]
    pnl_final_pct = [trade['pnl_final_pct'] for trade in analysis]
    pnl_max_pct = [trade['pnl_max_pct'] for trade in analysis]
    drawdown_max_pct = [trade['drawdown_max_pct'] for trade in analysis]
    x = range(len(pnl_final))
    n_trades = len(pnl_final)

    # Datos de ejemplo (debes reemplazar esto con tus datos reales)
    # x = range(len(analysis['trades']))
    # pnl_final = [trade.pnl for trade in analysis['trades']]
    # pnl_max = [trade.pnlmax for trade in analysis['trades']]
    # drawdown_max = [trade.drawdown for trade in analysis['trades']]
    # pnl_final_pct = [trade.pnl_pct for trade in analysis['trades']]
    # pnl_max_pct = [trade.pnlmax_pct for trade in analysis['trades']]
    # drawdown_max_pct = [trade.drawdown_pct for trade in analysis['trades']]
    # n_trades = len(analysis['trades'])

    # Configurar gráfica de valores absolutos
    ax[0].bar(x, pnl_final, label='PnL Final')
    ax[0].plot(x, pnl_max, color='green', linestyle='--', label='PnL Máximo')
    ax[0].plot(x, drawdown_max, color='red', linestyle='--', label='Drawdown Máximo')
    ax[0].set_xlabel('Trade')
    ax[0].set_ylabel('Valor')
    ax[0].set_title('Resultados de Trades (Valor Absoluto)')
    ax[0].legend()
    ax[0].xaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=n_trades))

    # Configurar gráfica de valores en porcentaje
    ax[1].bar(x, pnl_final_pct, label='PnL Final (%)')
    ax[1].plot(x, pnl_max_pct, color='green', linestyle='--', label='PnL Máximo (%)')
    ax[1].plot(x, drawdown_max_pct, color='red', linestyle='--', label='Drawdown Máximo (%)')
    ax[1].set_xlabel('Trade')
    ax[1].set_ylabel('Porcentaje')
    ax[1].set_title('Resultados de Trades (%)')
    ax[1].legend()
    ax[1].xaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=n_trades))

    # Ajustar el diseño de la figura
    fig.tight_layout()

    # Devolver la figura
    return fig

def graficar_trades3(analysis):
     # Datos de ejemplo (debes reemplazar esto con tus datos reales)
    pnl_final = [trade['pnl_final'] for trade in analysis]
    pnl_max = [trade['pnl_max'] for trade in analysis]
    drawdown_max = [trade['drawdown_max'] for trade in analysis]

    # Crear los datos para el gráfico de distribución
    hist_data = [pnl_final, pnl_max, drawdown_max]
    group_labels = ['PnL Final', 'PnL Máximo', 'Drawdown Máximo']

    # Crear el gráfico de distribución
    fig = ff.create_distplot(hist_data, group_labels, bin_size=[.1, .25, .5])

    # Devolver la figura
    return fig

def graficar_retornos(estrategia_resultado):
    portfolio_stats = estrategia_resultado.analyzers.pyfolio.get_analysis()
    returns_data = portfolio_stats['returns']

    if not isinstance(returns_data, (pd.Series, pd.DataFrame)):
        returns = pd.Series(returns_data)
        #print('retornos:', returns)
    else:
        returns = returns_data
        

    returns.index = pd.to_datetime(returns.index)

    # Calcular los retornos acumulados
    returns_acumulados = (1 + returns).cumprod() - 1

    # Graficar los retornos acumulados
    plt.figure(figsize=(10, 6))  # Tamaño de la figura
    returns_acumulados.plot(title='Retornos Acumulados de la Estrategia')  # Título de la gráfica
    plt.xlabel('Fecha')  # Etiqueta del eje X
    plt.ylabel('Retornos Acumulados')  # Etiqueta del eje Y
    plt.tight_layout()
    plt.show()

    return plt
import plotly.graph_objects as go

def graficar_trades4(analysis):
    # Extraer los datos de análisis (debes reemplazar esto con tus datos reales)
    pnl_final = [trade['pnl_final'] for trade in analysis]
    pnl_max = [trade['pnl_max'] for trade in analysis]
    drawdown_max = [trade['drawdown_max'] for trade in analysis]

    # Crear los datos para el gráfico de barras
    x = list(range(len(pnl_final)))

    # Crear el gráfico de barras
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=x,
        y=pnl_final,
        name='PnL Final',
        marker_color='blue'
    ))

    fig.add_trace(go.Scatter(
        x=x,
        y=pnl_max,
        mode='lines+markers',
        name='PnL Máximo',
        line=dict(color='green', dash='dash')
    ))

    fig.add_trace(go.Scatter(
        x=x,
        y=drawdown_max,
        mode='lines+markers',
        name='Drawdown Máximo',
        line=dict(color='red', dash='dash')
    ))

    # Actualizar el layout del gráfico
    fig.update_layout(
        title='Resultados de Trades',
        xaxis_title='Trade',
        yaxis_title='Valor',
        barmode='relative',
        legend_title='Metricas',
        template='plotly_white'
    )

    # Devolver la figura
    return fig

#este metodo se puede usar al integrarlo con flet para poner pegar los grafico a la interfaz y no a una ventana emergente
def qsmetodo(estrategia_resultado):
    portfolio_stats = estrategia_resultado.analyzers.pyfolio.get_analysis()
    returns_data = portfolio_stats['returns']

    if not isinstance(returns_data, (pd.Series, pd.DataFrame)):
        returns = pd.Series(returns_data)
        #print('retornos:', returns)
    else:
        returns = returns_data
        

    returns.index = pd.to_datetime(returns.index)

  
    #qs.plots.
    qs.plots.returns(returns, savefig='returns.png')
    qs.plots.drawdown(returns, savefig='drawdown.png')
    qs.plots.rolling_volatility(returns,savefig='rolling_volatility.png')
    qs.plots.rolling_sharpe(returns,savefig='sharpe.png')
    
    # Generar un informe de desempeño
    # performance = qs.reports.metrics(returns, mode='full')
    # print(performance)

    for filename in ['returns.png', 'drawdown.png', 'rolling_volatility.png', 'sharpe.png']:
        img = plt.imread(filename)
        plt.imshow(img)
        plt.axis('off')  # Ocultar los ejes
        plt.show()
        os.remove(filename) 

    
    
def qsmetodo_reporte(estrategia_resultado):
    portfolio_stats = estrategia_resultado.analyzers.pyfolio.get_analysis()
    returns_data = portfolio_stats['returns']

    if not isinstance(returns_data, (pd.Series, pd.DataFrame)):
        returns = pd.Series(returns_data)
        #print('retornos:', returns)
    else:
        returns = returns_data
        

    returns.index = pd.to_datetime(returns.index)
    performance = qs.reports.metrics(returns, mode='full')
    #print(performance)
    return performance
    

def main():
    #si quieres testear una estrategia intradia yfinance solo permite los ultimos 60dias, se puede hacer con un csv si no
    #ini = datetime.now() - timedelta(days=60)
    #fin = datetime.now()

    #ini_str = ini.strftime('%Y-%m-%d')
    #fin_str = fin.strftime('%Y-%m-%d')
    #'AAPL', '2020-01-01', '2020-12-31', '1d'
    #simbolos = ['AAPL', 'MSFT', 'SPY']  # Ejemplo con múltiples símbolos
    simbolo = ['IVV']
    ini = '2015-01-01'
    #fin = datetime.now()
    fin = '2023-12-31'
    #formato fechas: '2020-12-31'
    temporalidad = '1d'  # '1d' para diario, '1h' para cada hora, '1m' para cada minuto, etc.
    #temporalidades disponibles 1d, 1w
    slipage = 0.0  
    comision = 0.0


    datos = obtener_datos(simbolo, ini, fin, temporalidad= temporalidad)#obtiene los datos de yfinance
    estrategia_resultado = ejecutar_backtrader(Jaime, datos, slipage, comision)#ejecuta la estrategia y obtiene los resultados
    resultados = estrategia_resultado[0]

    #obtener_resultados2(resultados, simbolo)#hace el analisis de los retornos con quantstats en un html
    #graficar_trades(resultados.analyzers.trade_analyzer1.get_analysis())#grafica los trades individuales

    #graficar_retornos(resultados)#grafica los retornos de la estrategia

    #qsmetodo(resultados)#metodo para obtener informacion de los retornos de la estrategia(graficos utiles para la ui)
    performance = qsmetodo_reporte(resultados)#metodo para obtener solo las metricas
    #print(performance)






if __name__ == '__main__':
    main()
    