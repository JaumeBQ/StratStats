"""
ui_style.py
===========
Capa de estilo (CSS) y componentes de interfaz reutilizables para StratStats.

Uso en cada página, justo DESPUÉS de st.set_page_config(...):

    import ui_style as theme
    theme.apply_theme()

Y para los componentes:

    theme.section("Métricas de la cartera", "Resultados agregados del backtest")
    theme.kpi_grid([
        {"label": "Rentabilidad total", "value": "+142 %", "delta": "vs +37 % bench", "positive": True},
        {"label": "Sharpe",             "value": "1.34"},
        {"label": "Máx. drawdown",      "value": "-21 %", "positive": False},
    ])
    theme.table(mi_dataframe)

No usa ninguna librería externa: solo CSS y HTML inyectados con st.markdown.
"""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------- #
# CSS
# --------------------------------------------------------------------------- #
_CSS = """
<style>
/* ====== 1. TOKENS DE DISEÑO ====== */
:root {
  --bg:          #121826;   /* fondo de la app (slate, no negro) */
  --surface:     #19212f;   /* paneles / sidebar */
  --surface-2:   #202a3a;   /* tarjetas */
  --surface-3:   #29354a;   /* hover / inputs */
  --border:      #36445b;   /* bordes visibles */
  --border-soft: #28323f;   /* bordes sutiles */
  --text:        #f1f4fa;   /* texto principal */
  --text-muted:  #aab6c9;   /* texto secundario */
  --text-dim:    #6b7a92;   /* texto terciario */
  --accent:      #45b3cc;   /* acento (teal) */
  --accent-2:    #5b8fd6;   /* acento (azul) */
  --accent-grad: linear-gradient(135deg, #31859C 0%, #4F81BD 100%);
  --success:     #34d399;
  --danger:      #f87171;
  --warning:     #fbbf24;
  --radius:      14px;
  --radius-sm:   10px;
  --shadow:      0 1px 2px rgba(0,0,0,.45), 0 10px 30px -12px rgba(0,0,0,.55);
  --font:        -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono:   ui-monospace, "SF Mono", "Cascadia Code", "JetBrains Mono", Menlo, Consolas, monospace;
}

/* ====== 2. BASE Y CONTENEDOR PRINCIPAL ====== */
.stApp {
  background:
    radial-gradient(1100px 560px at 12% -8%, rgba(91,143,214,.12), transparent 58%),
    radial-gradient(900px 520px at 100% -5%, rgba(69,179,204,.10), transparent 55%),
    var(--bg);
  color: var(--text); font-family: var(--font);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }
.block-container { padding: 2.4rem 2.2rem 4rem; max-width: 1240px; }
a { color: var(--accent); }
hr { border-color: var(--border-soft); }

/* ====== 3. TIPOGRAFÍA Y JERARQUÍA ====== */
h1, h2, h3, h4 { color: var(--text); font-weight: 700; letter-spacing: -0.02em; }
h1 { font-size: 2rem; }
h2 { font-size: 1.4rem; margin-top: 0.4rem; }
h3 { font-size: 1.12rem; }
[data-testid="stCaptionContainer"], .stCaption, small { color: var(--text-muted) !important; }

/* ====== 4. SIDEBAR (FILTROS) ====== */
[data-testid="stSidebar"] {
  background: var(--surface);
  border-right: 1px solid var(--border-soft);
}
[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2 { font-size: 1.1rem; }
[data-testid="stSidebar"] label { color: var(--text-muted) !important; font-size: .82rem; font-weight: 600; }
.ss-sidebar-title {
  text-transform: uppercase; letter-spacing: .12em; font-size: .72rem;
  font-weight: 700; color: var(--text-dim); margin: 1.2rem 0 .4rem;
}

/* ====== 5. INPUTS (selectbox, number, date, multiselect, uploader, slider) ====== */
[data-baseweb="select"] > div,
[data-baseweb="input"] {
  background: var(--surface-3) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text) !important;
}
[data-baseweb="select"] > div:hover,
[data-baseweb="input"]:hover { border-color: var(--accent) !important; }
[data-baseweb="select"] > div:focus-within,
[data-baseweb="input"]:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(58,166,192,.18) !important;
}
input, textarea { color: var(--text) !important; }
/* etiquetas (chips) del multiselect */
[data-baseweb="tag"] {
  background: rgba(79,129,189,.18) !important;
  border: 1px solid rgba(79,129,189,.45) !important;
  color: #cfe0f5 !important; border-radius: 8px !important;
}
/* file uploader */
[data-testid="stFileUploaderDropzone"] {
  background: var(--surface-2); border: 1px dashed var(--border);
  border-radius: var(--radius);
}
/* slider */
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] { background: var(--accent) !important; }

/* ====== 6. BOTONES DE ACCIÓN ====== */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius: var(--radius-sm); border: 1px solid var(--border);
  background: var(--surface-3); color: var(--text);
  font-weight: 600; padding: .5rem 1.1rem; transition: all .15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  border-color: var(--accent); transform: translateY(-1px);
  box-shadow: var(--shadow);
}
/* botón primario (type="primary") */
.stButton > button[kind="primary"] {
  background: var(--accent-grad); border: none; color: #fff;
  box-shadow: 0 6px 18px -6px rgba(49,133,156,.6);
}
.stButton > button[kind="primary"]:hover { filter: brightness(1.08); }

/* ====== 7. MÉTRICAS NATIVAS (st.metric) ====== */
[data-testid="stMetric"] {
  background: var(--surface-2); border: 1px solid var(--border-soft);
  border-radius: var(--radius); padding: 1rem 1.1rem; box-shadow: var(--shadow);
}
[data-testid="stMetricLabel"] { color: var(--text-muted); font-weight: 600; }
[data-testid="stMetricValue"] { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }

/* ====== 8. TARJETAS KPI (componente propio) ====== */
.ss-kpi-grid {
  display: grid; gap: 14px; margin: .5rem 0 1.4rem;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
}
.ss-kpi {
  position: relative; overflow: hidden;
  background: linear-gradient(160deg, var(--surface-2) 0%, #1b2433 100%);
  border: 1px solid var(--border); border-radius: var(--radius);
  padding: 1.15rem 1.2rem 1.1rem; box-shadow: var(--shadow);
  transition: border-color .18s ease, transform .18s ease, box-shadow .18s ease;
}
.ss-kpi:hover {
  border-color: var(--accent); transform: translateY(-3px);
  box-shadow: 0 14px 34px -14px rgba(69,179,204,.45);
}
.ss-kpi::before {
  content: ""; position: absolute; left: 0; right: 0; top: 0; height: 3px;
  background: var(--accent-grad);
}
.ss-kpi-label {
  color: var(--text-muted); font-size: .76rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .07em;
}
.ss-kpi-value {
  color: #fff; font-family: var(--font-mono); font-variant-numeric: tabular-nums;
  font-size: 1.85rem; font-weight: 700; margin-top: .45rem; line-height: 1.05;
}
.ss-kpi-delta {
  display: inline-flex; align-items: center; gap: .3rem;
  font-size: .8rem; font-weight: 600; margin-top: .5rem;
  padding: .12rem .5rem; border-radius: 999px;
}
.ss-kpi-delta.up   { color: var(--success); background: rgba(52,211,153,.12); }
.ss-kpi-delta.down { color: var(--danger);  background: rgba(248,113,113,.12); }
.ss-kpi-delta.flat { color: var(--text-dim); background: rgba(107,122,146,.14); }

/* ====== 9. SECCIÓN / CABECERA DE BLOQUE ====== */
.ss-section { margin: 1.6rem 0 .4rem; }
.ss-section h3 { margin: 0; font-size: 1.15rem; }
.ss-section p { margin: .15rem 0 0; color: var(--text-muted); font-size: .9rem; }
.ss-section-bar { height: 2px; width: 38px; background: var(--accent-grad);
  border-radius: 2px; margin-bottom: .5rem; }

/* ====== 10. TABLAS ====== */
/* contenedor de st.dataframe / st.table */
[data-testid="stDataFrame"], [data-testid="stTable"] {
  border: 1px solid var(--border-soft); border-radius: var(--radius); overflow: hidden;
}
/* tabla HTML propia (theme.table) */
.ss-table-wrap { overflow-x: auto; border: 1px solid var(--border-soft);
  border-radius: var(--radius); }
table.ss-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
table.ss-table th {
  background: var(--surface-3); color: var(--text-muted); text-align: right;
  font-weight: 600; padding: .6rem .9rem; position: sticky; top: 0;
  border-bottom: 1px solid var(--border);
}
table.ss-table th:first-child, table.ss-table td:first-child { text-align: left; }
table.ss-table td {
  padding: .55rem .9rem; text-align: right; color: var(--text);
  font-family: var(--font-mono); font-variant-numeric: tabular-nums;
  border-bottom: 1px solid var(--border-soft);
}
table.ss-table tr:last-child td { border-bottom: none; }
table.ss-table tbody tr:hover td { background: rgba(79,129,189,.07); }

/* ====== 11. EXPANDERS ====== */
[data-testid="stExpander"] {
  border: 1px solid var(--border-soft); border-radius: var(--radius);
  background: var(--surface); overflow: hidden;
}
[data-testid="stExpander"] summary:hover { color: var(--accent); }

/* ====== 12. ALERTAS ====== */
[data-testid="stAlert"] { border-radius: var(--radius-sm); border: 1px solid var(--border-soft); }

/* ====== 13. PESTAÑAS (tabs) ====== */
[data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--border-soft); }
[data-baseweb="tab"] { color: var(--text-muted); }
[data-baseweb="tab"][aria-selected="true"] { color: var(--text); }
[data-baseweb="tab-highlight"] { background: var(--accent) !important; }

/* ====== 14. GRÁFICOS (Plotly) INTEGRADOS ====== */
[data-testid="stPlotlyChart"] {
  background: var(--surface-2); border: 1px solid var(--border-soft);
  border-radius: var(--radius); padding: .5rem; box-shadow: var(--shadow);
}

/* ====== 15. CABECERA DE MARCA (opcional) ====== */
.ss-hero { display: flex; align-items: center; gap: .9rem; margin-bottom: 1.4rem; }
.ss-hero-badge { width: 42px; height: 42px; border-radius: 12px;
  background: var(--accent-grad); box-shadow: 0 6px 18px -6px rgba(49,133,156,.7); }
.ss-hero h1 { margin: 0; }
.ss-hero p { margin: 0; color: var(--text-muted); }

/* ====== 16. BARRA DE SCROLL ====== */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: var(--surface-3); border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: var(--border); }
::-webkit-scrollbar-track { background: transparent; }

/* ====== 17. RESPONSIVE ====== */
@media (max-width: 640px) {
  .block-container { padding: 1.4rem 1rem 3rem; }
  .ss-kpi-grid { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
  .ss-kpi-value { font-size: 1.4rem; }
}
</style>
"""


