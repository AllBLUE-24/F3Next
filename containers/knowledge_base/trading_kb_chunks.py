# ============================================================
# F3Next Knowledge Base — TRADING F3ICHE
# Complete 50-chunk content for pgvector population
# Categories: FMCG Distribution, Wholesale, Retail, Cross-cutting
# Chunk size target: 400–600 tokens (~1,600–2,400 chars)
# ============================================================

# ============================================================
# FMCG DISTRIBUTION — 15 CHUNKS
# ============================================================

TRADING_FMCG_COMPLIANCE = [
    {
        "title": "GST Registration and E-Invoicing for FMCG Traders",
        "content": """
GST REGISTRATION FOR FMCG TRADING BUSINESSES

All trading businesses with annual turnover above ₹40 lakhs (₹20 lakhs for special category states) must mandatorily register under GST. FMCG distributors typically cross this threshold quickly due to high volume.

REGISTRATION PROCESS:
1. Visit gst.gov.in and click New Registration
2. Fill Form GST REG-01 with PAN, Aadhaar, business address
3. Upload documents: PAN card, Aadhaar, address proof, bank statement, passport photo
4. ARN (Application Reference Number) issued within 15 minutes
5. GST registration certificate issued within 7 working days
6. Multiple business verticals or states require separate GSTIN

E-INVOICING REQUIREMENTS:
- Mandatory for turnover above ₹5 crores (from Aug 2023)
- Each invoice must carry IRN (Invoice Reference Number) — a 64-character hash
- QR code mandatory on B2B invoices
- E-invoice must be generated before or at time of supply, never retrospectively

ERPNext INTEGRATION FOR COMPLIANCE:
- Enable E-Invoicing in GST Settings doctype
- IRN auto-generated via NIC API on submission of Sales Invoice
- Custom fields store IRN and QR code on invoice printout
- GSTR-1 auto-populated from submitted invoices
- HSN Summary auto-computed for filing

COMMON GST MISTAKES BY FMCG TRADERS:
- Missing or incorrect HSN codes (6-digit mandatory above ₹5 crore turnover)
- Wrong tax rate applied to items (FMCG spans 0%, 5%, 12%, 18% slabs)
- Incorrect Place of Supply for inter-state sales
- Not reconciling GSTR-2A with purchase register before ITC claim
        """,
        "tags": ["gst", "e-invoicing", "compliance", "fmcg", "irn"],
        "priority": "high"
    },
    {
        "title": "FSSAI Licensing Requirements for FMCG Distributors",
        "content": """
FSSAI LICENSING FOR FMCG DISTRIBUTION

Any business involved in storing, distributing, or trading food products is required to obtain FSSAI (Food Safety and Standards Authority of India) registration or license under the Food Safety and Standards Act, 2006.

THREE LICENSE TIERS:
1. BASIC REGISTRATION (< ₹12 lakh annual turnover)
   - Form A registration, fee ₹100/year
   - Valid 1–5 years, renewable
   - Issued by local Food Safety Officer

2. STATE LICENSE (₹12 lakh – ₹20 crore turnover)
   - Form B license, fee ₹2,000–₹5,000/year
   - Issued by State Food Safety Commissioner
   - Physical inspection of premises mandatory
   - Takes 30–60 days

3. CENTRAL LICENSE (> ₹20 crore turnover or multi-state operations)
   - Fee ₹7,500/year
   - Issued by FSSAI central authority
   - Regular third-party audits required
   - Mandatory for importers and large distributors

STORAGE AND HANDLING COMPLIANCE:
- Warehouse must be clean, dry, and well-ventilated
- Temperature-controlled storage for dairy, frozen, and perishables
- FIFO (First In First Out) stock rotation must be maintained
- Pest control records maintained with licensed pest control vendor
- No storage of food adjacent to chemicals or non-food items

MANDATORY DOCUMENTATION:
- Purchase invoices must carry supplier's FSSAI license number
- Inward stock register with batch numbers and expiry dates
- Temperature logs for cold chain items (2x daily minimum)
- Pest control certificates and visit logs

ERPNext SETUP FOR FSSAI:
- Add custom field "FSSAI License No" in Supplier master
- Validate FSSAI field is filled before Purchase Order submission
- Track item expiry dates in Batch master
- Generate expiry-based stock reports for monthly audit readiness
        """,
        "tags": ["fssai", "food_safety", "licensing", "fmcg", "compliance"],
        "priority": "high"
    },
    {
        "title": "Drug License and Cosmetic Regulations for FMCG Traders",
        "content": """
DRUG LICENSE REQUIREMENTS FOR FMCG DISTRIBUTORS

FMCG distributors dealing in OTC medicines, health supplements, or cosmetics require additional licenses beyond GST and FSSAI. This is governed by the Drugs and Cosmetics Act, 1940.

WHO NEEDS A DRUG LICENSE:
- Distributors of Schedule H, H1, or X drugs (prescription medicines)
- Wholesale dealers of OTC drugs, cough syrups, vitamins
- Distributors of cosmetics containing restricted substances

WHOLESALE DRUG LICENSE (Form 20B / 21B):
- Issued by State Drug Controller
- Requires qualified pharmacist or technical staff
- Premises must meet minimum area requirements (usually 10 sq m)
- Separate storage for Schedule X substances
- Application fee: ₹3,000–₹5,000

COSMETIC REGISTRATION:
- Cosmetics imported or manufactured need Form 42 registration
- Domestic cosmetics distributed via licensed channels do not need registration
- Ensure all cosmetic products on shelf carry valid manufacturing license from supplier

COMPLIANCE CALENDAR FOR FMCG DISTRIBUTORS:
- GST Returns: GSTR-1 (11th), GSTR-3B (20th) monthly
- FSSAI Renewal: 30 days before expiry
- Drug License Renewal: Annual, before expiry date
- Shop & Establishment Act Renewal: As per state (annual/biannual)
- Professional Tax: Monthly/Quarterly as per state rules

ERPNext COMPLIANCE TRACKING:
- Use "Compliance Tracker" custom doctype or Notice of Intent module
- Set reminder alerts 60 days before license expiry
- Maintain scanned copies of all licenses in File Manager
- Create compliance checklist items in Task module linked to company
        """,
        "tags": ["drug_license", "cosmetics", "compliance", "fmcg", "schedule_h"],
        "priority": "medium"
    },
    {
        "title": "Shop and Establishment Act, Labour Law Compliance for Traders",
        "content": """
SHOP AND ESTABLISHMENT ACT COMPLIANCE FOR TRADING BUSINESSES

Every trading business — whether a distributor, wholesaler, or retailer — operating a shop, warehouse, or office must register under the Shop and Establishment Act of their respective state. This is among the first registrations needed before commencing business.

REGISTRATION PROCESS:
- Apply to local municipal corporation or labour department within 30 days of starting business
- Form and fees vary by state (typically ₹200–₹2,000 annually)
- Certificate must be displayed prominently at the business premises
- Renewal is annual or biannual based on state

WHAT IT GOVERNS:
- Working hours: typically 8–9 hours/day, max 48 hours/week
- Overtime: Double wages for work beyond prescribed hours
- Weekly off: Mandatory one day off per week for employees
- Leave: Minimum 12 days earned leave + 12 days casual/medical leave per year
- Prohibited employment of children below 14 years

ADDITIONAL LABOUR COMPLIANCES FOR FMCG DISTRIBUTORS:
1. Employees Provident Fund (EPF): Mandatory if 20+ employees, 12% employer + 12% employee on basic salary
2. Employees State Insurance (ESIC): Mandatory if 10+ employees, 3.25% employer + 0.75% employee on gross wages
3. Professional Tax: Deducted from employee salary, varies by state (max ₹2,500/year)
4. Gratuity: Payable after 5 years of service, 15 days salary per year

ERPNext PAYROLL SETUP:
- Create salary structures with EPF and ESI components
- Set up Payroll Entry for monthly processing
- Auto-generate EPF ECR (Electronic Challan cum Return) format
- Generate Form 16 from salary slips at year end
- Attendance integration with biometric device via API
        """,
        "tags": ["labour_law", "shop_establishment", "epf", "esic", "compliance"],
        "priority": "medium"
    },
    {
        "title": "APMC Act and Trade Licensing for Agricultural FMCG Commodities",
        "content": """
APMC ACT COMPLIANCE FOR AGRICULTURAL COMMODITY TRADERS

FMCG distributors dealing in agricultural commodities (pulses, grains, spices, edible oils, etc.) must comply with the Agricultural Produce Market Committee (APMC) Act, which varies significantly by state. Post the 2020 Farm Acts debate, states have diverged in their approach.

STATE-WISE APMC STATUS:
- States like Maharashtra, Karnataka, Gujarat still have active APMC mandis
- Uttar Pradesh, Bihar, Madhya Pradesh have reformed or abolished APMC
- Traders dealing across state borders must check destination state rules
- Some states require separate mandi license for each commodity category

MANDI LICENSE (WHERE APPLICABLE):
- License from local APMC market committee
- Fee based on turnover and commodity type (typically 0.5%–2% market fee)
- Renewal annual, linked to mandi arrival register
- Weighbridge/weighment slips mandatory for each transaction

COMMODITY-SPECIFIC REGULATIONS:
- Edible Oils: PFA Act compliance, ISI or Agmark certification verification
- Spices: Spices Board registration for exporters, FPO mark verification for domestic
- Pulses and Grains: State government stock holding limits (vary during inflation/shortage periods)
- Sugar: Controlled commodity, linked to allocated quota from sugar mills

ESSENTIAL COMMODITIES ACT WATCH:
- Government can impose stock limits during scarcity
- FMCG distributors must report stock positions to district collector when directed
- Violations attract criminal prosecution, so real-time stock visibility is critical

ERPNext FOR COMMODITY COMPLIANCE:
- Maintain commodity-wise stock in separate warehouses
- Generate stock position reports at item category level
- Stock limit alerts via ERPNext notification system
- Purchase order linked to APMC license fields for audit trail
        """,
        "tags": ["apmc", "agricultural_commodities", "mandi_license", "compliance", "fmcg"],
        "priority": "medium"
    }
]

