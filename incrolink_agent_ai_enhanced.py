
# ============================================================================
# INTEGRATED AI AGENT WITH LLAMA.CPP - FINANCIAL PLATFORM
# ============================================================================
# This file integrates llama.cpp local LLM capabilities with the existing
# financial analysis platform infrastructure. All original function logic
# is preserved while adding AI agent interface for chat and analysis tasks.
# ============================================================================

import streamlit as st
import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from datetime import datetime
import pathlib
import io
import os
from contextlib import closing
import dropbox
from dotenv import load_dotenv
import json
import requests
from typing import Optional, List, Dict, Any
import logging

# ============================================================================
# LLAMA.CPP AI AGENT INITIALIZATION (NEW)
# ============================================================================
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logging.warning("llama-cpp-python not installed. Install with: pip install llama-cpp-python")

# ============================================================================
# CUSTOM STYLING - Modern Design with White Sidebar & Shadow
# ============================================================================

def load_css(file_path):
    try:
        with open(file_path) as f:
            st.html(f"<style>{f.read()}</style>")
    except FileNotFoundError:
        st.warning(f"CSS file not found: {file_path}")

css_path = pathlib.Path("style.css")
load_css(css_path)

# ============================================================================
# DROPBOX API CONFIGURATION WITH TOKEN REFRESH (STREAMLIT SECRETS STRATEGY)
# ============================================================================

load_dotenv()

# Primary: Try Streamlit secrets (production), fallback to environment variables (development)
DROPBOX_APP_KEY = st.secrets.get("DROPBOX_APP_KEY", os.getenv("DROPBOX_APP_KEY"))
DROPBOX_APP_SECRET = st.secrets.get("DROPBOX_APP_SECRET", os.getenv("DROPBOX_APP_SECRET"))
DROPBOX_REFRESH_TOKEN = st.secrets.get("DROPBOX_REFRESH_TOKEN", os.getenv("DROPBOX_REFRESH_TOKEN"))

try:
    DROPBOX_TOKEN = st.secrets.get("DROPBOX_TOKEN", os.getenv("DROPBOX_TOKEN", None))
except:
    DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN", None)

# AI Model configuration from Streamlit secrets
LLAMA_MODEL_PATH = st.secrets.get("LLAMA_MODEL_PATH", os.getenv("LLAMA_MODEL_PATH", "./models/model.gguf"))
LLAMA_N_GPU_LAYERS = st.secrets.get("LLAMA_N_GPU_LAYERS", os.getenv("LLAMA_N_GPU_LAYERS", 0))
LLAMA_N_CTX = st.secrets.get("LLAMA_N_CTX", os.getenv("LLAMA_N_CTX", 2048))
LLAMA_TEMPERATURE = st.secrets.get("LLAMA_TEMPERATURE", os.getenv("LLAMA_TEMPERATURE", 0.7))

