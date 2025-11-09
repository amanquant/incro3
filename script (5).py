
# Create comprehensive README documentation
readme = """# Incrolink Agent - AI-Powered Finance Intelligence Platform

An intelligent DCF (Discounted Cash Flow) valuation platform with integrated AI assistant capabilities. This application combines traditional financial analysis with modern conversational AI to provide an intuitive interface for company valuation.

## 🎯 Features

### Core Functionality
- **DCF Valuation Engine**: Automated Discounted Cash Flow analysis
- **Company Search**: Natural language search through company datasets
- **WACC Integration**: Weighted Average Cost of Capital mapping
- **Enterprise Value Calculation**: Current and projected valuations

### AI Assistant Features
- **Conversational Interface**: Chat-based interaction using Streamlit's native chat components
- **Multi-Provider Support**: Choose from 4 free LLM providers
- **Natural Language Queries**: Search and analyze companies using plain English
- **Smart Query Processing**: Understands file upload, search, and analysis requests
- **Financial Explanations**: Get AI-powered insights on valuation metrics

### Supported Free LLM Providers

| Provider | Speed | Free Tier | Best For | Setup Difficulty |
|----------|-------|-----------|----------|------------------|
| **Groq** ⭐ | ⚡ Very Fast | 500k tokens/day | Production use | Easy |
| **Ollama** | 🔥 Fast | Unlimited (local) | Privacy, offline use | Medium |
| **OpenRouter** | ⚡ Fast | Limited free models | Testing multiple models | Easy |
| **GitHub Models** | 🔥 Fast | Rate limited | GitHub users | Easy |

**Recommended:** Groq for best balance of speed, quality, and free tier limits.

## 📋 Requirements

### System Requirements
- Python 3.8+
- 4GB+ RAM
- Internet connection (except for Ollama)

### Data Requirements
Your dataset must include these columns:
- `company` - Company name
- `nace` - NACE industry code
- `ebit` - Earnings Before Interest and Taxes
- `employees` - Number of employees
- `net income` - Net income
- `capex` - Capital expenditures
- `d&a` - Depreciation and amortization
- `changes in wc` - Changes in working capital
- `lt debt` - Long-term debt
- `st debt` - Short-term debt
- `sh equity` - Shareholder equity
- `capital equity` - Capital equity
- `cash` - Cash and equivalents
- `category_code` - Category code for WACC mapping

## 🚀 Quick Start

### Installation

```bash
# Clone or download the project
git clone <repository-url>
cd incrolink-agent

# Install dependencies
pip install -r requirements.txt
```

### Setup Options

#### Option 1: Groq (Recommended - Fastest Setup)

```bash
# 1. Sign up at https://console.groq.com
# 2. Get your free API key (no credit card required)
# 3. Set environment variable
export GROQ_API_KEY='your-groq-api-key'

# 4. Run the app
streamlit run incrolink_agent_ai_enhanced.py
```

#### Option 2: Ollama (Local - No API Key)

```bash
# 1. Install Ollama from https://ollama.com
# For macOS/Linux:
curl -fsSL https://ollama.com/install.sh | sh

# For Windows: Download installer from website

# 2. Pull a model
ollama pull llama3.2

# 3. Start Ollama server (keep this running)
ollama serve

# 4. In another terminal, run the app
streamlit run incrolink_agent_ai_enhanced.py
```

#### Option 3: OpenRouter

```bash
# 1. Sign up at https://openrouter.ai
# 2. Get API key
# 3. Set environment variable
export OPENROUTER_API_KEY='your-key'

# 4. Run the app
streamlit run incrolink_agent_ai_enhanced.py
```

#### Option 4: GitHub Models

```bash
# 1. Generate GitHub Personal Access Token
# Visit: https://github.com/settings/personal-access-tokens/new
# 2. Set environment variable
export GITHUB_TOKEN='your-pat'

# 3. Run the app
streamlit run incrolink_agent_ai_enhanced.py
```

## 💡 Usage Guide

### 1. Launch Application

```bash
streamlit run incrolink_agent_ai_enhanced.py
```

The app will open in your browser at `http://localhost:8501`

### 2. Configure AI Assistant

In the sidebar:
- Select your LLM provider (e.g., "Groq (Free)")
- Enter API key if required (or load from environment variable)
- Choose model (e.g., "llama-3.3-70b-versatile")

### 3. Upload Data

In the sidebar:
- Click "Upload Dataset (XLSX)" → Select your company data file
- Click "Upload WACC Map (XLSX)" → Select your WACC parameters file

### 4. Interact with AI Assistant

Example queries you can ask:

**Search for companies:**
```
"Search for companies in the technology sector"
"Find companies with 'Tesla' in their name"
"Look for automotive companies"
```

**Run DCF analysis:**
```
"Analyze Apple Inc"
"Run DCF valuation for Microsoft"
"What is the valuation of Google?"
```

**General questions:**
```
"Explain what WACC means"
"What is enterprise value?"
"How does DCF valuation work?"
```

## 🏗️ Architecture

### Code Structure

```
incrolink_agent_ai_enhanced.py
├── Configuration
│   ├── Column requirements
│   └── LLM provider configurations
├── Core DCF Functions (preserved from original)
│   ├── validate_columns()
│   └── DCF_automated()
├── AI Assistant Functions
│   ├── get_llm_client()
│   ├── get_ai_response()
│   ├── create_system_prompt()
│   └── process_user_query()
└── Streamlit UI
    ├── Sidebar (config & file upload)
    └── Main chat interface
```

### Data Flow

```
User Input → Chat Interface
    ↓
Query Processing
    ├── File Upload Request → Guide to sidebar
    ├── Company Search → Search dataset
    ├── DCF Analysis → Run calculation
    └── General Question → AI assistant
    ↓
Response Generation
    ↓
Chat Display
```

## 🔧 Customization

### Adding New LLM Providers

Edit the `LLM_PROVIDERS` dictionary in the code:

```python
LLM_PROVIDERS = {
    "Your Provider": {
        "env_var": "YOUR_API_KEY_VAR",
        "base_url": "https://api.yourprovider.com/v1",
        "models": ["model-1", "model-2"],
        "default_model": "model-1"
    }
}
```

### Customizing System Prompt

Modify the `create_system_prompt()` function to change AI behavior:

```python
def create_system_prompt() -> str:
    return """Your custom system prompt here..."""
```

### Adjusting DCF Parameters

Modify the `DCF_automated()` function to change:
- Projection years
- Terminal value calculation
- Discount methodology

## 🐛 Troubleshooting

### Common Issues

**Issue: "API key not found"**
```bash
# Solution: Set environment variable
export GROQ_API_KEY='your-key'
# Or enter directly in sidebar
```

**Issue: "Ollama error: Make sure Ollama is running"**
```bash
# Solution: Start Ollama server
ollama serve
```

**Issue: "Missing required columns"**
```
Solution: Ensure your Excel file has all required columns.
Check the "Required Columns" section in the sidebar.
```

**Issue: "ModuleNotFoundError: No module named 'openai'"**
```bash
# Solution: Install requirements
pip install -r requirements.txt
```

### Performance Optimization

**For faster responses:**
1. Use Groq with Llama 3.3 70B (fastest API)
2. Use Ollama locally with smaller models (8B parameters)
3. Reduce chat history context (modify `messages[-5:]` to `messages[-3:]`)

**For better quality responses:**
1. Use larger models (70B+ parameters)
2. Increase max_tokens in `get_ai_response()`
3. Provide more context in queries

## 📊 Example Datasets

### Sample Dataset Structure (dataset.xlsx)

| company | nace | ebit | employees | net income | ... |
|---------|------|------|-----------|------------|-----|
| Acme Corp | 6201 | 1000000 | 500 | 800000 | ... |
| Tech Inc | 6202 | 2000000 | 1000 | 1500000 | ... |

### Sample WACC Map Structure (wacc_map.xlsx)

| category_code | re | rd | wacc | g |
|---------------|-----|-----|------|-----|
| 6201 | 0.10 | 0.05 | 0.08 | 0.03 |
| 6202 | 0.12 | 0.06 | 0.09 | 0.04 |

## 🔒 Security & Privacy

### API Key Safety
- Never commit API keys to version control
- Use environment variables for production
- Rotate keys regularly

### Data Privacy
- Use Ollama for sensitive data (runs locally)
- Check provider terms for data retention policies
- Groq doesn't use free tier data for training

### Best Practices
```python
# ✅ Good: Use environment variables
api_key = os.getenv('GROQ_API_KEY')

# ❌ Bad: Hardcode keys
api_key = 'gsk_abc123...'  # Don't do this!
```

## 📈 Comparison with Original

| Feature | Original | AI Enhanced |
|---------|----------|-------------|
| Interface | Sidebar search | Chat-based |
| File Upload | Sidebar only | Sidebar + chat guidance |
| Search | Manual text input | Natural language |
| Analysis | Button-triggered | Conversational |
| Help | Static | AI-powered |
| Multi-provider | ❌ | ✅ 4 providers |
| Cost | Free | Free |

## 🚀 Deployment

### Local Development
```bash
streamlit run incrolink_agent_ai_enhanced.py
```

### Streamlit Cloud
1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Connect repository
4. Add API keys in Secrets:
   ```toml
   GROQ_API_KEY = "your-key"
   ```
5. Deploy!

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "incrolink_agent_ai_enhanced.py"]
```

## 🤝 Contributing

Feel free to:
- Add new LLM providers
- Improve query processing logic
- Enhance financial calculations
- Add new features

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- Streamlit for the amazing framework
- Groq for ultra-fast inference
- Meta for Llama models
- OpenAI for the API standard

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Check troubleshooting section
- Review provider documentation

---

**Built with ❤️ for finance professionals**
"""

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(readme)

print("✅ Created comprehensive README.md")
print("\n" + "="*80)
print("DOCUMENTATION COMPLETE")
print("="*80)
