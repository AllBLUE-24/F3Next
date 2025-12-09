import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv  # <--- 1. IMPORT THIS

load_dotenv()

# Import your files
from agents.health_check.knowledge_base import KNOWLEDGE_BASE
from agents.health_check.prompts import REPORT_GENERATION_PROMPT

# Define State
class AgentState(TypedDict):
    user_inputs: dict
    analysis_results: dict
    final_report: str

# --- Node 1: Python Calculator ---
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

    # 2. Math Helpers
    # Parse Turnover
    t_str = inputs.get("annual_turnover", "0")
    turnover = 10000000 # Default 1 Cr
    if "50 Cr" in t_str: turnover = 500000000
    elif "10 Cr" in t_str: turnover = 300000000
    elif "2 Cr" in t_str: turnover = 60000000
    
    # Parse Inventory
    i_str = inputs.get("inventory_value", "0")
    inventory = 0
    if "50 Lakhs - 2 Crores" in i_str: inventory = 12500000
    elif "10 Lakhs - 50 Lakhs" in i_str: inventory = 3000000
    elif "No live record" in i_str: inventory = turnover * 0.10 # Guess 10%

    # 3. Operational Waste Calculation
    # Try to get invoice count, default to 100 if not provided
    inv_count_str = inputs.get("invoice_volume", "100") 
    try:
        invoice_count = int(inv_count_str)
    except:
        invoice_count = 100 # Default fallback
        
    manual_cost = kb["industry_benchmarks"]["manual_invoice_processing_cost_inr"]
    annual_operational_waste = invoice_count * manual_cost * 12

    # 4. Dead Capital Calculation
    ideal_inventory = turnover * kb["roi_formulas"]["excess_inventory_threshold"]
    dead_capital = max(0, inventory - ideal_inventory)
    monthly_interest_loss = dead_capital * (kb["roi_formulas"]["dead_capital_interest_rate"] / 12)
    annual_interest_loss = monthly_interest_loss * 12

    # 5. Total Annual Bleed & Tangible Comparison
    total_annual_bleed = annual_operational_waste + annual_interest_loss
    
    tangible_item = "Growth Capital" # Default
    for asset in kb["tangible_assets"]:
        if total_annual_bleed > asset["threshold"]:
            tangible_item = asset["item"]

    # Efficiency Zone Calculation
    inventory_percent = (inventory / turnover) * 100 if turnover > 0 else 0
    efficiency_zone = "Green"
    if inventory_percent > 25: efficiency_zone = "Red (Critical)"
    elif inventory_percent > 15: efficiency_zone = "Yellow (Warning)"

    return {"analysis_results": {
        "risks": risks_found,
        "estimated_turnover": turnover,
        "dead_capital_detected": dead_capital,
        "monthly_interest_loss": int(monthly_interest_loss),
        "annual_operational_waste": int(annual_operational_waste), # NEW
        "total_annual_bleed": int(total_annual_bleed), # NEW
        "tangible_comparison": tangible_item, # NEW
        "efficiency_zone": efficiency_zone # NEW
    }}
    
# --- Node 2: AI Writer ---
async def writer_node(state: AgentState):
    # <--- 2. UPDATED KEY LOGIC HERE
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        # Explicitly tell LangChain to use your specific variable name
        google_api_key=os.environ.get("GEMINI_API_KEY") 
    )
    
    prompt = REPORT_GENERATION_PROMPT.format(
        user_inputs=str(state["user_inputs"]),
        analysis_results=str(state["analysis_results"]),
        dream_fix=state["user_inputs"].get("dream_fix", "General Improvement")
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"final_report": response.content}

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
    return result["final_report"]