def retrieve_dropbox_access_token(app_key, app_secret, refresh_token):
    """
    Retrieve fresh Dropbox access token using OAuth2 refresh token
    Args:
        app_key (str): Dropbox application key
        app_secret (str): Dropbox application secret
        refresh_token (str): Long-lived refresh token
    Returns:
        str: Fresh access token for current session
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
        access_token = response_data["access_token"]
        return access_token
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Failed to retrieve Dropbox access token: {str(e)}")
        return None

# Generate access token at module load (internal, not exposed)
DROPBOX_TOKEN = None
if DROPBOX_APP_KEY and DROPBOX_APP_SECRET and DROPBOX_REFRESH_TOKEN:
    DROPBOX_TOKEN = retrieve_dropbox_access_token(
        DROPBOX_APP_KEY,
        DROPBOX_APP_SECRET,
        DROPBOX_REFRESH_TOKEN
    )

if not DROPBOX_TOKEN:
    # Fallback: Try to get token from Streamlit secrets or environment variable (backward compatibility)
    try:
        DROPBOX_TOKEN = st.secrets.get("dropbox_token", os.getenv("DROPBOX_TOKEN", None))
    except:
        DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN", None)

# Dropbox file paths (not URLs)
DROPBOX_PATHS = {
    'financial_statements': '/volkfs.xlsx',
    'dataset': '/datasetincro1.xlsx',
    'portfolio': '/db.xlsx',
    'wacc': '/wacc.xlsx',
    'contacts': '/contacts.xlsx'
}

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

COLUMNS_REQUIRED = [
    "company", "nace", "ebit", "employees", "net income", "capex", "d&a",
    "changes in wc", "lt debt", "st debt", "sh equity", "capital equity", "cash", "category_code"
]

COLUMNS_PORTFOLIO = [
    "company", "nace", "ebit", "employees", "net income", "capex", "d&a",
    "changes in wc", "lt debt", "st debt", "sh equity", "capital equity", "cash", "category_code"
]

FINANCIAL_ITEMS = {
    'long_term_debt': 'Long term debt',
    'shareholders_funds': 'Shareholders funds',
    'operating_revenue': 'Operating revenue (Turnover)',
    'cost_of_employees': 'Costs of employees',
    'ebitda': 'EBITDA'
}

PREDICTABILITY_CATEGORIES = {
    "0": "low growth",
    "0,23": "good growth, low sell side operations",
    "0,43": "good financials and sector conditions, but Management too young",
    "0,54": "good company and sector conditions, but revenue is too small",
    "0,65": "optimal conditions, but margins are weak",
    "0,8": "optimal conditions"
}

# ============================================================================
# LLAMA.CPP AI AGENT CLASS (NEW)
# ============================================================================

class LlamaFinanceAgent:
    """AI Agent using llama.cpp for financial analysis and chat"""

    def __init__(self, model_path: str = LLAMA_MODEL_PATH, n_gpu_layers: int = LLAMA_N_GPU_LAYERS):
        """
        Initialize the Llama finance agent

        Args:
            model_path: Path to GGUF model file
            n_gpu_layers: Number of layers to offload to GPU (-1 for all)
        """
        self.model_path = model_path
        self.n_gpu_layers = n_gpu_layers
        self.llm = None
        self.conversation_history = []
        self.initialized = False

    def initialize(self) -> bool:
        """Initialize the llama.cpp model"""
        if not LLAMA_CPP_AVAILABLE:
            logging.error("llama-cpp-python not available")
            return False

        if not os.path.exists(self.model_path):
            logging.error(f"Model file not found: {self.model_path}")
            return False

        try:
            self.llm = Llama(
                model_path=self.model_path,
                n_gpu_layers=self.n_gpu_layers,
                n_ctx=int(LLAMA_N_CTX),
                verbose=False,
                chat_format="chatml"
            )
            self.initialized = True
            logging.info(f"llama.cpp model loaded successfully: {self.model_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize llama.cpp: {str(e)}")
            return False

    def generate_response(
        self, 
        user_message: str, 
        system_prompt: str = None,
        max_tokens: int = 512,
        temperature: float = float(LLAMA_TEMPERATURE)
    ) -> str:
        """
        Generate response using llama.cpp

        Args:
            user_message: User's input message
            system_prompt: System context/instructions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Generated response text
        """
        if not self.initialized or self.llm is None:
            return "Error: AI model not initialized"

        try:
            # Build message history
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add conversation history (limited to last 5 exchanges to preserve context)
            for msg in self.conversation_history[-10:]:
                messages.append(msg)

            # Add current user message
            messages.append({"role": "user", "content": user_message})

            # Generate completion
            response = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
                top_k=40
            )

            generated_text = response["choices"][0]["message"]["content"]

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": generated_text})

            return generated_text

        except Exception as e:
            logging.error(f"Error generating response: {str(e)}")
            return f"Error: {str(e)}"

    def analyze_company(self, company_data: Dict[str, Any]) -> str:
        """Analyze company financial data using AI"""
        company_info = f"""
        Company: {company_data.get('company', 'N/A')}
        EBIT: €{company_data.get('ebit', 0):,.2f}
        Net Income: €{company_data.get('net income', 0):,.2f}
        Employees: {company_data.get('employees', 'N/A')}
        Long-term Debt: €{company_data.get('lt debt', 0):,.2f}
        Shareholders Equity: €{company_data.get('sh equity', 0):,.2f}
        """

        system_prompt = """You are a financial analyst specializing in company valuation and analysis. 
        Provide concise, professional analysis based on the financial metrics provided."""

        user_message = f"Analyze this company:\n{company_info}"

        return self.generate_response(user_message, system_prompt)

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []

    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.conversation_history.copy()

# ============================================================================
# DROPBOX API FUNCTIONS - OPTIMIZED WITH BETTER ERROR HANDLING
# ============================================================================

def initialize_dropbox():
    """Initialize Dropbox client"""
    if not DROPBOX_TOKEN:
        return None

    try:
        dbx = dropbox.Dropbox(DROPBOX_TOKEN)
        # Test the connection
        dbx.users_get_current_account()
        return dbx
    except dropbox.exceptions.AuthError as e:
        st.error(f"❌ Dropbox authentication failed: Invalid token")
        return None
    except Exception as e:
        st.error(f"❌ Dropbox connection error: {str(e)}")
        return None

def stream_dropbox_file(dropbox_path):
    """
    Stream a file directly from Dropbox using the Dropbox API.
    Args:
        dropbox_path (str): Path to file in Dropbox (e.g., '/folder/file.xlsx')
    Returns:
        pandas.DataFrame or None: DataFrame if successful, None otherwise
    """
    try:
        dbx = initialize_dropbox()
        if dbx is None:
            return None

        # Download file from Dropbox
        _, res = dbx.files_download(dropbox_path)

        # Use closing context manager to properly handle response
        with closing(res) as result:
            byte_data = result.content
            # Create BytesIO stream
            file_stream = io.BytesIO(byte_data)
            # Read Excel file with explicit engine
            df = pd.read_excel(file_stream, engine='openpyxl')
            return df

    except dropbox.exceptions.ApiError as e:
        st.error(f"❌ Dropbox API error: {str(e)}")
        return None
    except ValueError as e:
        st.error(f"❌ File format error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ Error loading file from Dropbox: {str(e)}")
        return None

def load_all_data_from_dropbox():
    """Load all data files from Dropbox using the API"""
    with st.spinner("🔄 Loading data from Dropbox..."):
        data_dict = {}

        # Load Dataset
        st.write("📂 Loading Dataset...")
        dataset_df = stream_dropbox_file(DROPBOX_PATHS['dataset'])
        if dataset_df is not None:
            st.success("✅ Dataset loaded successfully")
            data_dict['dataset'] = dataset_df
        else:
            st.error("❌ Failed to load Dataset")
            return None

        # Load WACC
        st.write("📂 Loading WACC File...")
        wacc_df = stream_dropbox_file(DROPBOX_PATHS['wacc'])
        if wacc_df is not None:
            st.success("✅ WACC file loaded successfully")
            data_dict['wacc'] = wacc_df
        else:
            st.error("❌ Failed to load WACC")
            return None

        # Load Portfolio (optional)
        st.write("📂 Loading Portfolio...")
        portfolio_df = stream_dropbox_file(DROPBOX_PATHS['portfolio'])
        if portfolio_df is not None:
            st.success("✅ Portfolio loaded successfully")
            data_dict['portfolio'] = portfolio_df
        else:
            st.warning("⚠️ Portfolio not loaded (optional)")
            data_dict['portfolio'] = None

        # Load Financial Statements (optional)
        st.write("📂 Loading Financial Statements...")
        fs_df = stream_dropbox_file(DROPBOX_PATHS['financial_statements'])
        if fs_df is not None:
            st.success("✅ Financial Statements loaded successfully")
            data_dict['financial_statements'] = fs_df
        else:
            st.warning("⚠️ Financial Statements not loaded (optional)")
            data_dict['financial_statements'] = None

        # Load Contacts (optional)
        st.write("📂 Loading Contacts...")
        contacts_df = stream_dropbox_file(DROPBOX_PATHS['contacts'])
        if contacts_df is not None:
            st.success("✅ Contacts loaded successfully")
            data_dict['contacts'] = contacts_df
        else:
            st.warning("⚠️ Contacts not loaded (optional)")
            data_dict['contacts'] = None

        return data_dict

# ============================================================================
# UTILITY FUNCTIONS (ALL ALGORITHMS UNCHANGED - FROM ORIGINAL)
# ============================================================================

def validate_columns(df, file_type="Dataset", required_cols=None):
    """Validate that the dataframe has all required columns"""
    if required_cols is None:
        required_cols = COLUMNS_REQUIRED
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"❌ {file_type} - Missing required columns: {', '.join(missing_cols)}")
        return False
    st.success(f"✅ {file_type} uploaded")
    return True

def extract_date_columns(df):
    """Extract date columns from dataframe (date format like 31/12/2024)"""
    date_cols = []
    for col in df.columns:
        if col == 'value':
            continue
        try:
            parsed_date = pd.to_datetime(col, format='%d/%m/%Y', errors='coerce')
            if pd.notna(parsed_date):
                date_cols.append((col, parsed_date))
        except:
            pass
    date_cols.sort(key=lambda x: x[1], reverse=True)
    return [col[0] for col in date_cols]

def find_financial_item(df, item_name):
    """Find a financial statement item by name (fuzzy matching)"""
    value_col = df.columns[0]
    if value_col not in df.columns:
        return None
    items = df[value_col].astype(str).tolist()
    matches = process.extract(item_name, items, scorer=fuzz.token_set_ratio, limit=1)
    if matches and matches[0][1] >= 60:
        matching_item = matches[0][0]
        row_idx = df[df[value_col] == matching_item].index
        if len(row_idx) > 0:
            return row_idx[0]
    return None

def extract_financial_statement_data(df, date_cols):
    """Extract financial data from financial statement format"""
    data = {}
    if not date_cols:
        return data, "No date columns found"
    latest_date = date_cols[0]
    try:
        value_col = df.columns[0]
        items_found = {}
        for key, item_name in FINANCIAL_ITEMS.items():
            row_idx = find_financial_item(df, item_name)
            if row_idx is not None:
                try:
                    value = df.loc[row_idx, latest_date]
                    if pd.notna(value):
                        items_found[key] = float(value)
                    else:
                        items_found[key] = np.nan
                except:
                    items_found[key] = np.nan
            else:
                items_found[key] = np.nan
        return items_found, latest_date
    except Exception as e:
        return data, f"Error extracting data: {str(e)}"

def calculate_ratios_from_financial_statement(items_found):
    """Calculate LTDE, EDAMARGIN, FX ratios from extracted financial statement data"""
    metrics = {}
    try:
        lt_debt = items_found.get('long_term_debt', np.nan)
        sh_funds = items_found.get('shareholders_funds', np.nan)
        if not pd.isna(sh_funds) and sh_funds != 0 and not pd.isna(lt_debt):
            metrics['ltde'] = lt_debt / sh_funds
        else:
            metrics['ltde'] = np.nan

        ebitda = items_found.get('ebitda', np.nan)
        op_revenue = items_found.get('operating_revenue', np.nan)
        if not pd.isna(op_revenue) and op_revenue != 0 and not pd.isna(ebitda):
            metrics['edamargin'] = ebitda / op_revenue
        else:
            metrics['edamargin'] = np.nan

        cost_emp = items_found.get('cost_of_employees', np.nan)
        if not pd.isna(op_revenue) and op_revenue != 0 and not pd.isna(cost_emp):
            metrics['fx'] = cost_emp / op_revenue
        else:
            metrics['fx'] = np.nan

        return metrics
    except Exception as e:
        st.error(f"Error calculating ratios: {str(e)}")
        return metrics

def calculate_metrics_from_dataset(company_row):
    """Calculate LTDE, FX, EDAMARGIN from dataset columns"""
    metrics = {}
    try:
        lt_debt = company_row.get('lt debt', np.nan)
        sh_equity = company_row.get('sh equity', np.nan)
        if not pd.isna(sh_equity) and sh_equity != 0 and not pd.isna(lt_debt):
            metrics['ltde'] = lt_debt / sh_equity
        else:
            metrics['ltde'] = np.nan

        ebit = company_row.get('ebit', np.nan)
        d_and_a = company_row.get('d&a', np.nan)
        metrics['edamargin'] = np.nan
        metrics['fx'] = np.nan

        return metrics
    except Exception as e:
        return {'ltde': np.nan, 'edamargin': np.nan, 'fx': np.nan}

def get_company_category_code(company_name, dataset_df):
    """Lookup company's category_code from dataset"""
    matching_companies = dataset_df[dataset_df['company'].str.contains(company_name, case=False, na=False)]
    if not matching_companies.empty:
        category_code = matching_companies.iloc[0]['category_code']
        return category_code
    return None

