from __future__ import annotations

# Default run_demo parameters (match notebook defaults)
DEFAULT_TICKER = "NVDA"
DEFAULT_YEARS = 10
DEFAULT_INTERVAL = "1d"
DEFAULT_TRAIN_END = "2019-12-31"
DEFAULT_VAL_END = "2022-12-31"
DEFAULT_TRADING_COST = 0.0005
DEFAULT_INITIAL_CAPITAL = 1.0

VOL_WINDOW_FOR_SIGNALS = 20

# Parameter grid (match notebook)
PARAM_GRID_MAIN = [
    dict(ema_fast=20, ema_slow=100, regime_buffer_pct=0.01, vol_window=20, enter_score=2.8, exit_score=1.0, hysteresis_buffer=1, regime_penalty=1),
    dict(ema_fast=20, ema_slow=100, regime_buffer_pct=0.02, vol_window=20, enter_score=2.8, exit_score=1.0, hysteresis_buffer=1, regime_penalty=1),
    dict(ema_fast=30, ema_slow=150, regime_buffer_pct=0.01, vol_window=20, enter_score=2.8, exit_score=1.0, hysteresis_buffer=1, regime_penalty=1),
    dict(ema_fast=50, ema_slow=200, regime_buffer_pct=0.01, vol_window=20, enter_score=2.8, exit_score=1.0, hysteresis_buffer=1, regime_penalty=1),
]

# Benchmark label reflects the fair execution convention used in this project (1-bar delayed execution via shift in run_backtest)
LABEL_BH = "Benchmark: Buy & Hold (fair, 1-bar delayed execution)"
LABEL_MAIN = "Strategy: Hybrid Main"

MA_FAST = 50
MA_SLOW = 200
