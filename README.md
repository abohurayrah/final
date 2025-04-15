# Agentic Document Processing System

This system provides an intelligent, agentic approach to document classification and analysis, utilizing Google's Gemini 2.5 Pro model.

## Features

- **Document Classification**: Automatically identifies document types from uploads.
- **Specialized Analysis**: Processes each document type with tailored analysis.
- **Decision Engine**: Aggregates analysis to produce final recommendations.
- **Report Generation**: Creates comprehensive reports with key insights.
- **Result Storage**: Saves all analysis results in timestamped directories.

## Document Types Supported

- Bank Statements
- Financial Statements
- Project Lists
- GOSI Certificates
- VAT Statements/Returns
- Saudization Certificates
- Project Contracts
- Commercial Registrations (CR)
- Company Profiles

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/agentic-document-processor.git
cd agentic-document-processor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your Gemini API key in a `.env` file:
```
GEMINI_API_KEY=your_api_key_here
```

## Usage

1. Run the application:
```bash
python run.py
```

2. Open your browser and navigate to `http://localhost:8501`

3. Upload your documents and follow the interface instructions to process them.

4. Check the `results_TIMESTAMP` directory for saved analysis files.

## Flow

1. **Upload & Classification**: Upload documents and classify them by type.
2. **Individual Analysis**: Process each document category with specialized analysis.
3. **Decision Generation**: Generate overall recommendations based on all analyses.
4. **Final Report**: Create comprehensive report with key insights and recommendations.

## File Structure

- `agentic_processor.py`: Main Streamlit application
- `magic_box.py`: Document classification functionality
- `run.py`: Helper script to run the application
- `results_*/`: Directories containing analysis results (created at runtime)

## Requirements

- Python 3.8+
- Streamlit
- Google Generative AI Python SDK
- Pandas
- Internet connection for API calls 