def get_sector_percentiles(category_code, waccmap):
    """Retrieve sector percentile ranges for LTDE, EDAMARGIN, FX"""
    percentiles = {}
    category_data = waccmap[waccmap['category_code'].astype(str) == str(category_code)]
    if not category_data.empty:
        row = category_data.iloc[0]
        percentiles['ltde'] = {
            'p10': row.get('ltde10th', np.nan),
            'p25': row.get('ltde25th', np.nan),
            'p50': row.get('ltde50th', np.nan),
            'p75': row.get('ltde75th', np.nan),
            'p90': row.get('ltde90th', np.nan)
        }

        percentiles['edamargin'] = {
            'p10': row.get('edamarg10th', np.nan),
            'p25': row.get('edamarg25th', np.nan),
            'p50': row.get('edamarg50th', np.nan),
            'p75': row.get('edamarg75th', np.nan),
            'p90': row.get('edamarg90th', np.nan)
        }

        percentiles['fx'] = {
            'p10': row.get('fx10th', np.nan),
            'p25': row.get('fx25th', np.nan),
            'p50': row.get('fx50th', np.nan),
            'p75': row.get('fx75th', np.nan),
            'p90': row.get('fx90th', np.nan)
        }

        percentiles['nsellside_p50'] = row.get('nsellside50th', np.nan)
        percentiles['nsellside'] = row.get('nsellside', np.nan)
        return percentiles

