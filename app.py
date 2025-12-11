
import streamlit as st
import os
import json
import base64
import tempfile
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io
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


# --- MAIN APP LOGIC ---

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📤 Upload Invoice(s)")
    uploaded_files = st.file_uploader("Drop invoice images or PDFs", 
                                    type=['png', 'jpg', 'jpeg', 'pdf'], 
                                    accept_multiple_files=True)

    if uploaded_files:
        st.success(f"{len(uploaded_files)} file(s) uploaded")
        
        # Process Button
        if st.button("🚀 Process All Invoices", type="primary"):
            st.session_state['all_results'] = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with tempfile.TemporaryDirectory() as temp_input_dir:
                
                for idx, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Processing {uploaded_file.name} ({idx+1}/{len(uploaded_files)})...")
                    
                    try:
                        # Prepare input images (List of pages)
                        input_image_paths = []
                        
                        if uploaded_file.type == "application/pdf":
                            # Process PDF - Extract ALL Pages
                            with fitz.open(stream=uploaded_file.getvalue(), filetype="pdf") as doc:
                                for page_num in range(len(doc)):
                                    page = doc.load_page(page_num)
                                    pix = page.get_pixmap()
                                    img_data = pix.tobytes("png")
                                    
                                    # Save page image
                                    page_filename = f"{Path(uploaded_file.name).stem}_page{page_num+1}.png"
                                    page_path = os.path.join(temp_input_dir, page_filename)
                                    with open(page_path, "wb") as f:
                                        f.write(img_data)
                                    input_image_paths.append(page_path)
                        else:
                            # Process Image
                            img_filename = uploaded_file.name
                            img_path = os.path.join(temp_input_dir, img_filename)
                            with open(img_path, "wb") as f:
                                f.write(uploaded_file.getvalue())
                            input_image_paths.append(img_path)

                        # Initialize Pipeline & Process
                        # We use a persistent output dir for the session if needed, 
                        # but for now temp dir per batch is fine as we read results immediately
                        with tempfile.TemporaryDirectory() as output_dir:
                            pipeline = InvoiceProcessingPipeline(output_dir=output_dir)
                            
                            # process_single_invoice now accepts List[str]
                            result = pipeline.process_single_invoice(input_image_paths)
                            
                            # Add original filename for reference
                            result['original_filename'] = uploaded_file.name
                            st.session_state['all_results'].append(result)
                            
                    except Exception as e:
                        st.error(f"Error processing {uploaded_file.name}: {e}")
                    
                    progress_bar.progress((idx + 1) / len(uploaded_files))
            
            status_text.text("Processing Complete! ✅")


with col2:
    st.subheader("📊 Extraction Results")
    
    if 'all_results' in st.session_state and st.session_state['all_results']:
        results = st.session_state['all_results']
        
        # Selector for multiple invoices
        invoice_options = [f"{r['original_filename']} ({r['status']})" for r in results]
        selected_option = st.selectbox("Select Invoice to View", invoice_options)
        
        # Find selected result
        selected_index = invoice_options.index(selected_option)
        result = results[selected_index]
        
        if result['status'] == 'success':
            extracted_data = result['extracted_data']
            tally_xml = result['tally_xml']
            
            # Show summary metrics
            if extracted_data:
                inv = extracted_data[0]
                m1, m2, m3 = st.columns(3)
                m1.metric("Invoice #", inv.get('invoice_number', 'N/A'))
                m2.metric("Date", inv.get('invoice_date', 'N/A'))
                m3.metric("Total", f"{inv.get('currency', '')} {inv.get('total_amount', 0)}")
            
            # Tabs for details
            tab_json, tab_xml = st.tabs(["JSON Data", "Tally XML"])
            
            with tab_json:
                st.json(extracted_data)
                json_str = json.dumps(extracted_data, indent=2)
                st.download_button("📥 Download JSON", json_str, f"invoice_{selected_index}.json", "application/json")

            with tab_xml:
                if tally_xml:
                    full_xml = "\n".join(tally_xml.values())
                    st.code(full_xml, language="xml")
                    st.download_button("📥 Download XML", full_xml, f"voucher_{selected_index}.xml", "application/xml")
                else:
                    st.warning("No XML generated")
        else:
            st.error(f"Processing Failed: {result.get('error')}")
            
    else:
        st.info("Upload invoices and click Process to start.")
        st.markdown("""
        <div style="text-align: center; padding: 40px; color: #64748b; border: 2px dashed #334155; border-radius: 12px;">
            Waiting for uploads...
        </div>
        """, unsafe_allow_html=True)
