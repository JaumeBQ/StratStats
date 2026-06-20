"""
test_data_loader.py
===================
Pruebas unitarias de la capa de acceso a datos (data_loader.py).

Cubren la normalizacion OHLC, la deteccion de la columna de fecha, el saneado
del nombre de activo, el guardado de subidas y la carga desde el almacen.
"""

from __future__ import annotations

import pandas as pd
import pytest

import data_loader as dl
from data_loader import (
    DataError,
    validate_ohlc_dataframe,
    save_uploaded_csv,
    load_asset,
    list_assets,
    _sanitize_ticker,
)


# --------------------------------------------------------------------------- #
# validate_ohlc_dataframe
# --------------------------------------------------------------------------- #
def test_acepta_columnas_en_ingles(serie_precios):
    """Un DataFrame ya canonico se normaliza sin error."""
    out = validate_ohlc_dataframe(serie_precios.reset_index())
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert isinstance(out.index, pd.DatetimeIndex)


def test_acepta_columnas_en_espanol(csv_es):
    """Nombres en espanol (Apertura, Cierre...) se mapean a la forma canonica."""
    raw = pd.read_csv(csv_es)
    out = validate_ohlc_dataframe(raw)
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(out) == 300


def test_rellena_volumen_si_falta():
    """Si no hay columna de volumen, se rellena con cero (es opcional)."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2021-01-01", periods=3),
            "open": [1, 2, 3],
            "high": [1, 2, 3],
            "low": [1, 2, 3],
            "close": [1, 2, 3],
        }
    )
    out = validate_ohlc_dataframe(df)
    assert (out["Volume"] == 0).all()


def test_dataframe_vacio_lanza_error():
    with pytest.raises(DataError):
        validate_ohlc_dataframe(pd.DataFrame())


def test_sin_columna_de_fecha_lanza_error():
    df = pd.DataFrame({"open": [1], "high": [1], "low": [1], "close": [1]})
    with pytest.raises(DataError):
        validate_ohlc_dataframe(df)


def test_faltan_columnas_obligatorias_lanza_error():
    df = pd.DataFrame(
        {"date": pd.date_range("2021-01-01", periods=2), "close": [1, 2]}
    )
    with pytest.raises(DataError):
        validate_ohlc_dataframe(df)


def test_descarta_filas_no_numericas():
    """Las filas con texto en los precios se descartan al convertir a numero."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2021-01-01", periods=3),
            "open": [10, "x", 12],
            "high": [10, 11, 12],
            "low": [10, 11, 12],
            "close": [10, 11, 12],
        }
    )
    out = validate_ohlc_dataframe(df)
    assert len(out) == 2  # se elimina la fila con "x"


def test_elimina_indices_duplicados():
    df = pd.DataFrame(
        {
            "date": ["2021-01-01", "2021-01-01", "2021-01-02"],
            "open": [1, 2, 3],
            "high": [1, 2, 3],
            "low": [1, 2, 3],
            "close": [1, 2, 3],
        }
    )
    out = validate_ohlc_dataframe(df)
    assert len(out) == 2  # un unico registro por fecha


# --------------------------------------------------------------------------- #
# _sanitize_ticker
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("ticker", ["AAPL", "BTC-USD", "BRK.B", "EUR_USD"])
def test_tickers_validos(ticker):
    assert _sanitize_ticker(ticker) == ticker


@pytest.mark.parametrize("ticker", ["", "  ", "../etc/passwd", "a/b", "x" * 31])
def test_tickers_invalidos_lanzan_error(ticker):
    with pytest.raises(DataError):
        _sanitize_ticker(ticker)


# --------------------------------------------------------------------------- #
# save_uploaded_csv + load_asset + list_assets (ciclo completo)
# --------------------------------------------------------------------------- #
def test_subida_y_carga_ciclo_completo(tmp_path, csv_es):
    base = str(tmp_path / "datos")
    ruta = save_uploaded_csv(csv_es, ticker="MIDATO", timeframe="1d", base_dir=base)
    assert ruta.endswith("MIDATO.csv")

    # el activo aparece en el listado
    assert "MIDATO" in list_assets("1d", base_dir=base)

    # y se puede recuperar y recortar por fechas
    df = load_asset("MIDATO", "1d", base_dir=base)
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]


def test_subida_temporalidad_no_admitida(csv_es, tmp_path):
    with pytest.raises(DataError):
        save_uploaded_csv(csv_es, "X", "2d", base_dir=str(tmp_path))


def test_carga_activo_inexistente(almacen):
    with pytest.raises(DataError):
        load_asset("NO_EXISTE", "1d", base_dir=almacen)


def test_carga_rango_fuera_de_datos(almacen):
    """Pedir un rango sin datos lanza DataError, no devuelve vacio."""
    with pytest.raises(DataError):
        load_asset("AAA", "1d", start="2050-01-01", base_dir=almacen)
