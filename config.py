# Fyers API Credentials
APP_ID = "WQPNJZHYO1-100"  # Replace with your App ID
SECRET_KEY = "PUF02F01IT"  # Replace with your Secret Key
REDIRECT_URI = "https://www.google.com"  # Replace with your Redirect URI

# Common Strategy Parameters
TIME_FRAME = "5"  # 5 Minutes
EMA_FAST = 9
EMA_SLOW = 21

# Trading Parameters
LOT_SIZE = 1  # Number of lots to trade
STOP_LOSS_PCT = 0.5  # 0.5% stop loss
TARGET_PCT = 1.0  # 1.0% target

# Nifty Settings
NIFTY_SYMBOL = "NSE:NIFTY50-INDEX"
NIFTY_EXPIRY = "25FEB"
NIFTY_STRIKE_INTERVAL = 50
NIFTY_WINDOW = ("09:30", "15:10")

# Crude Oil Settings
CRUDE_SYMBOL = "MCX:CRUDEOILM26FEBFUT"
CRUDE_EXPIRY = "26FEB"
CRUDE_STRIKE_INTERVAL = 100
CRUDE_WINDOW = ("15:30", "23:10")

# File paths
TOKEN_FILE = "access_token.txt"