def get_percentile_position(value, percentiles_dict):
    """Calculate company's percentile position within sector range"""
    if np.isnan(value):
        return None, None, "N/A"

    p10 = percentiles_dict.get('p10', np.nan)
    p25 = percentiles_dict.get('p25', np.nan)
    p50 = percentiles_dict.get('p50', np.nan)
    p75 = percentiles_dict.get('p75', np.nan)
    p90 = percentiles_dict.get('p90', np.nan)

    if value < p10:
        position = "Below P10"
        rank = "Exceptional (Bottom)"
    elif value < p25:
        position = "P10-P25"
        rank = "Q1 (Very Low)"
    elif value < p50:
        position = "P25-P50"
        rank = "Q2 (Below Median)"
    elif value < p75:
        position = "P50-P75"
        rank = "Q3 (Above Median)"
    elif value < p90:
        position = "P75-P90"
        rank = "Q4 (High)"
    else:
        position = "Above P90"
        rank = "Exceptional (Top)"

    return position, rank, f"{p10:.4f} | {p25:.4f} | {p50:.4f} | {p75:.4f} | {p90:.4f}"

def display_metric_comparison(company_metrics, sector_percentiles, metric_name, metric_label):
    """Display metric with sector percentile comparison"""
    company_value = company_metrics.get(metric_name, np.nan)
    percentiles = sector_percentiles.get(metric_name, {})
    st.write(f"**{metric_label}**")
    if not np.isnan(company_value):
        position, rank, percentile_range = get_percentile_position(company_value, percentiles)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Company Value", f"{company_value:.4f}")
        with col2:
            st.metric("Sector Position", rank)
        with col3:
            st.metric("Percentile Range", position)
        st.write("**Sector Distribution (P10 | P25 | P50 | P75 | P90):**")
        st.write(percentile_range)
    else:
        st.metric(metric_label, "N/A")
    st.markdown("---")

