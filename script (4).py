
# Create requirements.txt file
requirements = """# Core Dependencies
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
openpyxl>=3.1.0

# AI/LLM Dependencies
openai>=1.0.0
requests>=2.31.0

# Optional: For local LLM support
# ollama>=0.1.0
"""

with open('requirements.txt', 'w') as f:
    f.write(requirements)

print("✅ Created requirements.txt")
