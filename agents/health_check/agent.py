import os
import re
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv 

load_dotenv()

# Import your files
from agents.health_check.knowledge_base import KNOWLEDGE_BASE
from agents.health_check.prompts import REPORT_GENERATION_PROMPT

# --- Helper: The "Sanitizer" ---
def parse_financial_input(input_val):
    clean_val = str(input_val).replace(",", "").replace("₹", "").lower()
    
    multiplier = 1
    if "cr" in clean_val: multiplier = 10000000
    elif "lakh" in clean_val or "lac" in clean_val: multiplier = 100000
    
    numbers = re.findall(r"[\d\.]+", clean_val)
    if numbers:
        return float(numbers[0]) * multiplier
    
    # Fallback buckets
    if "50 cr" in clean_val: return 500000000
    if "10 cr" in clean_val: return 100000000
    if "1 cr" in clean_val: return 10000000
    if "50 lakh" in clean_val: return 5000000
    if "10 lakh" in clean_val: return 1000000
    
    return 0.0

# Define State
class AgentState(TypedDict):
    user_inputs: dict
    analysis_results: dict
    final_report: str

# --- Node 1: Python Calculator & Analyst ---
def analyze_node(state: AgentState):
    inputs = state["user_inputs"]
    kb = KNOWLEDGE_BASE
    risks_found = []
    
    # 1. Risk Matrix Check
    for rule in kb["risk_matrix"]:
        user_val = inputs.get(rule["condition_field"], "")
        for bad_val in rule["condition_values"]:
            if bad_val in user_val:
                risks_found.append({
                    "diagnosis": rule["diagnosis"],
                    "consequence": rule["consequence"],
                    "solution": rule["solution_module"]
                })
    
    # 2. Financial Parsing
    turnover = parse_financial_input(inputs.get("annual_turnover", "10000000"))
    if turnover == 0: turnover = 10000000
    
    inventory = parse_financial_input(inputs.get("inventory_value", "0"))
    if inventory == 0: inventory = turnover * 0.10
    
    # 3. Operational Waste
    try:
        inv_vol = parse_financial_input(inputs.get("invoice_volume", "100"))
    except:
        inv_vol = 100
        
    manual_cost = kb["industry_benchmarks"]["manual_invoice_processing_cost_inr"]
    annual_operational_waste = inv_vol * manual_cost * 12

    # 4. Dead Capital
    ideal_inventory = turnover * kb["roi_formulas"]["excess_inventory_threshold"]
    dead_capital = max(0, inventory - ideal_inventory)
    
    annual_interest_loss = dead_capital * kb["roi_formulas"]["dead_capital_interest_rate"]
    monthly_interest_loss = annual_interest_loss / 12

    # 5. Total Bleed
    total_annual_bleed = annual_operational_waste + annual_interest_loss

    # 6. Tangible Asset
    tangible_item = "Growth Capital"
    for asset in kb["tangible_assets"]:
        if total_annual_bleed > asset["threshold"]:
            tangible_item = asset["item"]

    # 7. Efficiency Zone
    inventory_percent = (inventory / turnover) * 100 if turnover > 0 else 0
    efficiency_zone = "Green"
    if inventory_percent > 25: efficiency_zone = "Red (Critical)"
    elif inventory_percent > 15: efficiency_zone = "Yellow (Warning)"

    return {"analysis_results": {
        "risks": risks_found,
        "estimated_turnover": turnover,
        "dead_capital_detected": int(dead_capital),
        "monthly_interest_loss": int(monthly_interest_loss),
        "annual_operational_waste": int(annual_operational_waste),
        "total_annual_bleed": int(total_annual_bleed),
        "tangible_comparison": tangible_item,
        "efficiency_zone": efficiency_zone
    }}

# --- Node 2: AI Writer (FIXED FOR MARKDOWN) ---
async def writer_node(state: AgentState):
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=os.environ.get("GEMINI_API_KEY") 
    )
    
    prompt = REPORT_GENERATION_PROMPT.format(
        user_inputs=str(state["user_inputs"]),
        analysis_results=str(state["analysis_results"]),
        dream_fix=state["user_inputs"].get("dream_fix", "General Improvement")
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    # --- CLEANING STEP ---
    clean_content = response.content
    
    # Remove code block markers if present
    if clean_content.startswith("```markdown"):
        clean_content = clean_content.replace("```markdown", "").replace("```", "")
    elif clean_content.startswith("```"):
        clean_content = clean_content.replace("```", "")
        
    # Strip extra whitespace
    clean_content = clean_content.strip()
    
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

# Runner Function
async def run_health_check_agent(data: dict):
    agent = build_agent()
    result = await agent.ainvoke({"user_inputs": data})
    return result