def get_ceo_age(company_row, contacts_df):
    """Get CEO age from contacts file via companyID"""
    if contacts_df is None:
        return None
    if 'companyID' not in company_row.index:
        return None
    company_id = company_row['companyID']
    if 'companyID' not in contacts_df.columns:
        return None
    company_contacts = contacts_df[contacts_df['companyID'] == company_id]
    if company_contacts.empty:
        return None
    if 'CEO' in company_contacts.columns and 'age' in company_contacts.columns:
        ceo_row = company_contacts[company_contacts['CEO'].notna()]
        if not ceo_row.empty:
            try:
                return float(ceo_row.iloc[0]['age'])
            except:
                return None
    return None

def get_contacts_by_company_id(company_id, contacts_df):
    """Get all contacts for a company by companyID"""
    if contacts_df is None:
        return None
    if 'companyID' not in contacts_df.columns:
        return None
    company_contacts = contacts_df[contacts_df['companyID'] == company_id]
    return company_contacts if not company_contacts.empty else None

def get_contact_by_id(contact_id, contacts_df):
    """Get specific contact by contactID"""
    if contacts_df is None or 'contactID' not in contacts_df.columns:
        return None
    contact = contacts_df[contacts_df['contactID'] == contact_id]
    return contact.iloc[0] if not contact.empty else None

