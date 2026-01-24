import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def run_backtest(data: pd.DataFrame, cost_per_trade: float = 0.001, risk_free_rate: float = 0.03):
    bt_data = data.copy()
    bt_data['OBV_MA20'] = bt_data['OBV'].rolling(window=20).mean()

    bt_data['Signal'] = 0
    condition_buy = (
        (bt_data['MACD_Line'] > bt_data['Signal_Line']) &
        (bt_data['RSI'] < 85) &
        (bt_data['OBV'] > bt_data['OBV_MA20'])
    )
    condition_sell = (
        (bt_data['MACD_Line'] < bt_data['Signal_Line']) |
        (bt_data['Close'] < bt_data['BB_Lower'])
    )

    bt_data.loc[condition_buy, 'Signal'] = 1
    bt_data.loc[condition_sell, 'Signal'] = 0
    bt_data['Signal'] = bt_data['Signal'].ffill().fillna(0)

    bt_data['Position'] = bt_data['Signal'].shift(1)
    bt_data['Market_Return'] = bt_data['Close'].pct_change()
    bt_data['Strategy_Gross_Return'] = bt_data['Market_Return'] * bt_data['Position']

    trades = bt_data['Position'].diff().abs()
    bt_data['Strategy_Net_Return'] = bt_data['Strategy_Gross_Return'] - (trades * cost_per_trade)
    bt_data['Strategy_Net_Return'] = bt_data['Strategy_Net_Return'].fillna(0)

    bt_data['Equity_Curve'] = (1 + bt_data['Strategy_Net_Return']).cumprod()
    bt_data['Benchmark_Curve'] = (1 + bt_data['Market_Return']).cumprod()

    days = len(bt_data)
    total_return = bt_data['Equity_Curve'].iloc[-1] - 1
    cagr = (1 + total_return) ** (252 / days) - 1

    excess_returns = bt_data['Strategy_Net_Return'] - (risk_free_rate/252)
    sharpe_ratio = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)

    rolling_max = bt_data['Equity_Curve'].cummax()
    drawdown = (bt_data['Equity_Curve'] - rolling_max) / rolling_max
    max_drawdown = drawdown.min()

    real_trades = bt_data[bt_data['Position'] == 1]
    win_trades = real_trades[real_trades['Strategy_Net_Return'] > 0]
    win_rate = len(win_trades) / len(real_trades) if len(real_trades) > 0 else 0

    metrics = {
        'total_return': total_return,
        'cagr': cagr,
        'sharpe': sharpe_ratio,
        'drawdown': max_drawdown,
        'win_rate': win_rate
    }

    print(f"=== Advanced Strategy Report ({bt_data.get('Ticker','NVDA')}) ===")
    print(f"Indicators Used: MACD, RSI, Bollinger Bands, OBV")
    print("-" * 40)
    print(f"Total Return:       {total_return:.2%}")
    print(f"Annualized (CAGR):  {cagr:.2%}")
    print(f"Sharpe Ratio:       {sharpe_ratio:.2f}")
    print(f"Max Drawdown:       {max_drawdown:.2%}")
    print(f"Win Rate:           {win_rate:.2%}")
    print("-" * 40)

    # quick plot
    try:
        plt.figure(figsize=(14, 8))
        plt.plot(bt_data.index, bt_data['Benchmark_Curve'], label='Buy & Hold (Benchmark)', color='gray', alpha=0.4)
        plt.plot(bt_data.index, bt_data['Equity_Curve'], label='Multi-Factor AI Strategy', color='green', linewidth=2)
        plt.title(f'Advanced Backtest: NVDA (MACD + RSI + BB + OBV)')
        plt.ylabel('Portfolio Value')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.show()
    except Exception:
        pass

    return metrics, bt_data
