import streamlit as st
import os
import json
import base64
from typing import List, Dict, Any, Optional
import google.generativeai as genai
import pandas as pd

# Only set page config when running magic_box.py directly, not when importing functions
if __name__ == "__main__":
    # Set page config
    st.set_page_config(
        page_title="Document Classification System",
        page_icon="📄",
        layout="wide"
    )

    # Styling
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1E3A8A;
            margin-bottom: 1.5rem;
            text-align: center;
        }
        .sub-header {
            font-size: 1.5rem;
            font-weight: 600;
            color: #2563EB;
            margin-bottom: 1rem;
        }
        .card {
            background-color: #F3F4F6;
            border-radius: 0.5rem;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        .doc-card {
            background-color: white;
            border: 1px solid #E5E7EB;
            border-radius: 0.5rem;
            padding: 1.2rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .doc-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .tag-critical {
            background-color: #FEE2E2;
            color: #B91C1C;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        .tag-important {
            background-color: #FEF3C7;
            color: #92400E;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        .tag-optional {
            background-color: #E0F2FE;
            color: #0369A1;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        .status {
            color: #6B7280;
            font-size: 0.9rem;
            font-weight: 400;
            margin-bottom: 0.5rem;
        }
        .upload-box {
            border: 2px dashed #D1D5DB;
            border-radius: 0.5rem;
            padding: 2rem;
            text-align: center;
            background-color: #F9FAFB;
            height: 100%;
            min-height: 300px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .upload-icon {
            font-size: 2.5rem;
            color: #9CA3AF;
            margin-bottom: 1rem;
        }
        .upload-text {
            color: #4B5563;
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }
        .file-types {
            color: #6B7280;
            font-size: 0.875rem;
        }
        .positive {
            color: #047857;
            font-weight: 600;
        }
        .likely {
            color: #0369A1;
            font-weight: 600;
        }
        .possible {
            color: #B45309;
            font-weight: 600;
        }
        .uncertain {
            color: #7F1D1D;
            font-weight: 600;
        }
        .metadata-item {
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
        }
        .metadata-container {
            margin-top: 0.5rem;
            padding: 0.75rem;
            background-color: #F9FAFB;
            border-radius: 0.25rem;
            border: 1px solid #E5E7EB;
        }
        .metadata-title {
            font-weight: 600;
            margin-bottom: 0.5rem;
            font-size: 0.95rem;
        }
        .results-section {
            margin-top: 2rem;
        }
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.markdown("<h1 class='main-header'>Document Classification System</h1>", unsafe_allow_html=True)
    
    # Initialize session state to store classification results
    if 'classification_results' not in st.session_state:
        st.session_state.classification_results = None
    
    # Sidebar for API key
    with st.sidebar:
        st.markdown("<h2 class='sub-header'>Configuration</h2>", unsafe_allow_html=True)
        api_key = st.text_input("Enter Gemini API Key", type="password")
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                st.success("API key configured successfully!")
            except Exception as e:
                st.error(f"Error configuring API: {str(e)}")
        
        st.markdown("---")
        st.markdown("""
        ## Supported Document Types
        - Bank Statement
        - Financial Statement
        - Project List
        - GOSI Certificate
        - VAT Statement/Return
        - Saudization Certificate
        - Project Contract
        - Commercial Registration (CR)
        - Company Profile
        """)
    
    # Define document requirements (including all supported types)
    doc_requirements = [
        {"name": "Commercial Registration (CR)", "type": "CR", "importance": "critical"},
        {"name": "GOSI Certificate", "type": "GOSI", "importance": "important"},
        {"name": "VAT Certificate", "type": "VAT Statement", "importance": "critical"},
        {"name": "Bank Statements", "type": "Bank Statement", "importance": "critical"},
        {"name": "Financial Statements", "type": "Financial Statement", "importance": "critical"},
        {"name": "VAT Returns", "type": "VAT Statement", "importance": "important"},
        {"name": "Project Contracts", "type": "Project Contract", "importance": "important"},
        {"name": "Project List", "type": "Project List", "importance": "important"},
        {"name": "Saudization Certificate", "type": "Saudization Certificate", "importance": "optional"},
        {"name": "Company Profile", "type": "Company Profile", "importance": "optional"}
    ]
    
    # Main content - Two column layout
    col1, col2 = st.columns([1, 1])
    
    with col2:
        st.markdown("<h2 class='sub-header'>Upload Documents</h2>", unsafe_allow_html=True)
        
        # Create custom upload box
        st.markdown("""
        <div class="upload-box">
            <div class="upload-icon">📤</div>
            <div class="upload-text">Drag & drop files here, or click to select files</div>
            <div class="file-types">Supports PDF, PNG, and JPEG files</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Hide this behind the custom design
        uploaded_files = st.file_uploader(
            "Upload PDF files (and optionally Excel for Project List)",
            type=["pdf", "xlsx", "xls", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        
        # Process button centered
        st.markdown("<div style='text-align: center; margin-top: 20px;'>", unsafe_allow_html=True)
        process_button = st.button("Process Documents", use_container_width=False)
        st.markdown("</div>", unsafe_allow_html=True)
        
        if uploaded_files and process_button:
            if not api_key:
                st.error("Please enter a valid Gemini API key in the sidebar.")
            else:
                with st.spinner("Processing documents... This may take a while."):
                    results = process_and_classify_documents(uploaded_files)
                    if results:
                        st.session_state.classification_results = results
                        
                        # Provide download option
                        json_results = json.dumps(results, indent=2)
                        st.download_button(
                            label="Download Results as JSON",
                            data=json_results,
                            file_name="document_classification_results.json",
                            mime="application/json"
                        )
                        
                        # Show missing requirements
                        if "missing_requirements" in results and results["missing_requirements"]:
                            st.markdown("<h3>Missing Requirements</h3>", unsafe_allow_html=True)
                            missing_html = "<ul>"
                            for item in results["missing_requirements"]:
                                missing_html += f"<li>{item}</li>"
                            missing_html += "</ul>"
                            st.markdown(missing_html, unsafe_allow_html=True)
                            
                        # Show raw JSON in expander
                        with st.expander("View Raw JSON Response"):
                            st.json(results)
    
    with col1:
        st.markdown("<h2 class='sub-header'>Required Documents</h2>", unsafe_allow_html=True)
        
        # Display required documents with status and importance tags
        for doc in doc_requirements:
            tag_class = f"tag-{doc['importance']}"
            
            # Check if we have results for this document type
            doc_results = None
            if st.session_state.classification_results and "classified_documents" in st.session_state.classification_results:
                for classified_doc in st.session_state.classification_results["classified_documents"]:
                    if classified_doc["document_type"] == doc["type"]:
                        doc_results = classified_doc
                        break
            
            # Create card HTML
            card_html = f"""
            <div class="doc-card">
                <div class="doc-title">
                    {doc['name']} <span class="{tag_class}">{doc['importance']}</span>
                </div>
            """
            
            # Add status based on results
            if doc_results:
                status_class = doc_results["status"].lower() if doc_results["status"] in ["Positive", "Likely", "Possible"] else "uncertain"
                card_html += f'<div class="status">Found in file: <span class="{status_class}">{doc_results["original_filename"]}</span></div>'
                
                # Add metadata if available
                if "metadata" in doc_results and doc_results["metadata"]:
                    card_html += '<div class="metadata-container"><div class="metadata-title">Document Details</div><ul>'
                    for key, value in doc_results["metadata"].items():
                        if value:  # Only display if value exists
                            if isinstance(value, list):
                                value_str = ", ".join(str(item) for item in value)
                                card_html += f'<li class="metadata-item"><strong>{key.replace("_", " ").title()}:</strong> {value_str}</li>'
                            else:
                                card_html += f'<li class="metadata-item"><strong>{key.replace("_", " ").title()}:</strong> {value}</li>'
                    card_html += '</ul></div>'
            else:
                card_html += '<div class="status">Waiting for upload</div>'
            
            card_html += "</div>"
            st.markdown(card_html, unsafe_allow_html=True)

def process_and_classify_documents(uploaded_files) -> Optional[Dict[str, Any]]:
    """Process files and send them to Gemini API for classification."""
    try:
        model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
        
        # Create parts list with the prompt text as the first item
        parts = [
            {"text": construct_prompt_text()}
        ]
        
        # Process Excel files and add their text content
        excel_text = ""
        pdf_filenames = []
        
        for uploaded_file in uploaded_files:
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            
            if file_extension in ['.xlsx', '.xls']:
                try:
                    # Process Excel
                    df = pd.read_excel(uploaded_file)
                    excel_content = df.to_string(index=False)
                    
                    excel_text += f"\n===== START OF DOCUMENT: [{uploaded_file.name}] =====\n"
                    excel_text += excel_content
                    excel_text += f"\n===== END OF DOCUMENT: [{uploaded_file.name}] =====\n"
                    
                except Exception as e:
                    st.error(f"Error processing Excel file {uploaded_file.name}: {str(e)}")
            elif file_extension in ['.pdf', '.png', '.jpg', '.jpeg']:
                # Save filename
                pdf_filenames.append(uploaded_file.name)
                # Add file as binary data
                file_bytes = uploaded_file.getvalue()
                mime_type = {
                    '.pdf': 'application/pdf',
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg'
                }.get(file_extension, 'application/pdf')
                
                parts.append({
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64.b64encode(file_bytes).decode('utf-8')
                    }
                })
        
        # Add all Excel content text after the prompt
        if excel_text:
            parts.append({"text": excel_text})
        
        # If there are files, add context about filenames to help Gemini match them
        if pdf_filenames:
            pdf_context = "\n\nFiles being processed (in order):\n"
            for i, name in enumerate(pdf_filenames):
                pdf_context += f"{i+1}. {name}\n"
            parts.append({"text": pdf_context})
        
        # Create content object
        content = {"parts": parts}
        
        # Generate response from Gemini with extended timeout
        response = model.generate_content(
            contents=content,
            generation_config={"temperature": 0.5},
            request_options={"timeout": 1000}  # 1000 seconds timeout
        )
        
        # Parse the JSON response
        return extract_json_from_response(response.text)
    
    except Exception as e:
        st.error(f"Error calling Gemini API: {str(e)}")
        st.error(f"Details: {str(e.__class__.__name__)}")
        return None

def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse JSON from the API response text."""
    try:
        # Try to parse the entire response as JSON
        return json.loads(response_text)
    except json.JSONDecodeError:
        # If that fails, try to find JSON within the response
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                st.error("Could not extract valid JSON from API response.")
                st.text(response_text)
                return None
        except Exception as e:
            st.error(f"Error extracting JSON from response: {str(e)}")
            st.text(response_text)
            return None

def construct_prompt_text() -> str:
    """Construct the prompt text for Gemini API."""
    return """You are an AI assistant specialized in classifying business documents and extracting key metadata based on document content. Your task is to analyze the provided PDF files and Excel data to generate a structured JSON output summarizing your findings for each file.

**IMPORTANT INSTRUCTIONS:**
- For each PDF document, only analyze the first 30 pages, even if the document is much longer (some may be 1000+ pages).
- For image-based or scanned PDFs, use your advanced vision capabilities to extract and analyze the text and layout.
- Conduct a thorough analysis of these pages to understand the document's purpose, type, and key metadata.

**CORE TASK:** For each document provided:
1. **Classify:** Determine the most likely document type from the predefined list below. Look for identifying headers, layouts, official stamps, letterheads, and content patterns.
2. **Extract Metadata:** Carefully analyze the content to identify and extract all relevant metadata associated with the document type (Company Name, Dates/Years, Bank Name, etc.).
3. **Assign Status:** Assign a confidence level (Status) to your classification based on the strength of evidence found.
4. **Summarize Missing:** After classifying all provided documents, identify which *required* document types/years appear to be missing based on the predefined requirements list.

**DOCUMENT ANALYSIS APPROACH:**
- For Bank Statements: Look for transaction tables, account information sections, bank logos, and date ranges.
- For Financial Statements: Examine for accounting tables, balance sheets, income statements, cash flow statements, and auditor notes.
- For GOSI/VAT/Saudization documents: Identify official headers, registration numbers, validity dates, and government entity logos/watermarks.
- For Contracts: Look for signature sections, party information, terms and conditions, and project specifications.

**PREDEFINED DOCUMENT TYPES & REQUIRED METADATA:**

*   **Bank Statement:** Keywords: Bank Name, Account Number, Statement Period, Transactions, Balances. Metadata: `Bank Name`, `Account Holder Name`, `Statement Period/Year(s)`.
*   **Financial Statement:** Keywords: Financial Statements, Balance Sheet, Income Statement, Cash Flow, Auditor's Report, Dates (As at...). Metadata: `Company Name`, `Financial Year(s)`, `Audit Status` (if mentioned).
*   **Project List:** Keywords: Project Name, Client, Contract Value, Status columns (often Excel/table format). Metadata: `Document Type Confirmed` (as Project List).
*   **GOSI:** Keywords: GOSI, General Organization for Social Insurance, Certificate Number, Validity Date. Metadata: `Company Name`, `Validity Period/Date`.
*   **VAT Statement:** Keywords: VAT Return Form (نموذج اﻹقرار اﻟﴬﻳﺒﻲ), Tax Period (اﻟﻔﱰة اﻟﴬﻳﺒﻴﺔ), Tax Account Number (رﻗﻢ اﻟﺤﺴﺎب اﻟﴬﻳﺒﻲ), ZATCA, Sales, Purchases. Metadata: `Company Name`, `Tax Period(s)`.
*   **Saudization Certificate:** Keywords: Certificate of Saudization (شهادة التوطين), MHRSD, Nitaqat Level, Expiry Date. Metadata: `Company Name`, `Validity Period/Expiry Date`.
*   **Project Contract:** Keywords: Contract/Agreement (عقد/اتفاقية), Parties (Contractor, Owner), Contract Value, Payment Terms. Metadata: `Parties Involved`, `Contract Date`, `Project Scope (brief)`.
*   **CR (Commercial Registration):** Keywords: Commercial Registration (السجل التجاري), Ministry of Commerce, CR Number (رقم السجل), Expiry Date. Metadata: `Company Name`, `CR Number`, `Expiry Date`.
*   **Company Profile:** Keywords: About Us, Mission, Vision, Services, Org Chart (often presentation format). Metadata: `Company Name`.
*   **Other:** Any document not fitting the above categories. Metadata: `Brief Description` (if possible).

**REQUIRED DOCUMENT CHECKLIST (for Missing Summary):**
*   Bank Statements: Covering Full Year 2024 AND Jan-Apr 2025.
*   Financial Statements: For any TWO years from 2022, 2023, 2024.
*   Project List: Yes.
*   GOSI: Yes (current).
*   VAT Statement: Yes (recent periods).
*   Saudization Certificate: Yes (current).
*   Project Contract(s): Yes (significant ones implied).
*   CR: Yes (current).
*   Company Profile: Yes.

**CONFIDENCE/STATUS LEVELS:**
*   **Positive:** High certainty, multiple key identifiers present.
*   **Likely:** Good certainty, several identifiers present, minor ambiguity possible.
*   **Possible:** Low-moderate certainty, some matching features, but limited evidence.
*   **Uncertain/Other:** Cannot reasonably classify into a required category.

**INPUT FORMAT:**
You will receive:
1. PDF files directly through the API
2. Excel file contents in text format with markers:
```
===== START OF DOCUMENT: [Original_Filename.xlsx] =====
[Content of Excel file as text]
===== END OF DOCUMENT: [Original_Filename.xlsx] =====
```
3. A list of PDF filenames in order that they appear in the input

**OUTPUT FORMAT (Strict JSON):**
Respond ONLY with a single JSON object with the following structure:

```json
{
  "classified_documents": [
    {
      "original_filename": "...",
      "document_type": "Bank Statement | Financial Statement | Project List | GOSI | VAT Statement | Saudization Certificate | Project Contract | CR | Company Profile | Other",
      "status": "Positive | Likely | Possible | Uncertain/Other",
      "metadata": {
        "company_name": "...", // If found
        "bank_name": "...", // If Bank Statement
        "statement_period_years": ["...", "..."], // If Bank Statement/VAT
        "financial_years": ["...", "..."], // If Financial Statement
        "audit_status": "...", // If Financial Statement
        "validity_expiry_date": "...", // If GOSI/Saudization/CR
        "tax_periods": ["...", "..."], // If VAT
        "cr_number": "...", // If CR
        "contract_parties": ["...", "..."], // If Contract
        "other_info": "..." // Any other key identifiable info or description for 'Other'
      }
    }
    // ... more documents
  ],
  "missing_requirements": [
    "Bank Statement (Year 2024)",
    "Bank Statement (Jan-Apr 2025)",
    "Financial Statement (Year needed)", // Specify which year combo is missing
    "Project List",
    "GOSI (Current)",
    "VAT Statement (Recent)",
    "Saudization Certificate (Current)",
    "Project Contract(s)",
    "CR (Current)",
    "Company Profile"
    // List only the requirements NOT met by the classified documents
  ]
}
```

Instructions:
- Analyze the content of all provided PDF files (strictly only first 30 pages each) and Excel files.
- For PDFs, use your advanced document understanding capabilities to extract text and recognize content, even from image-based/scanned PDFs.
- Fill the classified_documents list, one entry per input file.
- Be precise with extracted metadata (e.g., list all years found in financial statements). Always include all detected metadata fields that are relevant to the document type.
- If metadata isn't found, omit the key rather than including it with an empty value.
- Use the status field honestly based on your confidence.
- Carefully compare the identified documents against the REQUIRED DOCUMENT CHECKLIST to populate the missing_requirements list accurately. Only list items that are definitively missing based on your classifications and the year requirements.

Here are the documents to analyze:
"""

if __name__ == "__main__":
    main() 
    