def get_related_contacts_by_relative(contact_id, contacts_df):
    """Get contacts that have relationship with given contact via 'relative' column"""
    if contacts_df is None:
        return None
    if 'contactID' not in contacts_df.columns or 'relative' not in contacts_df.columns:
        return None
    related = contacts_df[contacts_df['relative'] == contact_id]
    return related if not related.empty else None

def predictability_decision_tree(ev_growth, nsellside, nsellside_p50, ceo_age, revenue, edamargin, edamargin_p75):
    """Decision tree for predictability classification"""
    path = []
    path.append(f"EV Growth: {ev_growth:.2%}")

    if ev_growth < 0.15:
        return "0", PREDICTABILITY_CATEGORIES["0"], path

    path.append(f"N Sell Side: {nsellside} vs P50: {nsellside_p50}")
    if not np.isnan(nsellside) and not np.isnan(nsellside_p50) and nsellside < nsellside_p50:
        return "0,23", PREDICTABILITY_CATEGORIES["0,23"], path

    path.append(f"CEO Age: {ceo_age}")
    if ceo_age is not None and not np.isnan(ceo_age) and ceo_age < 60:
        return "0,43", PREDICTABILITY_CATEGORIES["0,43"], path

    path.append(f"Revenue: €{revenue:,.0f}")
    if not np.isnan(revenue) and revenue < 90000000:
        return "0,54", PREDICTABILITY_CATEGORIES["0,54"], path

    path.append(f"EDAMARGIN: {edamargin:.4f} vs P75: {edamargin_p75:.4f}")
    if not np.isnan(edamargin) and not np.isnan(edamargin_p75) and edamargin < edamargin_p75:
        return "0,65", PREDICTABILITY_CATEGORIES["0,65"], path

    return "0,8", PREDICTABILITY_CATEGORIES["0,8"], path

def nace_to_category(nace_code, nace_mapping=None):
    """Convert NACE code to category code using mapping"""
    if nace_mapping is None or nace_code not in nace_mapping.values:
        return None
    mapping_row = nace_mapping[nace_mapping['nace'] == nace_code]
    return mapping_row['category_code'].iloc[0] if not mapping_row.empty else None

def fuzzy_match_companies(portfolio_company, db_companies, threshold=80):
    """Find similar companies in database using fuzzy matching"""
    matches = process.extract(
        portfolio_company,
        db_companies['company'].tolist(),
        scorer=fuzz.token_set_ratio,
        limit=5
    )
    return [match for match in matches if match[1] >= threshold]

def DCF_automated(company_row, waccmap, years=5):
    """Calculate DCF valuation for a company"""
    sh_equity = company_row['sh equity']
    capital_equity = company_row['capital equity']
    lt_debt = company_row['lt debt']
    st_debt = company_row['st debt']
    cash = company_row['cash']

    EV_current = sh_equity + lt_debt + st_debt - cash

    category_code = str(company_row['category_code'])
    params_match = waccmap[waccmap['category_code'].astype(str) == category_code]

    if not params_match.empty:
        re = params_match.iloc[0]['re']
        rd = params_match.iloc[0]['rd']
        wacc = params_match.iloc[0]['wacc']
        g = params_match.iloc[0]['g']
    else:
        re = rd = wacc = g = np.nan

    net_income = company_row['net income']
    d_and_a = company_row['d&a']
    capex = company_row['capex']
    changes_in_wc = company_row['changes in wc']

    FCF0 = net_income + d_and_a - capex - changes_in_wc

    FCFs = [FCF0 * ((1 + g) ** n) for n in range(1, years + 1)]

    TV = FCFs[-1] / (wacc - g) if (wacc - g) != 0 else 0

    discount_factors = [(1 + wacc) ** n for n in range(1, years + 1)]

    discounted_FCFs = [f / d for f, d in zip(FCFs, discount_factors)]

    discounted_TV = TV / discount_factors[-1]

    EV_DCF = sum(discounted_FCFs) + discounted_TV

    growth_expected = (EV_DCF / EV_current) - 1 if EV_current else np.nan

    return {
        'EV_current': EV_current,
        'EV_DCF': EV_DCF,
        'growth_expected': growth_expected,
        'category_code': category_code,
        'params': dict(re=re, rd=rd, wacc=wacc, g=g),
        'FCF0': FCF0,
        'FCFs': FCFs,
        'TV': TV,
        'discounted_FCFs': discounted_FCFs,
        'discounted_TV': discounted_TV,
        'years': years
    }

