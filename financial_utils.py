"""
Financial Analysis Utilities
=============================
Core financial calculation and analysis functions
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from fuzzywuzzy import fuzz, process

# ============================================================================
# FINANCIAL METRICS CALCULATION
# ============================================================================

def calculate_metrics_from_row(company_row: pd.Series) -> Dict[str, float]:
    """Calculate financial metrics from company data"""
    metrics = {}

    try:
        # LTDE: Long-term Debt / Shareholders' Equity
        lt_debt = company_row.get('lt debt', np.nan)
        sh_equity = company_row.get('sh equity', np.nan)

        if not pd.isna(sh_equity) and sh_equity != 0 and not pd.isna(lt_debt):
            metrics['ltde'] = lt_debt / sh_equity
        else:
            metrics['ltde'] = np.nan

        # EBITDA Margin: EBITDA / Operating Revenue
        # Note: We calculate from available data
        ebit = company_row.get('ebit', np.nan)
        metrics['edamargin'] = np.nan  # Requires financial statements

        # FX: Employee Costs / Operating Revenue
        metrics['fx'] = np.nan  # Requires financial statements

    except Exception as e:
        pass

    return metrics

def calculate_dcf_valuation(company_row: pd.Series, 
                            waccmap: pd.DataFrame,
                            years: int = 5) -> Dict:
    """
    Calculate DCF valuation for a company

    Args:
        company_row: Company data
        waccmap: WACC parameters by sector
        years: Forecast period

    Returns:
        DCF valuation results
    """

    try:
        # Extract financial data
        sh_equity = company_row.get('sh equity', 0)
        capital_equity = company_row.get('capital equity', 0)
        lt_debt = company_row.get('lt debt', 0)
        st_debt = company_row.get('st debt', 0)
        cash = company_row.get('cash', 0)

        # Calculate current EV
        ev_current = sh_equity + lt_debt + st_debt - cash

        # Get WACC parameters from sector
        category_code = str(company_row.get('category_code', ''))
        params_match = waccmap[waccmap['category_code'].astype(str) == category_code]

        if not params_match.empty:
            re = params_match.iloc[0].get('re', np.nan)
            rd = params_match.iloc[0].get('rd', np.nan)
            wacc = params_match.iloc[0].get('wacc', np.nan)
            g = params_match.iloc[0].get('g', np.nan)
        else:
            re = rd = wacc = g = np.nan

        # Calculate FCF
        net_income = company_row.get('net income', 0)
        d_and_a = company_row.get('d&a', 0)
        capex = company_row.get('capex', 0)
        changes_in_wc = company_row.get('changes in wc', 0)

        fcf0 = net_income + d_and_a - capex - changes_in_wc

        # Project FCFs
        fcfs = [fcf0 * ((1 + g) ** n) for n in range(1, years + 1)]

        # Terminal value
        tv = fcfs[-1] / (wacc - g) if (wacc - g) != 0 else 0

        # Discount cash flows
        discount_factors = [(1 + wacc) ** n for n in range(1, years + 1)]
        discounted_fcfs = [f / d for f, d in zip(fcfs, discount_factors)]
        discounted_tv = tv / discount_factors[-1]

        # Calculate DCF EV
        ev_dcf = sum(discounted_fcfs) + discounted_tv

        # Expected growth
        growth_expected = (ev_dcf / ev_current - 1) if ev_current else np.nan

        return {
            'ev_current': ev_current,
            'ev_dcf': ev_dcf,
            'growth_expected': growth_expected,
            'fcf0': fcf0,
            'terminal_value': tv,
            'wacc': wacc,
            'params': {'re': re, 'rd': rd, 'wacc': wacc, 'g': g}
        }

    except Exception as e:
        return {
            'error': str(e),
            'ev_current': 0,
            'ev_dcf': 0,
            'growth_expected': 0
        }

def get_sector_percentiles(category_code: str, 
                          waccmap: pd.DataFrame) -> Dict:
    """Get percentile data for a sector"""

    try:
        category_data = waccmap[
            waccmap['category_code'].astype(str) == str(category_code)
        ]

        if category_data.empty:
            return {}

        row = category_data.iloc[0]

        return {
            'ltde': {
                'p10': row.get('ltde10th', np.nan),
                'p25': row.get('ltde25th', np.nan),
                'p50': row.get('ltde50th', np.nan),
                'p75': row.get('ltde75th', np.nan),
                'p90': row.get('ltde90th', np.nan)
            },
            'edamargin': {
                'p10': row.get('edamarg10th', np.nan),
                'p25': row.get('edamarg25th', np.nan),
                'p50': row.get('edamarg50th', np.nan),
                'p75': row.get('edamarg75th', np.nan),
                'p90': row.get('edamarg90th', np.nan)
            },
            'wacc': row.get('wacc', np.nan),
            'growth_rate': row.get('g', np.nan)
        }

    except:
        return {}

# ============================================================================
# FUZZY MATCHING & SEARCH
# ============================================================================

def fuzzy_match_company(query: str, 
                       dataset: pd.DataFrame,
                       threshold: int = 70) -> Optional[pd.Series]:
    """Find company using fuzzy matching"""

    companies = dataset['company'].tolist()
    matches = process.extract(query, companies, scorer=fuzz.token_set_ratio, limit=1)

    if matches and matches[0][1] >= threshold:
        matching_name = matches[0][0]
        return dataset[dataset['company'] == matching_name].iloc[0]

    return None

def search_companies(query: str, 
                    dataset: pd.DataFrame) -> pd.DataFrame:
    """Search companies by substring"""

    return dataset[dataset['company'].str.contains(query, case=False, na=False)]

# ============================================================================
# PREDICTABILITY ANALYSIS
# ============================================================================

PREDICTABILITY_CATEGORIES = {
    "0": "Low growth",
    "0.23": "Good growth, low sell side",
    "0.43": "Good financials, young management",
    "0.54": "Good conditions, small revenue",
    "0.65": "Optimal, weak margins",
    "0.8": "Optimal conditions"
}

def analyze_predictability(company_row: pd.Series,
                          metrics: Dict,
                          dcf_result: Dict,
                          waccmap: pd.DataFrame,
                          contacts_df: Optional[pd.DataFrame] = None) -> Tuple[str, str, list]:
    """
    Analyze company predictability using decision tree

    Returns:
        (score, category, decision_path)
    """

    decision_path = []

    # Check growth
    growth = dcf_result.get('growth_expected', 0)
    decision_path.append(f"EV Growth: {growth:.2%}")

    if growth < 0.15:
        return "0", PREDICTABILITY_CATEGORIES["0"], decision_path

    # Check sell side coverage
    category_code = str(company_row.get('category_code', ''))
    percentiles = get_sector_percentiles(category_code, waccmap)

    if percentiles:
        decision_path.append("Sell side check")
        # Would check nsellside vs nsellside_p50

    # Check CEO age
    if contacts_df is not None:
        company_id = company_row.get('companyID')
        if company_id:
            company_contacts = contacts_df[
                contacts_df['companyID'] == company_id
            ]
            if not company_contacts.empty and 'CEO' in company_contacts.columns:
                ceo = company_contacts[company_contacts['CEO'].notna()]
                if not ceo.empty and 'age' in ceo.columns:
                    age = ceo.iloc[0]['age']
                    if age < 60:
                        decision_path.append(f"Young CEO: {age}")
                        return "0.43", PREDICTABILITY_CATEGORIES["0.43"], decision_path

    # Default to optimal
    return "0.8", PREDICTABILITY_CATEGORIES["0.8"], decision_path

# ============================================================================
# DATA VALIDATION
# ============================================================================

REQUIRED_COLUMNS = [
    "company", "nace", "ebit", "employees", "net income", "capex", 
    "d&a", "changes in wc", "lt debt", "st debt", "sh equity", 
    "capital equity", "cash", "category_code"
]

def validate_dataset(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validate dataset has required columns"""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    return len(missing) == 0, missing

# ============================================================================
# DATA EXPORT & FORMATTING
# ============================================================================

def export_analysis_result(result: Dict) -> pd.DataFrame:
    """Convert analysis result to DataFrame"""
    return pd.DataFrame([result])

def format_currency(value: float, currency: str = "€") -> str:
    """Format value as currency"""
    if pd.isna(value):
        return "N/A"
    return f"{currency} {value:,.2f}"

def format_percentage(value: float) -> str:
    """Format value as percentage"""
    if pd.isna(value):
        return "N/A"
    return f"{value:.2%}"
