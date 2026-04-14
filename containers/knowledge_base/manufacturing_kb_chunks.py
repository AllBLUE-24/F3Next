# ============================================================
# F3Next Knowledge Base — MANUFACTURING F3ICHE
# Complete 60-chunk content for pgvector population
# Categories: Food Processing, Textile, Pharmaceutical, Cross-cutting
# Chunk size target: 400–600 tokens (~1,600–2,400 chars)
# ============================================================


# ============================================================
# FOOD PROCESSING — 18 CHUNKS
# ============================================================

MFG_FOOD_COMPLIANCE = [
    {
        "title": "FSSAI Central License and Food Manufacturing Compliance",
        "content": """
FSSAI COMPLIANCE FOR FOOD PROCESSING MANUFACTURERS

Food processing units are among the most heavily regulated manufacturing sectors in India. Any unit manufacturing, processing, packing, or storing food products must obtain FSSAI license under the Food Safety and Standards Act, 2006.

LICENSE TIERS FOR MANUFACTURERS:
1. BASIC REGISTRATION (< ₹12 lakh turnover): Simple registration, Form A, ₹100/year
2. STATE LICENSE (₹12 lakh – ₹20 crore): Form B, state-issued, ₹2,000–₹5,000/year, inspection required
3. CENTRAL LICENSE (> ₹20 crore, or multi-state, or certain product categories): Form B to FSSAI central, ₹7,500/year, mandatory for exporters, importers, and large FBOs

PRODUCT-SPECIFIC MANDATORY REQUIREMENTS:
- Packaged drinking water / mineral water: IS 14543 / IS 13428 certification + BIS license mandatory
- Infant foods: Additional FSSAI standards, no advertising restrictions
- Health supplements / nutraceuticals: FSSAI notification No. 2016 compliance
- Milk and dairy products: Pasteurization standards, microbial limits per FSS Act

MANUFACTURING HYGIENE STANDARDS (SCHEDULE 4, FSS ACT):
- Plant and premises: Pest-proof, food-grade surfaces, adequate drainage
- Equipment: Stainless steel or food-grade material, no lead/cadmium coatings
- Personnel hygiene: Health certificates for all food handlers, no infectious disease
- Water: Potable water as per IS 10500 for all food contact purposes
- Waste: Segregated waste disposal, no cross-contamination with food zones

MANDATORY DOCUMENTATION FOR FSSAI AUDIT:
- Raw material incoming register with supplier FSSAI details
- Production batch log with batch number, date, quantity, ingredients
- QC test results for each batch (internal or third-party lab)
- Temperature and humidity monitoring logs
- Pest control records with licensed pest control company certificates
- Employee health and training records

ERPNext FOR FSSAI COMPLIANCE:
- Batch master: Record batch number, production date, best-before date
- Quality Inspection doctype: Record QC test results per batch before dispatch
- Supplier master: Mandatory FSSAI license number field with expiry alert
- Recall procedure: Trace batch → identify all Sales Invoices where batch was dispatched
        """,
        "tags": ["fssai", "food_manufacturing", "central_license", "compliance", "hygiene"],
        "priority": "high"
    },
    {
        "title": "GST for Food Manufacturers: HSN Codes, Tax Rates, and Input Tax Credit",
        "content": """
GST COMPLIANCE FOR FOOD PROCESSING MANUFACTURERS

Food products have one of the most complex GST rate structures — spanning 0%, 5%, 12%, and 18% — making correct classification critical to avoid under/over-billing and ITC mismatches.

FOOD PRODUCT GST RATE GUIDE:
- 0% (Exempt): Unbranded/unpackaged rice, wheat, vegetables, fish, eggs, fresh milk, curd
- 5%: Branded/packaged cereals, flour, pulses, sugar, edible oils, packaged curd/lassi/buttermilk, frozen vegetables
- 12%: Ghee, butter, cheese, dry fruits (not cashews), fruit juices, sauces, jams, pickles
- 18%: Flavored milk, chocolates, cocoa products, instant food mixes, soups
- 28%: Carbonated beverages with fruit juice (removed from 0% in 2022)

CRITICAL DISTINCTION — BRANDED vs. UNBRANDED:
- If a food item is sold under a registered brand or trademark: GST applies
- Same product unbranded/unpackaged: Exempt
- Implication: Small food processors without registered brands may qualify for exemption

INPUT TAX CREDIT (ITC) ELIGIBILITY FOR FOOD MANUFACTURERS:
Eligible for ITC:
- Raw materials, packaging materials, machinery, equipment, factory consumables
- GST on freight for inward goods
- Capital goods used in production

NOT eligible for ITC:
- Food and beverages for employee consumption (staff canteen, tea/coffee)
- Personal vehicles (unless in transportation business)
- Works contract for construction of factory building (ITC blocked)

JOB WORK UNDER GST (SECTION 143):
- Food manufacturers often outsource processing (milling, packing, roasting) to job workers
- Goods sent to job worker: No GST if returned within 1 year (raw material) or 3 years (capital goods)
- Issue Delivery Challan for goods sent to job worker (not a tax invoice)
- Job worker charges GST on their service charges only (not on the principal's goods)

ERPNext GST SETUP FOR FOOD MANUFACTURERS:
- Item-wise tax templates: Assign correct GST rate to each finished good
- HSN code mandatory in Item master (6-digit for > ₹5 crore turnover)
- Job work flow: Subcontracting module in ERPNext handles job work with proper challan generation
- GSTR-1 auto-populated from submitted Sales Invoices
        """,
        "tags": ["gst", "hsn_codes", "food_manufacturing", "itc", "job_work", "compliance"],
        "priority": "high"
    },
    {
        "title": "BIS Certification, Agmark, and Product Certifications for Food Manufacturers",
        "content": """
PRODUCT CERTIFICATIONS AND QUALITY MARKS FOR FOOD MANUFACTURERS

Beyond FSSAI, many food products require additional certification from BIS (Bureau of Indian Standards), APEDA (for exports), or carry voluntary quality marks like Agmark.

BIS CERTIFICATION (ISI MARK) — MANDATORY FOR:
- Packaged drinking water (IS 14543) — No BIS = illegal to sell
- Mineral water (IS 13428) — Mandatory BIS certification
- Baby foods and weaning foods (IS 1656, IS 1657)
- Iodized salt (IS 252) — Mandatory for branded salt
- Edible refined oils — Not mandatory but important for market access

BIS CERTIFICATION PROCESS:
1. Application to BIS regional office with product specifications
2. Sample testing at BIS-recognized lab (NABL accredited)
3. Factory inspection by BIS officer
4. Grant of license: Fixed term (1–5 years), renewable
5. Annual surveillance visit + random market sample testing
6. Fee: Based on turnover (₹5,000–₹50,000+ per license)

AGMARK CERTIFICATION (VOLUNTARY BUT MARKET-LINKED):
- Administered by DACFW (Dept of Agriculture)
- Applicable to: Spices, pulses, edible oils, ghee, wheat products, honey
- Grades: Special, Grade A, Grade B based on quality parameters
- Required for: Government tenders, institutional supply, export to some countries
- Process: Application to State Agmark Lab, testing, grading, labeling approval

EXPORT CERTIFICATIONS:
- APEDA Registration: For export of scheduled agricultural products
- Spices Board: Mandatory for spice exporters; quality certificate per consignment
- MPEDA: For marine products export
- Organic: NPOP (National Programme for Organic Production) certification via accredited certifying body

ERPNext CERTIFICATION TRACKING:
- Add certification fields in Item master: BIS License No., Agmark Grade, Organic Cert No.
- Certification expiry alerts via ERPNext Notification rules
- Batch-level certification: Attach lab test report to Batch master
- Export documentation: Attach APEDA/Spices Board certificates to Delivery Note
        """,
        "tags": ["bis_certification", "agmark", "isi_mark", "food_export", "quality_certification"],
        "priority": "high"
    },
    {
        "title": "Environmental Clearance and Pollution Control for Food Processing Units",
        "content": """
ENVIRONMENTAL CLEARANCE AND POLLUTION COMPLIANCE FOR FOOD PROCESSING MANUFACTURERS

Food processing units generate effluents, solid waste, and air emissions that require regulatory clearance from the State Pollution Control Board (SPCB) and sometimes the Ministry of Environment.

INDUSTRY CATEGORY CLASSIFICATION:
- Green (Low Pollution): Dal mills, flour mills, fruit/vegetable processing, bakeries, tea processing
- Orange (Medium Pollution): Oil mills, rice mills, spice grinding, sugar processing, starch manufacture
- Red (High Pollution): Slaughterhouses, tanneries, distilleries, large dairy processing

CONSENT TO ESTABLISH (CTE):
- Required before constructing a new food processing plant
- Submit application to SPCB with project details, EIA report (for large units)
- Processing time: 2–6 months depending on category and state
- One-time permission; must be renewed to "Consent to Operate"

CONSENT TO OPERATE (CTO):
- Required before commencing production
- Annual renewal
- Site inspection by SPCB officer
- Conditions: Effluent Treatment Plant (ETP), air pollution control measures, solid waste management

EFFLUENT TREATMENT REQUIREMENTS:
- Discharge standards: BOD < 30 mg/L, COD < 250 mg/L, pH 6.5–8.5 (food processing)
- ETP mandatory for units discharging above prescribed limits
- Zero Liquid Discharge (ZLD): Mandatory in water-stressed areas (Maharashtra, Rajasthan, parts of Tamil Nadu)
- Daily effluent quality log: Must be maintained and submitted quarterly to SPCB

SOLID WASTE MANAGEMENT:
- Food waste: Segregated and disposed via approved composting/biogas facility
- Packaging waste: Extended Producer Responsibility (EPR) registration with CPCB mandatory from 2022 for packaged food manufacturers
- Hazardous waste (chemicals, lubricants): Disposal through CPCB-approved manifest system

ERPNext FOR ENVIRONMENTAL COMPLIANCE:
- Maintenance module: Schedule ETP servicing, air filter replacement, compliance visits
- Document manager: Store CTE, CTO, effluent test reports with expiry alerts
- Compliance calendar: SPCB return due dates, EPR submission deadlines
        """,
        "tags": ["pollution_control", "spcb", "cto", "etp", "food_manufacturing", "environment"],
        "priority": "medium"
    },
    {
        "title": "Labour Law Compliance for Food Processing Factories",
        "content": """
LABOUR LAW COMPLIANCE FOR FOOD PROCESSING MANUFACTURING UNITS

Food processing factories are subject to the Factories Act, 1948 and multiple central/state labour laws. Non-compliance attracts criminal prosecution, factory closure orders, and reputational damage.

FACTORIES ACT, 1948 — KEY REQUIREMENTS:
- Factory License: Mandatory before commencing production; issued by Chief Inspector of Factories
- Coverage: Any premises with 10+ workers using power, or 20+ workers without power
- Working hours: Max 48 hours/week, max 9 hours/day, mandatory weekly off
- Overtime: 125% of ordinary wages; max 50 hours overtime per quarter
- Annual leave: 1 day per 20 days worked (minimum)
- Health and Safety: Adequate ventilation, lighting, temperature control, sanitation

WELFARE PROVISIONS UNDER FACTORIES ACT:
- Canteen: Mandatory if 250+ workers
- Crèche: Mandatory if 30+ female workers with children below 6 years
- First Aid: One box per 150 workers; qualified first aider if 500+ workers
- Rest rooms: Mandatory provision

FOOD INDUSTRY SPECIFIC LABOUR ISSUES:
- Contract labour: Many food units use seasonal contract labour for harvesting/processing season; CLRA (Contract Labour Regulation and Abolition Act) compliance mandatory
- Contract Labour License: Principal employer must have license from Labour Commissioner
- Minimum Wages: Food processing has state-specific minimum wage schedules; varies by skill level (unskilled, semi-skilled, skilled)

SOCIAL SECURITY FOR FACTORY WORKERS:
- EPF: 12% employer + 12% employee on basic salary; mandatory if 20+ workers
- ESIC: 3.25% employer + 0.75% employee on gross wages; mandatory if 10+ workers; factory workers get full medical coverage
- Gratuity: 15 days salary per year of service; payable after 5 years
- Bonus: Minimum 8.33% of salary under Payment of Bonus Act (if 20+ workers)

ERPNext FACTORY PAYROLL SETUP:
- Department-wise payroll: Separate production, quality, admin departments
- Shift roster: ERPNext shift management for multi-shift food factories
- Contract worker management: Create Employee records with contract type = "Contract"
- EPF/ESIC computation: Auto-calculated in ERPNext payroll run
- ECR (EPF Electronic Challan cum Return): ERPNext generates ECR format for EPF filing
        """,
        "tags": ["factories_act", "labour_law", "epf", "esic", "food_manufacturing", "contract_labour"],
        "priority": "high"
    },
    {
        "title": "MSME Registration, PLI Scheme, and Government Incentives for Food Processors",
        "content": """
MSME REGISTRATION AND GOVERNMENT INCENTIVES FOR FOOD PROCESSING MANUFACTURERS

Food processing is a priority sector under the Indian government. Multiple central and state schemes offer capital subsidy, credit support, and market linkage to registered food processing units.

UDYAM REGISTRATION (MSME):
- Mandatory for availing most government benefits
- Online registration at udyamregistration.gov.in; instant certificate
- Classification: Micro (< ₹2.5 crore investment + < ₹10 crore turnover), Small (< ₹25 crore + ₹100 crore), Medium (< ₹125 crore + ₹500 crore)
- Benefits: Priority sector lending, GeM portal access, delayed payment protection, credit guarantee, subsidized rates on power/water in some states

PRODUCTION LINKED INCENTIVE (PLI) FOR FOOD PROCESSING:
- Launched under PM Kisan Sampada Yojana umbrella
- PLI food: ₹10,900 crore over 6 years; target food segments include ready-to-eat, marine products, fruits/vegetables, mozzarella cheese
- Incentive: 4–10% of incremental sales over base year for 6 years
- Eligibility: Minimum investment ₹10 crore (new) or expansion, apply via MoFPI portal
- Status: Applications closed for initial tranche; watch for new tranches

PM FORMALISATION OF MICRO FOOD PROCESSING ENTERPRISES (PM FME):
- For existing micro food enterprises
- 35% capital subsidy (max ₹10 lakh) via NABARD/SHG route
- Technical and business training
- Common processing facilities (CPF) created in clusters
- Apply through state nodal agency

STATE-LEVEL INCENTIVES (EXAMPLE — MAHARASHTRA):
- Package Scheme of Incentives (PSI): Capital subsidy 20–40% based on region (D+ areas get highest)
- Stamp duty exemption on land/property for new factories
- Power tariff subsidy for first 5–7 years
- Employment generation subsidy: ₹1,500–₹3,000 per job created per month for 3 years

ERPNext FOR GOVERNMENT COMPLIANCE AND SUBSIDY TRACKING:
- Project tracking: Capital investment details for subsidy claims
- Production reports: Sales volume and value for PLI incentive calculation
- Employment records: Headcount by category for employment generation claims
- Investment register: Asset-wise capital expenditure for subsidy documentation
        """,
        "tags": ["msme", "pli_scheme", "pm_fme", "subsidies", "food_manufacturing", "government_incentives"],
        "priority": "medium"
    }
]

