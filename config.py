"""
Configuration and Constants
===========================
Centralized configuration for the agent system
"""

# Financial Analysis Configuration
REQUIRED_COLUMNS = [
    "company", "nace", "ebit", "employees", "net income", "capex",
    "d&a", "changes in wc", "lt debt", "st debt", "sh equity",
    "capital equity", "cash", "category_code"
]

FINANCIAL_ITEMS = {
    'long_term_debt': 'Long term debt',
    'shareholders_funds': 'Shareholders funds',
    'operating_revenue': 'Operating revenue (Turnover)',
    'cost_of_employees': 'Costs of employees',
    'ebitda': 'EBITDA'
}

PREDICTABILITY_CATEGORIES = {
    "0": "Low growth",
    "0.23": "Good growth, low sell side",
    "0.43": "Good financials, young management",
    "0.54": "Good conditions, small revenue",
    "0.65": "Optimal, weak margins",
    "0.8": "Optimal conditions"
}

# Agent Configuration
AGENT_CONFIG = {
    'max_conversation_history': 10,
    'fuzzy_match_threshold': 70,
    'dcf_forecast_period': 5,
    'sector_percentiles': ['p10', 'p25', 'p50', 'p75', 'p90'],
    'enable_memory_persistence': True,
    'memory_export_format': 'json'
}

# UI Configuration
UI_CONFIG = {
    'page_title': 'Financial Analysis Agent',
    'layout': 'wide',
    'initial_sidebar_state': 'expanded',
    'max_messages_display': 100
}

# Dropbox Configuration
DROPBOX_CONFIG = {
    'api_version': 2,
    'retry_attempts': 3,
    'timeout': 30,
    'chunk_size': 1024 * 1024
}

# Data Paths in Dropbox
DROPBOX_PATHS = {
    'financial_statements': '/volkfs.xlsx',
    'dataset': '/datasetincro1.xlsx',
    'portfolio': '/db.xlsx',
    'wacc': '/wacc.xlsx',
    'contacts': '/contacts.xlsx'
}

# Financial Metrics
METRICS = {
    'ltde': {
        'name': 'Long-term Debt to Equity',
        'formula': 'LT Debt / Shareholders Equity',
        'interpretation': 'Financial leverage'
    },
    'edamargin': {
        'name': 'EBITDA Margin',
        'formula': 'EBITDA / Operating Revenue',
        'interpretation': 'Operational efficiency'
    },
    'fx': {
        'name': 'Labor Cost Intensity',
        'formula': 'Employee Costs / Revenue',
        'interpretation': 'Cost structure'
    }
}

# Intent Mapping
INTENTS = {
    'company_search': ['company', 'search', 'find', 'lookup'],
    'metric_analysis': ['metric', 'ratio', 'compare', 'benchmark'],
    'valuation': ['dcf', 'valuation', 'value', 'price'],
    'predictability': ['grow', 'growth', 'predict', 'predictable'],
    'contacts': ['contact', 'manager', 'ceo', 'people'],
    'general': ['help', 'what', 'how', 'tell me']
}

# Message Templates
MESSAGE_TEMPLATES = {
    'welcome': """
        I'm your Financial Analysis Agent. I can help you with:

        📊 **Company Search** - Find and analyze companies
        📈 **Metrics Analysis** - Compare financial ratios
        💰 **Valuation** - Calculate DCF values
        🎯 **Predictability** - Assess company predictability
        📇 **Contacts** - Find key contacts

        What would you like to explore?
    """,

    'company_found': """
        I found **{company_name}**! Here's what I know:
        - **Category:** {category_code}
        - **NACE:** {nace}
        - **Employees:** {employees}
        - **EBIT:** €{ebit:,.2f}
        - **Net Income:** €{net_income:,.2f}

        Would you like me to run a valuation analysis or compare metrics?
    """,

    'metrics_ready': """
        I'm ready to analyze metrics for **{company_name}**.
        I can compare:
        - LTDE (Long-term Debt / Shareholders' Funds)
        - EDAMARGIN (EBITDA / Revenue)
        - FX (Employee Costs / Revenue)

        Which metric interests you most?
    """,

    'valuation_ready': """
        I'll calculate a DCF valuation for **{company_name}**.
        I need to know:
        1. Forecast period (default: 5 years)
        2. Should I use sector WACC or company-specific parameters?
        3. Any specific growth assumptions?

        What would you prefer?
    """,

    'error': """
        Sorry, I encountered an issue: {error_msg}

        Please try again or rephrase your question.
    """
}

# Validation Rules
VALIDATION_RULES = {
    'company_name': {
        'min_length': 2,
        'max_length': 100,
        'pattern': '[a-zA-Z0-9\s\-&]+'
    },
    'category_code': {
        'type': 'string',
        'pattern': '[0-9]+\.[0-9]+'
    }
}

# Export Formats
EXPORT_FORMATS = {
    'json': {'extension': '.json', 'mime': 'application/json'},
    'csv': {'extension': '.csv', 'mime': 'text/csv'},
    'xlsx': {'extension': '.xlsx', 'mime': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
}
