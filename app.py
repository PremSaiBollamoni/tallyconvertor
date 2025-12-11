import streamlit as st
import json
from invoice_extractor import process_invoice_image
from tally_converter import TallyXMLConverter
from datetime import datetime
import os
import tempfile

st.set_page_config(page_title="Invoice to Tally Converter", layout="wide")

st.title("📄 Invoice to Tally Converter")
st.markdown("Extract invoice data and generate Tally XML")

st.divider()

# Upload section
st.subheader("📤 Upload Invoice Image")
uploaded_file = st.file_uploader(
    "Select an invoice image",
    type=["png", "jpg", "jpeg"],
    help="Supported formats: PNG, JPG, JPEG"
)

if uploaded_file:
    col1, col2 = st.columns(2)
    
    with col1:
        if uploaded_file.type.startswith('image/'):
            st.image(uploaded_file, caption="Invoice Preview")
    
    with col2:
        st.info(f"✓ File: {uploaded_file.name}")
        st.info(f"Size: {len(uploaded_file.getbuffer())} bytes")
    
    st.divider()
    
    if st.button("🚀 Extract & Convert to XML", use_container_width=True, type="primary"):
        temp_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            # Extract invoice data
            with st.spinner("🔄 Extracting invoice data..."):
                invoices = process_invoice_image(temp_path)
            
            if not invoices or (invoices and "error" in invoices[0]):
                st.error(f"❌ Error: {invoices[0].get('error') if invoices else 'No data'}")
            else:
                st.success(f"✓ Extracted {len(invoices)} invoice(s)")
                
                # Show extracted data
                st.subheader("📋 Extracted Data")
                for idx, invoice in enumerate(invoices, 1):
                    with st.expander(f"Invoice {idx}: {invoice.get('invoice_number', 'N/A')}"):
                        st.json(invoice)
                
                st.divider()
                
                # Generate XML
                with st.spinner("🔄 Generating Tally XML..."):
                    converter = TallyXMLConverter()
                    xml_outputs = []
                    json_outputs = []
                    
                    for invoice in invoices:
                        xml_content = converter.create_tally_voucher(invoice)
                        xml_outputs.append((invoice.get('invoice_number', 'unknown'), xml_content))
                        json_outputs.append((invoice.get('invoice_number', 'unknown'), invoice))
                
                st.success("✓ Generated files")
                
                # Download buttons
                st.subheader("📥 Download")
                col1, col2 = st.columns(2)
                
                with col1:
                    for invoice_num, json_data in json_outputs:
                        json_str = json.dumps(json_data, indent=2)
                        st.download_button(
                            label=f"📄 {invoice_num}.json",
                            data=json_str,
                            file_name=f"invoice_{invoice_num}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                
                with col2:
                    for invoice_num, xml_content in xml_outputs:
                        st.download_button(
                            label=f"📦 voucher_{invoice_num}.xml",
                            data=xml_content,
                            file_name=f"voucher_{invoice_num}.xml",
                            mime="application/xml",
                            use_container_width=True
                        )
                
                st.divider()
                
                # Raw data viewers
                with st.expander("📊 View Raw JSON"):
                    for invoice_num, json_data in json_outputs:
                        st.markdown(f"**{invoice_num}**")
                        st.json(json_data)
                
                with st.expander("📋 View Raw XML"):
                    for invoice_num, xml_content in xml_outputs:
                        st.markdown(f"**{invoice_num}**")
                        st.code(xml_content, language="xml")
        
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
        
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

else:
    st.info("👆 Upload an invoice image to get started")