TRADING_FMCG_BEST_PRACTICES = [
    {
        "title": "Inventory Management Best Practices for FMCG Distribution",
        "content": """
INVENTORY MANAGEMENT FOR FMCG DISTRIBUTORS

FMCG distribution is defined by high SKU count, short shelf life, and thin margins. Inventory accuracy directly impacts profitability. Best-in-class FMCG distributors maintain less than 0.5% inventory variance and 15–20 days of stock on hand.

CORE INVENTORY PRINCIPLES:
1. FEFO (First Expiry First Out): In FMCG, always prioritize FEFO over FIFO. Products with nearest expiry must be sold first regardless of when they were received.
2. ABC Analysis: Classify SKUs by revenue contribution — A items (top 10% SKUs, 70% revenue) get daily count, B items weekly, C items monthly.
3. Safety Stock: Maintain 7-day safety stock for A items, 3-day for B items to buffer demand variability.
4. Dead Stock Identification: Any item not moved in 30 days should trigger return-to-supplier or discount pricing action.

FMCG-SPECIFIC INVENTORY WORKFLOWS:
- Goods Receipt: Check physical count, batch number, and expiry before accepting. Reject any lot expiring within 30% of shelf life.
- Put-away: Assign bin locations by category; cold chain items moved to refrigerated section within 30 minutes of receipt.
- Picking: Picker uses FEFO logic; bin allocation must reflect this.
- Van Sales Replenishment: Van stock reconciled daily at route completion.

COMMON INVENTORY PROBLEMS AND FIXES:
- Problem: Phantom inventory (system shows stock but shelf is empty) → Fix: Cycle counts by category weekly
- Problem: Short expiry write-offs → Fix: Expiry alert 60 days before; initiate return or trade discount
- Problem: Slow-moving buildup → Fix: 30-day no-movement report reviewed every Monday
- Problem: Stockouts on A items → Fix: Auto-reorder points in ERPNext Item master

ERPNext CONFIGURATION:
- Enable Batch tracking for all FMCG items
- Set expiry date mandatory in Batch master
- Configure reorder level and reorder quantity per item
- Use Stock Ledger Entry reports for real-time movement visibility
- Enable UOM conversion (case to piece) for picking accuracy
        """,
        "tags": ["inventory_management", "fefo", "fmcg", "best_practices", "abc_analysis"],
        "priority": "high"
    },
    {
        "title": "Credit and Receivables Management for FMCG Distributors",
        "content": """
CREDIT MANAGEMENT FOR FMCG DISTRIBUTION

In FMCG distribution, credit to retailers is the norm — most distributors extend 7–30 days credit to their retail channel. Poor receivables management is the leading cause of working capital crises in distribution businesses.

CREDIT POLICY FRAMEWORK:
- Credit Limit: Assign credit limit per customer based on 3-month average purchase history (typically 1.5x monthly purchase)
- Credit Days: 7 days for new customers, 14 days for established, 21 days for modern trade
- Credit Stop: Auto-block further orders when outstanding exceeds credit limit by 20%
- Security: Collect post-dated cheques or personal guarantee for customers above ₹2 lakh limit

COLLECTION PROCESS:
- T+7: SMS/WhatsApp reminder on due date
- T+10: Phone call by salesperson
- T+14: Collection visit by area manager, issue credit note only after cash collection
- T+21: Escalate to management; issue legal notice if needed
- Never adjust credit notes against outstanding without written approval

DISTRIBUTOR-SPECIFIC CREDIT RISKS:
- Seasonal retailers go out of business after season; collect before season ends
- New retail openings — never extend credit for the first 2 orders
- Modern trade (supermarkets) — long credit cycles (45–60 days) but reliable; plan working capital accordingly
- Van sales — salesperson collecting cash is a fraud risk; use digital payments only

ERPNext RECEIVABLES SETUP:
- Set credit limit in Customer master (Credit Limit field)
- Enable "Block Invoice on Credit Limit Breach" in Account Settings
- Dunning document for automated overdue reminders (SMS/email)
- Customer-wise Accounts Receivable Aging report (0–30, 31–60, 61–90, 90+ days)
- Cheque tracking via Journal Entry with cheque date field
- Collection Dashboard: daily outstanding by salesperson territory
        """,
        "tags": ["credit_management", "receivables", "collections", "fmcg", "working_capital"],
        "priority": "high"
    },
    {
        "title": "Pricing and Scheme Management for FMCG Distributors",
        "content": """
PRICING AND TRADE SCHEME MANAGEMENT FOR FMCG DISTRIBUTION

FMCG pricing is multi-layered — distributors work within MRP constraints, receive distributor margins, pass on retailer margins, and manage trade schemes from principals (brand companies). Managing this complexity manually leads to billing errors and margin leakage.

FMCG PRICING STRUCTURE:
- MRP: Fixed by manufacturer, cannot be exceeded
- Distributor Landing Price = Principal's Invoice Price (after primary scheme deduction)
- Distributor Selling Price to Retailer = Landing Price ÷ (1 – Retailer Margin %)
- Typical margins: Retailer 8–15%, Distributor 3–8% depending on category

TYPES OF TRADE SCHEMES FROM PRINCIPALS:
1. % Discount Scheme: 2% on invoices above ₹50,000/month
2. FOC (Free of Cost) Scheme: Buy 10 get 1 free — most common in FMCG
3. Cash Discount: 0.5–1% for payment within 7 days
4. Quantity Slab Scheme: Different discount % at different purchase volumes
5. Special Seasonal Schemes: Festival offers, clearance schemes with expiry date

SCHEME ACCOUNTING PITFALLS:
- FOC goods received must be valued at purchase price for GST (not zero)
- Scheme discounts from principal: credit note must carry GST, not just adjustment
- Secondary schemes passed to retailers: must be tracked separately for margin calculation
- Expired scheme claims from principal: must be raised within claim period (usually 30 days after scheme end)

ERPNext PRICING SETUP:
- Create Price List per customer segment (Retailer, Modern Trade, Horeca)
- Use Pricing Rules for volume discounts and FOC schemes
- Promotional Scheme doctype for trade offers with validity dates
- Margin tracking: Item-level margin report showing actual vs. target margin
- Scheme Claim doctype: Track pending claims from principal, auto-alert on claim expiry
        """,
        "tags": ["pricing", "trade_schemes", "foc", "margin", "fmcg", "best_practices"],
        "priority": "high"
    },
    {
        "title": "Route Planning and Van Sales Workflow for FMCG Distribution",
        "content": """
ROUTE PLANNING AND VAN SALES OPERATIONS FOR FMCG DISTRIBUTORS

Van sales (also called pre-sales + delivery or ready-stock delivery) is the backbone of FMCG last-mile distribution in India. Efficient route planning directly impacts coverage, collection efficiency, and fuel costs.

ROUTE DESIGN PRINCIPLES:
- Divide territory into permanent journey plans (PJPs): each salesperson covers fixed routes on fixed days
- Route density: 40–80 outlets per route per day depending on outlet type (kirana vs. modern trade)
- Beat frequency: A-class outlets visited daily or 3x/week; B-class 2x/week; C-class weekly
- Route sequencing: Minimize backtracking; plan morning start near warehouse, end near collection-heavy zones

VAN SALES DAILY WORKFLOW:
1. Morning: Van loading based on previous day's pre-booking + buffer stock
2. Van dispatch: Stock transfer from warehouse to van (internal transfer in ERPNext)
3. Route execution: Salesperson visits outlets, takes orders and delivers from van
4. Payment collection: Collect against outstanding, issue receipt on mobile
5. End of day: Van return, stock reconciliation, cash/digital payment handover
6. EOD report: Sales, collection, new orders, complaints, outlet additions

KEY VAN SALES METRICS:
- Lines per call (LPC): Number of SKUs sold per outlet visit, target > 5
- Productive calls %: Outlets that made a purchase vs. total visited, target > 70%
- Collection efficiency: Amount collected vs. amount due on route
- Van fill rate: % of pre-booked orders fulfilled from van stock

ERPNext CONFIGURATION FOR VAN SALES:
- Create van as separate warehouse (Stock Transfer to van = Delivery Note against van warehouse)
- Territory and Route master linked to salesperson and customer
- Mobile Sales app (ERPNext mobile or Frappe-based) for in-field order capture
- Daily reconciliation report: van opening stock + purchases – sales = closing stock
- GPS or last-mile delivery tracking integration via custom fields
        """,
        "tags": ["van_sales", "route_planning", "fmcg", "last_mile", "pjp", "best_practices"],
        "priority": "high"
    },
    {
        "title": "Returns and Damage Handling in FMCG Distribution",
        "content": """
RETURNS, DAMAGE, AND EXPIRY HANDLING FOR FMCG DISTRIBUTORS

Product returns are an unavoidable and high-cost activity in FMCG distribution. Industry average: 2–5% of gross sales are returned. Effective returns management protects margin and maintains retailer relationships.

CATEGORIES OF RETURNS IN FMCG:
1. Expired Products: Goods past printed expiry date — must be pulled from market
2. Damaged Products: Transit damage, warehouse mishandling — often not claimable
3. Market Returns (Rate Difference): Retailer returns stock due to price revision or scheme change
4. Short Expiry Returns: Slow-moving items with less than 30% shelf life remaining
5. Saleable Returns: Good condition goods returned due to excess ordering

RETURN-TO-PRINCIPAL PROCESS:
- Maintain claims register: batch number, expiry, quantity, reason, value
- Submit claim to principal's sales team within claim window (typically 30–90 days depending on company)
- Principal issues credit note after their claims team verifies
- GST on credit note: must carry original GST rate, not net-of-tax credit
- Rejected claims: escalate within 7 days or write off with management approval

HANDLING EXPIRED GOODS:
- Segregate expired stock in a separate "quarantine" zone in warehouse
- Do not mix expired stock with saleable inventory
- Disposal must be documented (destruction certificate or principal pickup acknowledgment)
- GST reversal required if ITC was claimed on expired goods that are destroyed

ERPNext RETURN WORKFLOW:
- Purchase Return (Debit Note) for goods returned to principal
- Sales Return (Credit Note) for goods received back from retailers
- Batch-tracked returns: system validates expiry date at return entry
- Separate warehouse/bin for damaged/quarantine stock
- Claims tracker: custom doctype to track principal claims with status (raised, approved, received)
- Write-off journal entry for non-recoverable damaged or expired stock
        """,
        "tags": ["returns", "expiry", "damaged_goods", "claims", "fmcg", "best_practices"],
        "priority": "medium"
    }
]

TRADING_FMCG_ERPNEXT = [
    {
        "title": "ERPNext Module Setup for FMCG Distribution",
        "content": """
ERPNEXT MODULE CONFIGURATION FOR FMCG DISTRIBUTORS

CRITICAL MODULES TO ENABLE:
1. Stock (Inventory Management) — Core for all trading businesses
2. Buying (Purchase Management) — For principal company orders and supplier POs
3. Selling (Sales Management) — Customer invoicing and order processing
4. Accounts (Financial Accounting) — GST, reconciliation, P&L
5. CRM — Customer master, territory, salesperson management

KEY DOCTYPES FOR FMCG DISTRIBUTION:
- Item Master: Enable "Has Batch No" and "Has Expiry Date" for all FMCG items
- Batch: Stores batch number, manufacturing date, expiry date
- Warehouse: Create separate warehouses for: Main Store, Cold Store, Van 1, Van 2, Quarantine
- Customer: Fields for territory, salesperson, credit limit, credit days, route
- Supplier: Fields for principal company, distributor territory, scheme eligibility
- Price List: Create separate lists for Retailer, Modern Trade, Horeca, Institution

RECOMMENDED CUSTOM FIELDS:
- Item: FSSAI Category (food/non-food), HSN Code (pre-filled), Brand
- Customer: Beat/Route Code, Outlet Type (kirana/general/medical/supermarket), FSSAI No (for food retailers)
- Sales Invoice: Salesperson Route, Van No., E-Invoice IRN, QR Code
- Supplier: Principal Company, State License No., FSSAI License No.

CRITICAL SETTINGS:
- Accounts Settings: Enable "Make Payment via Journal Entry" for cheque tracking
- Stock Settings: Enable "Automatically Set Serial No Based on FIFO" 
- Selling Settings: Enable "Customer Credit Limit" block
- GST Settings: Configure GSTIN, HSN codes, E-Invoice API credentials

WORKFLOW FOR LIVE OPERATIONS:
Principal → Purchase Order → GRN (with batch/expiry) → Stock in Main Warehouse
→ Delivery Note to Van (Stock Transfer) → Sales Invoice to Retailer
→ Payment Collection → Bank Reconciliation → GSTR Filing
        """,
        "tags": ["erpnext_setup", "modules", "fmcg", "configuration", "doctypes"],
        "priority": "high"
    },
    {
        "title": "ERPNext Batch Tracking and Expiry Management for FMCG",
        "content": """
BATCH TRACKING AND EXPIRY MANAGEMENT IN ERPNEXT FOR FMCG

WHY BATCH TRACKING IS NON-NEGOTIABLE IN FMCG:
- FSSAI requires traceability from supplier to end consumer
- Expired batch recall requires knowing which batches went where
- Claim management requires batch-level proof with principal companies
- GST compliance for returns requires original batch reference

SETTING UP BATCH TRACKING IN ERPNEXT:
1. In Item master: Check "Has Batch No" and "Has Expiry Date"
2. In Stock Settings: Enable "Use Naming Series for Batch ID" for system-generated batch IDs
3. Batch Naming Convention: Suggested format — ITEM-DDMMYY-SEQ (e.g., TATA-SALT-010125-001)
4. In Batch master: Fill Batch ID, Manufacturing Date, Expiry Date, Supplier Lot No.

RECEIVING GOODS WITH BATCHES:
- Purchase Receipt → select/create batch for each line item
- Multiple batches can be received in one Purchase Receipt (add rows)
- System validates: expiry date must be filled if item has "Has Expiry Date" checked

FEFO PICKING CONFIGURATION:
- ERPNext does not auto-enforce FEFO by default
- Workaround: Use "Pick List" doctype; sort by batch expiry date
- Custom script: auto-populate batch with earliest expiry on Pick List creation
- Alternative: Use Batch-wise Balance Sheet report to manually identify FEFO batch before picking

EXPIRY ALERT SETUP:
- Go to Item → set "Shelf Life In Days"
- Create a scheduled ERPNext alert/notification for batches expiring within 30, 15, 7 days
- Generate "Batch-Wise Expiry Status" report weekly for manual review
- Quarantine expired batches using "Quality Inspection" rejection workflow

RETURNS AND EXPIRY WRITE-OFF:
- Stock Entry (Material Issue) to write off expired stock from Quarantine warehouse
- Expense account: "Inventory Write-off" or "Spoilage and Waste"
- GST ITC reversal required via GSTR-3B if expired goods on which ITC was claimed
        """,
        "tags": ["batch_tracking", "expiry_management", "fefo", "fmcg", "erpnext"],
        "priority": "high"
    },
    {
        "title": "ERPNext Sales and Delivery Workflow for FMCG Distributors",
        "content": """
ERPNEXT SALES AND DELIVERY WORKFLOW FOR FMCG DISTRIBUTION

STANDARD FMCG SALES FLOW IN ERPNEXT:
Sales Order → Pick List → Delivery Note → Sales Invoice → Payment Entry

STEP-BY-STEP CONFIGURATION:

1. SALES ORDER:
   - Created by salesperson from route (mobile or desktop)
   - Customer auto-populates: price list, territory, salesperson, payment terms
   - Credit check triggers on Save if outstanding > credit limit
   - Expected Delivery Date mandatory for dispatch planning

2. PICK LIST:
   - Generated from Sales Order (single or bulk)
   - Assign picker and target warehouse
   - Print pick list for warehouse team
   - Pick List picks from correct batch (FEFO sorting required via customization)

3. DELIVERY NOTE:
   - Created from Pick List or directly from Sales Order
   - Vehicle No. and Driver fields (add custom fields)
   - E-Way Bill auto-generated for goods > ₹50,000 inter-state or ₹1 lakh intra-state (state-specific)
   - Print delivery challan for goods in transit

4. SALES INVOICE:
   - Created from Delivery Note (most common in FMCG)
   - Or POS invoice for counter sales
   - Auto-populated: items, quantities, prices from Delivery Note
   - E-Invoice IRN generated on submission (if applicable)
   - Print: Tax Invoice with QR code

5. PAYMENT ENTRY:
   - Mode of Payment: Cash, Cheque, UPI, NEFT/RTGS
   - Cheque payments: Record cheque number, date, bank in Payment Entry
   - Partial payments: Allocate against oldest invoice first (FIFO allocation)
   - Advance payment: Adjust against future invoices

USEFUL ERPNEXT REPORTS FOR FMCG SALES:
- Sales Person-wise Sales Summary
- Item-wise Sales History
- Customer Acquisition and Loyalty Report
- Delivery Note Trends
- Outstanding Receivables with Ageing
        """,
        "tags": ["sales_workflow", "delivery_note", "erpnext", "fmcg", "e_way_bill"],
        "priority": "high"
    }
]

