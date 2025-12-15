import os
import re
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv 

load_dotenv()

from agents.health_check.knowledge_base import KNOWLEDGE_BASE
from agents.health_check.prompts import REPORT_GENERATION_PROMPT

# --- 1. THE EXACT MAP (Calibrated to your Question Options) ---
# This ensures we convert the exact string the user clicks into a real number.
OPTION_MAP = {
    # Turnover Options (Using Mid-point averages)
    "₹50L - ₹2 Cr": 12500000,   # 1.25 Cr
    "₹2 Cr - ₹10 Cr": 60000000, # 6 Cr
    "₹10 Cr - ₹50 Cr": 300000000, # 30 Cr
    "₹50 Cr+": 600000000,       # 60 Cr (Conservative base)

    # Inventory Options (Using Mid-point averages)
    "< ₹10 Lakhs": 500000,      # 5 Lakhs
    "₹10 Lakhs - ₹50 Lakhs": 3000000, # 30 Lakhs
    "₹50 Lakhs - ₹2 Crores": 12500000, # 1.25 Cr
    "I honestly don't know (No live record)": -1, # Trigger for logic calculation
}

def get_mapped_value(user_input, category):
    """
    Looks up the exact string in the map. 
    If not found (e.g. frontend sends 'q2_option1'), tries to parse, else defaults.
    """
    clean_key = str(user_input).strip()
    
    # 1. Direct Lookup
    if clean_key in OPTION_MAP:
        return OPTION_MAP[clean_key]
    
    # 2. Fallback Parsing (In case of slight text mismatch)
    print(f"⚠️ Warning: Exact match not found for '{clean_key}'. Attempting fallback parse.")
    clean_val = clean_key.lower().replace(",", "").replace("₹", "").replace("lakhs", "").replace("cr", "")
    numbers = re.findall(r"[\d\.]+", clean_val)
    if numbers:
        # Heuristic: If number is small (<100), it might be Crores, multiply appropriately
        val = float(numbers[0])
        if "cr" in clean_key.lower(): return val * 10000000
        if "lakh" in clean_key.lower(): return val * 100000
        return val
        
    # 3. Absolute Fail Safe (Defaults to prevent crash)
    if category == "turnover": return 10000000 # 1 Cr
    if category == "inventory": return 1000000 # 10 Lakhs
    return 0

class AgentState(TypedDict):
    user_inputs: dict
    analysis_results: dict
    final_report: str

