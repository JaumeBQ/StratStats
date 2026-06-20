#falta iterar sobre estrategias
#
# Versión integrada con:
#   * subida de datos del usuario (data_loader / ui_helpers)
#   * capa visual: tema oscuro + KPIs en tarjetas + gráficos integrados (ui_style)

import streamlit as st
import SBacktesting as sb
import datos as dt
import pandas as pd
import backtrader as bt
import quantstats as qs
import datetime
import matplotlib.pyplot as plt
import ast

import backtest_utils as bu
import data_loader as dl
import ui_helpers as ui
import ui_style as theme

if "df_dict" not in st.session_state:
    st.session_state.df_dict = {}

if "df_dict2" not in st.session_state:
    st.session_state.df_dict2 = {}

if "df_dict3" not in st.session_state:
    st.session_state.df_dict3 = {}

if "total_returns" not in st.session_state:
    st.session_state.total_returns = None

if "show_individual_stats" not in st.session_state:
    st.session_state.show_individual_stats = False

if "strategy" not in st.session_state:
    st.session_state.strategy = None

if "start_index" not in st.session_state:
            st.session_state.start_index = 0

def metricas_retornos(returns, returns_benchmark):
    return bu.safe_metricas_retornos(returns, returns_benchmark)

def qsmetodo_reporte(estrategia_resultado):
    portfolio_stats = estrategia_resultado.analyzers.pyfolio.get_analysis()
    returns_data = portfolio_stats['returns']

    if not isinstance(returns_data, (pd.Series, pd.DataFrame)):
        returns = pd.Series(returns_data)
    else:
        returns = returns_data

    returns.index = pd.to_datetime(returns.index)
    return returns

def find_strategies_in_code(code):
    """
    Devuelve un diccionario con las clases que heredan de backtrader.Strategy
    encontradas en el código proporcionado.
    """
    parsed_code = ast.parse(code)
    strategies_found = {}

    for node in parsed_code.body:
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if getattr(base, 'attr', '') == 'Strategy':
                    local_ns = {}
                    exec(code, local_ns)
                    strategy_class = local_ns.get(node.name, None)
                    if strategy_class:
                        strategies_found[node.name] = strategy_class

    return strategies_found

st.set_page_config(page_title="Backtesting-StratStats", layout="wide")
theme.apply_theme()

st.title('Backtesting')

# --- Configuración (barra lateral) ---
# La temporalidad se elige primero porque la lista de activos disponibles
# (almacén + datos subidos por el usuario) depende de ella.
theme.sidebar_title("Configuración")
temporalidad = st.sidebar.selectbox("Timeframe", ['1min','5min','15min','30min', '1h', '4h','1d'])

Available_Tickers = ui.available_assets(
    temporalidad,
    extra=['AAPL', 'MSFT', 'AMZN', 'TSLA', 'S&P500', 'BTCUSD', 'EURUSD', 'XAUUSD', 'XAGUSD'],
)
Tikers = st.sidebar.multiselect("Tickers", Available_Tickers)
Available_Benchmarks = ['S&P500', 'USD_BOND','UK_BOND']
Benchmark = st.sidebar.selectbox("Benchmarks", Available_Benchmarks)
st.sidebar.write('Not all the tikers have the same range, you can see it in the instructions')
ini = st.sidebar.date_input("Start date",min_value=datetime.date(2000, 1, 1), max_value=datetime.date(2024, 12, 31))
end = st.sidebar.date_input("End date",min_value=datetime.date(2000, 1, 1), max_value=datetime.date(2024, 12, 31))

capital_inicial = st.sidebar.number_input("Initial Cash",  value=100000.0)
Slippage = st.sidebar.number_input("Slippage",  value=0.0)
Comission = st.sidebar.number_input("Comission",  value=0.0)

# --- Subida de datos propios (CSV con estructura OHLC) ---
if ui.data_upload_widget(temporalidad):
    st.rerun()


