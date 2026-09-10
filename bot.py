import MetaTrader5 as mt5
import time, os, sys
from datetime import datetime

# YOUR REAL ACCOUNT
LOGIN = 17375873
SERVER = "HeadwayReal"
SYMBOL = "XAUUSDm"
LOT = 0.01
GRID_DOLLARS = 2.5      # Buy new when Gold drops $2.5 - like video
PROFIT_TO_CLOSE = 0.50  # Close ALL when +$0.50 - grows like video

password = os.getenv("MT5_PASSWORD")
if not password:
    print("ERROR: Set MT5_PASSWORD secret!"); sys.exit(1)

mt5.initialize(path=r"C:\Program Files\MetaTrader 5\terminal64.exe")
time.sleep(2)

if not mt5.login(LOGIN, password=password, server=SERVER):
    print("Login FAILED", mt5.last_error()); sys.exit(1)

print(f"=== ROBOT TRADING LIVE ===")
print(f"Balance: ${mt5.account_info().balance}")

# Enable symbol
mt5.symbol_select(SYMBOL, True)

def buy_now():
    tick = mt5.symbol_info_tick(SYMBOL)
    req = {
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
    r = mt5.order_send(req)
    print(f"BUY {LOT} at {tick.ask} -> {r.retcode}")
    return r

# Main loop - same as video
while True:
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        positions = []

    total_profit = sum([p.profit for p in positions])
    count = len(positions)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Count:{count} Profit:${total_profit:.2f} Target:${PROFIT_TO_CLOSE:.2f}")

    # 1. CLOSE ALL - this is the profit jump you see in video
    if count > 0 and total_profit >= PROFIT_TO_CLOSE:
        print(f"*** CLOSE ALL PROFIT ${total_profit:.2f} ***")
        for p in positions:
            tick = mt5.symbol_info_tick(SYMBOL)
            mt5.order_send({
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": SYMBOL,
                "volume": p.volume,
                "type": mt5.ORDER_TYPE_SELL,
                "position": p.ticket,
                "price": tick.bid,
                "deviation": 100,
                "magic": 777,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            })
        # After win, increase target like video $0.50 -> $1 -> $2.5
        PROFIT_TO_CLOSE = round(min(PROFIT_TO_CLOSE * 1.8, 5.0), 2)
        time.sleep(3)
        continue

    # 2. GRID - Buy first or buy when price drops
    if count == 0:
        buy_now()
    else:
        lowest_open = min([p.price_open for p in positions])
        current_price = mt5.symbol_info_tick(SYMBOL).bid
        drop = lowest_open - current_price
        if drop >= GRID_DOLLARS:
            buy_now()

    time.sleep(4)
