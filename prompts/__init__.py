from .bank_statement_prompt import BANK_STATEMENT_PROMPT
from .financial_statement_prompt import FINANCIAL_STATEMENT_PROMPT
from .vat_statement_prompt import VAT_STATEMENT_PROMPT
from .contract_prompt import CONTRACT_PROMPT
from .other_documents_prompt import OTHER_DOCUMENTS_PROMPT
from .decision_dynamo_prompt import DECISION_DYNAMO_PROMPT
from .final_report_prompt import FINAL_REPORT_PROMPT

# Mapping of document types to their specialized prompts
DOCUMENT_TYPE_PROMPTS = {
    "Bank Statement": BANK_STATEMENT_PROMPT,
    "Financial Statement": FINANCIAL_STATEMENT_PROMPT,
    "VAT Statement": VAT_STATEMENT_PROMPT,
    "Project Contract": CONTRACT_PROMPT,
    "CR": OTHER_DOCUMENTS_PROMPT,
    "GOSI": OTHER_DOCUMENTS_PROMPT,
    "Saudization Certificate": OTHER_DOCUMENTS_PROMPT,
    "Company Profile": OTHER_DOCUMENTS_PROMPT,
    "Project List": OTHER_DOCUMENTS_PROMPT,
    "Other": OTHER_DOCUMENTS_PROMPT
}

# Get the appropriate prompt for a given document type
def get_prompt_for_document_type(document_type):
    """Returns the specialized prompt for a given document type"""
    return DOCUMENT_TYPE_PROMPTS.get(document_type, OTHER_DOCUMENTS_PROMPT) 