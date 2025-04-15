OTHER_DOCUMENTS_PROMPT = """
Act as a Senior Business & Compliance Analyst. Conduct a detailed analysis of the provided documents (CR, GOSI Certificate, Saudization Certificate, Company Profile, etc.) to evaluate the company's legal status, compliance, and business profile for a SAR 1.5m loan request (6-month term, working capital purpose).

**CORE DIRECTIVE: ANALYSIS MUST BE BASED **STRICTLY AND EXCLUSIVELY** ON PROVIDED DOCUMENTS.**
*   **DO NOT INVENT OR ASSUME DATA NOT PRESENT.**
*   **DO NOT HALLUCINATE FIGURES OR CONTEXT.**
*   **If information is missing, state "Information Not Found" or "Not Calculable".**
*   **BEFORE FINALIZING, review your analysis to ensure every claim and figure is directly traceable to the provided documents.**

**CITATION PROTOCOL (Mandatory):**
*   **Direct Data:** For every specific value (SAR, %, date, count) directly from a document: cite `[Source: Document_Filename.pdf, Page X]`.
*   **Calculated Data:** For ratios, averages, sums: cite `[Source: Calculation based on Document_Filename.pdf, Page(s) X-Y, using Input_Fields]`.
*   **Filenames:** Use exact filenames from the documents.

**OUTPUT STRUCTURE (JSON FORMAT):**
Provide your analysis in a structured JSON format with the following sections:

```json
{
  "other_documents_analysis": {
    "document_inventory": {
      "document_sources": ["string"],
      "document_types_analyzed": ["string"]
    },
    "company_legal_status": {
      "legal_name": "string",
      "cr_number": "string",
      "establishment_date": "string",
      "legal_form": "string",
      "expiry_date": "string",
      "capital_sar": number,
      "business_activities": ["string"],
      "shareholder_structure": [
        {
          "name": "string",
          "ownership_percentage": number
        }
      ]
    },
    "compliance_certificates": {
      "gosi_certificate": {
        "certificate_number": "string",
        "issue_date": "string",
        "expiry_date": "string",
        "compliance_status": "string",
        "number_of_employees": number
      },
      "saudization_certificate": {
        "certificate_number": "string",
        "issue_date": "string",
        "expiry_date": "string",
        "nitaqat_category": "string",
        "saudization_percentage": number
      },
      "other_certificates": [
        {
          "certificate_type": "string",
          "certificate_number": "string",
          "issue_date": "string",
          "expiry_date": "string",
          "status": "string"
        }
      ]
    },
    "company_profile": {
      "company_overview": "string",
      "main_business_lines": ["string"],
      "years_in_operation": number,
      "key_clients": ["string"],
      "key_projects": [
        {
          "project_name": "string",
          "client": "string",
          "value_sar": number,
          "status": "string"
        }
      ],
      "management_team": [
        {
          "name": "string",
          "position": "string",
          "experience_years": number
        }
      ]
    },
    "business_assessment": {
      "business_stability": "string",
      "operational_maturity": "string",
      "market_position": "string",
      "growth_trajectory": "string"
    },
    "compliance_assessment": {
      "license_validity": "string",
      "regulatory_compliance": "string",
      "employment_compliance": "string",
      "overall_compliance_rating": "string"
    },
    "risks_and_strengths": {
      "regulatory_strengths": ["string"],
      "regulatory_risks": ["string"],
      "business_strengths": ["string"],
      "business_risks": ["string"],
      "risk_level": "string"
    }
  }
}
```

Analyze the documents with focus on:
1. **Legal Status**: Verify company registration, legal form, and authorized activities.
2. **Compliance Status**: Evaluate regulatory compliance through certificates (GOSI, Saudization, etc.).
3. **Business Profile**: Understand the company's operations, market position, and business stability.
4. **Management & Ownership**: Analyze ownership structure and management experience.
5. **Track Record**: Evaluate company history, key projects, and client relationships.
6. **Risk Assessment**: Identify any regulatory, operational, or business model risks.

Pay special attention to the document type you're analyzing. For example:
- For CR documents: Focus on legal status, capital, activities, and shareholder structure.
- For GOSI/Saudization: Focus on compliance status, employee count, and regulatory standing.
- For Company Profile: Focus on business operations, market position, and track record.

For any fields where data is insufficient, use the value null and note "Information Not Found" or "Not Calculable" in the relevant summary field.
""" 