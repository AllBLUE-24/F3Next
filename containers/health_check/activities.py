import os
from pathlib import Path
from dotenv import load_dotenv
from temporalio import activity
from langchain_google_genai import ChatGoogleGenerativeAI 
from shared.utils.health_check_financial import get_mapped_value
from containers.health_check.knowledge_base import KNOWLEDGE_BASE
from containers.health_check.prompts import REPORT_GENERATION_PROMPT
from sqlalchemy import text
from backend.app.core.db import engine

# Setup absolute path for .env to ensure GEMINI_API_KEY is found
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

@activity.defn
async def analyze_health_logic(data: dict) -> dict:
    """Calculates all financial variables for the Forensic Audit prompt."""
    inputs = data.get("answers", {})
    kb = KNOWLEDGE_BASE
    
    # 1. Basic Financial Mapping
    turnover_val = get_mapped_value(inputs.get("q2_turnover"), "turnover")
    inventory_val = get_mapped_value(inputs.get("q3_inventory_value"), "inventory")
    
    # 2. Calculate Annual Bleed (Dead Capital Interest)
    interest_rate = kb["roi_formulas"]["dead_capital_interest_rate"]
    total_annual_bleed = inventory_val * interest_rate
    
    # 3. Calculate Management Waste (Owner-Debt)
    # Estimate: 20% of turnover is lost to 'Firefighting' in inefficient factories
    management_waste = turnover_val * 0.05 
    
    # 4. Calculate Monthly Interest Loss
    monthly_interest_loss = total_annual_bleed / 12
    
    # 5. Determine Tangible Comparison Asset
    tangible_comparison = "Three High-End Laptops" # Default
    for asset in reversed(kb["tangible_assets"]): # Check highest threshold first
        if total_annual_bleed >= asset["threshold"]:
            tangible_comparison = asset["item"]
            break

    # 6. Determine Efficiency Zone
    efficiency_zone = "CRITICAL" if total_annual_bleed > 500000 else "WARNING"

    # Return exactly what REPORT_GENERATION_PROMPT.format() needs
    return {
        "efficiency_zone": efficiency_zone,
        "total_annual_bleed": f"{total_annual_bleed:,.2f}",
        "tangible_comparison": tangible_comparison,
        "management_waste": f"{management_waste:,.2f}",
        "monthly_interest_loss": f"{monthly_interest_loss:,.2f}",
        "raw_data": inputs # Passing raw inputs for secondary checks if needed
    }

@activity.defn
async def generate_health_report(analysis_results: dict) -> str:
    """Generates the Forensic Audit report using Gemini."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing!")

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
    
    # Fix the KeyError by mapping every placeholder in prompts.py
    formatted_prompt = REPORT_GENERATION_PROMPT.format(
        efficiency_zone=analysis_results["efficiency_zone"],
        total_annual_bleed=analysis_results["total_annual_bleed"],
        tangible_comparison=analysis_results["tangible_comparison"],
        management_waste=analysis_results["management_waste"],
        monthly_interest_loss=analysis_results["monthly_interest_loss"]
    )
    
    response = await llm.ainvoke(formatted_prompt)
    return str(response.content)


@activity.defn
async def save_report_to_db(data: dict):
    """Saves the final forensic audit to the database."""

    print(f"DEBUG: save_report_to_db received keys: {list(data.keys())}")
    # Extract variables from the dictionary passed by the workflow
    project_id = data.get("project_id")
    report = data.get("report")

    if not project_id or not report:
        raise ValueError(f"❌ Missing data: project_id={project_id}, report exists={bool(report)}")

    async with engine.begin() as conn:
        # We update the hooks table using the project_id
        await conn.execute(
            text("UPDATE hooks SET report_content = :report WHERE project_id = :pid"),
            {"report": report, "pid": project_id}
        )
    return True