# --------------------------------------------------------------------------- #
# Inyección del tema
# --------------------------------------------------------------------------- #
def apply_theme() -> None:
    """Inyecta el CSS del tema. Llamar en cada página tras set_page_config()."""
    st.markdown(_CSS, unsafe_allow_html=True)


inject_css = apply_theme  # alias


# --------------------------------------------------------------------------- #
# Componentes (constructores de HTML puros + envoltorios de Streamlit)
# --------------------------------------------------------------------------- #
def _esc(value) -> str:
    return html.escape(str(value))


def _delta_class(positive) -> str:
    if positive is True:
        return "up"
    if positive is False:
        return "down"
    return "flat"


def _kpi_card_html(label, value, delta=None, positive=None) -> str:
    parts = [
        '<div class="ss-kpi">',
        f'<div class="ss-kpi-label">{_esc(label)}</div>',
        f'<div class="ss-kpi-value">{_esc(value)}</div>',
    ]
    if delta is not None:
        parts.append(f'<div class="ss-kpi-delta {_delta_class(positive)}">{_esc(delta)}</div>')
    parts.append("</div>")
    return "".join(parts)


def _kpi_grid_html(items: list[dict]) -> str:
    cards = "".join(
        _kpi_card_html(it.get("label", ""), it.get("value", ""),
                       it.get("delta"), it.get("positive"))
        for it in items
    )
    return f'<div class="ss-kpi-grid">{cards}</div>'