TRADING_FMCG_PAIN_POINTS = [
    {
        "title": "Top Pain Points: Stock Visibility and Shrinkage in FMCG Distribution",
        "content": """
PAIN POINT: STOCK VISIBILITY AND SHRINKAGE IN FMCG DISTRIBUTION

PROBLEM DESCRIPTION:
FMCG distributors with multiple warehouses, multiple vans, and high SKU counts frequently face "phantom inventory" — the system shows stock but the shelf is empty, or vice versa. Shrinkage (theft, pilferage, miscounting) averages 0.5–2% of inventory value annually.

ROOT CAUSES:
- Stock transfers to vans not entered in system in real time
- Physical counting errors at goods receipt (rushed during peak deliveries)
- Salespersons giving informal discounts or extra goods not documented
- Expiry write-offs not entered promptly, causing ghost stock
- Multiple locations with no bin-level tracking

IMPACT ON BUSINESS:
- Customer orders fulfilled partially → lost sales, retailer dissatisfaction
- Excess purchasing due to invisible stock → working capital tied up
- Audit failures with principal companies during stock audits
- Year-end book vs. physical mismatch → unexplained losses

HOW ERPNext SOLVES THIS:
1. Real-time Stock Ledger: Every movement (GRN, Delivery, Transfer, Return) posts immediately
2. Warehouse-level visibility: Drill down by item, batch, warehouse in Stock Balance report
3. Van Stock Tracking: Van = Warehouse; transfer entries on van dispatch and return mandatory
4. Cycle Count via Stock Reconciliation: Weekly cycle counts by category, system auto-highlights variance
5. Batch-level trace: For any expiry or loss, trace by batch to identify source

PROCESS IMPROVEMENTS TO IMPLEMENT:
- Gate entry check: Security records inward/outward and matches against system GRN/DN
- Salesperson cannot create Delivery Note; warehouse team creates and hands over
- Mobile scanning of barcodes at receipt reduces counting errors
- End-of-day van reconciliation mandatory before system allows next day's transfer
- Monthly physical count: Full physical vs. system, variance > 0.1% triggers investigation
        """,
        "tags": ["inventory_shrinkage", "stock_visibility", "pain_points", "fmcg", "cycle_count"],
        "priority": "high"
    },
    {
        "title": "Top Pain Points: Payment Collection Delays in FMCG Distribution",
        "content": """
PAIN POINT: PAYMENT COLLECTION AND OVERDUE MANAGEMENT IN FMCG DISTRIBUTION

PROBLEM DESCRIPTION:
The most common financial crisis in FMCG distribution is the "collection gap" — the distributor must pay the principal company within 7–14 days (to avail cash discount and maintain relationship) but retailers pay in 21–30 days. This structural mismatch creates chronic working capital pressure.

TYPICAL SYMPTOMS:
- Overdue receivables growing month-on-month
- Salespersons booking new orders to meet targets without collecting old dues
- Management unaware of customer-level outstanding until banker calls
- Multiple partial payments misapplied, causing reconciliation confusion
- Postdated cheques bouncing, no follow-up system

WHY IT HAPPENS:
- No real-time visibility of outstanding by salesperson/route
- No hard credit stop — billing continues even when customer is overdue
- Collection not tracked as a KPI for sales team
- No digital payment incentive — cash still dominant in kirana channel

HOW ERPNext SOLVES THIS:
1. Customer Credit Limit Block: System prevents invoice creation when customer exceeds limit
2. Dunning Documents: Auto-send overdue reminders via email/SMS at configurable intervals
3. Ageing Report by Salesperson: Daily report showing 0–30, 31–60, 61–90, 90+ buckets by territory
4. Collection Entry on Mobile: Salesperson records payment on mobile app immediately upon receipt
5. Cheque Register: Tracks postdated cheques, sends alert 3 days before presentation date
6. KPI Dashboard: Collection efficiency % as a live dashboard metric for management

PROCESS CHANGES REQUIRED:
- Make collection target equal to sales target for each salesperson
- Weekly collection review meeting with territory-wise ageing report
- No new order for any customer with outstanding > 45 days
- Route manager must countersign collection receipts above ₹10,000
- Implement UPI QR code at point of collection to reduce cash handling
        """,
        "tags": ["payment_collection", "receivables", "overdue", "fmcg", "pain_points", "working_capital"],
        "priority": "high"
    }
]


# ============================================================
# WHOLESALE TRADING — 12 CHUNKS
# ============================================================

TRADING_WHOLESALE_COMPLIANCE = [
    {
        "title": "GST Compliance for Wholesale Traders: TCS, TDS, and E-Way Bill",
        "content": """
GST AND TAX COMPLIANCE FOR WHOLESALE TRADING BUSINESSES

Wholesale trading operates at higher transaction values than retail, triggering additional GST compliance requirements like TCS (Tax Collected at Source), TDS under GST, and mandatory e-way bill generation.

E-WAY BILL COMPLIANCE FOR WHOLESALERS:
- Mandatory for goods movement > ₹50,000 (inter-state) or ₹1,00,000 (intra-state for most states)
- Validity: Up to 100 km = 1 day; 100–300 km = 3 days; 300–500 km = 5 days
- Transporter ID or vehicle number mandatory at time of generation
- Consigner (seller) must generate e-way bill before goods leave premises
- Penalties for non-generation: ₹10,000 or tax amount, whichever is higher + goods seizure

TCS (TAX COLLECTED AT SOURCE) FOR WHOLESALE:
- Applicable for e-commerce operators collecting payments (not traditional wholesale)
- Not typically applicable to standard wholesale unless operating online marketplace
- If operating B2B marketplace: TCS @ 1% on net taxable value, file Form GSTR-8

TDS UNDER GST (SECTION 51):
- Applicable to government entities, PSUs, local authorities — not private wholesale
- If selling to government departments: buyer deducts 2% TDS on taxable value
- Seller claims TDS credit in GSTR-3B, reflected in GSTR-7A of buyer

INCOME TAX TDS APPLICABILITY FOR WHOLESALERS:
- Purchases from manufacturers > ₹50 lakh: Buyer (wholesaler) must deduct TDS @ 0.1% under Sec 194Q
- If turnover < ₹10 crore: Sec 194Q not applicable
- If paying commission to agents: TDS @ 5% under Sec 194H if commission > ₹15,000/year

ERPNext FOR WHOLESALE TAX COMPLIANCE:
- Configure TDS on Purchase for Sec 194Q (if applicable)
- E-Way Bill integration via NIC API — auto-generate from Delivery Note
- E-Way Bill validity alert: notification when expiry is approaching for in-transit goods
- GST returns reconciliation: match purchase register with GSTR-2B before ITC claim
        """,
        "tags": ["gst", "e_way_bill", "tds", "tcs", "wholesale", "compliance"],
        "priority": "high"
    },
    {
        "title": "Trade License, Weights and Measures Compliance for Wholesale",
        "content": """
TRADE LICENSE AND WEIGHTS & MEASURES COMPLIANCE FOR WHOLESALE TRADERS

TRADE LICENSE (MUNICIPAL):
Every wholesale business operating from a premises requires a trade license from the local municipal corporation or panchayat. This is separate from GST registration and shop establishment.

TRADE LICENSE REQUIREMENTS:
- Apply to municipal corporation within 30 days of business commencement
- Documents: premises ownership/lease deed, building plan, NOC from owner, ID proof
- Fee: Based on premises area and business type (typically ₹500–₹5,000/year)
- Renewal: Annual, usually before March 31 of each year
- Display: Physical certificate must be displayed at entrance

WEIGHTS AND MEASURES (LEGAL METROLOGY ACT, 2009):
Wholesale traders dealing in packaged commodities or using weighing equipment must comply.

PACKAGED COMMODITY RULES:
- All packaged goods must display: MRP, net weight, manufacturer details, FSSAI (if food), batch/mfg date
- Wholesale repacking of commodities must comply with Packaged Commodity Rules
- Penalty for non-compliant packaging: ₹25,000 to ₹1 lakh

WEIGHING EQUIPMENT COMPLIANCE:
- All commercial weighing scales must be verified and stamped by Legal Metrology Inspector
- Verification frequency: Annual for most scales
- Unstamped scales: ₹10,000–₹25,000 penalty + equipment seizure
- Digital weighbridges for heavy goods: Annual calibration from state-certified lab

IMPORT EXPORT CODE (IEC) FOR INTERNATIONAL WHOLESALE:
- Mandatory for any business importing goods or raw materials
- Issued by DGFT (Director General of Foreign Trade)
- One-time registration, no renewal needed
- Required for: customs clearance, foreign remittance, import of goods

ERPNext FOR WEIGHTS AND MEASURES:
- UOM conversion tables: case → piece → kg for accurate billing
- Weighbridge integration: Auto-import vehicle tare/gross weight into GRN
- Package size variants: manage 1kg, 5kg, 25kg packs as Item Variants
        """,
        "tags": ["trade_license", "weights_measures", "legal_metrology", "wholesale", "compliance"],
        "priority": "medium"
    },
    {
        "title": "Inter-State Trade Compliance for Wholesale Distributors",
        "content": """
INTER-STATE TRADE COMPLIANCE FOR WHOLESALE BUSINESSES

Wholesalers typically operate across multiple states or districts, creating additional compliance obligations. Understanding IGST, state-specific regulations, and documentation is essential.

IGST ON INTER-STATE SALES:
- All sales where supplier and buyer are in different states attract IGST
- IGST = CGST + SGST rates combined (e.g., 18% GST = 18% IGST inter-state)
- Place of supply determines whether CGST+SGST or IGST applies
- ITC of IGST can be used to offset CGST, SGST, or IGST liability

STATE REGISTRATION REQUIREMENTS:
- Business with operations or agents in multiple states may need GST registration in each state
- If only selling inter-state from one state: Single GSTIN sufficient
- If maintaining warehouse/depot in another state: Registration in that state mandatory
- If salesperson in another state books orders: May trigger nexus, consult tax advisor

MULTI-STATE STOCK TRANSFER (BRANCH TRANSFER):
- Stock sent from one state godown to another state godown of same company
- Treated as supply under GST (taxable even though no sale occurs)
- Must generate tax invoice at applicable rate for ITC credit at destination
- E-Way bill mandatory for every such transfer

CUSTOMS COMPLIANCE FOR IMPORT-ORIGIN GOODS:
- Wholesale traders importing goods must file Bill of Entry at customs port
- ITC on IGST paid at customs is claimable in GSTR-3B
- Basic Customs Duty (BCD) is not claimable as ITC — it's a cost
- Anti-Dumping Duty applicable on some categories; verify tariff code

ERPNext MULTI-STATE SETUP:
- Create separate Company or Branch for each state registration
- Configure GSTIN per company/branch in GST Settings
- Inter-company transactions for stock movement between states
- State-wise P&L via cost center structure
- HSN-wise tax mapping for all states using Tax Templates
        """,
        "tags": ["inter_state_trade", "igst", "branch_transfer", "wholesale", "multi_state"],
        "priority": "medium"
    }
]

TRADING_WHOLESALE_BEST_PRACTICES = [
    {
        "title": "Supplier Relationship and Purchase Negotiation for Wholesale Traders",
        "content": """
SUPPLIER MANAGEMENT AND PURCHASE NEGOTIATION FOR WHOLESALE BUSINESSES

Wholesale success depends on buying right. A 1% improvement in purchase price at wholesale volumes translates directly to margin improvement. Disciplined supplier management creates sustainable competitive advantage.

SUPPLIER CATEGORIZATION:
- Tier 1 (Strategic): Top 20% of suppliers by purchase value; negotiate annual contracts, priority allocation, extended credit
- Tier 2 (Preferred): Regular suppliers; quarterly reviews, standard credit terms
- Tier 3 (Transactional): Ad-hoc or spot purchases; no credit, COD or advance preferred

ANNUAL PURCHASE NEGOTIATION CHECKLIST:
- Price: Volume-linked pricing slabs; commit to minimum monthly off-take in exchange for best rate
- Credit Terms: Target 30–45 days credit from supplier (vs. 14–21 days to customers = positive working capital)
- FOB vs. CIF: For imported goods, negotiate CIF; for domestic, negotiate delivered price
- Returns Policy: Pre-agree % of purchase value allowed as return (typically 2–5%)
- Payment Terms: Early payment discount (0.5–1%); cash discount vs. credit — do the math

PURCHASE PLANNING BEST PRACTICES:
- Demand-based planning: 3-month moving average purchase + seasonal uplift
- Never buy more than 45 days of stock for any item (working capital discipline)
- For imported goods: Factor in 45–60 days lead time + customs clearance delays
- Opportunistic bulk buying: Only for non-perishables with > 6 months shelf life and clear demand

VENDOR PERFORMANCE TRACKING:
- On-time delivery %: Target > 90%
- Quality rejection rate: Target < 1%
- Invoice accuracy rate: Correct price, quantities, HSN — target 100%
- Claim settlement speed: Target < 15 days

ERPNext FOR SUPPLIER MANAGEMENT:
- Supplier Scorecard: Rate suppliers on delivery, quality, pricing quarterly
- Purchase Order with expected delivery date; track delays in PO Status report
- Supplier-wise purchase analysis: Monthly report on volume, value, price trends
- Outstanding payables by supplier: Know who you owe before they call you
        """,
        "tags": ["supplier_management", "procurement", "negotiation", "wholesale", "best_practices"],
        "priority": "high"
    },
    {
        "title": "Warehouse Operations and Space Optimization for Wholesale",
        "content": """
WAREHOUSE OPERATIONS AND SPACE MANAGEMENT FOR WHOLESALE BUSINESSES

Warehouse efficiency determines operating costs in wholesale. A well-designed warehouse can handle 30–40% more throughput with the same staff and space through better layout and process design.

WAREHOUSE LAYOUT PRINCIPLES:
- ABC Layout: Fast-moving (A) items near dispatch dock; slow-movers (C) in deep storage
- Vertical racking: Use height; most Indian warehouses underutilize vertical space
- Clear lanes: Minimum 3-foot aisle for hand trolley; 8-foot for forklift operations
- Receiving zone: Separate from dispatch; temporary holding before put-away
- Quarantine zone: Clearly marked area for damaged/expired/under-inspection goods

INWARD PROCESSING WORKFLOW:
1. Supplier vehicle arrival → Security gate entry with vehicle number and supplier name
2. Unloading into receiving dock
3. Physical count vs. purchase order — count before signing LR (lorry receipt)
4. Quality check: Visual inspection for damage, expiry date verification
5. Discrepancy: Note on LR; call supplier within 24 hours for shortage/damage claim
6. GRN entry in system with batch details
7. Put-away to designated bin location

OUTWARD (DISPATCH) WORKFLOW:
1. Sales Order/Delivery Note received from sales team
2. Pick list generated; picker picks goods from designated bins
3. Goods staged in dispatch dock; secondary verification against pick list
4. Loading on vehicle; LR issued
5. E-Way Bill generated before vehicle departure
6. Delivery Note submitted in system; stock deducted

WAREHOUSE KPIs FOR WHOLESALE:
- Receiving accuracy %: Physical match with PO (target 99%)
- Put-away time: Goods from dock to shelf within 4 hours
- Pick accuracy %: Items picked matching delivery note (target 99.5%)
- Dispatch TAT: Order to vehicle departure within 2 hours (for in-stock items)
- Space utilization %: Target 80–85% (above 90% = congested; below 70% = expensive)

ERPNext WAREHOUSE FEATURES:
- Bin/Rack locations in Warehouse master (Address field or custom fields)
- Stock Balance drill-down by warehouse → item → batch
- Put-away rules (custom development required) for automatic bin assignment
- Physical Inventory tool (Stock Reconciliation) for cycle counts
        """,
        "tags": ["warehouse", "operations", "space_optimization", "wholesale", "logistics"],
        "priority": "high"
    },
    {
        "title": "Working Capital Management for Wholesale Trading",
        "content": """
WORKING CAPITAL MANAGEMENT FOR WHOLESALE TRADING BUSINESSES

Wholesale businesses are capital-intensive by nature. Goods must be purchased (and often paid for) before they are sold and collected. Managing the cash conversion cycle is the single most important financial discipline for a wholesale trader.

CASH CONVERSION CYCLE (CCC):
CCC = Days Inventory Outstanding + Days Sales Outstanding – Days Payable Outstanding
- Target CCC for healthy wholesale: < 45 days
- If CCC > 60 days: Business needs working capital financing or must reduce inventory/credit

LEVERS TO IMPROVE CASH CONVERSION CYCLE:

1. REDUCE DAYS INVENTORY OUTSTANDING (DIO):
- Cut slow-moving stock aggressively with discounts
- Increase purchase frequency, reduce order quantity (JIT where possible)
- Target: 20–30 days inventory for most categories

2. REDUCE DAYS SALES OUTSTANDING (DSO):
- Enforce credit limits; no billing when overdue
- Offer cash discount to incentivize early payment (0.5–1%)
- Switch large customers to digital payment for faster credit
- Target: 21–30 days for small wholesale; 30–45 for institutional buyers

3. INCREASE DAYS PAYABLE OUTSTANDING (DPO):
- Negotiate longer credit terms with suppliers (target 45–60 days)
- Use supplier credit as working capital — legitimate if used responsibly
- Pay on exact due date, not early (unless cash discount makes it worthwhile)

WORKING CAPITAL FINANCING OPTIONS:
- CC (Cash Credit) from bank: Secured against stock and debtors; 10–12% interest
- Invoice Discounting / Factoring: Sell invoices to financier for immediate cash; 1–2% fee per 30 days
- Supplier Credit: Most cost-effective; negotiate hard at annual review
- NBFC Short-term Loans: Higher cost, use only for gaps < 30 days

ERPNext FOR WORKING CAPITAL VISIBILITY:
- Cash Flow Statement: Monthly projection using open SO, PO, and payment terms
- Accounts Receivable Ageing vs. Accounts Payable Ageing side-by-side comparison
- Stock Ageing Report: Items not moved in 30/60/90 days — target for liquidation
- Projected Cash Flow tool (or custom dashboard) for 30-day liquidity planning
        """,
        "tags": ["working_capital", "cash_flow", "ccc", "wholesale", "finance", "best_practices"],
        "priority": "high"
    },
    {
        "title": "Multi-Location Inventory Management for Wholesale",
        "content": """
MULTI-LOCATION INVENTORY AND STOCK TRANSFER FOR WHOLESALE BUSINESSES

Many wholesale businesses operate from multiple godowns, branches, or regional distribution points. Managing stock across locations without confusion requires disciplined processes and system support.

MULTI-LOCATION COMMON CHALLENGES:
- Salesperson doesn't know which location has stock → double-promising to customers
- Head office can't see real-time position at branch locations
- Stock transfer between locations not tracked → mysterious shrinkage
- Purchases made at one location for another → billing and GST confusion

STOCK TRANSFER FRAMEWORK:
INTERNAL TRANSFER (Same GSTIN, same state):
- Stock Transfer via Material Transfer (Stock Entry) — no GST implication
- Must create a Delivery Challan for goods in transit (not a tax invoice)
- E-Way Bill required if goods value > threshold even for internal transfers
- Receiving location acknowledges receipt in system within 24 hours

BRANCH TRANSFER (Different state or different GSTIN):
- Must be treated as a taxable supply — issue Tax Invoice at applicable GST rate
- Receiving branch claims ITC on the invoice
- Both entities must file independent GST returns
- Intercompany reconciliation required monthly

CONSIGNMENT STOCK TO STOCKIST:
- Goods placed with stockist remain on your books (consignment, not sale)
- Periodic reconciliation with stockist against their stock register
- Invoice raised only on actual sales made by stockist (consignment sales model)
- High audit risk if not documented properly; maintain signed consignment agreement

ERPNext MULTI-LOCATION SETUP:
- Each location = separate Warehouse in ERPNext (can be under one Company)
- Inter-warehouse Stock Entry for internal transfers
- Intercompany Sales/Purchase Invoice for different GSTIN branches
- Stock Projected Quantity report: Shows balance + PO incoming – SO committed, per warehouse
- Stock Reorder rules per warehouse with warehouse-specific reorder levels
- Branch-level P&L using Cost Centers (one cost center per location)
        """,
        "tags": ["multi_location", "stock_transfer", "godown", "wholesale", "branch_operations"],
        "priority": "high"
    }
]

