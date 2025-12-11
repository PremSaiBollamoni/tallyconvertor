
import streamlit as st
import os
import json
import base64
import tempfile
from pathlib import Path
from pipeline import InvoiceProcessingPipeline

# --- CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="Tally Connector | AI Invoice Processor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look (Glassmorphism + Gradients)
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    }
    
    /* Typography */
    h1, h2, h3, p, div, label, span {
        color: #e2e8f0 !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Cards / Containers */
    .css-1r6slb0, .stMarkdown, .stButton, .stDownloadButton, [data-testid="stFileUploader"] {
        background-color: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 20px;
    }

    /* File Uploader */
    [data-testid="stFileUploader"] {
        border: 2px dashed #4f46e5;
        background-color: rgba(79, 70, 229, 0.1);
        text-align: center;
    }
    
    /* Primary Button */
    .stButton > button {
        background: linear-gradient(to right, #4f46e5, #4338ca);
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        width: 100%;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    /* Code Blocks */
    .stCode {
        background-color: #0f172a !important;
        border-radius: 8px;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.95);
        border-right: 1px solid rgba(148, 163, 184, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("📄 Tally Connector")
    st.markdown("---")
    st.markdown("""
    **Transform Invoices to Tally XML**
    
    Using advanced AI Computer Vision to:
    1. 📤 Upload Invoice Image
    2. 👁️ Extract Data (AI OCR)
    3. 🔄 Convert to Tally XML
    4. 📥 Import to TallyPrime
    """)
    st.info("Supported formats: PNG, JPG, JPEG")

# --- MAIN APP LOGIC ---

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📤 Upload Invoice")
    uploaded_file = st.file_uploader("Drop your invoice image here", type=['png', 'jpg', 'jpeg'])

    if uploaded_file is not None:
        # Show Preview
        st.image(uploaded_file, caption="Invoice Preview", use_column_width=True)
        
        # Process Button
        if st.button("🚀 Process Invoice", type="primary"):
            with st.spinner("Analyzing document with AI..."):
                try:
                    # Save to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name

                    # Initialize Pipeline
                    with tempfile.TemporaryDirectory() as output_dir:
                        pipeline = InvoiceProcessingPipeline(output_dir=output_dir)
                        
                        # Run Extraction
                        result = pipeline.process_single_invoice(tmp_path)
                        
                        # Cleanup temp input file
                        os.unlink(tmp_path)

                        if result["status"] == "success":
                            st.session_state['result'] = result
                            st.toast("Processing Complete!", icon="✅")
                        else:
                            st.error(f"Processing failed: {result.get('error')}")

                except Exception as e:
                    st.error(f"An unexpected error occurred: {str(e)}")


with col2:
    st.subheader("📊 Extraction Results")
    
    if 'result' in st.session_state:
        result = st.session_state['result']
        extracted_data = result['extracted_data']
        tally_xml = result['tally_xml']
        
        # Tabs for JSON vs XML
        tab_json, tab_xml = st.tabs(["JSON Data", "Tally XML"])
        
        with tab_json:
            st.json(extracted_data)
            
            # Download JSON
            json_str = json.dumps(extracted_data, indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name="invoice_data.json",
                mime="application/json"
            )

        with tab_xml:
            if tally_xml:
                # Combine XMLs if multiple
                full_xml = "\n".join(tally_xml.values())
                st.code(full_xml, language="xml")
                
                # Download XML
                st.download_button(
                    label="📥 Download Tally XML",
                    data=full_xml,
                    file_name="tally_import.xml",
                    mime="application/xml"
                )
            else:
                st.info("No XML generated.")
    else:
        st.info("Upload an invoice and click Process to see results here.")
        # Placeholder visual
        st.markdown("""
        <div style="text-align: center; padding: 40px; color: #64748b; border: 2px dashed #334155; border-radius: 12px;">
            Waiting for data...
        </div>
        """, unsafe_allow_html=True)
