# containers/knowledge_base/project_manufacturing_kb_chunks.py

project_manufacturing_kb_chunks = [
    {
        "title": "Batch Production in ERPNext for Chemical Manufacturing",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "manufacturing",
        "tags": ["batch production", "work order", "yield", "epoxy", "traceability"],
        "content": """
        BATCH PRODUCTION IN ERPNEXT FOR CHEMICAL MANUFACTURING
        
        Chemical manufacturing is entirely batch-centric. Every gallon of resin or hardener must be traceable back to the mixing tank in case of a field failure.
        
        ERPNext Setup:
        1. Batch Tracking: Ensure 'Has Batch No' is checked in the Item Master for all resins, hardeners, and finished goods. 
        2. Work Orders: Production is managed via 'Work Orders'. The system generates a unique Batch ID upon completion.
        3. Yield Variance: Chemical processes have high yield loss due to solvent evaporation and tank cling. Use 'Material Consumption' set to 'Manual' instead of 'Backflush' to record exactly what was used vs. what was produced, accurately capturing yield loss in the stock ledger.
        
        Industry Context:
        If a floor fails 6 months after installation, the manufacturer must determine if it was a bad chemical batch or field error. ERPNext's Batch tracking allows the QA team to recall the exact 'Work Order' and see if the disperser overheated or if the wrong hardener was used.
        """
    },
    {
        "title": "BOM Management for Epoxy/PU Formulations",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "manufacturing",
        "tags": ["bom", "formulation", "uom", "part a", "part b", "mix ratio"],
        "content": """
        BOM MANAGEMENT FOR EPOXY/PU FORMULATIONS
        
        Plural-component chemical systems (Part A Resin + Part B Hardener) are manufactured separately and must NEVER be combined in the same Bill of Materials (BOM) for manufacturing.
        
        ERPNext Setup:
        1. Separate BOMs: Create one BOM for 'Epoxy Base - Part A' and a completely separate BOM for 'Catalyst - Part B'.
        2. UOM Conversions: Factory raw materials are bought in weight (Lbs/Kg) but finished goods are sold in volume (Gallons/Liters). The Item Master must have exact UOM conversion factors based on the specific gravity of the chemical.
        3. Scrap and Process Loss: Add expected evaporation or filtration loss as a 'Scrap %' on the specific solvent/resin rows in the BOM.
        
        Industry Context:
        Chemical recipes (formulations) require letdown adjustments. A batch might need extra solvent to hit a target viscosity. ERPNext BOMs provide the baseline, but the system must allow operators to over-consume specific raw materials on the Work Order to account for these real-time tinting or thinning adjustments.
        """
    },
    {
        "title": "Batch Expiry and Shelf Life for Chemicals",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "inventory",
        "tags": ["batch expiry", "shelf life", "isocyanates", "fefo", "stock"],
        "content": """
        BATCH EXPIRY AND SHELF LIFE FOR CHEMICALS
        
        Many chemical components, specifically catalysts like isocyanates and certain amines, have strict shelf lives (e.g., 6 to 12 months) and degrade rapidly due to moisture.
        
        ERPNext Setup:
        1. Item Master: Check 'Has Expiry Date' and define 'Shelf Life in Days' for sensitive chemical items.
        2. Auto-Calculation: When a Batch is created via a Purchase Receipt (raw materials) or a Work Order (finished goods), ERPNext automatically calculates the Expiry Date.
        3. FEFO Valuation: While default valuation is FIFO, expiration dates force a First-Expired-First-Out (FEFO) physical picking strategy. Configure Stock Settings to 'Do Not Allow Expired Batch' to prevent shipping dead hardener to a project site.
        
        Industry Context:
        Shipping expired catalyst to a site guarantees the floor will not cure (a "tacky floor" nightmare). ERPNext acts as a hard stop. Sales managers should utilize the 'Batch-Wise Balance Report' to identify near-expiry stock and sell it at a discount before it becomes hazardous waste.
        """
    },
    {
        "title": "Quality Inspection for Chemical Batches",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "quality",
        "tags": ["quality inspection", "hegman", "viscosity", "qa", "in-process"],
        "content": """
        QUALITY INSPECTION FOR CHEMICAL BATCHES
        
        Quality control happens at three stages: receiving raw bulk chemicals, in-process manufacturing, and final batch approval.
        
        ERPNext Setup:
        1. QA Templates: Create 'Quality Inspection Templates' for different product families. Example: "PU Topcoat QA" with parameters like Viscosity (CPS), Hegman Grind (microns), and Color (Delta E).
        2. In-Process QC: Link Quality Inspections to specific 'Job Cards' (e.g., after the milling operation) to ensure dispersion is correct before adding letting-down solvents.
        3. Approval Gates: Use ERPNext workflow rules to block the 'Stock Entry (Manufacture)' until the linked Quality Inspection is marked as 'Accepted'.
        
        Industry Context:
        A bad batch of epoxy can cost tens of thousands in field rework. QC must take a sample of Part A, mix it with Part B in the lab, and verify the 'Pot Life' and 'Cure Time' before the ERPNext system allows the factory to package the 500-gallon batch into retail pails.
        """
    },
    {
        "title": "Raw Material Management (Resins, Hardeners, Pigments)",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "inventory",
        "tags": ["raw materials", "hazmat", "warehousing", "procurement"],
        "content": """
        RAW MATERIAL MANAGEMENT (RESINS, HARDENERS, PIGMENTS)
        
        Chemical plants handle hazardous materials (Hazmat). Procurement and storage are dictated by safety regulations (flammability, VOCs) and bulk logistics.
        
        ERPNext Setup:
        1. Segregated Warehouses: Create strictly defined warehouses in ERPNext: 'RM-Flammables', 'RM-Dry Powders', 'RM-Bulk Resins'. 
        2. Min/Max Stock Rules: Set up 'Auto Material Requests' based on minimum stock levels for base resins, taking into account volatile global petrochemical lead times.
        3. Custom Fields: Add custom fields in the Item Master for 'Hazmat Class', 'UN Number', and 'VOC Content (g/L)' which are essential for compliance reporting and shipping.
        
        Industry Context:
        Storing an oxidizer next to a flammable solvent is a massive safety hazard. ERPNext warehouse routing ensures that when a Purchase Receipt is created for Acetone, the default accepted warehouse is explicitly the Flammable vault, forcing physical compliance.
        """
    },
    {
        "title": "Work Order and Job Card for Batch Production",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "manufacturing",
        "tags": ["work order", "job card", "routing", "dispersion", "milling"],
        "content": """
        WORK ORDER AND JOB CARD FOR BATCH PRODUCTION
        
        Production requires precise tracking of machine time (dispersers, bead mills) and labor to accurately calculate overhead costs.
        
        ERPNext Setup:
        1. Routing: Define a 'Routing' for chemical manufacturing, detailing operations like 'High-Speed Dispersion', 'Bead Milling', 'Letdown', and 'Canning'.
        2. Job Cards: When a Work Order is started, ERPNext generates Job Cards. Operators use these to clock time against the specific disperser (Workstation).
        3. Data Logging: Utilize custom fields on the Job Card to log critical environmental/process data, such as 'Max Tank Temperature' during the exothermic dispersion phase.
        
        Industry Context:
        High-speed mixing creates friction and heat. If resin exceeds 140°F, it degrades. By logging tank temperatures on the ERPNext Job Card, the production manager creates a verifiable audit trail showing that the chemical integrity was maintained during processing.
        """
    },
    {
        "title": "Batch-wise Costing and Variance Analysis",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "accounting",
        "tags": ["batch costing", "variance", "valuation", "yield loss"],
        "content": """
        BATCH-WISE COSTING AND VARIANCE ANALYSIS
        
        The cost to produce a gallon of epoxy varies wildly based on raw material market fluctuations and daily factory yield losses.
        
        ERPNext Setup:
        1. Valuation Method: Set Item valuation to FIFO or Moving Average. 
        2. Work Order Costing: Upon completing a Work Order, ERPNext calculates the total cost based on the exact quantity of raw materials consumed (Stock Entry - Material Issue) + Operating Costs (Job Cards) + Scrap.
        3. Variance Reports: Compare the standard BOM cost against the actual Work Order cost to identify variances.
        
        Industry Context:
        If an operator accidentally spills 50 lbs of expensive titanium dioxide pigment, the 'Material Consumption' entry will be higher than the BOM standard. ERPNext ensures this loss is absorbed into the valuation rate of that specific Finished Good batch, rather than becoming an invisible hole in the company's P&L.
        """
    },
    {
        "title": "Production Planning: Make-to-Stock vs Make-to-Order",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "manufacturing",
        "tags": ["production plan", "make to stock", "make to order", "planning"],
        "content": """
        PRODUCTION PLANNING: MAKE-TO-STOCK + MAKE-TO-ORDER
        
        Coating manufacturers operate in a hybrid model. Base primers and standard grey epoxies are 'Make-to-Stock' (MTS). Custom colored urethanes for specific clients are 'Make-to-Order' (MTO).
        
        ERPNext Setup:
        1. MTS: Use the 'Production Plan' tool configured to 'Material Requests'. The system scans minimum stock levels for standard resins and suggests Work Orders to replenish inventory.
        2. MTO: Generate a 'Production Plan' directly from 'Sales Orders'. The system creates Work Orders specifically linked to that customer's Sales Order.
        3. Sub-assembly Planning: ERPNext can automatically explode the BOM to plan the manufacture of intermediate pastes (sub-assemblies) needed for the final topcoat.
        
        Industry Context:
        To optimize factory capacity, the production manager relies on ERPNext to aggregate demand. Instead of making 5 separate 100-gallon batches of custom grey for 5 different Make-to-Order projects, the Production Plan consolidates them into a single 500-gallon Work Order, saving hours of machine cleaning time.
        """
    },
    {
        "title": "Project Setup in ERPNext for Site Installation Services",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "project_management",
        "tags": ["project setup", "installation", "site", "turnkey", "tasks"],
        "content": """
        PROJECT SETUP IN ERPNEXT FOR SITE INSTALLATION SERVICES
        
        When the company is acting as a Turnkey installer, the factory is just the supplier. The real complexity moves to the job site.
        
        ERPNext Setup:
        1. Project Creation: A 'Sales Order' for installation services automatically generates a 'Project' in ERPNext.
        2. Task Trees: Build Project Templates with standard task phases: 'Site Assessment', 'Mechanical Surface Prep (Grinding/Shotblasting)', 'Primer Application', 'Base Coat', and 'Topcoat'.
        3. Project Tracking: The Project record acts as the central hub, linking all material consumptions, labor timesheets, and purchase orders for site-specific tooling (diamond blades).
        
        Industry Context:
        Surface preparation dictates the success of a coating. 60% of site time is spent grinding concrete. By segmenting the ERPNext Project into specific Tasks, management can track if the 'Surface Prep' phase is burning through the labor budget before a single drop of epoxy is even opened.
        """
    },
    {
        "title": "Material Estimation and Allocation for Site Projects",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "project_management",
        "tags": ["material estimation", "allocation", "sq ft coverage", "porosity"],
        "content": """
        MATERIAL ESTIMATION AND ALLOCATION FOR SITE PROJECTS
        
        Estimating material relies on square footage and theoretical coverage rates, which often fail when encountering real-world concrete porosity.
        
        ERPNext Setup:
        1. Material Requests: The Project Manager creates a 'Material Request' (Purpose: Material Transfer) linked explicitly to the 'Project'.
        2. BOM for Projects: While not a manufacturing BOM, project estimators use 'Quotation' item bundles to calculate required Part A and Part B quantities based on Sq Ft. 
        3. Stock Allocation: Utilize the 'Stock Reservation' feature to lock down factory inventory specifically for the project, preventing it from being sold to a walk-in distributor.
        
        Industry Context:
        If a warehouse floor is highly pitted (CSP 4 profile), it will absorb 30% more primer than estimated. ERPNext allows the field supervisor to trigger an emergency Material Request linked to the project, providing visibility into exactly why the material budget was exceeded.
        """
    },
    {
        "title": "Project-wise Costing and Profitability Tracking",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "project_management",
        "tags": ["project costing", "profitability", "margin", "material issue"],
        "content": """
        PROJECT-WISE COSTING AND PROFITABILITY TRACKING
        
        Project manufacturing requires tracking costs at both the factory production level and the site installation level to determine true margin.
        
        ERPNext Setup:
        1. Material Costs: When epoxy is dispatched, use a 'Stock Entry' (Material Issue) linked to the 'Project'. This debits inventory and adds to project cost.
        2. Direct Expenses: Field expenses (per diems, hotel stays, rental lifts) are logged via 'Expense Claims' or 'Purchase Invoices' linked directly to the Project.
        3. Profitability Dashboard: The ERPNext Project Dashboard aggregates total Material Issue + Timesheet Costs + Expenses, and compares it against the Sales Invoice to calculate actual Gross Margin.
        
        Industry Context:
        Turnkey coating projects suffer from margin bleed due to unseen field variables. An estimated 50% margin can drop to 15% if an extra coat of vapor barrier is required. The ERPNext Project Costing dashboard provides real-time visibility before the project is even closed out.
        """
    },
    {
        "title": "Labor, Subcontractor, and Equipment Management in Projects",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "project_management",
        "tags": ["timesheets", "subcontractors", "labor cost", "equipment"],
        "content": """
        LABOR, SUBCONTRACTOR, AND EQUIPMENT MANAGEMENT IN PROJECTS
        
        Field crews travel to sites. Sometimes surface preparation is subcontracted to specialized grinding companies.
        
        ERPNext Setup:
        1. Timesheets: Field technicians log hours via mobile 'Timesheets' linked to the 'Project' and 'Task'. The 'Activity Cost' setting determines the internal hourly costing rate.
        2. Subcontracting: Create a 'Purchase Order' for the subcontracted grinding service, linking the PO directly to the Project. The subsequent 'Purchase Invoice' impacts project profitability.
        3. Equipment Allocation: Tooling like planetary grinders can be managed as fixed assets. Maintenance or blade wear costs can be apportioned to the project via Journal Entries.
        
        Industry Context:
        A crew might spend 3 days stuck in a hotel due to high humidity preventing a pour. Those labor hours and per diems must be logged in ERPNext against the project. This data allows estimators to build better "weather delay" contingencies into future bids.
        """
    },
    {
        "title": "Project Milestones and Payment Schedules",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "accounting",
        "tags": ["milestones", "payment terms", "invoicing", "retention"],
        "content": """
        PROJECT MILESTONES AND PAYMENT SCHEDULES
        
        Commercial flooring projects involve large sums of money and are rarely paid 100% upfront.
        
        ERPNext Setup:
        1. Payment Terms: Configure 'Payment Terms Templates' (e.g., 40% Mobilization Deposit, 40% on Basecoat Completion, 20% on Handover). Link this to the Quotation and Sales Order.
        2. Payment Requests: Use 'Payment Requests' triggered by the completion of specific Project Tasks (Milestones).
        3. Retention Money: General contractors often hold back 5-10% retainage. Track this in ERPNext using specific accounting ledgers until the warranty period clears.
        
        Industry Context:
        Material procurement for a 100,000 sq ft hangar requires massive cash flow. The ERPNext system ensures the 40% mobilization deposit is invoiced and received *before* the factory begins the expensive Work Orders to produce the custom urethane batches.
        """
    },
    {
        "title": "Project Completion, Handover, and Warranty",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "project_management",
        "tags": ["handover", "warranty", "completion", "traceability"],
        "content": """
        PROJECT COMPLETION, HANDOVER, AND WARRANTY
        
        The point where the physical installation ends and the legal warranty period begins.
        
        ERPNext Setup:
        1. Project Status: Update the Project status to 'Completed'. This should trigger a workflow to review final costing.
        2. Leftover Material: Execute a 'Stock Entry' (Material Receipt) to return unmixed Part A and Part B from the Site Warehouse back to the Main Warehouse, crediting the project cost.
        3. Warranty Tracking: Use the 'Serial No' or 'Batch' doctype to track the warranty of the installed floor. If a defect is reported, the system can trace the exact chemical batches used on that specific site.
        
        Industry Context:
        Flooring warranties usually cover chemical delamination, not physical abuse (like dragging a pallet of steel). If a client files a claim, the ERPNext Batch history allows the manufacturer to prove that the material passed factory QC, shifting the focus to potential field or client-use errors.
        """
    },
    {
        "title": "Stock Reservation for Projects (Material vs Free Stock)",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "inventory",
        "tags": ["stock reservation", "allocation", "free stock", "virtual warehouse"],
        "content": """
        STOCK RESERVATION FOR PROJECTS (MATERIAL VS FREE STOCK)
        
        Factory inventory must be ruthlessly protected. Material produced for a specific site installation must not be accidentally sold to a B2B distributor.
        
        ERPNext Setup:
        1. Stock Reservation: Use the 'Stock Reservation' feature against the Sales Order/Project. This reduces the 'Available Qty' (Free Stock) while keeping the 'Actual Qty' unchanged until dispatch.
        2. Virtual Warehouses: Best practice is to create a temporary, virtual 'Site Warehouse' (e.g., 'Site - Texas Hangar') nested under a parent 'Projects Warehouse'.
        3. Visibility: The Stock Balance report immediately reflects that 500 gallons of epoxy are physically in the building, but mathematically reserved for the Texas project.
        
        Industry Context:
        A B2B distributor urgently asks for 100 gallons of clear epoxy. The warehouse manager looks at the floor, sees the pallets, and ships them. The next day, the installation crew realizes their material is gone. ERPNext's Stock Reservation prevents this fatal logistical error.
        """
    },
    {
        "title": "Transfer from Manufacturing Stock to Project Stock",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "inventory",
        "tags": ["material transfer", "dispatch", "logistics", "stock entry"],
        "content": """
        TRANSFER FROM MANUFACTURING STOCK TO PROJECT STOCK
        
        The physical movement of hazmat materials from the controlled factory to the uncontrolled job site.
        
        ERPNext Setup:
        1. Material Transfer: Create a 'Stock Entry' (Purpose: Material Transfer) from 'FG-Warehouse' to the specific 'Site-Warehouse'.
        2. Delivery Note: Generate a 'Delivery Note' from the Sales Order. This acts as the physical packing slip and includes crucial Hazmat shipping data (UN Numbers, weights).
        3. Batch Enforcement: ERPNext forces the dispatcher to scan/select the exact 'Batch Numbers' being loaded onto the truck, ensuring field traceability.
        
        Industry Context:
        Shipping 50 buckets of Part A and accidentally forgetting the 10 buckets of Part B is a catastrophic error. The crew is on site, hotel paid, labor ticking, but they can't pour. ERPNext Delivery Notes act as the definitive checklist, preventing mismatched plural-component shipments.
        """
    },
    {
        "title": "Dual Sales Process (Product Invoice vs Project Invoice)",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "selling",
        "tags": ["invoicing", "b2b", "turnkey", "services", "sales order"],
        "content": """
        DUAL SALES PROCESS (PRODUCT INVOICE VS PROJECT INVOICE)
        
        The company runs two different business models simultaneously: Selling buckets to contractors (Product), and selling installed floors to facility owners (Project).
        
        ERPNext Setup:
        1. Product Sales: Sales Order -> Delivery Note -> Sales Invoice. The invoice lists physical Items (Epoxy Kits) and depletes inventory.
        2. Project Sales: Sales Order -> Project -> Sales Invoice. The invoice lists a Service Item (e.g., "Epoxy Floor Installation per Sq Ft"). 
        3. Separation: Material consumed during the Project is logged via 'Stock Entry' (Material Issue) to track cost, but the final customer Invoice only shows the agreed-upon turnkey service price, hiding the granular material line items.
        
        Industry Context:
        Facility managers don't want to buy buckets of chemicals; they want to buy a finished floor. B2B contractors, however, want to buy buckets. ERPNext handles both gracefully by splitting physical item invoicing from service/milestone invoicing.
        """
    },
    {
        "title": "Integration: Manufacturing Module + Projects Module in ERPNext",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "architecture",
        "tags": ["integration", "modules", "data flow", "mto"],
        "content": """
        INTEGRATION: MANUFACTURING MODULE + PROJECTS MODULE IN ERPNEXT
        
        The true power of ERPNext is passing data seamlessly from the Project Estimator to the Factory Floor.
        
        ERPNext Setup:
        1. The Nexus: The 'Sales Order' is the anchor. It can simultaneously generate a 'Project' (for the field crew) and a 'Production Plan' (for the factory).
        2. Unified Costing: By linking the 'Material Request' (triggered by the Project) to the 'Work Order' (executed by Manufacturing), the system connects factory yield variances directly to site profitability.
        3. Real-time Visibility: The Project Manager can look at the ERPNext Project dashboard and see that the required topcoat is currently in the 'WIP-Letdown' phase in the factory, allowing them to confidently schedule the field crew's travel.
        
        Industry Context:
        Without integration, estimators use spreadsheets, factories use whiteboards, and crews sit idle waiting for material. ERPNext acts as the central nervous system, ensuring that if a project date shifts, the manufacturing queue can be adjusted dynamically.
        """
    },
    {
        "title": "Composite Supply GST Invoicing for Project-Based Businesses",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "accounting",
        "tags": ["gst", "invoicing", "composite supply", "works contract", "india"],
        "content": """
        COMPOSITE SUPPLY GST INVOICING FOR PROJECT-BASED BUSINESSES
        
        For turnkey installations, billing involves both goods (chemicals) and services (labor), creating complex tax implications (e.g., under Indian GST).
        
        ERPNext Setup:
        1. Item Tax Templates: Configure correct tax rates. Chemicals usually attract a standard goods rate (e.g., 18% HSN), while labor attracts a service rate (SAC).
        2. Works Contract: A turnkey flooring project is often legally classified as a 'Works Contract' (a composite supply). Create a specific Service Item in ERPNext for "Turnkey Flooring Solution" mapped to the relevant Works Contract SAC code.
        3. Invoicing: Generate the Sales Invoice using this composite Service Item. Do not invoice the chemical buckets separately to the client, as that violates the works contract taxation rules.
        
        Industry Context:
        Billing a client separately for buckets of epoxy and hours of labor can trigger tax audits and mismatched GST liabilities. By treating the installation as a single composite supply in ERPNext, the company simplifies compliance while still using backend Stock Entries to track granular material costs.
        """
    },
    {
        "title": "Dual Costing Architecture (Product Costing + Project Costing)",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "architecture",
        "tags": ["costing architecture", "bom cost", "project cost", "margin"],
        "content": """
        DUAL COSTING ARCHITECTURE (PRODUCT COSTING + PROJECT COSTING)
        
        To understand true net profit, the system must separate what it costs to MAKE the chemical from what it costs to INSTALL the chemical.
        
        ERPNext Setup:
        1. Product Costing (Factory): Determined by BOM + Work Order operations. This establishes the 'Valuation Rate' of the finished chemical in inventory (e.g., $20/gallon).
        2. Project Costing (Field): Determined by Material Issues (gallons used * valuation rate) + Field Timesheets + Travel Expenses. 
        3. The Architecture: ERPNext acts as a two-stage engine. Stage 1 generates the inventory asset value. Stage 2 consumes that asset, adding field liabilities, to calculate the final Project Gross Profit against the Turnkey Sales Invoice.
        
        Industry Context:
        A company might have a highly efficient, low-cost factory but terribly inefficient field crews. If costing isn't separated, management just sees "low overall profit" and might blame the chemists. ERPNext's dual costing isolates the factory efficiency from the field efficiency, highlighting exactly where the money is bleeding.
        """
    },
   # Append these 20 chunks to containers/knowledge_base/project_manufacturing_kb_chunks.py
    {
        "title": "Waste Management in Chemical Manufacturing",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "manufacturing",
        "tags": ["waste management", "scrap", "bom", "hazardous waste"],
        "content": """
        WASTE MANAGEMENT IN CHEMICAL MANUFACTURING
        
        Chemical production generates hazardous waste (e.g., solvent wash from cleaning tanks) that cannot just be thrown away; it must be tracked for EPA/environmental compliance.
        
        ERPNext Setup:
        1. BOM Scrap Setup: Add non-valued or negative-value items to the BOM as 'Scrap'. 
        2. Scrap Warehouse: Create a dedicated 'Hazmat Scrap Warehouse'. When a Work Order is completed, ERPNext automatically moves the designated scrap items here.
        3. Disposal Tracking: When a certified disposal company takes the waste, create a 'Delivery Note' or 'Stock Entry (Material Issue)' to deplete the Scrap Warehouse, linking the disposal certificate as an attachment.
        
        Industry Context:
        Flushing a bead mill with xylene creates dirty solvent. You can't sell it, but you are legally liable for its volume. Tracking scrap quantities in ERPNext ensures that if you buy 500 gallons of xylene and only use 400 in products, the remaining 100 gallons are explicitly accounted for in the Hazmat Scrap warehouse.
        """
    },
    {
        "title": "Batch Traceability for Quality Recalls",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "quality",
        "tags": ["batch traceability", "recall", "stock ledger", "qa"],
        "content": """
        BATCH TRACEABILITY FOR QUALITY RECALLS
        
        If a specific lot of amine hardener is found to be defective, the manufacturer must instantly identify every factory batch it was mixed into, and every project site where it was poured.
        
        ERPNext Setup:
        1. Strict Batch Tracking: Enforce 'Has Batch No' across the entire supply chain (Purchase Receipt -> Work Order -> Delivery Note).
        2. Batch View / Stock Ledger: Use the 'Batch' record to view the 'Stock Ledger' linked to it. This shows the genealogy of the batch.
        3. Upstream/Downstream Traceability: The system allows tracing a defective raw material batch (from a Purchase Receipt) forward into all completed Work Orders, and tracing a defective finished good batch backward to its BOM ingredients.
        
        Industry Context:
        A supplier issues a recall on a red pigment. Within 60 seconds in ERPNext, the QA manager filters the Stock Ledger by the supplier's Batch No., sees it was used in Work Orders #401 and #405, and that Delivery Notes #89 and #92 shipped those finished goods to a hospital project in Texas and a warehouse in Ohio. Recall calls are made immediately.
        """
    },
    {
        "title": "Subcontracting in Manufacturing",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "manufacturing",
        "tags": ["subcontracting", "toll manufacturing", "purchase order"],
        "content": """
        SUBCONTRACTING IN MANUFACTURING
        
        Chemical companies often use "Toll Manufacturers" (subcontractors) to produce specialized formulations they lack the equipment for (e.g., ultra-fine media milling).
        
        ERPNext Setup:
        1. Subcontracting BOM: Create a BOM for the item where 'Is Subcontracted Item' is checked.
        2. Material Transfer: Create a 'Purchase Order' for the tolling service. Use 'Transfer Material to Supplier' to move raw resins and pigments from the main warehouse to the 'Supplier Warehouse'.
        3. Receipt and Valuation: Create a 'Purchase Receipt' when the finished chemical returns. ERPNext automatically values the finished good as (Cost of Raw Materials + Subcontractor Service Fee).
        
        Industry Context:
        You send $5,000 of raw epoxy base to a toll manufacturer. They charge you $1,000 to process it. ERPNext ensures that while the material is at their facility, it remains on your balance sheet, and when it returns, the inventory valuation is perfectly adjusted to $6,000.
        """
    },
    {
        "title": "Multi-BOM Management for Different Formulations",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "manufacturing",
        "tags": ["bom", "multi-bom", "formulation", "seasonality"],
        "content": """
        MULTI-BOM MANAGEMENT FOR DIFFERENT FORMULATIONS
        
        Chemical formulations often change based on the season (Winter vs. Summer blends) without changing the final product SKU sold to the customer.
        
        ERPNext Setup:
        1. Multiple BOMs per Item: ERPNext allows creating multiple BOMs for a single Finished Good Item. 
        2. Default BOM Selection: Mark the Summer formulation as 'Default' from May to September, and the Winter formulation as 'Default' from October to April.
        3. Routing Variations: Different BOMs can have different Routings. A winter blend might require an extra 30 minutes in a heated mixer, which is captured in the specific BOM's Job Cards.
        
        Industry Context:
        A Polyurethane Topcoat needs a faster-evaporating solvent in the winter so it cures properly in cold weather. The customer just orders "PU Topcoat". By switching the active BOM in ERPNext, the factory uses the correct solvent without sales reps having to memorize seasonal SKUs.
        """
    },
    {
        "title": "Manufacturing Licenses and Compliance (Factory Act, Pollution Control)",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "compliance",
        "tags": ["compliance", "licenses", "pollution control", "audit"],
        "content": """
        MANUFACTURING LICENSES AND COMPLIANCE (FACTORY ACT, POLLUTION CONTROL)
        
        Chemical plants require strict air permit and pollution control board licenses to operate legally. Expired licenses result in immediate factory shutdowns.
        
        ERPNext Setup:
        1. Custom Doctype / Custom Fields: Create a Custom DocType called 'Compliance License' OR add custom fields to the Company master (e.g., 'Pollution Control Board Expiry Date').
        2. Email Alerts: Set up an 'Email Alert' (Notification) triggered 90, 60, and 30 days before the Date field expires.
        3. Validation Scripts: (Advanced) Use a Client/Server script to block the submission of 'Work Orders' if a critical environmental license is currently marked as expired.
        
        Industry Context:
        Operating a disperser without a valid VOC emissions permit carries massive daily fines. Proactive ERPNext notifications ensure the EHS (Environmental Health & Safety) manager initiates the renewal paperwork months before the hard deadline.
        """
    },
    {
        "title": "Hazardous Material Handling Documentation & SDS",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "compliance",
        "tags": ["sds", "hazmat", "shipping", "un number", "voc"],
        "content": """
        HAZARDOUS MATERIAL HANDLING DOCUMENTATION & SDS
        
        Safety Data Sheets (SDS) must accompany shipments of hazardous chemicals, and shipping manifests must legally display UN classifications.
        
        ERPNext Setup:
        1. Item Master Custom Fields: Add custom fields for 'UN Number', 'Hazmat Class' (e.g., Class 3 Flammable), and 'Packing Group'.
        2. Attachments: Upload the PDF SDS directly to the Item record.
        3. Print Formats: Customize the 'Delivery Note' Print Format to pull the UN Number and Hazmat Class fields next to the item name, ensuring DOT (Department of Transportation) compliance.
        
        Industry Context:
        If a highway patrol officer pulls over your delivery truck, the driver must hand over a shipping manifest detailing exactly what Hazmat class is in the back. By baking these fields into the ERPNext Delivery Note Print Format, compliance is automated on every single shipment.
        """
    },
    {
        "title": "Work-in-Progress (WIP) Tracking for Projects",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "project_management",
        "tags": ["wip", "project tracking", "timesheets", "completion"],
        "content": """
        WORK-IN-PROGRESS (WIP) TRACKING FOR PROJECTS
        
        Turnkey coating projects can span weeks. Financial controllers need to know the WIP value of incomplete projects at month-end to accurately report revenue.
        
        ERPNext Setup:
        1. Task Progress: Field supervisors update '% Complete' on Project Tasks. 
        2. Submitted Timesheets: Timesheets submitted but not yet billed represent unbilled labor WIP.
        3. Material WIP: Material transferred to the 'Site Warehouse' via Stock Entry but not yet consumed via 'Material Issue' remains on the balance sheet as WIP inventory.
        
        Industry Context:
        If a $100k job is paused over month-end due to rain, the controller runs an ERPNext Stock Balance report for the 'Site Warehouse' and a Timesheet report to calculate exactly how much labor and material is currently tied up in that unfinished floor.
        """
    },
    {
        "title": "Equipment and Tool Tracking for Projects",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "project_management",
        "tags": ["assets", "tooling", "equipment", "depreciation"],
        "content": """
        EQUIPMENT AND TOOL TRACKING FOR PROJECTS
        
        Sending a $50,000 planetary floor grinder to a job site requires tracking its location to prevent theft, and expensing its wear-and-tear against the project.
        
        ERPNext Setup:
        1. Asset Module: Register the grinder as a Fixed Asset.
        2. Asset Movement: Use 'Asset Movement' to transfer the grinder from the 'HQ Location' to the 'Project Site Location'. 
        3. Project Costing: Instead of charging the full $50k to one job, create a Journal Entry for equipment rental/depreciation costs linked to the Project's cost center.
        
        Industry Context:
        Crews frequently "lose" expensive HEPA vacuums and diamond grinders by leaving them at old sites. By utilizing ERPNext Asset Movements tied to Project locations, the Operations Manager knows exactly which crew truck or active job site holds which piece of heavy equipment.
        """
    },
    {
        "title": "Site Expense Management",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "accounting",
        "tags": ["expenses", "per diem", "travel", "project cost"],
        "content": """
        SITE EXPENSE MANAGEMENT
        
        Field crews rack up expenses for fuel, hotels, per diems, and emergency hardware store runs. These must hit the Project's profitability ledger immediately.
        
        ERPNext Setup:
        1. Expense Claims: Foremen use the mobile interface to submit 'Expense Claims', attaching photos of receipts.
        2. Project Linkage: The crucial step is selecting the specific 'Project' in the Expense Claim detail row.
        3. Approval Workflow: The Project Manager approves the claim, triggering the accounting ledger to debit project expenses and credit the employee payable account.
        
        Industry Context:
        A crew runs out of masking tape and buys $200 worth at Home Depot. If they just hand the receipt to HR, it becomes a generic overhead expense. By enforcing ERPNext Expense Claims linked to the Project, that $200 directly reduces the specific job's margin.
        """
    },
    {
        "title": "Project-Specific Purchase Orders (Drop-shipping)",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "buying",
        "tags": ["purchase order", "drop-ship", "logistics", "direct-to-site"],
        "content": """
        PROJECT-SPECIFIC PURCHASE ORDERS
        
        Sometimes materials (like specialized anti-slip aggregates) are purchased from a third-party vendor and shipped directly to the client's job site, bypassing the factory warehouse.
        
        ERPNext Setup:
        1. Drop-shipping: In the Sales Order, mark the item for 'Drop Ship' and link the Supplier. This auto-generates a Purchase Order.
        2. Delivery Address: On the PO, change the 'Select Shipping Address' from 'Company Address' to 'Customer Address' (the job site).
        3. Link to Project: Ensure the Purchase Order is linked to the Project so the incoming vendor invoice hits the project cost dashboard, even though the physical inventory never touched the factory.
        
        Industry Context:
        Ordering 5 pallets of silica sand to be shipped from a quarry directly to a job site saves thousands in double-freight costs. ERPNext routes the logistics directly to the site while ensuring the financial liability correctly docks against the project's profit margin.
        """
    },
    {
        "title": "Multi-Project Resource Allocation",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "project_management",
        "tags": ["resource allocation", "capacity", "scheduling", "crews"],
        "content": """
        MULTI-PROJECT RESOURCE ALLOCATION
        
        An installation company might have 3 field crews but 10 active projects. Scheduling conflicts cause cascading delays.
        
        ERPNext Setup:
        1. Task Assignment: Assign specific Employees (or User groups representing crews) to specific Project Tasks with hard Start and End dates.
        2. Employee Calendar / Gantt: Use the standard Task Gantt chart and Employee Calendar views to visually identify overlaps where Crew A is booked in two places at once.
        3. Leave Management: Integration with the HR module ensures tasks cannot be assigned to a foreman whose Leave Application is approved for that week.
        
        Industry Context:
        A project is delayed by rain, pushing Crew B's schedule back by two days. The dispatcher looks at the ERPNext Calendar view to instantly see which upcoming project needs to be rescheduled or if Crew C has capacity to step in.
        """
    },
    {
        "title": "Customer Management (B2B Industrial vs Distributors)",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "selling",
        "tags": ["crm", "customer groups", "pricing rules", "b2b"],
        "content": """
        CUSTOMER MANAGEMENT (B2B INDUSTRIAL VS DISTRIBUTORS)
        
        The business sells direct Turnkey installations to facility owners at full price, but sells bulk chemical pails to regional distributors at a deep discount.
        
        ERPNext Setup:
        1. Customer Groups: Create groups for 'Turnkey End-Users', 'Tier 1 Distributors', and 'Independent Contractors'.
        2. Pricing Rules: Set up 'Pricing Rules' linked to Customer Groups. A Tier 1 Distributor automatically gets a 30% discount on the Item Group 'Epoxy Resins' when a Quotation is created.
        3. Credit Limits: Enforce strict 'Credit Limits' on contractors to block Sales Orders if they have unpaid invoices > 60 days old.
        
        Industry Context:
        A contractor tries to buy 50 gallons of topcoat but has $20k in unpaid invoices. ERPNext’s Credit Limit feature puts a hard hold on the Sales Order. The system also prevents sales reps from accidentally quoting a Tier 1 discount to a one-time walk-in buyer.
        """
    },
    {
        "title": "Quotation Process (Product Quote vs Turnkey Project Quote)",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "selling",
        "tags": ["quotation", "estimating", "services", "products"],
        "content": """
        QUOTATION PROCESS (PRODUCT QUOTE VS TURNKEY PROJECT QUOTE)
        
        A quote for 10 buckets of epoxy is a simple itemized list. A quote for a 10,000 sq ft installation is a complex service proposal.
        
        ERPNext Setup:
        1. Item Types: Product quotes use physical Items. Turnkey quotes use a non-stock Service Item (e.g., "Installation Services per Sq Ft").
        2. Quotation Templates: Create specific 'Terms and Conditions' templates. Turnkey quotes require heavy legal text regarding substrate condition, moisture limits, and curing times.
        3. Print Formats: Use a custom Print Format for Turnkey quotes to hide granular material line items and present a clean, single-price milestone summary to the facility owner.
        
        Industry Context:
        If you show a facility owner exactly how many gallons of epoxy you are buying and what you pay for them, they will negotiate your margin to zero. ERPNext Turnkey print formats bundle the value into "Services", protecting your material margins while delivering professional proposals.
        """
    },
    {
        "title": "Customer Complaints and Service Management",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "support",
        "tags": ["support", "issue", "complaints", "peeling", "warranty"],
        "content": """
        CUSTOMER COMPLAINTS AND SERVICE MANAGEMENT
        
        When a floor peels or delaminates, the customer is furious. The support workflow must immediately link the complaint to the project and batch data.
        
        ERPNext Setup:
        1. Issue Tracking: Log the complaint as an 'Issue' in the Support module. 
        2. Link to Project/Batch: Use custom fields or standard reference links to tie the Issue directly to the original 'Project' and the 'Batch No' of the material used.
        3. Warranty Claim: If a repair is needed, generate a zero-dollar 'Sales Order' linked to the Issue for replacement material, consuming inventory but logging it as a warranty expense.
        
        Industry Context:
        A client calls saying the topcoat bubbled. The Support agent creates an ERPNext Issue, looks up the Project, and sees the installation happened on a day with 95% humidity. Instead of blaming the chemical batch, the data points to an environmental application error.
        """
    },
    {
        "title": "Seasonal Demand Planning",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "manufacturing",
        "tags": ["demand planning", "seasonality", "material request", "safety stock"],
        "content": """
        SEASONAL DEMAND PLANNING
        
        Construction and coating application peaks in the spring and summer. Base resin inventory must be drastically ramped up in March.
        
        ERPNext Setup:
        1. Reorder Levels: Manually adjust the 'Min/Max Reorder Levels' in the Item Master for bulk raw materials ahead of peak season.
        2. Production Plan (Forecast): Use the 'Production Plan' tool based on 'Sales from previous year' (filtering for Q2/Q3 dates) to generate bulk Work Orders for standard Make-to-Stock primers before the rush hits.
        3. Lead Time Buffers: Increase the Safety Stock parameters in the Item master to account for summer logistics bottlenecks.
        
        Industry Context:
        If you wait for a Sales Order to trigger a Purchase Order for raw resin in July, you will lose the job because the supplier lead time is 4 weeks. ERPNext allows the purchasing manager to run a predictive Production Plan based on last summer's data, ensuring the warehouse is full by April.
        """
    },
    {
        "title": "Manufacturing Dashboard and KPIs",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "analytics",
        "tags": ["dashboard", "kpi", "oee", "yield", "scrap percentage"],
        "content": """
        MANUFACTURING DASHBOARD AND KPIS
        
        The Factory Manager needs a real-time pulse on production efficiency, yield losses, and machine utilization.
        
        ERPNext Setup:
        1. Custom Dashboard: Build a 'Manufacturing Dashboard' using standard ERPNext charts and Number Cards.
        2. Yield Variance KPI: Create a chart tracking the difference between 'Planned Material Consumption' (from BOM) vs. 'Actual Material Consumption' (from Work Orders).
        3. Open Work Orders: Use a list view or metric card to show 'Pending Work Orders' to visualize factory backlog.
        
        Industry Context:
        Chemical yield is the biggest margin killer. If the factory yield drops from 95% to 88% over a month, the ERPNext dashboard flags the variance instantly. Management can investigate and discover a worn-out pump is leaving 15 gallons of resin at the bottom of every mixing tank.
        """
    },
    {
        "title": "Dashboard for Manufacturing + Projects KPIs Combined",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "analytics",
        "tags": ["dashboard", "executive", "hybrid", "margin", "utilization"],
        "content": """
        DASHBOARD FOR MANUFACTURING + PROJECTS KPIS COMBINED
        
        The CEO of a turnkey coating company needs a unified view bridging the gap between factory output and field revenue.
        
        ERPNext Setup:
        1. Executive Workspace: Create a custom Workspace that pulls charts from both the Accounts/Projects module and the Manufacturing module.
        2. Unified Metrics: Display 'Project Gross Margin' (Accounts) right next to 'Factory Scrap %' (Manufacturing).
        3. Labor Utilization: Combine 'Factory Timesheet Hours' with 'Field Task Timesheet Hours' to see total payroll utilization across both divisions.
        
        Industry Context:
        A company might have 10 highly profitable projects in the field, but the overall P&L looks terrible because the factory produced 5 bad batches of epoxy that had to be written off. A combined ERPNext Executive Dashboard connects the dots, preventing the CEO from blaming the field crews for factory failures.
        """
    },
    {
        "title": "Warranty Management for Completed Projects",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "support",
        "tags": ["warranty", "maintenance", "amc", "inspections"],
        "content": """
        WARRANTY MANAGEMENT FOR COMPLETED PROJECTS
        
        Industrial floors often carry 3-to-5 year warranties, requiring tracked annual inspections to keep the warranty valid.
        
        ERPNext Setup:
        1. Warranty Tracking: Use the 'Warranty Period' fields on the Item Master/Sales Order.
        2. Maintenance Schedule: Generate an 'Annual Maintenance Schedule' (AMC) linked to the Customer/Project to remind the sales team to perform a yearly site inspection.
        3. Expiry Alerts: Set up automated email alerts 30 days before a major project's warranty expires, offering the client a paid maintenance top-coat.
        
        Industry Context:
        Most companies treat warranties as liabilities. By using ERPNext Maintenance Schedules, the company turns warranties into a revenue engine. The system automatically reminds the sales rep to call the facility owner after 3 years and say: "Your warranty is expiring, let's do a $5,000 clear-coat refresh to extend it another 3 years."
        """
    },
    {
        "title": "Project Profitability Analysis",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "analytics",
        "tags": ["profitability", "gross profit", "costing", "financials"],
        "content": """
        PROJECT PROFITABILITY ANALYSIS
        
        True profitability is only known after all vendor bills, employee timesheets, and material issues are fully reconciled.
        
        ERPNext Setup:
        1. Gross Profit Report: Use the standard 'Gross Profit' report, filtering explicitly by the 'Project' field.
        2. Cost Center Mapping: Ensure each Project automatically creates a linked 'Cost Center' to easily filter all P&L entries.
        3. Variance Analysis: Compare the 'Estimated Cost' on the original Quotation against the 'Actual Cost' aggregated in the Project dashboard.
        
        Industry Context:
        You quoted $20,000 for a floor. The client paid $20,000. It feels like a win. But the ERPNext Project Profitability report reveals that because the crew had to rent an extra grinder ($1k) and consumed 20 extra gallons of primer ($1.5k), the actual margin was only 5%. This data is vital for estimators quoting the next job.
        """
    },
    {
        "title": "Material Allocation from Stock to Projects",
        "industry": "Specialty Chemicals / Construction Coatings",
        "kb_type": "inventory",
        "tags": ["allocation", "pick list", "material transfer", "staging"],
        "content": """
        MATERIAL ALLOCATION FROM STOCK TO PROJECTS
        
        Before a field crew leaves the shop on Monday morning, the exact materials needed for the week must be physically staged and logically allocated.
        
        ERPNext Setup:
        1. Material Request: The Project Manager submits a Material Request (Transfer) for the job.
        2. Pick List: Generate a 'Pick List' from the Material Request. This routes the warehouse staff to pull specific Batch Numbers from the racks.
        3. Stock Transfer: Execute a 'Stock Entry (Material Transfer)' moving the items from 'FG-Approved Warehouse' to the virtual 'Site-Warehouse'.
        
        Industry Context:
        A field foreman walking through the warehouse grabbing random buckets of epoxy creates immediate inventory chaos. By enforcing the ERPNext Pick List and Stock Transfer workflow, the physical staging area matches the digital ledger perfectly, ensuring no crew accidentally takes material reserved for another project.
        """
    }
] 

