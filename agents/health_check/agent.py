# app/agents/agent.py

import os
import re
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv 

load_dotenv()

# Ensure these match your actual file paths
from app.agents.health_check.knowledge_base import KNOWLEDGE_BASE
from app.agents.health_check.prompts import REPORT_GENERATION_PROMPT

# --- 1. THE EXACT MAP (Calibrated to your Questions) ---
OPTION_MAP = {
    # Turnover Options
    "₹50l-₹2cr": 12500000,   # 1.25 Cr
    "₹2cr-₹10cr": 60000000,  # 6 Cr
    "₹10cr-₹50cr": 300000000, # 30 Cr
    "₹50cr+": 600000000,     # 60 Cr

    # Inventory Options
    "<₹10lakhs": 500000,      # 5 Lakhs
    "₹10lakhs-₹50lakhs": 3000000, # 30 Lakhs
    "₹50lakhs-₹2crores": 12500000, # 1.25 Cr
    "ihonestlydon'tknow(noliverecord)": -1, 
}

def get_mapped_value(user_input, category):
    """
    Robust Fuzzy Matcher: Strips ALL spaces and symbols to match the map key.
    """
    if not user_input:
        return 10000000 if category == "turnover" else 1000000

    # Normalize: lowercase, remove spaces, remove symbols
    clean_input = str(user_input).lower().replace(" ", "").strip()
    
    # Direct Map Lookup
    if clean_input in OPTION_MAP:
        return OPTION_MAP[clean_input]
        
    # Regex Fallback
    clean_val = clean_input.replace(",", "").replace("₹", "").replace("lakhs", "").replace("cr", "")
    numbers = re.findall(r"[\d\.]+", clean_val)
    if numbers:
        val = float(numbers[0])
        if "cr" in clean_input: return val * 10000000
        if "lakh" in clean_input or "lac" in clean_input: return val * 100000
        return val
        
    return 10000000 if category == "turnover" else 1000000

class AgentState(TypedDict):
    user_inputs: dict
    analysis_results: dict
    final_report: str

# --- Node 1: Analyst ---
def analyze_node(state: AgentState):
    raw_inputs = state["user_inputs"]
    kb = KNOWLEDGE_BASE
    risks_found = []
    
    # 🚨 CRITICAL: Unwrap 'answers' if nested (Frontends often send {answers: {...}})
    inputs = raw_inputs.get("answers", raw_inputs)
    
    # --- 1. RISK DIAGNOSIS ---
    for rule in kb["risk_matrix"]:
        for answer in inputs.values():
            if str(answer) in rule["condition_values"]:
                risks_found.append({
                    "diagnosis": rule["diagnosis"],
                    "consequence": rule["consequence"],
                    "solution": rule["solution_module"]
                })
    
    # --- 2. FINANCIAL MATH ---
    
    # A. TURNOVER (Hunting for keys containing 'turnover' or 'q2')
    turnover_val = "₹50L - ₹2 Cr" # Default
    for key, val in inputs.items():
        if ("turnover" in key.lower() or "q2" in key.lower()) and val:
            turnover_val = val
            break
    turnover = get_mapped_value(turnover_val, "turnover")
    
    # B. INVENTORY (Hunting for keys containing 'inventory' or 'q4')
    inventory_val = "< ₹10 Lakhs" # Default
    for key, val in inputs.items():
        if ("inventory" in key.lower() or "q4" in key.lower()) and val:
            inventory_val = val
            break
    inventory = get_mapped_value(inventory_val, "inventory")
    
    # Special Logic: Unknown Inventory
    is_unknown_inventory = False
    if inventory == -1:
        inventory = turnover * 0.20
        is_unknown_inventory = True

    # C. INVOICE VOLUME ESTIMATION
    avg_invoice_val = 50000
    estimated_invoice_count = max(10, turnover / avg_invoice_val)
    manual_cost = kb["industry_benchmarks"]["manual_invoice_processing_cost_inr"]
    annual_operational_waste = estimated_invoice_count * manual_cost * 12

    # D. DEAD CAPITAL
    ideal_inventory = turnover * kb["roi_formulas"]["excess_inventory_threshold"]
    dead_capital = max(0, inventory - ideal_inventory)
    
    annual_interest_loss = dead_capital * kb["roi_formulas"]["dead_capital_interest_rate"]
    monthly_interest_loss = annual_interest_loss / 12

    # E. OPPORTUNITY LOSS
    opportunity_loss = 0
    if dead_capital == 0 and not is_unknown_inventory:
        if (inventory / turnover) < 0.10: # <10% Inventory
            opportunity_loss = turnover * 0.05
    elif is_unknown_inventory:
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
    elif inventory_percent < 10:
        efficiency_zone = "Yellow (Stockout Risk)"

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

# --- Node 2: Writer ---
async def writer_node(state: AgentState):
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=os.environ.get("GEMINI_API_KEY") 
    )
    
    # Handle Nested Inputs for Dream Fix retrieval
    raw_inputs = state["user_inputs"]
    inputs = raw_inputs.get("answers", raw_inputs)
    
    dream_fix = "General Improvement"
    for key, val in inputs.items():
        if "dream" in key.lower() or "fix" in key.lower():
            dream_fix = val
            break
            
    prompt = REPORT_GENERATION_PROMPT.format(
        user_inputs=str(inputs),
        analysis_results=str(state["analysis_results"]),
        dream_fix=dream_fix
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
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