MFG_FOOD_BEST_PRACTICES = [
    {
        "title": "Bill of Materials (BOM) Management for Food Processing",
        "content": """
BILL OF MATERIALS (BOM) MANAGEMENT FOR FOOD PROCESSING MANUFACTURERS

The BOM is the recipe of your product — it defines exactly which raw materials, in what quantities, are needed to produce one unit of finished goods. In food processing, BOM accuracy directly impacts cost control, procurement, and recipe compliance.

FOOD BOM STRUCTURE:
- Finished Good: Item being produced (e.g., Tomato Ketchup 500g)
- Raw Materials: Tomatoes, sugar, salt, acetic acid, spices
- Packaging Materials: Glass bottle, metal cap, label, outer carton
- Overhead/Consumables: Gas (for cooking), water (for washing/processing)
- By-products: Tomato pulp/skin if recovered and sold

FOOD-SPECIFIC BOM CONSIDERATIONS:
1. MOISTURE LOSS (EVAPORATION FACTOR): In cooking/drying, raw material weight is always higher than finished good weight. BOM must reflect this. Example: 1.4 kg tomatoes → 1 kg ketchup (30% moisture loss)
2. YIELD % PER INGREDIENT: Actual usable portion of raw material. Example: 1 kg raw onions → 0.75 kg peeled (25% wastage). BOM should be built on actual yield.
3. SEASONAL VARIATION: Brix content of tomatoes varies seasonally — recipe quantities may change. Maintain BOM version by season.
4. SUBSTITUTE INGREDIENTS: Document approved substitutes with quality parameters in case primary ingredient is unavailable

BOM COSTING:
- Standard Cost per unit = Sum of (raw material quantity × raw material standard rate) + direct labor + overhead
- Standard vs. Actual: Compare actual raw material consumed per batch vs. BOM standard; variance > 2% triggers investigation
- Recosting: When raw material prices change significantly (> 5%), update BOM rates and recalculate product cost

ERPNext BOM FEATURES:
- Multi-level BOM: Supports sub-assemblies (e.g., spice mix is a sub-BOM within ketchup BOM)
- Scrap/By-product: Enter by-product and scrap % in BOM; ERPNext accounts for by-product value
- BOM versions: Maintain historical BOMs when recipe changes; link version to production batch
- BOM Cost: ERPNext auto-calculates standard cost from BOM + routing; update rates periodically
- Raw material requirement: Production Plan uses active BOM to compute procurement requirement
        """,
        "tags": ["bom", "bill_of_materials", "food_manufacturing", "recipe", "costing"],
        "priority": "high"
    },
    {
        "title": "Production Planning and Scheduling for Food Processing Units",
        "content": """
PRODUCTION PLANNING AND SCHEDULING FOR FOOD PROCESSING MANUFACTURERS

Food processing production planning is constrained by raw material availability (seasonal, perishable), equipment capacity, shelf life requirements, and firm order commitments. Effective planning bridges demand with supply.

DEMAND-DRIVEN PRODUCTION PLANNING:
1. Start with: Confirmed Sales Orders + Forecast for next 4–8 weeks
2. Net against: Finished goods inventory (available stock)
3. Result: Production requirement by item and week
4. Explode BOM: Convert production requirement to raw material requirement
5. Net raw material: Against current stock + incoming purchase orders
6. Gap = procurement required

FOOD MANUFACTURING SCHEDULING CONSTRAINTS:
- Batch cooking equipment: Continuous or batch? Batch cooking limits throughput to one product per cycle
- CIP (Clean-In-Place) time: Food equipment must be sanitized between batches of different products — schedule cleaning time
- Allergen management: Allergen-containing products (nuts, dairy, gluten) must be scheduled last in day; full CIP before next product
- FIFO production: When raw material has limited shelf life, process oldest stock first
- Cold chain: Products requiring cold chain must be dispatched same day as production (ice cream, fresh paneer)

CAPACITY PLANNING:
- Identify bottleneck (constraining resource): Usually the cooking vessel, dryer, or packing line
- Calculate throughput per bottleneck hour: Production rate of bottleneck equipment
- Available hours per month: Working days × shifts × hours/shift (minus downtime/CIP)
- Max monthly production = Bottleneck throughput × Available hours

SEASONAL PLANNING FOR AGRO-BASED PROCESSORS:
- Procurement season (raw material flush): Buy and store raw material when prices are low (post-harvest)
- Production run: Process through the year from stored stock
- Forward coverage ratio: Months of raw material stock on hand; target 6–9 months for seasonal items

ERPNext PRODUCTION PLANNING:
- Production Plan doctype: Combines open Sales Orders + forecast; auto-generates Work Orders
- Work Order: Schedules production of a specific quantity on a specific date
- Material Request: Auto-generated for raw material shortfalls identified in planning
- Capacity planning report: Planned production hours vs. available capacity per work center
        """,
        "tags": ["production_planning", "scheduling", "capacity_planning", "food_manufacturing", "work_order"],
        "priority": "high"
    },
    {
        "title": "Quality Control and HACCP Implementation for Food Manufacturers",
        "content": """
QUALITY CONTROL AND HACCP FOR FOOD PROCESSING MANUFACTURERS

HACCP (Hazard Analysis and Critical Control Points) is a systematic preventive approach to food safety. It is mandatory for export-oriented food units and strongly recommended for domestic manufacturers targeting organized retail.

SEVEN HACCP PRINCIPLES:
1. Hazard Analysis: Identify biological (bacteria, viruses), chemical (pesticides, allergens), and physical (glass, metal) hazards at each production step
2. Critical Control Points (CCPs): Identify steps where control is essential (e.g., pasteurization temperature, metal detection)
3. Critical Limits: Define acceptable limits at each CCP (e.g., pasteurization ≥ 72°C for 15 seconds)
4. Monitoring Procedures: Define who checks what, how often, and with what instrument
5. Corrective Actions: What to do when CCP is breached (e.g., re-process, discard, hold batch)
6. Verification: Regular audits to confirm HACCP system is working
7. Record Keeping: All CCP monitoring records retained for minimum 2 years

IN-PROCESS QUALITY CHECKS (FOOD MANUFACTURING):
- Raw material incoming: Visual, organoleptic, moisture, pesticide residue (for agro products)
- In-process: pH, temperature, Brix (sugar content), viscosity, fill weight, seam integrity
- Finished goods: Microbial testing (TPC, coliform, yeast/mold), nutritional testing, packaging integrity, label check
- Shelf life validation: Accelerated shelf life testing before new product launch

LABORATORY SETUP FOR QC:
- Minimum in-house lab: Moisture analyzer, pH meter, refractometer (Brix), weighing balance, thermometers
- Outsourced testing: NABL-accredited lab for microbial and chemical testing (cost: ₹500–₹5,000 per test depending on parameters)

ERPNext QC WORKFLOW:
- Quality Inspection doctype: Triggered automatically on Goods Receipt (for raw materials) and before Delivery Note (for finished goods)
- QC template: Define inspection parameters per item (e.g., moisture, pH, visual check)
- Accept/Reject: QC pass → stock updated; QC fail → quarantine, triggers non-conformance
- QC history: Full history of inspections per batch — available for FSSAI/buyer audit
- Non-Conformance Report (NCR): Custom doctype to track quality failures, root cause, corrective action
        """,
        "tags": ["haccp", "quality_control", "food_safety", "qc", "food_manufacturing"],
        "priority": "high"
    },
    {
        "title": "Cold Chain and Storage Management for Food Processing",
        "content": """
COLD CHAIN AND TEMPERATURE-CONTROLLED STORAGE FOR FOOD MANUFACTURERS

Cold chain integrity is non-negotiable for dairy, meat, seafood, ready-to-eat, and some beverage manufacturers. A cold chain breach doesn't just spoil product — it can cause food safety incidents with serious liability.

COLD CHAIN INFRASTRUCTURE REQUIREMENTS:
- Blast Freezer: For rapid cooling of hot-processed product to -18°C or below
- Cold Storage Room: Maintained at -18°C to -22°C for frozen products; +2°C to +8°C for chilled
- Refrigerated Vehicles: Pre-cooled before loading; temperature monitored in-transit
- Cold Room at Retailer: Part of cold chain continuity; supplier's responsibility to audit

TEMPERATURE MONITORING STANDARDS:
- Continuous data loggers: Digital temperature loggers with 15-minute recording interval mandatory for food grade cold rooms
- Alarm systems: Automated alarm when temperature deviates beyond set range; alert to phone/email within 5 minutes
- Calibration: Temperature instruments calibrated annually by certified lab
- Record retention: Temperature logs retained for product shelf life + 6 months (or regulatory minimum)

COLD CHAIN BREAKS — RESPONSE PROTOCOL:
- Identify: Immediately determine duration and extent of breach
- Assess: Microbiologist evaluates safety based on time-temperature abuse calculation
- Decide: Hold, test, destroy, or approve for sale (with documented risk assessment)
- Document: Record every breach with timestamp, root cause, corrective action

PRODUCT-SPECIFIC TEMPERATURE REQUIREMENTS:
- Fresh pasteurized milk/curd: 0–4°C; 4–7 day shelf life
- Paneer/cheese: 0–4°C; 7–15 days depending on packing
- Frozen vegetables/ready meals: -18°C; 12–24 months
- Fruit juices (non-carbonated, non-pasteurized): 0–4°C; 7–14 days
- Chocolate and confectionery: 15–18°C, humidity < 55% (not "cold chain" but temperature-sensitive)

ERPNext FOR COLD CHAIN MANAGEMENT:
- Warehouse properties: Tag warehouses as "cold_storage" vs. "ambient" — auto-validate item storage requirement
- Batch-level temperature log: Custom table in Batch master to log temperature readings
- Delivery Note: Custom field for vehicle temperature at dispatch; driver sign-off
- Expiry alert by storage condition: Shorter alert window for cold chain items (7 days) vs. ambient (30 days)
        """,
        "tags": ["cold_chain", "temperature_control", "food_storage", "food_manufacturing", "dairy"],
        "priority": "high"
    },
    {
        "title": "Packaging, Labeling, and Brand Compliance for Food Manufacturers",
        "content": """
PACKAGING AND LABELING COMPLIANCE FOR FOOD MANUFACTURERS IN INDIA

Food labeling is governed by FSSAI's Food Safety and Standards (Labelling and Display) Regulations, 2020. Non-compliant labels risk product recalls, fines, and market withdrawal.

MANDATORY LABEL REQUIREMENTS (ALL PACKAGED FOODS):
1. Name of food: Common or generic name clearly stated
2. Net weight/volume: In metric units (g, ml, kg, L); numeric size of declaration ≥ 1.5mm per FSSAI rules
3. Ingredients list: In descending order by weight; allergens in bold or highlighted
4. Nutritional information: Per 100g/100ml AND per serving; energy (kcal), protein, fat, carbohydrate, sodium mandatory
5. Manufacturer details: Name, address, FSSAI license number
6. Best Before / Use By date
7. Batch/Lot number: For traceability
8. Country of origin (if imported or partially imported)
9. Vegetarian/Non-vegetarian symbol: Green dot (veg) or brown/maroon dot (non-veg)
10. MRP: Inclusive of all taxes

ALLERGEN DECLARATION (MANDATORY FROM 2022):
Major allergens must be declared clearly on pack: Gluten (wheat, barley, rye), dairy, eggs, fish, shellfish, peanuts, tree nuts (cashew, almond, walnut), soy, sesame

FRONT-OF-PACK LABELING (FOPL) — EMERGING REQUIREMENT:
- FSSAI proposed FOPL rules (star ratings) still under consideration as of 2024
- High fat, sugar, sodium (HFSS) foods may be required to carry health warning
- Monitor FSSAI notifications; changes expected in 2025–2026

PACKAGING MATERIAL COMPLIANCE:
- Food-grade packaging mandatory: BPA-free plastics for food contact
- EPR (Extended Producer Responsibility): All packaged food manufacturers with turnover > ₹10 lakh must register with CPCB and meet plastic waste collection targets
- Bio-degradable claims: Must meet IS 17088 standard; no unverified "eco" claims

ERPNext LABEL MANAGEMENT:
- Item master: Store label version, artwork file reference, FSSAI text details
- Batch-specific label: Label generation linked to Batch with auto-filled: batch number, mfg date, best-before date
- Label version control: Track which label version was used per batch for recall traceability
- Artwork approval workflow: Custom Workflow in ERPNext for label design → legal review → approve
        """,
        "tags": ["labeling", "packaging", "fssai_label", "allergen", "food_manufacturing"],
        "priority": "high"
    },
    {
        "title": "Sourcing and Raw Material Management for Food Processors",
        "content": """
RAW MATERIAL SOURCING AND PROCUREMENT FOR FOOD PROCESSING MANUFACTURERS

Raw material quality and availability are the biggest operational risks for food processors. Agro-based inputs are seasonal, perishable, and price-volatile. Building robust sourcing is a strategic necessity.

SOURCING STRATEGY FOR FOOD MANUFACTURERS:
1. DIRECT FROM FARMER: Best for large processors; better price, full traceability, Farmer Producer Organisation (FPO) partnerships
   - Advantages: Lower cost (no middleman), direct relationship, season advance payments for farmer loyalty
   - Disadvantages: Logistics, quality variability, requires agronomy team or FPO management
2. MANDIS/WHOLESALE MARKET: Most common for SMEs; immediate availability, price discovery
   - Advantages: Flexible, no minimum commitment
   - Disadvantages: Quality variability, APMC compliance, no traceability to farm level
3. CONTRACT FARMING: Pre-agreed quantity, quality, and price before season
   - Advantages: Supply certainty, quality specification compliance
   - Disadvantages: Requires monitoring, advance payment risk
4. TRADERS/IMPORTERS: For specialized/imported ingredients (spices, dry fruits, flavors)

RAW MATERIAL QUALITY SPECIFICATIONS:
- Develop Written Specifications (WS) for each key raw material: moisture %, color (Minolta reading), size/grade, defect %, microbial limits, pesticide residue limits
- Share WS with all suppliers; only accept material meeting specs
- Reject non-conforming material at gate; issue Rejection Memo to supplier

SEASONAL PROCUREMENT CALENDAR:
- Tomato: Peak March–June; buy and concentrate/process during peak
- Mangoes: March–June; pulping season
- Chillies: Jan–March (Guntur season); buy dried chilli for year-round use
- Pulses: Oct–March post-harvest; build 6-month stock

ERPNext PROCUREMENT FOR FOOD:
- Item Quality Parameters: Custom fields for moisture, grade, source farm/region
- Purchase Order with quality spec: Attach WS as PDF to PO
- Batch-wise incoming quality: Create QC inspection at Goods Receipt; link to batch
- Supplier performance: Track % of deliveries meeting spec by supplier — only reorder from compliant suppliers
- Seasonal stock build: Create Forward Purchase Orders for entire season; track against planned requirement
        """,
        "tags": ["raw_material_sourcing", "procurement", "agri_input", "food_manufacturing", "contract_farming"],
        "priority": "high"
    }
]

MFG_FOOD_ERPNEXT = [
    {
        "title": "ERPNext Manufacturing Module Setup for Food Processing",
        "content": """
ERPNEXT MANUFACTURING MODULE CONFIGURATION FOR FOOD PROCESSING

MODULES TO ENABLE:
1. Manufacturing: BOM, Work Orders, Production Plan, Job Cards
2. Stock: Raw material, WIP, finished goods, batch tracking
3. Buying: Seasonal procurement, quality inspection at receipt
4. Selling: Customer orders, dispatch, e-invoicing
5. Quality Management: QC templates, inspections, non-conformance
6. Accounts: Job costing, overhead allocation, cost center P&L

KEY DOCTYPES FOR FOOD MANUFACTURING:
- Bill of Materials (BOM): Recipe with raw materials, quantities, yield %
- Work Order: Production instruction for a specific batch/quantity
- Job Card: Time and material tracking at each work center
- Production Plan: Aggregate planning from Sales Orders + forecast
- Quality Inspection: QC test template + result capture
- Batch: Tracks one production batch through the system

ITEM SETUP FOR FOOD MANUFACTURING:
- Finished Goods: Is Sales Item ✓, Is Manufactured Item ✓, Has Batch No ✓, Has Expiry Date ✓
- Raw Materials: Is Purchase Item ✓, Has Batch No ✓ (for agricultural raw materials)
- Packaging: Is Purchase Item ✓, Item Group = "Packaging Material"
- WIP (Work-in-Progress): Internal item for intermediate product tracking if needed

WAREHOUSE STRUCTURE:
- Raw Material Store: Ambient and cold storage (separate)
- WIP (Work-in-Progress) Area: Where production happens
- Finished Goods Store: Pre-dispatch holding
- Packaging Store: Cartons, labels, pouches
- Quarantine Store: Failed QC or hold items
- Rejection Store: Raw material or FG rejected and awaiting return/disposal

CRITICAL SETTINGS FOR FOOD MANUFACTURING:
- Manufacturing Settings: "Update Finished Goods Cost Automatically" = Yes
- Stock Settings: "Allow Negative Stock" = No (food manufacturing must not oversell)
- Quality Inspection: "Inspection Required Before Purchase" = Yes (for raw materials)
- Batch Auto-naming: Enable naming series for batch IDs (e.g., PROD-DDMMYY-001)
        """,
        "tags": ["erpnext_setup", "manufacturing_module", "food_processing", "configuration"],
        "priority": "high"
    },
    {
        "title": "ERPNext Work Order and Production Execution for Food Manufacturers",
        "content": """
ERPNEXT WORK ORDER AND PRODUCTION EXECUTION FOR FOOD MANUFACTURING

THE WORK ORDER LIFECYCLE IN ERPNEXT:
Draft → Submitted → In Process → Completed (stock updated) → Closed

CREATING A WORK ORDER:
1. Go to Work Order → New
2. Select Item (finished good to produce) and BOM
3. Enter: Planned Quantity, Planned Start Date
4. Warehouses: Raw material from (RM Store), FG to (FG Store)
5. Submit: Work Order is now "Submitted" and can be released to production

MATERIAL ISSUE TO PRODUCTION (STOCK ENTRY — MATERIAL TRANSFER FOR MANUFACTURE):
- System shows required raw material quantities from BOM
- Actual quantities issued may differ (over-consumption = production loss, under = excess remaining)
- Variance from BOM is captured and forms the basis for material variance analysis
- Batch selection: Issue raw materials in FIFO/FEFO order

RECORDING PRODUCTION OUTPUT (STOCK ENTRY — MANUFACTURE):
- Record actual finished good quantity produced
- If yield is lower than planned (e.g., 95% of planned output): System records yield loss
- By-products: Record actual by-product quantity produced
- Scrap: Record actual scrap produced (auto-valued if scrap value entered in BOM)

JOB CARDS FOR LABOR TRACKING:
- Each Work Order generates Job Cards per Operation (Cleaning, Cooking, Packing, etc.)
- Operator starts and ends Job Card: Captures actual time taken
- Material consumed at operation level (if operation-wise material tracking enabled)
- Comparison: Planned hours (from Routing) vs. actual hours (from Job Cards) = labor efficiency

POST-PRODUCTION FLOW:
Work Order completed → Batch created in FG Store → Quality Inspection triggered → QC Pass → Available for Sale → Delivery Note → Sales Invoice

FOOD-SPECIFIC WORK ORDER TIPS:
- Create one Work Order per production batch (not per week)
- Batch ID of finished good should reference Work Order for traceability
- If batch fails QC: Do NOT close Work Order; initiate re-processing or disposal
- Multiple output batches from one Work Order: Supported via additional rows in manufacture Stock Entry
        """,
        "tags": ["work_order", "production_execution", "erpnext", "food_manufacturing", "job_card"],
        "priority": "high"
    },
    {
        "title": "ERPNext Costing and Profitability for Food Processing",
        "content": """
PRODUCT COSTING AND PROFITABILITY ANALYSIS IN ERPNEXT FOR FOOD MANUFACTURERS

COST COMPONENTS FOR FOOD MANUFACTURING:
1. Direct Materials: Raw materials + packaging (from BOM × actual consumption)
2. Direct Labor: Operator wages allocated to production (from Job Cards)
3. Manufacturing Overhead: Factory rent, electricity, machine depreciation, supervisory wages — allocated via overhead rate
4. Yield Loss Cost: Cost of raw material used in waste/by-products

STANDARD COSTING IN ERPNEXT:
- Set standard rate for each raw material in Item Valuation Rate
- BOM Cost auto-calculated: Sum of (standard rate × BOM quantity) per finished good
- Standard Cost per unit = Material cost + Direct labor + Overhead
- Compare with actual cost after production → Standard vs. Actual Variance

MANUFACTURING OVERHEAD ALLOCATION:
- Method 1: % of direct material cost (simple; e.g., overhead = 20% of material cost)
- Method 2: Rate per machine hour (accurate; requires hour tracking via Job Cards)
- ERPNext: Configure in "Manufacturing Settings" → add overhead cost per Work Order

FOOD PRODUCT PROFITABILITY ANALYSIS:
- Contribution per unit = Selling Price – Variable Cost (materials + direct labor)
- Contribution Margin % = Contribution / Selling Price × 100
- Target CM% for food: 35–50% (premium products), 15–25% (commodity food)
- Break-even volume per product = Fixed overhead / Contribution per unit

BATCH-WISE COSTING:
- Each production batch has its own cost (raw material prices fluctuate)
- ERPNext captures actual material cost per batch from Stock Entries
- Compare batch-wise cost → identify production efficiency trends

KEY ERPNEXT REPORTS FOR FOOD COST MANAGEMENT:
- Item-wise Gross Profit: Revenue vs. COGS by product
- Work Order Stock Summary: Planned vs. actual materials per Work Order
- Job Card Summary: Planned vs. actual labor hours by work center
- BOM vs. Actual Cost report: Standard cost vs. actual production cost per batch
- Cost Center P&L: Factory cost center vs. selling cost center — identify overhead leakages
        """,
        "tags": ["costing", "profitability", "standard_cost", "overhead", "food_manufacturing", "erpnext"],
        "priority": "high"
    },
    {
        "title": "ERPNext Batch Traceability and Recall Management for Food",
        "content": """
BATCH TRACEABILITY AND RECALL MANAGEMENT IN ERPNEXT FOR FOOD MANUFACTURERS

REGULATORY REQUIREMENT:
FSSAI mandates full forward and backward traceability for food manufacturers. In a recall, you must identify within 24 hours: which batches are affected, which customers received them, and pull them from market.

FORWARD TRACEABILITY (BATCH → CUSTOMER):
- Question: "Batch B001 had a contamination. Who received it?"
- ERPNext: Batch → Delivery Notes using this batch → Sales Invoices → Customers
- Report: "Batch-wise Sales History" → filter by batch number → get customer list
- Use: Recall notification list; regulatory reporting

BACKWARD TRACEABILITY (FINISHED GOOD BATCH → RAW MATERIALS):
- Question: "Supplier reported pesticide contamination in Lot RM-234. Which of our batches used it?"
- ERPNext: Purchase Receipt batch → Stock Entry (material issue) → Work Order → Finished Good batch
- Report: "Production traceability" report — traces FG batch to RM batches used
- Use: Proactive recall before consumer complaint

RECALL MANAGEMENT PROCESS:
1. DETECT: Quality complaint, regulatory notice, or supplier alert
2. ASSESS: Determine scope (which batches, which markets)
3. INITIATE: Inform management, regulatory authority (FSSAI portal for Class 1 recalls)
4. NOTIFY: Contact all affected customers with batch numbers and return instructions
5. RETRIEVE: Receive returned stock; segregate in quarantine
6. DISPOSE: Destroy or re-process recalled stock with documentation
7. INVESTIGATE: Root cause analysis; CAPA (Corrective and Preventive Action)
8. CLOSE: FSSAI closure report

SETTING UP TRACEABILITY IN ERPNEXT:
- Batch tracking mandatory for all food items: Check "Has Batch No" in Item master
- Never receive without batch number: Make Batch field mandatory in Purchase Receipt
- Never produce without batch: Work Order → Production Stock Entry auto-assigns batch
- Never dispatch without batch: Delivery Note → batch field mandatory

MOCK RECALL EXERCISE (BEST PRACTICE):
- Conduct quarterly mock recall within factory: Pick random batch → trace all raw materials and all dispatches within 4 hours
- Target: 100% traceability within 4 hours
- Document and improve process each time
        """,
        "tags": ["batch_traceability", "recall", "fssai", "food_safety", "erpnext", "food_manufacturing"],
        "priority": "high"
    }
]

