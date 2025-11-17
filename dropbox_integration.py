"""
Dropbox Integration Module
==========================
Handles token refresh and financial data streaming
"""

import os
import json
import requests
import dropbox
import pandas as pd
from io import BytesIO
from contextlib import closing
from dotenv import load_dotenv
import streamlit as st

# Load environment variables
load_dotenv()

# Dropbox OAuth2 credentials
DROPBOX_APP_KEY = st.secrets.get("DROPBOX_APP_KEY", os.getenv("DROPBOX_APP_KEY"))
DROPBOX_APP_SECRET = st.secrets.get("DROPBOX_APP_SECRET", os.getenv("DROPBOX_APP_SECRET"))
DROPBOX_REFRESH_TOKEN = st.secrets.get("DROPBOX_REFRESH_TOKEN", os.getenv("DROPBOX_REFRESH_TOKEN"))

try:
    DROPBOX_TOKEN = st.secrets.get("DROPBOX_TOKEN", os.getenv("DROPBOX_TOKEN", None))
except:
    DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN", None)

# Dropbox file paths
DROPBOX_PATHS = {
    'financial_statements': '/volkfs.xlsx',
    'dataset': '/datasetincro1.xlsx',
    'portfolio': '/db.xlsx',
    'wacc': '/wacc.xlsx',
    'contacts': '/contacts.xlsx'
}

def retrieve_dropbox_access_token(app_key, app_secret, refresh_token):
    """
    Retrieve fresh Dropbox access token using OAuth2 refresh token

    Args:
        app_key (str): Dropbox application key
        app_secret (str): Dropbox application secret
        refresh_token (str): Long-lived refresh token

    Returns:
        str: Fresh access token or None if failed
    """
    data = {
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'client_id': app_key,
        'client_secret': app_secret,
    }

    try:
        response = requests.post('https://api.dropbox.com/oauth2/token', data=data)
        response.raise_for_status()
        response_data = json.loads(response.text)
        return response_data.get("access_token")
    except Exception as e:
        return None

def get_dropbox_token():
    """Get valid Dropbox token (with auto-refresh)"""
    global DROPBOX_TOKEN

    # Try OAuth2 refresh first
    if DROPBOX_APP_KEY and DROPBOX_APP_SECRET and DROPBOX_REFRESH_TOKEN:
        token = retrieve_dropbox_access_token(
            DROPBOX_APP_KEY,
            DROPBOX_APP_SECRET,
            DROPBOX_REFRESH_TOKEN
        )
        if token:
            DROPBOX_TOKEN = token
            return token

    # Fallback to stored token
    return DROPBOX_TOKEN

def initialize_dropbox():
    """Initialize Dropbox client"""
    token = get_dropbox_token()

    if not token:
        return None

    try:
        dbx = dropbox.Dropbox(token)
        dbx.users_get_current_account()
        return dbx
    except:
        return None

def stream_dropbox_file(dropbox_path: str) -> pd.DataFrame:
    """Stream a file directly from Dropbox"""
    try:
        dbx = initialize_dropbox()
        if dbx is None:
            return None

        _, res = dbx.files_download(dropbox_path)

        with closing(res) as result:
            byte_data = result.content
            file_stream = BytesIO(byte_data)
            df = pd.read_excel(file_stream, engine='openpyxl')
            return df
    except:
        return None

def load_all_data_from_dropbox():
    """Load all financial data from Dropbox"""
    data_dict = {}

    # Load Dataset (required)
    dataset_df = stream_dropbox_file(DROPBOX_PATHS['dataset'])
    if dataset_df is not None:
        data_dict['dataset'] = dataset_df
    else:
        raise Exception("Failed to load dataset from Dropbox")

    # Load WACC (required)
    wacc_df = stream_dropbox_file(DROPBOX_PATHS['wacc'])
    if wacc_df is not None:
        data_dict['wacc'] = wacc_df
    else:
        raise Exception("Failed to load WACC from Dropbox")

    # Load Portfolio (optional)
    portfolio_df = stream_dropbox_file(DROPBOX_PATHS['portfolio'])
    data_dict['portfolio'] = portfolio_df

    # Load Financial Statements (optional)
    fs_df = stream_dropbox_file(DROPBOX_PATHS['financial_statements'])
    data_dict['financial_statements'] = fs_df

    # Load Contacts (optional)
    contacts_df = stream_dropbox_file(DROPBOX_PATHS['contacts'])
    data_dict['contacts'] = contacts_df

    return data_dict
