import streamlit as st
import fitz  # PyMuPDF
import os
from PIL import Image
import pytesseract

# --- 1. CONFIGURATION ---
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
st.set_page_config(page_title="NS WORLD | Label Cropper", layout="wide")

st.title("✂️ PDF Label Cropper & Resizer")

# --- 2. MOBILE-FRIENDLY UPLOADERS ---
# We use two separate areas to keep the mobile browser from getting confused
st.subheader("1. Upload FMP Codes")
uploaded_images = st.file_uploader(
    "Select images (JPG/PNG)", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True,
    key="image_uploader"
)

st.subheader("2. Upload Label PDFs")
uploaded_pdfs = st.file_uploader(
    "Select PDF files", 
    type=['pdf'], 
    accept_multiple_files=True,
    key="pdf_uploader"
)

# --- 3. PROCESSING LOGIC ---
def process_labels(image_files, pdf_files):
    target_codes = set()
    
    # OCR Stage
    progress_bar = st.progress(0, text="Reading images...")
    for i, img_file in enumerate(image_files):
        try:
            pil_image = Image.open(img_file)
            text = pytesseract.image_to_string(pil_image).lower()
            codes = {word.strip(',.!') for word in text.split() if word.startswith('fmp')}
            target_codes.update(codes)
        except:
            continue
        progress_bar.progress((i + 1) / len(image_files), text=f"Read {img_file.name}")

    if not target_codes:
        st.error("No FMP codes found in images.")
        return None, None, None

    # PDF Processing Stage
    output_doc = fitz.open()
    found_codes = set()
    
    for pdf_file in pdf_files:
        # CRITICAL MOBILE FIX: Use .getvalue() instead of .read()
        pdf_bytes = pdf_file.getvalue() 
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text().lower()
            codes_on_page = {c for c in target_codes if c in page_text}
            
            if codes_on_page - found_codes:
                # Cropping logic
                x_off = (page.rect.width - 244.8) / 2
                source_rect = fitz.Rect(x_off, 0, x_off + 244.8, 396)
                new_page = output_doc.new_page(width=216, height=360)
                new_page.show_pdf_page(fitz.Rect(0, 0, 216, 360), doc, page_num, clip=source_rect)
                found_codes.update(codes_on_page)
        doc.close()

    if len(output_doc) > 0:
        output_path = "final_labels.pdf"
        output_doc.save(output_path)
        return output_path, target_codes, found_codes
    return None, target_codes, found_codes

# --- 4. RUN BUTTON ---
if st.button("🚀 Run Processor", type="primary"):
    if uploaded_images and uploaded_pdfs:
        path, total, found = process_labels(uploaded_images, uploaded_pdfs)
        if path:
            st.success(f"Done! Found {len(found)} labels.")
            with open(path, "rb") as f:
                st.download_button("📥 Download Final PDF", f, file_name="labels_3x5.pdf")
    else:
        st.warning("Please upload both images and PDFs.")
