"""
Discovery Agent — Knowledge Base v2

Used by Adi (the discovery consultant persona) to validate and enrich
signals extracted from user answers. The LLM receives these as system
context so it can make grounded, taxonomy-aware decisions.
"""

KNOWLEDGE_BASE = {

    # =========================================================
    # TAXONOMY — the only tags that may be emitted
    # =========================================================
    "taxonomy": {
        "industry":  ["#Ind_Manufacturing", "#Ind_Process", "#Ind_Discrete",
                      "#Ind_Retail", "#Ind_Service", "#Ind_Trading"],
        "strategy":  ["#Strat_MakeToStock", "#Strat_MakeToOrder", "#Strat_JobWork",
                      "#Strat_Assembly", "#Strat_ProjectBased"],
        "scale":     ["#Scale_Micro", "#Scale_SMB", "#Scale_Large"],
        "system":    ["#Legacy_Excel", "#Legacy_Tally", "#Legacy_Busy",
                      "#Legacy_Zoho", "#Legacy_SAP", "#Legacy_Oracle",
                      "#Legacy_CustomERP", "#Legacy_None"],
        "pain":      ["#Goal_Inventory", "#Goal_Costing", "#Goal_Efficiency",
                      "#Goal_Compliance", "#Goal_Billing", "#Goal_MRP"],
    },

    # =========================================================
    # SIGNAL VOCABULARY
    # Rich keyword banks so the LLM can do grounded extraction
    # even when users speak informally.
    # =========================================================
    "signal_vocabulary": {

        "industry": {
            "manufacturing": [
                "make", "produce", "assemble", "fabricate", "factory", "plant",
                "machining", "casting", "forging", "stamping", "weld", "moulding",
                "auto parts", "components", "OEM", "Tier-1", "Tier-2", "FMCG",
                "packaging", "printing", "textile", "garments", "chemicals",
                "pharma", "pharmaceutical", "food processing", "electronics",
                "engineering goods", "capital goods"
            ],
            "process": [
                "batch", "continuous", "formulation", "blending", "mixing",
                "recipe", "BOM", "raw material to finished goods"
            ],
            "retail": [
                "sell", "shop", "distribute", "trade", "store", "outlet",
                "wholesale", "dealer", "stockist", "retailer", "POS",
                "showroom", "chain", "franchise"
            ],
            "service": [
                "consult", "repair", "maintain", "amc", "advisory", "IT",
                "software", "agency", "facilities", "staffing", "logistics"
            ],
            "trading": [
                "import", "export", "buy and sell", "resell", "distribution",
                "broker", "commission agent", "merchant"
            ],
        },

        "strategy": {
            "make_to_stock":  ["keep stock", "maintain inventory", "ready stock",
                               "warehouse", "finished goods stock", "off-the-shelf"],
            "make_to_order":  ["custom order", "order-based", "client spec",
                               "made on demand", "project order", "bespoke"],
            "job_work":       ["job work", "sub-contract", "outsource processing",
                               "toll processing", "work for others", "CMO"],
            "assembly":       ["assemble", "kit", "BOM assembly", "semi-finished",
                               "BOQ", "build to order"],
            "project_based":  ["project", "milestone", "contract", "tender",
                               "turnkey", "construction"],
        },

        "scale": {
            "#Scale_Micro": {
                "revenue_hints": ["less than 2 crore", "below 2Cr", "startup", "small shop",
                                  "just starting", "1-2 employees", "sole proprietor"],
                "headcount":     ["1", "2", "3", "4", "5 people"]
            },
            "#Scale_SMB": {
                "revenue_hints": ["2 to 50 crore", "10 crore", "20 crore", "30 crore",
                                  "few crores", "mid-size", "medium"],
                "headcount":     ["10 to 200 employees", "50 people", "100 staff"]
            },
            "#Scale_Large": {
                "revenue_hints": ["more than 50 crore", "100 crore", "200 Cr", "500 Cr",
                                  "1000 crore", "group company", "multiple plants",
                                  "pan-India", "multinational"],
                "headcount":     ["500+", "1000 employees", "large workforce"]
            },
            "suspicious_combos": [
                "100 crore with 2 employees",
                "1000 crore with no ERP"
            ]
        },

        "legacy_system": {
            "#Legacy_Excel":     ["excel", "spreadsheet", "google sheets", "manual", "nothing"],
            "#Legacy_Tally":     ["tally", "tally prime", "tally erp 9"],
            "#Legacy_Busy":      ["busy", "busy accounting"],
            "#Legacy_Zoho":      ["zoho", "zoho books", "zoho inventory"],
            "#Legacy_SAP":       ["sap", "sap b1", "sap hana", "sap erp"],
            "#Legacy_Oracle":    ["oracle", "oracle netsuite"],
            "#Legacy_CustomERP": ["custom software", "in-house", "local ERP", "our own system",
                                  "custom-built", "vendor built for us"],
            "#Legacy_None":      ["nothing", "no system", "pen and paper", "register"],
        },

        "pain_point": {
            "#Goal_Inventory":   ["inventory", "stock", "wastage", "shrinkage", "expiry",
                                  "don't know what's in store", "overstocking", "out of stock"],
            "#Goal_Costing":     ["costing", "margin", "profit", "pricing", "overheads",
                                  "job cost", "production cost", "landed cost"],
            "#Goal_Efficiency":  ["slow", "manual process", "too much paperwork",
                                  "takes too long", "not automated", "double entry"],
            "#Goal_Compliance":  ["GST", "audit", "compliance", "reporting",
                                  "statutory", "tax", "e-invoice", "e-way bill"],
            "#Goal_Billing":     ["billing", "invoicing", "delayed payments",
                                  "collections", "accounts receivable", "dunning"],
            "#Goal_MRP":         ["production planning", "MRP", "work order",
                                  "scheduling", "shop floor", "capacity"],
        }
    },

    # =========================================================
    # VALIDATION RULES
    # =========================================================
    "validation_rules": {
        "scale_ratios": {
            "rule": "Revenue per employee usually falls between ₹5L - ₹5Cr.",
            "flag_if": "User claims >₹50Cr turnover with fewer than 10 employees."
        },
        "gibberish_detection": {
            "min_length": 3,
            "reject_patterns": ["abc", "xyz", "test", "asdf", "na", "idk", "dunno", "???"]
        },
        "vagueness_signals": [
            "we do everything", "all kinds of things", "various products",
            "business", "company", "work", "stuff"
        ]
    },

    # =========================================================
    # CONSULTANT CLARIFICATION TEMPLATES
    # Natural-language ways to ask follow-up without sounding robotic.
    # =========================================================
    "clarification_templates": {
        "vague_industry":    "Could you give me a specific example of what you produce or sell?",
        "vague_scale":       "Just to calibrate — roughly what's your annual turnover range? Even a ballpark helps.",
        "vague_strategy":    "Do you make products ahead of time and keep stock, or do you only produce once a customer places an order?",
        "vague_legacy":      "What software does your team use today for billing or inventory? Even if it's just Excel, that's fine.",
        "vague_pain":        "What's the one thing that takes up the most time or causes the most stress in your operations?",
        "gibberish":         "I didn't quite get that — could you tell me a bit about what your company does?",
        "suspicious_scale":  "That's a significant scale. Just to confirm — is that your group's combined turnover or this specific entity?",
        "multi_step_skip":   "Based on what you've shared, it sounds like you {inferred}. That covers a lot of ground — let me now ask about {remaining}."
    },

    # =========================================================
    # ERP FIT MATRIX (used by RECOMMENDATION_PROMPT)
    # =========================================================
    "erp_fit_matrix": {
        "high":   ["#Ind_Manufacturing", "#Ind_Service", "#Ind_Retail",
                   "#Ind_Trading", "#Scale_SMB", "#Strat_MakeToOrder"],
        "medium": ["#Scale_Large", "#Strat_JobWork", "#Ind_Process"],
        "low":    ["#Scale_Micro"]
    }
}