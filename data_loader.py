"""
data_loader.py
==============
Capa de acceso a datos de StratStats.

Responsabilidades:
    * Leer ficheros CSV de precios del almacén local ``datos/<temporalidad>/<ticker>.csv``.
    * Validar y normalizar la estructura OHLC, sea cual sea el formato de entrada.
    * Permitir que el usuario suba sus propios datos y guardarlos en el almacén.
    * Construir el *data feed* que consume Backtrader.

El módulo es independiente de Streamlit: solo trabaja con rutas, ficheros
y ``DataFrame`` de pandas, de modo que puede probarse de forma aislada.
"""

from __future__ import annotations

import os
import re
from typing import Iterable

import pandas as pd

# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #
BASE_DIR = "datos"

#: Temporalidades admitidas por la aplicación.
TIMEFRAMES = ("1min", "5min", "15min", "30min", "1h", "4h", "1d")

#: Columnas OHLC obligatorias (forma canónica interna).
OHLC_COLS = ("Open", "High", "Low", "Close")

#: Posibles nombres de la columna de fecha/hora en un fichero de entrada.
_DATETIME_ALIASES = ("datetime", "date", "fecha", "time", "timestamp")

#: Alias admitidos para cada columna canónica (en minúsculas, sin acentos).
_COLUMN_ALIASES = {
    "Open": ("open", "apertura", "o"),
    "High": ("high", "maximo", "max", "h"),
    "Low": ("low", "minimo", "min", "l"),
    "Close": ("close", "cierre", "c", "adj close", "adj_close"),
    "Volume": ("volume", "volumen", "vol", "v"),
}


class DataError(Exception):
    """Error controlado en la carga, validación o guardado de datos."""


# --------------------------------------------------------------------------- #
# Utilidades internas
# --------------------------------------------------------------------------- #
def _norm(text: str) -> str:
    """Normaliza un nombre de columna: minúsculas y sin espacios sobrantes."""
    return str(text).strip().lower()


def _find_datetime_column(columns: Iterable[str]) -> str | None:
    """Devuelve el nombre de la columna de fecha/hora, o ``None`` si no existe."""
    norm = {_norm(c): c for c in columns}
    for alias in _DATETIME_ALIASES:
        if alias in norm:
            return norm[alias]
    return None


def _map_ohlc_columns(columns: Iterable[str]) -> dict[str, str]:
    """Asocia cada columna canónica con su nombre real en el fichero."""
    norm = {_norm(c): c for c in columns}
    mapping: dict[str, str] = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in norm:
                mapping[canonical] = norm[alias]
                break
    return mapping


