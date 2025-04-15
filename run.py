import streamlit as st
import subprocess
import os
import sys

def main():
    """
    Main function to run the agentic document processor
    """
    print("Starting Agentic Document Processor...")
    
    # Run the Streamlit app
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "agentic_processor.py", 
        "--server.port=8501", 
        "--server.address=localhost"
    ])

if __name__ == "__main__":
    main() 