uploaded_file = st.file_uploader("Sube tu archivo .py con estrategias", type=["py"])
if uploaded_file is not None:
    code = uploaded_file.read().decode("utf-8")
    estrategias_disponibles = find_strategies_in_code(code)

    if estrategias_disponibles:
        estrategia_seleccionada = st.selectbox(
            "Elige tu estrategia",
            list(estrategias_disponibles.keys())
        )
        st.session_state.strategy = estrategias_disponibles[estrategia_seleccionada]

    else:
        st.warning("No se encontraron estrategias que hereden de backtrader.Strategy en el archivo subido.")

if st.button('Run Backtest', type="primary"):
    if st.session_state.strategy is None:
        st.error("Selecciona una estrategia antes de ejecutar el backtest.")
    elif not Tikers:
        st.error("Selecciona al menos un ticker para continuar.")
    else:
        st.session_state.df_dict = {}
        st.session_state.df_dict2 = {}
        st.session_state.df_dict3 = {}

        for tiker in Tikers:
            try:
                df = dl.load_asset(tiker, temporalidad, ini, end)
            except dl.DataError as exc:
                st.error(f"{tiker}: {exc}")
                continue

            try:
                data = bt.feeds.PandasData(dataname=df)
                estrategia_resultado = sb.ejecutar_backtrader(
                    st.session_state.strategy,
                    data,
                    Slippage,
                    Comission,
                    capital_inicial,
                )
            except Exception as exc:
                st.error(f"{tiker}: error al ejecutar la estrategia ({exc}).")
                continue

            try:
                resultados = estrategia_resultado[0]
            except (IndexError, TypeError) as exc:
                st.error(f"{tiker}: resultados inesperados del backtest ({exc}).")
                continue

            try:
                returns = qsmetodo_reporte(resultados)
            except Exception as exc:
                st.error(f"{tiker}: no se pudieron calcular los retornos ({exc}).")
                continue

            if getattr(returns, 'empty', False):
                st.warning(f"{tiker}: no se generaron retornos para la estrategia.")
                continue

            st.session_state.df_dict[tiker] = returns
            st.session_state.df_dict2[tiker] = resultados
            st.session_state.df_dict3[tiker] = df

        if not st.session_state.df_dict:
            st.warning("No se generaron resultados válidos para los tickers seleccionados.")
            st.session_state.total_returns = None
            st.session_state.show_individual_stats = False
        else:
            try:
                total_returns = pd.concat(st.session_state.df_dict.values(), axis=1).sum(axis=1)
            except ValueError as exc:
                st.error(f"Error al combinar los retornos ({exc}).")
                st.session_state.total_returns = None
                st.session_state.show_individual_stats = False
            else:
                df_data = pd.DataFrame(st.session_state.df_dict)
                df_data['Portfolio'] = total_returns
                df_data.dropna(inplace=True)
                csv_data = df_data.to_csv(index=True)
                st.download_button(
                    label="Download results",
                    data=csv_data,
                    file_name="results.csv",
                    mime="text/csv",
                )

                st.session_state.total_returns = total_returns
                st.session_state.show_individual_stats = False


