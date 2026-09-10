import MetaTrader5 as mt5
import time
import os
import sys
from datetime import datetime

# === YOUR REAL ACCOUNT ===
LOGIN = 17375873
SERVER = "HeadwayReal"
SYMBOL = "XAUUSDm"
LOT = 0.01
GRID_DOLLARS = 2.5       # Buy new when drops $2.5 like video
PROFIT_TO_CLOSE = 0.50   # Close all when +$0.50

password = os.getenv("MT5_PASSWORD")
if not password:
    print("ERROR: Set MT5_PASSWORD secret in GitHub Settings!")
    sys.exit(1)

# === FIX FOR -10004 No IPC connection ===
print("Connecting to MT5 terminal...")
mt5_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
connected = False
for i in range(15):
    if mt5.initialize(path=mt5_path):
        print("MT5 terminal connected!")
        connected = True
        break
    print(f"Waiting for MT5 terminal... {i+1}/15")
    time.sleep(5)

if not connected:
    print(f"MT5 init failed: {mt5.last_error()}")
    sys.exit(1)

time.sleep(2)

# === LOGIN ===
print(f"Logging in {LOGIN} @ {SERVER}...")
if not mt5.login(LOGIN, password=password, server=SERVER):
    print(f"Login FAILED {mt5.last_error()}")
    mt5.shutdown()
    sys.exit(1)

acc = mt5.account_info()
print(f"=== ROBOT TRADING LIVE ===")
print(f"Balance: ${acc.balance} | Equity: ${acc.equity}")

# Enable symbol
if not mt5.symbol_select(SYMBOL, True):
    print(f"Failed to select {SYMBOL}")
    sys.exit(1)

def buy_now():
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        print("No tick")
        return None
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT,
        "type": mt5.ORDER_TYPE_BUY,
        "price": tick.ask,
        "deviation": 100,
        "magic": 777,
        "comment": "RobotTrading",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    print(f"BUY {LOT} at {tick.ask} -> retcode {result.retcode}")
    return result

# === MAIN LOOP LIKE VIDEO ===
print(f"Starting grid... GRID=${GRID_DOLLARS} TARGET=${PROFIT_TO_CLOSE}")

while True:
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        positions = []

    total_profit = sum([p.profit for p in positions])
    count = len(positions)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Count:{count} Profit:${total_profit:.2f} Target:${PROFIT_TO_CLOSE:.2f}")

    # 1. CLOSE ALL - This is the big profit jump in your video
    if count > 0 and total_profit >= PROFIT_TO_CLOSE:
        print(f"*** PROFIT HIT ${total_profit:.2f} - CLOSING ALL {count} TRADES ***")
        for p in positions:
            tick = mt5.symbol_info_tick(SYMBOL)
            if tick is None:
                continue
            close_req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": SYMBOL,
                "volume": p.volume,
                "type": mt5.ORDER_TYPE_SELL,
                "position": p.ticket,
                "price": tick.bid,
                "deviation": 100,
                "magic": 777,
                "comment": "CloseProfit",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            mt5.order_send(close_req)
        
        # Grow target like video 0.5 -> 1 -> 2.5 -> 5
        global_target = min(PROFIT_TO_CLOSE * 1.8, 5.0)
        # Need to re-assign via globals workaround
        PROFIT_TO_CLOSE = round(global_target, 2)
        print(f"New target: ${PROFIT_TO_CLOSE}")
        time.sleep(3)
        continue

    # 2. GRID BUY
    if count == 0:
        buy_now()
    else:
        try:
            lowest_open = min([p.price_open for p in positions])
            tick = mt5.symbol_info_tick(SYMBOL)
            if tick:
                drop = lowest_open - tick.bid
                if drop >= GRID_DOLLARS:
                    print(f"Price dropped ${drop:.2f} - Adding BUY")
                    buy_now()
        except Exception as e:
            print(f"Grid error {e}")

    time.sleep(5)
