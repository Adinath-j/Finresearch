"""Utility to generate realistic financial seed PDF documents for testing and demo."""

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def generate_seed_pdf_files(output_dir: Path) -> List[Path]:
    """Generate 4 realistic multi-page financial PDFs in output_dir using PyMuPDF (fitz)."""
    import fitz  # PyMuPDF

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files: List[Path] = []

    # 1. Zenith Energy
    zenith_path = output_dir / "zenith_energy_earnings_call_q4_fy25.pdf"
    if not zenith_path.exists():
        doc = fitz.open()
        p1 = doc.new_page(width=595, height=842)
        text_p1 = """ZENITH ENERGY RESOURCES CORP. (NYSE: ZER)
Q4 and Full Fiscal Year 2025 Earnings Call Transcript
Date: October 24, 2025 | Corporate Headquarters: Houston, Texas

Executive Leadership Remarks:
Chief Executive Officer:
"Zenith Energy closed fiscal year 2025 with strong operational execution across our upstream and midstream operations. Total revenue reached $8,420 million for fiscal year 2025, reflecting disciplined production growth and strong downstream crack spreads. Operating income grew to $1,980 million, representing an operating margin of 23.5%."

Chief Financial Officer:
"Our financial structure remains conservative. Key financial highlights for FY2025 include:
- Total Revenue: $8,420 million
- Gross Profit: $4,850 million
- Operating Income: $1,980 million
- Net Income: $1,450 million
- Operating Cash Flow: $2,650 million
- Capital Expenditure: $1,120 million
- Free Cash Flow: $1,530 million
- Total Assets: $22,400 million
- Total Current Assets: $6,900 million
- Total Current Liabilities: $3,200 million
- Current Ratio: 2.15x
- Total Debt: $3,800 million
- Shareholders Equity: $12,100 million
- Debt to Equity: 0.31x
- Return on Equity (ROE): 12.0%

During the year we repaid $450 million of long-term debt and distributed $600 million through dividends and share buybacks."
"""
        p1.insert_text(fitz.Point(50, 60), text_p1, fontsize=10, fontname="helv")

        p2 = doc.new_page(width=595, height=842)
        text_p2 = """ZENITH ENERGY RESOURCES CORP. - FINANCIAL DISCLOSURES & AUDIT REPORT

Auditor Disclosures & Key Audit Matters:
Independent Auditor Report provided by Ernst & Young LLP:
"We have audited the consolidated financial statements of Zenith Energy Resources Corp., which comprise the consolidated balance sheet as of December 31, 2025, and the related consolidated statements of income, cash flows, and equity.

Audit Opinion:
In our opinion, the consolidated financial statements present fairly, in all material respects, the financial position of the Company.

Key Audit Matters (KAM):
1. Asset Retirement Obligations (ARO): Valuation of decommissioning liabilities for offshore production platforms involves significant management estimates regarding discount rates and regulatory abandonment schedules.
2. Impairment Assessment of Proven Reserves: Evaluation of carrying values in light of fluctuating NYMEX crude oil benchmarks."
"""
        p2.insert_text(fitz.Point(50, 60), text_p2, fontsize=10, fontname="helv")
        doc.save(str(zenith_path))
        doc.close()
        generated_files.append(zenith_path)
    else:
        generated_files.append(zenith_path)

    # 2. Acme Cloud Technologies
    acme_path = output_dir / "acme_cloud_technologies_sec_10k_fy25.pdf"
    if not acme_path.exists():
        doc = fitz.open()
        p1 = doc.new_page(width=595, height=842)
        text_p1 = """UNITED STATES SECURITIES AND EXCHANGE COMMISSION
WASHINGTON, D.C. 20549
FORM 10-K
ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934
For the fiscal year ended December 31, 2025
Commission File Number: 001-38912
ACME CLOUD TECHNOLOGIES, INC.

PART II. ITEM 8. FINANCIAL STATEMENTS
Consolidated Statements of Operations (in USD millions):

| Line Item | FY 2025 | FY 2024 |
| Total Revenue | 14,300.00 | 12,500.00 |
| Subscription Revenue | 11,200.00 | 9,800.00 |
| Cost of Revenue | 4,550.00 | 4,100.00 |
| Gross Profit | 9,750.00 | 8,400.00 |
| Research & Development | 3,850.00 | 3,300.00 |
| Sales & Marketing | 2,600.00 | 2,300.00 |
| General & Administrative | 1,000.00 | 900.00 |
| Operating Expenses | 7,450.00 | 6,500.00 |
| Operating Income | 2,300.00 | 1,900.00 |
| Income Before Income Taxes | 1,600.00 | 1,320.00 |
| Provision for Income Taxes | 416.00 | 340.00 |
| Net Income | 1,184.00 | 980.00 |
"""
        p1.insert_text(fitz.Point(50, 60), text_p1, fontsize=10, fontname="helv")

        p2 = doc.new_page(width=595, height=842)
        text_p2 = """ACME CLOUD TECHNOLOGIES, INC. - FORM 10-K (CONTINUED)
Consolidated Balance Sheets (in USD millions):

| Line Item | December 31, 2025 | December 31, 2024 |
| Cash and Cash Equivalents | 3,450.00 | 2,900.00 |
| Accounts Receivable, net | 2,800.00 | 2,400.00 |
| Prepaid and Other Current Assets | 1,700.00 | 1,500.00 |
| Current Assets | 7,950.00 | 6,800.00 |
| Property and Equipment, net | 4,200.00 | 3,600.00 |
| Goodwill and Intangibles | 6,450.00 | 5,800.00 |
| Total Assets | 18,600.00 | 16,200.00 |
| Current Liabilities | 5,000.00 | 4,300.00 |
| Total Debt | 2,500.00 | 2,100.00 |
| Total Liabilities | 8,700.00 | 7,600.00 |
| Shareholders Equity | 9,900.00 | 8,600.00 |
| Operating Cash Flow | 3,150.00 | 2,700.00 |
| Capital Expenditure | 1,400.00 | 1,200.00 |
| Free Cash Flow | 1,750.00 | 1,500.00 |

Report of Independent Registered Public Accounting Firm:
PricewaterhouseCoopers LLP issued an unqualified audit opinion.
Key Audit Matter: Accounting for multi-element enterprise cloud subscription arrangements."""
        p2.insert_text(fitz.Point(50, 60), text_p2, fontsize=10, fontname="helv")
        doc.save(str(acme_path))
        # Also save copy as acme_tech_10k_fy25.pdf for test_milestone2_e2e
        doc.save(str(output_dir / "acme_tech_10k_fy25.pdf"))
        doc.close()
        generated_files.append(acme_path)
        generated_files.append(output_dir / "acme_tech_10k_fy25.pdf")
    else:
        generated_files.append(acme_path)
        if not (output_dir / "acme_tech_10k_fy25.pdf").exists():
            import shutil
            shutil.copyfile(acme_path, output_dir / "acme_tech_10k_fy25.pdf")
            generated_files.append(output_dir / "acme_tech_10k_fy25.pdf")

    # 3. Apex Financial Holdings
    apex_path = output_dir / "apex_financial_holdings_annual_report_fy25.pdf"
    if not apex_path.exists():
        doc = fitz.open()
        p1 = doc.new_page(width=595, height=842)
        text_p1 = """APEX FINANCIAL HOLDINGS GROUP
Annual Statutory Financial Report - Fiscal Year 2025
London & New York Stock Exchanges | Tier-1 Banking Institution

Consolidated Statement of Operations (in USD millions):
Total Revenue: $9,750 million
Net Interest Income: $6,840 million
Non-Interest Fee Income: $2,910 million
Operating Expenses: $5,120 million
Operating Profit: $4,630 million
Provisions for Expected Credit Losses: $1,380 million
Net Income: $2,420 million

Prudential Regulatory Capital Ratios (Basel III Framework):
- Capital to Risk Assets Ratio (CRAR Basel III): 16.8% (Regulatory Requirement: 11.5%)
- Common Equity Tier 1 (CET1) Ratio: 13.4%
- Liquidity Coverage Ratio (LCR): 142%
- Net Stable Funding Ratio (NSFR): 124%
- Gross Non-Performing Assets (GNPA): 2.1%
- Net NPA Ratio: 0.6%
"""
        p1.insert_text(fitz.Point(50, 60), text_p1, fontsize=10, fontname="helv")

        p2 = doc.new_page(width=595, height=842)
        text_p2 = """APEX FINANCIAL HOLDINGS GROUP - BALANCE SHEET & AUDIT OPINION
Consolidated Balance Sheet Summary (in USD millions):
- Total Assets: $94,500 million
- Cash and Interbank Balances: $12,400 million
- Customer Loans and Advances: $62,100 million
- Investment Securities: $16,800 million
- Total Current Assets: $28,500 million
- Customer Deposits: $71,200 million
- Total Debt: $6,400 million
- Total Current Liabilities: $18,900 million
- Current Ratio: 1.51x
- Shareholders Equity: $11,800 million
- Return on Equity (ROE): 20.5%

Independent Auditor Report:
KPMG LLP issued an unqualified audit opinion with Key Audit Matter focused on model validation for ECL loan impairment provisions."""
        p2.insert_text(fitz.Point(50, 60), text_p2, fontsize=10, fontname="helv")
        doc.save(str(apex_path))
        doc.close()
        generated_files.append(apex_path)
    else:
        generated_files.append(apex_path)

    # 4. Infosys Annual Report
    infy_path = output_dir / "infosys_annual_report_fy24.pdf"
    if not infy_path.exists():
        doc = fitz.open()
        p1 = doc.new_page(width=595, height=842)
        text_p1 = """INFOSYS LIMITED
Integrated Annual Report 2023-24 | Bengaluru, India
Consolidated Statement of Profit and Loss (in INR Crores):

| Particulars | Year ended March 31, 2024 | Year ended March 31, 2023 |
| Revenue from operations | 153,670 | 146,767 |
| Other income | 3,120 | 2,700 |
| Total revenue | 156,790 | 149,467 |
| Cost of sales | 107,850 | 101,847 |
| Gross profit | 45,820 | 44,920 |
| Selling and marketing expenses | 6,823 | 6,400 |
| General and administrative expenses | 7,250 | 8,415 |
| Total operating expenses | 121,923 | 116,662 |
| Operating profit | 31,747 | 30,105 |
| Operating margin | 20.7% | 20.5% |
| Profit before tax | 34,250 | 32,800 |
| Tax expense | 8,002 | 8,705 |
| Profit for the period | 26,248 | 24,095 |
| Diluted EPS (INR) | 63.40 | 57.60 |
"""
        p1.insert_text(fitz.Point(50, 60), text_p1, fontsize=10, fontname="helv")

        p2 = doc.new_page(width=595, height=842)
        text_p2 = """INFOSYS LIMITED - BALANCE SHEET & CASH FLOWS (CONTINUED)
Consolidated Balance Sheet & Capital Position (in INR Crores):

| Line Item | As at March 31, 2024 | As at March 31, 2023 |
| Total assets | 143,260 | 128,450 |
| Current assets | 89,450 | 81,200 |
| Cash and cash equivalents | 18,240 | 12,130 |
| Current liabilities | 36,210 | 32,150 |
| Total debt | 0 | 0 |
| Total liabilities | 44,720 | 39,130 |
| Shareholders equity | 98,540 | 89,320 |
| Current ratio | 2.47 | 2.53 |
| Return on equity (ROE) | 26.6% | 27.0% |
| Operating cash flow | 28,410 | 25,600 |
| Capital expenditure | 4,428 | 4,100 |
| Free cash flow | 23,982 | 21,500 |

Independent Auditor Report:
Deloitte Haskins & Sells LLP audited the consolidated financial statements and issued an unqualified unmodified opinion.
Key Audit Matters: Recognition of revenue under fixed-price contracts and percentage of completion."""
        p2.insert_text(fitz.Point(50, 60), text_p2, fontsize=10, fontname="helv")
        doc.save(str(infy_path))
        doc.close()
        generated_files.append(infy_path)
    else:
        generated_files.append(infy_path)

    logger.info("Generated %d seed financial PDF documents in %s", len(generated_files), output_dir)
    return generated_files