# ============================================================================
# AI CHAT INTERFACE (NEW)
# ============================================================================

def show_ai_chat_interface():
    """Display AI chat interface for financial analysis"""
    st.subheader("🤖 AI Finance Assistant (Powered by llama.cpp)")

    # Initialize AI agent in session state
    if 'ai_agent' not in st.session_state:
        st.session_state.ai_agent = None

    if 'ai_initialized' not in st.session_state:
        st.session_state.ai_initialized = False

    # Initialize AI model
    if not st.session_state.ai_initialized and LLAMA_CPP_AVAILABLE:
        with st.spinner("Initializing AI model..."):
            agent = LlamaFinanceAgent()
            if agent.initialize():
                st.session_state.ai_agent = agent
                st.session_state.ai_initialized = True
                st.success("✅ AI model initialized successfully")
            else:
                st.error("❌ Failed to initialize AI model")
                st.info("Ensure llama.cpp is installed and model path is correct")
                return

    if not LLAMA_CPP_AVAILABLE:
        st.warning("⚠️ llama-cpp-python not installed. Install with: pip install llama-cpp-python")
        st.info("Then configure LLAMA_MODEL_PATH in Streamlit secrets or environment variables")
        return

    if st.session_state.ai_agent is None:
        return

    # Chat interface
    st.markdown("---")
    st.write("Ask me about financial analysis, company valuation, or DCF calculations!")

    # Display conversation history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    for i, msg in enumerate(st.session_state.chat_history):
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    # User input
    user_input = st.chat_input("Ask a financial question...")

    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        # Generate response
        system_prompt = """You are an expert financial analyst with deep knowledge of:
        - DCF valuation and financial modeling
        - Company financial metrics and ratios
        - Sector benchmarking and comparative analysis
        - M&A and investment analysis
        Provide clear, professional, and actionable financial insights."""

        with st.spinner("🤔 Analyzing..."):
            response = st.session_state.ai_agent.generate_response(user_input, system_prompt)

        # Add assistant response to history
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)

    # Clear chat button
    if st.button("🔄 Clear Chat History"):
        st.session_state.chat_history = []
        if st.session_state.ai_agent:
            st.session_state.ai_agent.clear_history()
        st.rerun()

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'dataset_df' not in st.session_state:
    st.session_state.dataset_df = None
if 'waccmap' not in st.session_state:
    st.session_state.waccmap = None
if 'portfolio_df' not in st.session_state:
    st.session_state.portfolio_df = None
if 'financial_statements' not in st.session_state:
    st.session_state.financial_statements = None
if 'contacts_df' not in st.session_state:
    st.session_state.contacts_df = None
if 'auto_load' not in st.session_state:
    st.session_state.auto_load = False
