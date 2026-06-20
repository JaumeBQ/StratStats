import plotly.graph_objects as go
import backtrader as bt
import quantstats as qs
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
        marker_color='#45b3cc'
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
        line=dict(color='#f87171', dash='dash')
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



def ejecutar_backtrader(estrategia, datos, slipagge, comision, capital_inicial):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(estrategia)
    cerebro.adddata(datos)

    
    #analyzador personalizado
    cerebro.addanalyzer(TradeAnalyzer1, _name='trade_analyzer1')
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    #slipage y comisiones
    cerebro.broker.set_slippage_perc(perc = slipagge)
    cerebro.broker.setcommission(commission=comision )
    cerebro.broker.set_cash(capital_inicial)


    resultados = cerebro.run()
    #cerebro.plot()
    return resultados


def graficar_strat(trades, data):
    fig = go.Figure(data=[
        go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name='Precio'
        )
    ])
    
    fig.update_layout(
        xaxis=dict(rangeslider=dict(visible=True)),
        yaxis=dict(autorange=True, fixedrange=False)
    )
    start = data.index.min()
    end = data.index.max()
    filtered_trades = [t for t in trades if start <= t['datetime_open'] <= end or start <= t['datetime_close'] <= end]

    for trade in filtered_trades:
    #for trade in trades:
        fig.add_shape(type="line",
                      x0=trade['datetime_open'], y0=trade['price_open'],
                      x1=trade['datetime_close'], y1=trade['price_close'],
                      line=dict(color="#45b3cc", width=1)
        )

        pnl_text = f"PnL: {trade['pnl_final']:.2f}"
        fig.add_annotation(
            x=(trade['datetime_open'] + (trade['datetime_close'] - trade['datetime_open']) / 2),
            y=min(trade['price_open'], trade['price_close']) - 0.02 * (data['High'].max() - data['Low'].min()),
            text=pnl_text,
            showarrow=False,
            font=dict(color="#e8ecf4", size=10)
        )


    return fig


def graficos(returns, benchmark):
    drawdown = qs.stats.to_drawdown_series(returns)
    cumulative_returns = (1 + returns).cumprod() - 1

    benchmark_cumulative_returns = (1 + benchmark).cumprod() - 1
    benchmark_drawdown = qs.stats.to_drawdown_series(benchmark)


    # Crear el gráfico de retornos con Plotly
    # fig_returns = go.Figure()
    # fig_returns.add_trace(go.Scatter(x=returns.index, y=returns, mode='lines', name='AAPL Returns'))
    # fig_returns.update_layout(title='AAPL Returns Over Time', xaxis_title='Date', yaxis_title='Returns')
    
    # Crear el gráfico de retornos acumulados con Plotly
    fig_cumulative_returns = go.Figure()
    fig_cumulative_returns.add_trace(go.Scatter(x=cumulative_returns.index, y=cumulative_returns, mode='lines', name='Cumulative Returns', line=dict(color='#45b3cc')))
    fig_cumulative_returns.add_trace(go.Scatter(x=benchmark_cumulative_returns.index, y=benchmark_cumulative_returns, mode='lines', name='Benchmark Cumulative Returns', line=dict(color='#f87171')))
    fig_cumulative_returns.update_layout(title='Cumulative Returns Over Time', xaxis_title='Date', yaxis_title='Cumulative Returns')

    # Crear el gráfico de drawdown con Plotly
    fig_drawdown = go.Figure()
    fig_drawdown.add_trace(go.Scatter(x=drawdown.index, y=drawdown, mode='lines', name='Drawdown', line=dict(color='#45b3cc')))
    fig_drawdown.add_trace(go.Scatter(x=benchmark_drawdown.index, y=benchmark_drawdown, mode='lines', name='Benchmark Drawdown', line=dict(color='#f87171')))
    fig_drawdown.update_layout(title='Drawdown Over Time', xaxis_title='Date', yaxis_title='Drawdown')

     # Calcular Rolling Sharpe Ratio
    rolling_sharpe = qs.stats.rolling_sharpe(returns)
    rolling_sharpe_benchmark = qs.stats.rolling_sharpe(benchmark)
    fig_rolling_sharpe = go.Figure()
    fig_rolling_sharpe.add_trace(go.Scatter(x=rolling_sharpe.index, y=rolling_sharpe, mode='lines', name='Rolling Sharpe Ratio', line=dict(color='#45b3cc')))
    fig_rolling_sharpe.add_trace(go.Scatter(x=rolling_sharpe_benchmark.index, y=rolling_sharpe_benchmark, mode='lines', name='Benchmark Rolling Sharpe Ratio', line=dict(color='#f87171')))
    fig_rolling_sharpe.update_layout(title='Rolling Sharpe Ratio Over Time', xaxis_title='Date', yaxis_title='Rolling Sharpe Ratio')

    # Calcular Rolling Volatility
    rolling_volatility = qs.stats.rolling_volatility(returns)
    benchmark_rolling_volatility = qs.stats.rolling_volatility(benchmark)
    fig_rolling_volatility = go.Figure()
    fig_rolling_volatility.add_trace(go.Scatter(x=rolling_volatility.index, y=rolling_volatility, mode='lines', name='Rolling Volatility', line=dict(color='#45b3cc')))
    fig_rolling_volatility.add_trace(go.Scatter(x=benchmark_rolling_volatility.index, y=benchmark_rolling_volatility, mode='lines', name='Benchmark Rolling Volatility', line=dict(color='#f87171')))
    fig_rolling_volatility.update_layout(title='Rolling Volatility Over Time', xaxis_title='Date', yaxis_title='Rolling Volatility')

    # Calcular Win Rate
    win_rate = qs.stats.win_rate(returns)

    # Calcular Profit Factor
    profit_factor = qs.stats.profit_factor(returns)
    return fig_cumulative_returns, fig_drawdown, fig_rolling_sharpe, fig_rolling_volatility, win_rate, profit_factor

    #return fig_cumulative_returns, fig_drawdown

# # Mostrar los gráficos en Streamlit
# st.plotly_chart(fig_returns)
# st.plotly_chart(fig_drawdown)