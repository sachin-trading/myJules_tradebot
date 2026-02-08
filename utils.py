import config

def get_atm_strike(current_price, strike_interval=50):
    """
    Calculates the ATM strike price based on the current price.
    """
    return round(current_price / strike_interval) * strike_interval

def get_option_symbol(underlying_base, expiry_date, strike, option_type):
    """
    Generates the Fyers option symbol.
    Format: MCX:CRUDEOILM<YY><MMM><STRIKE><CE/PE>
    Example: MCX:CRUDEOILM25JAN6500CE
    Note: expiry_date should be in YYMMM format like '25JAN'
    """
    return f"MCX:{underlying_base}{expiry_date}{strike}{option_type}"

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

def calculate_mmr_qty(capital, risk_pct, sl_dist):
    """
    Calculates quantity based on risk per trade.
    """
    risk_amount = capital * risk_pct
    if sl_dist == 0:
        return 0
    return int(risk_amount / sl_dist)