TRADING_WHOLESALE_ERPNEXT = [
    {
        "title": "ERPNext Purchase to Pay Workflow for Wholesale",
        "content": """
ERPNEXT PURCHASE-TO-PAY (P2P) WORKFLOW FOR WHOLESALE BUSINESSES

STANDARD WHOLESALE P2P FLOW:
Purchase Order → Purchase Receipt → Purchase Invoice → Payment Entry

STEP-BY-STEP ERPNEXT CONFIGURATION:

1. PURCHASE ORDER (PO):
   - Raise PO per supplier; one PO can have multiple items
   - Set expected delivery date; auto-reminder 2 days before for follow-up
   - PO status: Draft → Submitted → Goods Received (auto-updates on receipt)
   - Email PO to supplier directly from ERPNext (SMTP configured)
   - Set "Per Ordered Qty" to track partial deliveries against one PO

2. PURCHASE RECEIPT (GRN):
   - Always created from PO (never standalone to maintain PO linkage)
   - If batch-tracked items: Fill batch number, mfg date, expiry date per line
   - Quality Inspection: Trigger inspection for items requiring QC before stock update
   - Multiple receipts against one PO possible (partial deliveries)
   - Landed Cost Voucher: Add freight, insurance, customs duty to item cost after receipt

3. PURCHASE INVOICE:
   - Created from Purchase Receipt (match invoice to GRN — 3-way match)
   - Supplier's invoice number and date must be entered (for GSTR-2B reconciliation)
   - ITC eligibility: Mark as "ITC Available" only for eligible purchases
   - GST category: Intra-state, Inter-state, SEZ, Reverse Charge — select correctly
   - Credit note from supplier: Create Debit Note against Purchase Invoice

4. PAYMENT ENTRY:
   - Select invoices to pay (oldest first)
   - Payment mode: NEFT/RTGS/Cheque/Cash
   - Bank account reconciliation: Match payment entries with bank statement monthly
   - Early payment discount: Apply discount on payment if within discount period

WHOLESALE-SPECIFIC ERPNEXT FEATURES:
   - Purchase Analytics: Supplier-wise, item-wise, period-wise purchase trends
   - GSTR-2B Reconciliation Tool: Match ERPNext purchase invoices with GSTR-2B
   - Outstanding Payables Ageing: Plan payments to avoid supplier credit freeze
   - Auto PO from Reorder Rules: System generates PO draft when stock hits reorder level
        """,
        "tags": ["purchase_workflow", "p2p", "grn", "erpnext", "wholesale"],
        "priority": "high"
    },
    {
        "title": "ERPNext Landed Cost, Valuation, and Margin Tracking for Wholesale",
        "content": """
LANDED COST AND INVENTORY VALUATION IN ERPNEXT FOR WHOLESALE

WHY LANDED COST MATTERS:
Most wholesale businesses record inventory at purchase invoice price but forget to add freight, handling, customs duties, and insurance. This understates true cost and overstates margin — leading to bad pricing decisions.

ERPNEXT LANDED COST VOUCHER:
The Landed Cost Voucher (LCV) distributes additional costs (freight, customs, handling) across items in a Purchase Receipt. This updates item valuation rate permanently in the system.

HOW TO USE LANDED COST VOUCHER:
1. After creating Purchase Receipt (GRN), create a new Landed Cost Voucher
2. Link the Purchase Receipt in "Purchase Receipts" table
3. Add costs in "Taxes and Charges" table:
   - Freight: ₹5,000 (charged by transporter)
   - Customs Duty: ₹8,000 (for imported goods)
   - Handling Charges: ₹1,500
4. Distribution Method: By Qty, By Amount, or By Weight
5. Submit: ERPNext recalculates valuation rate for each item in the linked GRN

EXAMPLE CALCULATION:
- Item: 100 kg Rice, Purchase Price ₹45/kg = ₹4,500
- Freight allocated: ₹300 (6.67% of total freight)
- Landed Cost: ₹4,800 / 100 kg = ₹48/kg
- If sold at ₹52/kg: Actual margin = 7.7% (not 13.3% as naive calculation suggests)

INVENTORY VALUATION METHODS IN ERPNEXT:
- FIFO (First In First Out): Default for most trading businesses; matches physical flow
- Moving Average: Smooths out price fluctuations; used in manufacturing, not ideal for trading
- LIFO: Not allowed under Indian GAAP/IND-AS

MARGIN REPORTING IN ERPNEXT:
- Gross Profit Report: Compares invoice selling price vs. stock valuation rate (FIFO cost)
- Item-wise Gross Profit: Drill down to see margin per SKU
- Customer-wise Gross Profit: Identify which customers are actually profitable
- Period Comparison: Q1 vs Q2 margin by category — spot margin trends early

PRO TIP: Run Gross Profit report monthly before finalizing pricing. Any item with GP < 5% needs immediate review — either cost has increased or selling price is stale.
        """,
        "tags": ["landed_cost", "valuation", "margin", "erpnext", "wholesale", "fifo"],
        "priority": "high"
    },
    {
        "title": "ERPNext Reporting for Wholesale Business Intelligence",
        "content": """
BUSINESS INTELLIGENCE AND REPORTING IN ERPNEXT FOR WHOLESALE

ESSENTIAL REPORTS FOR WHOLESALE MANAGEMENT:

DAILY OPERATIONS REPORTS:
- Stock Balance: Current inventory position by warehouse, item, batch
- Pending Purchase Orders: What is ordered but not yet received
- Pending Delivery Notes: What is sold but not yet dispatched
- Daily Cash and Bank Position: Opening + receipts – payments = closing balance
- Overdue Receivables: Customers past due date, sorted by amount

WEEKLY MANAGEMENT REPORTS:
- Sales Register: All invoices issued in the week, customer-wise
- Purchase Register: All purchase invoices in the week, supplier-wise
- Stock Movement Report: Receipts and issues by item in the week
- Collection Efficiency: Amount collected vs. amount due in the period
- Slow-Moving Items: Items with zero movement in the last 30 days

MONTHLY FINANCIAL REPORTS:
- Profit and Loss Statement: Gross margin, operating expenses, net profit
- Balance Sheet: Assets, liabilities, equity position
- Cash Flow Statement: Operating, investing, financing cash flows
- Accounts Receivable Ageing: 0-30, 31-60, 61-90, 90+ day buckets
- Accounts Payable Ageing: Know your payment obligations

MONTHLY COMPLIANCE REPORTS:
- GSTR-1 Summary: Tax collected on sales, by tax rate and HSN
- GSTR-3B Inputs: Tax collected – ITC claimed = Net tax payable
- E-Way Bill Register: All E-Way Bills generated in the month
- TDS Payable Summary: TDS deducted on purchases (if applicable)

ERPNext CUSTOM DASHBOARDS FOR WHOLESALE:
- Use ERPNext Dashboard feature to pin critical KPIs on home page:
  - Today's sales vs. target
  - Outstanding receivables total
  - Stock value by location
  - Top 5 overdue customers
  - Low stock items alert count
- Schedule auto-email of weekly reports to management on Monday morning
        """,
        "tags": ["reporting", "business_intelligence", "dashboards", "wholesale", "erpnext"],
        "priority": "medium"
    }
]

TRADING_WHOLESALE_PAIN_POINTS = [
    {
        "title": "Top Pain Points: Supplier Dependency and Supply Disruption in Wholesale",
        "content": """
PAIN POINT: SINGLE SUPPLIER DEPENDENCY AND SUPPLY DISRUPTION IN WHOLESALE

PROBLEM DESCRIPTION:
Many Indian wholesale businesses source 60–80% of their volume from a single supplier or manufacturer. When that supplier raises prices, changes terms, or faces production disruption, the wholesaler's entire business is at risk.

COMMON TRIGGERS FOR SUPPLY DISRUPTION:
- Manufacturer prioritizes larger distributors during shortage — smaller wholesaler gets reduced allocation
- Supplier changes credit terms suddenly (from 30 days to advance payment) due to own financial stress
- Quality issue at manufacturing plant triggers recall — entire batch inventory becomes worthless
- Supplier exits a product category or shuts down (especially post-COVID for several SME suppliers)
- Exclusivity taken away — manufacturer appoints additional distributors in your territory

IMPACT ON BUSINESS:
- Stockouts for customers → customer shifts to competitor who has supply
- Revenue drops 30–50% within 60 days when primary supplier disrupted
- Cash already deployed in advance payments to supplier — locked up
- Existing customer commitments unfulfilled → relationship damage

RISK MITIGATION STRATEGIES:
1. Supplier Diversification: For every top-5 product, maintain at least 2 qualified suppliers
2. Safety Stock: Higher than normal safety stock for critical items from concentrated suppliers
3. Supply Agreement: Signed minimum supply agreement with key supplier (legal protection)
4. Alternative Product Readiness: Identify substitute SKUs for each A-item; keep samples with customers
5. Supplier Financial Health Watch: Monitor news, market talk about key suppliers; early warning saves time

ERPNext FOR SUPPLY RISK MANAGEMENT:
- Supplier-wise purchase concentration report: Alert when one supplier > 40% of category purchase
- Alternate Item in Item master: Link substitute items for quick replacement
- Supplier performance tracking: Delivery reliability score; poor performers auto-flagged
- Pending PO report: Know how much is committed with each supplier before crisis hits
- Safety stock buffer field: Set higher reorder level for sole-sourced items
        """,
        "tags": ["supplier_risk", "supply_disruption", "single_source", "wholesale", "pain_points"],
        "priority": "high"
    },
    {
        "title": "Top Pain Points: Margin Erosion and Price Management in Wholesale",
        "content": """
PAIN POINT: MARGIN EROSION AND UNCONTROLLED DISCOUNTING IN WHOLESALE

PROBLEM DESCRIPTION:
Wholesale businesses frequently see gross margin shrinking quarter-on-quarter despite growing revenue. The typical cause is uncontrolled discounting by salespersons, buying at wrong prices, and inability to track true landed cost vs. selling price.

COMMON CAUSES OF MARGIN EROSION:
- Salesperson gives extra discount to close a deal — not tracked or approved
- Purchase team buys at spot price (high) due to stock-out pressure; no cost visibility before dispatch
- Freight not added to item cost → selling at what seems profitable but isn't
- Currency fluctuation for imported goods not updated in price list
- Schemes from suppliers (credit notes) not accounted for in margin calculation

MARGIN CALCULATION MISTAKES:
- Mistake: Margin = (Sale Price – Purchase Price) / Sale Price — ignores freight, loading, damage
- Correct: Gross Margin = (Sale Price – Total Landed Cost) / Sale Price
- Total Landed Cost = Purchase Price + Freight In + Customs/Duty + Loading/Unloading + Financing Cost

ERPNext SOLUTIONS FOR MARGIN PROTECTION:
1. Landed Cost Voucher: Add freight, duty, and incidentals to item cost at GRN stage — system tracks true landed cost
2. Pricing Rule with Minimum Margin: Set floor margin %; system blocks invoice if margin < threshold
3. Discount Approval Workflow: Any discount > 5% requires manager approval before invoice submission
4. Item-wise Margin Report: Real-time gross margin by item, customer, territory, salesperson
5. Price List Management: Quarterly price list review based on updated landed costs
6. Gross Profit report in ERPNext: Compare invoice selling price vs. valuation rate

EARLY WARNING SYSTEM:
- Alert: Any invoice with margin < 5% triggers manager notification
- Report: Weekly bottom-margin items report reviewed by purchasing team
- Process: Price revision cycle every quarter (or immediately on supplier price change)
        """,
        "tags": ["margin_erosion", "discounting", "landed_cost", "wholesale", "pain_points"],
        "priority": "high"
    }
]