MFG_FOOD_PAIN_POINTS = [
    {
        "title": "Top Pain Points: Spoilage, Wastage, and Yield Loss in Food Processing",
        "content": """
PAIN POINT: SPOILAGE, WASTAGE, AND YIELD LOSS IN FOOD PROCESSING

PROBLEM DESCRIPTION:
Food processing manufacturers lose 8–15% of raw material value to spoilage, trimming waste, and process loss. Without systematic tracking, this loss is invisible — absorbed into "cost of production" without analysis or action.

ROOT CAUSES:
- No BOM yield standards: No documented standard for how much raw material should produce how much finished good
- Batch size mismatch: Equipment designed for 500 kg batch run at 300 kg = inefficient conversion
- Over-ripened or poor-quality raw material: Accepted without strict QC, leading to higher processing loss
- Equipment maintenance failure: Inefficient sealing, cooking, or drying equipment increases loss
- Operator skill variability: Experienced operator wastes 5%; trainee wastes 15% — no standard process

FINANCIAL IMPACT:
- 10% excess wastage on ₹50 lakh/month raw material purchase = ₹5 lakh/month → ₹60 lakh/year
- Even 2% improvement in yield saves ₹12 lakh/year with no capital investment
- Customer pricing built on 10% wastage assumption; if actual wastage is 15%, entire margin is eroded

HOW ERPNext SOLVES THIS:
1. BOM with Standard Yield: Set expected yield % in BOM; system computes planned vs. actual output
2. Work Order Variance Report: After every batch, compare raw material issued vs. BOM standard
3. Scrap Entry: Record actual scrap quantity per batch — visible, not hidden in averages
4. Batch-wise yield tracking: Calculate actual yield % per batch; trend analysis reveals improvement/deterioration
5. Operator-wise variance: If Job Cards filled, compare yield by shift/operator

PROCESS IMPROVEMENTS:
- Incoming QC: Reject raw material below minimum grade — better to source better than process bad material
- Standardize batch sizes: Run equipment at design capacity for optimal conversion efficiency
- SOPs for trimming and preparation: Define max trim %, post visually at workstation
- Weekly yield review: Compare last 4 weeks' batch yield; investigate outliers > 5% below standard
- Equipment maintenance schedule: Scheduled maintenance prevents efficiency degradation
        """,
        "tags": ["spoilage", "wastage", "yield_loss", "food_manufacturing", "pain_points"],
        "priority": "high"
    },
    {
        "title": "Top Pain Points: Production Scheduling Conflicts in Food Manufacturing",
        "content": """
PAIN POINT: PRODUCTION SCHEDULING CONFLICTS AND EQUIPMENT DOWNTIME IN FOOD MANUFACTURING

PROBLEM DESCRIPTION:
Food manufacturers frequently face the "scheduling chaos" problem — sales team commits delivery dates without knowing production capacity, production team makes product that isn't ordered, and maintenance emergencies shut down lines at the worst times.

COMMON SCHEDULING PROBLEMS:
- Sales books order for delivery in 3 days; product needs 5 days to produce and cool
- Same packaging line is allocated to 3 products simultaneously by 3 different managers
- Allergen-containing product scheduled back-to-back with allergen-free, creating cross-contamination risk
- Weekend production planned but CIP (clean-in-place) was scheduled simultaneously
- Raw material arrives late; production plan set 3 days ago becomes impossible

EQUIPMENT DOWNTIME IMPACT:
- Average planned downtime in food factories: 10–15% (CIP, maintenance, changeover)
- Unplanned downtime: 5–10% for Indian SME food factories
- Every hour of downtime = lost production equivalent to hourly throughput × margin
- Chronic small breakdowns (MTTR < 30 min) are often ignored but add up to significant losses

HOW ERPNext HELPS:
1. Production Plan from Sales Orders: Prevents commitment beyond capacity; shows production queue
2. Work Center Capacity Check: ERPNext flags over-scheduling on a work center before submission
3. Planned Maintenance: Maintenance module schedules CIP and preventive maintenance; auto-creates Maintenance Visit records
4. Delivery Commitment Logic: Sales team sees "Delivery Date Available" before promising customer
5. Material Readiness Check: Production Plan validates raw material availability before generating Work Orders

PROCESS IMPROVEMENTS:
- S&OP Meeting (weekly): Sales, production, and supply chain align on what gets made in the coming week
- Frozen schedule (48 hours): No changes to production schedule within 48 hours without VP approval
- Maintenance windows: Fixed maintenance slots per line per week — never scheduled ad-hoc
- Changeover reduction (SMED): Single Minute Exchange of Die principles adapted to food production
- Visual production board: Physical or digital Kanban showing each line's current status
        """,
        "tags": ["scheduling", "downtime", "production_planning", "food_manufacturing", "pain_points"],
        "priority": "high"
    }
]


# ============================================================
# TEXTILE MANUFACTURING — 15 CHUNKS
# ============================================================

MFG_TEXTILE_COMPLIANCE = [
    {
        "title": "GST and Tax Compliance for Textile Manufacturers",
        "content": """
GST COMPLIANCE FOR TEXTILE MANUFACTURING — INVERTED DUTY STRUCTURE PROBLEM

Textile is one of India's most complex GST sectors due to the infamous "inverted duty structure" — raw materials attract higher GST than finished goods, creating a permanent ITC accumulation problem.

TEXTILE GST RATE STRUCTURE (POST-2022 REVISION):
- Cotton yarn, cotton fabric: 5%
- Synthetic yarn: 12% (man-made fibers, polyester)
- Apparel/garments > ₹1,000 MRP: 12%
- Apparel/garments < ₹1,000 MRP: 5%
- Technical textiles (industrial): 12–18%
- Embroidered fabric: 5%
- Silk, wool fabric: 5%

INVERTED DUTY STRUCTURE (IDS) — THE CORE PROBLEM:
- Synthetic textile manufacturers buy polyester fiber @ 18% GST (input)
- Sell finished fabric @ 5% GST (output)
- ITC accumulated every month — cannot be offset against output liability
- Solution: Claim IDS refund (Section 54 of CGST Act)

HOW TO CLAIM IDS REFUND:
1. File monthly refund application on GST portal (Form RFD-01)
2. Supporting documents: GSTR-2A, purchase invoices, export invoices (if applicable)
3. Refund only on GST portion of ITC (not on capital goods ITC under IDS)
4. Processing time: 15–60 days; auto-processing with Aadhaar authentication

TUF (TECHNOLOGY UPGRADATION FUND SCHEME):
- Capital subsidy on machinery for weaving, processing, garmenting
- Interest reimbursement: 4–6% on term loans for eligible machinery
- Apply through designated nodal banks (SBI, Bank of Baroda, etc.)

ERPNext FOR TEXTILE GST COMPLIANCE:
- Separate tax templates for yarn purchase (18% GST) vs. fabric sale (5% GST)
- IDS refund calculation report: Monthly accumulated ITC that qualifies for IDS refund
- GSTR-2B reconciliation: Match purchase invoices for refund claim support
- Job work compliance: Fabric sent for processing (dyeing, printing) — issue challan, not invoice
        """,
        "tags": ["gst", "inverted_duty_structure", "textile", "compliance", "itc_refund"],
        "priority": "high"
    },
    {
        "title": "Environmental Compliance for Textile Processing Units",
        "content": """
ENVIRONMENTAL COMPLIANCE FOR TEXTILE PROCESSING (DYEING AND PRINTING UNITS)

Textile wet processing (dyeing, bleaching, printing, finishing) generates highly polluted effluents with high BOD, COD, TDS, and color. It is categorized as "Red Industry" by CPCB and requires full environmental clearance.

CONSENT TO OPERATE (CTO) — MANDATORY FOR TEXTILE DYEING UNITS:
- Apply to State Pollution Control Board before commencing wet processing
- Submit: Effluent quality data, ETP design, production capacity, chemical inventory
- Site inspection by SPCB officer (3–6 months processing time for Red category)
- Annual renewal; non-renewal = production stop order

EFFLUENT TREATMENT STANDARDS FOR TEXTILE:
- BOD: < 30 mg/L (inland surface water)
- COD: < 250 mg/L
- TDS (Total Dissolved Solids): < 2,100 mg/L for inland
- Color: Not visible at 100× dilution (no standard but inspected visually)
- Temperature: < 40°C at discharge point

ZERO LIQUID DISCHARGE (ZLD) REQUIREMENT:
- Mandatory for textile units in specific areas: Tiruppur (Tamil Nadu), Surat (Gujarat), Ludhiana (Punjab) — state-specific
- ZLD means all effluent is treated and reused; zero discharge to environment
- ZLD plants are expensive (₹2–5 crore for medium units) but mandatory in notified areas

CHEMICAL MANAGEMENT (REACH COMPLIANCE FOR EXPORTS):
- EU buyers require REACH (Registration, Evaluation, Authorisation of Chemicals) compliance
- Banned chemicals in export garments: Azo dyes releasing carcinogenic amines, formaldehyde above limits, heavy metals (lead, chromium VI)
- Testing: Fabric sample to Oeko-Tex/GOTS certified lab before export; certification costs ₹20,000–₹1 lakh depending on scope

ENERGY AND WATER AUDIT:
- Water consumption benchmark: 80–150 liters per kg fabric (processed)
- High water use = high effluent = high treatment cost; water efficiency is also cost efficiency
- Energy audit mandatory for large units under Energy Conservation Act (Bureau of Energy Efficiency)

ERPNext ENVIRONMENTAL COMPLIANCE:
- Maintenance module: Schedule ETP maintenance, chemical dosing pump service
- Chemical inventory: Track hazardous chemical stock; generate chemical register for SPCB
- Water meter readings: Log daily water consumption in ERPNext custom doctype
        """,
        "tags": ["environment", "zld", "textile_dyeing", "pollution_compliance", "textile", "etp"],
        "priority": "high"
    },
    {
        "title": "BIS, OEKO-TEX, and Export Compliance for Textile Manufacturers",
        "content": """
CERTIFICATIONS AND EXPORT COMPLIANCE FOR TEXTILE MANUFACTURERS

India is the world's second-largest textile exporter. Accessing premium export markets requires multiple certifications that are separate from domestic compliance requirements.

DOMESTIC CERTIFICATIONS:
- BIS Woollen Textiles: IS certification for certain woollen fabrics
- Handloom Mark: Certification from Handloom Development Commissioner for genuine handloom products; prevents machine-made fabric from using handloom branding
- Silk Mark: For genuine silk products; issued by Central Silk Board; consumer protection against synthetic silk fraud
- India Organic (NPOP): For organic cotton and other organic textiles

EXPORT MARKET CERTIFICATIONS:

1. OEKO-TEX STANDARD 100 (Most popular global textile certification):
   - Tests for 100+ harmful substances (formaldehyde, heavy metals, pesticides, pH)
   - Certifies that every component of the garment is harmless to health
   - Cost: ₹30,000–₹1,50,000 depending on product and certifying institute
   - Validity: 1 year, with annual renewal and testing
   - Required for: EU, US, Japanese buyers; some specify as minimum requirement

2. GOTS (Global Organic Textile Standard):
   - Certifies organic fiber content and entire supply chain
   - Requires organic cotton (NPOP/NOP certified) + no toxic chemicals in processing
   - Annual inspection by GOTS-approved certifier
   - Used for: Organic clothing brands globally

3. WRAP (Worldwide Responsible Accredited Production):
   - Social compliance certification (labor practices, safety, environmental)
   - Important for US market (Gap, Target, Walmart suppliers)
   - Factory inspection + self-assessment + third-party audit

4. SA8000 (Social Accountability):
   - International social compliance standard; covers child labor, forced labor, health and safety
   - Similar to WRAP; preferred by European buyers

AEPC (APPAREL EXPORT PROMOTION COUNCIL) MEMBERSHIP:
- Mandatory for apparel exporters to access government export benefits
- Provides RCMC (Registration-cum-Membership Certificate) for duty drawback and export incentive claims

ERPNext EXPORT DOCUMENTATION:
- Export Invoice in foreign currency with FOBAS/CIF terms
- Packing List: Detailed carton-wise packing for customs clearance
- GST refund on export: Zero-rated export (IGST paid = claimable refund or LUT bond for zero payment)
- Shipping Bill: Filed by customs broker; integrate reference in ERPNext Delivery Note
        """,
        "tags": ["oeko_tex", "gots", "textile_export", "certifications", "textile", "compliance"],
        "priority": "medium"
    },
    {
        "title": "Labour Compliance and Wage Act for Garment and Textile Factories",
        "content": """
LABOUR COMPLIANCE SPECIFIC TO GARMENT AND TEXTILE MANUFACTURING

Garment and textile factories are labour-intensive — a 500-worker garment unit has more labour law complexity than a 50-worker food factory. This is also a sector with high regulatory scrutiny from buyer social audits.

FACTORIES ACT COMPLIANCE FOR GARMENT UNITS:
- Factory license from Chief Inspector of Factories (required for 10+ workers with power)
- Working hours: 9 hours/day, 48 hours/week; overtime at 125% wages
- Female workers restrictions: Cannot work before 6 AM or after 10 PM in most states
- Night shift for females requires specific state permission and added welfare measures
- Crèche: Mandatory if 30+ female workers with children below 6

PIECE RATE vs. TIME RATE WAGES:
- Most garment factories use piece rate payment (per piece stitched or finished)
- Piece rate must be set so average worker earns minimum wage or above
- If piece rate earnings < minimum wage: Employer must top up to minimum wage
- Time rate workers: Entitled to full minimum wage regardless of output

MIGRANT WORKER COMPLIANCE:
- Many garment hubs (Bengaluru, NCR, Tiruppur) employ interstate migrant workers
- Interstate Migrant Workmen Act: If employing migrant workers, register with Labour Commissioner
- Provide: Transport from home state, fare subsidy, home state minimum wage (if higher than destination state)

ESIC FOR GARMENT FACTORIES:
- Mandatory if 10+ employees, wages < ₹21,000/month
- Garment workers under ESIC: Full medical treatment for worker + dependents at ESIC dispensary/hospital
- Maternity benefit: Under ESI (for units covered under ESIC); 26 weeks full wages paid by ESIC for female employees

BUYER SOCIAL AUDITS (BSCI, SMETA, SA8000):
- International buyers conduct social compliance audits annually
- Common audit focus: Working hours, overtime pay, child labour, fire safety, chemical handling
- Pre-audit preparation: Update all registers, certify all licenses, prepare worker interview readiness
- ERPNext HR MODULE for audit readiness: Attendance records, salary slips, leave records — all available in system

ERPNext TEXTILE HR SETUP:
- Department structure: Spinning, Weaving, Processing, Finishing, Packing, Quality, Admin
- Shift pattern: 2-shift (day/night) or 3-shift roster managed in ERPNext Shift master
- Piece rate payroll: Custom salary component linked to pieces produced (from Job Cards)
- Leave management: Annual leave, earned leave, maternity leave — fully managed in ERPNext
        """,
        "tags": ["labour_compliance", "factories_act", "garment", "textile", "social_audit"],
        "priority": "high"
    }
]

