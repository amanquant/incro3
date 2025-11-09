"""
Incrolink Agent - Finance Intelligence Platform with AI Assistant
Enhanced version with chat interface and multiple free LLM API support
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
from typing import Optional, Dict, List
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

COLUMNS_REQUIRED = [
    "company", "nace", "ebit", "employees", "net income", "capex", "d&a",
    "changes in wc", "lt debt", "st debt", "sh equity", "capital equity", 
    "cash", "category_code"
]

# LLM API Configuration
LLM_PROVIDERS = {
    "Groq (Free)": {
        "env_var": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.3-70b-versatile", "llama3-8b-8192", "mixtral-8x7b-32768", "deepseek-r1-distill-llama-70b"],
        "default_model": "llama-3.3-70b-versatile"
    },
    "OpenRouter (Free)": {
        "env_var": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "models": ["meta-llama/llama-3.1-8b-instruct:free", "google/gemma-2-9b-it:free"],
        "default_model": "meta-llama/llama-3.1-8b-instruct:free"
    },
    "GitHub Models (Free)": {
        "env_var": "GITHUB_TOKEN",
        "base_url": "https://models.github.ai/inference",
        "models": ["gpt-4o-mini", "meta-llama-3.1-8b-instruct", "meta-llama-3-70b-instruct"],
        "default_model": "meta-llama-3.1-8b-instruct"
    },
    "Ollama (Local)": {
        "env_var": None,
        "base_url": "http://localhost:11434/v1",
        "models": ["llama3.2", "llama3.1", "mistral", "deepseek-r1"],
        "default_model": "llama3.2"
    }
}

# ============================================================================
# CORE DCF FUNCTIONS (Preserved from original)
# ============================================================================

def validate_columns(df, file_type="Dataset") -> bool:
    """Validate that the dataframe has all required columns"""
    missing_cols = [col for col in COLUMNS_REQUIRED if col not in df.columns]
    if missing_cols:
        st.error(f"❌ {file_type} - Missing required columns: {', '.join(missing_cols)}")
        return False
    st.success(f"✅ {file_type} - All required columns present")
    return True


def DCF_automated(company_row, waccmap, years=5) -> Dict:
    """Calculate DCF valuation for a company"""
    # Current Enterprise Value calculation
    sh_equity = company_row['sh equity']
    capital_equity = company_row['capital equity']
    lt_debt = company_row['lt debt']
    st_debt = company_row['st debt']
    cash = company_row['cash']
    EV_current = sh_equity + lt_debt + st_debt - cash

    # Retrieve WACC and growth parameters based on category code
    category_code = str(company_row['category_code'])
    params_match = waccmap[waccmap['category_code'].astype(str) == category_code]

    if not params_match.empty:
        re = params_match.iloc[0]['re']
        rd = params_match.iloc[0]['rd']
        wacc = params_match.iloc[0]['wacc']
        g = params_match.iloc[0]['g']
    else:
        re = rd = wacc = g = np.nan

    # Free Cash Flow calculation
    net_income = company_row['net income']
    d_and_a = company_row['d&a']
    capex = company_row['capex']
    changes_in_wc = company_row['changes in wc']
    FCF0 = net_income + d_and_a - capex - changes_in_wc

    # Project FCFs and calculate Terminal Value
    FCFs = [FCF0 * ((1 + g) ** n) for n in range(1, years + 1)]
    TV = FCFs[-1] / (wacc - g) if (wacc - g) != 0 else 0

    # Discount all cash flows and terminal value
    discount_factors = [(1 + wacc) ** n for n in range(1, years + 1)]
    discounted_FCFs = [f / d for f, d in zip(FCFs, discount_factors)]
    discounted_TV = TV / discount_factors[-1]

    # Calculate DCF Enterprise Value
    EV_DCF = sum(discounted_FCFs) + discounted_TV
    growth_expected = (EV_DCF / EV_current) - 1 if EV_current else np.nan

    return {
        'EV_current': EV_current,
        'EV_DCF': EV_DCF,
        'growth_expected': growth_expected,
        'category_code': category_code,
        'params': dict(re=re, rd=rd, wacc=wacc, g=g),
        'company_name': company_row['company']
    }


# ============================================================================
# AI ASSISTANT FUNCTIONS
# ============================================================================

def get_llm_client(provider: str, api_key: Optional[str] = None):
    """Initialize LLM client based on provider"""
    try:
        if provider == "Ollama (Local)":
            # For Ollama, we use requests or a simple HTTP client
            return {"type": "ollama", "base_url": LLM_PROVIDERS[provider]["base_url"]}
        else:
            # For API-based providers, we use OpenAI-compatible interface
            from openai import OpenAI
            config = LLM_PROVIDERS[provider]

            if api_key is None:
                api_key = os.getenv(config["env_var"])

            if not api_key:
                return None

            client = OpenAI(
                api_key=api_key,
                base_url=config["base_url"]
            )
            return client
    except Exception as e:
        st.error(f"Error initializing LLM client: {str(e)}")
        return None


def get_ai_response(messages: List[Dict], provider: str, model: str, api_key: Optional[str] = None) -> str:
    """Get response from AI assistant"""
    client = get_llm_client(provider, api_key)

    if client is None:
        return "❌ Please configure API key in the sidebar to use AI assistant."

    try:
        if isinstance(client, dict) and client["type"] == "ollama":
            # Handle Ollama locally
            import requests
            response = requests.post(
                f"{client['base_url']}/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                }
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"❌ Ollama error: Make sure Ollama is running locally (ollama serve)"
        else:
            # Handle API-based providers
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error getting AI response: {str(e)}"


def create_system_prompt() -> str:
    """Create system prompt for AI assistant"""
    return """You are an intelligent finance assistant for Incrolink Agent, a DCF valuation platform. 