if 'ai_initialized' not in st.session_state:
    st.session_state.ai_initialized = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point"""
    st.set_page_config(page_title="Financial AI Agent", layout="wide")

    st.title("💼 Financial AI Agent Platform")
    st.markdown("Powered by llama.cpp + Dropbox Integration + Financial Analysis")

    st.markdown("---")

    # Sidebar controls
    st.sidebar.header("⚙️ Controls")

    # Auto-load button
    if st.sidebar.button("🔄 Load Data from Dropbox"):
        st.session_state.auto_load = True

    # Check if auto-load was triggered
    if st.session_state.auto_load:
        if DROPBOX_TOKEN:
            data_dict = load_all_data_from_dropbox()
            if data_dict:
                st.session_state.dataset_df = data_dict.get('dataset')
                st.session_state.waccmap = data_dict.get('wacc')
                st.session_state.portfolio_df = data_dict.get('portfolio')
                st.session_state.financial_statements = data_dict.get('financial_statements')
                st.session_state.contacts_df = data_dict.get('contacts')
                st.session_state.auto_load = False
        else:
            st.error("❌ Dropbox token not configured.")
            st.stop()

    # Sidebar Data Configuration (for manual override only)
    st.sidebar.header("📁 Manual Data Upload")

    dataset_file = st.sidebar.file_uploader(
        "Upload Dataset (XLSX) - Optional Override",
        type="xlsx",
        key="dataset_uploader"
    )

    wacc_file = st.sidebar.file_uploader(
        "Upload WACC Map (XLSX) - Optional Override",
        type="xlsx",
        key="wacc_uploader"
    )

    portfolio_file = st.sidebar.file_uploader(
        "Upload Portfolio (XLSX) - Optional Override",
        type="xlsx",
        key="portfolio_uploader"
    )

    # Manual upload handling (overrides Dropbox data if provided)
    if dataset_file and wacc_file:
        st.session_state.dataset_df = pd.read_excel(dataset_file, engine='openpyxl')
        st.session_state.waccmap = pd.read_excel(wacc_file, engine='openpyxl')
        if portfolio_file:
            st.session_state.portfolio_df = pd.read_excel(portfolio_file, engine='openpyxl')

    # Main content
    dataset_df = st.session_state.get('dataset_df')
    waccmap = st.session_state.get('waccmap')

    # Tab interface
    tab1, tab2, tab3 = st.tabs(["📊 AI Assistant", "🏢 Company Analysis", "📋 Help"])

    with tab1:
        show_ai_chat_interface()

    with tab2:
        st.subheader("🏢 Company Financial Analysis")
        if dataset_df is not None and waccmap is not None:
            if validate_columns(dataset_df, "Dataset"):
                st.sidebar.metric("Companies Loaded", len(dataset_df))
                st.sidebar.metric("Categories", dataset_df['category_code'].nunique())

                # Company selection
                company_name = st.selectbox("Select a company:", dataset_df['company'].unique())

                company_data = dataset_df[dataset_df['company'] == company_name].iloc[0]

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("EBIT", f"€{company_data['ebit']:,.2f}")
                with col2:
                    st.metric("Net Income", f"€{company_data['net income']:,.2f}")
                with col3:
                    st.metric("Employees", f"{company_data['employees']:,.0f}")

                # DCF Valuation
                dcf_result = DCF_automated(company_data, waccmap)

                val_col1, val_col2, val_col3 = st.columns(3)
                with val_col1:
                    st.metric("Current EV", f"€{dcf_result['EV_current']:,.2f}")
                with val_col2:
                    st.metric("DCF EV", f"€{dcf_result['EV_DCF']:,.2f}")
                with val_col3:
                    st.metric("EV Growth", f"{dcf_result['growth_expected']:.2%}")

                # AI Analysis
                st.markdown("---")
                st.subheader("🤖 AI Analysis")

                if st.button("Generate AI Analysis for this Company"):
                    if st.session_state.ai_initialized and st.session_state.ai_agent:
                        with st.spinner("Generating analysis..."):
                            analysis = st.session_state.ai_agent.analyze_company(company_data)
                            st.info(analysis)
                    else:
                        st.warning("AI model not initialized")
        else:
            st.info("👈 Upload or load data from Dropbox first")

    with tab3:
        st.subheader("📋 Help & Documentation")
        st.write("**Setup Instructions:**")
        st.markdown("""
        1. **Streamlit Secrets Configuration:**
           - Create `.streamlit/secrets.toml` with:
           ```
           DROPBOX_APP_KEY = "your_key"
           DROPBOX_APP_SECRET = "your_secret"
           DROPBOX_REFRESH_TOKEN = "your_refresh_token"
           LLAMA_MODEL_PATH = "path/to/model.gguf"
           LLAMA_N_GPU_LAYERS = 0
           LLAMA_N_CTX = 2048
           LLAMA_TEMPERATURE = 0.7
           ```

        2. **Install llama.cpp:**
           ```bash
           pip install llama-cpp-python
           ```

        3. **Download a GGUF model** from Hugging Face (e.g., Mistral, Llama 2)

        4. **Required Columns in Dataset:**
        """
        )
        for col in COLUMNS_REQUIRED:
            st.text(f"• {col}")

if __name__ == "__main__":
    main()
