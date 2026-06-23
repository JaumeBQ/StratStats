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

Strategies must be written using the [Backtrader](https://www.backtrader.com/) framework. Here is a minimal example (see `estrategia_ejemplo.py` for a complete one):

```python
import backtrader as bt

class MyStrategy(bt.Strategy):
    params = (
        ("sma_fast", 10),
        ("sma_slow", 30),
    )

    def __init__(self):
        self.trade_log = []  # Required for trade analytics
        self.sma_fast = bt.ind.SMA(period=self.p.sma_fast)
        self.sma_slow = bt.ind.SMA(period=self.p.sma_slow)
        self.crossover = bt.ind.CrossOver(self.sma_fast, self.sma_slow)

    def next(self):
        if not self.position and self.crossover > 0:
            size = int((self.broker.getcash() * 0.95) // self.data.close[0])
            self.buy(size=size)
        elif self.position and self.crossover < 0:
            self.close()

    def notify_order(self, order):
        if order.status == order.Completed:
            if order.issell():
                self.trade_log.append({
                    "buyprice": ...,
                    "sellprice": order.executed.price,
                })
```

> ⚠️ Your strategy class **must** maintain a `self.trade_log` list with `buyprice` and `sellprice` entries for the analytics to work correctly.

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
