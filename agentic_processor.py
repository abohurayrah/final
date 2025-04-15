import streamlit as st
import os
import json
import base64
import time
import datetime
from typing import List, Dict, Any, Optional
import google.generativeai as genai
import pandas as pd
import shutil

# Set page config - this must be the first Streamlit command
st.set_page_config(
    page_title="Agentic Document Processing System",
    page_icon="🤖",
    layout="wide"
)

# Import magic_box functions after setting page config
from magic_box import construct_prompt_text, extract_json_from_response
# Import our specialized prompts
from prompts import (
    get_prompt_for_document_type,
    DECISION_DYNAMO_PROMPT,
    FINAL_REPORT_PROMPT
)

# Create directory for saving results
def create_results_directory():
    """Creates timestamped directory for saving analysis results"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"results_{timestamp}"
    os.makedirs(results_dir, exist_ok=True)
    return results_dir

# Group documents by their classified type
def group_documents_by_type(classification_results, uploaded_files):
    """Groups uploaded files based on their classification results"""
    document_groups = {}
    
    if not classification_results or "classified_documents" not in classification_results:
        return document_groups
    
    # Create a map of filename to file object
    filename_to_file = {f.name: f for f in uploaded_files}
    
    # Group files by their document type
    for doc in classification_results["classified_documents"]:
        doc_type = doc["document_type"]
        filename = doc["original_filename"]
        
        if filename in filename_to_file:
            if doc_type not in document_groups:
                document_groups[doc_type] = []
            
            document_groups[doc_type].append({
                "file": filename_to_file[filename],
                "metadata": doc.get("metadata", {}),
                "classification_info": doc
            })
    
    return document_groups

# Process documents by type using specialized prompts
def process_documents_by_type(doc_type, files_group, results_dir, api_key):
    """Process documents using a specialized prompt based on document type"""
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
        
        # Get the specialized prompt for this document type
        specialized_prompt = get_prompt_for_document_type(doc_type)
        
        # Prepare parts for API call
        parts = [{"text": specialized_prompt}]
        
        # Add each file to the parts
        for file_info in files_group:
            file = file_info["file"]
            file_extension = os.path.splitext(file.name)[1].lower()
            file_bytes = file.getvalue()
            
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
        
        # Add a summary of the files being analyzed
        files_summary = f"\n\nAnalyzing {len(files_group)} {doc_type} documents:\n"
        for i, file_info in enumerate(files_group):
            files_summary += f"{i+1}. {file_info['file'].name}\n"
        parts.append({"text": files_summary})
        
        # Generate response from Gemini
        response = model.generate_content(
            contents={"parts": parts},
            generation_config={"temperature": 0.2},
            request_options={"timeout": 1000}  # 1000 seconds timeout
        )
        
        # Extract and parse JSON response
        analysis_results = extract_json_from_response(response.text)
        
        # Save results to file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_type_slug = doc_type.lower().replace(' ', '_').replace('/', '_')
        results_file = os.path.join(results_dir, f"{doc_type_slug}_analysis_{timestamp}.json")
        with open(results_file, 'w') as f:
            json.dump(analysis_results, f, indent=2)
        
        return analysis_results
    
    except Exception as e:
        st.error(f"Error processing {doc_type}: {str(e)}")
        return {"error": str(e)}

# Generate final recommendation with Decision Dynamo
def generate_decision_dynamo(all_analysis_results, results_dir, api_key):
    """Generate final recommendation using Decision Dynamo"""
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
        
        # Prepare input for Decision Dynamo
        dynamo_input = {
            "bankAnalysisOutput": all_analysis_results.get("Bank Statement", {}),
            "financialAnalysisOutput": all_analysis_results.get("Financial Statement", {}),
            "vatAnalysisOutput": all_analysis_results.get("VAT Statement", {}),
            "contractAnalysisOutput": all_analysis_results.get("Project Contract", {}),
            "otherDocumentsOutput": {
                doc_type: results for doc_type, results in all_analysis_results.items() 
                if doc_type not in ["Bank Statement", "Financial Statement", "VAT Statement", "Project Contract"]
            }
        }
        
        # Extract Decision Dynamo prompt and model rules
        try:
            with open("6_decision_dynamo_prompt_DONE.md", "r") as f:
                dynamo_rules = f.read()
                
            # Combine the rules with our structured prompt
            combined_prompt = DECISION_DYNAMO_PROMPT + "\n\n# Decision Dynamo Scoring Model Rules\n\n" + dynamo_rules
        except Exception as e:
            st.warning(f"Could not load Decision Dynamo rules file: {str(e)}")
            combined_prompt = DECISION_DYNAMO_PROMPT
        
        # Generate response from Gemini
        response = model.generate_content(
            contents=[{
                "text": combined_prompt + "\n\nInput data:\n" + json.dumps(dynamo_input)
            }],
            generation_config={"temperature": 0.2},
            request_options={"timeout": 1000}  # 1000 seconds timeout
        )
        
        # Extract and parse JSON response
        decision_results = extract_json_from_response(response.text)
        
        # Save results to file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(results_dir, f"decision_dynamo_{timestamp}.json")
        with open(results_file, 'w') as f:
            json.dump(decision_results, f, indent=2)
        
        return decision_results
    
    except Exception as e:
        st.error(f"Error generating Decision Dynamo: {str(e)}")
        return {"error": str(e)}

# Generate final report
def generate_final_report(all_analysis_results, decision_dynamo_results, results_dir, api_key):
    """Generate final report based on all analyses"""
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
        
        # Prepare input for final report
        report_input = {
            "bankAnalysisOutput": all_analysis_results.get("Bank Statement", {}),
            "financialAnalysisOutput": all_analysis_results.get("Financial Statement", {}),
            "vatAnalysisOutput": all_analysis_results.get("VAT Statement", {}),
            "contractAnalysisOutput": all_analysis_results.get("Project Contract", {}),
            "otherDocumentsOutput": {
                doc_type: results for doc_type, results in all_analysis_results.items() 
                if doc_type not in ["Bank Statement", "Financial Statement", "VAT Statement", "Project Contract"]
            },
            "decisionDynamoOutput": decision_dynamo_results
        }
        
        # Generate response from Gemini
        response = model.generate_content(
            contents=[{
                "text": FINAL_REPORT_PROMPT + "\n\nInput data:\n" + json.dumps(report_input)
            }],
            generation_config={"temperature": 0.2},
            request_options={"timeout": 1000}  # 1000 seconds timeout
        )
        
        # Extract and parse JSON response
        final_report = extract_json_from_response(response.text)
        
        # Save results to file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(results_dir, f"final_report_{timestamp}.json")
        with open(results_file, 'w') as f:
            json.dump(final_report, f, indent=2)
        
        return final_report
    
    except Exception as e:
        st.error(f"Error generating final report: {str(e)}")
        return {"error": str(e)}

# Load results from an existing directory
def load_results_from_directory(directory_path):
    """Load analysis results from an existing directory"""
    try:
        if not os.path.exists(directory_path):
            return False, f"Directory does not exist: {directory_path}"
        
        # Set the results directory in session state
        st.session_state.results_dir = directory_path
        
        # Find classification results file
        classification_files = [f for f in os.listdir(directory_path) if f.startswith("classification_") and f.endswith(".json")]
        if classification_files:
            # Load the most recent classification file (sort by timestamp)
            classification_file = sorted(classification_files)[-1]
            with open(os.path.join(directory_path, classification_file), 'r') as f:
                st.session_state.classification_results = json.load(f)
                st.session_state.current_step = 2  # Set step to classification complete
        
        # Find analysis result files for different document types
        analysis_files = [f for f in os.listdir(directory_path) if f.endswith(".json") and "analysis" in f]
        if analysis_files:
            all_analysis_results = {}
            
            # Process each analysis file
            for file in analysis_files:
                with open(os.path.join(directory_path, file), 'r') as f:
                    analysis_result = json.load(f)
                
                # Extract document type from filename
                file_parts = file.split("_analysis_")[0]
                doc_type_map = {
                    "bank_statement": "Bank Statement",
                    "financial_statement": "Financial Statement",
                    "vat_statement": "VAT Statement",
                    "project_contract": "Project Contract",
                    "project_list": "Project List",
                    "commercial_registration": "CR",
                    "gosi": "GOSI Certificate",
                    "saudization": "Saudization Certificate",
                    "company_profile": "Company Profile"
                }
                
                # Find the matching document type
                doc_type = None
                for key, value in doc_type_map.items():
                    if key in file_parts:
                        doc_type = value
                        break
                
                if doc_type:
                    all_analysis_results[doc_type] = analysis_result
            
            # Store analysis results in session state if any were found
            if all_analysis_results:
                st.session_state.analysis_results = all_analysis_results
                st.session_state.current_step = 3  # Set step to analysis complete
        
        # Find decision dynamo results
        dynamo_files = [f for f in os.listdir(directory_path) if f.startswith("decision_dynamo_") and f.endswith(".json")]
        if dynamo_files:
            # Load the most recent dynamo file
            dynamo_file = sorted(dynamo_files)[-1]
            with open(os.path.join(directory_path, dynamo_file), 'r') as f:
                decision_results = json.load(f)
                st.session_state.decision_results = decision_results
                st.session_state.decision_dynamo_output = decision_results
                st.session_state.current_step = 4  # Set step to decision dynamo complete
        
        # Find final report
        report_files = [f for f in os.listdir(directory_path) if f.startswith("final_report_") and f.endswith(".json")]
        if report_files:
            # Load the most recent report file
            report_file = sorted(report_files)[-1]
            with open(os.path.join(directory_path, report_file), 'r') as f:
                final_report = json.load(f)
                st.session_state.final_report = final_report
                st.session_state.current_step = 5  # Set step to final report complete
        
        return True, f"Successfully loaded results from {directory_path}"
    
    except Exception as e:
        return False, f"Error loading results: {str(e)}"

def main():
    st.markdown("<h1 style='text-align: center;'>Agentic Document Processing System</h1>", unsafe_allow_html=True)
    
    # Initialize session state
    if 'classification_results' not in st.session_state:
        st.session_state.classification_results = None
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = {}
    if 'decision_results' not in st.session_state:
        st.session_state.decision_results = None
    if 'final_report' not in st.session_state:
        st.session_state.final_report = None
    if 'results_dir' not in st.session_state:
        st.session_state.results_dir = None
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1  # Track the current step in the flow
    if 'processed_documents' not in st.session_state:
        st.session_state.processed_documents = []
    if 'decision_dynamo_output' not in st.session_state:
        st.session_state.decision_dynamo_output = None
    
    # Sidebar for API key
    with st.sidebar:
        st.markdown("### Configuration")
        api_key = st.text_input("Enter Gemini API Key", type="password", help="Enter your Google Generative AI API key")
        
        # Try to get API key from .env file if not provided
        if not api_key:
            try:
                from dotenv import load_dotenv
                load_dotenv()
                api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
                if api_key:
                    st.success("API key loaded from .env file")
            except Exception as e:
                st.warning("Could not load API key from .env file. Please enter manually.")
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                st.success("API key configured successfully!")
            except Exception as e:
                st.error(f"Error configuring API: {str(e)}")
        
        # Show process flow in sidebar
        st.markdown("---")
        st.markdown("### Process Flow")
        
        # Highlight the current step
        step1_color = "green" if st.session_state.current_step >= 1 else "gray"
        step2_color = "green" if st.session_state.current_step >= 2 else "gray"
        step3_color = "green" if st.session_state.current_step >= 3 else "gray"
        step4_color = "green" if st.session_state.current_step >= 4 else "gray"
        step5_color = "green" if st.session_state.current_step >= 5 else "gray"
        
        st.markdown(
            f"""
            <div style="margin-bottom: 10px;">
                <span style="color: {step1_color}; font-weight: {'bold' if st.session_state.current_step == 1 else 'normal'};">1. File Upload</span>
                <span style="color: gray;"> → </span>
                <span style="color: {step2_color}; font-weight: {'bold' if st.session_state.current_step == 2 else 'normal'};">2. Classification</span>
                <span style="color: gray;"> → </span>
                <span style="color: {step3_color}; font-weight: {'bold' if st.session_state.current_step == 3 else 'normal'};">3. Analysis</span>
                <span style="color: gray;"> → </span>
                <span style="color: {step4_color}; font-weight: {'bold' if st.session_state.current_step == 4 else 'normal'};">4. Decision Dynamo</span>
                <span style="color: gray;"> → </span>
                <span style="color: {step5_color}; font-weight: {'bold' if st.session_state.current_step == 5 else 'normal'};">5. Final Report</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("---")
        st.markdown("""
        ### Supported Document Types
        - Bank Statement
        - Financial Statement
        - VAT Statement/Return
        - Project Contract
        - Project List
        - Commercial Registration (CR)
        - GOSI Certificate
        - Saudization Certificate
        - Company Profile
        """)
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["Document Upload & Classification", "Analysis Results", "Final Report"])
    
    with tab1:
        st.markdown("### Upload Documents")
        
        # Option to load from existing results directory
        st.markdown("""
        <div style="padding: 10px; margin-bottom: 20px; background-color: #f0f8ff; border-left: 5px solid #1e90ff; border-radius: 5px;">
            <h4 style="margin: 0; color: #1e90ff;">Load Previous Analysis</h4>
            <p style="margin: 5px 0 0 0;">Continue from a previous analysis by selecting the results directory</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Text input for results directory path
        prev_dir = st.text_input("Enter the path to a previous results directory (e.g., results_20250415_174208)", 
                                help="Enter the path to the directory containing previous analysis results")
        
        load_button = st.button("Load Previous Analysis", help="Load results from the specified directory")
        
        if prev_dir and load_button:
            success, message = load_results_from_directory(prev_dir)
            if success:
                st.success(message)
                # Display summary of what was loaded
                if st.session_state.classification_results:
                    num_docs = len(st.session_state.classification_results.get("classified_documents", []))
                    st.info(f"Loaded classification results for {num_docs} documents")
                
                if st.session_state.analysis_results:
                    st.info(f"Loaded analysis results for {len(st.session_state.analysis_results)} document types")
                
                if st.session_state.decision_results:
                    st.info("Loaded Decision Dynamo results")
                
                if st.session_state.final_report:
                    st.info("Loaded Final Report")
            else:
                st.error(message)
        
        st.markdown("<hr>", unsafe_allow_html=True)
        
        # Step 1: File Upload
        st.markdown("""
        <div style="padding: 10px; margin-bottom: 20px; background-color: #f0f8ff; border-left: 5px solid #1e90ff; border-radius: 5px;">
            <h4 style="margin: 0; color: #1e90ff;">Step 1: Upload Files</h4>
            <p style="margin: 5px 0 0 0;">Upload financial documents for analysis (PDF, Excel, Images)</p>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "Upload files (PDF, Excel, Images)",
            type=["pdf", "xlsx", "xls", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            help="Upload your financial documents for analysis"
        )
        
        if uploaded_files:
            st.session_state.current_step = 1
        
        # Step 2: Classification
        st.markdown("""
        <div style="padding: 10px; margin: 20px 0; background-color: #f0f8ff; border-left: 5px solid #1e90ff; border-radius: 5px;">
            <h4 style="margin: 0; color: #1e90ff;">Step 2: Classify Documents</h4>
            <p style="margin: 5px 0 0 0;">Automatically identify document types</p>
        </div>
        """, unsafe_allow_html=True)
        
        classify_button = st.button("Classify Documents", type="primary", 
                               help="First classify the documents by type")
        
        if uploaded_files and classify_button:
            if not api_key:
                st.error("Please enter a valid Gemini API key in the sidebar or set it in the .env file.")
            else:
                with st.spinner("Classifying documents... This may take a while."):
                    # Import the function from magic_box
                    from magic_box import process_and_classify_documents
                    
                    # Create results directory
                    results_dir = create_results_directory()
                    st.session_state.results_dir = results_dir
                    
                    # Classify documents
                    results = process_and_classify_documents(uploaded_files)
                    if results:
                        st.session_state.classification_results = results
                        st.session_state.current_step = 2  # Update current step
                        
                        # Save classification results
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        classification_file = os.path.join(results_dir, f"classification_{timestamp}.json")
                        with open(classification_file, 'w') as f:
                            json.dump(results, f, indent=2)
                        
                        st.success("Documents classified successfully!")
                        
                        # Display classification results in an expander
                        with st.expander("Classification Results"):
                            st.json(results)
        
        # Steps 3-5: Analysis, Decision Dynamo, and Final Report
        st.markdown("""
        <div style="padding: 10px; margin: 20px 0; background-color: #f0f8ff; border-left: 5px solid #1e90ff; border-radius: 5px;">
            <h4 style="margin: 0; color: #1e90ff;">Steps 3-5: Process Documents</h4>
            <p style="margin: 5px 0 0 0;">Analyze documents, generate Decision Dynamo scoring, and create final report</p>
        </div>
        """, unsafe_allow_html=True)
        
        process_button = st.button("Process All Documents", 
                              disabled=not st.session_state.classification_results,
                              help="Process the classified documents with specialized analysis")
        
        if st.session_state.classification_results and process_button:
            if not api_key:
                st.error("Please enter a valid Gemini API key in the sidebar or set it in the .env file.")
            else:
                with st.spinner("Processing documents by type... This may take a while."):
                    # Group documents by type
                    document_groups = group_documents_by_type(st.session_state.classification_results, uploaded_files)
                    
                    # Create a status container for progress updates
                    status_container = st.empty()
                    
                    # Step 3: Process each document group
                    status_container.info("Step 3: Analyzing documents by type...")
                    st.session_state.current_step = 3  # Update current step
                    
                    all_analysis_results = {}
                    for doc_type, files_group in document_groups.items():
                        status_container.info(f"Processing {doc_type} documents... ({len(files_group)} files)")
                        analysis_results = process_documents_by_type(
                            doc_type, 
                            files_group, 
                            st.session_state.results_dir, 
                            api_key
                        )
                        all_analysis_results[doc_type] = analysis_results
                    
                    # Step 4: Generate Decision Dynamo results
                    status_container.info("Step 4: Generating Decision Dynamo recommendation...")
                    st.session_state.current_step = 4  # Update current step
                    
                    decision_results = generate_decision_dynamo(
                        all_analysis_results, 
                        st.session_state.results_dir, 
                        api_key
                    )
                    
                    # Step 5: Generate Final Report
                    status_container.info("Step 5: Generating Final Report...")
                    st.session_state.current_step = 5  # Update current step
                    
                    final_report = generate_final_report(
                        all_analysis_results, 
                        decision_results, 
                        st.session_state.results_dir, 
                        api_key
                    )
                    
                    # Save to session state
                    st.session_state.analysis_results = all_analysis_results
                    st.session_state.decision_results = decision_results
                    st.session_state.final_report = final_report
                    
                    status_container.success(f"All documents processed successfully! Results saved to {st.session_state.results_dir}")
                    
                    # Switch to the results tab after processing
                    st.balloons()
                    js = """
                    <script>
                        var tabs = window.parent.document.querySelectorAll('.stTabs button[data-baseweb="tab"]');
                        if (tabs.length > 0) {
                            tabs[1].click();  // Click on the second tab (Analysis Results)
                        }
                    </script>
                    """
                    st.markdown(js, unsafe_allow_html=True)
    
    with tab2:
        st.markdown("## Analysis Results")
        
        # Add button to continue analysis if we have analysis results but no decision results
        if st.session_state.analysis_results and not (st.session_state.decision_results and st.session_state.final_report):
            st.info("Analysis results loaded. You can continue to generate Decision Dynamo and Final Report.")
            
            continue_button = st.button("Generate Decision Dynamo & Final Report", 
                                      type="primary",
                                      help="Generate Decision Dynamo and Final Report from loaded analysis results")
            
            if continue_button:
                if not api_key:
                    st.error("Please enter a valid Gemini API key in the sidebar or set it in the .env file.")
                else:
                    with st.spinner("Generating Decision Dynamo recommendation and Final Report... This may take a while."):
                        # Create a status container for progress updates
                        status_container = st.empty()
                        
                        # Step 4: Generate Decision Dynamo results
                        status_container.info("Step 4: Generating Decision Dynamo recommendation...")
                        st.session_state.current_step = 4  # Update current step
                        
                        decision_results = generate_decision_dynamo(
                            st.session_state.analysis_results,
                            st.session_state.results_dir, 
                            api_key
                        )
                        
                        # Step 5: Generate Final Report
                        status_container.info("Step 5: Generating Final Report...")
                        st.session_state.current_step = 5  # Update current step
                        
                        final_report = generate_final_report(
                            st.session_state.analysis_results, 
                            decision_results, 
                            st.session_state.results_dir, 
                            api_key
                        )
                        
                        # Save to session state
                        st.session_state.decision_results = decision_results
                        st.session_state.final_report = final_report
                        st.session_state.decision_dynamo_output = decision_results
                        
                        status_container.success("Decision Dynamo and Final Report generated successfully!")
                        st.balloons()
                        
                        # Reload the page to display the results
                        st.experimental_rerun()
        
        # Create a two-column layout for navigation
        result_cols = st.columns([1, 4])
        
        with result_cols[0]:
            # Navigation sidebar for results
            st.markdown("### Navigation")
            result_tabs = ["Document Analysis", "Decision Dynamo"]
            selected_result_tab = st.radio("Select View", result_tabs, label_visibility="collapsed")
        
        with result_cols[1]:
            if selected_result_tab == "Document Analysis":
                # Display the document analysis results
                if st.session_state.processed_documents:
                    document_tabs = []
                    for doc in st.session_state.processed_documents:
                        doc_name = doc['document_name']
                        doc_type = doc.get('document_type', 'Unknown')
                        document_tabs.append(f"{doc_type}: {doc_name}")
                    
                    if document_tabs:
                        selected_doc_tab = st.selectbox("Select Document", document_tabs)
                        selected_index = document_tabs.index(selected_doc_tab)
                        
                        if 0 <= selected_index < len(st.session_state.processed_documents):
                            doc_data = st.session_state.processed_documents[selected_index]
                            
                            # Display document type and name
                            st.markdown(f"#### {doc_data.get('document_type', 'Unknown')}: {doc_data['document_name']}")
                            
                            # Display analysis results
                            analysis = doc_data.get('analysis', {})
                            if analysis:
                                # Create expandable sections for different parts of the analysis
                                with st.expander("Key Information", expanded=True):
                                    key_info = analysis.get('key_information', {})
                                    for key, value in key_info.items():
                                        st.markdown(f"**{key}:** {value}")
                                
                                with st.expander("Analysis Summary", expanded=True):
                                    summary = analysis.get('summary', '')
                                    st.markdown(summary)
                                
                                with st.expander("Detailed Analysis"):
                                    detailed = analysis.get('detailed_analysis', {})
                                    for section, content in detailed.items():
                                        st.markdown(f"**{section}**")
                                        st.markdown(content)
                                
                                # Display raw JSON
                                with st.expander("View Raw JSON"):
                                    st.json(analysis)
                            else:
                                st.info("No analysis data available for this document.")
                    else:
                        st.info("No processed documents available.")
                else:
                    st.info("No documents have been processed yet. Please process documents first.")
            
            elif selected_result_tab == "Decision Dynamo":
                # Display the Decision Dynamo results if available
                if st.session_state.decision_dynamo_output:
                    try:
                        dynamo_data = st.session_state.decision_dynamo_output
                        
                        # Check if the main key exists, otherwise display error
                        if "decision_dynamo_output" not in dynamo_data:
                            st.error("Decision Dynamo output format is incorrect. Missing 'decision_dynamo_output' key.")
                            st.json(dynamo_data)
                        else:
                            # Access the actual output data
                            dynamo_output = dynamo_data["decision_dynamo_output"]

                            # Company and loan request information
                            request_summary = dynamo_output.get("request_summary", {})
                            company_summary = dynamo_output.get("company_summary", {})
                            company_name = company_summary.get('company_name', 'Company')
                            loan_amount = request_summary.get('loan_amount_sar', 0)
                            loan_term = request_summary.get('loan_term_months', 0)
                            loan_purpose = request_summary.get('loan_purpose', 'Not specified')
                            
                            # Display header
                            st.markdown(f"## Decision Dynamo: {company_name}")
                            
                            # Loan request info
                            st.markdown("### Loan Request")
                            loan_cols = st.columns(3)
                            loan_cols[0].metric("Amount", f"SAR {loan_amount:,}")
                            loan_cols[1].metric("Term", f"{loan_term} months")
                            loan_cols[2].metric("Purpose", loan_purpose)
                            
                            # Decision recommendation
                            recommendation = dynamo_output.get('recommendation', {})
                            if recommendation:
                                decision_status = recommendation.get('decision', 'Pending')
                                confidence = recommendation.get('confidence_level', 'Medium')
                                
                                # Set color based on decision
                                decision_color = {
                                    'Accept': 'green',
                                    'Reject': 'red',
                                    'Review': 'orange',
                                    'Pending': 'blue'
                                }.get(decision_status, 'blue')
                                
                                # Display decision banner
                                st.markdown(
                                    f"""
                                    <div style="padding: 20px; margin: 20px 0; background-color: {decision_color}15; 
                                            border-left: 8px solid {decision_color}; border-radius: 4px;">
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <h2 style="margin: 0; color: {decision_color};">Decision: {decision_status}</h2>
                                            <span style="font-weight: bold;">Confidence: {confidence}</span>
                                        </div>
                                    </div>
                                    """, 
                                    unsafe_allow_html=True
                                )
                            
                            # Scoring metrics
                            scores = dynamo_output.get('scoring', {})
                            if scores:
                                st.markdown("### Scoring Metrics")
                                
                                # Function to display score with color-coded bar
                                def display_score(label, score, max_score=100):
                                    # Calculate percentage and determine color
                                    percentage = min(100, max(0, (score / max_score) * 100)) if score is not None else 0
                                    score_display = score if score is not None else 'N/A'
                                    
                                    if score is None:
                                        color = "gray"
                                        assessment = "Not Available"
                                    elif percentage >= 70:
                                        color = "green"
                                        assessment = "Good"
                                    elif percentage >= 50:
                                        color = "orange"
                                        assessment = "Moderate"
                                    else:
                                        color = "red"
                                        assessment = "Poor"
                                    
                                    return f"""
                                    <div style="margin-bottom: 15px;">
                                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                            <span style="font-weight: bold;">{label}</span>
                                            <div>
                                                <span style="font-weight: bold; color: {color};">{score_display}/{max_score}</span>
                                                <span style="margin-left: 10px; color: {color}; font-style: italic;">{assessment}</span>
                                            </div>
                                        </div>
                                        <div style="background-color: #eee; border-radius: 10px; height: 12px;">
                                            <div style="background-color: {color}; width: {percentage}%; height: 12px; border-radius: 10px;"></div>
                                        </div>
                                    </div>
                                    """
                                
                                # Display each score as a horizontal bar
                                score_html = ""
                                
                                metrics = [
                                    ("Financial Health", scores.get('financial_health_score')),
                                    ("Cash Flow", scores.get('cash_flow_score')),
                                    ("Repayment Capacity", scores.get('repayment_capacity_score')),
                                    ("Business Stability", scores.get('business_stability_score')),
                                    ("Compliance", scores.get('compliance_score')),
                                    ("Documentation", scores.get('documentation_completeness_score'))
                                ]
                                
                                for label, score in metrics:
                                    score_html += display_score(label, score)
                                
                                st.markdown(score_html, unsafe_allow_html=True)
                                
                                # Overall score
                                overall_score = scores.get('final_score_adjusted')
                                overall_color = "gray"
                                overall_percentage = 0
                                if overall_score is not None:
                                    overall_percentage = min(100, max(0, overall_score))
                                    overall_color = "green" if overall_percentage >= 70 else "orange" if overall_percentage >= 50 else "red"
                                    overall_score_display = f"{overall_score}/100"
                                else:
                                    overall_score_display = "N/A"

                                st.markdown(
                                    f"""
                                    <div style="text-align: center; margin: 20px 0; padding: 20px; 
                                            background-color: #f0f0f0; border-radius: 10px;">
                                        <h3>Overall Score</h3>
                                        <div style="font-size: 48px; font-weight: bold; color: {overall_color};">{overall_score_display}</div>
                                        <div style="background-color: #ddd; border-radius: 10px; height: 15px; margin-top: 10px;">
                                            <div style="background-color: {overall_color}; width: {overall_percentage}%; height: 15px; border-radius: 10px;"></div>
                                        </div>
                                    </div>
                                    """, 
                                    unsafe_allow_html=True
                                )
                            
                            # Risk assessment
                            risk_assessment = dynamo_output.get('risk_assessment', {})
                            risks = risk_assessment.get('key_risk_factors', [])
                            if risks:
                                st.markdown("### Risk Assessment")
                                
                                for risk in risks:
                                    risk_factor = risk.get('risk_description', '')
                                    severity = risk.get('severity', 'Medium')
                                    mitigation = risk.get('mitigation_suggestion', '')
                                    
                                    # Set color based on severity
                                    severity_color = {
                                        'Low': 'green',
                                        'Medium': 'orange',
                                        'High': 'red',
                                        'Critical': 'darkred'
                                    }.get(severity, 'gray')
                                    
                                    # Display risk factor
                                    st.markdown(
                                        f"""
                                        <div style="margin-bottom: 15px; padding: 15px; border-left: 5px solid {severity_color}; 
                                                background-color: {severity_color}10; border-radius: 4px;">
                                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                                <span style="font-weight: bold;">{risk_factor}</span>
                                                <span style="color: {severity_color}; font-weight: bold; text-transform: uppercase;">{severity}</span>
                                            </div>
                                            {f'<div style="margin-top: 10px;"><strong>Mitigation:</strong> {mitigation}</div>' if mitigation else ''}
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
                            
                            # Repayment analysis
                            repayment = dynamo_output.get('repayment_analysis', {})
                            if repayment:
                                st.markdown("### Repayment Analysis")
                                
                                monthly_payment = repayment.get('monthly_payment_estimate_sar')
                                coverage_ratio = repayment.get('cash_flow_coverage_ratio')
                                probability = repayment.get('repayment_probability', 'Not Calculated') # String value from prompt
                                
                                # Display metrics in columns
                                rep_cols = st.columns(3)
                                
                                # Monthly payment
                                rep_cols[0].metric("Monthly Payment", f"SAR {monthly_payment:,}" if monthly_payment else "N/A")
                                
                                # Coverage ratio with color
                                coverage_color = "gray"
                                coverage_display = "N/A"
                                if coverage_ratio is not None:
                                    coverage_color = "green" if coverage_ratio >= 1.5 else "orange" if coverage_ratio >= 1.0 else "red"
                                    coverage_display = f"{coverage_ratio:.2f}x"
                                    
                                rep_cols[1].markdown(
                                    f"""
                                    <div style="text-align: center;">
                                        <div style="color: #808495; font-size: 0.8em;">Cash Flow Coverage</div>
                                        <div style="color: {coverage_color}; font-weight: bold; font-size: 1.5em;">{coverage_display}</div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                                
                                # Repayment probability with color
                                prob_color = {
                                    'High': 'green',
                                    'Medium': 'orange',
                                    'Low': 'red'
                                }.get(probability, 'gray')
                                rep_cols[2].markdown(
                                    f"""
                                    <div style="text-align: center;">
                                        <div style="color: #808495; font-size: 0.8em;">Repayment Probability</div>
                                        <div style="color: {prob_color}; font-weight: bold; font-size: 1.5em;">{probability}</div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                            
                            # Recommendation justification (already nested under 'recommendation')
                            if recommendation:
                                st.markdown("### Recommendation Justification")
                                
                                # Justification text
                                just_text = recommendation.get('justification', '')
                                st.markdown(just_text)
                                
                                # Conditions if any
                                conditions = recommendation.get('conditional_requirements', [])
                                if conditions:
                                    st.markdown("#### Conditions")
                                    for condition in conditions:
                                        st.markdown(f"- {condition}")
                                
                                # Additional information needed
                                additional_info = recommendation.get('additional_information_needed', [])
                                if additional_info:
                                    st.markdown("#### Additional Information Needed")
                                    for info in additional_info:
                                        st.markdown(f"- {info}")
                            
                            # View raw JSON
                            with st.expander("View Raw JSON"):
                                st.json(dynamo_data) # Show the original full JSON
                    
                    except Exception as e:
                        st.error(f"Error displaying Decision Dynamo: {str(e)}")
                        st.json(st.session_state.decision_dynamo_output)
                else:
                    st.info("No Decision Dynamo results available. Please run the Decision Dynamo first.")
    
    with tab3:
        st.markdown("## Final Report")
        
        if st.session_state.final_report:
            try:
                report_data = st.session_state.final_report
                
                # Extract company and loan information
                company_name = report_data.get('company_name', 'Company')
                loan_amount = report_data.get('loan_request', {}).get('amount_sar', 0)
                loan_term = report_data.get('loan_request', {}).get('term_months', 0)
                
                # Header with company and download button
                header_cols = st.columns([3, 1])
                
                with header_cols[0]:
                    st.markdown(f"# Loan Assessment Report: {company_name}")
                    st.markdown(f"**Loan Request:** SAR {loan_amount:,} for {loan_term} months")
                
                with header_cols[1]:
                    # Download button for the report
                    report_json = json.dumps(report_data, indent=2)
                    st.download_button(
                        label="Download Report",
                        data=report_json,
                        file_name=f"{company_name}_loan_report.json",
                        mime="application/json"
                    )
                
                # Decision banner
                decision = report_data.get('decision', {})
                if decision:
                    decision_status = decision.get('status', 'Pending')
                    confidence = decision.get('confidence', 'Medium')
                    
                    # Set color based on decision
                    decision_color = {
                        'Accept': 'green',
                        'Reject': 'red',
                        'Review': 'orange',
                        'Pending': 'blue'
                    }.get(decision_status, 'blue')
                    
                    # Display decision banner
                    st.markdown(
                        f"""
                        <div style="padding: 20px; margin: 20px 0; background-color: {decision_color}15; 
                                border-left: 8px solid {decision_color}; border-radius: 4px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h2 style="margin: 0; color: {decision_color};">Decision: {decision_status}</h2>
                                <span style="font-weight: bold;">Confidence: {confidence}</span>
                            </div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                # Report sections in tabs
                report_tabs = st.tabs([
                    "Executive Summary", 
                    "Company Profile", 
                    "Financial Assessment", 
                    "Cash Flow", 
                    "Repayment Capacity", 
                    "Risk Assessment"
                ])
                
                # 1. Executive Summary
                with report_tabs[0]:
                    st.markdown("### Executive Summary")
                    
                    # Overall score
                    overall_score = report_data.get('scores', {}).get('overall', 0)
                    overall_color = "green" if overall_score >= 70 else "orange" if overall_score >= 50 else "red"
                    
                    summary_cols = st.columns([1, 1])
                    
                    with summary_cols[0]:
                        # Key metrics
                        st.markdown("#### Key Metrics")
                        
                        metrics = [
                            ("Financial Health", report_data.get('scores', {}).get('financial_health', 0)),
                            ("Cash Flow", report_data.get('scores', {}).get('cash_flow', 0)),
                            ("Repayment Capacity", report_data.get('scores', {}).get('repayment_capacity', 0)),
                            ("Business Stability", report_data.get('scores', {}).get('business_stability', 0))
                        ]
                        
                        # Function to display score with color-coded text
                        def display_text_score(label, score, max_score=100):
                            # Determine color
                            if score >= 70:
                                color = "green"
                            elif score >= 50:
                                color = "orange"
                            else:
                                color = "red"
                            
                            return f"**{label}:** <span style='color: {color}; font-weight: bold;'>{score}/{max_score}</span>"
                        
                        for label, score in metrics:
                            st.markdown(display_text_score(label, score), unsafe_allow_html=True)
                    
                    with summary_cols[1]:
                        # Overall score visualization
                        st.markdown(
                            f"""
                            <div style="text-align: center; padding: 15px; background-color: #f0f0f0; border-radius: 10px;">
                                <h4>Overall Score</h4>
                                <div style="font-size: 48px; font-weight: bold; color: {overall_color};">{overall_score}/100</div>
                                <div style="background-color: #ddd; border-radius: 10px; height: 12px; margin-top: 10px;">
                                    <div style="background-color: {overall_color}; width: {overall_score}%; height: 12px; border-radius: 10px;"></div>
                                </div>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                    
                    # Recommendation justification
                    st.markdown("#### Recommendation")
                    justification = report_data.get('recommendation_justification', {}).get('justification', '')
                    if justification:
                        st.markdown(justification)
                    
                    # Conditions if any
                    conditions = report_data.get('recommendation_justification', {}).get('conditions', [])
                    if conditions:
                        st.markdown("#### Conditions")
                        for condition in conditions:
                            st.markdown(f"- {condition}")
                
                # 2. Company Profile
                with report_tabs[1]:
                    st.markdown("### Company Profile")
                    
                    # Extract company information
                    company_info = report_data.get('company_profile', {})
                    if company_info:
                        profile_cols = st.columns(2)
                        
                        with profile_cols[0]:
                            st.markdown("#### Basic Information")
                            company_fields = {
                                "Legal Name": company_info.get('legal_name', ''),
                                "Trade Name": company_info.get('trade_name', ''),
                                "CR Number": company_info.get('cr_number', ''),
                                "Industry": company_info.get('industry', ''),
                                "Company Type": company_info.get('company_type', ''),
                                "Establishment Date": company_info.get('establishment_date', '')
                            }
                            
                            for label, value in company_fields.items():
                                if value:
                                    st.markdown(f"**{label}:** {value}")
                        
                        with profile_cols[1]:
                            st.markdown("#### Contact Information")
                            contact_fields = {
                                "Address": company_info.get('address', ''),
                                "City": company_info.get('city', ''),
                                "Website": company_info.get('website', ''),
                                "Phone": company_info.get('phone', ''),
                                "Email": company_info.get('email', '')
                            }
                            
                            for label, value in contact_fields.items():
                                if value:
                                    st.markdown(f"**{label}:** {value}")
                        
                        # Management team
                        management = company_info.get('management_team', [])
                        if management:
                            st.markdown("#### Management Team")
                            for member in management:
                                name = member.get('name', '')
                                position = member.get('position', '')
                                experience = member.get('experience', '')
                                st.markdown(f"**{name}** - {position}")
                                if experience:
                                    st.markdown(f"Experience: {experience}")
                        
                        # Business description
                        business_desc = company_info.get('business_description', '')
                        if business_desc:
                            st.markdown("#### Business Description")
                            st.markdown(business_desc)
                    else:
                        st.info("No company profile information available.")
                
                # 3. Financial Assessment
                with report_tabs[2]:
                    st.markdown("### Financial Assessment")
                    
                    financial = report_data.get('financial_assessment', {})
                    if financial:
                        # Summary of financial health
                        st.markdown("#### Financial Health Overview")
                        fin_health_score = report_data.get('scores', {}).get('financial_health', 0)
                        fin_color = "green" if fin_health_score >= 70 else "orange" if fin_health_score >= 50 else "red"
                        
                        st.markdown(
                            f"""
                            <div style="padding: 15px; background-color: {fin_color}10; 
                                    border-left: 5px solid {fin_color}; border-radius: 4px; margin-bottom: 20px;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <h4 style="margin: 0;">Financial Health Score</h4>
                                    <span style="font-weight: bold; color: {fin_color};">{fin_health_score}/100</span>
                                </div>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                        
                        # Key financial metrics
                        st.markdown("#### Key Financial Metrics")
                        
                        # Display financial metrics in a table
                        metrics = financial.get('key_metrics', {})
                        if metrics:
                            metrics_data = []
                            for key, value in metrics.items():
                                # Format the metric name with spaces
                                formatted_key = ' '.join(word.capitalize() for word in key.split('_'))
                                metrics_data.append({"Metric": formatted_key, "Value": value})
                            
                            if metrics_data:
                                st.table(pd.DataFrame(metrics_data))
                        
                        # Financial trends
                        trends = financial.get('trends', {})
                        if trends:
                            st.markdown("#### Financial Trends")
                            
                            # Prepare data for chart
                            trend_data = []
                            for metric, values in trends.items():
                                if isinstance(values, dict):
                                    for period, value in values.items():
                                        trend_data.append({
                                            "Metric": metric.replace('_', ' ').title(),
                                            "Period": period,
                                            "Value": value
                                        })
                            
                            if trend_data:
                                trend_df = pd.DataFrame(trend_data)
                                
                                # Create a chart if we have data
                                if not trend_df.empty:
                                    # Pivot the data for charting
                                    pivot_df = trend_df.pivot(index="Period", columns="Metric", values="Value")
                                    st.line_chart(pivot_df)
                        
                        # Financial strengths and weaknesses
                        strengths = financial.get('strengths', [])
                        weaknesses = financial.get('weaknesses', [])
                        
                        fin_cols = st.columns(2)
                        
                        with fin_cols[0]:
                            st.markdown("#### Financial Strengths")
                            if strengths:
                                for strength in strengths:
                                    st.markdown(f"- {strength}")
                            else:
                                st.markdown("No specific strengths identified.")
                        
                        with fin_cols[1]:
                            st.markdown("#### Financial Weaknesses")
                            if weaknesses:
                                for weakness in weaknesses:
                                    st.markdown(f"- {weakness}")
                            else:
                                st.markdown("No specific weaknesses identified.")
                    else:
                        st.info("No financial assessment information available.")
                
                # 4. Cash Flow
                with report_tabs[3]:
                    st.markdown("### Cash Flow Analysis")
                    
                    cash_flow = report_data.get('cash_flow_analysis', {})
                    if cash_flow:
                        # Cash flow score
                        cash_flow_score = report_data.get('scores', {}).get('cash_flow', 0)
                        cf_color = "green" if cash_flow_score >= 70 else "orange" if cash_flow_score >= 50 else "red"
                        
                        st.markdown(
                            f"""
                            <div style="padding: 15px; background-color: {cf_color}10; 
                                    border-left: 5px solid {cf_color}; border-radius: 4px; margin-bottom: 20px;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <h4 style="margin: 0;">Cash Flow Score</h4>
                                    <span style="font-weight: bold; color: {cf_color};">{cash_flow_score}/100</span>
                                </div>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                        
                        # Cash flow metrics
                        cf_metrics = cash_flow.get('metrics', {})
                        if cf_metrics:
                            st.markdown("#### Cash Flow Metrics")
                            
                            metrics_data = []
                            for key, value in cf_metrics.items():
                                formatted_key = ' '.join(word.capitalize() for word in key.split('_'))
                                metrics_data.append({"Metric": formatted_key, "Value": value})
                            
                            if metrics_data:
                                st.table(pd.DataFrame(metrics_data))
                        
                        # Cash flow summary
                        cf_summary = cash_flow.get('summary', '')
                        if cf_summary:
                            st.markdown("#### Summary")
                            st.markdown(cf_summary)
                        
                        # Cash flow stability
                        stability = cash_flow.get('stability', '')
                        if stability:
                            st.markdown("#### Cash Flow Stability")
                            st.markdown(stability)
                    else:
                        st.info("No cash flow analysis information available.")
                
                # 5. Repayment Capacity
                with report_tabs[4]:
                    st.markdown("### Repayment Capacity")
                    
                    repayment = report_data.get('repayment_analysis', {})
                    if repayment:
                        # Repayment score
                        repayment_score = report_data.get('scores', {}).get('repayment_capacity', 0)
                        rc_color = "green" if repayment_score >= 70 else "orange" if repayment_score >= 50 else "red"
                        
                        # Repayment metrics
                        monthly_payment = repayment.get('monthly_payment_sar', 0)
                        coverage_ratio = repayment.get('cash_flow_coverage_ratio', 0)
                        probability = repayment.get('repayment_probability', 0)
                        
                        # Display metrics in columns
                        rep_cols = st.columns(3)
                        
                        # Monthly payment
                        rep_cols[0].metric("Monthly Payment", f"SAR {monthly_payment:,}")
                        
                        # Coverage ratio with color
                        coverage_color = "green" if coverage_ratio >= 1.5 else "orange" if coverage_ratio >= 1.0 else "red"
                        rep_cols[1].markdown(
                            f"""
                            <div style="text-align: center;">
                                <div style="color: #808495; font-size: 0.8em;">Cash Flow Coverage</div>
                                <div style="color: {coverage_color}; font-weight: bold; font-size: 1.5em;">{coverage_ratio:.2f}x</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        # Repayment probability with color
                        prob_color = "green" if probability >= 0.8 else "orange" if probability >= 0.6 else "red"
                        prob_percentage = probability * 100
                        rep_cols[2].markdown(
                            f"""
                            <div style="text-align: center;">
                                <div style="color: #808495; font-size: 0.8em;">Repayment Probability</div>
                                <div style="color: {prob_color}; font-weight: bold; font-size: 1.5em;">{prob_percentage:.1f}%</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        # Repayment capacity score
                        st.markdown(
                            f"""
                            <div style="padding: 15px; background-color: {rc_color}10; 
                                    border-left: 5px solid {rc_color}; border-radius: 4px; margin: 20px 0;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <h4 style="margin: 0;">Repayment Capacity Score</h4>
                                    <span style="font-weight: bold; color: {rc_color};">{repayment_score}/100</span>
                                </div>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                        
                        # Repayment analysis summary
                        rep_summary = repayment.get('analysis', '')
                        if rep_summary:
                            st.markdown("#### Analysis")
                            st.markdown(rep_summary)
                        
                        # Stress test if available
                        stress_test = repayment.get('stress_test', {})
                        if stress_test:
                            st.markdown("#### Stress Test Results")
                            
                            for scenario, result in stress_test.items():
                                scenario_name = scenario.replace('_', ' ').title()
                                st.markdown(f"**{scenario_name}:** {result}")
                    else:
                        st.info("No repayment capacity analysis information available.")
                
                # 6. Risk Assessment
                with report_tabs[5]:
                    st.markdown("### Risk Assessment")
                    
                    risks = report_data.get('risk_assessment', [])
                    if risks:
                        # Risk score
                        risk_score = report_data.get('scores', {}).get('risk', 0)
                        risk_color = "green" if risk_score >= 70 else "orange" if risk_score >= 50 else "red"
                        
                        # Display risks in expandable sections
                        for risk in risks:
                            risk_factor = risk.get('factor', '')
                            severity = risk.get('severity', 'Medium')
                            mitigation = risk.get('mitigation', '')
                            
                            # Set color based on severity
                            severity_color = {
                                'Low': 'green',
                                'Medium': 'orange',
                                'High': 'red',
                                'Critical': 'darkred'
                            }.get(severity, 'gray')
                            
                            # Display risk factor
                            st.markdown(
                                f"""
                                <div style="margin-bottom: 15px; padding: 15px; border-left: 5px solid {severity_color}; 
                                        background-color: {severity_color}10; border-radius: 4px;">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                        <span style="font-weight: bold;">{risk_factor}</span>
                                        <span style="color: {severity_color}; font-weight: bold; text-transform: uppercase;">{severity}</span>
                                    </div>
                                    {f'<div style="margin-top: 10px;"><strong>Mitigation:</strong> {mitigation}</div>' if mitigation else ''}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        
                        # Risk summary if available
                        risk_summary = report_data.get('risk_summary', '')
                        if risk_summary:
                            st.markdown("#### Risk Summary")
                            st.markdown(risk_summary)
                    else:
                        st.info("No risk assessment information available.")
                
            except Exception as e:
                st.error(f"Error displaying final report: {str(e)}")
                st.json(st.session_state.final_report)
        else:
            st.info("No final report available. Please run the Final Analysis first.")

if __name__ == "__main__":
    main() 