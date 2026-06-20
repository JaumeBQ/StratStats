"""
Página «Optimización y análisis de sensibilidad» de StratStats.

Capa fina de interfaz sobre ``data_loader``, ``strategy_loader`` y
``optimization``. Flujo:
    * subir datos propios o usar los del almacén,
    * cargar una estrategia y elegir QUÉ parámetros optimizar (1..N), con su
      rango y salto (unidades o %),
    * lanzar un único barrido sobre todas las combinaciones,
    * en la visualización: elegir la métrica objetivo, el modo de agregación
      (mejor / media) y qué parámetro ver en la curva y qué pareja en el mapa
      de calor, sin necesidad de re-ejecutar.
"""

import datetime

import streamlit as st

import data_loader as dl
import optimization as op
import strategy_loader as sl
import ui_helpers as ui
import ui_style as theme

st.set_page_config(page_title="Optimization - StratStats", layout="wide")
theme.apply_theme()

_DEFAULTS = {
    "opt_strategies": {},     # nombre -> clase
    "opt_results": None,      # DataFrame del barrido
    "opt_param_names": [],     # parámetros optimizados (orden)
}
for k, v in _DEFAULTS.items():
    st.session_state.setdefault(k, v)

DEFAULT_TICKERS = ["AAPL", "MSFT", "AMZN", "TSLA", "S&P500",
                   "BTCUSD", "EURUSD", "XAUUSD", "XAGUSD"]

st.title("Optimización y análisis de sensibilidad")

# --------------------------------------------------------------------------- #
# Barra lateral: configuración del backtest
# --------------------------------------------------------------------------- #
with st.sidebar:
    theme.sidebar_title("Configuración")
    timeframe = st.selectbox(
        "Temporalidad", ["1min", "5min", "15min", "30min", "1h", "4h", "1d"], index=6)
    assets = ui.available_assets(timeframe, extra=DEFAULT_TICKERS)
    ticker = st.selectbox("Activo", assets) if assets else None
    st.caption("No todos los activos cubren el mismo rango de fechas.")
    ini = st.date_input("Fecha inicial", min_value=datetime.date(2000, 1, 1),
                        max_value=datetime.date(2024, 12, 31),
                        value=datetime.date(2018, 1, 1))
    end = st.date_input("Fecha final", min_value=datetime.date(2000, 1, 1),
                        max_value=datetime.date(2024, 12, 31),
                        value=datetime.date(2024, 12, 31))
    capital = st.number_input("Capital inicial", min_value=0.0, value=100_000.0, step=1000.0)
    comision = st.number_input("Comisión (proporción, ej. 0.001)", min_value=0.0,
                               value=0.0, step=0.0005, format="%.4f")
    slippage = st.number_input("Slippage (proporción)", min_value=0.0,
                               value=0.0, step=0.0005, format="%.4f")

if ui.data_upload_widget(timeframe):
    st.rerun()

# --------------------------------------------------------------------------- #
# Carga de la estrategia
# --------------------------------------------------------------------------- #
uploaded = st.file_uploader("Sube tu archivo .py con estrategias", type=["py"])
if uploaded is not None:
    code = uploaded.read().decode("utf-8", errors="replace")
    risky = sl.scan_for_risky_imports(code)
    if risky:
        st.warning(
            "⚠️ La estrategia importa módulos potencialmente peligrosos: "
            f"{', '.join(risky)}. Ejecútala solo si confías en su origen.")
    try:
        st.session_state.opt_strategies = sl.find_strategies_in_code(code)
    except sl.StrategyLoadError as exc:
        st.session_state.opt_strategies = {}
        st.error(str(exc))