# ============================================================
# RETAIL TRADING — 12 CHUNKS
# ============================================================

TRADING_RETAIL_COMPLIANCE = [
    {
        "title": "GST Compliance for Retail Businesses: POS, Composition Scheme",
        "content": """
GST COMPLIANCE FOR RETAIL TRADING BUSINESSES

Retail businesses have distinct GST considerations compared to wholesale — primarily around consumer-facing invoicing, composition scheme eligibility, and point-of-sale compliance.

COMPOSITION SCHEME FOR SMALL RETAILERS:
- Eligible: Retailers with turnover < ₹1.5 crore (₹75 lakh for special category states)
- Tax rate: 1% of turnover (for traders) — no separate GST charged to customer
- No ITC claimable on purchases
- Cannot sell outside state, cannot sell on e-commerce
- File quarterly return (CMP-08) and annual GSTR-4
- Suitable for: Local kirana stores, small standalone retailers

REGULAR GST FOR LARGER RETAILERS:
- HSN code mandatory on invoice for turnover > ₹5 crore (4-digit for < ₹5 crore, 6-digit for > ₹5 crore)
- B2C invoices: Simplified invoice allowed (no buyer GSTIN needed)
- B2C Large invoices: > ₹2.5 lakh inter-state — must report individual in GSTR-1
- POS transactions: Multiple small invoices can be consolidated in daily sales summary

POINT-OF-SALE (POS) COMPLIANCE:
- POS receipt must contain: Seller name, GSTIN, date, items, quantity, price, GST amount, total
- Serial cash register or POS billing software acceptable
- Electronic POS must have tamper-proof audit log
- For retail with mixed GST rates: System must correctly bifurcate into 5%, 12%, 18%, 28%

REVERSE CHARGE MECHANISM (RCM):
- If retailer purchases from unregistered supplier: Retailer must pay GST under RCM
- Applies to: Purchases from unregistered dealers (not exempted goods/services)
- File RCM declaration in GSTR-3B, Table 3.1(d)
- Can claim ITC on RCM if goods used for business (not personal consumption)

ERPNext POS SETUP:
- POS Profile: Configure per cashier/outlet with default customer, price list, warehouse
- POS Closing Voucher: Daily cash reconciliation
- Offline POS: ERPNext supports offline invoicing with sync when internet available
- HSN-linked Tax Templates auto-applied on item scan/selection
        """,
        "tags": ["gst", "pos", "composition_scheme", "retail", "compliance"],
        "priority": "high"
    },
    {
        "title": "Consumer Protection Act and Retail Compliance",
        "content": """
CONSUMER PROTECTION ACT 2019 AND RETAIL BUSINESS COMPLIANCE

Retail businesses selling directly to end consumers are subject to the Consumer Protection Act, 2019, which significantly expanded consumer rights and retailer obligations.

KEY CONSUMER RIGHTS THAT AFFECT RETAIL OPERATIONS:
- Right to Safe Products: No defective goods; retailer jointly liable with manufacturer
- Right to Information: Clear pricing, composition, expiry date on all products displayed
- Right to Redressal: Complaint resolution within 30 days; non-compliance = penalty
- Protection from Unfair Trade Practices: No false claims, bait-and-switch, misleading promotions

UNFAIR TRADE PRACTICE RISKS FOR RETAILERS:
- Selling above MRP: ₹10,000–₹1,00,000 penalty + imprisonment
- False sale claims ("50% off" without real original price): Penalized as misleading advertisement
- Charging for carry bags without display of price: Violation of packaged commodity rules
- Not giving receipt: Consumer can file complaint if invoice not issued

PRODUCT LIABILITY:
- Retailer can be held liable for harm caused by a defective product even if retailer didn't manufacture it
- Mitigation: Sell only from licensed and registered manufacturers; maintain purchase invoices as proof of supply chain
- Return Policy: Must honor manufacturer's warranty; clear exchange policy must be displayed

ONLINE RETAIL ADDITIONAL COMPLIANCE:
- E-Commerce entities must register as "E-Commerce Entity" or "Seller" on platform
- Mandatory display: Country of origin, delivery timelines, return/refund policy
- Dark patterns (trick UX to force purchase) banned by Consumer Affairs Department

ERPNext RETAIL COMPLIANCE TOOLS:
- Item master: MRP field enforced in POS — system prevents billing above MRP
- Sales return policy: Credit Note issuance process configured per return reason
- Customer complaint tracking: Quality Inspection or custom Complaint doctype
- Warranty tracking: Serial number linked to warranty start/end date in ERPNext
        """,
        "tags": ["consumer_protection", "mrp", "retail_compliance", "product_liability", "pos"],
        "priority": "medium"
    },
    {
        "title": "Fire NOC, Pollution NOC, and Retail Store Licensing",
        "content": """
FIRE NOC, POLLUTION CLEARANCE, AND PHYSICAL RETAIL LICENSING

Large retail stores (typically above 500 sq ft) and those handling flammable or chemical products require additional licenses from fire, pollution, and municipal authorities.

FIRE NOC (NO OBJECTION CERTIFICATE):
Required for: Retail stores above 500 sq m, malls, stores handling combustible goods, basement stores
- Issued by local fire department / state fire service
- Requires: Fire extinguishers (as per IS codes), smoke detectors, emergency exit signage, evacuation plan
- Annual inspection and renewal
- Processing time: 15–45 days

POLLUTION CLEARANCE:
Required for: Retailers using generators (DG sets), retail processing (bakeries, meat shops), chemical/paint retail
- Consent to Operate (CTO) from State Pollution Control Board
- Category "Green" industries (low pollution): Simplified registration
- Category "Orange/Red" (e.g., chemical retailers): Full EIA and inspection
- DG Set NOC: For DG sets above 15 kVA

FOOD BUSINESS OPERATOR ANNUAL AUDIT:
- FSSAI-licensed food retailers must undergo annual food safety audit
- Audit covers: Storage conditions, personal hygiene, pest control, temperature logs
- Rating system: A, B, C grades displayed publicly from 2025 onwards
- Non-compliance: License suspension or cancellation

BUILDING AND SIGNAGE PERMISSIONS:
- Shop signage: Local municipal body permission required for external signage
- Flex boards above a certain size require permissions in most cities
- Structural modifications (removing walls, adding mezzanine): Building plan approval from municipality

ERPNext COMPLIANCE CALENDAR:
- Add all license expiry dates as Events or as Tasks with reminders in ERPNext
- Assign compliance tasks to store manager as responsible employee
- Document storage: Attach scanned licenses to Company document in ERPNext
- Maintenance schedule: ERPNext Maintenance module for fire extinguisher, DG service intervals
        """,
        "tags": ["fire_noc", "retail_licensing", "pollution_clearance", "store_compliance"],
        "priority": "medium"
    }
]

TRADING_RETAIL_BEST_PRACTICES = [
    {
        "title": "Category Management and Planogram for Retail Stores",
        "content": """
CATEGORY MANAGEMENT AND SHELF SPACE OPTIMIZATION FOR RETAIL

Category management is the strategic discipline of managing product categories as business units to maximize profitability per square foot of shelf space. Indian retailers who implement category management typically see 10–15% improvement in gross margin.

CATEGORY MANAGEMENT FRAMEWORK:
1. DEFINE CATEGORIES: Group items by consumer decision-making logic (e.g., "morning breakfast," not just "cereals")
2. ASSESS PERFORMANCE: Gross margin per shelf foot, stockout frequency, inventory turns per category
3. SET CATEGORY ROLE: Destination (drives traffic), Routine (daily needs), Convenience (impulse), Seasonal
4. PLAN SPACE ALLOCATION: Allocate shelf space proportional to category revenue and margin contribution
5. OPTIMIZE ASSORTMENT: Remove slow-movers; add complementary items

PLANOGRAM BASICS:
- Eye level = buy level: Best-margin items at eye level (waist to shoulder height)
- Bottom shelves: Heavy items (oils, beverages) or items with own demand (economy packs)
- Top shelves: Slow-movers or reserve stock
- Checkout area: High-margin impulse items (chocolates, mints, small snacks)
- End caps (gondola ends): Promotional items or seasonal pushes — highest visibility

CATEGORY REVIEW PROCESS (MONTHLY):
- Items with < 3 turns/month: Review for delist or reposition
- Out-of-stock frequency > 2 times/month per item: Increase reorder quantity
- Shrinkage hotspots (CCTV review): Reposition small-ticket theft-prone items near cashier

ERPNext FOR CATEGORY MANAGEMENT:
- Item Group hierarchy: Create 3-level category structure (Department → Category → Sub-category)
- Category-wise sales report: Revenue, margin, turns by item group
- Reorder rules per item: Auto-alert when stock hits reorder level
- Item variants for size packs: Manage 1kg, 5kg packs under one item code
- POS category navigation: Cashier finds items faster with clean category structure
        """,
        "tags": ["category_management", "planogram", "shelf_space", "retail", "best_practices"],
        "priority": "high"
    },
    {
        "title": "Shrinkage Control and Theft Prevention for Retail",
        "content": """
SHRINKAGE CONTROL AND LOSS PREVENTION FOR RETAIL STORES

Retail shrinkage (inventory loss from theft, damage, admin error, vendor fraud) averages 1.4% of retail revenue in India. For a ₹1 crore/month store, that's ₹14 lakh/year in losses. Structured shrinkage control can reduce this by 50–70%.

SOURCES OF RETAIL SHRINKAGE:
1. External Theft (shoplifting): ~35% of total shrinkage
2. Employee Theft: ~28% — most damaging and hardest to detect
3. Vendor/Supplier Fraud (short deliveries): ~20%
4. Administrative Errors (wrong entry, wrong pricing): ~17%

SHOPLIFTING PREVENTION:
- CCTV: Full coverage with no blind spots; entrance, exit, and all aisles
- Security tagging: EAS (Electronic Article Surveillance) tags on high-value items (cosmetics, electronics accessories)
- Mirror placement in corners to eliminate blind spots
- Single-exit policy: All customers must exit through billing counter
- "Greet every customer" policy: Awareness of presence deters shoplifting

EMPLOYEE THEFT PREVENTION:
- Cashier accountability: Cashier shortfall > ₹200 in cash drawer = mandatory reporting
- Void and discount approval: Manager PIN required for every discount/return/void transaction
- Bag check at exit: All employee bags checked by security before leaving
- Rotation of staff: No single cashier at same till for more than 4 hours continuously
- Surprise cash counts: Random mid-shift cash reconciliation by supervisor

VENDOR FRAUD PREVENTION:
- Count before signing: Always count delivered goods before signing LR/delivery receipt
- Separate receiver and buyer: Person who raised PO should not be the one accepting goods
- Weight-based items: Weigh on calibrated scale at receiving dock; never accept supplier's declaration
- Invoice matching: GRN to supplier invoice before payment — 3-way match mandatory

ERPNext FOR SHRINKAGE CONTROL:
- Stock Reconciliation alerts: Any variance > 0.5% triggers automatic escalation
- POS return policies: Return requires supervisor approval and reason code
- GRN vs. PO variance report: Highlights short deliveries automatically
- Cashier-wise transaction report: Identify excessive voids/discounts by individual cashier
        """,
        "tags": ["shrinkage", "theft_prevention", "loss_prevention", "retail", "best_practices"],
        "priority": "high"
    },
    {
        "title": "Customer Loyalty Programs and Retail CRM",
        "content": """
CUSTOMER LOYALTY AND RETENTION STRATEGIES FOR RETAIL

Acquiring a new retail customer costs 5–7x more than retaining an existing one. Loyalty programs increase purchase frequency by 20–30% and basket size by 10–15% for Indian retail stores.

TYPES OF LOYALTY PROGRAMS FOR INDIAN RETAIL:
1. POINTS-BASED: ₹100 spend = 1 point; 100 points = ₹5 discount. Simple, universal.
2. TIER-BASED: Silver/Gold/Platinum based on annual spend. Tier upgrades unlock better discounts.
3. CASHBACK: Percentage of bill value credited to store wallet for future use (popular in grocery)
4. PUNCH CARD: Buy 10, get 1 free — simple for local stores without tech infrastructure
5. REFERRAL PROGRAM: Existing customer gets ₹50 credit when they refer a new customer who makes a purchase

LOYALTY PROGRAM DESIGN PRINCIPLES:
- Keep it simple: Customer must understand the benefit immediately
- Make it attainable: First reward within 1–2 visits (not after 6 months)
- Personalize: Birthday discount, anniversary offer, favorite product restock alert
- Mobile-first: WhatsApp integration for point balance, redemption — no app needed

CUSTOMER DATA CAPTURE AT POS:
- Capture mobile number at billing (minimum viable customer ID)
- Name optional; mobile links to purchase history
- Do not make signup mandatory — capture gradually over multiple visits
- OTP-based verification optional but reduces fake numbers

CUSTOMER SEGMENTATION (RFM ANALYSIS):
- Recency: When did they last buy?
- Frequency: How often do they buy?
- Monetary: How much do they spend?
- Champions: High R, F, M — protect, reward
- At-Risk: Were champions, now declining — re-engage with offer
- Lost: No visit in 90+ days — win-back campaign

ERPNext CRM FOR RETAIL:
- Customer master with mobile number as primary identifier
- Loyalty Program doctype: Configure point accrual and redemption rules
- Customer purchase history: All invoices linked to customer profile
- Birthday/anniversary automation: Send WhatsApp via integration when date matches
- RFM segmentation via custom report or Python script on ERPNext data
        """,
        "tags": ["loyalty_program", "crm", "customer_retention", "retail", "rfm"],
        "priority": "medium"
    },
    {
        "title": "Retail Store Operations: Opening, Closing, and Daily Checklists",
        "content": """
RETAIL STORE OPERATIONS: STANDARD OPERATING PROCEDURES

Consistent store operations across shifts and days create customer trust and operational efficiency. SOPs reduce dependence on individual staff and enable scale.

STORE OPENING CHECKLIST (30 MINUTES BEFORE OPENING):
- Cash drawer: Count opening float; confirm correct denomination breakdown
- POS system: Log in, verify all POS terminals online, test one sample transaction
- Lighting: All section lights working; highlight promotional areas
- Display: Check planogram compliance — all items in correct position
- Price tags: Verify price tags in place for all items; no missing or outdated tags
- Expiry check: Daily expiry scan of near-expiry items; remove from shelf if expired or < 7 days
- Cleanliness: All surfaces dusted, floors mopped, entrance clean
- Staff positions: All scheduled staff confirmed and assigned to section

DAILY OPERATIONS STANDARDS:
- Restocking: Shelf fill-up by 10 AM from backroom; FEFO maintained
- Price change: Implement price changes before store opens (not during busy hours)
- Customer complaints: Record in complaint register; resolve same day or escalate
- Cash handling: No single cashier handles > ₹10,000 without supervisor co-signing

STORE CLOSING CHECKLIST:
- POS closing: Run end-of-day report; verify total sales vs. POS receipt total
- Cash reconciliation: Count cash; compare with POS cash sales; explain any variance
- Credit card / UPI reconciliation: Match terminal settlement report with POS
- Safe deposit: All cash above float locked in safe; key access logged
- Inventory: Verify no items left in trial rooms/non-display areas
- Lights, AC, security: Systematic shutdown per circuit; CCTV set to overnight recording
- Alarm and lock: Security armed; manager and guard both sign off on closing

ERPNext DAILY OPERATIONS INTEGRATION:
- POS Closing Voucher: Captures actual cash, expected cash, difference — flags variance
- Shift Report: Summary of sales, returns, discounts, by shift and cashier
- End-of-day Stock Snapshot: Trigger stock balance report at 10 PM daily
- Daily Sales Dashboard: Management sees D1 sales vs. previous day, vs. budget
        """,
        "tags": ["store_operations", "sop", "opening_closing", "retail", "daily_checklist"],
        "priority": "medium"
    }
]

