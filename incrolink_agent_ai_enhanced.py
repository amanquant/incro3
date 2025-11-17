"""
Streamlit Application - Main Entry Point
=========================================
Financial Analysis Agent with LangGraph Memory Integration
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from financial_agent import display_agent_interface, init_agent_session
from dropbox_integration import load_all_data_from_dropbox

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Financial Analysis Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/amanquant/financial-agent",
        "Report a bug": "https://github.com/amanquant/financial-agent/issues",
        "About": "Financial Analysis Agent powered by LangGraph"
    }
)

# ============================================================================
# STYLING & BRANDING
# ============================================================================

st.markdown("""
<style>
    .stChatMessage {
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
    }

    .stChatMessage.user {
        background-color: #E3F2FD;
        border-left: 4px solid #1976D2;
    }

    .stChatMessage.assistant {
        background-color: #F3E5F5;
        border-left: 4px solid #7B1FA2;
    }

    .agent-info {
        background-color: #F0F2F6;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 16px;
        border-left: 4px solid #00BFA5;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    # Mode selection
    mode = st.radio(
        "Select Mode:",
        options=["Chat Agent", "Data Management", "Settings"],
        help="Choose between agent chat, data management, or settings"
    )

    st.markdown("---")

    # Data status
    st.markdown("### 📊 Data Status")

    if st.session_state.get('data_loaded', False):
        st.success("✅ Financial data loaded")

        if st.session_state.get('dataset_df') is not None:
            st.metric("Companies", len(st.session_state['dataset_df']))

        if st.session_state.get('waccmap') is not None:
            st.metric("Sectors", 
                     st.session_state['waccmap']['category_code'].nunique())
    else:
        st.info("📂 Click 'Load Data' to get started")

    st.markdown("---")

    # Load data button
    st.markdown("### 📥 Data Loading")

    if st.button("🔄 Load from Dropbox", use_container_width=True, key="sidebar_load"):
        with st.spinner("Loading financial data..."):
            try:
                data = load_all_data_from_dropbox()
                st.session_state.dataset_df = data.get('dataset')
                st.session_state.waccmap = data.get('wacc')
                st.session_state.portfolio_df = data.get('portfolio')
                st.session_state.financial_statements = data.get('financial_statements')
                st.session_state.contacts_df = data.get('contacts')
                st.session_state.data_loaded = True
                st.success("✅ Data loaded successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load data: {str(e)}")

    # Manual upload
    st.markdown("### 📤 Manual Upload")

    dataset_file = st.file_uploader("Dataset (XLSX)", type="xlsx", key="dataset_upload")
    if dataset_file:
        st.session_state.dataset_df = pd.read_excel(dataset_file, engine='openpyxl')
        st.success("✅ Dataset uploaded")

    wacc_file = st.file_uploader("WACC Map (XLSX)", type="xlsx", key="wacc_upload")
    if wacc_file:
        st.session_state.waccmap = pd.read_excel(wacc_file, engine='openpyxl')
        st.success("✅ WACC loaded")

    st.markdown("---")

    # Info
    st.markdown("### ℹ️ About")
    st.info("""
    **Financial Analysis Agent**

    powered by:
    - 🔗 LangGraph
    - 🧠 InMemoryStore
    - 📊 Financial Data
    """)

# ============================================================================
# MAIN CONTENT
# ============================================================================

def main():
    """Main application logic"""

    # Initialize session
    init_agent_session()

    if mode == "Chat Agent":
        st.markdown("# 🤖 Financial Analysis Agent")
        st.markdown("""
        *Your intelligent assistant for financial data analysis, company valuation, and investment insights.*
        """)

        # Agent info box
        st.markdown("""
        <div class="agent-info">
            <strong>🧠 Agent Capabilities:</strong><br>
            • Search and analyze companies<br>
            • Calculate financial metrics & ratios<br>
            • Run DCF valuation models<br>
            • Assess company predictability<br>
            • Find and manage contacts
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Check data loaded
        if not st.session_state.get('data_loaded', False):
            st.warning("""
            ⚠️ **Data not loaded!**

            Please load financial data first:
            1. Click **"Load from Dropbox"** in the sidebar, OR
            2. Upload files manually using the file uploaders

            Once loaded, the agent will be ready to assist.
            """)
        else:
            # Display agent interface
            display_agent_interface()

    elif mode == "Data Management":
        st.markdown("# 📊 Data Management")

        tab1, tab2, tab3 = st.tabs(["Dataset", "WACC Map", "Contacts"])

        with tab1:
            st.markdown("## Dataset")
            if st.session_state.get('dataset_df') is not None:
                df = st.session_state['dataset_df']
                st.success(f"✅ {len(df)} companies loaded")
                st.dataframe(df, use_container_width=True, height=400)

                # Download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name="dataset.csv",
                    mime="text/csv"
                )
            else:
                st.info("No dataset loaded yet")

        with tab2:
            st.markdown("## WACC Map")
            if st.session_state.get('waccmap') is not None:
                df = st.session_state['waccmap']
                st.success(f"✅ {len(df)} categories")
                st.dataframe(df, use_container_width=True, height=400)
            else:
                st.info("No WACC map loaded yet")

        with tab3:
            st.markdown("## Contacts")
            if st.session_state.get('contacts_df') is not None:
                df = st.session_state['contacts_df']
                st.success(f"✅ {len(df)} contacts")
                st.dataframe(df, use_container_width=True, height=400)
            else:
                st.info("No contacts loaded yet")

    elif mode == "Settings":
        st.markdown("# ⚙️ Settings")

        st.markdown("## Agent Configuration")

        col1, col2 = st.columns(2)

        with col1:
            max_history = st.slider(
                "Max Conversation History",
                min_value=3,
                max_value=50,
                value=10,
                help="Number of recent messages to consider in agent memory"
            )
            st.session_state.max_history = max_history

        with col2:
            enable_logging = st.checkbox(
                "Enable Logging",
                value=False,
                help="Log all agent interactions"
            )
            st.session_state.enable_logging = enable_logging

        st.markdown("---")

        st.markdown("## Session Information")

        if 'agent_state' in st.session_state:
            agent_state = st.session_state.agent_state

            info_col1, info_col2, info_col3 = st.columns(3)

            with info_col1:
                st.metric("Session ID", agent_state.session_id[:8] + "...")

            with info_col2:
                st.metric("Total Turns", len(agent_state.conversation_history))

            with info_col3:
                st.metric("Stored Companies", len(agent_state.company_contexts))

        st.markdown("---")

        st.markdown("## Danger Zone")

        if st.button("🗑️ Clear All Data", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("✅ All data cleared")
            st.rerun()

if __name__ == "__main__":
    main()
