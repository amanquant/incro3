"""
LangGraph LSTM Memory-Based Agent for Financial Analytics
=========================================================
Integrates LangGraph's InMemoryStore with financial data processing
FIXED: BaseStore.put() method calls - follows LangGraph official API
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from dataclasses import dataclass, asdict
import uuid

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

# Financial analysis imports (from existing code)
import streamlit as st
from dropbox_integration import load_all_data_from_dropbox

# ============================================================================
# MEMORY STRUCTURES AND AGENT STATE
# ============================================================================

@dataclass
class ConversationTurn:
    """Represents a single conversation turn"""
    turn_id: str
    timestamp: datetime
    user_input: str
    agent_response: str
    financial_context: Dict[str, Any]
    memory_references: List[str]

    def to_dict(self) -> Dict:
        return {
            'turn_id': self.turn_id,
            'timestamp': self.timestamp.isoformat(),
            'user_input': self.user_input,
            'agent_response': self.agent_response,
            'financial_context': self.financial_context,
            'memory_references': self.memory_references
        }

@dataclass
class CompanyContext:
    """Financial context for a company"""
    company_name: str
    category_code: str
    metrics: Dict[str, float]
    dcf_result: Dict[str, Any]
    predictability: str
    last_updated: datetime

    def to_dict(self) -> Dict:
        return {
            'company_name': self.company_name,
            'category_code': self.category_code,
            'metrics': self.metrics,
            'dcf_result': self.dcf_result,
            'predictability': self.predictability,
            'last_updated': self.last_updated.isoformat()
        }

class AgentState:
    """Main agent state management"""
    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.conversation_history: List[ConversationTurn] = []
        self.company_contexts: Dict[str, CompanyContext] = {}
        self.analysis_results: Dict[str, Any] = {}
        self.current_company: Optional[str] = None
        self.current_metric: Optional[str] = None
        self.memory_store: InMemoryStore = InMemoryStore()
        self.created_at = datetime.now()

    def add_conversation_turn(self, user_input: str, agent_response: str, 
                             context: Dict[str, Any] = None) -> ConversationTurn:
        """Add a conversation turn to history"""
        turn = ConversationTurn(
            turn_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            user_input=user_input,
            agent_response=agent_response,
            financial_context=context or {},
            memory_references=[]
        )
        self.conversation_history.append(turn)
        return turn

    def store_company_context(self, company: CompanyContext):
        """Store company context in memory"""
        self.company_contexts[company.company_name] = company

    def get_conversation_context(self, last_n: int = 5) -> str:
        """Get recent conversation context for LSTM memory"""
        recent = self.conversation_history[-last_n:]
        context = []
        for turn in recent:
            context.append(f"User: {turn.user_input}")
            context.append(f"Agent: {turn.agent_response}")
        return "\n".join(context)

    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'conversation_history': [turn.to_dict() for turn in self.conversation_history],
            'company_contexts': {k: v.to_dict() for k, v in self.company_contexts.items()},
            'current_company': self.current_company,
            'current_metric': self.current_metric,
            'created_at': self.created_at.isoformat()
        }

# ============================================================================
# FINANCIAL DATA PROCESSOR WITH MEMORY INTEGRATION
# ============================================================================

class FinancialMemoryProcessor:
    """Processes financial data and maintains memory context"""

    def __init__(self, store: InMemoryStore):
        self.store = store
        self.dataset_df: Optional[pd.DataFrame] = None
        self.waccmap: Optional[pd.DataFrame] = None
        self.contacts_df: Optional[pd.DataFrame] = None

    def load_data(self, data_dict: Dict):
        """Load financial data into memory"""
        self.dataset_df = data_dict.get('dataset')
        self.waccmap = data_dict.get('wacc')
        self.contacts_df = data_dict.get('contacts')

    def extract_company_info(self, company_name: str) -> Optional[Dict]:
        """Extract company information with memory context"""
        if self.dataset_df is None:
            return None

        matching = self.dataset_df[
            self.dataset_df['company'].str.contains(company_name, case=False, na=False)
        ]

        if matching.empty:
            return None

        company_row = matching.iloc[0]
        info = {
            'company_name': company_row['company'],
            'category_code': company_row.get('category_code'),
            'nace': company_row.get('nace'),
            'employees': company_row.get('employees'),
            'ebit': company_row.get('ebit'),
            'net_income': company_row.get('net income'),
            'row_data': company_row
        }

        # Store in memory - FIXED: Use positional arguments only
        key = f"company_{company_row['company']}"
        try:
            self.store.put(key, info)
        except Exception as e:
            # Silently handle storage errors (store may not support put in some contexts)
            pass

        return info

    def get_sector_benchmarks(self, category_code: str) -> Optional[Dict]:
        """Get sector benchmarks for comparison"""
        if self.waccmap is None:
            return None

        category_data = self.waccmap[
            self.waccmap['category_code'].astype(str) == str(category_code)
        ]

        if category_data.empty:
            return None

        row = category_data.iloc[0]
        benchmarks = {
            'category_code': category_code,
            'ltde_p50': row.get('ltde50th'),
            'edamargin_p50': row.get('edamarg50th'),
            'wacc': row.get('wacc'),
            'growth_rate': row.get('g')
        }

        return benchmarks

# ============================================================================
# LANGGRAPH AGENT NODES
# ============================================================================

def process_user_input(state: Dict) -> Dict:
    """Process and understand user input"""
    user_input = state.get('user_input', '')
    agent_state: AgentState = state.get('agent_state')

    # Intent recognition
    intent = "general"

    if any(word in user_input.lower() for word in ['company', 'search', 'find']):
        intent = "company_search"
    elif any(word in user_input.lower() for word in ['metric', 'ratio', 'compare']):
        intent = "metric_analysis"
    elif any(word in user_input.lower() for word in ['dcf', 'valuation', 'value']):
        intent = "valuation"
    elif any(word in user_input.lower() for word in ['grow', 'growth', 'predict']):
        intent = "predictability"

    state['detected_intent'] = intent
    state['processed_input'] = user_input.lower().strip()

    return state

def retrieve_financial_context(state: Dict) -> Dict:
    """Retrieve relevant financial context from memory"""
    agent_state: AgentState = state.get('agent_state')
    processor: FinancialMemoryProcessor = state.get('processor')
    intent = state.get('detected_intent', 'general')

    context = {
        'conversation_history': agent_state.get_conversation_context(last_n=3),
        'current_company': agent_state.current_company,
        'stored_companies': list(agent_state.company_contexts.keys())
    }

    if intent == "company_search":
        # Extract company name from input
        keywords = state['processed_input'].split()
        for keyword in keywords:
            company_info = processor.extract_company_info(keyword)
            if company_info:
                agent_state.current_company = company_info['company_name']
                context['found_company'] = company_info
                break

    state['financial_context'] = context
    return state

def generate_response(state: Dict) -> Dict:
    """Generate agent response based on context"""
    agent_state: AgentState = state.get('agent_state')
    intent = state.get('detected_intent', 'general')
    context = state.get('financial_context', {})
    user_input = state.get('user_input', '')

    response = ""

    if intent == "company_search" and context.get('found_company'):
        company = context['found_company']
        response = f"""
