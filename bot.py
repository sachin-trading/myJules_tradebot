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

    def run(self):
        print("Starting TradeBot...")
        underlying = config.SYMBOL_UNDERLYING
        
        while True:
            try:
                # Check for signals
                signal = strategy.get_current_signal(self.fyers, underlying)
                current_price = self.get_market_price(underlying)
                signal = 'BEARISH'

                if current_price:
                    print(f"[{datetime.datetime.now()}] {underlying} Price: {current_price}, Signal: {signal}")
                
                if signal == 'BULLISH' and self.current_position != 'LONG':
                    # Exit previous short if any
                    if self.current_position == 'SHORT':
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

                elif signal == 'BEARISH' and self.current_position != 'SHORT':
                    # Exit previous long if any
                    if self.current_position == 'LONG':
                        print("Exiting Long Position...")
                        self.place_order(self.active_symbol, -1, config.LOT_SIZE)
                    
                    # Entry Short (Buy Put)
                    strike = utils.get_atm_strike(current_price)
                    option_symbol = utils.get_option_symbol("CRUDEOILM", config.SYMBOL_EXPIRY, strike, "PE")
                    print(f"Bearish Signal! Buying {option_symbol}")
                    self.place_order(option_symbol, 1, config.LOT_SIZE)
                    self.current_position = 'SHORT'
                    self.active_symbol = option_symbol

                # Sleep for 1 minute before next check
                time.sleep(60)
                
            except Exception as e:
                print(f"Error in bot loop: {e}")
                time.sleep(10)

if __name__ == "__main__":
    bot = TradeBot()
    bot.run()
