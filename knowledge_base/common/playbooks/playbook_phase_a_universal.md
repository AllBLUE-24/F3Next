# ERPNext Phase A — Universal Foundation Setup Sequence

Every ERPNext implementation, regardless of industry, begins with the same
foundational sequence. These records are NEVER sourced from client data files.
They are either auto-created by ERPNext or seeded from F3Next's default baseline.

Step 1: Company Record
  - Created with: company_name, abbr, country, default_currency
  - ERPNext auto-creates: default Chart of Accounts (country-specific), 
    default Cost Center (Main), default Warehouse
  - No client data file needed.

Step 2: Fiscal Year
  - Created from company settings (fiscal_year_start, fiscal_year_end)
  - If not provided, default to April-March (India) or Jan-Dec (US/EU)
  - Auto-linked to Company. No client data file needed.

Step 3: Chart of Accounts
  - ERPNext auto-generates a standard COA on Company creation
  - F3Next supplements with industry-specific accounts from baseline
  - Client data NOT required at this stage — accounts are added progressively

Step 4: Cost Centers
  - "Main" cost center is auto-created with Company
  - Additional cost centers are seeded from F3Next baseline (Finance, Operations)
  - No client data file needed.

Step 5: Warehouses
  - Default warehouse auto-created with Company
  - Additional warehouses (if needed) are asked as simple questions, not file uploads
  - Example: "Do you have multiple storage locations? (Yes/No)"

After Phase A completes: the system is ready to receive Master Data (customers, items, suppliers).
This is the correct professional sequence. Skipping this means ALL subsequent imports will fail
with link validation errors.