MFG_TEXTILE_BEST_PRACTICES = [
    {
        "title": "Production Planning and Fabric Yield Management for Textile",
        "content": """
PRODUCTION PLANNING AND FABRIC YIELD MANAGEMENT FOR TEXTILE MANUFACTURERS

TEXTILE PRODUCTION FLOW:
Fibre/Yarn Procurement → Weaving/Knitting → Grey Fabric Inspection → Dyeing/Processing → Finished Fabric Inspection → Cutting → Stitching → Quality Check → Packing → Dispatch

FABRIC YIELD MANAGEMENT:
- Fabric Utilization % = (Fabric used in finished garments) / (Total fabric issued to cutting) × 100
- Target: 85–90% utilization for woven garments; 80–85% for knits (due to seam allowance, collar, etc.)
- Cut ratio: Number of pieces produced per meter of fabric; track by style and size mix
- Shade lot management: Fabric from different dye batches (lots) must not be mixed in one garment order; separate cut plans per shade lot

PRODUCTION PLANNING FOR ORDER-BASED GARMENT MANUFACTURING:
1. Receive buyer order with style, quantity, size ratio, delivery date
2. Create Production BOM: Fabric consumption + trims (buttons, thread, zip, label, tag)
3. Procurement plan: Order fabric with 3–5% excess for wastage allowance; source trims
4. Line loading plan: Allocate production to stitching lines by operator skill (style-specific)
5. Daily production target: Style-wise, line-wise target (pieces/shift)
6. Monitoring: Actual vs. target hourly; intervene if line is running behind

LINE EFFICIENCY MANAGEMENT:
- Line efficiency % = (Actual output × SAM) / (Workers × Hours worked × 60) × 100
- SAM (Standard Allowed Minutes): Industry standard time for each operation (collar attachment, sleeve join, etc.)
- Target line efficiency: 60–70% for established lines; 40–50% for new style learning curve
- Learning curve: First 3 days of a new style always have low efficiency; plan for this

ERPNext FOR TEXTILE PRODUCTION:
- BOM per style: Fabric + all trims in one BOM linked to the style item
- Work Order per customer order (or per color/size break)
- Job Cards per operation: Measures operator efficiency per operation
- Fabric stock by shade lot: Batch = shade lot; never mix batches in one order
- Cut order tracking: Custom doctype for cut plan with pieces per size
- Daily production dashboard: Line-wise output vs. target, running efficiency %
        """,
        "tags": ["production_planning", "fabric_yield", "line_efficiency", "textile", "garment"],
        "priority": "high"
    },
    {
        "title": "Quality Control in Textile Manufacturing: AQL and Inline Inspection",
        "content": """
QUALITY CONTROL IN TEXTILE MANUFACTURING — AQL SYSTEM AND INLINE INSPECTION

AQL (ACCEPTABLE QUALITY LIMIT) — THE INDUSTRY STANDARD:
AQL is the maximum defect level considered acceptable for a shipment. The most common buyer AQL in garments is 2.5 (major defects), 4.0 (minor defects).

HOW AQL WORKS:
- Based on IS 2500 / MIL-STD-1916 sampling tables
- From shipment of 5,000 pieces (lot size), sample 200 pieces (at AQL 2.5)
- If defects found ≤ 10: PASS (shipment approved)
- If defects found ≥ 11: FAIL (100% inspection required or shipment rejected)
- Online AQL calculator: Buyer or factory uses to determine sample size

DEFECT CLASSIFICATION:
- Critical: Safety hazard (sharp metal, toxic chemical, choking hazard for children's wear) — 0% tolerance
- Major: Functional or visual defect visible at 1 meter distance that affects saleability (wrong shade, size, broken zipper)
- Minor: Defects noticeable only on close inspection; may be acceptable in some markets

INLINE QUALITY INSPECTION (IN-PROCESS):
- End-of-line audit: After stitching, before packing; catch defects before accumulation
- 10% hourly audit: Quality checker audits 10% of output every hour on each line
- Defect rate by line: If > 5% defect rate, stop line, retrain operator, investigate
- Seven QC tools: Pareto chart for defect frequency, fishbone for root cause — used in weekly QC review

PRE-SHIPMENT INSPECTION (PSI):
- Conducted 48 hours before shipment; 100% of packing completed before PSI
- Third-party inspector (SGS, Intertek, Bureau Veritas) engaged by buyer for large orders
- Inspection report: Pass/Fail; rejection triggers rework or replacement production
- PSI cost: ₹15,000–₹40,000 per inspection (typically buyer's cost but impacts relationship if failed)

ERPNext QC FOR TEXTILE:
- Quality Inspection per batch: AQL parameters (defect types, sample size, AQL level) as inspection template
- Defect recording: Inspector logs defect type and count per piece sampled
- AQL pass/fail auto-calculated based on inspection results
- Pre-shipment checklist: Custom form with buyer specifications; signed off by QC head
- Defect trend report: Track top 5 defect types by month; inform training priorities
        """,
        "tags": ["quality_control", "aql", "inline_inspection", "textile", "garment", "defects"],
        "priority": "high"
    },
    {
        "title": "Inventory Management for Yarn, Fabric, and Trims in Textile",
        "content": """
INVENTORY MANAGEMENT FOR TEXTILE MANUFACTURING (YARN, FABRIC, TRIMS)

TEXTILE RAW MATERIAL COMPLEXITY:
A garment manufacturer may manage 500+ active raw material SKUs — dozens of yarn counts/colors, multiple fabric qualities, hundreds of trim varieties (buttons, zippers, elastic, thread, labels, hangtags). Without systematic inventory, material costs spiral.

YARN AND FABRIC INVENTORY SPECIFICS:
- Unit of measurement: Yarn in KG or cones; fabric in meters or KG (knit fabric often in KG)
- Shade/lot management: Different purchase lots of same color fabric can have shade variation — must track lot-wise and use per-order
- Count and composition: Yarn count (e.g., 30s, 40s) and composition (100% cotton, 65/35 PC) are critical item attributes
- Shrinkage: Grey fabric shrinks on washing/processing; procurement plan must account for shrinkage factor

TRIM INVENTORY MANAGEMENT:
- Trim variety explosion: 10 styles × 5 colors × 3 size options = 150 different button SKUs
- Trim lead time: Branded trims (Coats thread, YKK zipper) have 2–4 week lead time from overseas
- Over-ordering to avoid stockout: Industry norm but creates accumulation of dead trim inventory
- Trim rationalization: Standardize trims across styles where possible; reduce variety

FABRIC REMNANT AND OFF-CUT MANAGEMENT:
- End bits (small remnant pieces after cutting): Calculate and record per cutting lot
- Use for: Sample making, small accessories, sale to rag traders
- ERPNext: Record end-bit yardage as by-product in cutting Work Order

INVENTORY VALUATION FOR TEXTILE:
- Yarn: FIFO or Moving Average; track count-wise, color-wise separately
- Fabric: By shade lot; FIFO within same shade lot
- WIP valuation: Grey fabric (purchased) + processing cost = greige value

ERPNext TEXTILE INVENTORY SETUP:
- Item attributes: Color, count, composition, lot number as item variants or custom fields
- Batch = shade lot for fabric; batch = production lot for yarn
- UOM conversion: Fabric in meters and KG (conversion rate per item)
- Reorder alerts by shade/color: Most critical — style-specific colors can't be substituted
- Remnant tracking: Sub-location for "remnant store" within fabric warehouse
        """,
        "tags": ["inventory", "yarn", "fabric", "trims", "textile", "shade_lot"],
        "priority": "high"
    },
    {
        "title": "Export Documentation and Merchandising for Textile Exporters",
        "content": """
EXPORT DOCUMENTATION AND MERCHANDISING MANAGEMENT FOR TEXTILE EXPORTERS

EXPORT DOCUMENTATION FLOW FOR TEXTILE:
Purchase Order from Buyer → PI (Proforma Invoice) → Production → Pre-Shipment Inspection → Packing → Shipping Bill → Bill of Lading → Invoice + Packing List → Payment (LC or TT)

KEY EXPORT DOCUMENTS FOR TEXTILE:
1. Commercial Invoice: Item description, quantity, unit price (FOB/CIF), total value in foreign currency
2. Packing List: Carton-wise, box-wise, piece-wise breakdown; carton dimensions and weight
3. Certificate of Origin: For claiming preferential duty in importing country (Form A for GSP, SAFTA for SAARC, AIFTA for ASEAN)
4. Quality/Inspection Certificate: Third-party PSI report or buyer-approved in-house QC sign-off
5. GST/Tax Invoice: For customs clearance in India (Shipping Bill filing)
6. Shipping Bill: Filed by customs broker with ICEGATE; required for customs clearance
7. Bill of Lading / Airway Bill: Transport document; issued by shipping line or airline

LETTER OF CREDIT (LC) IN TEXTILE TRADE:
- Common payment term for new buyers or large orders
- LC types: Sight LC (payment on presentation of documents), Usance LC (30/60/90 days after shipment)
- Document compliance: Every field in LC must match exactly — discrepancies lead to rejection
- ERPNext: Sales Invoice and Packing List must match LC terms exactly

MERCHANDISER'S ROLE AND WORKFLOW:
- Receives buyer Tech Pack (style specification, fabric details, construction, measurements)
- Converts to BOM, sources fabric and trims, creates sampling plan
- Manages Time & Action (T&A) calendar: Every milestone from order to shipment with responsibility and dates
- Coordinates with production, QC, factory for on-time delivery

T&A CALENDAR (TIME AND ACTION CALENDAR):
- Day 0: Order confirmed
- Day 5: BOM approved, fabric ordered
- Day 20: Fabric received, PP sample submitted to buyer
- Day 25: PP sample approved by buyer
- Day 30: Bulk production starts
- Day 50: Production complete, PSI called
- Day 55: Packing complete, Shipping Bill filed
- Day 57: Shipment on vessel

ERPNext FOR TEXTILE EXPORT:
- Export Sales Order with buyer PO number, destination country, payment terms (LC/TT/DA)
- Packing List generation from Delivery Note (carton-wise)
- Multi-currency invoicing: USD, EUR invoices with auto-conversion to INR for accounts
- Shipping tracker: AWB/BL number, vessel name, ETA — custom fields on Delivery Note
- FIRC tracking: Foreign Inward Remittance Certificate from bank; attach to payment entry
        """,
        "tags": ["textile_export", "export_documentation", "lc", "merchandising", "shipping"],
        "priority": "medium"
    },
    {
        "title": "Cost Reduction and Lean Manufacturing for Textile Units",
        "content": """
LEAN MANUFACTURING AND COST REDUCTION FOR TEXTILE MANUFACTURERS

Textile is a margin-competitive industry. With buyer prices stagnating and input costs rising, operational excellence is the primary lever for profitability improvement. Lean manufacturing techniques can reduce cost by 15–25% without capital investment.

LEAN TOOLS FOR TEXTILE MANUFACTURING:

1. 5S (SORT, SET IN ORDER, SHINE, STANDARDIZE, SUSTAIN):
   - Cutting room: Only tools in use should be on cutting table; everything else removed
   - Stitching line: Thread, needles, and attachments standardized per machine; nothing extra
   - Audit: 5S score posted on department notice board weekly; competition between lines
   - Impact: 10–15% productivity improvement through reduced motion waste

2. LINE BALANCING:
   - Every stitching line operation takes different time (SAM); fastest operation = bottleneck waits
   - Balance: Allocate 1 operator to fast operations, 2 to slow operations — smooth flow
   - Analysis: Measure each operation's actual cycle time; redistribute when imbalanced
   - Impact: Eliminates WIP pile-up between operations; improves flow efficiency

3. CHANGEOVER TIME REDUCTION (SMED):
   - Style changeover: How long does it take to go from finishing one style to first piece of new style?
   - Target: < 4 hours changeover time; world-class = < 2 hours
   - Method: Pre-positioning attachments, pre-programming machines, parallel activities
   - Impact: Enables smaller order acceptance (more flexible for buyers)

4. DEFECT ELIMINATION (POKA-YOKE):
   - Fix attachments that prevent wrong stitching (physical mistake-proofing)
   - Color-coded thread bobbins to prevent wrong thread use
   - Size guides at each machine so operator never cuts wrong length

OVERHEAD COST REDUCTION:
- Electricity: Variable frequency drives (VFD) on fans and compressors save 20–30% power
- Water: Rinse water recycling in dyeing reduces water consumption by 30–40%
- Chemical: Automatic chemical dispensing system reduces over-dosing by 10–15%

ERPNext LEAN METRICS:
- OEE (Overall Equipment Effectiveness): Planned production vs. actual; downtime tracking
- Line efficiency dashboard: Real-time efficiency per line per shift
- Defect rate trend: Weekly defect % by line and defect type
- SAM achievement: Planned SAM vs. actual SAM per operator per day
        """,
        "tags": ["lean_manufacturing", "5s", "line_balancing", "textile", "cost_reduction"],
        "priority": "medium"
    }
]

MFG_TEXTILE_ERPNEXT = [
    {
        "title": "ERPNext Style and BOM Management for Garment Manufacturers",
        "content": """
ERPNEXT STYLE AND BOM MANAGEMENT FOR GARMENT MANUFACTURERS

ITEM SETUP FOR GARMENT MANUFACTURING:
- Finished Garment Item: One item per style (e.g., Men's Polo Shirt Style A) with Color and Size as item variants
- Fabric Item: Separate item per quality (e.g., 100% Cotton 180 GSM Pique) — NOT per color (color managed via Batch)
- Trim Items: One item per trim specification (e.g., Button 15mm 4-hole White Round — Coats brand)
- Thread: Item per shade and ticket number

ITEM VARIANTS FOR FINISHED GARMENTS:
- Variant attributes: Color (Navy, White, Red) × Size (S, M, L, XL, XXL)
- Template item: "Men's Polo Style A"; variants: "Men's Polo Style A - Navy - L"
- Advantage: One BOM per style (not per color-size combination)

BOM STRUCTURE FOR GARMENT STYLE:
- Item: Men's Polo Style A (per piece)
- Raw Materials:
  - Fabric (item + shade lot via batch): 0.85 meters (including 5% wastage allowance)
  - Button 15mm: 2 nos
  - Thread 40/2: 0.015 cones (per piece)
  - Neck Tape: 35 cm
  - Label (brand): 1 no
  - Hangtag: 1 no
  - Polybag: 1 no
  - Carton (12 pieces): 0.0833 (1/12th carton per piece)

MULTI-BOM SCENARIOS:
- Same style, different fabric: Create BOM version per fabric quality
- Custom orders: Buyer may spec different trims; create buyer-specific BOM variant

WORK ORDER PER CUSTOMER ORDER:
- One Work Order per buyer PO (or per style per buyer PO)
- Links to: Sales Order (buyer PO), BOM (style), quantity, delivery date
- Material requirement: Auto-calculated from BOM × quantity
- Shade lot selection: At material issue stage, operator selects correct shade lot batch

TRACEABILITY IN GARMENT ERPONEXT:
- Sales Order → Work Order → Material Issue (batch with shade lot) → Production Output → Quality Inspection → Delivery Note
- Any customer complaint: Trace back through this chain to identify which fabric lot and which production line

PURCHASE PLANNING FOR TRIMS:
- Trim requirement report from Production Plan: Total button, thread, label requirement for next 4 weeks
- Group by trim supplier for efficient PO creation
- Track trim delivery against expected dates: Trim shortage is a common cause of production delay
        """,
        "tags": ["erpnext_setup", "garment_manufacturing", "bom", "style_management", "textile"],
        "priority": "high"
    },
    {
        "title": "ERPNext Job Work (Subcontracting) for Textile Manufacturers",
        "content": """
ERPNEXT JOB WORK AND SUBCONTRACTING FOR TEXTILE MANUFACTURERS

WHY TEXTILE USES JOB WORK EXTENSIVELY:
Textile production is inherently fragmented — a garment factory may own cutting and stitching but outsource embroidery, printing, washing, and dyeing to specialized job workers.

JOB WORK FLOW IN ERPNEXT:
1. Create Subcontracting Order (replaces old Purchase Order for job work)
2. Issue raw material to subcontractor: Stock Entry (Send to Subcontractor)
3. Receive finished goods: Subcontracting Receipt
4. Record job worker's invoice (for their service charges only — not for materials)

GST COMPLIANCE FOR JOB WORK IN TEXTILE:
- Issue Delivery Challan (not Tax Invoice) when sending material to job worker
- Material must be returned within 1 year (raw material) or 3 years (capital goods)
- Job worker's invoice: GST only on processing charges (not on value of fabric)
- If job worker has turnover < ₹20 lakh: Exempt from GST on processing (confirm with CA)

MANAGING MULTIPLE JOB WORKERS:
- Embroidery unit: Issues fabric + design thread; receives embroidered panels
- Dyeing unit: Issues grey fabric + color recipe; receives dyed fabric
- Washing/laundry: Issues stitched garments; receives washed + finished garments
- Track separately in ERPNext: Each job worker is a Supplier; separate Purchase Order and receipt per job worker

RECONCILIATION WITH JOB WORKERS:
- Monthly: Reconcile material sent vs. material returned; job worker must account for all material
- Tolerance: Accept up to 3% material variance as process loss; investigate anything above
- Rejection by job worker: Job worker may reject some material (damaged, wrong shade); receive back and update inventory

CRITICAL CONTROLS FOR JOB WORK:
- Never send material without Delivery Challan (GST compliance)
- Record every Delivery Challan in ERPNext: Update subcontracting order
- Track outstanding material at each job worker: Report monthly
- Advance payment to job workers: Record in ERPNext; adjust against invoices systematically

ERPNext CONFIGURATION:
- Supplier master: Tag suppliers as "Job Worker" type
- Subcontracting Order: Specify material to supply, expected return date, job description
- Job Worker Inventory Report: Outstanding material balance at each job worker location
- Quality Inspection at receipt: Run QC check on goods received from job worker before accepting into main stock
        """,
        "tags": ["job_work", "subcontracting", "textile", "erpnext", "gst_compliance"],
        "priority": "high"
    },
    {
        "title": "ERPNext Order Management and Customer Communication for Textile Exporters",
        "content": """
ERPNEXT ORDER MANAGEMENT FOR TEXTILE EXPORT MANUFACTURERS

EXPORT ORDER LIFECYCLE IN ERPNEXT:
Buyer PO received → Sales Order → Production Plan → Work Orders → Quality Inspection → Packing → Delivery Note → Sales Invoice → Payment

SALES ORDER SETUP FOR TEXTILE EXPORT:
- Customer: Buyer company (e.g., "H&M Germany GmbH")
- Currency: USD / EUR / GBP (foreign currency)
- Price List: Export Price List (in foreign currency)
- Delivery Terms: FOB Mumbai, CIF Hamburg — enter in ERPNext Terms field
- Payment Terms: 30% advance + 70% against documents (LC) — configure payment schedule
- Custom fields to add:
  - Buyer PO Number
  - Season (SS25, FW24)
  - Destination Country
  - Port of Discharge

T&A CALENDAR INTEGRATION:
- Create Project in ERPNext linked to Sales Order
- Project tasks = T&A milestones (Fabric Approval, PP Sample, Production Start, etc.)
- Assign responsible person and due date to each task
- Auto-reminder: Email alert 2 days before task due date
- T&A review: Weekly project status review shows on-time vs. delayed milestones

PACKING LIST GENERATION:
- ERPNext Delivery Note → Packing section → Enter carton details
- Custom fields: Carton number, gross weight, net weight, dimensions, pieces per carton
- Print packing list: Buyer-format packing list from ERPNext print format
- Barcode labels: Generate carton barcodes from ERPNext for scanning at customs

MULTI-CURRENCY INVOICING:
- Sales Invoice in USD: ERPNext auto-converts to INR at prevailing exchange rate
- Exchange gain/loss: ERPNext auto-posts when payment received at different rate
- FIRC (Foreign Inward Remittance Certificate): Record bank reference in payment entry

SHIPPING BILL AND CUSTOMS:
- Shipping Bill filed by customs broker via ICEGATE
- Enter Shipping Bill number and date in ERPNext Delivery Note (custom field)
- GST refund (IGST) claim: Submit GSTR-1 shipping bill data for auto-refund processing by customs
        """,
        "tags": ["export_order_management", "textile_export", "erpnext", "packing_list", "sales_order"],
        "priority": "medium"
    },
    {
        "title": "ERPNext Reporting and KPIs for Textile Manufacturing",
        "content": """
ERPNEXT REPORTING AND KPIs FOR TEXTILE MANUFACTURING MANAGEMENT

DAILY OPERATIONAL REPORTS (PRODUCTION):
- Line-wise Production Output vs. Target: Actual pieces vs. planned pieces per stitching line per shift
- Defect Rate Report: % defects by line, by operation, by defect type
- Work-in-Progress (WIP) Report: Pieces in each stage (cutting, stitching, finishing, packing)
- Job Worker Status: Pieces sent to each job worker vs. received back
- Raw Material Shortage Alert: Items below reorder level that can delay production

WEEKLY MANAGEMENT REPORTS:
- Order Completion Status: Each customer order's % completion vs. delivery date
- Fabric Consumption Efficiency: Actual vs. standard fabric consumption per style
- Trim Utilization: Trim consumed per piece vs. BOM standard
- Operator Efficiency: Individual operator SAM achievement % (from Job Cards)

MONTHLY FINANCIAL REPORTS:
- Product-wise Gross Margin: Selling price vs. actual production cost per style
- Overhead Absorption: Planned vs. actual overhead per unit
- Customer-wise Revenue and Margin: Which buyers are profitable?
- Export Realization: USD invoice value × exchange rate = INR realization; compare to target

COMPLIANCE REPORTS:
- Job Worker Reconciliation: Material issued vs. received per job worker
- GST IDS (Inverted Duty) Refund Calculation: Accumulated ITC eligible for refund this month
- Export Incentive Tracking: MEIS/RoSCTL claims status (submit on DGFT portal)

ERPNEXT CUSTOM DASHBOARDS FOR TEXTILE:
- Factory Floor Screen: Real-time line efficiency %, production count per shift (updates every 30 min)
- Export Order Dashboard: All open export orders, shipment dates, status (production/inspection/shipped)
- Accounts Dashboard: Outstanding receivables by buyer, FIRC received vs. pending, IDS refund status

ERPNext REPORTS SPECIFIC TO TEXTILE:
- Fabric Consumption Statement: Per style, per work order, actual vs. standard
- Batch-wise Fabric Utilization: Meters received vs. used vs. remnant per shade lot
- Style-wise Profitability: Revenue – direct material – job work – overhead = contribution per style
        """,
        "tags": ["reporting", "kpi", "textile_manufacturing", "erpnext", "dashboards"],
        "priority": "medium"
    }
]