TRADING_RETAIL_ERPNEXT = [
    {
        "title": "ERPNext POS Setup and Configuration for Retail",
        "content": """
ERPNEXT POINT OF SALE (POS) SETUP FOR RETAIL BUSINESSES

ERPNext has a built-in POS module that supports modern retail operations including touchscreen billing, barcode scanning, loyalty points, and offline mode.

INITIAL POS CONFIGURATION:

1. POS PROFILE:
   - Create one profile per terminal/cashier
   - Configure: Default warehouse, Price List, Customer (for walk-in), Payment methods
   - Set: Opening balance, print format for receipt, applicable taxes
   - Link: Cashier employee and allowed users

2. ITEM SETUP FOR POS:
   - All sellable items: Check "Is Sales Item" in Item master
   - Barcode: Enter EAN/UPC barcode in Item Barcode table (supports multiple barcodes per item)
   - Default UOM for retail: "Nos" or "Pcs" (not "Case" or "Carton")
   - POS display: Upload item image for touchscreen POS navigation

3. PAYMENT METHOD CONFIGURATION:
   - Cash: Default payment method, linked to Cash account
   - Card: Link to Card Payment account; configure payment gateway if online card processing
   - UPI: Configure UPI gateway or manual UPI entry with UTR number
   - Loyalty Points: Configure redemption value (e.g., 1 point = ₹0.05)

4. CUSTOMER MANAGEMENT AT POS:
   - Walk-in customer: Create default "Walk-in Customer" with no credit limit
   - Registered customers: Search by mobile number at counter; points auto-applied
   - New customer registration: Capture mobile + name at POS without slowing queue

POS DAILY WORKFLOW:
Opening → Log in to POS → Verify opening balance → Process sales (scan/select → qty → payment) → Print receipt → End-of-day close voucher → Match physical cash to system

ADVANCED POS FEATURES IN ERPNEXT:
- Offline mode: Continue billing without internet; sync when reconnected
- Returns at POS: Return items, issue cash or credit to loyalty wallet
- Hold Invoice: Park an incomplete invoice and return to it
- Price override: With manager permission only
- Discount at line or invoice level: Configurable by role
        """,
        "tags": ["pos", "erpnext_setup", "retail", "barcode", "configuration"],
        "priority": "high"
    },
    {
        "title": "ERPNext Inventory Replenishment and Reorder Automation for Retail",
        "content": """
INVENTORY REPLENISHMENT AND REORDER AUTOMATION IN ERPNEXT FOR RETAIL

WHY AUTOMATED REORDERING IS ESSENTIAL FOR RETAIL:
Retail stores carry 500–5,000 SKUs. Manual reordering is unreliable — items stock out before someone notices. ERPNext's reorder system can automate purchase requests and reduce stockouts by 60–80%.

SETTING UP REORDER LEVELS IN ERPNEXT:

Step 1: Item Master → Reorder section:
- Reorder Level: Stock quantity that triggers a Material Request (e.g., 10 units)
- Reorder Quantity: How much to order when triggered (e.g., 50 units)
- Set per warehouse: Different reorder levels for Main Store vs. Display Floor

Step 2: Enable Auto Material Request:
- Manufacturing Settings → "Raise Material Request when stock reaches reorder level"
- Runs as a scheduled background job (daily by default)
- Auto-creates Material Request in Draft status for review

Step 3: Material Request to Purchase Order:
- Review auto-generated Material Requests daily (takes 5 minutes)
- Approve and convert to Purchase Order per supplier
- Supplier-wise PO auto-emails sent

REORDER LEVEL CALCULATION GUIDE:
- Reorder Level = (Average Daily Sales × Lead Time in Days) + Safety Stock
- Example: Item sells 5 units/day, supplier lead time 3 days, safety stock 7 days
  - Reorder Level = (5 × 3) + (5 × 7) = 15 + 35 = 50 units
- Reorder Quantity = Economic Order Quantity or supplier minimum order quantity

SEASONAL ADJUSTMENT:
- Manually increase reorder levels 4 weeks before festive season (Diwali, Christmas)
- Reduce reorder levels for seasonal items after peak (avoid post-season overstock)
- Create a reminder task in ERPNext to review reorder levels in September (pre-festive)

SUPPLIER LEAD TIME TRACKING:
- ERPNext Purchase Order: Track actual delivery date vs. expected date
- Lead time history per supplier informs reorder level calculations
- Supplier with erratic delivery: Increase safety stock allocation

STOCKOUT PREVENTION REPORTS:
- Items Below Reorder Level: Daily report; items already at reorder level
- Projected Stock: Shows stock + incoming PO – pending SO commitments
- No-Sale Items: Items with zero sales in last 14 days (potential display/facing issue)
        """,
        "tags": ["reorder", "replenishment", "automation", "retail", "erpnext", "stockout"],
        "priority": "high"
    },
    {
        "title": "ERPNext Promotions, Offers, and Seasonal Sale Management for Retail",
        "content": """
MANAGING PROMOTIONS AND SEASONAL OFFERS IN ERPNEXT FOR RETAIL

Retail businesses run frequent promotions — weekend offers, festive discounts, buy-one-get-one (BOGO), clearance sales. ERPNext's Pricing Rules and Promotional Schemes handle these natively.

PRICING RULES IN ERPNEXT:
Used for: Automatic discounts, special rates, minimum quantity triggers

Configuration:
- Rule for: Item, Item Group, Customer, Customer Group, or Brand
- Conditions: Minimum quantity, minimum amount, applicable period (date range)
- Action: Discount %, Discount Amount, or Fixed Rate

COMMON RETAIL PROMOTION TYPES IN ERPNEXT:

1. FLAT DISCOUNT ON ITEM GROUP:
   - Pricing Rule: Item Group = "Apparel" → 20% discount
   - Valid from 01-Oct to 31-Oct
   - Applied automatically at POS when item scanned

2. BOGO (BUY 1 GET 1 FREE):
   - Promotional Scheme doctype → "Free Item" tab
   - Buy Qty: 1, Free Qty: 1, Free Item: Same or different item
   - Free item appears as separate line at zero price

3. QUANTITY-SLAB DISCOUNT:
   - Buy 1–5 units: 5% discount
   - Buy 6–10 units: 10% discount
   - Buy 11+ units: 15% discount
   - Configure in Pricing Rule with multiple slabs

4. MINIMUM INVOICE VALUE DISCOUNT:
   - Spend above ₹1,000 → 5% discount on whole bill
   - Pricing Rule: Min Amount = ₹1,000, Discount = 5%
   - Applied at invoice level, not line level

MANAGING PROMOTION CONFLICTS:
- Priority: Assign priority number to each Pricing Rule (lower number = higher priority)
- Only one rule applies per item by default (unless "Apply Multiple Pricing Rules" is enabled)
- Exclusions: Discount rule can exclude items already on clearance

SEASONAL SALE PREP IN ERPNEXT:
- Create all Pricing Rules 2 weeks before sale with future start date
- Test with dummy invoice before live date
- Auto-expire on sale end date — no manual intervention needed
- Post-sale analysis: Compare item-wise sales in sale period vs. prior period
        """,
        "tags": ["promotions", "pricing_rules", "bogo", "seasonal_sale", "retail", "erpnext"],
        "priority": "medium"
    }
]

TRADING_RETAIL_PAIN_POINTS = [
    {
        "title": "Top Pain Points: High Staff Attrition and Training Cost in Retail",
        "content": """
PAIN POINT: STAFF ATTRITION AND TRAINING BURDEN IN RETAIL OPERATIONS

PROBLEM DESCRIPTION:
Indian retail stores face monthly attrition of 5–10% among frontline staff (cashiers, floor staff, helpers). This translates to replacing 60–120% of frontline workforce annually. Each replacement costs ₹5,000–₹15,000 in recruitment, training, and lost productivity.

ROOT CAUSES OF RETAIL ATTRITION:
- Wages: Entry-level retail pays ₹8,000–₹12,000/month — insufficient in urban centers
- Working hours: Long shifts (10–12 hours) with few breaks; mandatory Sunday working
- No career path: Staff see no growth beyond cashier/floor supervisor in 3–5 years
- Seasonal layoffs: Festival hiring + post-season layoffs destroys loyalty
- No recognition: High performers not differentiated from average performers

COST OF HIGH ATTRITION:
- Recruitment cost: Job portal ads + consultant fees = ₹5,000–₹10,000 per hire
- Training time: New cashier takes 2–3 weeks to be independently productive
- Error rate: New staff make more billing errors, returns, and customer complaints
- Manager bandwidth: Team lead spends 40% of time training/monitoring new joinees instead of operations
- Customer experience: Unfamiliar faces reduce regular customer comfort and loyalty

RETENTION STRATEGIES THAT WORK:
1. Transparent incentives: Every staff member knows exactly how to earn extra ₹1,000–₹3,000/month
2. Meals and transport: High-value benefit with low cost to employer; ₹2,000–₹3,000/month in value
3. Festival bonus: Small Diwali/Eid/Christmas bonus signals respect and appreciation
4. Public recognition: "Staff of the Month" visible to all; peer recognition drives morale
5. Career ladder: Cashier → Senior Cashier → Section Lead → Supervisor → Store Manager — write it out

ERPNext HR FOR RETAIL:
- Attendance tracking: Biometric integration with ERPNext; late-comers flagged automatically
- Leave management: Self-service leave application via mobile reduces manager overhead
- Payroll consistency: On-time, accurate salary builds trust; ERPNext payroll automation prevents errors
- Performance appraisal: Quarterly review linked to KPIs; documented feedback reduces "gut feel" perception bias
- Attrition dashboard: Track monthly joinings vs. leavings; exit reason analysis by store and role
        """,
        "tags": ["attrition", "staff_retention", "hr", "retail", "pain_points"],
        "priority": "medium"
    },
    {
        "title": "Top Pain Points: Stock Outs and Over-Ordering in Retail",
        "content": """
PAIN POINT: STOCKOUTS AND EXCESS INVENTORY IN RETAIL STORES

PROBLEM DESCRIPTION:
Retail stores simultaneously suffer from stockouts on bestsellers (losing sales) and excess inventory on slow-movers (tying up cash). This contradiction is caused by intuition-based buying without data.

ROOT CAUSES:
- Buying based on "gut feel" of store owner or manager
- Seasonal demand patterns not modeled (Diwali rush, monsoon slowdown)
- Supplier minimum order quantities forcing over-buy on some items
- No reorder alerts — ordering only when shelf is visibly empty (too late)
- No vendor-managed inventory for top suppliers — all ordering manual

STOCKOUT IMPACT:
- Lost sale: Customer buys elsewhere and may not return
- Customer dissatisfaction: Erodes trust in store reliability
- Brand perception: Frequent stockouts signal poor management
- Indian kirana stockout rate: Estimated at 7–12% of SKUs on any given day

EXCESS INVENTORY IMPACT:
- Cash locked up in slow-moving goods
- Risk of expiry for food items
- Storage space consumed by non-contributing items
- Forced discounting to liquidate — margin loss

HOW ERPNext SOLVES THIS:
1. Reorder Levels: Set minimum stock level per item; system auto-generates Material Request when level hit
2. Demand Forecast: ERPNext has basic demand forecasting using moving average in "Production Plan" module — adaptable for retail
3. Stock Ageing Report: Identifies slow-movers by days-since-last-sale
4. ABC-XYZ Classification: A/B/C by value, X/Y/Z by demand variability — combined to create precise reorder policies
5. Seasonal Buffer: Add manual safety stock uplift for festive periods using bulk Material Request

PROCESS IMPROVEMENTS:
- Daily: Check reorder alerts in ERPNext and raise PO that morning
- Weekly: Review slow-mover report and initiate clearance discount
- Monthly: Review top 50 stockout incidents and adjust reorder levels
- Quarterly: Full assortment review — add new items, delist dead items
        """,
        "tags": ["stockout", "overstock", "demand_planning", "retail", "pain_points", "inventory"],
        "priority": "high"
    }
]


