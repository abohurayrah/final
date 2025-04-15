BANK_STATEMENT_PROMPT = """
Act as a Senior Banking & Cash Flow Analyst. Conduct a detailed analysis of the provided bank statements to evaluate cash flow patterns and financial health for a SAR 1.5m loan request (6-month term, working capital purpose).

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
  "bank_statement_analysis": {
    "overview": {
      "accounts_analyzed": "string",
      "period_covered": "string",
      "document_sources": ["string"]
    },
    "cash_flow_summary": {
      "analysis_period": "string",
      "months_analyzed": number,
      "total_inflows_sar": number,
      "total_outflows_sar": number,
      "net_cash_flow_sar": number,
      "avg_monthly_inflow_sar": number,
      "avg_monthly_outflow_sar": number,
      "avg_monthly_net_cash_flow_sar": number,
      "ending_balance_sar": number,
      "min_balance_sar": number,
      "nsfs_overdrafts": number
    },
    "inflow_analysis": {
      "summary": "string",
      "major_inflow_sources": [
        {
          "source_type": "string",
          "frequency": "string",
          "avg_amount_sar": number,
          "percentage_of_total": number
        }
      ],
      "unusual_inflows": [
        {
          "date": "string",
          "amount_sar": number,
          "description": "string"
        }
      ],
      "consistency_assessment": "string"
    },
    "outflow_analysis": {
      "summary": "string",
      "major_outflow_categories": [
        {
          "category": "string",
          "avg_monthly_amount_sar": number,
          "percentage_of_total": number
        }
      ],
      "owner_withdrawals": {
        "avg_monthly_amount_sar": number,
        "pattern": "string"
      },
      "tax_vat_payments": {
        "avg_monthly_amount_sar": number,
        "consistency": "string"
      },
      "existing_loan_payments": {
        "avg_monthly_amount_sar": number,
        "consistency": "string"
      },
      "unusual_outflows": [
        {
          "date": "string",
          "amount_sar": number,
          "description": "string"
        }
      ]
    },
    "balance_trend": {
      "trend_pattern": "string",
      "volatility": "string",
      "minimum_balance_implications": "string"
    },
    "repayment_capacity": {
      "est_monthly_repayment_sar": number,
      "cash_flow_coverage_ratio": number,
      "assessment": "string"
    },
    "financial_discipline": {
      "withdrawal_pattern": "string",
      "cash_management_assessment": "string",
      "payment_consistency": "string",
      "overall_discipline_rating": "string"
    },
    "risks_and_strengths": {
      "strengths": ["string"],
      "weaknesses": ["string"],
      "risk_level": "string"
    }
  }
}
```

Analyze the bank statements with focus on:
1. **Cash Flow Patterns**: Inflows vs outflows, stability, seasonality, and trends over time.
2. **Transaction History**: Regular payment patterns, major transactions, unusual activities.
3. **Balance Trends**: Average balance maintenance, minimum balances, overdrafts.
4. **Repayment Capacity**: Based on historical cash flows, assess ability to handle monthly loan payments.
5. **Financial Discipline**: Evidence of consistent financial management, regular payments, and appropriate withdrawals.
6. **Risk Indicators**: Identify irregular transactions, bounced payments, or concerning patterns.

For any fields where data is insufficient, use the value null and note "Information Not Found" or "Not Calculable" in the relevant summary field.
""" 