# --- Node 1: Python Calculator & Analyst ---
def analyze_node(state: AgentState):
    inputs = state["user_inputs"]
    kb = KNOWLEDGE_BASE
    risks_found = []
    
    print("\n" + "="*30)
    print("🚨 ANALYZING INPUTS (DEBUG):")
    for k, v in inputs.items():
        print(f"   - {k}: {v}")
    
    # --- 1. RISK DIAGNOSIS (Text Matching) ---
    # We match the EXACT text from your questions to the Risk Matrix
    for rule in kb["risk_matrix"]:
        # We search all input values to find the matching answer text
        # (Since we don't know if frontend sends 'q5' or 'bom_handling')
        found_risk = False
        for answer in inputs.values():
            if str(answer) in rule["condition_values"]:
                risks_found.append({
                    "diagnosis": rule["diagnosis"],
                    "consequence": rule["consequence"],
                    "solution": rule["solution_module"]
                })
                found_risk = True
                break
    
    # --- 2. FINANCIAL MATH (The Fix) ---
    
    # A. TURNOVER
    # Look for the answer to Question 2
    turnover_input = inputs.get("annual_turnover") or inputs.get("q2") or "₹50L - ₹2 Cr"
    turnover = get_mapped_value(turnover_input, "turnover")
    
    # B. INVENTORY
    # Look for the answer to Question 4
    inventory_input = inputs.get("inventory_value") or inputs.get("q4") or "< ₹10 Lakhs"
    inventory = get_mapped_value(inventory_input, "inventory")
    
    # Special Logic: If they said "I honestly don't know" (-1), assume 20% of turnover (High Bleed)
    is_unknown_inventory = False
    if inventory == -1:
        inventory = turnover * 0.20
        is_unknown_inventory = True

    # C. INVOICE VOLUME ESTIMATION (The 72k Fix)
    # Since we don't ask for volume, we estimate based on turnover.
    # Assumption: Avg Invoice Value = ₹50,000
    avg_invoice_val = 50000
    estimated_invoice_count = max(10, turnover / avg_invoice_val) # Min 10 invoices
    
    manual_cost = kb["industry_benchmarks"]["manual_invoice_processing_cost_inr"] # 60
    annual_operational_waste = estimated_invoice_count * manual_cost * 12

    # D. DEAD CAPITAL
    ideal_inventory = turnover * kb["roi_formulas"]["excess_inventory_threshold"] # 15%
    dead_capital = max(0, inventory - ideal_inventory)
    
    annual_interest_loss = dead_capital * kb["roi_formulas"]["dead_capital_interest_rate"]
    monthly_interest_loss = annual_interest_loss / 12

    # E. OPPORTUNITY COST (For lean/unknown inventory)
    opportunity_loss = 0
    if dead_capital == 0 and not is_unknown_inventory:
        # If inventory is extremely low (<5%), they are missing sales
        if (inventory / turnover) < 0.05:
            opportunity_loss = turnover * 0.05
    elif is_unknown_inventory:
        # If they don't know, we add a "Risk Penalty"
        opportunity_loss = turnover * 0.02

    # F. TOTAL BLEED
    total_annual_bleed = annual_operational_waste + annual_interest_loss + opportunity_loss

    # G. TANGIBLE ASSET
    tangible_item = "Growth Capital"
    for asset in kb["tangible_assets"]:
        if total_annual_bleed > asset["threshold"]:
            tangible_item = asset["item"]

    # H. EFFICIENCY ZONE
    inventory_percent = (inventory / turnover) * 100 if turnover > 0 else 0
    
    efficiency_zone = "Green"
    if is_unknown_inventory:
        efficiency_zone = "Red (Blindness)"
    elif inventory_percent > 25: 
        efficiency_zone = "Red (Critical Hoarding)"
    elif inventory_percent > 18: 
        efficiency_zone = "Yellow (Warning)"
    elif inventory_percent < 5:
        efficiency_zone = "Yellow (Stockout Risk)"

    print(f"✅ CALCULATED: Turnover: {turnover}, Inv: {inventory}, Bleed: {total_annual_bleed}")
    print("="*30 + "\n")

    return {"analysis_results": {
        "risks": risks_found,
        "estimated_turnover": int(turnover),
        "dead_capital_detected": int(dead_capital),
        "monthly_interest_loss": int(monthly_interest_loss),
        "annual_operational_waste": int(annual_operational_waste),
        "total_annual_bleed": int(total_annual_bleed),
        "tangible_comparison": tangible_item,
        "efficiency_zone": efficiency_zone,
        "is_unknown_inventory": is_unknown_inventory
    }}

# --- Node 2: AI Writer (With Context Awareness) ---
async def writer_node(state: AgentState):
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=os.environ.get("GEMINI_API_KEY") 
    )
    
    # We pass the user's specific "Dream Fix" to the prompt
    dream_fix = state["user_inputs"].get("dream_fix") or state["user_inputs"].get("q10") or "General Improvement"
    
    prompt = REPORT_GENERATION_PROMPT.format(
        user_inputs=str(state["user_inputs"]),
        analysis_results=str(state["analysis_results"]),
        dream_fix=dream_fix
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    # Clean Markdown
    clean_content = response.content.replace("```markdown", "").replace("```", "").strip()
    
    return {"final_report": clean_content}

# --- Workflow ---
def build_agent():
    workflow = StateGraph(AgentState)
    workflow.add_node("analyst", analyze_node)
    workflow.add_node("writer", writer_node)
    
    workflow.set_entry_point("analyst")
    workflow.add_edge("analyst", "writer")
    workflow.add_edge("writer", END)
    
    return workflow.compile()

async def run_health_check_agent(data: dict):
    agent = build_agent()
    result = await agent.ainvoke({"user_inputs": data})
    return result