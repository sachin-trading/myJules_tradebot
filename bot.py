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
        self.current_position = None  # None, 'LONG', 'SHORT'
        self.active_symbol = None
        self.entry_price = 0
        self.current_underlying = None

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

    def is_in_window(self, window):
        now = datetime.datetime.now().time()
        start = datetime.datetime.strptime(window[0], "%H:%M").time()
        end = datetime.datetime.strptime(window[1], "%H:%M").time()
        return start <= now <= end

    def get_active_config(self):
        if self.is_in_window(config.NIFTY_WINDOW):
            return {
                "underlying": config.NIFTY_SYMBOL,
                "expiry": config.NIFTY_EXPIRY,
                "strike_interval": config.NIFTY_STRIKE_INTERVAL,
                "base": "NIFTY",
                "exchange": "NSE"
            }
        elif self.is_in_window(config.CRUDE_WINDOW):
            return {
                "underlying": config.CRUDE_SYMBOL,
                "expiry": config.CRUDE_EXPIRY,
                "strike_interval": config.CRUDE_STRIKE_INTERVAL,
                "base": "CRUDEOILM",
                "exchange": "MCX"
            }
        return None

    def run(self):
        print("Starting TradeBot...")
        
        while True:
            try:
                active_cfg = self.get_active_config()

                if not active_cfg:
                    if self.current_position and self.active_symbol:
                        print("Outside trading windows. Closing open positions...")
                        self.place_order(self.active_symbol, -1, config.LOT_SIZE)
                        self.current_position = None
                        self.active_symbol = None
                        self.entry_price = 0
                        self.current_underlying = None

                    print(f"[{datetime.datetime.now()}] Outside trading hours. Waiting...")
                    time.sleep(60)
                    continue

                underlying = active_cfg["underlying"]

                # If we switched instruments, close old position
                if self.current_underlying and self.current_underlying != underlying:
                    if self.current_position and self.active_symbol:
                        print(f"Switching instrument. Closing {self.active_symbol}")
                        self.place_order(self.active_symbol, -1, config.LOT_SIZE)
                        self.current_position = None
                        self.active_symbol = None
                        self.entry_price = 0

                self.current_underlying = underlying

                # Check for signals
                signal = strategy.get_current_signal(self.fyers, underlying)
                current_price = self.get_market_price(underlying)

                if current_price:
                    print(f"[{datetime.datetime.now()}] {underlying} Price: {current_price}, Signal: {signal}")

                # Check for SL/Target
                if self.current_position and self.active_symbol:
                    # If entry price is missing, try to fetch it
                    if not self.entry_price or self.entry_price <= 0:
                        self.entry_price = self.get_market_price(self.active_symbol) or 0
                        if self.entry_price > 0:
                            print(f"Recovered entry price for {self.active_symbol}: {self.entry_price}")

                    if self.entry_price > 0:
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
                    strike = utils.get_atm_strike(current_price, active_cfg["strike_interval"])
                    option_symbol = utils.get_option_symbol(active_cfg["exchange"], active_cfg["base"], active_cfg["expiry"], strike, "CE")
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
                    strike = utils.get_atm_strike(current_price, active_cfg["strike_interval"])
                    option_symbol = utils.get_option_symbol(active_cfg["exchange"], active_cfg["base"], active_cfg["expiry"], strike, "PE")
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

if __name__ == "__main__":
    bot = TradeBot()
    bot.run()
