# ERPNext Phase A — Manufacturing Foundation Setup Sequence

Manufacturing implementations follow the Universal Foundation Setup Sequence but require a few critical additions before Master Data can be safely imported. These additions represent physical and operational infrastructure.

Step 1: Universal Foundation (Company, Fiscal Year, COA, Cost Center, Currency)
  - Handled automatically as per universal phase A playbook.

Step 2: Warehouses (Stores and WIP)
  - Manufacturing requires distinct separation between Raw Material storage (Stores) and Work In Progress (WIP).
  - ERPNext auto-creates default warehouse on Company creation.
  - F3Next auto-seeds additional "Stores" and "WIP" child warehouses under the default warehouse.
  - No client data file needed.

Step 3: UOM (Unit of Measure)
  - Manufacturing relies heavily on precise conversions. 
  - The universal baseline seeds common UOMs (Nos, Kg, Ltr, Meter, Hour).
  - F3Next automatically creates these so that Phase B (Item) imports don't fail due to missing UOM references.

Step 4: Workstations and Operations
  - Basic setups are seeded from F3Next baseline based on industry.
  - If a specific industry baseline exists (e.g., Chemical), standard operations like "Mixing", "Heating", and "Packing" are seeded.
  - Client data NOT required at this stage — they can refine workstations later in the UI.

After this Phase A completes: the system is ready to receive Master Data (Items, BOMs, Suppliers).
Skipping this means Item defaults (like default_wip_warehouse) and BOMs will fail to import.
