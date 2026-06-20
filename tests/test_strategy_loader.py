"""
test_strategy_loader.py
=======================
Pruebas unitarias de la carga dinamica de estrategias (strategy_loader.py):
deteccion de clases que heredan de bt.Strategy, manejo de errores de sintaxis
y aviso de importaciones potencialmente peligrosas.
"""

from __future__ import annotations

import pytest

from strategy_loader import (
    StrategyLoadError,
    find_strategies_in_code,
    scan_for_risky_imports,
)


CODIGO_VALIDO = '''
import backtrader as bt

class MiEstrategia(bt.Strategy):
    params = (("periodo", 10),)
    def next(self):
        pass
'''

CODIGO_DOS_ESTRATEGIAS = '''
import backtrader as bt
from backtrader import Strategy

class EstrategiaA(bt.Strategy):
    pass

class EstrategiaB(Strategy):
    pass

class NoEsEstrategia:
    pass
'''


# --------------------------------------------------------------------------- #
# find_strategies_in_code
# --------------------------------------------------------------------------- #
def test_detecta_una_estrategia():
    estrategias = find_strategies_in_code(CODIGO_VALIDO)
    assert "MiEstrategia" in estrategias
    assert len(estrategias) == 1


def test_detecta_varias_formas_de_herencia():
    """Detecta tanto bt.Strategy como 'from backtrader import Strategy'."""
    estrategias = find_strategies_in_code(CODIGO_DOS_ESTRATEGIAS)
    assert set(estrategias) == {"EstrategiaA", "EstrategiaB"}
    assert "NoEsEstrategia" not in estrategias


def test_codigo_sin_estrategias_falla():
    with pytest.raises(StrategyLoadError):
        find_strategies_in_code("x = 1\n")


def test_codigo_con_error_de_sintaxis_falla():
    with pytest.raises(StrategyLoadError):
        find_strategies_in_code("class Mal(bt.Strategy)\n    pass")  # falta ':'


def test_estrategia_de_ejemplo_real():
    """La estrategia de ejemplo que se distribuye con la app debe detectarse."""
    with open("estrategia_ejemplo.py", encoding="utf-8") as fh:
        codigo = fh.read()
    estrategias = find_strategies_in_code(codigo)
    assert "CruceMedias" in estrategias


# --------------------------------------------------------------------------- #
# scan_for_risky_imports
# --------------------------------------------------------------------------- #
def test_detecta_import_peligroso():
    assert "os" in scan_for_risky_imports("import os\n")


def test_detecta_import_from_peligroso():
    assert "subprocess" in scan_for_risky_imports("from subprocess import run\n")


def test_codigo_limpio_no_avisa():
    assert scan_for_risky_imports(CODIGO_VALIDO) == []


def test_varios_imports_peligrosos_ordenados():
    code = "import socket\nimport os\nimport requests\n"
    assert scan_for_risky_imports(code) == ["os", "requests", "socket"]


def test_sintaxis_invalida_no_revienta():
    """Ante codigo no parseable, devuelve lista vacia en lugar de fallar."""
    assert scan_for_risky_imports("def (:::") == []