def _section_html(title, subtitle=None) -> str:
    sub = f'<p>{_esc(subtitle)}</p>' if subtitle else ""
    return (f'<div class="ss-section"><div class="ss-section-bar"></div>'
            f'<h3>{_esc(title)}</h3>{sub}</div>')


def _hero_html(title, subtitle=None) -> str:
    sub = f'<p>{_esc(subtitle)}</p>' if subtitle else ""
    return (f'<div class="ss-hero"><div class="ss-hero-badge"></div>'
            f'<div><h1>{_esc(title)}</h1>{sub}</div></div>')


def _table_html(df: pd.DataFrame, index: bool = False) -> str:
    inner = df.to_html(classes="ss-table", border=0, index=index, escape=True)
    return f'<div class="ss-table-wrap">{inner}</div>'


# ---- Envoltorios públicos (renderizan en la página) ---- #
def kpi_grid(items: list[dict]) -> None:
    """Rejilla responsive de tarjetas KPI.

    items: lista de dicts con claves 'label', 'value' y, opcionalmente,
    'delta' y 'positive' (True=verde, False=rojo, None=neutro).
    """
    st.markdown(_kpi_grid_html(items), unsafe_allow_html=True)


def kpi_card(label, value, delta=None, positive=None) -> None:
    """Una sola tarjeta KPI."""
    st.markdown(f'<div class="ss-kpi-grid">{_kpi_card_html(label, value, delta, positive)}</div>',
                unsafe_allow_html=True)


def section(title, subtitle=None) -> None:
    """Cabecera de sección con barra de acento."""
    st.markdown(_section_html(title, subtitle), unsafe_allow_html=True)


def hero(title, subtitle=None) -> None:
    """Cabecera de marca (para la página de inicio)."""
    st.markdown(_hero_html(title, subtitle), unsafe_allow_html=True)


def table(df: pd.DataFrame, index: bool = False) -> None:
    """Tabla HTML con el estilo del tema (ideal para tablas pequeñas/medianas)."""
    st.markdown(_table_html(df, index=index), unsafe_allow_html=True)


def sidebar_title(text) -> None:
    """Etiqueta de grupo dentro de la barra lateral."""
    st.sidebar.markdown(f'<div class="ss-sidebar-title">{_esc(text)}</div>',
                        unsafe_allow_html=True)


def style_plotly(fig):
    """Adapta una figura Plotly al tema oscuro (fondo transparente).

    Úsalo opcionalmente sobre tus figuras: fig = theme.style_plotly(fig).
    """
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e8ecf4"),
        margin=dict(l=40, r=20, t=50, b=40),
    )
    fig.update_xaxes(gridcolor="#263141", zerolinecolor="#263141")
    fig.update_yaxes(gridcolor="#263141", zerolinecolor="#263141")
    return fig
