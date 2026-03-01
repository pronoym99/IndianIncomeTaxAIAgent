"""Modern Streamlit UI for AI Tax Assistant - Clean Version"""

import streamlit as st
import os
import base64
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from datetime import datetime

# Import our chat functionality
from azure_openai import create_client, get_deployment_name

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Tax Assistant", 
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Simplified CSS for better visibility
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
        max-width: none;
    }
    
    /* Header styling */
    .header-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .header-section h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .header-section p {
        margin: 0.8rem 0 0 0;
        font-size: 1.2rem;
        opacity: 0.9;
    }

    /* Content Headings */
    .stChatMessage  h1 {
        font-size: 1.75rem;
    }
    .stChatMessage  h2 {
        font-size: 1.5rem;
    }
    .stChatMessage  h3 {
        font-size: 1.25rem;
    }
    
    /* Welcome section */
    .welcome-section {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
        border: 1px solid #e9ecef;
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #ddd;
        font-weight: 500;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* File upload styling */
    .uploadedFile {
        background-color: #e3f2fd;
        border: 1px solid #90caf9;
        border-radius: 8px;
        padding: 0.5rem;
        margin: 0.25rem 0;
    }
</style>
""", unsafe_allow_html=True)

SUPPORTED_TEXT_EXT = {'.txt', '.csv', '.md'}
SUPPORTED_PDF_EXT = {'.pdf'}  
SUPPORTED_IMG_EXT = {'.png', '.jpg', '.jpeg'}

def load_system_prompt() -> str:
    """Load the system prompt from markdown file."""
    path = os.environ.get("SYSTEM_PROMPT_PATH", "docs/system_prompt.md")
    if not os.path.exists(path):
        return ("You are an expert Indian Chartered Accountant–style AI Tax Assistant. "
                "If information is missing ask clarifying questions. End with a disclaimer.")
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract the main system prompt
    marker = "You are an expert Indian Chartered Accountant"
    if marker in content:
        seg = content.split(marker, 1)[1]
        seg = marker + seg
        for stop in ["CORE OBJECTIVES", "MANDATORY CLARIFYING"]:
            idx = seg.find(stop)
            if idx != -1:
                seg = seg[:idx]
                break
        return seg.strip()
    return content[:4000]

def process_uploaded_file(uploaded_file) -> Dict[str, Any]:
    """Process an uploaded file and extract content."""
    file_details = {"name": uploaded_file.name, "size": uploaded_file.size}
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    
    try:
        if file_ext in SUPPORTED_TEXT_EXT:
            content = uploaded_file.read().decode('utf-8', errors='ignore')
            return {
                "type": "text",
                "name": uploaded_file.name,
                "content": content,
                "details": file_details
            }
        elif file_ext in SUPPORTED_PDF_EXT:
            try:
                import PyPDF2
                from io import BytesIO
                
                pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
                text_parts = []
                for page in pdf_reader.pages:
                    try:
                        text_parts.append(page.extract_text() or "")
                    except Exception:
                        pass
                
                return {
                    "type": "pdf",
                    "name": uploaded_file.name,
                    "content": "\n".join(text_parts),
                    "details": file_details
                }
            except ImportError:
                st.error("PyPDF2 not installed. Cannot process PDF files.")
                return None
        elif file_ext in SUPPORTED_IMG_EXT:
            try:
                from PIL import Image
                from io import BytesIO
                
                image = Image.open(BytesIO(uploaded_file.read()))
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                return {
                    "type": "image",
                    "name": uploaded_file.name,
                    "content": img_str,
                    "details": file_details
                }
            except ImportError:
                st.error("PIL not installed. Cannot process image files.")
                return None
        else:
            st.error(f"Unsupported file type: {file_ext}")
            return None
    except Exception as e:
        st.error(f"Error processing {uploaded_file.name}: {str(e)}")
        return None

def build_message_with_files(user_input: str, files: List[Dict[str, Any]]) -> str:
    """Build user message including file contents."""
    # Get current financial year info
    current_date = datetime.now()
    if current_date.month >= 4:  # April to March is Indian FY
        current_fy = f"{current_date.year}-{current_date.year + 1}"
        previous_fy = f"{current_date.year - 1}-{current_date.year}"
    else:
        current_fy = f"{current_date.year - 1}-{current_date.year}"
        previous_fy = f"{current_date.year - 2}-{current_date.year - 1}"
    
    parts = [f"User Question: {user_input.strip()}"]
    parts.append(f"Current Financial Year: {current_fy}")
    parts.append(f"If no specific financial year is mentioned in documents or questions, assume {previous_fy} (previous FY).")
    
    if files:
        parts.append("\n--- ATTACHED DOCUMENTS FOR ANALYSIS ---")
        parts.append("Please extract specific values from these documents and use them in your analysis:")
        for i, file_data in enumerate(files, 1):
            if file_data['type'] in {"text", "pdf"}:
                content = file_data['content'][:4000]  # Limit content length
                if len(file_data['content']) > 4000:
                    content += "\n... (content truncated for brevity)"
                parts.append(f"\n📄 **Document {i}: {file_data['name']}** ({file_data['type']}, {len(file_data['content'])} chars):")
                parts.append(f"```\n{content}\n```")
            else:
                parts.append(f"\n🖼️ **Document {i}: {file_data['name']}** ({file_data['type']}): Image file attached (base64 encoded)")
    
    parts.append("\n🎯 **CRITICAL INSTRUCTIONS:**")
    parts.append("1. EXTRACT specific numerical values from the attached documents (salary amounts, deductions, TDS, etc.)")
    parts.append("2. USE these actual values in your calculations and regime comparisons")
    parts.append("3. CREATE detailed tables showing calculations based on the provided data")
    parts.append("4. PROVIDE personalized recommendations based on the specific numbers found")
    parts.append("5. If user says they don't have additional information, work with available data and make reasonable assumptions")
    parts.append("6. ALWAYS prompt for missing key information that would improve the analysis (investments, rent, dependents, etc.)")
    parts.append("7. Ask clarifying questions about: HRA eligibility, metro/non-metro city, health insurance premiums, existing investments")
    parts.append("8. For comprehensive analysis, inquire about: previous year returns, investment goals, risk appetite, family situation")
    
    # Add specific prompting strategies based on the query type
    user_input_lower = user_input.lower()
    
    if "form 16" in user_input_lower or "salary" in user_input_lower:
        parts.append("\n📋 **FOR FORM 16/SALARY ANALYSIS - PROMPT FOR:**")
        parts.append("- Current city (metro/non-metro) for HRA calculation")
        parts.append("- Rent amount and duration if claiming HRA")
        parts.append("- Health insurance premiums (self, parents, senior citizens)")
        parts.append("- Existing investments (EPF, PPF, ELSS, NSC, etc.)")
        parts.append("- Education loan interest payments")
        parts.append("- Charitable donations made")
    
    if "regime" in user_input_lower or "compare" in user_input_lower:
        parts.append("\n⚖️ **FOR REGIME COMPARISON - PROMPT FOR:**")
        parts.append("- Complete list of current deductions and investments")
        parts.append("- Future investment plans and capacity")
        parts.append("- Risk tolerance and investment preferences")
        parts.append("- Long-term financial goals")
    
    if "investment" in user_input_lower or "planning" in user_input_lower:
        parts.append("\n💰 **FOR INVESTMENT PLANNING - PROMPT FOR:**")
        parts.append("- Current age and retirement timeline")
        parts.append("- Risk appetite (conservative/moderate/aggressive)")
        parts.append("- Emergency fund status")
        parts.append("- Dependents and their insurance needs")
        parts.append("- Existing portfolio and performance")
    
    if "hra" in user_input_lower or "house" in user_input_lower:
        parts.append("\n🏠 **FOR HRA ANALYSIS - PROMPT FOR:**")
        parts.append("- Current residential city classification")
        parts.append("- Monthly rent amount and rental agreement details")
        parts.append("- Landlord's PAN details")
        parts.append("- Own house ownership status")
        parts.append("- Home loan EMI if applicable")
    
    # Check if user is indicating they don't have additional information
    user_input_lower = user_input.lower()
    if any(phrase in user_input_lower for phrase in ["don't have", "not have", "no additional", "missing", "unavailable"]):
        parts.append("\n⚠️ **USER INDICATED LIMITED INFORMATION AVAILABLE**")
        parts.append("The user has indicated they don't have additional information. Proceed with analysis using available data and make reasonable assumptions.")
    
    return "\n".join(parts)

def call_model(client, model: str, system_prompt: str, messages: List[Dict[str, str]]) -> str:
    """Call the AI model with the conversation."""
    try:
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Debug: Show what we're sending to the model (optional)
        if st.session_state.get('debug_mode', False):
            with st.expander("🔍 Debug: Messages sent to AI"):
                st.json({"message_count": len(full_messages), "last_user_message_preview": messages[-1]["content"][:500] if messages else "None"})
        
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=full_messages,
            max_tokens=1200
        )
        
        return resp.choices[0].message.content
        
    except Exception as e:
        try:
            # Fallback for different API versions
            resp = client.responses.create(
                model=model,
                input=full_messages,
                temperature=0,
                max_output_tokens=1200
            )
            return resp.output_text
        except Exception:
            return f"❌ Error calling AI model: {str(e)}"

def clean_and_format_response(response: str) -> str:
    """Clean and format AI response for better display in Streamlit."""
    if not response:
        return response
    
    import re
    
    # Split into lines for processing
    lines = response.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Skip lines that are just excessive pipe characters
        if re.match(r'^\s*\|{10,}\s*$', line):
            continue
            
        # If line has too many pipes (malformed table), try to fix it
        if '|' in line:
            pipe_count = line.count('|')
            if pipe_count > 15:  # Likely malformed
                # Extract meaningful text between pipes
                parts = [part.strip() for part in line.split('|') if part.strip() and not re.match(r'^-+$', part.strip())]
                if parts and len(parts) <= 6:  # Reasonable number of columns
                    # Reconstruct as proper table row
                    line = '| ' + ' | '.join(parts) + ' |'
                else:
                    # Skip this malformed line
                    continue
            elif pipe_count >= 3:  # Looks like a table
                # Clean up spacing in table
                parts = line.split('|')
                cleaned_parts = []
                for part in parts:
                    cleaned_part = part.strip()
                    # Skip empty parts at start/end
                    if cleaned_part or (len(cleaned_parts) > 0 and len(cleaned_parts) < len(parts) - 1):
                        cleaned_parts.append(cleaned_part)
                
                if len(cleaned_parts) > 1:
                    line = '| ' + ' | '.join(cleaned_parts) + ' |'
        
        # Clean up whitespace
        line = re.sub(r'\s+', ' ', line).strip()
        
        if line:  # Only add non-empty lines
            formatted_lines.append(line)
    
    formatted_response = '\n'.join(formatted_lines)
    
    # Final cleanup
    formatted_response = re.sub(r'\n{3,}', '\n\n', formatted_response)  # Remove excessive newlines
    
    return formatted_response

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'client' not in st.session_state:
    try:
        st.session_state.client = create_client()
        st.session_state.model = get_deployment_name()
        st.session_state.system_prompt = load_system_prompt()
    except Exception as e:
        st.error(f"Failed to initialize AI client: {e}")
        st.stop()

# Header
st.markdown("""
<div class="header-section">
    <h1>🧾 AI Tax Assistant</h1>
    <p>Your Expert Indian Chartered Accountant • Intelligent Document Analysis • Tax Optimization</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for file uploads and controls
with st.sidebar:
    st.markdown("### 📎 Document Upload")
    st.markdown("*Upload your tax documents for personalized analysis*")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose files",
        type=['txt', 'csv', 'md', 'pdf', 'png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        help="📄 Form 16 • 💰 Salary slips • 📊 Investment proofs • 🏠 Rent receipts",
        label_visibility="collapsed"
    )
    
    # Process uploaded files
    if uploaded_files:
        processed_files = []
        for uploaded_file in uploaded_files:
            processed_file = process_uploaded_file(uploaded_file)
            if processed_file:
                processed_files.append(processed_file)
        st.session_state.uploaded_files = processed_files
    
    st.markdown("---")
    
    # Document status in sidebar
    # st.markdown("### 📁 Document Status")
    if st.session_state.uploaded_files:
        if st.button("🗑️ Clear Files", use_container_width=True):
            st.session_state.uploaded_files = []
            st.rerun()
            st.markdown("---")
    
    # Enhanced Quick Actions with comprehensive tax scenarios
    # st.markdown("### 🚀 Comprehensive Tax Analysis")
    
    # Form 16 Analysis Section
    st.markdown("**📋 Form 16 Analysis:**")
    
    if st.button("📊 Analyze Form 16 Part A & B", use_container_width=True):
        prompt = "Please provide a comprehensive analysis of my Form 16 including:\n1. Part A (TDS Certificate) analysis\n2. Part B (Computation of Income) breakdown\n3. Salary components (Basic, HRA, Allowances, Perquisites)\n4. All deductions claimed (Section 16, 80C, 80D, etc.)\n5. Tax computation and TDS details\n6. Insights and optimization opportunities"
        if st.session_state.uploaded_files:
            st.session_state.messages.append({"role": "user", "content": build_message_with_files(prompt, st.session_state.uploaded_files)})
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
        response = call_model(st.session_state.client, st.session_state.model, st.session_state.system_prompt, st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
    
    if st.button("📈 Salary Breakdown Analysis", use_container_width=True):
        prompt = "Break down my salary structure in detail:\n1. Basic salary, allowances (HRA, LTA, Medical, etc.)\n2. Perquisites and their tax implications\n3. Bonus, commissions, and variable pay\n4. Section 10 exemptions available (HRA, LTA, gratuity)\n5. Standard deduction and professional tax\n6. Recommendations for salary restructuring"
        if st.session_state.uploaded_files:
            st.session_state.messages.append({"role": "user", "content": build_message_with_files(prompt, st.session_state.uploaded_files)})
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
        response = call_model(st.session_state.client, st.session_state.model, st.session_state.system_prompt, st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
    
    # Tax Regime Comparison
    st.markdown("**⚖️ Tax Regime Analysis:**")
    
    if st.button("🆚 Old vs New Regime Comparison", use_container_width=True):
        prompt = "Provide a detailed comparison of Old vs New tax regime for my situation:\n1. Tax calculation under both regimes\n2. Available deductions in each regime\n3. Net tax liability comparison\n4. Take-home salary impact\n5. Which regime is better and why?\n6. Multi-year projection and recommendations"
        if st.session_state.uploaded_files:
            st.session_state.messages.append({"role": "user", "content": build_message_with_files(prompt, st.session_state.uploaded_files)})
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
        response = call_model(st.session_state.client, st.session_state.model, st.session_state.system_prompt, st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
    
    # Investment & Deduction Planning
    st.markdown("**💰 Investment & Tax Planning:**")
    
    if st.button("🎯 Complete Deduction Analysis", use_container_width=True):
        prompt = "Analyze all possible deductions for my situation:\n1. Section 80C investments (EPF, PPF, ELSS, Insurance)\n2. Section 80D health insurance premiums\n3. Section 80E education loan interest\n4. Section 80G charitable donations\n5. Other applicable deductions (80TTA, 24b, etc.)\n6. Unused deduction limits and recommendations"
        if st.session_state.uploaded_files:
            st.session_state.messages.append({"role": "user", "content": build_message_with_files(prompt, st.session_state.uploaded_files)})
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
        response = call_model(st.session_state.client, st.session_state.model, st.session_state.system_prompt, st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
    
    if st.button("📊 Investment Recommendations", use_container_width=True):
        prompt = "Suggest optimal investment strategy based on my profile:\n1. Tax-saving investments for immediate benefit\n2. Long-term wealth creation options\n3. Risk-appropriate portfolio allocation\n4. Emergency fund recommendations\n5. Insurance needs analysis\n6. Timeline-based investment planning"
        if st.session_state.uploaded_files:
            st.session_state.messages.append({"role": "user", "content": build_message_with_files(prompt, st.session_state.uploaded_files)})
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
        response = call_model(st.session_state.client, st.session_state.model, st.session_state.system_prompt, st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
    
    # Tax Assessment & Planning
    st.markdown("**📋 Tax Assessment:**")
    
    if st.button("� Tax Liability Assessment", use_container_width=True):
        prompt = "Calculate my complete tax assessment:\n1. Total taxable income computation\n2. Tax liability under applicable slabs\n3. TDS vs actual tax liability\n4. Refund due or additional tax payable\n5. Advance tax planning for next year\n6. ITR filing guidance and timeline"
        if st.session_state.uploaded_files:
            st.session_state.messages.append({"role": "user", "content": build_message_with_files(prompt, st.session_state.uploaded_files)})
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
        response = call_model(st.session_state.client, st.session_state.model, st.session_state.system_prompt, st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
    
    st.markdown("---")
    
    # Tips moved to sidebar
    st.markdown("### 💡 Quick Tips")
    st.markdown("""
    📊 **Form 16** gives best analysis  
    💰 **Include salary slips** for accuracy  
    📈 **Upload investment proofs** for optimization  
    🏠 **Add rent receipts** for HRA claims
    """)
    
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    
    debug_mode = st.checkbox("Debug Mode", help="Show detailed message information")
    st.session_state.debug_mode = debug_mode
    
    if st.button("🔄 New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Main chat interface - full width
st.markdown("### 💬 Chat with Your Tax Expert")

# Display attached files indicator if any files are uploaded
if st.session_state.uploaded_files:
    with st.expander(f"📎 {len(st.session_state.uploaded_files)} file(s) attached - Click to view details", expanded=False):
        for i, file_data in enumerate(st.session_state.uploaded_files):
            file_icon = "📄" if file_data['type'] in ['text', 'pdf'] else "🖼️"
            
            # Use columns for better layout
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown(file_icon)
            with col2:
                st.markdown(f"**{file_data['name']}**")
                st.caption(f"{file_data['type'].upper()} • {file_data['details']['size']} bytes")
            
            # Show preview for text files
            if file_data['type'] in ['text', 'pdf'] and st.checkbox(f"Show preview", key=f"preview_{i}"):
                preview = file_data['content'][:500]
                if len(file_data['content']) > 500:
                    preview += "\n... (content truncated)"
                st.text_area("Content Preview", preview, height=100, disabled=True, key=f"content_{i}")

# Welcome message when no chat history
if not st.session_state.messages:
    st.markdown("### 👋 Welcome! How can I help you today?")
    st.markdown("I'm your expert CA assistant, ready to analyze your tax documents and provide personalized advice.")
    
    # Enhanced Quick action buttons that work with attachments
    st.markdown("**📋 Form 16 & Document Analysis:**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Form 16 Analysis", use_container_width=True):
            question = "Provide comprehensive Form 16 analysis including Part A & B breakdown, salary components, deductions, and tax computation with optimization suggestions."
            full_message = build_message_with_files(question, st.session_state.uploaded_files)
            st.session_state.messages.append({"role": "user", "content": full_message})
            st.rerun()
    
    with col2:
        if st.button("⚖️ Tax Regime Compare", use_container_width=True):
            question = "Compare old vs new tax regime for my specific situation. Show detailed calculations, tax liability, and recommend the better option with reasoning."
            full_message = build_message_with_files(question, st.session_state.uploaded_files)
            st.session_state.messages.append({"role": "user", "content": full_message})
            st.rerun()
    
    with col3:
        if st.button("💰 Tax Assessment", use_container_width=True):
            question = "Calculate my complete tax assessment: total taxable income, tax liability, TDS analysis, refund/payment due, and next year planning."
            full_message = build_message_with_files(question, st.session_state.uploaded_files)
            st.session_state.messages.append({"role": "user", "content": full_message})
            st.rerun()
    
    with col4:
        if st.button("📈 Salary Breakdown", use_container_width=True):
            question = "Analyze my salary structure in detail: basic salary, allowances, perquisites, exemptions, deductions, and restructuring recommendations."
            full_message = build_message_with_files(question, st.session_state.uploaded_files)
            st.session_state.messages.append({"role": "user", "content": full_message})
            st.rerun()
    
    st.markdown("**💡 Investment & Tax Planning:**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🎯 Deduction Analysis", use_container_width=True):
            question = "Analyze all possible deductions (80C, 80D, 80E, 80G, etc.) for my situation, show unused limits, and recommend optimal utilization."
            full_message = build_message_with_files(question, st.session_state.uploaded_files)
            st.session_state.messages.append({"role": "user", "content": full_message})
            st.rerun()
    
    with col2:
        if st.button("� Investment Guide", use_container_width=True):
            question = "Recommend optimal investment strategy based on my profile: tax-saving options, wealth creation, risk allocation, and timeline-based planning."
            full_message = build_message_with_files(question, st.session_state.uploaded_files)
            st.session_state.messages.append({"role": "user", "content": full_message})
            st.rerun()
    
    with col3:
        if st.button("🏠 HRA Optimization", use_container_width=True):
            question = "Analyze my HRA situation: exemption calculation, rent vs ownership benefits, metro/non-metro impact, and optimization strategies."
            full_message = build_message_with_files(question, st.session_state.uploaded_files)
            st.session_state.messages.append({"role": "user", "content": full_message})
            st.rerun()
    
    with col4:
        if st.button("🔮 Next Year Planning", use_container_width=True):
            question = "Create next year tax planning strategy: investment recommendations, salary restructuring, advance tax planning, and timeline for actions."
            full_message = build_message_with_files(question, st.session_state.uploaded_files)
            st.session_state.messages.append({"role": "user", "content": full_message})
            st.rerun()
    
    # st.markdown("**📋 Detailed Analysis Options:**")
    
    # col1, col2 = st.columns(2)
    
    # with col1:
    #     if st.button("🩺 Health Insurance Analysis", use_container_width=True):
    #         question = "Analyze health insurance for tax benefits: Section 80D optimization for self, parents, and senior citizens with premium recommendations."
    #         full_message = build_message_with_files(question, st.session_state.uploaded_files)
    #         st.session_state.messages.append({"role": "user", "content": full_message})
    #         st.rerun()
    
    # with col2:
    #     if st.button("📄 ITR Filing Guide", use_container_width=True):
    #         question = "Guide me through ITR filing process: which form to use, key sections to fill, documents needed, and common mistakes to avoid."
    #         full_message = build_message_with_files(question, st.session_state.uploaded_files)
    #         st.session_state.messages.append({"role": "user", "content": full_message})
    #         st.rerun()
    
    # st.markdown("**📝 Popular Questions & Use Cases:**")
    # st.markdown("• **Form 16 Analysis:** Understand Part A/B, salary breakdown, deductions claimed")
    # st.markdown("• **Tax Regime:** Should I choose old or new tax regime? Show detailed comparison")
    # st.markdown("• **Deductions:** What are all possible deductions I can claim? (80C, 80D, 80E, etc.)")
    # st.markdown("• **Investment Planning:** Recommend tax-saving investments based on my salary")
    # st.markdown("• **HRA Optimization:** How to maximize HRA exemption? Metro vs non-metro benefits")
    # st.markdown("• **Health Insurance:** Section 80D benefits for self, parents, senior citizens")
    # st.markdown("• **Tax Assessment:** How much tax do I owe or get as refund?")
    # st.markdown("• **Next Year Planning:** What should I do next financial year to reduce tax?")
    # st.markdown("• **Salary Restructuring:** How to optimize my salary components for tax efficiency")
    # st.markdown("• **ITR Filing:** Which ITR form should I use and how to file correctly?")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            # Check if this message contains file attachments
            content = message["content"]
            if "--- ATTACHED DOCUMENTS FOR ANALYSIS ---" in content:
                # Split user question from file content
                parts = content.split("--- ATTACHED DOCUMENTS FOR ANALYSIS ---", 1)
                user_question = parts[0].replace("User Question:", "").strip()
                
                st.markdown(f"**Question:** {user_question}")
                if st.session_state.uploaded_files:
                    st.caption(f"📎 {len(st.session_state.uploaded_files)} document(s) analyzed")
            else:
                st.markdown(content)
        else:
            st.markdown(message["content"])

# Handle pending AI response (when quick actions are clicked)
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    # Get AI response for the last user message
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your query..."):
            response = call_model(
                st.session_state.client,
                st.session_state.model,
                st.session_state.system_prompt,
                st.session_state.messages
            )
        
        st.markdown(clean_and_format_response(response))
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()  # Rerun to update the display

# Chat input
if prompt := st.chat_input("Ask me anything about Indian taxes..."):
    # Build message with attached files
    full_message = build_message_with_files(prompt, st.session_state.uploaded_files)
    
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": full_message})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(f"**Question:** {prompt}")
        if st.session_state.uploaded_files:
            st.markdown(f"📎 **{len(st.session_state.uploaded_files)} file(s) attached**")
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your query..."):
            response = call_model(
                st.session_state.client,
                st.session_state.model,
                st.session_state.system_prompt,
                st.session_state.messages
            )
        
        st.markdown(clean_and_format_response(response))
        st.session_state.messages.append({"role": "assistant", "content": response})
