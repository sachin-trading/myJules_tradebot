# Crude Oil Mini Options Trading Bot (Fyers API V3)

This is a sample trading bot for Crude Oil Mini options using the Fyers API V3. It uses an EMA Crossover strategy on the Crude Oil Mini futures to trigger option trades.

## Strategy: EMA Crossover
- **Underlying**: Crude Oil Mini Futures (MCX).
- **Timeframe**: 5 Minutes.
- **Signal**: 
  - **Bullish**: 9 EMA crosses above 21 EMA. -> **Action**: Buy At-The-Money (ATM) Call Option.
  - **Bearish**: 9 EMA crosses below 21 EMA. -> **Action**: Buy At-The-Money (ATM) Put Option.
- **Exit**: Position is exited when an opposite crossover occurs.

## Prerequisites
- Python 3.8+
- Fyers Trading Account
- API App created on Fyers API Dashboard (V3)

## Installation
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install fyers-apiv3 pandas numpy
   ```

## Setup
1. Open `config.py` and update your `APP_ID`, `SECRET_KEY`, and `REDIRECT_URI`.
2. Update the `SYMBOL_UNDERLYING` and `SYMBOL_EXPIRY` in `config.py` to match the current active contracts.

## How to Run
1. **Authentication**: Run `auth.py` to generate your access token.
   ```bash
   python auth.py
   ```
   Follow the instructions in the terminal to login and paste the `auth_code`. This will save an `access_token.txt` file.

2. **Start the Bot**: Run `bot.py` to start the trading bot.
   ```bash
   python bot.py
   ```

## Project Structure
- `config.py`: Configuration parameters.
- `auth.py`: Authentication and token management.
- `strategy.py`: EMA Crossover logic.
- `utils.py`: Utility functions for symbol generation and ATM strike calculation.
- `bot.py`: Main entry point and trade execution loop.

## Disclaimer
This is a sample bot for educational purposes. Algorithmic trading involves significant risk. Always test your strategies in a paper trading environment before using real capital. The author is not responsible for any financial losses incurred using this code.
