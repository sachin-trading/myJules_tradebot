import time
import config
import auth
import strategy
import utils
import datetime

class TradeBot:
    def __init__(self):
        self.access_token = auth.load_access_token()
        if not self.access_token:
            print("Access token not found. Run auth.py first.")
            exit(1)
        
        self.fyers = auth.get_fyers_instance(self.access_token)
        # For EMA Crossover (single position)
        self.current_position = None  # None, 'LONG', 'SHORT'
        self.active_symbol = None
        self.entry_price = 0

        # For MMR (multiple positions)
        self.mmr_positions = {} # symbol -> {side, entry, qty, sl, target, capital}
        self.used_capital = 0

    def get_market_price(self, symbol):
        data = {"symbols": symbol}
        response = self.fyers.quotes(data=data)
        return utils.parse_market_data(response, symbol)

    def place_order(self, symbol, side, qty):
        """
        side: 1 for Buy, -1 for Sell
        """
        data = {
            "symbol": symbol,
            "qty": qty,
            "type": 2,  # Market order
            "side": side,
            "productType": "INTRADAY",
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
        }
        response = self.fyers.place_order(data=data)
        print(f"Order placed for {symbol}: {response}")
        return response

    def run_ema_crossover(self):
        print("Starting EMA Crossover Strategy...")
        underlying = config.SYMBOL_UNDERLYING
        
        while True:
            try:
                # Check for signals
                signal = strategy.get_current_signal(self.fyers, underlying)
                current_price = self.get_market_price(underlying)

                if current_price:
                    print(f"[{datetime.datetime.now()}] {underlying} Price: {current_price}, Signal: {signal}")

                # Check for SL/Target
                if self.current_position and self.active_symbol and self.entry_price and self.entry_price > 0:
                    option_price = self.get_market_price(self.active_symbol)
                    if option_price:
                        target_price = self.entry_price * (1 + config.TARGET_PCT / 100)
                        sl_price = self.entry_price * (1 - config.STOP_LOSS_PCT / 100)

                        print(f"Checking SL/Target for {self.active_symbol}: Current {option_price}, Target {target_price:.2f}, SL {sl_price:.2f}")

                        if option_price >= target_price:
                            print(f"Target Hit! Exiting {self.active_symbol}")
                            self.place_order(self.active_symbol, -1, config.LOT_SIZE)
                            self.current_position = None
                            self.active_symbol = None
                            self.entry_price = 0
                        elif option_price <= sl_price:
                            print(f"Stop Loss Hit! Exiting {self.active_symbol}")
                            self.place_order(self.active_symbol, -1, config.LOT_SIZE)
                            self.current_position = None
                            self.active_symbol = None
                            self.entry_price = 0

                if signal == 'BULLISH' and self.current_position != 'LONG':
                    # Exit previous short if any
                    if self.current_position == 'SHORT' and self.active_symbol:
                        print("Exiting Short Position...")
                        self.place_order(self.active_symbol, -1, config.LOT_SIZE)
                    
                    # Entry Long (Buy Call)
                    strike = utils.get_atm_strike(current_price)
                    # Use the expiry from config
                    option_symbol = utils.get_option_symbol("CRUDEOILM", config.SYMBOL_EXPIRY, strike, "CE")
                    print(f"Bullish Signal! Buying {option_symbol}")
                    self.place_order(option_symbol, 1, config.LOT_SIZE)
                    self.current_position = 'LONG'
                    self.active_symbol = option_symbol
                    self.entry_price = self.get_market_price(option_symbol) or 0
                    print(f"Entered LONG at {self.entry_price}")

                elif signal == 'BEARISH' and self.current_position != 'SHORT':
                    # Exit previous long if any
                    if self.current_position == 'LONG' and self.active_symbol:
                        print("Exiting Long Position...")
                        self.place_order(self.active_symbol, -1, config.LOT_SIZE)
                    
                    # Entry Short (Buy Put)
                    strike = utils.get_atm_strike(current_price)
                    option_symbol = utils.get_option_symbol("CRUDEOILM", config.SYMBOL_EXPIRY, strike, "PE")
                    print(f"Bearish Signal! Buying {option_symbol}")
                    self.place_order(option_symbol, 1, config.LOT_SIZE)
                    self.current_position = 'SHORT'
                    self.active_symbol = option_symbol
                    self.entry_price = self.get_market_price(option_symbol) or 0
                    print(f"Entered SHORT at {self.entry_price}")

                # Sleep for 1 minute before next check
                time.sleep(60)
                
            except Exception as e:
                print(f"Error in bot loop: {e}")
                time.sleep(10)

    def run_mmr(self):
        print("Starting MMR Strategy...")
        index_symbol = config.MMR_INDEX_SYMBOL

        while True:
            try:
                now = datetime.datetime.now()
                range_to = now.strftime('%Y-%m-%d')
                range_from = (now - datetime.timedelta(days=5)).strftime('%Y-%m-%d')

                # 1. Fetch Index Data
                index_data = strategy.get_historical_data(self.fyers, index_symbol, config.MMR_INTERVAL, range_from, range_to)
                if index_data is None:
                    print("Failed to fetch index data. Retrying...")
                    time.sleep(10)
                    continue

                index_data = strategy.add_mmr_indicators(index_data)

                # 2. Iterate through stocks
                for symbol in config.MMR_STOCKS:
                    # Check if already in position
                    if symbol in self.mmr_positions:
                        pos = self.mmr_positions[symbol]
                        curr_price = self.get_market_price(symbol)

                        if not curr_price: continue

                        # Check SL/Target
                        exit_price = None
                        if pos['side'] == 'BUY':
                            if curr_price <= pos['sl']:
                                exit_price = pos['sl']
                                print(f"SL Hit for {symbol} (BUY)")
                            elif curr_price >= pos['target']:
                                exit_price = pos['target']
                                print(f"Target Hit for {symbol} (BUY)")
                        else: # SELL
                            if curr_price >= pos['sl']:
                                exit_price = pos['sl']
                                print(f"SL Hit for {symbol} (SELL)")
                            elif curr_price <= pos['target']:
                                exit_price = pos['target']
                                print(f"Target Hit for {symbol} (SELL)")

                        # Time-based exit (15:10 IST)
                        if now.time() >= datetime.time(15, 10):
                            exit_price = curr_price
                            print(f"End of day exit for {symbol}")

                        if exit_price:
                            self.place_order(symbol, -1 if pos['side'] == 'BUY' else 1, pos['qty'])
                            self.used_capital -= pos['capital']
                            del self.mmr_positions[symbol]
                            continue

                    else:
                        # Entry Logic
                        if self.used_capital >= config.MAX_CAPITAL:
                            continue

                        stock_data = strategy.get_historical_data(self.fyers, symbol, config.MMR_INTERVAL, range_from, range_to)
                        if stock_data is None: continue

                        stock_data = strategy.add_mmr_indicators(stock_data)
                        signal = strategy.get_mmr_signal(stock_data, index_data)

                        if signal:
                            stock_row = stock_data.iloc[-1]
                            close = stock_row['close']
                            atr = stock_row['ATR']
                            sl_dist = atr * config.MMR_SL_ATR_MULT
                            qty = utils.calculate_mmr_qty(config.MAX_CAPITAL, config.RISK_PER_TRADE_PCT, sl_dist)

                            if qty <= 0: continue

                            capital_required = qty * close
                            if self.used_capital + capital_required > config.MAX_CAPITAL:
                                continue

                            side = 1 if signal == 'BUY' else -1
                            print(f"MMR {signal} signal for {symbol}. Qty: {qty}")
                            self.place_order(symbol, side, qty)

                            self.mmr_positions[symbol] = {
                                "side": signal,
                                "entry": close,
                                "qty": qty,
                                "sl": close - sl_dist if signal == 'BUY' else close + sl_dist,
                                "target": close + atr * config.MMR_TARGET_ATR_MULT if signal == 'BUY' else close - atr * config.MMR_TARGET_ATR_MULT,
                                "capital": capital_required
                            }
                            self.used_capital += capital_required

                    # Rate limiting: small sleep between stocks to avoid hitting API limits
                    time.sleep(0.5)

                # Wait for next interval
                time.sleep(60)

            except Exception as e:
                print(f"Error in MMR loop: {e}")
                time.sleep(10)

    def run(self):
        if config.STRATEGY == "MMR":
            self.run_mmr()
        else:
            self.run_ema_crossover()

if __name__ == "__main__":
    bot = TradeBot()
    bot.run()
