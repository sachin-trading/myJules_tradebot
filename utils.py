import config

def get_atm_strike(current_price, strike_interval=50):
    """
    Calculates the ATM strike price based on the current price.
    """
    return round(current_price / strike_interval) * strike_interval

def get_option_symbol(exchange, underlying_base, expiry_date, strike, option_type):
    """
    Generates the Fyers option symbol.
    Format: {EXCHANGE}:{UNDERLYING}{EXPIRY}{STRIKE}{CE/PE}
    Example: MCX:CRUDEOILM25JAN6500CE, NSE:NIFTY25FEB23500CE
    """
    return f"{exchange}:{underlying_base}{expiry_date}{strike}{option_type}"

def parse_market_data(response, symbol):
    """
    Parses the quotes response to get the last traded price.
    """
    if response and response.get('s') == 'ok':
        data = response.get('d', [])
        for item in data:
            if item.get('n') == symbol:
                return item.get('v', {}).get('lp')
    return None