MFG_TEXTILE_PAIN_POINTS = [
    {
        "title": "Top Pain Points: Fabric Shade Mismatch and Rework in Textile",
        "content": """
PAIN POINT: FABRIC SHADE MISMATCH AND QUALITY REWORK IN TEXTILE MANUFACTURING

PROBLEM DESCRIPTION:
Shade variation is the most costly and frequent quality problem in textile manufacturing — different dye lots of the same color look visually different, causing garments assembled from mixed lots to be rejected. Average rework cost from shade issues: ₹50–₹200 per garment; shipment rejection risk if undiscovered.

ROOT CAUSES:
- Multiple fabric lots purchased at different times (different dye batches) mixed in production
- Dyeing job worker not following approved shade standard consistently
- Shade approved in artificial light (office) but difference visible in sunlight (metamerism)
- No light box (D65 standard) for shade evaluation — visual judgment unreliable
- Cutting team not checking fabric lot before issuing to stitching line

IMPACT ON BUSINESS:
- Buyer rejects shipment: Revenue delayed or lost; freight paid both ways
- Rework: Cost of separating, re-stitching, re-inspecting
- Relationship damage: Buyer moves order to competitor after repeated shade issues
- Dyeing rework: Re-dyeing fabric = 2× dyeing cost + risk of fabric damage

HOW ERPNext ADDRESSES THIS:
1. Shade lot tracking via Batch: Every fabric receipt = unique batch with shade lot ID
2. Cut order planning: Custom doctype that allocates specific batch (shade lot) to each cutting layer
3. Batch-wise allocation: Stitching line only receives fabric from one batch per work order
4. Incoming shade approval: QC Inspection at receipt stage includes shade check vs. approved standard
5. Lab dip approval tracking: Custom workflow for buyer approval of color shade before bulk dyeing

PROCESS CONTROLS TO IMPLEMENT:
- Standard light box (D65, TL84, UV) for all shade evaluations — standardizes visual assessment
- One lot per order rule: Never mix shade lots within a buyer order shipment
- Shade continuity testing: Before production, assess all lots for visual continuity in store (view all lots together in one pass)
- Dye lab log: Every dyeing batch gets a color measurement reading (L*, a*, b* values) attached to batch record
- Barcode on each fabric roll: Roll barcode scanned at cutting; system validates correct lot for the work order
        """,
        "tags": ["shade_mismatch", "fabric_quality", "rework", "textile", "pain_points"],
        "priority": "high"
    },
    {
        "title": "Top Pain Points: Delivery Delays and Order Tracking in Textile Manufacturing",
        "content": """
PAIN POINT: ON-TIME DELIVERY (OTD) FAILURES AND ORDER TRACKING IN TEXTILE

PROBLEM DESCRIPTION:
On-time delivery performance is the #1 metric buyers use to evaluate textile suppliers. Indian garment exporters average 60–75% OTD; world-class is 95%+. Missing shipment dates incurs air freight penalties (3–5× sea freight), buyer chargebacks, and order loss.

COMMON CAUSES OF LATE DELIVERY:
- Fabric delayed: Job dyer delivered 7 days late; entire production delayed
- Sample approval late: Buyer takes 10 days instead of 5 to approve PP sample; production delayed
- Production underperformance: Line efficiency 50% instead of 70%; output behind plan
- Quality failure at PSI: Buyer inspector fails shipment; 3 days rework before re-inspection
- Trim shortage: Branded button arrived 4 days late; production line waiting

FINANCIAL COST OF LATE DELIVERY:
- Air freight penalty: Buyer charges difference between sea and air freight (₹50–200/kg difference)
- Chargeback: Buyer deducts 1–5% of order value as late delivery penalty
- Order cancellation: Buyer cancels if shipment > 2 weeks late (especially seasonal merchandise)
- Relationship cost: Buyer shifts next season allocation to supplier with better OTD

HOW ERPNext ADDRESSES DELIVERY TRACKING:
1. T&A Calendar as ERPNext Project: Every milestone has an assigned person and due date
2. Automatic delay alerts: Task overdue by 1 day → email to responsible person AND their manager
3. Production progress tracking: Daily Work Order completion % vs. required completion for delivery date
4. Material readiness check: Can system confirm all fabric + trims are received before production start?
5. Shipment countdown: "X days to shipment" displayed on Sales Order; red when less than 5 days

PREVENTIVE ACTIONS FOR OTD IMPROVEMENT:
- Fabric order 15 days before required (not 5 days before)
- Sample submission 5 days before buyer's deadline (not on deadline day)
- Build 5% contingency time in T&A (assume 1 day delay at each stage)
- Daily production meeting: 15-minute stand-up reviewing day's target vs. yesterday's achievement
- Escalation protocol: Any delay > 2 days triggers VP-level review and recovery plan
        """,
        "tags": ["on_time_delivery", "otd", "order_tracking", "textile", "pain_points"],
        "priority": "high"
    }
]


# ============================================================
# PHARMACEUTICAL MANUFACTURING — 15 CHUNKS
# ============================================================

MFG_PHARMA_COMPLIANCE = [
    {
        "title": "Drug License and Schedule M Compliance for Pharmaceutical Manufacturers",
        "content": """
DRUG LICENSE AND SCHEDULE M GMP COMPLIANCE FOR PHARMACEUTICAL MANUFACTURERS

The pharmaceutical manufacturing sector is the most heavily regulated manufacturing industry in India. Non-compliance results in product recalls, license cancellation, criminal prosecution, and in export markets, import alerts from international regulatory agencies.

DRUG MANUFACTURING LICENSE:
- Issued under Drugs and Cosmetics Act, 1940 by State Licensing Authority (SLA)
- Separate license for each category: Tablets/Capsules (Form 25), Liquids (Form 25), Topicals (Form 25D), Sterile products (Form 25)
- Qualified Person requirement: Registered Pharmacist or competent person as per Schedule M
- Renewal: Annual or biannual depending on state; non-renewal = immediate stop to production

SCHEDULE M — REVISED 2023:
Schedule M sets minimum standards for GMP (Good Manufacturing Practices). Revised Schedule M notified in December 2023 includes:
- WHO-GMP aligned requirements
- Enhanced documentation requirements
- Risk-based approach to manufacturing
- Electronic records and e-signatures acceptance
- Mandatory QMS (Quality Management System)

KEY SCHEDULE M REQUIREMENTS:
- Premises: Designed to prevent contamination, mix-up, cross-contamination
- Equipment: Qualified, calibrated, and validated
- Personnel: Written job descriptions, GMP training, health monitoring
- Documentation: Batch Manufacturing Records (BMR), Standard Operating Procedures (SOPs), Specifications
- Quality Control: QC lab with NABL accreditation preferred; retain all test records for 5 years post expiry
- Product Recall: SOP and mock drill mandatory; must complete within 48 hours if required

STATE vs. CENTRAL LICENSING:
- State License: For drugs sold only within the state (rare in practice)
- Central License (CDSCO): For drugs exported, for certain categories (vaccines, biologics, new drugs), for pan-India sale

CDSCO (CENTRAL DRUGS STANDARD CONTROL ORGANIZATION):
- National regulatory body under MoHFW
- Issues marketing authorization for new drugs
- Conducts GMP inspections for export-oriented manufacturers

ERPNext FOR PHARMA REGULATORY:
- License register: All drug licenses with numbers, validity dates, conditions — auto-alert 60 days before expiry
- Change control: Document and approve every change to process, equipment, raw material
- Regulatory audit trail: All transactions with user, timestamp — required under 21 CFR Part 11 equivalent
        """,
        "tags": ["drug_license", "schedule_m", "gmp", "pharmaceutical", "compliance", "cdsco"],
        "priority": "high"
    },
    {
        "title": "WHO-GMP and International Regulatory Compliance for Pharma Exporters",
        "content": """
WHO-GMP AND INTERNATIONAL REGULATORY COMPLIANCE FOR PHARMACEUTICAL EXPORTERS

India is the pharmacy of the world — supplying 60% of the world's vaccines and significant share of generic medicines. Accessing regulated markets requires international GMP certification.

WHO-GMP CERTIFICATION:
- Issued by WHO or national regulatory authorities (CDSCO for India)
- Required for export to: African countries (through WHO prequalification), UNICEF tenders, many developing country tenders
- Inspection by WHO inspector or CDSCO inspector on WHO's behalf
- Common inspection triggers: New product registration, periodic renewal (every 3 years)

US FDA (21 CFR PART 210/211) COMPLIANCE:
- For export to United States; mandatory for any API or finished dosage form sold in US market
- 21 CFR Part 211: Current Good Manufacturing Practice for finished pharmaceuticals
- 21 CFR Part 210: Minimum CGMP requirements
- FDA inspection: Pre-approval inspection (PAI) for NDA/ANDA approval; routine surveillance inspection
- Warning Letter: Issued for CGMP violations; can result in import alert (all shipments from facility blocked)
- Common FDA 483 observations: Data integrity violations, contamination, inadequate CAPA

EU GMP (EMA — EUROPEAN MEDICINES AGENCY):
- For export to European Union
- EU GMP Guidelines (Volume 4 of EU pharmaceutical legislation)
- Inspection by national authorities of EU member states (e.g., MHRA for UK, BfArM for Germany)
- GMP Certificate: Valid for 3 years; updated after each inspection

DATA INTEGRITY (CRITICAL FOR ALL REGULATORY MARKETS):
- All records: Paper or electronic, must be ALCOA+ compliant
- ALCOA+: Attributable, Legible, Contemporaneous, Original, Accurate + Complete, Consistent, Enduring, Available
- Common violations: Backdating entries, deleting chromatography runs, sharing login credentials
- ERPNext: User-specific login, immutable audit trail, no editing of submitted records — supports ALCOA+

ERPNext FOR REGULATORY EXPORT:
- Batch Manufacturing Records: Digital BMR in ERPNext with mandatory fields and approval workflow
- Document Management: SOPs, specifications, method validations — version controlled in ERPNext
- Change Control: Documented change requests with regulatory impact assessment and approval
- CAPA Management: Corrective and Preventive Actions tracked in ERPNext with due dates and verification
        """,
        "tags": ["who_gmp", "fda_compliance", "eu_gmp", "pharma_export", "data_integrity"],
        "priority": "high"
    },
    {
        "title": "Narcotics and Controlled Substance Compliance for Pharma Manufacturers",
        "content": """
NARCOTICS AND PSYCHOTROPIC SUBSTANCE COMPLIANCE FOR PHARMACEUTICAL MANUFACTURERS

Pharmaceutical manufacturers dealing in Schedule H1 drugs, narcotic or psychotropic substances face significantly enhanced regulatory requirements under the NDPS Act and specific drug regulatory guidelines.

NDPS ACT COMPLIANCE (NARCOTIC DRUGS AND PSYCHOTROPIC SUBSTANCES ACT, 1985):
- Any manufacturer producing or using narcotics (morphine, codeine, buprenorphine) or psychotropics (alprazolam, diazepam, tramadol) must hold a permit from Narcotics Commissioner or State Narcotics Cell
- Annual quota: Government allocates annual quota for production; cannot produce beyond quota
- Import/Export: Special NDPS permit from DCG (I) required for each import/export
- Record keeping: NDPS register must be maintained in Form prescribed under NDPS Rules; inspection on demand

SCHEDULE H AND H1 DRUG CONTROLS:
- Schedule H: Drugs sold only on prescription (antibiotics, steroids, many common medicines)
- Schedule H1 (Third Schedule): Enhanced restrictions — opioid analogues, habit-forming drugs
  - Cannot be sold without prescription
  - Pharmacist must maintain register of Schedule H1 sales
  - Manufacturer must report production and sale data quarterly to SLA
- Schedule X: Habit-forming drugs (barbiturates, stimulants); even stricter controls

DRUG RECALL PROTOCOL:
- Class I Recall: Serious health hazard; must be completed within 48 hours nationwide
- Class II Recall: Product may cause adverse health consequences; 72-hour initiation
- Class III Recall: Unlikely to cause harm but violates regulations; within 7 days
- CDSCO notification mandatory for all recalls; press release for Class I
- All returned goods: Quarantine and destroy under regulatory witness

GST COMPLIANCE FOR PHARMACEUTICALS:
- APIs (Active Pharmaceutical Ingredients): 18% GST
- Formulations: 12% GST (most medicines)
- Some specific medicines for chronic diseases: 5% or exempt
- Medical devices: 5–18% depending on classification
- ITC on API purchases: Claimable by pharma manufacturers

ERPNext FOR NARCOTICS COMPLIANCE:
- NDPS register: Custom doctype for narcotic raw material receipt, usage, and balance tracking
- Batch-level narcotic tracking: Know exact narcotic quantity in each production batch
- Quota monitoring: Alert when production approaches NDPS quota limit
        """,
        "tags": ["ndps", "schedule_h", "controlled_substances", "narcotics", "pharmaceutical", "compliance"],
        "priority": "high"
    },
    {
        "title": "Quality Management System (QMS) for Pharmaceutical Manufacturing",
        "content": """
QUALITY MANAGEMENT SYSTEM (QMS) FOR PHARMACEUTICAL MANUFACTURERS

A pharmaceutical QMS is not optional — it is the backbone of GMP compliance and regulatory approval. Every product released to market must be supported by documented evidence of quality.

CORE QMS DOCUMENTS:
1. SOPs (Standard Operating Procedures): Step-by-step instructions for every activity; reviewed annually
2. Specifications: For every raw material, packaging material, intermediate, and finished product
3. BMR (Batch Manufacturing Record): Complete record of one production batch; filled in real-time
4. BPR (Batch Packing Record): Record of packing operations for one batch
5. Analytical Methods: Validated test methods for QC testing
6. Validation Protocols: Process validation, cleaning validation, equipment qualification
7. Deviation Reports: Any departure from SOP or specification; root cause and CAPA
8. Change Control: Any change to process, specification, equipment, or supplier requires documented approval

BATCH RELEASE PROCEDURE:
1. Production complete → BMR review by production supervisor
2. QC testing complete → Certificate of Analysis (CoA) generated
3. QC Head review: All tests pass, no open deviations
4. Authorized Person (AP) sign-off: Final batch release authorization
5. Batch released to distribution → only now can product be sold

DEVIATION AND OOS (OUT OF SPECIFICATION) MANAGEMENT:
- OOS Result: Any test result outside approved specification
- Phase 1: Lab investigation (instrument error, analyst error?) within 3 days
- Phase 2: If Phase 1 invalidated, full process investigation within 10 days
- OOS confirmed: Product quarantine, CAPA initiated, regulatory notification if required
- Root cause categories: Human error, instrument/equipment failure, raw material quality, process issue

ANNUAL PRODUCT REVIEW (APR):
- Compile data for each product: All batch records, QC results, deviations, complaints, stability data
- Identify trends: Is process drifting? Are complaints increasing?
- Conclusions: Process validated and under control; or identify improvement actions
- Submitted to SLA (State Licensing Authority) as per Schedule M requirements

ERPNext QMS MODULES:
- Quality Inspection: Linked to each batch at multiple stages (RM receiving, in-process, finished goods)
- Non-Conformance Reports (NCR): Deviations, OOS, complaints — tracked with CAPA
- Document control: SOPs versioned; effective date, review date, approver tracked
- Change Control: Workflow with impact assessment and multi-department approval
        """,
        "tags": ["qms", "batch_release", "sop", "bmr", "pharmaceutical", "compliance"],
        "priority": "high"
    },
    {
        "title": "Pharmacovigilance and Post-Market Surveillance for Pharma Companies",
        "content": """
PHARMACOVIGILANCE AND POST-MARKET SURVEILLANCE FOR PHARMACEUTICAL MANUFACTURERS

Pharmacovigilance (PV) is the science and activities related to the detection, assessment, understanding, and prevention of adverse effects of medicines. It is mandatory under the New Drugs and Clinical Trials Rules, 2019.

REGULATORY REQUIREMENT FOR PV IN INDIA:
- All licensed pharmaceutical manufacturers must have a Pharmacovigilance system
- Designated PV officer (usually Medical Director or Senior Pharmacist)
- Adverse Drug Reaction (ADR) reporting to PVPI (Pharmacovigilance Programme of India) — operated by IPC (Indian Pharmacopoeia Commission)
- PVPI ADR Portal: adrpvpi.gov.in — mandatory online reporting

ADVERSE EVENT REPORTING TIMELINES:
- Serious, unexpected ADR (fatal or life-threatening): Report to CDSCO within 15 calendar days
- Serious, expected ADR: Report within 15 days but less urgently
- Non-serious ADR: Report quarterly (periodic safety update)
- Periodic Safety Update Report (PSUR): Annually for products approved in last 5 years

MARKET COMPLAINT HANDLING:
- Receive complaint → Log in complaint register → Classify (quality, efficacy, adverse reaction)
- Investigate: Retain complaint sample; retrieve batch records; QC testing of retained sample
- Root cause analysis: Is this an isolated event or systemic? → CAPA
- Respond to complainant: Acknowledge within 3 days; full response within 30 days
- Regulatory escalation: If complaint suggests systematic quality failure → consider recall

STABILITY TESTING:
- Mandatory to confirm shelf life under accelerated and real-time conditions
- Accelerated stability: 40°C/75% RH for 6 months → supports 24-month shelf life claim
- Real-time stability: 25°C/60% RH for full claimed shelf life period
- Stability station: Stability chambers (NABL calibrated) in QC lab; samples placed at defined time points

COLD CHAIN PRODUCTS (BIOLOGICS, VACCINES, INSULINS):
- 2–8°C storage throughout supply chain
- GDP (Good Distribution Practice) certification for cold chain medicines
- Temperature excursion management: Protocol for what to do when cold chain breaks

ERPNext FOR PHARMACOVIGILANCE:
- Complaint doctype: Log all product complaints with batch details and complainant information
- CAPA tracking: Each complaint or ADR → CAPA with owner, due date, verification
- Stability schedule: Remind QC team of stability pull-out dates per batch
- Recall tracking: If recall initiated, trace all batches distributed to distributors/customers
        """,
        "tags": ["pharmacovigilance", "adr_reporting", "post_market", "pharmaceutical", "complaint_handling"],
        "priority": "medium"
    }
]

