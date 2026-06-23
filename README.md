# 💰 StratStats

> **A simple yet powerful backtesting web app for trading strategies on stocks and options portfolios.**

StratStats is a [Streamlit](https://streamlit.io)-based web application that lets you upload your own trading strategy (written in Python/Backtrader), backtest it against historical market data, and optimize its parameters — all from a clean browser interface.

---

## ✨ Features

- 📈 **Backtesting** — Run your strategy against historical OHLCV data fetched via `yfinance`
- 🔧 **Parameter Optimization** — Sweep parameter ranges and find the best-performing configuration
- 📊 **Performance Analytics** — Full tearsheet powered by `QuantStats`: Sharpe ratio, drawdown, returns, and more
- 📉 **Interactive Charts** — Visual trade log and equity curves via `Plotly`
- 🧩 **Plug & Play Strategies** — Upload any `.py` file with a `backtrader`-compatible strategy class
- 🎨 **Custom UI Theme** — Clean, dark-themed interface built with Streamlit

---

## 🗂️ Project Structure

```
StratStats/
│
├── Welcome_page.py          # App entry point
├── pages/
│   ├── 1_Backtest.py        # Backtesting page
│   └── 2_Optimization.py    # Parameter optimization page
│
├── SBacktesting.py          # Core backtesting engine (Backtrader wrapper)
├── backtest_utils.py        # Utility functions for backtest execution
├── data_loader.py           # Historical data fetching (yfinance)
├── optimization.py          # Parameter sweep & optimization logic
├── strategy_loader.py       # Dynamic strategy class loader from uploaded .py files
├── bench.py                 # Benchmark comparison utilities
├── ui_style.py              # Global UI theme and styling
├── ui_helpers.py            # Reusable UI components
│
├── estrategia_ejemplo.py    # Example strategy: SMA crossover
├── requirements.txt
└── .gitignore
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/JaumeBQ/StratStats.git
cd StratStats
```

### 2. Install dependencies

It is recommended to use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the app

```bash
streamlit run Welcome_page.py
```

The app will open in your browser at `http://localhost:8501`.

---

## 📝 Writing Your Own Strategy

Strategies must be written using the [Backtrader](https://www.backtrader.com/) framework and follow two contracts to be fully compatible with StratStats:

### Contract 1 — `params` tuple (required for Optimization page)

To use the **Optimization** page, your strategy must declare a `params` tuple at class level. The optimizer will automatically detect these parameters and let you define a sweep range for each one from the UI.

```python
class MyStrategy(bt.Strategy):
    params = (
        ("sma_rapida", 10),   # (parameter_name, default_value)
        ("sma_lenta",  30),
        ("stop_loss",   0.0),
    )
```

> Parameters not selected for optimization will remain at their default value during the sweep.

### Contract 2 — `self.trade_log` (required for Backtest analytics)

The **Backtest** page uses `self.trade_log` to compute per-trade analytics and display the trade table. Your strategy must initialise it as an empty list in `__init__` and append one entry per completed round-trip trade inside `notify_order`:

```python
def __init__(self):
    self.trade_log = []  # required
    self.precio_entrada = None
    # ... your indicators ...

def notify_order(self, order):
    if order.status == order.Completed:
        if order.isbuy():
            self.precio_entrada = order.executed.price
        elif order.issell():
            self.trade_log.append({
                "buyprice":  self.precio_entrada,
                "sellprice": order.executed.price,
            })
```

### Full example — SMA Crossover

A complete ready-to-upload example is provided in [`estrategia_ejemplo.py`](estrategia_ejemplo.py). It implements a simple moving-average crossover strategy with an optional stop-loss, and respects both contracts above.

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| `streamlit` | Web application framework |
| `backtrader` | Backtesting engine |
| `yfinance` | Historical market data |
| `quantstats` | Performance analytics & tearsheets |
| `plotly` | Interactive charts |
| `pandas` / `numpy` | Data manipulation |
| `scipy` | Statistical analysis |
| `matplotlib` / `seaborn` | Additional visualizations |

---

## 📄 License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

---

<p align="center">Made with ❤️ by <a href="https://github.com/JaumeBQ">JaumeBQ</a></p>