Your capabilities:
1. Help users upload and analyze company financial data
2. Perform DCF (Discounted Cash Flow) analysis
3. Search for companies in the dataset
4. Explain financial metrics and valuation results
5. Provide insights on enterprise value, WACC, and growth rates

When users ask to:
- "upload data" or "add files" → Guide them to use the file upload in sidebar
- "search for [company]" → I'll search the dataset
- "analyze [company]" or "run DCF" → I'll perform DCF analysis
- "explain results" → Provide clear financial interpretation

Be concise, professional, and finance-focused. Always format numbers clearly."""


def process_user_query(query: str, df: Optional[pd.DataFrame], waccmap: Optional[pd.DataFrame]) -> str:
    """Process user query and generate appropriate response"""
    query_lower = query.lower()

    # Check if data is loaded
    if df is None or waccmap is None:
        if "upload" in query_lower or "file" in query_lower or "data" in query_lower:
            return "📁 **To upload your data:**\n\n1. Look at the sidebar on the left\n2. Click on \'Upload Dataset (XLSX)\'\n3. Upload your company dataset\n4. Then upload the WACC Map file\n\nOnce both files are uploaded, I can help you analyze companies!"
        else:
            return "⚠️ Please upload your dataset and WACC map files using the sidebar first. Then I can help you search and analyze companies!"

    # Search for company
    if "search" in query_lower or "find" in query_lower or "look for" in query_lower:
        # Extract company name (simplified - in production, use better NLP)
        words = query_lower.split()
        search_terms = [w for w in words if w not in ["search", "for", "find", "company", "look", "the", "a", "an"]]
        if search_terms:
            search_query = " ".join(search_terms)
            filtered_df = df[df['company'].str.contains(search_query, case=False, na=False)]

            if filtered_df.empty:
                return f"❌ No companies found matching \'{search_query}\'. Try different keywords."
            elif len(filtered_df) > 5:
                companies_list = filtered_df['company'].head(5).tolist()
                return f"✅ Found {len(filtered_df)} companies matching \'{search_query}\':\n\n" + "\n".join([f"• {c}" for c in companies_list]) + f"\n\n... and {len(filtered_df)-5} more. Please be more specific!"
            else:
                companies_list = filtered_df['company'].tolist()
                return f"✅ Found {len(filtered_df)} company(ies):\n\n" + "\n".join([f"• {c}" for c in companies_list]) + "\n\nWould you like me to analyze any of these?"

    # Analyze company
    if ("analyze" in query_lower or "dcf" in query_lower or "valuation" in query_lower) and df is not None:
        # Try to find company name in query
        for idx, row in df.iterrows():
            if row['company'].lower() in query_lower:
                # Perform DCF analysis
                result = DCF_automated(row, waccmap)

                response = f"## 📊 DCF Analysis: {result['company_name']}\n\n"
                response += f"**Current Enterprise Value:** ${result['EV_current']:,.2f}\n\n"
                response += f"**DCF Enterprise Value:** ${result['EV_DCF']:,.2f}\n\n"
                response += f"**Expected Growth:** {result['growth_expected']:.2%}\n\n"
                response += f"**Valuation Parameters:**\n"
                response += f"- Cost of Equity (re): {result['params']['re']:.2%}\n"
                response += f"- Cost of Debt (rd): {result['params']['rd']:.2%}\n"
                response += f"- WACC: {result['params']['wacc']:.2%}\n"
                response += f"- Growth Rate (g): {result['params']['g']:.2%}\n"

                # Store analysis in session state for reference
                st.session_state.last_dcf_result = result

                return response

    # Default: Use AI to respond
    return None  # Will trigger AI response


# ============================================================================
# STREAMLIT UI
# ============================================================================

def main():
    # Page configuration
    st.set_page_config(
        page_title="Incrolink Agent - AI Finance Assistant",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Header
    st.title("🤖 Incrolink Agent")
    try:
        st.logo("logoincrolink1.jpeg")
    except:
        pass  # Logo file might not exist
    st.markdown("**AI-Powered DCF Valuation Platform**")
    st.markdown("---")

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "dataset" not in st.session_state:
        st.session_state.dataset = None

    if "waccmap" not in st.session_state:
        st.session_state.waccmap = None

    if "last_dcf_result" not in st.session_state:
        st.session_state.last_dcf_result = None

    # ========================================================================
    # SIDEBAR - Configuration & File Upload
    # ========================================================================

    with st.sidebar:
        st.header("⚙️ Configuration")

        # LLM Provider Selection
        st.subheader("🤖 AI Assistant Setup")
        selected_provider = st.selectbox(
            "Select LLM Provider",
            list(LLM_PROVIDERS.keys()),
            help="Choose your preferred AI provider. Groq and Ollama are recommended for free usage."
        )

        provider_config = LLM_PROVIDERS[selected_provider]

        # API Key input (if needed)
        api_key = None
        if provider_config["env_var"]:
            api_key = st.text_input(
                f"API Key ({provider_config['env_var']})",
                type="password",
                help=f"Enter your API key or set {provider_config['env_var']} environment variable"
            )
            if not api_key:
                api_key = os.getenv(provider_config["env_var"])
                if api_key:
                    st.success("✅ API key loaded from environment")
                else:
                    st.warning("⚠️ API key not found")
        else:
            st.info("ℹ️ Ollama runs locally - no API key needed. Make sure Ollama is running!")

        # Model selection
        selected_model = st.selectbox(
            "Select Model",
            provider_config["models"],
            index=provider_config["models"].index(provider_config["default_model"])
        )

        st.markdown("---")

        # File Upload Section
        st.subheader("📁 Data Upload")

        dataset_file = st.file_uploader(
            "Upload Dataset (XLSX)",
            type="xlsx",
            key="dataset_uploader",
            help="Upload the company dataset with all required columns"
        )

        wacc_file = st.file_uploader(
            "Upload WACC Map (XLSX)",
            type="xlsx",
            key="wacc_uploader",
            help="Upload the WACC parameters mapped by category code"
        )

        # Process uploaded files
        if dataset_file and wacc_file:
            try:
                df = pd.read_excel(dataset_file)
                waccmap = pd.read_excel(wacc_file)

                if validate_columns(df, "Dataset"):
                    st.session_state.dataset = df
                    st.session_state.waccmap = waccmap

                    st.metric("Companies Loaded", len(df))
                    st.metric("Categories", df['category_code'].nunique())

                    # Add welcome message to chat
                    if len(st.session_state.messages) == 0:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"✅ **Data loaded successfully!**\n\n📊 {len(df)} companies across {df['category_code'].nunique()} categories.\n\nYou can now:\n• Search for companies\n• Run DCF analysis\n• Ask questions about valuations\n\nHow can I help you today?"
                        })
            except Exception as e:
                st.error(f"Error loading files: {str(e)}")
        elif len(st.session_state.messages) == 0:
            # Initial welcome message
            st.session_state.messages.append({
                "role": "assistant", 
                "content": "👋 **Welcome to Incrolink Agent!**\n\nI'm your AI finance assistant. To get started:\n\n1. Upload your Dataset (XLSX)\n2. Upload your WACC Map (XLSX)\n3. Ask me to search or analyze companies!\n\nWhat would you like to do?"
            })

        st.markdown("---")

        # Required columns reference
        with st.expander("📋 Required Columns"):
            st.write("Dataset must include:")
            for col in COLUMNS_REQUIRED:
                st.text(f"• {col}")

        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

    # ========================================================================
    # MAIN CHAT INTERFACE
    # ========================================================================

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask me anything about company valuations..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process query and generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # First, try to process with built-in logic
                built_in_response = process_user_query(
                    prompt, 
                    st.session_state.dataset, 
                    st.session_state.waccmap
                )

                if built_in_response:
                    # Use built-in response
                    response = built_in_response
                else:
                    # Use AI for general questions
                    messages_for_ai = [
                        {"role": "system", "content": create_system_prompt()}
                    ] + [
                        {"role": m["role"], "content": m["content"]} 
                        for m in st.session_state.messages[-5:]  # Last 5 messages for context
                    ]

                    response = get_ai_response(
                        messages_for_ai,
                        selected_provider,
                        selected_model,
                        api_key
                    )

                st.markdown(response)

        # Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": response})

    # ========================================================================
    # FOOTER
    # ========================================================================

    st.markdown("---")
    st.caption("💡 **Tip:** Ask me to search for companies, run DCF analysis, or explain financial metrics!")


if __name__ == "__main__":
    main()
