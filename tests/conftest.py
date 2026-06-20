"""
conftest.py
===========
Fixtures compartidas por la batería de pruebas de StratStats.

Todos los datos de prueba son sintéticos y deterministas (semilla fija), de
modo que las pruebas son reproducibles y no dependen de descargas de red ni de
datos reales de mercado. Esto es coherente con el requisito no funcional de
fiabilidad/reproducibilidad descrito en el capitulo 3.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def serie_precios() -> pd.DataFrame:
    """
    DataFrame OHLCV diario, determinista, con tendencia suave al alza.

    300 sesiones a partir de 2020-01-01. Sirve tanto para pruebas de
    validacion de datos como para backtests de integracion.
    """
    n = 300
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    rng = np.random.default_rng(42)
    close = 100.0 + np.cumsum(rng.normal(0.10, 1.0, size=n))
    df = pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": 1_000.0,
        },
        index=idx,
    )
    df.index.name = "datetime"
    return df


@pytest.fixture
def csv_es(tmp_path, serie_precios) -> str:
    """Ruta a un CSV con columnas en espanol (Fecha, Apertura, ...)."""
    df = serie_precios.reset_index().rename(
        columns={
            "datetime": "Fecha",
            "Open": "Apertura",
            "High": "Maximo",
            "Low": "Minimo",
            "Close": "Cierre",
            "Volume": "Volumen",
        }
    )
    ruta = tmp_path / "activo_es.csv"
    df.to_csv(ruta, index=False)
    return str(ruta)


@pytest.fixture
def almacen(tmp_path, serie_precios) -> str:
    """
    Crea un almacen de datos temporal con la estructura datos/<tf>/<ticker>.csv
    y devuelve su ruta base. Contiene AAA en 1d.
    """
    carpeta = tmp_path / "datos" / "1d"
    carpeta.mkdir(parents=True)
    serie_precios.to_csv(carpeta / "AAA.csv", index_label="datetime")
    return str(tmp_path / "datos")
