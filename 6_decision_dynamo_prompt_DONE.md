# Decision Dynamo Model Calculation Rules

## Overview
The Decision Dynamo model is a scoring system that evaluates companies based on financial and technical metrics. The model produces a final score and recommendation based on weighted calculations of various factors.

## Model Versions
- v2.0: Original model
- v2.1: Updated model (currently same as v2.0)

## Revenue Bins
Companies are classified into three revenue bins based on their annual revenue in SAR:
- Small: < 10,000,000 SAR
- Medium: 10,000,000 - 30,000,000 SAR
- Large: > 30,000,000 SAR

## Company Types
Companies are classified by two main attributes:
1. MTC (Manufacturer/Trader/Contractor):
   - m: Manufacturer
   - t: Trader
   - c: Contractor

2. Niche Classification:
   - co: Commodity
   - ni: Niche
   - na: N/A

## Scoring Components

### 1. Financial Score (40-60% of final score)
The financial score is composed of three categories:

#### Liquidity (f1)
- Current Ratio
- Weights vary by MTC:
  - Manufacturer: 43.5%
  - Trader: 47%
  - Contractor: 50%

#### Profitability (f2)
- Net Profit Margin
- Gross Profit Margin
- Weights vary by MTC:
  - Manufacturer: 23%
  - Trader: 23%
  - Contractor: 50%

#### Activity (f3)
- Cash Conversion Cycle
- Weights vary by MTC:
  - Manufacturer: 33.5%
  - Trader: 30%
  - Contractor: 0%

### 2. Technical Score (40-60% of final score)
The technical score is composed of six categories:

#### End User (t1)
- End User Size
- Revenue Concentration
- Payment Delay
- Weights vary by MTC:
  - Manufacturer: 16%
  - Trader: 11%
  - Contractor: 25%

#### History (t2)
- Buildnow Payments
- Simah Delinquencies
- Current Delinquency Status
- Weights vary by MTC:
  - Manufacturer: 26%
  - Trader: 26%
  - Contractor: 19%

#### Management (t3)
- Owner's Age
- Management Experience
- Weights vary by MTC:
  - Manufacturer: 21%
  - Trader: 21%
  - Contractor: 9%

#### Company (t4)
- Years in Business
- Company Age
- References
- Weights vary by MTC:
  - Manufacturer: 37%
  - Trader: 42%
  - Contractor: 19%

#### Project List (t5)
- Number of Projects
- Project Completion
- Weights vary by MTC:
  - Manufacturer: 0%
  - Trader: 0%
  - Contractor: 28%

#### Site Visits (t6)
- Overall Office/Site Rating
- Used as a multiplier for technical score
- Multipliers:
  - Good (t6a_1): 1.2x
  - Okay (t6a_2): 1.0x
  - Poor (t6a_3): 0.8x

## Final Score Calculation

1. Calculate individual scores for each metric using the provided answer weights
2. Apply subcategory weights to get subcategory scores
3. Apply category weights to get category scores
4. Calculate financial and technical component scores
5. Apply revenue bin weights to combine components:
   - Small: 30% Financial, 70% Technical
   - Medium: 50% Financial, 50% Technical
   - Large: 60% Financial, 40% Technical
6. Apply site visit multiplier to technical score for adjusted final score

## Recommendation Rules
The final recommendation is based on the adjusted final score ranges:
- Accept: Score above threshold (varies by model version)
- Reject: Score below threshold (varies by model version)
- Review: Score within review range (varies by model version)

## Special Cases
1. For Niche Manufacturers (m_ni):
   - f3a_3 answer is not allowed
   - Different weights for profitability metrics

2. For Commodity Traders (t_co):
   - f2a_2 and f2b_2 answers are not allowed
   - Different weights for profitability metrics

3. For Contractors (c_na):
   - No weight on activity metrics
   - Higher weight on project list metrics
   - Different profitability weight distribution

## Data Validation Rules
1. All required metrics must be provided
2. Answers must match the allowed values for each metric
3. Revenue must be a positive number
4. Current ratio and profit margins must be non-negative
5. Cash conversion cycle must be a non-negative integer 