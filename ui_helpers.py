"""
ui_helpers.py
=============
Componentes de interfaz reutilizables entre páginas (subida y selección de
datos del usuario). Aíslan a Streamlit del resto de la lógica.
"""

from __future__ import annotations

import streamlit as st

import data_loader as dl


def data_upload_widget(timeframe: str, base_dir: str = dl.BASE_DIR, *, key: str = "up") -> bool:
    """
    Muestra un cargador para que el usuario suba su propio CSV de precios y lo
    guarde en el almacén. Devuelve ``True`` si se ha guardado un fichero nuevo.

    El CSV debe contener columnas OHLC (Open, High, Low, Close) y una columna de
    fecha (Date/datetime); el volumen es opcional.
    """
    saved = False
    with st.expander("➕ Subir mis propios datos (CSV con estructura OHLC)"):
        st.caption(
            "El fichero debe incluir una columna de fecha (Date o datetime) y las "
            "columnas Open, High, Low y Close. El volumen es opcional."
        )
        col1, col2 = st.columns([2, 1])
        file = col1.file_uploader(
            "Fichero CSV de datos", type=["csv"], key=f"{key}_file"
        )
        ticker = col2.text_input("Nombre del activo (ticker)", key=f"{key}_ticker")
        if st.button("Guardar datos", key=f"{key}_save"):
            if file is None:
                st.warning("Selecciona primero un fichero CSV.")
            elif not ticker.strip():
                st.warning("Indica un nombre para el activo.")
            else:
                try:
                    path = dl.save_uploaded_csv(file, ticker.strip(), timeframe, base_dir)
                except dl.DataError as exc:
                    st.error(f"No se pudo guardar: {exc}")
                else:
                    st.success(
                        f"Datos de «{ticker.strip()}» guardados en {timeframe}. "
                        "Ya puedes seleccionarlo en la lista de activos."
                    )
                    saved = True
    return saved


def available_assets(timeframe: str, extra: list[str] | None = None,
                     base_dir: str = dl.BASE_DIR) -> list[str]:
    """
    Devuelve la lista de activos disponibles para una temporalidad, combinando
    los del almacén con una lista fija opcional (p. ej. los activos por defecto).
    """
    found = dl.list_assets(timeframe, base_dir)
    merged = list(dict.fromkeys((extra or []) + found))  # sin duplicados, orden estable
    return merged