# ============================================================
# CROSS-CUTTING TRADING — 11 CHUNKS
# ============================================================

TRADING_CROSSCUTTING = [
    {
        "title": "GST Deep Dive: ITC Reconciliation and GSTR Filing for All Traders",
        "content": """
GST INPUT TAX CREDIT (ITC) RECONCILIATION FOR TRADING BUSINESSES

ITC reconciliation is the process of matching the ITC you claim in GSTR-3B with what your suppliers have reported in their GSTR-1 (which appears as GSTR-2B for you). Mismatches result in ITC reversal + 18% interest + penalties.

WHY ITC RECONCILIATION IS CRITICAL:
- You can only claim ITC on invoices that appear in GSTR-2B (auto-generated from supplier's GSTR-1)
- Supplier not filing GSTR-1 → invoice not in your GSTR-2B → ITC at risk
- GST Department auto-generates DRC-01A notices for ITC claimed but not in GSTR-2B

STEP-BY-STEP ITC RECONCILIATION PROCESS:
1. Download GSTR-2B for the month from GST portal (available after 14th of next month)
2. Export your purchase register from ERPNext (all supplier invoices in the month)
3. Match: Supplier GSTIN, Invoice Number, Invoice Date, Taxable Value, Tax Amount
4. MATCHED: Claim ITC confidently in GSTR-3B
5. IN GSTR-2B BUT NOT IN YOUR REGISTER: Check if you received goods; if yes, enter the purchase invoice
6. IN YOUR REGISTER BUT NOT IN GSTR-2B: Follow up with supplier to file their GSTR-1; do NOT claim ITC for now

ITC INELIGIBLE CATEGORIES (EVEN IF IN GSTR-2B):
- Personal use items or goods for owner/director personal consumption
- Motor vehicles (unless in transportation business)
- Food and beverages (unless in restaurant/hospitality business)
- Goods/services used for exempt supplies
- Club memberships

ERPNext ITC RECONCILIATION WORKFLOW:
- GST module → GSTR-2B Reconciliation tool
- Upload GSTR-2B JSON file from GST portal
- System auto-matches with purchase invoices in ERPNext
- Color-coded output: Green (matched), Red (unmatched), Yellow (partial match)
- Export mismatch report to share with suppliers for correction

GSTR FILING CALENDAR FOR TRADERS:
- GSTR-1: 11th of next month (monthly) OR quarterly for Quarterly Return Monthly Payment (QRMP) filers
- GSTR-3B: 20th of next month (monthly) OR quarterly for QRMP
- GSTR-9 (Annual Return): December 31 of next financial year
        """,
        "tags": ["gst", "itc_reconciliation", "gstr_2b", "gstr_filing", "trading", "compliance"],
        "priority": "high"
    },
    {
        "title": "Working Capital Finance Options for Indian Trading Businesses",
        "content": """
WORKING CAPITAL FINANCING FOR INDIAN TRADING BUSINESSES

Trading businesses are perpetually in need of working capital — money to buy stock before it's sold and collected. Understanding and optimizing financing options can reduce interest costs by 2–5% annually.

BANK WORKING CAPITAL PRODUCTS:

1. CASH CREDIT (CC):
   - Revolving credit facility against stock and debtors
   - Interest charged only on amount drawn (not sanctioned limit)
   - Typical rate: MCLR + 2–3% = 10–13% per annum
   - Eligibility: Audited financials, 2 years profitable track record, collateral
   - Documents: Stock statement (monthly), debtor statement (monthly), audited P&L

2. OVERDRAFT (OD):
   - Against property or FD security
   - Lower interest rate (8–10%) but requires collateral
   - No stock/debtor statement requirement
   - Good for: Established businesses with property as security

3. BILL DISCOUNTING (INVOICE DISCOUNTING):
   - Sell confirmed purchase orders / invoices to bank or NBFC for immediate cash
   - Rate: 0.5–1.5% per 30 days (approx 12–18% annualized)
   - No collateral needed if invoices are from creditworthy buyers (large companies)
   - Good for: Distributors selling to large corporates, modern trade, government

4. SUPPLY CHAIN FINANCE (REVERSE FACTORING):
   - Principal company (e.g., HUL, Nestlé) anchors credit for their distributors
   - Distributor gets payment from finance company immediately; principal pays finance company later
   - Rate: 9–11% (lower because anchor company's credit rating is used)

GOVERNMENT SCHEMES:
- CGTMSE (Credit Guarantee Fund): Collateral-free loans up to ₹2 crore for MSMEs
- MUDRA Loans: Shishu (< ₹50K), Kishor (₹50K–5L), Tarun (₹5L–10L)
- SIDBI assistance for small manufacturers/traders

ERPNext FOR LOAN MANAGEMENT:
- Loan doctype: Track loan amount, rate, EMI schedule
- Interest accrual: Monthly journal entry for interest payable
- Bank reconciliation: Match CC account drawings with invoices
- Stock Statement generation: Required monthly for CC account; auto-generate from ERPNext stock reports
        """,
        "tags": ["working_capital", "finance", "cash_credit", "bill_discounting", "trading"],
        "priority": "high"
    },
    {
        "title": "Digital Payments and UPI Integration for Trading Businesses",
        "content": """
DIGITAL PAYMENTS AND UPI INTEGRATION FOR TRADING BUSINESSES

India's payment landscape has shifted dramatically. UPI processes over 15 billion transactions/month. Trading businesses that embrace digital payments reduce cash handling costs, improve collection speed, and build better credit history.

DIGITAL PAYMENT OPTIONS FOR TRADING BUSINESSES:

1. UPI:
   - Best for: Retailer and customer collections, van sales collection
   - Zero MDR (Merchant Discount Rate) for merchant UPI transactions
   - Settlement: Same day or next day
   - Limit: ₹1 lakh per transaction (₹2 lakh for verified merchants)
   - Integration: UPI QR code sticker, UPI payment links, API integration

2. POS MACHINES (CARD SWIPE):
   - Best for: Retail counter, modern trade, organized retail
   - MDR: 0% for debit cards < ₹2,000; 0.9% for larger transactions; 1.5–2% for credit cards
   - Settlement: T+1 or T+2 business days
   - Required for: Businesses with monthly card volume justifying the machine cost

3. PAYMENT GATEWAY (ONLINE):
   - Best for: E-commerce, B2B portal payments, invoice payment links
   - Options: Razorpay, PayU, CCAvenue, Cashfree
   - MDR: 1.5–2.5% for card payments; 0% for UPI
   - Integration with ERPNext: Razorpay and Cashfree have ERPNext apps

4. NACH / ENACH (AUTO-DEBIT):
   - Best for: Recurring fixed payments from institutional customers
   - Process: Customer authorizes mandate; payment auto-debits on due date
   - Eliminates follow-up calls for regular customers

CASH MANAGEMENT (REDUCING CASH DEPENDENCY):
- Target < 20% of collections in cash; rest in digital
- For van sales: Mandate UPI-only collection for orders above ₹500
- Cash deposit: Same-day deposit of collections via CDM (Cash Deposit Machine)

ERPNext PAYMENT INTEGRATION:
- Razorpay integration: Payment link auto-sent on invoice email; payment auto-reconciles in ERPNext
- Bank Statement Import: Upload CSV/Excel bank statement → ERPNext auto-matches to payment entries
- UPI payment reference: Record UTR number in Payment Entry for audit trail
- POS card settlement: Daily terminal settlement report matched to POS Closing Entry
        """,
        "tags": ["digital_payments", "upi", "payment_gateway", "collection", "trading"],
        "priority": "high"
    },
    {
        "title": "Accounting Setup and Chart of Accounts for Trading Businesses",
        "content": """
ACCOUNTING SETUP AND CHART OF ACCOUNTS FOR TRADING BUSINESSES

A clean chart of accounts is the foundation of financial visibility. Most Indian SMB traders run with inadequate accounts, making it impossible to understand true profitability.

RECOMMENDED CHART OF ACCOUNTS FOR TRADING BUSINESSES:

ASSETS:
- Current Assets:
  - Bank Accounts (one per bank account)
  - Cash (one per petty cash location)
  - Accounts Receivable (one control account; details in customer ledger)
  - Stock in Trade (one per warehouse if needed for COGS separation)
  - Advance to Suppliers
  - Loans and Advances (given)
  - GST Input Tax Credit (CGST, SGST, IGST — separate)
  - TDS Receivable

LIABILITIES:
- Current Liabilities:
  - Accounts Payable (control account; details in supplier ledger)
  - GST Payable (CGST, SGST, IGST — separate)
  - TDS Payable
  - Employee Payroll Payable
  - Advance from Customers
  - Bank CC / OD Account

INCOME:
  - Sales Revenue (by product group or channel)
  - Other Income (interest received, scheme income from principals)

EXPENSES:
  - Cost of Goods Sold (separate account for purchases)
  - Freight and Logistics
  - Salaries and Wages
  - Rent
  - Utilities (Electricity, Water)
  - Marketing and Promotions
  - Vehicle Running Cost
  - Professional Fees (CA, legal)
  - Bank Charges and Interest
  - Depreciation
  - Inventory Write-off / Shrinkage

MONTHLY CLOSING CHECKLIST:
- Bank reconciliation complete for all bank accounts
- Debtors reconciliation: Aging matches general ledger
- Creditors reconciliation: AP aging matches supplier statements
- Stock reconciliation: System stock = physical count
- GST payable computed and matched to GSTR filing
- Depreciation journal entry posted
- Prepaid expenses and accruals posted

ERPNext ACCOUNTING CONFIGURATION:
- Enable multi-currency if dealing in imports/exports
- Configure fiscal year (April–March for most Indian companies)
- Set up cost centers per branch/location for P&L segmentation
- Enable budget control to flag expenses beyond approved limits
        """,
        "tags": ["accounting", "chart_of_accounts", "financial_setup", "trading", "erpnext"],
        "priority": "high"
    },
    {
        "title": "Logistics and Freight Management for Trading Businesses",
        "content": """
LOGISTICS AND FREIGHT MANAGEMENT FOR TRADING BUSINESSES

Freight is the 3rd largest cost for most trading businesses after product cost and salaries. Optimizing logistics can add 1–3% to net margin.

INBOUND FREIGHT (PURCHASING):
- Negotiate CIF (Cost Insurance Freight) from supplier when possible — transfers risk
- For FOB purchases: Develop a panel of trusted transporters for each lane
- Compare: Own transport vs. third-party logistics (3PL) for regular lanes
- Freight negotiation: Annual rate contract with transporters based on guaranteed volume
- Rate structure: Per KG or Per Km rate; full truck load (FTL) vs. less than truck load (LTL)

OUTBOUND FREIGHT (SALES):
- Zone-based freight matrix: Fixed freight charge per zone to customers
- Free delivery above threshold: Build freight cost into product price; offer "free delivery" above ₹500/₹1,000 order
- Van sales: Company-owned vans amortized over useful life; track per km cost including fuel, driver, maintenance
- 3PL for long-distance: Use specialized last-mile logistics companies for out-of-city orders

COURIER AND LAST-MILE FOR SMALL ORDERS:
- Blue Dart, Delhivery, Xpressbees for smaller parcel shipments
- Negotiate monthly contract rates vs. per-shipment walk-in rate (30–40% savings)
- COD (Cash on Delivery) shipments: Higher freight cost + COD charge; use only where necessary
- Tracking: Provide AWB/tracking number to customer; embed tracking link in delivery notification

FREIGHT COST ACCOUNTING:
- Inbound freight: Capitalize into item cost using Landed Cost Voucher in ERPNext
- Outward freight charged to customer: Credit to Freight Income account
- Outward freight borne by company: Debit to Freight and Logistics expense
- GST on freight: 5% GST on freight; claimable as ITC if freight input for business

ERPNext LOGISTICS FEATURES:
- Shipment doctype: Track courier AWB, transporter, vehicle number
- Delivery Note: Vehicle number, driver name, LR number custom fields
- Freight charges on Sales Invoice: Separate line item for freight charges
- Landed Cost Voucher: Distribute freight to item cost at GRN stage
- Transporter master: Maintain approved transporter list with rate contracts
        """,
        "tags": ["logistics", "freight", "transport", "landed_cost", "trading", "best_practices"],
        "priority": "medium"
    },
    {
        "title": "Salesperson KPIs, Incentive, and Performance Management for Traders",
        "content": """
SALESPERSON PERFORMANCE MANAGEMENT FOR TRADING BUSINESSES

Sales team management is a universal challenge across FMCG, wholesale, and retail trading. Without clear KPIs and fair incentive structures, top performers leave and bottom performers stay.

CORE SALESPERSON KPIs FOR TRADING:
1. Primary Sales Target: Total invoice value billed in the month (gross sales)
2. Collection Target: Cash/digital payment collected against outstanding (target = 95% of due)
3. New Customer Additions: Number of new customers who made first purchase this month
4. Active Customer %: % of assigned customer base that purchased at least once in the month (target > 70%)
5. Lines per Call (FMCG-specific): Average SKUs sold per customer visit (target > 5)
6. SKU Coverage: % of portfolio items sold to each customer

INCENTIVE STRUCTURE DESIGN:
- Base salary: Covers basic living; should be 60–70% of total compensation
- Sales incentive: Paid monthly on % of target achievement (typically 80–120% achievement zone pays incentive)
- Collection incentive: Separate bonus for collection efficiency > 90%
- New customer bonus: Fixed amount per new customer who completes 3 orders in first month
- Annual performance bonus: Based on full-year achievement

DO NOT PAY INCENTIVE ON:
- Sales to customers with > 60 days outstanding (incentive creates moral hazard)
- Sales where collection is not made (no payment = no incentive)
- Returns: Deduct from incentive calculation

ERPNext SALES PERFORMANCE TOOLS:
- Sales Person master: Assign targets, territory, customers to each salesperson
- Target vs. Achievement report: Real-time tracking in ERPNext
- Commission calculation: ERPNext can auto-calculate commission on invoices
- Salesperson-wise Receivables: See outstanding by salesperson territory
- Customer visit log: CRM module for recording outlet visits and outcomes
- Daily sales dashboard: Each salesperson sees their own scorecard on login
        """,
        "tags": ["sales_performance", "kpi", "incentive", "salesperson", "trading", "hr"],
        "priority": "medium"
    },
    {
        "title": "Technology Stack Recommendations for Indian Trading SMBs",
        "content": """
TECHNOLOGY STACK FOR INDIAN TRADING BUSINESSES (SMB CONTEXT)

Beyond ERPNext, a trading business needs a complementary set of tools for communication, payments, and operations. Here is the recommended stack for Indian SMBs.

CORE ERP:
- ERPNext (Frappe Cloud or self-hosted): Full business management — accounting, inventory, sales, purchasing, payroll
- Cost: Frappe Cloud starts at ₹4,000/month for small businesses; self-hosted is cheaper

ACCOUNTING AND TAX:
- LEDGERS by ClearTax / TallyPrime: Some businesses prefer Tally for accounting + ERPNext for ops; run dual system if needed
- ClearTax: GST filing, e-invoicing API, e-way bill management
- Income Tax filing: Winman CA-ERP or myITreturn for proprietorships

PAYMENTS:
- Razorpay: Payment gateway + payment links + UPI + subscription billing + payout to vendors
- Cost: 0% for UPI, 2% for cards (plus GST)
- BharatPe / PhonePe for Business: Simple UPI QR, good for retail POS environments

COMMUNICATION:
- WhatsApp Business API: Customer notifications, payment reminders, order confirmations
- Tool: Interakt, AiSensy, or Wati (₹2,500–₹7,000/month for 1,000 conversations)
- Email: Google Workspace (₹180/user/month) — professional email domain

DELIVERY AND LOGISTICS:
- Delhivery API / Shiprocket: For courier-based deliveries (D2C or e-commerce orders)
- Wahyd Freight / LoadShare: For truck-based logistics (B2B wholesale)

HR AND ATTENDANCE:
- keka / HROne / greytHR: Indian payroll software (EPF, ESIC, PT, TDS compliant)
- OR: ERPNext HR module for businesses already on ERPNext

E-COMMERCE:
- Shopify + Razorpay: For consumer-facing online store
- Udaan / IndiaMART: B2B marketplace for wholesale
- ERPNext integrated with WooCommerce/Shopify for inventory sync

ERPNEXT INTEGRATION PRIORITIES:
1. Razorpay: For auto-payment reconciliation
2. WhatsApp (Interakt): For customer communication from ERPNext
3. Shipping (Delhivery): Auto-create shipments from Delivery Note
4. GST / E-Invoice (NIC API): Auto-IRN generation
5. Biometric (eSSL/Realtime): Auto-attendance import to ERPNext payroll
        """,
        "tags": ["technology_stack", "tools", "software", "trading", "sme", "integration"],
        "priority": "medium"
    },
    {
        "title": "Staffing, Hiring, and Training for Trading Businesses",
        "content": """
STAFFING AND HUMAN RESOURCES FOR TRADING BUSINESSES

Trading businesses are labor-intensive — warehouse workers, salespersons, delivery staff, cashiers, and accounts staff. High attrition and unstructured hiring are common pain points.

KEY ROLES IN A TRADING BUSINESS (AND WHAT TO LOOK FOR):

1. WAREHOUSE SUPERVISOR:
   - Must know: Stock counting, GRN process, FIFO/FEFO, packing
   - Red flags: Cannot reconcile physical vs. system; history of shortages
   - Pay range: ₹15,000–₹25,000/month (Mumbai/Delhi); ₹10,000–₹18,000 (Tier 2)

2. SALESPERSON (FIELD):
   - Must know: Product knowledge, route management, basic calculation
   - Look for: Market knowledge, existing retailer relationships, honest character
   - Red flags: Excessive cash advances, erratic collection, working two jobs
   - Pay range: ₹12,000–₹20,000 base + incentive

3. ACCOUNTS EXECUTIVE:
   - Must know: Tally or ERPNext basics, GST returns, invoice verification
   - Look for: Tally/ERPNext experience, experience with GST compliance
   - Pay range: ₹15,000–₹28,000/month depending on city and experience

4. DELIVERY STAFF / DRIVER:
   - Must have: Valid driving license (LMV for tempo/van, HMV for truck)
   - Red flags: Expired license, prior accidents, cash handling irregularities
   - Pay range: ₹12,000–₹18,000/month + fuel allowance

TRAINING PRIORITIES FOR NEW JOINERS:
- Week 1: Product knowledge and company SOPs
- Week 2: System training (ERPNext for their role)
- Week 3: Supervised field/warehouse work
- Week 4: Independent work with daily manager check-in

ATTRITION MANAGEMENT:
- Track attrition rate monthly (target < 2% monthly = < 24% annual)
- Exit interview for everyone; identify top 3 reasons for leaving
- Retention: Timely salary, clear incentives, clean workplace, career path visibility

ERPNext HR FEATURES:
- Employee onboarding checklist with task assignment
- Leave management: Apply and approve leaves in system
- Payroll: Monthly salary processing with EPF/ESIC/PT auto-computation
- Appraisal module: Quarterly performance review linked to KPI scores
        """,
        "tags": ["hr", "staffing", "hiring", "training", "trading", "attrition"],
        "priority": "medium"
    },
    {
        "title": "Business Continuity and Risk Management for Trading Businesses",
        "content": """
BUSINESS CONTINUITY AND RISK MANAGEMENT FOR TRADING SMBs

Trading businesses face diverse risks — supplier failure, key employee leaving, fire/flood, cyber attack, economic disruption. Most Indian SMBs have no risk management plan and discover gaps only after an incident.

TOP RISKS FOR TRADING BUSINESSES:

1. SINGLE SUPPLIER DEPENDENCY:
   - Risk: Supplier stops supply → your business stops
   - Mitigation: Qualify at least 2 suppliers per category; maintain 2-week safety stock for critical items
   - ERPNext: Supplier-wise purchase concentration report

2. KEY PERSON RISK:
   - Risk: Owner, accounts head, or warehouse supervisor leaves → operations stall
   - Mitigation: Document all SOPs; cross-train 2nd person for each critical function
   - ERPNext: User access audit — no one should be the only person with admin access

3. FIRE / FLOOD RISK:
   - Risk: Warehouse fire destroys stock and records
   - Mitigation: Adequate stock insurance (Bharat Sookshma Udyam Suraksha Policy for MSMEs); cloud backup of ERPNext data
   - ERPNext: Cloud-hosted ERPNext automatically backed up; if self-hosted, configure daily offsite backup

4. CYBER RISK:
   - Risk: Ransomware, data breach, financial fraud via email
   - Mitigation: Two-factor authentication on all business accounts; no vendor payments via WhatsApp instructions alone; regular backup testing

5. CREDIT CONCENTRATION RISK:
   - Risk: Top 3 customers = 60% of revenue; one defaults → business crisis
   - Mitigation: Diversify customer base; no single customer > 20% of revenue; insure large outstanding via trade credit insurance

6. REGULATORY RISK:
   - Risk: GST notice, FSSAI license cancellation, income tax raid
   - Mitigation: Compliance calendar with alerts; monthly CA review; never compromise on GST filing

INSURANCE CHECKLIST FOR TRADERS:
- Stock insurance (fire, flood, burglary): ₹5,000–₹15,000/year per ₹1 crore stock value
- Trade credit insurance: Protects against buyer default
- Employee workmen's compensation insurance: Mandatory for some categories
- Vehicle insurance: Comprehensive for all company vehicles
        """,
        "tags": ["risk_management", "business_continuity", "insurance", "trading", "bcp"],
        "priority": "medium"
    },
    {
        "title": "ERPNext User Roles and Access Control for Trading Businesses",
        "content": """
ERPNEXT USER ROLES AND ACCESS CONTROL FOR TRADING BUSINESSES

Data security and role-based access is critical in trading businesses where financial fraud, inventory manipulation, and price override are real risks. ERPNext's permission system is powerful but requires thoughtful setup.

RECOMMENDED ROLE STRUCTURE FOR TRADING BUSINESSES:

1. OWNER / DIRECTOR:
   - Access: Full read access to all modules; approval authority
   - Should NOT have: Edit access to completed vouchers (audit trail must be preserved)
   - Key reports: P&L, Balance Sheet, Outstanding Receivables, Stock Value

2. ACCOUNTS MANAGER:
   - Access: Full Accounts module; view Stock; submit/cancel invoices
   - Restricted from: Modifying submitted payment entries without admin

3. SALES MANAGER:
   - Access: Sales Orders, Delivery Notes, Customers; view Stock; view (not edit) Pricing
   - Restricted from: Accounts, Payroll, supplier data

4. SALESPERSON (FIELD):
   - Access: Create Sales Orders only; view own customer list; view price list
   - Restricted from: Credit limit override, discount above X%, cancellation

5. WAREHOUSE STAFF:
   - Access: Create GRN, Stock Entry, Delivery Note; no financial entries
   - Restricted from: Modifying item prices, accessing customer financial data

6. PURCHASE MANAGER:
   - Access: Purchase Orders, GRN, Supplier master; view Stock
   - Restricted from: Payment Entry (separation of duties)

CRITICAL PERMISSION CONTROLS:
- Cancel Permission: Only Admin and Accounts Manager should cancel submitted documents
- Price Override: Only Sales Manager and above
- Credit Limit Override: Only Owner/Director
- Backdated Entries: Restrict to Accounts Manager; all backdated entries logged

AUDIT TRAIL BEST PRACTICES:
- Enable "Track Changes" for all critical doctypes (Sales Invoice, Payment Entry)
- Never share login credentials between users (one login per person)
- Review User Activity Log monthly for unusual access patterns
- Disable ex-employee accounts on last working day (not after)
        """,
        "tags": ["user_roles", "access_control", "security", "erpnext", "trading", "permissions"],
        "priority": "medium"
    },
    {
        "title": "Year-End Financial Closing and Audit Preparation for Traders",
        "content": """
YEAR-END FINANCIAL CLOSING AND AUDIT PREPARATION FOR TRADING BUSINESSES

March 31 is financial year-end for Indian companies. A structured year-end close ensures accurate financials, smooth audit, and compliant tax filing.

MARCH YEAR-END CLOSING CHECKLIST:

INVENTORY:
- Physical stocktake: Full physical count of all warehouses as of 31 March
- System reconciliation: Match physical count to ERPNext stock balance; post adjustments
- Valuation: Confirm FIFO valuation method applied consistently
- Write-off: Write off confirmed damaged/expired/obsolete stock before year-end

RECEIVABLES:
- Confirm balances: Send balance confirmation letters to top 20 customers (by outstanding value)
- Bad debt provision: Identify debts > 6 months old; provide for bad debts in accounts
- Reconcile ledger to aging report: Every customer balance must match aged receivables total

PAYABLES:
- Confirm balances with top 20 suppliers
- Ensure all purchase invoices for goods received before 31 March are posted
- Post accruals for expenses incurred but not yet invoiced (provision entries)

BANK:
- Bank reconciliation complete for all accounts as of 31 March
- Outstanding cheques > 6 months old: Reverse if not cleared

GST:
- GSTR-1 and GSTR-3B filed for all months of the year
- ITC reconciliation with GSTR-2B for all months
- Any ITC reversal for ineligible credits posted in March

FIXED ASSETS:
- Depreciation calculated and posted for the full year
- Fixed asset register reconciled to general ledger
- New additions and disposals properly documented

AUDIT DOCUMENTATION PACK (PREPARE IN ADVANCE):
- Audited financial statements (previous year)
- Bank statements (all accounts, April–March)
- GST returns (GSTR-1, GSTR-3B for all 12 months)
- TDS certificates received and issued
- Fixed asset register
- Stock statement as of 31 March
- All loan account statements

ERPNext YEAR-END TASKS:
- Run "Period Closing Voucher" in ERPNext to close financial year
- Create new fiscal year for April 1 start
- Opening balances carried forward automatically by ERPNext
- Generate audit reports: Trial Balance, P&L, Balance Sheet as of 31 March
        """,
        "tags": ["year_end_closing", "audit", "financial_closing", "trading", "compliance"],
        "priority": "high"
    }
]


