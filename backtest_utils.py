"""Utility helpers and custom exceptions for the Streamlit backtest page.

These helpers let us centralise validation logic so we can unit-test the
most error-prone behaviours without having to spin up the UI layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Tuple

import pandas as pd
import quantstats as qs


class BacktestError(Exception):
    """Base exception for controlled backtest failures."""


class StrategyNotSelectedError(BacktestError):
    """Raised when the user attempts to run the app without a strategy."""

    def __init__(self) -> None:
        super().__init__("Selecciona una estrategia antes de ejecutar el backtest.")


class NoTickersSelectedError(BacktestError):
    """Raised when no tickers were supplied."""

    def __init__(self) -> None:
        super().__init__("Selecciona al menos un ticker para lanzar el backtest.")


class DataLoadingError(BacktestError):
    """Raised when we cannot read or parse the price data."""


class EmptyDataError(DataLoadingError):
    """Raised when the resulting data frame ends up empty."""


class AnalyzerResultsError(BacktestError):
    """Raised when a Backtrader analyzer does not return the expected data."""


class MetricComputationError(BacktestError):
    """Raised when we cannot derive metrics from the returns series."""


class SliderWindowError(BacktestError):
    """Raised when the zoom window cannot be constructed."""


@dataclass(frozen=True)
class SliderConfig:
    """Encapsulates the slider settings for the price window."""

    show_slider: bool
    min_value: Optional[pd.Timestamp]
    max_value: Optional[pd.Timestamp]
    default_value: Optional[pd.Timestamp]


REQUIRED_COLUMNS = {"Open", "High", "Low", "Close"}


def ensure_strategy_selected(strategy: Optional[object]) -> object:
    """Ensure a strategy instance/class is provided."""

    if strategy is None:
        raise StrategyNotSelectedError()
    return strategy


def ensure_tickers_selected(tickers: Sequence[str]) -> Sequence[str]:
    """Ensure the ticker list is not empty."""

    if not tickers:
        raise NoTickersSelectedError()
    return tickers


def load_price_data(
    data_dir: Path | str,
    timeframe: str,
    ticker: str,
    start_date,
    end_date,
) -> pd.DataFrame:
    """Load and filter the OHLCV data for a specific ticker.

    Raises:
        DataLoadingError: when files are missing or malformed.
        EmptyDataError: when no data remains after filtering.
    """

    file_path = Path(data_dir) / timeframe / f"{ticker}.csv"
    if not file_path.exists():
        raise DataLoadingError(f"No se encontró el archivo de datos para {ticker}.")

    try:
        df = pd.read_csv(file_path)
    except Exception as exc:  # pragma: no cover - unlikely but guarded
        raise DataLoadingError(f"Error al leer el CSV de {ticker}: {exc}") from exc

    date_column = "Date" if timeframe == "1d" else "datetime"
    if date_column not in df.columns:
        raise DataLoadingError(
            f"El archivo de {ticker} no contiene la columna '{date_column}'."
        )

    missing_columns = REQUIRED_COLUMNS.difference(df.columns)
    if missing_columns:
        raise DataLoadingError(
            f"Faltan columnas obligatorias {sorted(missing_columns)} en {ticker}."
        )

    df[date_column] = pd.to_datetime(df[date_column], errors="coerce")
    df = df.dropna(subset=[date_column])

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    mask = (df[date_column] >= start_ts) & (df[date_column] <= end_ts)
    df = df.loc[mask]

    if df.empty:
        raise EmptyDataError(
            f"El rango seleccionado no contiene datos para {ticker}."
        )

    df = df.sort_values(date_column)
    df.set_index(date_column, inplace=True)
    return df


def compute_portfolio_returns(
    returns_by_ticker: Dict[str, pd.Series]
) -> Tuple[pd.Series, pd.DataFrame]:
    """Aggregate the individual return series into a portfolio.

    Returns the aggregated series and the dataframe used for the CSV export.
    """

    if not returns_by_ticker:
        raise EmptyDataError("No se generaron retornos para las estrategias seleccionadas.")

    df = pd.DataFrame(returns_by_ticker)
    if df.empty:
        raise EmptyDataError("No se pudieron combinar los retornos de las estrategias.")

    df = df.sort_index()
    df = df.fillna(0)
    total_returns = df.sum(axis=1)

    if total_returns.empty:
        raise EmptyDataError("La serie de retornos del portfolio está vacía.")

    df["Portfolio"] = total_returns
    return total_returns, df


def safe_metricas_retornos(
    returns: pd.Series,
    benchmark_returns: pd.Series,
) -> Tuple[float, float, float, float, pd.Series, float, float, float, float, float]:
    """Compute metrics while guarding against divisions by zero."""

    if returns.empty:
        raise MetricComputationError("No hay retornos para calcular métricas.")
    if benchmark_returns.empty:
        raise MetricComputationError("No hay retornos del benchmark disponibles.")

    mean_return = returns.mean()
    std_return = returns.std()
    sharpe_ratio = mean_return / std_return if std_return != 0 else float("nan")

    try:
        cagr = qs.stats.cagr(returns)
    except Exception as exc:
        raise MetricComputationError(f"No se pudo calcular el CAGR: {exc}") from exc

    drawdown = qs.stats.max_drawdown(returns)
    percentiles = returns.quantile([0.1, 0.25, 0.5, 0.75, 0.9])

    mean_return_benchmark = benchmark_returns.mean()
    try:
        cagr_benchmark = qs.stats.cagr(benchmark_returns)
    except Exception as exc:
        raise MetricComputationError(
            f"No se pudo calcular el CAGR del benchmark: {exc}"
        ) from exc
    drawdown_benchmark = qs.stats.max_drawdown(benchmark_returns)

    total_returns = (returns + 1).prod() - 1
    total_returns_benchmark = (benchmark_returns + 1).prod() - 1

    return (
        mean_return,
        std_return,
        sharpe_ratio,
        drawdown,
        percentiles,
        cagr,
        cagr_benchmark,
        drawdown_benchmark,
        total_returns,
        total_returns_benchmark,
    )


def build_slider_config(index: pd.Index, window_size: int) -> SliderConfig:
    """Return slider settings or hide it when there is not enough data."""

    if len(index) == 0:
        raise SliderWindowError("No hay datos para mostrar en el gráfico de precios.")

    if not isinstance(index, pd.DatetimeIndex):
        raise SliderWindowError("El índice no es de tipo fecha.")

    sorted_index = index.sort_values()
    min_value = sorted_index[0]

    if len(sorted_index) <= window_size + 1:
        max_value = sorted_index[-1]
        return SliderConfig(False, min_value, max_value, min_value)

    max_slider_position = len(sorted_index) - window_size - 1
    max_value = sorted_index[max_slider_position]
    default_value = max_value

    return SliderConfig(True, min_value, max_value, default_value)


def slice_window(df: pd.DataFrame, start_datetime: pd.Timestamp, window_size: int) -> pd.DataFrame:
    """Return a window of size `window_size` starting at `start_datetime`."""

    if start_datetime not in df.index:
        raise SliderWindowError("La fecha seleccionada no está en el dataset.")

    start_pos = df.index.get_loc(start_datetime)
    end_pos = min(start_pos + window_size, len(df) - 1)
    return df.iloc[start_pos : end_pos + 1]


def extract_returns_from_pyfolio(resultados) -> pd.Series:
    """Safely obtain the returns series from the PyFolio analyzer."""

    try:
        portfolio_stats = resultados.analyzers.pyfolio.get_analysis()
    except AttributeError as exc:
        raise AnalyzerResultsError(
            "La estrategia no devolvió el analizador PyFolio con los retornos."
        ) from exc

    returns_data = portfolio_stats.get("returns") if portfolio_stats else None
    if returns_data is None:
        raise AnalyzerResultsError("PyFolio no devolvió la serie de retornos.")

    if isinstance(returns_data, pd.Series):
        returns = returns_data
    elif isinstance(returns_data, pd.DataFrame):
        if returns_data.empty:
            raise EmptyDataError("PyFolio devolvió una serie de retornos vacía.")
        returns = returns_data.squeeze()
    else:
        returns = pd.Series(returns_data)

    if returns.empty:
        raise EmptyDataError("La serie de retornos obtenida está vacía.")

    returns.index = pd.to_datetime(returns.index, errors="coerce")
    returns = returns.dropna()

    if returns.empty:
        raise EmptyDataError("No hay fechas válidas en la serie de retornos.")

    return returns


def load_benchmark_returns(
    data_dir: Path | str,
    timeframe: str,
    benchmark: str,
    start_date,
    end_date,
) -> pd.Series:
    """Load benchmark prices and convert them to returns."""

    df = load_price_data(data_dir, timeframe, benchmark, start_date, end_date)
    returns = df["Close"].pct_change().dropna()
    if returns.empty:
        raise EmptyDataError("El benchmark no tiene retornos en el rango seleccionado.")
    return returns