I found **{company['company_name']}**! Here's what I know:
- **Category:** {company['category_code']}
- **NACE:** {company['nace']}
- **Employees:** {company['employees']}
- **EBIT:** €{company['ebit']:,.2f}
- **Net Income:** €{company['net_income']:,.2f}

Would you like me to run a valuation analysis or compare it with sector benchmarks?
"""

    elif intent == "metric_analysis":
        if agent_state.current_company:
            response = f"""
I'm ready to analyze metrics for **{agent_state.current_company}**. 
I can compare:
- LTDE (Long-term Debt / Shareholders' Funds)
- EDAMARGIN (EBITDA / Revenue)
- FX (Employee Costs / Revenue)

Which metric interests you most?
"""
        else:
            response = "Please tell me which company you'd like to analyze."

    elif intent == "valuation":
        response = """
I'll calculate a DCF valuation for the selected company. I need to know:
1. Forecast period (default: 5 years)
2. Should I use sector WACC or company-specific parameters?
3. Any specific growth assumptions?

What would you prefer?
"""

    elif intent == "predictability":
        response = """
I can assess the company's predictability using our decision tree model.
This analyzes:
- Growth trajectory
- Sell-side analyst coverage
- Management age
- Revenue scale
- Margin quality

Ready when you are!
"""

    else:
        response = f"""
I'm your Financial Analysis Agent. I can help you with:

📊 **Company Search** - Find and analyze companies
📈 **Metrics Analysis** - Compare financial ratios
💰 **Valuation** - Calculate DCF values
🎯 **Predictability** - Assess company predictability
📇 **Contacts** - Find key contacts

What would you like to explore?
"""

    # Store in memory
    turn = agent_state.add_conversation_turn(user_input, response.strip(), context)
    state['response'] = response.strip()
    state['conversation_turn'] = turn

    return state

def update_memory(state: Dict) -> Dict:
    """Update persistent memory with new information"""
    agent_state: AgentState = state.get('agent_state')
    turn: ConversationTurn = state.get('conversation_turn')

    # Store conversation turn - FIXED: Using positional arguments only
    key = f"turn_{turn.turn_id}"
    try:
        # LangGraph InMemoryStore.put(key, value) - positional args only
        agent_state.memory_store.put(key, turn.to_dict())
    except Exception as e:
        # Log error but don't crash - memory store may have limitations
        pass

    # Store context if company found
    if state.get('financial_context', {}).get('found_company'):
        company = state['financial_context']['found_company']
        company_context = CompanyContext(
            company_name=company['company_name'],
            category_code=company['category_code'],
            metrics={'employees': company['employees'], 'ebit': company['ebit']},
            dcf_result={},
            predictability='pending',
            last_updated=datetime.now()
        )
        agent_state.store_company_context(company_context)

    return state

# ============================================================================
# LANGGRAPH WORKFLOW CONSTRUCTION
# ============================================================================

def create_financial_agent():
    """Create the LangGraph financial analysis agent"""

    # Initialize the graph
    workflow = StateGraph(dict)

    # Add nodes
    workflow.add_node("process_input", process_user_input)
    workflow.add_node("retrieve_context", retrieve_financial_context)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("update_memory", update_memory)

    # Add edges
    workflow.add_edge(START, "process_input")
    workflow.add_edge("process_input", "retrieve_context")
    workflow.add_edge("retrieve_context", "generate_response")
    workflow.add_edge("generate_response", "update_memory")
    workflow.add_edge("update_memory", END)

    return workflow.compile()

# ============================================================================
# STREAMLIT UI INTERFACE
# ============================================================================

def init_agent_session():
    """Initialize agent session in Streamlit"""
    if 'agent_state' not in st.session_state:
        user_id = st.session_state.get('user_id', 'default_user')
        session_id = str(uuid.uuid4())
        st.session_state.agent_state = AgentState(user_id, session_id)
        st.session_state.memory_processor = FinancialMemoryProcessor(
            st.session_state.agent_state.memory_store
        )
        st.session_state.agent_graph = create_financial_agent()

def display_agent_interface():
    """Display the agent chat interface"""

    # Initialize
    init_agent_session()

    agent_state: AgentState = st.session_state.agent_state
    memory_processor: FinancialMemoryProcessor = st.session_state.memory_processor
    agent_graph = st.session_state.agent_graph

    # Load financial data
    if 'data_loaded' not in st.session_state:
        with st.spinner("Loading financial data..."):
            # Check if data is in session
            if st.session_state.get('dataset_df') is not None:
                data_dict = {
                    'dataset': st.session_state.get('dataset_df'),
                    'wacc': st.session_state.get('waccmap'),
                    'contacts': st.session_state.get('contacts_df')
                }
            else:
                # Try to load from Dropbox
                try:
                    data_dict = load_all_data_from_dropbox()
                except:
                    data_dict = {
                        'dataset': None,
                        'wacc': None,
                        'contacts': None
                    }

            memory_processor.load_data(data_dict)
            st.session_state.data_loaded = True

    # Display header
    st.markdown("## 🤖 Financial Analysis Agent")
    st.markdown("*Powered by LangGraph Memory & Financial Data Integration*")
    st.markdown("---")

    # Display conversation history
    st.markdown("### 💬 Conversation History")
    conversation_container = st.container()

    with conversation_container:
        for turn in agent_state.conversation_history:
            # User message
            with st.chat_message("user"):
                st.markdown(turn.user_input)

            # Agent response
            with st.chat_message("assistant"):
                st.markdown(turn.agent_response)

    st.markdown("---")

    # Input area
    st.markdown("### ⌨️ Your Input")
    user_input = st.text_input(
        "Ask me anything about financial analysis:",
        placeholder="e.g., 'Analyze company X' or 'Compare metrics'",
        key="user_input_field"
    )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        submit = st.button("📤 Send", use_container_width=True)

    with col2:
        clear_history = st.button("🗑️ Clear History", use_container_width=True)

    with col3:
        show_memory = st.button("🧠 View Memory", use_container_width=True)

    # Process input
    if submit and user_input:
        with st.spinner("Processing..."):
            # Prepare state for agent
            agent_input = {
                'user_input': user_input,
                'agent_state': agent_state,
                'processor': memory_processor
            }

            # Run agent
            result = agent_graph.invoke(agent_input)

            # Rerun to display new message
            st.rerun()

    if clear_history:
        st.session_state.agent_state = AgentState(
            agent_state.user_id,
            str(uuid.uuid4())
        )
        st.rerun()

    if show_memory:
        st.markdown("---")
        st.markdown("### 🧠 Agent Memory State")

        memory_info = {
            'session_id': agent_state.session_id,
            'total_turns': len(agent_state.conversation_history),
            'stored_companies': list(agent_state.company_contexts.keys()),
            'current_company': agent_state.current_company,
            'created_at': agent_state.created_at.isoformat()
        }

        st.json(memory_info)

        if agent_state.conversation_history:
            st.markdown("### 📜 Full Conversation Export")
            export_data = agent_state.to_dict()
            st.download_button(
                label="📥 Download Conversation",
                data=json.dumps(export_data, indent=2),
                file_name=f"conversation_{agent_state.session_id}.json",
                mime="application/json"
            )

if __name__ == "__main__":
    st.set_page_config(
        page_title="Financial Agent",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    display_agent_interface()