MFG_PHARMA_BEST_PRACTICES = [
    {
        "title": "Batch Manufacturing Record (BMR) and Documentation for Pharma",
        "content": """
BATCH MANUFACTURING RECORDS (BMR) AND DOCUMENTATION MANAGEMENT FOR PHARMACEUTICAL MANUFACTURERS

The BMR is the heartbeat of pharmaceutical manufacturing — it is the complete, contemporaneous record of everything that happened during the production of one batch. A complete BMR is required for every batch release and for responding to regulatory inspections.

BMR STRUCTURE (CONTENTS):
1. Product name, formulation code, batch number, batch size, manufacturing date
2. Master Formula Reference (MFR): Which version of the formula was followed
3. Raw material details: Name, AR number (Analytical Release number), lot number, quantity weighed and by whom
4. Process steps: Each step with parameters (temperature, time, speed), actual values recorded, and signature of operator and supervisor
5. In-process checks: pH, viscosity, appearance, fill weight — recorded at prescribed intervals
6. Yield calculations: Theoretical yield vs. actual yield; reconciliation
7. Environmental conditions: Temperature and humidity of manufacturing area at start and end
8. Equipment used: Equipment ID, cleaning status verification, calibration status
9. Incidents or deviations: Any departure from SOP noted in real-time with deviation reference
10. QC release: Reference to Certificate of Analysis; QC Head sign-off

GOOD DOCUMENTATION PRACTICES (GDP) IN PHARMA:
- All entries: In indelible ink (never pencil)
- Correction: Single line through error, correct value, sign and date; no white-out/erasure
- Contemporaneous: Record at the time of action, never from memory later
- Never leave blank fields: Write "N/A" if not applicable
- Check weighing: Two-person verification for all raw material weighing

ELECTRONIC BATCH RECORDS (eBMR):
- Replacing paper BMR in modern facilities
- Must comply with 21 CFR Part 11 (US) or Annex 11 (EU) for electronic records and signatures
- Features: Audit trail, user authentication, time-stamp, no edit without authorization
- ERPNext supports eBMR concept through Quality Management module

ERPNext BMR IMPLEMENTATION:
- Work Order as electronic BMR backbone: Records batch, BOM used, materials issued
- Custom form for each product: QC checks, parameters, operator signatures (via user login)
- Attachment of raw data: Lab printouts, instrument data attached to Quality Inspection
- Batch approval workflow: Production → QC → Release → auto-update batch status
- BMR archival: Completed BMRs in ERPNext system; retained for 5 years post expiry
        """,
        "tags": ["bmr", "documentation", "batch_records", "gdp", "pharmaceutical", "best_practices"],
        "priority": "high"
    },
    {
        "title": "Inventory and Raw Material Management for Pharmaceutical Manufacturers",
        "content": """
INVENTORY AND RAW MATERIAL MANAGEMENT FOR PHARMACEUTICAL MANUFACTURERS

PHARMACEUTICAL INVENTORY UNIQUENESS:
Pharmaceutical raw material management differs from other industries in its documentation intensity, controlled substance tracking, quarantine requirements, and expiry criticality.

RAW MATERIAL STATUS SYSTEM:
Every raw material lot must be in one of these statuses — never in an ambiguous state:
1. Quarantine: Just received; awaiting QC testing (stored in designated quarantine area)
2. Under Test: QC analysis in progress
3. Approved: QC approved; ready for production use
4. Rejected: Failed QC; cannot be used; must be returned or destroyed
5. Expired: Past re-test date; requires re-testing or rejection
6. Sampled: QC sample taken; balance in quarantine

AR NUMBER (ANALYTICAL RELEASE NUMBER):
- Every raw material lot gets a unique AR number from QC on receipt
- AR number is referenced in BMR when the material is used in production
- Traceability: AR number → test reports → batch used in → finished product batch

EXPIRY AND RE-TEST DATE MANAGEMENT:
- Re-test date (not expiry): APIs have a "re-test date" after which material must be re-tested before use (they don't "expire" like food — they may still be fine but need verification)
- ERPNext: Batch master stores manufacturing date, re-test date, expiry date
- Alert at 60 days before re-test date: Initiate re-testing or return to supplier
- Expired material: Immediately move to "Rejected" status; quarantine; do not use

COLD CHAIN RAW MATERIALS:
- Temperature-sensitive APIs: Insulin, enzymes, vaccines components
- Store at manufacturer-recommended temperature (2–8°C, -20°C, -70°C for different materials)
- Temperature monitoring: Data logger in cold room; review log before using each lot
- Cold chain integrity on receipt: Check temperature during transit (packaging indicators or logger inside shipment)

SOLVENT AND HAZARDOUS CHEMICAL MANAGEMENT:
- Store solvents in dedicated, ventilated, fireproof solvent store
- Fire safety: No sparking electrical equipment in solvent store; earthing for all containers
- MSDS (Material Safety Data Sheet): Display at point of storage and use
- Quantity limits in production area: Only one day's requirement; rest in bulk store

ERPNext RAW MATERIAL MANAGEMENT FOR PHARMA:
- Batch → QC status field (Quarantine / Approved / Rejected / Expired)
- Block production stock entry if batch status ≠ Approved
- Expiry report: Weekly alert for batches within 60 days of re-test date
- AR number as batch ID for complete audit trail
        """,
        "tags": ["raw_material_management", "ar_number", "quarantine", "pharmaceutical", "inventory"],
        "priority": "high"
    },
    {
        "title": "Validation and Equipment Qualification for Pharmaceutical Manufacturing",
        "content": """
VALIDATION AND EQUIPMENT QUALIFICATION FOR PHARMACEUTICAL MANUFACTURERS

Validation is the documented evidence that a process, equipment, or system consistently produces a result meeting predetermined specifications. It is a fundamental GMP requirement — "if it isn't documented, it didn't happen."

EQUIPMENT QUALIFICATION STAGES:
1. DQ (Design Qualification): Is the design of the equipment suitable for the intended use?
2. IQ (Installation Qualification): Is the equipment installed correctly as per manufacturer specifications?
3. OQ (Operational Qualification): Does the equipment operate as intended across its design range?
4. PQ (Performance Qualification): Does the equipment perform consistently in the actual production environment?
All four stages documented with protocols, execution records, and summary reports.

PROCESS VALIDATION:
- 3 consecutive commercial-scale batches at nominal operating parameters → all must pass specification
- Demonstrates process is reproducible and under control
- Required for: New products, significant process changes, site transfer
- Statistical approach: Process capability indices (Cpk) calculated for critical quality attributes

CLEANING VALIDATION:
- Demonstrates cleaning procedure removes previous product residue and cleaning agents to acceptable levels
- Sampling: Swab sampling or rinse water sampling from worst-case locations on equipment
- Acceptance criteria: Not more than 1/1000th of minimum therapeutic dose in maximum daily dose of next product (HBEL-based limits)
- Visual inspection: Equipment surface must be visibly clean before chemical test

ANALYTICAL METHOD VALIDATION:
- Before using a QC test method, validate it to demonstrate it is fit for purpose
- Parameters validated: Specificity, accuracy, precision, linearity, range, LOD, LOQ, robustness
- Reference: ICH Q2(R1) guideline

COMPUTER SYSTEM VALIDATION (CSV):
- Any computerized system used in GMP environment must be validated
- ERPNext: If used for BMR, QMS, or batch records, requires CSV
- GAMP 5 framework: Categorize software, validate per risk category

ERPNext VALIDATION SUPPORT:
- Equipment master: IQ/OQ/PQ status, next qualification due date per equipment
- Calibration log: Calibration date, calibration lab, certificate number, next due date
- Validation protocol workflow: Draft → Review → Approve → Execute → Report → Approved
- CSV documentation: ERPNext can maintain its own validation documentation within the system
        """,
        "tags": ["validation", "equipment_qualification", "process_validation", "pharmaceutical", "gmp"],
        "priority": "high"
    },
    {
        "title": "Procurement and Approved Vendor List for Pharmaceutical Raw Materials",
        "content": """
APPROVED VENDOR LIST (AVL) AND PROCUREMENT FOR PHARMACEUTICAL MANUFACTURERS

In pharmaceuticals, raw material quality is product quality. Unapproved or unqualified vendors are the single largest source of product recalls globally. Every ingredient must come from a qualified, approved supplier.

APPROVED VENDOR LIST (AVL) PROCESS:
1. Identification: Technical team identifies potential supplier
2. Questionnaire: Send Supplier Qualification Questionnaire (SQQ) — covers GMP status, QC capability, regulatory filings
3. Sample: Obtain samples from 2–3 batches; QC tests against specifications
4. On-site audit: QA team audits supplier's facility (if critical raw material)
5. Approval: Quality Head approves supplier; add to AVL with approved grade and specification
6. Re-qualification: Periodic re-audit (every 2–3 years) or on any significant change

KEY CATEGORIES FOR QUALIFICATION:
- API suppliers: Strictest qualification; must hold CEP (Certificate of Suitability, European) or DMF (Drug Master File, US) if exporting to regulated markets
- Excipient suppliers: Qualify for pharmaceutical grade; food/industrial grade not acceptable
- Packaging material suppliers: Validate packaging compatibility (migration testing for primary packaging)

PURCHASE SPECIFICATION vs. SUPPLIER SPECIFICATION:
- Always buy against your own approved specification (not supplier's)
- Specify: Identity test, purity, moisture, heavy metals, microbial limits, residual solvents (for APIs)
- Include regulatory parameters: EP/USP/BP grade requirement if applicable

COA (CERTIFICATE OF ANALYSIS) VERIFICATION:
- Every batch: Supplier sends CoA with test results
- Do not blindly accept CoA: Must verify identity test at minimum in-house
- Reduced testing for approved suppliers: After qualification, may test fewer parameters but never skip identity
- Fake CoA risk: Cross-check lot number with supplier if suspect

ERPNext FOR PHARMACEUTICAL PROCUREMENT:
- Supplier master: AVL status (Approved/Probationary/Suspended/Rejected), last audit date, next audit due
- Purchase Order: Only from AVL-approved suppliers for each material
- GRN with AR number: Quarantine batch created on receipt; QC triggered automatically
- CoA upload: Attach supplier CoA to batch record at receipt
- Price tracking: API prices fluctuate significantly; track price trends per supplier per quarter
        """,
        "tags": ["approved_vendor_list", "avl", "supplier_qualification", "raw_material", "pharmaceutical"],
        "priority": "high"
    }
]

MFG_PHARMA_ERPNEXT = [
    {
        "title": "ERPNext Setup and Configuration for Pharmaceutical Manufacturing",
        "content": """
ERPNEXT SETUP FOR PHARMACEUTICAL MANUFACTURING

PHARMA-SPECIFIC ERPNEXT CONFIGURATION:

ITEM MASTER SETTINGS:
- All pharma items: "Has Batch No" = Yes; "Has Expiry Date" = Yes
- Item types: API, Excipient, Packaging Primary, Packaging Secondary, Finished Drug Product, Intermediates
- Custom fields per item: Product code, Pharmacopoeia grade (IP/BP/USP/EP), regulatory status, storage condition
- Finished products: Additional custom fields — formulation type (Tablet/Capsule/Syrup), strength, pack size

BATCH MASTER CUSTOM FIELDS:
- AR Number (Analytical Release Number)
- QC Status: (Quarantine / Under Test / Approved / Rejected / Expired)
- Manufacturing Date
- Expiry Date / Re-test Date
- Supplier Lot Number
- CoA Reference
- Batch released by (QC Head employee ID)

WAREHOUSE STRUCTURE FOR PHARMA:
- Raw Material Quarantine Store
- Raw Material Approved Store
- Solvent Store (with fire safety classification)
- Production Floor (WIP)
- Finished Product Quarantine
- Finished Product Approved Store
- Rejected / Destruction Area
- Stability Samples Store

QUALITY MANAGEMENT CONFIGURATION:
- Quality Inspection templates per item: Define all QC parameters, acceptance criteria, test methods
- Inspection required: "Before Receipt" (RM incoming QC) + "Before Delivery" (FG batch release)
- QC workflow: Lab analyst enters results → QC Head reviews → Approve/Reject batch

ERPNEXT MANUFACTURING WORKFLOW FOR PHARMA:
Production Plan → Work Order (= Production Batch) → Material Issue (RM from Approved store) → In-process QC Inspections → Manufacture (FG to Quarantine store) → QC Final Testing → Batch Release (move to Approved store) → Delivery Note

USER ACCESS CONTROL:
- QC staff: Can create and submit Quality Inspections; cannot override batch status without QA Head approval
- Production staff: Create Job Cards, material issue; cannot override QC status
- QA Head: Full QMS access; batch release authority
- No backdating: ERPNext setting to prevent posting entries before current date
        """,
        "tags": ["erpnext_setup", "pharma_configuration", "pharmaceutical", "modules", "qms"],
        "priority": "high"
    },
    {
        "title": "ERPNext CAPA, Deviation, and Non-Conformance Management for Pharma",
        "content": """
ERPNEXT CAPA, DEVIATION, AND NON-CONFORMANCE MANAGEMENT FOR PHARMACEUTICAL

CAPA (CORRECTIVE AND PREVENTIVE ACTION):
The CAPA system is the quality system's engine for improvement. Every deviation, OOS, complaint, or audit finding must link to a CAPA.

CAPA DOCTYPE CONFIGURATION IN ERPNEXT:
Fields to include:
- CAPA Number (auto-generated)
- Source: Deviation / OOS / Complaint / Audit Finding / Stability Failure / Other
- Source Reference: Link to the originating Deviation, Complaint, or Inspection record
- Description of Issue
- Impact Assessment: What was the impact? Product affected? Regulatory notification needed?
- Root Cause Analysis (5-Why or Fishbone): Document the investigation
- Corrective Action: Specific action to fix the immediate problem (with owner and due date)
- Preventive Action: Action to prevent recurrence (with owner and due date)
- Effectiveness Check: How will we know the action worked? (with verification due date)
- Status: Open / In Progress / Pending Verification / Closed
- Approver sign-off: QA Head approval to close

DEVIATION MANAGEMENT:
- Planned Deviation: Pre-approved change to SOP for a specific batch or period
- Unplanned Deviation: Any unexpected departure from SOP that occurred; must be documented immediately
- Deviation doctype: Link to batch, describe deviation, categorize as critical/major/minor, assign investigation owner
- Impact on batch: Hold batch pending investigation; release only after QA Head approval

AUDIT FINDING MANAGEMENT:
- Internal audit or external regulatory audit generates findings
- Classify: Major / Minor / Observation
- Every finding: CAPA assigned with committed date
- CAPA response to regulatory authority: Submitted within 15 days for WHO/FDA inspections

OOS (OUT-OF-SPECIFICATION) TRACKING:
- OOS doctype: Links to batch, test method, result obtained vs. specification
- Phase 1 conclusion: Lab error (invalidated) or genuine OOS
- Phase 2 investigation records attached
- Disposition decision: Rework, reject, or release with justification
- Regulatory notification if OOS confirmed for released product

ERPNext IMPLEMENTATION APPROACH:
- Build CAPA as a custom doctype in Frappe (ERPNext framework)
- Link from Quality Inspection (rejection), Complaint, and Deviation doctypes
- CAPA aging report: All open CAPAs beyond due date — weekly management review
- Trend analysis: Top 5 CAPA sources → focus quality improvement programs
        """,
        "tags": ["capa", "deviation", "non_conformance", "erpnext", "pharmaceutical", "quality"],
        "priority": "high"
    },
    {
        "title": "ERPNext Serialized Tracking and Regulatory Reporting for Pharma",
        "content": """
ERPNEXT SERIALIZED TRACKING AND REGULATORY REPORTING FOR PHARMACEUTICAL

SERIALIZATION IN PHARMACEUTICAL (TRACK AND TRACE):
- India mandate: Serialization of export medicines to US/EU mandatory (as per buyer country requirements)
- Each saleable unit: Unique serial number (GTIN + batch + expiry + serial = GS1 DataMatrix barcode)
- Aggregation: Individual pack → shipper box → pallet — hierarchical tracking

GS1 BARCODING FOR PHARMA:
- GTIN (Global Trade Item Number): Assigned by GS1 India; identifies the product
- DataMatrix barcode on each pack: Encodes GTIN, batch, expiry, serial number
- Aggregation barcode on box/pallet: Encoded with all individual pack serials within

ERPNext SERIAL NO TRACKING:
- Enable "Has Serial No" for finished pharmaceutical items where serialization required
- Serial numbers generated at packing stage (one per saleable unit)
- Delivery Note: Serial numbers assigned to each customer/order
- If returned: Serial number marked "returned" and investigated before any reuse

REGULATORY REPORTING IN INDIA:
- Drugs Controller: Annual report of manufacture, sales, and exports (Form 18)
- NDPS (if applicable): Quarterly returns to Narcotics Commissioner
- CDSCO Market Surveillance: Adverse drug reaction reports via PVPI portal

EXPORT REGULATORY DOCUMENTATION:
- Free Sale Certificate: Issued by CDSCO; certifies product is approved for sale in India; required by many importing countries
- CEP (Certificate of Suitability): For API manufacturers exporting to Europe; issued by EDQM
- WHO Type 3 Certificate: For finished product export; issued by CDSCO on behalf of WHO

ERPNext COMPLIANCE REPORTS FOR PHARMA:
- Batch Manufacturing Report: All batches produced in a month with product, quantity, date
- Distribution Audit Trail: Every batch → which distributors received it → when
- QC Summary Report: All test results by batch; pass/fail rates by product
- Stability Schedule Report: Upcoming stability pull-out dates with batch and storage condition
- CAPA Aging Report: Open CAPAs by owner and due date
- Expiry and Re-test Date Report: All batches approaching expiry or re-test date in next 60 days
        """,
        "tags": ["serialization", "track_and_trace", "gs1", "pharma_reporting", "pharmaceutical", "erpnext"],
        "priority": "medium"
    },
    {
        "title": "ERPNext for Pharmaceutical Production Cost Control",
        "content": """
ERPNEXT PRODUCTION COST CONTROL FOR PHARMACEUTICAL MANUFACTURERS

COST STRUCTURE IN PHARMACEUTICAL MANUFACTURING:
1. Raw Material Cost: API + excipients + packaging; typically 40–60% of selling price for generics
2. Manufacturing Cost: Labor + utilities (electricity, water, compressed air, nitrogen) + consumables
3. Quality Control Cost: Lab reagents, reference standards, testing, stability
4. Regulatory Cost: Registration fees, licenses, dossier preparation
5. Overhead: Factory depreciation, rent, administrative overheads

STANDARD COST SETUP IN ERPNEXT FOR PHARMA:
- BOM per formulation: API quantity per batch + all excipients + packaging components
- Routing per formulation: Granulation, blending, compression, coating, packing — each operation with labor time and machine time
- Overhead rate: Machine-hour based or as % of direct cost (configure in Manufacturing Settings)
- Standard cost per batch = BOM cost + Routing (labor + machine) cost + Overhead

BATCH-WISE COST VARIANCE ANALYSIS:
- After production: Compare actual RM consumed (from Stock Entry) vs. BOM standard
- Common variances in pharma: Yield variance (batch yield lower than standard), usage variance (higher excipient use)
- Investigate: Any variance > 2% of batch value requires deviation and investigation
- Trend: If variance consistently negative on one product → SOP needs revision or specification needs review

QC COST ALLOCATION:
- QC lab costs allocated to products based on testing time per batch
- High QC cost items: Sterile injectables, complex analytical tests → higher overhead per unit
- Outsourced testing cost: Charge directly to batch

PRODUCT PROFITABILITY FOR PHARMA:
- Generic portfolio analysis: Rank all products by gross contribution (revenue – variable cost)
- Fixed cost absorption: Only products with positive gross margin AND sufficient volume to absorb share of fixed cost should be retained in portfolio
- Discontinuation decision: Products with < 5% gross margin or < 50 batches/year → consider discontinuing or outsourcing manufacture

ERPNext KEY PHARMA FINANCIAL REPORTS:
- Product-wise gross margin: Revenue per unit – standard cost per unit
- Batch-wise actual cost: Actual material + labor (from Job Cards) per batch
- Overhead recovery report: Overhead allocated vs. overhead budget
- Annual product review financial section: Volume, revenue, cost trends for each product
        """,
        "tags": ["cost_control", "standard_cost", "profitability", "pharmaceutical", "erpnext"],
        "priority": "medium"
    }
]