def validate_ohlc_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Valida y normaliza un ``DataFrame`` de precios.

    Acepta distintos nombres de columnas (mayúsculas/minúsculas, español/inglés)
    y una columna de fecha con varios alias posibles. Devuelve un ``DataFrame``
    con índice ``DatetimeIndex`` y columnas ``Open, High, Low, Close, Volume``.

    Lanza :class:`DataError` con un mensaje claro si la estructura no es válida.
    """
    if df is None or df.empty:
        raise DataError("El fichero no contiene datos.")

    df = df.copy()

    # 1) Localizar y fijar el índice temporal.
    if isinstance(df.index, pd.DatetimeIndex):
        df.index.name = "datetime"
    else:
        dt_col = _find_datetime_column(df.columns)
        if dt_col is None:
            raise DataError(
                "No se encontró ninguna columna de fecha "
                "(se esperaba una llamada 'Date' o 'datetime')."
            )
        df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")
        df = df.dropna(subset=[dt_col])
        df = df.set_index(dt_col)
        df.index.name = "datetime"

    # 2) Mapear las columnas OHLC(V).
    mapping = _map_ohlc_columns(df.columns)
    missing = [c for c in OHLC_COLS if c not in mapping]
    if missing:
        raise DataError(
            "Faltan columnas obligatorias en los datos: "
            + ", ".join(missing)
            + ". Se requiere la estructura OHLC (Open, High, Low, Close)."
        )

    canonical = pd.DataFrame(index=df.index)
    for col, source in mapping.items():
        canonical[col] = pd.to_numeric(df[source], errors="coerce")

    # 3) El volumen es opcional: si no existe, se rellena con cero.
    if "Volume" not in canonical.columns:
        canonical["Volume"] = 0.0

    canonical = canonical[["Open", "High", "Low", "Close", "Volume"]]

    # 4) Limpieza y comprobaciones finales.
    canonical = canonical.dropna(subset=list(OHLC_COLS))
    if canonical.empty:
        raise DataError("Tras descartar filas no numéricas no quedan datos válidos.")

    canonical = canonical[~canonical.index.duplicated(keep="last")]
    canonical = canonical.sort_index()

    return canonical


# --------------------------------------------------------------------------- #
# Carga desde el almacén
# --------------------------------------------------------------------------- #
def asset_path(ticker: str, timeframe: str, base_dir: str = BASE_DIR) -> str:
    """Devuelve la ruta esperada de un activo en el almacén."""
    return os.path.join(base_dir, timeframe, f"{ticker}.csv")


def list_assets(timeframe: str, base_dir: str = BASE_DIR) -> list[str]:
    """Lista los *tickers* disponibles para una temporalidad dada."""
    folder = os.path.join(base_dir, timeframe)
    if not os.path.isdir(folder):
        return []
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(folder)
        if f.lower().endswith(".csv")
    )


def load_price_csv(path: str) -> pd.DataFrame:
    """Lee y valida un CSV de precios desde una ruta."""
    if not os.path.isfile(path):
        raise DataError(f"No se encontró el fichero de datos: {path}")
    try:
        raw = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise DataError(f"El fichero de datos está vacío: {path}") from exc
    except Exception as exc:  # noqa: BLE001 - se reempaqueta como DataError
        raise DataError(f"No se pudo leer el fichero {path}: {exc}") from exc
    return validate_ohlc_dataframe(raw)


def load_asset(
    ticker: str,
    timeframe: str,
    start=None,
    end=None,
    base_dir: str = BASE_DIR,
) -> pd.DataFrame:
    """
    Carga un activo del almacén y, opcionalmente, lo recorta al rango de fechas.

    Lanza :class:`DataError` si el fichero no existe, está mal formado o no
    quedan datos en el rango solicitado.
    """
    df = load_price_csv(asset_path(ticker, timeframe, base_dir))

    if start is not None:
        df = df[df.index >= pd.to_datetime(start)]
    if end is not None:
        df = df[df.index <= pd.to_datetime(end)]

    if df.empty:
        raise DataError(
            f"No hay datos de '{ticker}' ({timeframe}) en el rango seleccionado."
        )
    return df


# --------------------------------------------------------------------------- #
# Subida de datos del usuario
# --------------------------------------------------------------------------- #
_TICKER_RE = re.compile(r"^[A-Za-z0-9_\-\.&]{1,30}$")


def _sanitize_ticker(ticker: str) -> str:
    """Valida que el nombre del activo sea seguro como nombre de fichero."""
    ticker = (ticker or "").strip()
    if not _TICKER_RE.match(ticker):
        raise DataError(
            "Nombre de activo no válido. Usa solo letras, números y los "
            "caracteres . _ - & (máximo 30 caracteres)."
        )
    return ticker


def save_uploaded_csv(
    file,
    ticker: str,
    timeframe: str,
    base_dir: str = BASE_DIR,
    overwrite: bool = True,
) -> str:
    """
    Valida un CSV subido por el usuario y lo guarda en el almacén en forma
    canónica (``Open, High, Low, Close, Volume`` con índice temporal).

    Parameters
    ----------
    file : str | ruta | objeto tipo fichero
        CSV de entrada (por ejemplo, el ``UploadedFile`` de Streamlit).
    ticker, timeframe : str
        Identificadores con los que se almacenará el activo.

    Returns
    -------
    str
        Ruta del fichero guardado.
    """
    ticker = _sanitize_ticker(ticker)
    if timeframe not in TIMEFRAMES:
        raise DataError(f"Temporalidad no admitida: {timeframe}.")

    try:
        raw = pd.read_csv(file)
    except pd.errors.EmptyDataError as exc:
        raise DataError("El fichero subido está vacío.") from exc
    except Exception as exc:  # noqa: BLE001
        raise DataError(f"No se pudo leer el fichero subido: {exc}") from exc

    clean = validate_ohlc_dataframe(raw)  # valida la estructura OHLC

    folder = os.path.join(base_dir, timeframe)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{ticker}.csv")
    if os.path.exists(path) and not overwrite:
        raise DataError(f"Ya existe un activo '{ticker}' en {timeframe}.")

    # Se guarda con la columna de fecha explícita para conservar el formato.
    clean.to_csv(path, index_label="datetime")
    return path


# --------------------------------------------------------------------------- #
# Integración con Backtrader
# --------------------------------------------------------------------------- #
def make_feed(df: pd.DataFrame):
    """
    Construye un ``bt.feeds.PandasData`` a partir de un ``DataFrame`` validado.

    Se importa Backtrader de forma diferida para que este módulo pueda usarse
    (por ejemplo, para validar subidas de datos) sin tener Backtrader instalado.
    """
    import backtrader as bt

    return bt.feeds.PandasData(dataname=df)
