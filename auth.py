import os
from fyers_apiv3 import fyersModel
import config

def get_fyers_instance(access_token=None):
    """
    Returns an instance of FyersModel.
    """
    return fyersModel.FyersModel(
        client_id=config.APP_ID, 
        token=access_token, 
        is_async=False, 
        log_path=""
    )

def get_auth_url():
    """
    Generates the URL for getting the auth code.
    """
    session = fyersModel.SessionModel(
        client_id=config.APP_ID,
        redirect_uri=config.REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code"
    )
    return session.generate_authcode()

def generate_access_token(auth_code):
    """
    Generates the access token using the auth code.
    """
    session = fyersModel.SessionModel(
        client_id=config.APP_ID,
        secret_key=config.SECRET_KEY,
        redirect_uri=config.REDIRECT_URI,
        grant_type="authorization_code"
    )
    session.set_token(auth_code)
    response = session.generate_token()
    
    if "access_token" in response:
        with open(config.TOKEN_FILE, "w") as f:
            f.write(response["access_token"])
        return response["access_token"]
    else:
        print("Error generating access token:", response)
        return None

def load_access_token():
    """
    Loads the access token from the token file.
    """
    if os.path.exists(config.TOKEN_FILE):
        with open(config.TOKEN_FILE, "r") as f:
            return f.read().strip()
    return None

if __name__ == "__main__":
    # If run directly, help the user get the token
    if not load_access_token():
        print("Access token not found. Please follow these steps:")
        print("1. Go to this URL and login:", get_auth_url())
        print("2. After login, you will be redirected to your redirect URI.")
        print("3. Copy the 'auth_code' from the URL.")
        auth_code = input("Enter the auth_code: ")
        token = generate_access_token(auth_code)
        if token:
            print("Access token generated and saved successfully.")
    else:
        print("Access token already exists.")