MFG_PHARMA_PAIN_POINTS = [
    {
        "title": "Top Pain Points: Regulatory Inspection Preparedness in Pharma",
        "content": """
PAIN POINT: REGULATORY INSPECTION PREPAREDNESS AND DATA INTEGRITY FAILURES IN PHARMA

PROBLEM DESCRIPTION:
Regulatory inspections (FDA, WHO, EU) are the most existential risk for pharmaceutical manufacturers. An import alert (US FDA) or certificate suspension (WHO) can stop all export revenue immediately. The primary triggers for adverse inspection outcomes have shifted to data integrity rather than visible GMP failures.

MOST COMMON REGULATORY FAILURES:
1. Data Integrity (DI) Violations: #1 cause of FDA Warning Letters to Indian pharma
   - Test and discard failing results; run again until passing (OOS data manipulation)
   - Shared login credentials (cannot attribute data to individual)
   - Backdated entries in batch records
   - Unofficial "rough draft" notebooks later transcribed
2. Out-of-Specification (OOS) Investigation Deficiencies: Inadequate or template-copy investigations
3. CAPA Ineffectiveness: Promises made to regulators not implemented; same issues recur
4. Batch Record Completeness: Blank fields, corrections without counter-signature
5. Laboratory Equipment Calibration: Expired calibrations used; or calibration certificates not retrievable

PREPARATION FOR FDA/WHO INSPECTION:
Pre-inspection (6 months before anticipated):
- Mock inspection: Internal team poses as inspectors; identify gaps before real inspector does
- Data integrity audit: Review all computerized system audit trails; check for anomalies
- CAPA closure: Close all open CAPAs; verify effectiveness
- Documentation completeness: Sample 20 BMRs at random; check completeness

During inspection:
- Escort inspector professionally; answer only what is asked — no volunteering extra information
- Never answer "I don't know" without "I will find out within X hours"
- All requested documents within 30 minutes or acknowledge timeline
- 483 observations: Acknowledge professionally; commit to timeline; no defensive responses

Post-inspection (if 483 or Warning Letter received):
- 15 business days to respond to Form 483 observations
- Warning Letter response: 30 days; must demonstrate systemic correction, not just batch-level fix
- Third-party consultant for preparation of response if major issues

HOW ERPNext SUPPORTS INSPECTION READINESS:
- Immutable audit trail: Every record shows who did what and when — cannot be altered retroactively
- User-specific logins: No shared passwords — each action attributable to one person
- Document control: Every SOP has version history; effective version clearly identified
- CAPA tracker: Inspector can review all CAPAs — open, closed, overdue — with evidence
- OOS tracker: Complete investigation records per OOS incident with timelines
        """,
        "tags": ["regulatory_inspection", "data_integrity", "fda", "pharma", "warning_letter", "pain_points"],
        "priority": "high"
    },
    {
        "title": "Top Pain Points: Raw Material Availability and API Price Volatility in Pharma",
        "content": """
PAIN POINT: API AVAILABILITY RISK AND RAW MATERIAL PRICE VOLATILITY IN PHARMACEUTICAL

PROBLEM DESCRIPTION:
India imports 70–80% of its API (Active Pharmaceutical Ingredient) requirements from China. When Chinese factories face regulatory action, natural disaster, or export restrictions, Indian pharma manufacturers face supply disruption and price spikes simultaneously.

SUPPLY RISK FACTORS:
- Single-source APIs: Many APIs have only 1–2 global manufacturers; supply constraint = price + availability crisis
- NDPS-controlled APIs: Government allocation limits quantity available regardless of price
- Quality failure at API supplier: Regulatory action on API supplier = your product's supply chain fails
- Geopolitical risk: India-China tensions periodically threaten API imports
- Port/logistics disruption: COVID-era shipping disruptions showed multi-month delays

PRICE VOLATILITY IMPACT:
- API price can swing 50–200% in a year for some products (acetic acid, paracetamol, vitamins saw this during COVID)
- Selling price to distributor fixed by long-term contracts → cost increase not recoverable immediately
- NPPA (National Pharmaceutical Pricing Authority) controls prices for essential medicines → no flexibility to raise price even when API price spikes

RISK MITIGATION STRATEGIES:
1. Dual Sourcing: Qualify 2 suppliers for each API; alternate orders to maintain relationship with both
2. Safety Stock: 3–4 months of API stock for critical products (vs. typical 1–2 months)
3. Indian API alternatives: Wherever Indian API manufacturers exist, qualify and use (less vulnerable to China disruption)
4. Formula flexibility: Where possible, design formulation that accepts API from multiple sources (with appropriate revalidation)
5. Price escalation clauses: In new distributor contracts, include raw material escalation clause beyond ±15% API price change

HOW ERPNext HELPS:
1. API inventory visibility: Stock balance by API, batch, expiry — always know position
2. Coverage calculation: (API stock on hand) / (Average monthly API consumption) = months of coverage
3. Price trend tracking: Purchase order history → API price trend by supplier
4. Supplier qualification status: AVL status and audit due dates — flag suppliers approaching requalification
5. Low-coverage alert: When months of coverage < 2 months, automatic Material Request triggered
6. Alternative supplier: Alternate supplier linked in Item master; quickly switch if primary fails
        """,
        "tags": ["api_availability", "supply_risk", "raw_material", "pharma", "pain_points", "china_api"],
        "priority": "high"
    }
]


# ============================================================
# CROSS-CUTTING MANUFACTURING — 12 CHUNKS
# ============================================================