if st.session_state.total_returns is not None:
    total_returns = st.session_state.total_returns
    theme.section("Métricas de la cartera", "Resultados agregados frente al benchmark")

    # Carga del benchmark con la misma capa de datos.
    portfolio_error = False
    benchmark_returns = None
    try:
        bench_df = dl.load_asset(Benchmark, temporalidad, ini, end)
        benchmark_returns = bench_df['Close'].pct_change().dropna()
    except dl.DataError as exc:
        st.error(f"Benchmark no disponible: {exc}")
        portfolio_error = True

    if portfolio_error or benchmark_returns is None or benchmark_returns.empty:
        st.session_state.total_returns = None
        st.session_state.show_individual_stats = False
    else:
        with st.expander('Show  metrics'):
                try:
                    dff2 = qs.reports.metrics(total_returns, mode='full', display=False)
                except Exception as exc:
                    st.error(f"Portfolio: no se pudieron generar las métricas ({exc}).")
                else:
                    st.write('Portfolio')
                    st.write(dff2.T)
                try:
                    dff3 = qs.reports.metrics(benchmark_returns, mode='full', display=False)
                except Exception as exc:
                    st.error(f"Benchmark: no se pudieron generar las métricas ({exc}).")
                else:
                    st.write('Benchmark')
                    st.write(dff3.T)

        try:
            mean_return, std_return, sharpe_ratio, drawdown, percentiles, cagr, cagr_benchmark, drawdown_benchmark, total_return, total_return_bench = metricas_retornos(total_returns, benchmark_returns)
        except bu.BacktestError as exc:
            st.error(f"Portfolio: {exc}")
        except Exception as exc:
            st.error(f"Portfolio: error al calcular métricas ({exc}).")
        else:
            theme.kpi_grid([
                {"label": "Rentabilidad total", "value": f"{total_return*100:.2f}%",
                 "delta": f"Bench {total_return_bench*100:.2f}%", "positive": total_return >= total_return_bench},
                {"label": "CAGR", "value": f"{cagr*100:.2f}%",
                 "delta": f"Bench {cagr_benchmark*100:.2f}%", "positive": cagr >= cagr_benchmark},
                {"label": "Ratio de Sharpe", "value": f"{sharpe_ratio:.2f}",
                 "positive": sharpe_ratio >= 1},
                {"label": "Máx. drawdown", "value": f"{drawdown*100:.2f}%",
                 "delta": f"Bench {drawdown_benchmark*100:.2f}%", "positive": drawdown >= drawdown_benchmark},
                {"label": "Volatilidad (std)", "value": f"{std_return*100:.2f}%"},
            ])

        try:
            fig_returns, fig_drawdown, fig_rolling_sharpe, fig_rolling_volatility, win_rate, profit_factor = sb.graficos(total_returns, benchmark_returns)
        except Exception as exc:
            st.error(f"Portfolio: no se pudieron generar los gráficos ({exc}).")
            st.session_state.show_individual_stats = False
        else:
            theme.kpi_grid([
                {"label": "Win rate", "value": f"{win_rate:.1%}"},
                {"label": "Profit factor", "value": f"{profit_factor:.2f}", "positive": profit_factor >= 1},
            ])
            co1, co2 = st.columns(2)
            co1.plotly_chart(theme.style_plotly(fig_returns), key="portfolio_returns")
            co2.plotly_chart(theme.style_plotly(fig_drawdown), key="portfolio_drawdown")
            co1.plotly_chart(theme.style_plotly(fig_rolling_sharpe), key="portfolio_rolling_sharpe")
            co2.plotly_chart(theme.style_plotly(fig_rolling_volatility), key="portfolio_rolling_volatility")


    if st.button('Show individual stats'):

        st.session_state.show_individual_stats = True

        st.rerun()