strategies = st.session_state.opt_strategies
if strategies:
    name = st.selectbox("Elige tu estrategia", list(strategies.keys()))
    strategy_class = strategies[name]

    try:
        param_names = op.get_param_names(strategy_class)
    except op.OptimizationError as exc:
        st.error(str(exc)); param_names = []

    if not param_names:
        st.info("La estrategia seleccionada no declara parámetros optimizables.")
    else:
        # ------------------------------------------------------------------- #
        # Selección de los parámetros a optimizar (1..N)
        # ------------------------------------------------------------------- #
        theme.section("Parámetros a optimizar")
        st.caption("Los parámetros que no selecciones quedan en su valor por defecto.")
        chosen = st.multiselect("Parámetros", param_names)

        param_grid, config_ok = {}, True
        for pname in chosen:
            try:
                default = float(op.default_param_value(strategy_class, pname))
            except (TypeError, ValueError):
                default = 0.0
            st.markdown(f"**{pname}**  ·  valor por defecto: `{default:g}`")
            c1, c2, c3, c4 = st.columns(4)
            v_ini = c1.number_input("Inicial", value=default, key=f"{pname}_ini")
            v_fin = c2.number_input("Final", value=default + 10, key=f"{pname}_fin")
            v_step = c3.number_input("Salto", value=1.0, min_value=0.0, key=f"{pname}_step")
            v_type = c4.selectbox("Tipo de salto", ["unidades", "%"], key=f"{pname}_type")
            try:
                values = op.build_param_values(
                    v_ini, v_fin, v_step, "pct" if v_type == "%" else "abs")
                st.caption(f"{len(values)} valores: {values}")
                param_grid[pname] = values
            except op.OptimizationError as exc:
                st.error(f"Parámetro «{pname}»: {exc}"); config_ok = False

        if param_grid:
            n_comb = op.count_combinations(param_grid)
            msg = f"Se ejecutarán **{n_comb}** backtests (una combinación por punto)."
            (st.warning if n_comb > 1000 else st.info)(msg)

        # ------------------------------------------------------------------- #
        # Ejecución del barrido
        # ------------------------------------------------------------------- #
        if st.button("Ejecutar optimización", type="primary"):
            if not param_grid:
                st.error("Selecciona al menos un parámetro y define su rango.")
            elif not config_ok:
                st.error("Corrige la configuración de los parámetros antes de ejecutar.")
            elif ticker is None:
                st.error("No hay ningún activo disponible para esta temporalidad.")
            else:
                try:
                    feed = dl.make_feed(dl.load_asset(ticker, timeframe, ini, end))
                    with st.spinner(f"Ejecutando {op.count_combinations(param_grid)} backtests…"):
                        results = op.run_optimization(
                            strategy_class, feed, param_grid,
                            cash=capital, commission=comision, slippage=slippage)
                except (dl.DataError, op.OptimizationError) as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001 - red de seguridad
                    st.error(f"Error inesperado durante la optimización: {exc}")
                else:
                    st.session_state.opt_results = results
                    st.session_state.opt_param_names = list(param_grid.keys())
                    st.success("Optimización completada.")

# --------------------------------------------------------------------------- #
# Resultados y visualizaciones (sin re-ejecutar el barrido)
# --------------------------------------------------------------------------- #
results = st.session_state.opt_results
opt_names = st.session_state.opt_param_names
if results is not None and opt_names:
    theme.section("Resultados del barrido", "Métrica, agregación y visualizaciones")

    col_obj, col_agg = st.columns(2)
    objective = col_obj.selectbox("Métrica objetivo", list(op.OBJECTIVES.keys()))
    agg = col_agg.radio(
        "Agregación de los demás parámetros", op.AGGREGATIONS, horizontal=True,
        help="«mejor»: el mejor resultado posible variando los demás parámetros "
             "(útil para localizar el óptimo). «media»: el resultado medio "
             "(útil para medir la sensibilidad/robustez).")

    try:
        best = op.best_row(results, objective)
        obj_col = op.OBJECTIVES[objective].column
        cfg = ", ".join(f"{n} = {best[n]:g}" for n in opt_names)
        theme.kpi_grid([{"label": "Óptimo · " + cfg, "value": f"{best[obj_col]:.4f}",
                         "delta": objective, "positive": True}])
    except op.OptimizationError as exc:
        st.warning(str(exc))

    st.dataframe(results, use_container_width=True)

    # --- Curva: un parámetro a elegir ---
    st.markdown("#### Curva (un parámetro)")
    curve_param = st.selectbox("Parámetro para la curva", opt_names, key="curve_param")
    try:
        st.plotly_chart(
            theme.style_plotly(op.make_curve_figure(results, curve_param, objective, agg)),
            use_container_width=True)
    except op.OptimizationError as exc:
        st.warning(str(exc))

    # --- Mapa de calor: pareja a elegir (requiere >= 2 parámetros optimizados) ---
    if len(opt_names) >= 2:
        st.markdown("#### Mapa de calor (dos parámetros)")
        h1, h2 = st.columns(2)
        p1 = h1.selectbox("Eje X", opt_names, index=0, key="heat_p1")
        p2_options = [p for p in opt_names if p != p1]
        p2 = h2.selectbox("Eje Y", p2_options, index=0, key="heat_p2")
        try:
            st.plotly_chart(
                theme.style_plotly(op.make_heatmap_figure(results, p1, p2, objective, agg)),
                use_container_width=True)
        except op.OptimizationError as exc:
            st.warning(str(exc))
    else:
        st.caption("Optimiza al menos dos parámetros para ver el mapa de calor.")

    st.download_button(
        "Descargar resultados (CSV)",
        data=results.to_csv(index=False).encode("utf-8"),
        file_name="optimizacion.csv", mime="text/csv")