MFG_CROSSCUTTING = [
    {
        "title": "Manufacturing Overhead Allocation and Product Costing Across Industries",
        "content": """
MANUFACTURING OVERHEAD ALLOCATION AND PRODUCT COSTING FOR MANUFACTURERS

WHAT IS MANUFACTURING OVERHEAD?
All manufacturing costs that are NOT direct material or direct labor:
- Factory rent and depreciation
- Utilities (electricity, water, gas, steam)
- Equipment depreciation
- Quality control lab costs
- Factory supervisor salaries
- Maintenance staff and spares
- Factory insurance

WHY OVERHEAD ALLOCATION MATTERS:
Without proper allocation, some products appear more profitable than they are (under-costing) while others seem unviable (over-costing). Bad costing leads to wrong pricing decisions, wrong product mix decisions, and eventually business failure.

OVERHEAD ALLOCATION METHODS:

1. MACHINE HOUR RATE (Most accurate for capital-intensive manufacturing):
   - Total factory overhead / Total machine hours available = Rate per machine hour
   - Product cost = BOM cost + (machine hours consumed × machine hour rate)
   - Suitable for: Food processing, pharma, chemical manufacturing

2. LABOR HOUR RATE (Better for labor-intensive manufacturing):
   - Total factory overhead / Total labor hours available = Rate per labor hour
   - Product cost = BOM cost + (labor hours consumed × labor hour rate)
   - Suitable for: Garments, handicrafts, assembly operations

3. PERCENTAGE OF DIRECT MATERIAL (Simplest):
   - Overhead rate = 20% of direct material cost (for example)
   - Product cost = BOM cost × 1.20
   - Suitable for: Simple product mix where overhead scales with material

ACTIVITY-BASED COSTING (ABC) FOR COMPLEX MANUFACTURERS:
- Assigns overhead to activities (machine setup, quality testing, material handling)
- Allocates activity costs to products based on how much of each activity they consume
- More accurate but complex; worthwhile for manufacturers with diverse product ranges

ERPNext OVERHEAD CONFIGURATION:
- Manufacturing Settings: Add overhead cost per Work Order (flat amount or % of material)
- Job Card time tracking: Enables labor hour-based allocation
- Work Center: Define hourly operating cost per work center (machine hour rate built in)
- Cost Center: Factory overhead costs collected here; allocated out to products at period-end
        """,
        "tags": ["overhead_allocation", "product_costing", "manufacturing", "accounting", "costing"],
        "priority": "high"
    },
    {
        "title": "Preventive Maintenance and OEE for Manufacturing Equipment",
        "content": """
PREVENTIVE MAINTENANCE AND OEE FOR MANUFACTURING BUSINESSES

WHY PREVENTIVE MAINTENANCE:
Equipment breakdown in manufacturing costs 3–10× more than planned maintenance. A food processing line breakdown during peak season, a pharma reactor breakdown mid-batch, or a garment line breakdown on deadline day — all have disproportionate cost impact.

OEE (OVERALL EQUIPMENT EFFECTIVENESS):
OEE = Availability × Performance × Quality
- Availability = (Planned production time – Downtime) / Planned production time
- Performance = Actual output / Maximum theoretical output
- Quality = Good output / Total output
- World-class OEE: 85%+; Indian SME average: 40–60%

INTERPRETING OEE:
- Low Availability: Equipment breaking down or long setup/changeover → prioritize maintenance and SMED
- Low Performance: Running at less than full speed → operator training, minor stoppages, speed losses
- Low Quality: High defect/rejection rate → process optimization, better QC

PREVENTIVE MAINTENANCE PROGRAM:

DAILY CHECKS (BY OPERATOR):
- Lubrication points: Visual check, top up if needed
- Temperature gauges, pressure gauges: Verify in normal range
- Safety devices: Emergency stop, guards — verify operational
- Noise and vibration: Unusual sounds reported immediately

WEEKLY MAINTENANCE:
- Belt tension check and adjustment
- Filter cleaning/replacement
- Hydraulic fluid level
- Cooling system check

MONTHLY/QUARTERLY:
- Full mechanical inspection by qualified engineer
- Calibration of measuring instruments
- Safety valve testing
- Alignment check

ANNUAL OVERHAUL:
- Complete disassembly and inspection
- Replace worn parts preemptively
- Pressure vessel certification (statutory requirement)

ERPNext MAINTENANCE MODULE:
- Maintenance Schedule: Define maintenance tasks, frequency, responsible person per equipment
- Auto-generated Maintenance Visits: System creates maintenance tasks on schedule
- Downtime Log: Record actual downtime events with duration and cause
- Spare Parts Inventory: Track critical spares in ERPNext stock; reorder when minimum reached
- Equipment History: All maintenance records against each equipment ID
- OEE Dashboard: Calculate availability from downtime log; performance and quality from production data
        """,
        "tags": ["preventive_maintenance", "oee", "equipment", "manufacturing", "downtime"],
        "priority": "high"
    },
    {
        "title": "Supply Chain Risk Management for Manufacturers",
        "content": """
SUPPLY CHAIN RISK MANAGEMENT FOR MANUFACTURING BUSINESSES

WHY SUPPLY CHAIN RISK IS CRITICAL FOR MANUFACTURERS:
Unlike trading, manufacturers cannot substitute raw material easily. A different API, different fabric, or different food ingredient may require formulation change, regulatory re-approval, or buyer re-approval — taking months. Supply chain disruptions can stop production entirely.

SUPPLY CHAIN RISK CATEGORIES:

1. SUPPLY DISRUPTION RISKS:
   - Supplier financial failure
   - Supplier regulatory/quality issue
   - Single-source materials (no alternative)
   - Geopolitical/trade disruption (China imports for API, textile fiber)
   - Natural disasters at supplier location or transit route

2. DEMAND VOLATILITY RISKS:
   - Large customer cancellation mid-production
   - Sudden demand spike beyond capacity
   - Product becoming obsolete (regulatory change, new competition)

3. LOGISTICS RISKS:
   - Port congestion (affects import-export timelines)
   - Freight rate spikes (2020–2022 container crisis saw 5–10× freight increases)
   - Customs delays

4. INTERNAL RISKS:
   - Key employee departure (master formulator, critical machine operator)
   - Equipment breakdown (single critical equipment, no backup)
   - IT failure (ERP down = production and dispatch halt)

RISK MITIGATION FRAMEWORK:

DUAL SOURCING:
- For every top-5 raw material: Qualify 2 suppliers; give 70/30 volume split
- Both suppliers remain active and familiar with your requirements

SAFETY STOCK POLICY:
- High-risk materials (single source, long lead time): 3–4 months safety stock
- Standard materials: 4–6 weeks safety stock
- ERPNext: Set per-item safety stock level; reorder when stock < safety stock + lead time demand

SUPPLY CHAIN VISIBILITY:
- Track PO delivery performance: % on-time by supplier
- Flag chronic late suppliers; replace or reduce dependence
- SCOR (Supply Chain Operations Reference) metrics: OTIF, fill rate, days of supply

ERPNext SUPPLY CHAIN RISK TOOLS:
- Supplier performance dashboard: On-time delivery %, quality rejection % per supplier
- Days of supply report: Months of coverage per critical raw material
- Open PO aging: POs past expected delivery date — follow up immediately
- Alternative item mapping: For each key RM, identify and qualify alternative; link in Item master
        """,
        "tags": ["supply_chain_risk", "dual_sourcing", "safety_stock", "manufacturing", "risk_management"],
        "priority": "high"
    },
    {
        "title": "Energy Management and Sustainability for Manufacturing",
        "content": """
ENERGY MANAGEMENT AND SUSTAINABILITY FOR MANUFACTURING BUSINESSES

ENERGY AS A COST DRIVER:
Energy is typically 8–20% of total manufacturing cost. For energy-intensive industries (textile dyeing, food processing, pharma API synthesis), it can reach 25–30%. Energy efficiency directly improves competitiveness.

ENERGY CONSUMPTION BENCHMARKS:
- Food processing: 0.3–0.8 kWh per kg of product (varies widely by product)
- Textile dyeing: 8–15 kWh per kg fabric processed + 80–150 liters water
- Pharma tablets: 0.2–0.5 kWh per 1,000 tablets
- Garment manufacturing: 2–4 kWh per garment

ENERGY SAVING OPPORTUNITIES (QUICK WINS):
1. Power Factor Correction: Capacitor banks to improve power factor from 0.7 to 0.95 → 10–15% reduction in electricity bill
2. VFD (Variable Frequency Drives): On pumps, fans, compressors → 20–40% energy saving
3. LED Lighting: Replace fluorescent and metal halide → 60–70% lighting energy reduction
4. Waste Heat Recovery: Use exhaust heat from boiler/generator for pre-heating water or feed
5. Air Compressor Optimization: Fix leaks (5–30% of compressed air is leaked in typical factory); optimize pressure settings
6. Solar Rooftop: Captive solar reduces grid electricity consumption; 5–7 year payback typical

REGULATORY REQUIREMENTS:
- PAT Scheme (Perform Achieve Trade): Energy conservation targets for designated consumers (large industries)
- BEE Energy Audit: Mandatory for designated consumers; voluntary but valuable for SMEs
- Renewable Purchase Obligation (RPO): Some states mandate renewable energy % in total consumption

WATER CONSERVATION IN MANUFACTURING:
- Water recycling: Cooling tower blowdown recycling; rinse water reuse in food/textile
- Wastewater treatment: ETP effluent recycled to process (ZLD approach)
- Rainwater harvesting: Roof runoff captured for non-contact water needs

ERPNext ENERGY MONITORING:
- Custom Energy Log doctype: Daily electricity meter reading, diesel consumption
- Product-wise energy allocation: If metered at line level, allocate energy cost to products
- Energy KPI dashboard: kWh per unit of production; trend over months
- Maintenance: Schedule VFD service, capacitor bank testing, solar panel cleaning
        """,
        "tags": ["energy_management", "sustainability", "energy_efficiency", "manufacturing", "vfd"],
        "priority": "medium"
    },
    {
        "title": "New Product Development (NPD) Process for Manufacturers",
        "content": """
NEW PRODUCT DEVELOPMENT (NPD) PROCESS FOR MANUFACTURING BUSINESSES

STAGE-GATE NPD PROCESS FOR MANUFACTURERS:
A stage-gate process breaks product development into stages with go/no-go decision points (gates) between them. This prevents resource waste on projects that should have been killed earlier.

STAGE 0: IDEA AND SCREENING
- Source: Market research, customer request, competitor analysis, sales team feedback
- Evaluation criteria: Market size, manufacturing feasibility, regulatory requirements, investment needed
- Gate decision: Proceed to concept stage or kill (budget: 0, time: 1–2 weeks)

STAGE 1: CONCEPT AND FEASIBILITY
- Lab scale prototype: Formulate/produce small quantity; test against target specification
- Market validation: Show prototype to 5–10 target customers; get feedback
- Financial feasibility: Rough cost estimate vs. target selling price → target margin achievable?
- Regulatory assessment: What approvals are needed? (FSSAI for food, CDSCO for pharma, BIS for some products)
- Gate: Feasibility confirmed? Proceed to pilot?

STAGE 2: PILOT AND DEVELOPMENT
- Pilot production: 3–5 batches at 10–20% of commercial scale; optimize recipe/process
- Specification development: Set formal specifications for raw material and finished product
- Shelf life study: Accelerated stability testing initiated
- Packaging development: Design, material selection, regulatory compliance (label)
- Gate: Pilot results satisfactory? Cost confirmed? Sample approved by buyer?

STAGE 3: COMMERCIALIZATION
- Commercial scale validation: 3 consecutive batches at full scale (required for pharma; recommended for food)
- Regulatory filing: Submit to FSSAI/CDSCO/BIS as applicable; wait for approval
- Sales material: Pricing, product data sheet, samples for customers
- Launch plan: Phased rollout vs. full launch

ERPNext NPD TRACKING:
- Project doctype: One project per NPD; linked to estimated commercialization date
- BOM development: Create and version draft BOMs during development; finalize on commercialization
- Sample Sales Order: Internal sales of pilot samples to customer for testing
- Quality Inspection template: Developed during NPD; finalized before commercialization
- NPD dashboard: All active NPD projects, stage, expected launch date, % tasks complete
        """,
        "tags": ["npd", "new_product_development", "stage_gate", "manufacturing", "innovation"],
        "priority": "medium"
    },
    {
        "title": "GST for Manufacturers: Input Tax Credit, Job Work, and Reverse Charge",
        "content": """
GST COMPLIANCE FOR MANUFACTURERS: ITC, JOB WORK, AND REVERSE CHARGE

INPUT TAX CREDIT (ITC) FOR MANUFACTURERS:
Manufacturers have the most comprehensive ITC eligibility — GST paid on virtually all business inputs can be credited against output GST liability.

ELIGIBLE ITC FOR MANUFACTURERS:
- Raw materials and packaging
- Capital goods (machinery, equipment) — 100% ITC claimable in first year
- Consumables (lab supplies, maintenance materials)
- Freight inward
- Professional services (CA, consulting, testing lab)
- Rent on factory premises
- Utilities (electricity not taxable under GST; no ITC)

BLOCKED ITC (CANNOT CLAIM):
- Motor vehicles (unless in transportation business)
- Construction of immovable property (factory building construction ITC blocked)
- Food and beverages for employees
- Club memberships
- Beauty products and cosmetic services

JOB WORK PROVISIONS FOR MANUFACTURERS:
- Section 143, CGST Act: Goods sent to job worker for processing without treating as supply
- Delivery Challan: Issue DC (not invoice) when sending RM/semi-finished goods to job worker
- Time limit: Return goods within 1 year (RM) or 3 years (capital goods) or supply from job worker's premises
- Job worker's invoice: GST on processing charges only; job worker can claim ITC on his consumables

REVERSE CHARGE MECHANISM (RCM) FOR MANUFACTURERS:
Manufacturers may need to pay GST under RCM when:
- Purchasing from unregistered suppliers (certain categories)
- Importing services (e.g., foreign consultant, offshore software subscription — OIDAR services)
- Legal services from individual advocate: RCM at 18%
- Security services from unregistered provider: RCM at 18%
- Freight from GTA (Goods Transport Agency): RCM at 5% if transport supplier not in GST

ERPNext GST CONFIGURATION FOR MANUFACTURERS:
- ITC categories in Purchase Invoice: Mark each invoice as "ITC Available," "ITC Not Available," "Blocked ITC"
- Job work flow: Subcontracting module with Delivery Challan instead of Purchase Invoice
- RCM invoices: Mark as Reverse Charge = Yes in Purchase Invoice; system posts GST to both input and output simultaneously
- GSTR-2B reconciliation: Monthly exercise before filing GSTR-3B
- IDS refund (for inverted duty manufacturers like textile): ERPNext calculates accumulated ITC eligible for refund
        """,
        "tags": ["gst", "itc", "job_work", "reverse_charge", "manufacturing", "compliance"],
        "priority": "high"
    },
    {
        "title": "Digital Manufacturing and Industry 4.0 for Indian SME Manufacturers",
        "content": """
DIGITAL MANUFACTURING AND INDUSTRY 4.0 FOR INDIAN MANUFACTURING SMEs

THE DIGITAL MANUFACTURING OPPORTUNITY:
Indian manufacturing SMEs that adopt digital technologies outperform peers by 15–25% on productivity and 10–20% on quality metrics. The cost of entry has dropped dramatically — cloud software, affordable sensors, and mobile technology make digital manufacturing accessible below ₹5 lakh investment for most SMEs.

DIGITAL MATURITY LEVELS FOR MANUFACTURERS:
Level 1 (Analog): Paper records, spreadsheets, manual tracking
Level 2 (Digital Backbone): ERP (ERPNext) for core operations — inventory, production, accounting
Level 3 (Connected): Real-time data from machines and processes fed into ERP
Level 4 (Intelligent): Analytics, AI-driven predictions, autonomous adjustments

LEVEL 2 → LEVEL 3 UPGRADES (PRACTICAL AND AFFORDABLE):

1. DIGITAL QUALITY INSPECTION:
   - Replace paper QC sheets with tablet-based digital inspection
   - Inspector enters results on tablet → auto-saved to ERPNext Quality Inspection
   - Eliminates transcription errors; real-time visibility

2. PRODUCTION COUNTER (MACHINE-LEVEL OUTPUT TRACKING):
   - Inductive proximity sensor on machine output conveyor; counts units per minute
   - Data via Raspberry Pi or PLC to ERPNext via API
   - Real-time production count vs. target on floor screen
   - Cost: ₹15,000–₹50,000 per machine

3. ENERGY MONITORING:
   - Smart energy meter on each production line
   - kWh per unit of production tracked in real time
   - Alerts when energy consumption exceeds benchmark (equipment inefficiency indicator)

4. COLD ROOM TEMPERATURE MONITORING:
   - IoT temperature logger (e.g., SensoTech, LocoNav, or custom Arduino-based)
   - Sends reading every 15 minutes to cloud; alerts on deviation
   - Integrated with ERPNext batch records for cold chain compliance evidence
   - Cost: ₹5,000–₹20,000 per sensor point

5. BARCODE/QR CODE AT PRODUCTION:
   - Print batch barcode label at production; scan at every stage
   - Eliminates manual batch entry errors
   - Full traceability with minimal effort

ERPNext AS DIGITAL BACKBONE:
ERPNext is the Level 2 foundation — all other Level 3 upgrades feed into it via APIs or custom integrations. Build ERPNext first, then add IoT/sensors layer progressively.
        """,
        "tags": ["digital_manufacturing", "industry_4_0", "iot", "technology", "manufacturing", "sensors"],
        "priority": "medium"
    },
    {
        "title": "Waste Management, Scrap Tracking, and By-Product Accounting for Manufacturers",
        "content": """
WASTE MANAGEMENT, SCRAP, AND BY-PRODUCT ACCOUNTING FOR MANUFACTURERS

WHY SCRAP AND BY-PRODUCT TRACKING MATTERS:
Manufacturing generates waste, scrap, and by-products. In most Indian SMEs, scrap is sold informally with no accounting — this represents an untracked revenue and an unchecked loss. Systematic tracking reveals true cost of production and identifies reduction opportunities.

DEFINITIONS:
- Scrap: Unavoidable residue with minimal/no value (dust, clippings, trimmings); usually sold to scrap dealer
- Waste: Material lost in process with no recoverable value (evaporation, spillage, combustion)
- By-product: Secondary useful output from production (tomato skin from ketchup, oil cakes from oil pressing, yarn waste from textile)
- Rework: Material that failed QC but can be reprocessed to meet specification

BY-PRODUCT EXAMPLES BY INDUSTRY:
- Food processing: Tomato skin/seeds (can feed animals), whey from paneer, bran from flour milling
- Textile: Yarn waste (regenerated fiber), fabric off-cuts (rag trade), effluent recovered fiber
- Pharma: Granule fines (reprocessed into tablets), cleaning solvents (recovered for reuse)

ACCOUNTING FOR SCRAP AND BY-PRODUCTS:
Two approaches:
1. CREDIT TO COST: By-product value reduces production cost of main product (by-product at NRV — Net Realizable Value)
2. SEPARATE REVENUE: By-product recognized as separate revenue item at time of sale

ERPNext SCRAP AND BY-PRODUCT HANDLING:
- BOM: Enter by-products with estimated quantity and valuation rate
- Production Stock Entry: Record actual by-product quantity at manufacture stage
- Scrap Account: Scrap value credited to "Scrap Income" account; net COGS reduced
- Sale of scrap: Create Item "Steel Scrap" or "Cloth Waste"; record Sales Invoice to scrap dealer (GST applicable if scrap is taxable)

WASTE REDUCTION PROGRAM:
- Measure: Calculate actual waste % per batch for top 10 materials
- Target: Set 5–10% reduction target vs. current baseline
- Track: Weekly waste rate by material; compare to target
- Investigate: Any batch with waste > 2× baseline triggers root cause analysis
- ERPNext: Scrap Entry comparison: Planned scrap (from BOM) vs. actual scrap per batch
        """,
        "tags": ["waste_management", "scrap", "by_product", "manufacturing", "accounting"],
        "priority": "medium"
    },
    {
        "title": "Workforce Planning and Skill Development for Manufacturing Units",
        "content": """
WORKFORCE PLANNING AND SKILL DEVELOPMENT FOR MANUFACTURING BUSINESSES

MANUFACTURING WORKFORCE CHALLENGES IN INDIA:
- Skill gap: ITI-trained operators insufficient in supply; fresh graduates need significant on-job training
- Attrition: Manufacturing towns with multiple factories create competition for skilled workers
- Multi-skill: Single-skill workers limit production flexibility
- Language: Migrant workers from different states create communication barriers

WORKFORCE PLANNING FRAMEWORK:
Step 1: Capacity plan → How many units do we need to produce per month?
Step 2: Productivity standard → Units per operator per shift (from historical data or industry benchmark)
Step 3: Headcount required = Production target / Operator productivity / Working days
Step 4: Compare to current headcount → gap = hiring need; surplus = redeployment or efficiency improvement

SKILL MATRIX FOR MANUFACTURING:
- List all critical skills: Machine operation, QC testing, material handling, maintenance, supervisory
- Rate each employee: 0 (not trained), 1 (trained, needs supervision), 2 (competent), 3 (can train others)
- Identify gaps: Skills where < 2 employees are at level 2 or 3 = vulnerability
- Training plan: Address vulnerabilities; develop backup for each critical skill

ON-THE-JOB TRAINING STRUCTURE:
Week 1: Product and company orientation; safety training
Week 2: Machine familiarization (observing experienced operator)
Week 3: Supervised operation (experienced operator supervises)
Week 4: Independent operation with daily quality check by supervisor
Month 2: Full independence; monthly assessment

STATUTORY TRAINING REQUIREMENTS:
- Safety training: Factories Act requires workers to be trained on safety equipment, emergency procedures
- Fire safety: Annual fire drill; fire extinguisher handling training
- GMP training (pharma, food): Required under Schedule M / FSSAI; minimum annual
- Hazardous chemical handling (chemical manufacturers): HASAW Act compliance

ERPNext HR FOR MANUFACTURING:
- Employee Skill matrix: Custom doctype to record skill level per employee per skill
- Training calendar: Scheduled training events; attendance recorded
- Training effectiveness: Assessment score post-training; track improvement
- Shift roster: ERPNext Shift management for 2-shift or 3-shift factory operations
- Overtime tracking: Auto-flag when operator exceeds statutory overtime limits
        """,
        "tags": ["workforce_planning", "skill_development", "training", "manufacturing", "hr"],
        "priority": "medium"
    },
    {
        "title": "Manufacturing Finance: Working Capital, Term Loans, and MSME Benefits",
        "content": """
MANUFACTURING FINANCE: WORKING CAPITAL, CAPITAL INVESTMENT, AND MSME BENEFITS

MANUFACTURING FINANCIAL STRUCTURE:
Unlike trading, manufacturers have significant fixed assets (machinery, factory building) and higher working capital requirement (raw material inventory + WIP + finished goods + receivables – payables).

WORKING CAPITAL FOR MANUFACTURERS:
Working capital requirement = (RM days + WIP days + FG days + Debtor days – Creditor days) × Daily Cost of Sales
- RM days: How many days of raw material stock? (food: 30 days; pharma: 90 days; textile: 45 days)
- WIP days: Production cycle time (1 day for simple food; 30 days for pharma with stability holds)
- FG days: How long does FG sit before dispatch? (target < 15 days)
- Debtor days: Customer payment terms (45–90 days for institutional customers)
- Creditor days: Supplier credit (30–60 days) — reduces working capital need

BANK FINANCE FOR MANUFACTURERS:
1. Cash Credit (CC): Against RM + WIP + FG stock and debtors; 10–13% per annum
2. Term Loan: For machinery and factory construction; 5–10 year tenure; 9–12% interest
3. ECLGS (Emergency Credit Line Guarantee Scheme): MSME COVID relief; may still be available in some form
4. MSME Loan without collateral (CGTMSE): Up to ₹2 crore with credit guarantee; no collateral
5. NBFC equipment finance: For specific machinery purchase; asset-backed; 12–18%

MSME BENEFITS FOR REGISTERED MANUFACTURERS:
- Priority Sector Lending: Banks mandated to allocate credit to MSME; easier loan access
- GeM Portal: Government procurement marketplace; MSMEs get purchase preference
- Delayed Payment Protection (MSMED Act): If large company delays payment beyond 45 days, liable to pay 3× bank rate compound interest
- Government tender preferences: MSMEs get price preference in government tenders
- TReDS (Trade Receivables Discounting System): MSME can discount invoices on TReDS platform for immediate cash; large corporate buyer pays at due date

ERPNext FOR MANUFACTURING FINANCE:
- Project vs. actual CapEx tracking: Track capital investment against budgeted project cost
- Loan management: EMI schedule, interest accrual, outstanding balance
- Working capital analysis: Custom report showing RM days, WIP, FG days, debtor and creditor days
- Stock statement auto-generation: Monthly statement for bank CC account renewal
        """,
        "tags": ["manufacturing_finance", "working_capital", "msme_benefits", "term_loan", "capex"],
        "priority": "high"
    },
    {
        "title": "ERPNext Implementation Roadmap for Manufacturing SMEs",
        "content": """
ERPNEXT IMPLEMENTATION ROADMAP FOR MANUFACTURING SMALL AND MEDIUM ENTERPRISES

WHY ERPNext IMPLEMENTATIONS FAIL (AND HOW TO AVOID):
60–70% of ERP implementations fail to meet their objectives. For manufacturing SMEs, the most common failure causes are: scope creep, inadequate training, incorrect setup, and no process change management.

PHASE-WISE IMPLEMENTATION APPROACH (12–16 WEEKS):

PHASE 1 — FOUNDATION (Weeks 1–4):
- Chart of Accounts setup: Revenue, COGS, expenses, assets, liabilities
- Customer and Supplier master data migration
- Item master creation: All items with correct UOM, item groups, reorder levels
- Warehouse setup: All storage locations
- GST configuration: GSTIN, HSN codes, tax templates
- Opening balances: Stock, debtors, creditors, bank balances
Deliverable: Company is live on basic financial and inventory functions

PHASE 2 — OPERATIONS (Weeks 5–10):
- BOM creation: All active products with current recipe and routing
- Work Order workflow: Test end-to-end production cycle
- Purchase workflow: PO → GRN → Invoice → Payment
- Sales workflow: SO → Delivery Note → Invoice → Payment
- Quality Inspection setup: Templates per item; link to GRN and Delivery
Deliverable: Factory operations running through ERPNext

PHASE 3 — COMPLIANCE (Weeks 11–13):
- E-invoicing setup and testing (if applicable)
- E-Way Bill integration testing
- GST return auto-population testing (GSTR-1, GSTR-3B)
- Payroll setup: Salary structures, EPF/ESIC configuration
Deliverable: Compliance reports auto-generated from ERPNext

PHASE 4 — REPORTING AND HANDOFF (Weeks 14–16):
- Management dashboard configuration
- Custom reports per management requirement
- Training: All user roles trained on their specific workflows
- Go-live support: Dedicated support for first month
Deliverable: Management independently using ERPNext for decision making

CHANGE MANAGEMENT — CRITICAL SUCCESS FACTORS:
- CEO/Owner visible support: If top management doesn't use ERPNext, team won't
- No parallel systems: Kill the spreadsheets after Go-live; no safety net encourages adoption
- Champions: One power user per department who owns the system in their area
- Quick wins: Demonstrate value within 30 days (e.g., inventory accuracy improvement visible immediately)
        """,
        "tags": ["erpnext_implementation", "roadmap", "manufacturing", "change_management", "erp"],
        "priority": "high"
    },
    {
        "title": "Intellectual Property and Trade Secret Protection for Manufacturers",
        "content": """
INTELLECTUAL PROPERTY AND TRADE SECRET PROTECTION FOR MANUFACTURERS

TYPES OF IP RELEVANT TO MANUFACTURERS:
1. PATENT: For novel products or processes; 20-year monopoly on the invention
2. TRADEMARK: Brand name, logo, packaging design; renewable indefinitely
3. TRADE SECRET: Recipes, formulations, processes not filed as patent; protected by secrecy
4. COPYRIGHT: Packaging artwork, instruction manuals, software
5. GEOGRAPHICAL INDICATION (GI): For products linked to a specific region (Darjeeling tea, Kolhapur chappals)

PATENT PROTECTION FOR MANUFACTURERS:
- File at Indian Patent Office (IPO) for India protection; via PCT route for international
- Patentable: Novel process, novel composition, novel use of existing compound (with conditions)
- Not patentable in India: Pure discovery, mathematical method, software (as such), business method, plants/animals
- Timeline: 2–5 years from filing to grant (Indian patent)
- Cost: ₹8,000–₹25,000 for filing (MSME rates lower); legal fees additional

TRADE SECRET PROTECTION (MOST PRACTICAL FOR FOOD AND PHARMA):
- Maintain secrecy: Limit access to recipe/formula to essential personnel only
- Non-Disclosure Agreement (NDA): With all employees, contractors, and partners who have access
- Compartmentalization: No single person knows the entire formula (Cola's "secret recipe" strategy)
- IT security: Formula stored in encrypted, access-controlled system
- When trade secret protection fails: Employee joins competitor and replicates → civil suit for breach of NDA

TRADEMARK FOR MANUFACTURERS:
- Register brand name and logo with Trade Marks Registry (Ministry of Commerce)
- Class matters: Register in all product classes you sell in
- Cost: ₹4,500–₹9,000 per class (MSME/startup rates)
- Process: Filing → Examination → Publication (4 months objection window) → Registration
- International: Madrid Protocol for registration in multiple countries via WIPO

ERPNext FOR IP MANAGEMENT:
- Product master: Add patent number, filing date, expiry for patented products
- License agreements: Track IP licensing arrangements if licensing your IP to others
- NDA tracking: Record all NDAs with employees and suppliers; alert when NDA expiry approaches
- Design files: Store packaging artwork (label, box design) with version control in ERPNext File Manager
        """,
        "tags": ["intellectual_property", "patent", "trademark", "trade_secret", "manufacturing"],
        "priority": "medium"
    }
]


# ============================================================
# MASTER STRUCTURE: All 60 Manufacturing Chunks
# ============================================================

ALL_MANUFACTURING_CHUNKS = [
    # Food Processing — 18 chunks
    {"f3iche": "manufacturing", "industry": "Food Processing", "kb_type": "compliance",
     "chunks": MFG_FOOD_COMPLIANCE},
    {"f3iche": "manufacturing", "industry": "Food Processing", "kb_type": "best_practices",
     "chunks": MFG_FOOD_BEST_PRACTICES},
    {"f3iche": "manufacturing", "industry": "Food Processing", "kb_type": "erpnext_setup",
     "chunks": MFG_FOOD_ERPNEXT},
    {"f3iche": "manufacturing", "industry": "Food Processing", "kb_type": "pain_points",
     "chunks": MFG_FOOD_PAIN_POINTS},

    # Textile — 15 chunks
    {"f3iche": "manufacturing", "industry": "Textile", "kb_type": "compliance",
     "chunks": MFG_TEXTILE_COMPLIANCE},
    {"f3iche": "manufacturing", "industry": "Textile", "kb_type": "best_practices",
     "chunks": MFG_TEXTILE_BEST_PRACTICES},
    {"f3iche": "manufacturing", "industry": "Textile", "kb_type": "erpnext_setup",
     "chunks": MFG_TEXTILE_ERPNEXT},
    {"f3iche": "manufacturing", "industry": "Textile", "kb_type": "pain_points",
     "chunks": MFG_TEXTILE_PAIN_POINTS},

    # Pharmaceutical — 15 chunks
    {"f3iche": "manufacturing", "industry": "Pharmaceutical", "kb_type": "compliance",
     "chunks": MFG_PHARMA_COMPLIANCE},
    {"f3iche": "manufacturing", "industry": "Pharmaceutical", "kb_type": "best_practices",
     "chunks": MFG_PHARMA_BEST_PRACTICES},
    {"f3iche": "manufacturing", "industry": "Pharmaceutical", "kb_type": "erpnext_setup",
     "chunks": MFG_PHARMA_ERPNEXT},
    {"f3iche": "manufacturing", "industry": "Pharmaceutical", "kb_type": "pain_points",
     "chunks": MFG_PHARMA_PAIN_POINTS},

    # Cross-cutting Manufacturing — 12 chunks
    {"f3iche": "manufacturing", "industry": "Cross-cutting", "kb_type": "best_practices",
     "chunks": MFG_CROSSCUTTING},
]


def count_chunks():
    total = 0
    for category in ALL_MANUFACTURING_CHUNKS:
        count = len(category["chunks"])
        print(f"  {category['industry']} | {category['kb_type']}: {count} chunks")
        total += count
    print(f"\n  TOTAL: {total} chunks")

if __name__ == "__main__":
    count_chunks()
