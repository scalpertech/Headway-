import MetaTrader5 as mt5
import time, os, sys
from datetime import datetime

# === CONFIG CHALLENGE B ===
LOGIN = 17375873
SERVER = "Headway-Real"
SYMBOL = "GOLD"
PASSWORD = os.getenv("MT5_PASSWORD", "")
START_TARGET = 50.0
MAX_TIME_SEC = 10800  # 3 HRS

print(f"===== HEADWAY CHALLENGE B STARTED =====")
print(f"Account: {LOGIN} | Server: {SERVER} | Goal: $3.99 -> ${START_TARGET} in 3HRS")

if not mt5.initialize():
    print(f"MT5 init failed: {mt5.last_error()}")
    sys.exit(1)

if PASSWORD == "":
    print("ERROR: MT5_PASSWORD secret empty! Set it in GitHub Secrets!")
    sys.exit(1)

if not mt5.login(LOGIN, password=PASSWORD, server=SERVER):
    print(f"LOGIN FAILED {LOGIN}@{SERVER}: {mt5.last_error()}")
    mt5.shutdown()
    sys.exit(1)

acc = mt5.account_info()
print(f"CONNECTED! Balance: ${acc.balance:.2f} | Equity: ${acc.equity:.2f}")

for sym_try in [SYMBOL, "XAUUSD", "XAUUSD.m", "GOLD.m"]:
    if mt5.symbol_select(sym_try, True):
        SYMBOL = sym_try
        print(f"Trading symbol: {SYMBOL}")
        break

# SCALPER PARAMS
LOT = 0.01
SL_POINTS = 300
TP_POINTS = 600
MAGIC = 17375873
MAX_SPREAD = 600

start_balance = acc.balance
target_balance = START_TARGET
start_time = time.time()
trades = 0

def get_signal():
    try:
        rates = mt5.copy_rates(SYMBOL, mt5.TIMEFRAME_M1, 0, 50)
        if rates is None or len(rates) < 30:
            return None
        import numpy as np
        closes = rates['close']
        ema9 = np.convolve(closes, np.ones(9)/9, mode='valid')[-1]
        ema21 = np.convolve(closes, np.ones(21)/21, mode='valid')[-1]
        deltas = np.diff(closes[-15:])
        gains = deltas[deltas>0].sum() / 14 if len(deltas[deltas>0])>0 else 0
        losses = -deltas[deltas<0].sum() / 14 if len(deltas[deltas<0])>0 else 0.001
        rsi = 100 - (100/(1+gains/losses))
        last_close = closes[-1]
        prev_close = closes[-2]
        if last_close > ema9 > ema21 and prev_close < last_close and 30 < rsi < 68:
            return "BUY"
        if last_close < ema9 < ema21 and prev_close > last_close and 32 < rsi < 70:
            return "SELL"
    except Exception as e:
        print(f"Signal error: {e}")
    return None

def open_trade(signal):
    global trades, LOT
    tick = mt5.symbol_info_tick(SYMBOL)
    info = mt5.symbol_info(SYMBOL)
    if not tick or not info:
        return False
    spread = (tick.ask - tick.bid) / info.point
    if spread > MAX_SPREAD:
        print(f"Spread high {spread:.0f}, skip")
        return False
    price = tick.ask if signal=="BUY" else tick.bid
    sl = price - SL_POINTS*info.point if signal=="BUY" else price + SL_POINTS*info.point
    tp = price + TP_POINTS*info.point if signal=="BUY" else price - TP_POINTS*info.point
    acc_now = mt5.account_info()
    if acc_now:
        if acc_now.balance >= 20: LOT = 0.03
        elif acc_now.balance >= 12: LOT = 0.02
        else: LOT = 0.01
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": float(LOT),
        "type": mt5.ORDER_TYPE_BUY if signal=="BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 30,
        "magic": MAGIC,
        "comment": f"ScalpB {signal}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        trades += 1
        print(f">>> OPENED {signal} #{trades} {SYMBOL} {LOT} @ {price:.2f} Ticket {result.order}")
        return True
    else:
        print(f"Order failed {signal}: {result.retcode if result else 'None'}")
        return False

print(f"START ${start_balance:.2f} -> TARGET ${target_balance:.2f} LOT {LOT}")

while True:
    elapsed = time.time() - start_time
    if elapsed > MAX_TIME_SEC:
        print("3 HOURS UP!")
        break
    acc = mt5.account_info()
    if not acc:
        time.sleep(5)
        continue
    if acc.balance >= target_balance or acc.equity >= target_balance:
        print(f"========== CHALLENGE COMPLETE! ${acc.balance:.2f} ==========")
        break
    if acc.equity < 1.0:
        print("EQUITY LOW < $1 - stop")
        break
    positions = mt5.positions_get(symbol=SYMBOL)
    pos_count = len(positions) if positions else 0
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bal ${acc.balance:.2f} Eq ${acc.equity:.2f} P/L ${acc.profit:.2f} Pos {pos_count} Trades {trades} {elapsed/60:.0f}m/180m")
    if pos_count == 0:
        signal = get_signal()
        if signal:
            print(f"SIGNAL: {signal}")
            open_trade(signal)
    time.sleep(10)

acc = mt5.account_info()
if acc:
    print(f"FINAL: ${acc.balance:.2f} Profit ${acc.balance-start_balance:.2f} Trades {trades}")
mt5.shutdown()