# ============================================================
# MASTER STRUCTURE: All 50 Trading Chunks
# ============================================================

ALL_TRADING_CHUNKS = [
    # FMCG Distribution — 15 chunks
    {"f3iche": "trading", "industry": "FMCG Distribution", "kb_type": "compliance",
     "chunks": TRADING_FMCG_COMPLIANCE},
    {"f3iche": "trading", "industry": "FMCG Distribution", "kb_type": "best_practices",
     "chunks": TRADING_FMCG_BEST_PRACTICES},
    {"f3iche": "trading", "industry": "FMCG Distribution", "kb_type": "erpnext_setup",
     "chunks": TRADING_FMCG_ERPNEXT},
    {"f3iche": "trading", "industry": "FMCG Distribution", "kb_type": "pain_points",
     "chunks": TRADING_FMCG_PAIN_POINTS},

    # Wholesale — 12 chunks
    {"f3iche": "trading", "industry": "Wholesale", "kb_type": "compliance",
     "chunks": TRADING_WHOLESALE_COMPLIANCE},
    {"f3iche": "trading", "industry": "Wholesale", "kb_type": "best_practices",
     "chunks": TRADING_WHOLESALE_BEST_PRACTICES},
    {"f3iche": "trading", "industry": "Wholesale", "kb_type": "erpnext_setup",
     "chunks": TRADING_WHOLESALE_ERPNEXT},
    {"f3iche": "trading", "industry": "Wholesale", "kb_type": "pain_points",
     "chunks": TRADING_WHOLESALE_PAIN_POINTS},

    # Retail — 12 chunks
    {"f3iche": "trading", "industry": "Retail", "kb_type": "compliance",
     "chunks": TRADING_RETAIL_COMPLIANCE},
    {"f3iche": "trading", "industry": "Retail", "kb_type": "best_practices",
     "chunks": TRADING_RETAIL_BEST_PRACTICES},
    {"f3iche": "trading", "industry": "Retail", "kb_type": "erpnext_setup",
     "chunks": TRADING_RETAIL_ERPNEXT},
    {"f3iche": "trading", "industry": "Retail", "kb_type": "pain_points",
     "chunks": TRADING_RETAIL_PAIN_POINTS},

    # Cross-cutting Trading — 11 chunks
    {"f3iche": "trading", "industry": "Cross-cutting", "kb_type": "best_practices",
     "chunks": TRADING_CROSSCUTTING},
]


def count_chunks():
    total = 0
    for category in ALL_TRADING_CHUNKS:
        count = len(category["chunks"])
        print(f"  {category['industry']} | {category['kb_type']}: {count} chunks")
        total += count
    print(f"\n  TOTAL: {total} chunks")

if __name__ == "__main__":
    count_chunks()