if st.session_state.show_individual_stats:

    for key, value in st.session_state.df_dict.items():

        tiker = key
        theme.section(f"Backtesting · {tiker}")
        returns = st.session_state.df_dict[tiker]
        resultados = st.session_state.df_dict2[tiker]
        df = st.session_state.df_dict3[tiker]

        try:
            mean_return, std_return, sharpe_ratio, drawdown, percentiles,cagr, cagr_benchmark, drawdown_benchmark, total_return, total_return_bench = metricas_retornos(returns, benchmark_returns)
        except bu.BacktestError as exc:
            st.error(f"{tiker}: {exc}")
            continue
        theme.kpi_grid([
            {"label": "Rentabilidad total", "value": f"{total_return*100:.2f}%",
             "delta": f"Bench {total_return_bench*100:.2f}%", "positive": total_return >= total_return_bench},
            {"label": "CAGR", "value": f"{cagr*100:.2f}%",
             "delta": f"Bench {cagr_benchmark*100:.2f}%", "positive": cagr >= cagr_benchmark},
            {"label": "Ratio de Sharpe", "value": f"{sharpe_ratio:.2f}", "positive": sharpe_ratio >= 1},
            {"label": "Máx. drawdown", "value": f"{drawdown*100:.2f}%",
             "delta": f"Bench {drawdown_benchmark*100:.2f}%", "positive": drawdown >= drawdown_benchmark},
            {"label": "Volatilidad (std)", "value": f"{std_return*100:.2f}%"},
        ])

        col1, col2 = st.columns(2)

        try:
            fig = sb.graficar_trades4(resultados.analyzers.trade_analyzer1.get_analysis())
        except Exception as exc:
            st.error(f"{tiker}: no se pudieron graficar los trades ({exc}).")
        else:
            col2.plotly_chart(theme.style_plotly(fig))

        window_size = 200
        if not isinstance(df.index, pd.DatetimeIndex):
            st.error(f"{tiker}: se requieren índices de tiempo para mostrar el gráfico deslizante.")
            continue

        if len(df) <= window_size:
            st.warning(f"{tiker}: se necesitan al menos {window_size + 1} registros para la vista dinámica.")
            continue

        try:
            start = df.index.min().to_pydatetime()
            end_index2 = df.index[len(df)-window_size-1].to_pydatetime()
            default_value = df.index[len(df)-window_size-1].to_pydatetime()
        except Exception as exc:
            st.error(f"{tiker}: error al preparar el selector de fechas ({exc}).")
            continue

        try:
            start_date = st.slider(
                "Start Date",
                min_value=start,
                max_value=end_index2,
                value=default_value,
                format="Y-m-d H:M",
                key=f"{tiker}_slider",
            )
        except Exception as exc:
            st.error(f"{tiker}: no se pudo crear el control deslizante ({exc}).")
            continue

        try:
            start_index = df.index.get_loc(start_date)
            end_index = min(start_index + window_size, len(df) - 1)
            end_date = df.index[end_index].to_pydatetime()
            subset = df.loc[start_date:end_date]
        except Exception as exc:
            st.error(f"{tiker}: error al construir la ventana temporal ({exc}).")
            continue

        try:
            fig_cotizaciones2 = sb.graficar_strat(resultados.analyzers.trade_analyzer1.get_analysis(), subset)
        except Exception as exc:
            st.error(f"{tiker}: no se pudo generar el gráfico de precios ({exc}).")
        else:
            col1.plotly_chart(theme.style_plotly(fig_cotizaciones2))


        with st.expander(f'Show trades {tiker}'):
            try:
                trades = resultados.analyzers.trade_analyzer1.get_analysis()
                df_trades = pd.DataFrame(trades)
                if 'datetime_open' in df_trades.columns:
                    df_trades.set_index('datetime_open', inplace=True)
                st.write(df_trades)
            except Exception as exc:
                st.error(f"{tiker}: no se pudieron mostrar los trades ({exc}).")

        with st.expander(f'Show advanced {tiker} metrics'):
                try:
                    dff = qs.reports.metrics(returns, mode='full', display=False)
                except Exception as exc:
                    st.error(f"{tiker}: no se pudieron generar las métricas ({exc}).")
                else:
                    st.write(dff.T)

        with st.expander(f'Show cumulative returns {tiker}'):
                try:
                    fig_returns, fig_drawdown, fig_rolling_sharpe, fig_rolling_volatility, win_rate, profit_factor = sb.graficos(returns, benchmark_returns)
                except Exception as exc:
                    st.error(f"{tiker}: no se pudieron generar los gráficos ({exc}).")
                else:
                    theme.kpi_grid([
                        {"label": "Win rate", "value": f"{win_rate:.1%}"},
                        {"label": "Profit factor", "value": f"{profit_factor:.2f}", "positive": profit_factor >= 1},
                    ])
                    co1, co2 = st.columns(2)
                    co1.plotly_chart(theme.style_plotly(fig_returns))
                    co2.plotly_chart(theme.style_plotly(fig_drawdown))
                    co1.plotly_chart(theme.style_plotly(fig_rolling_sharpe))
                    co2.plotly_chart(theme.style_plotly(fig_rolling_volatility))
