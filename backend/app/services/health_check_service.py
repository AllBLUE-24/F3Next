# app/services/health_check_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.core import Client, Project  # Ensure these import paths match your project structure
from agents.health_check.agent import run_health_check_agent # IMPORT THE AGENT

async def process_health_check(
    uid: str, 
    email: str, 
    company: str, 
    full_name: str, 
    role: str, 
    answers: dict, 
    db: AsyncSession
):
    print(f"\n🚀 STARTING HEALTH CHECK FOR: {company} ({uid})")

    # --- 1. ENSURE CLIENT EXISTS ---
    # We check if the user (Client) is already in the DB. If not, create them.
    res_c = await db.execute(select(Client).where(Client.id == uid))
    client = res_c.scalar_one_or_none()
    
    if not client:
        print(f"   -> Creating New Client: {full_name}")
        client = Client(
            id=uid, 
            email=email,
            full_name=full_name,
            role=role,
            company_name=company,
            status="active"
        )
        db.add(client)
        # Flush to get the ID ready (though we provided it)
        await db.flush()
    else:
        # Update details if they changed
        if company: client.company_name = company
        if full_name: client.full_name = full_name
        # Note: You might want to save the new answers to the client/project record here if your schema supports it

    # --- 2. ENSURE PROJECT EXISTS ---
    # A 'Project' tracks the specific engagement/audit for this client.
    res_p = await db.execute(select(Project).where(Project.client_id == uid))
    project = res_p.scalar_one_or_none()
    
    if not project:
        print("   -> Creating New Project Context")
        project = Project(
            client_id=uid, 
            company_name=company,
            status="created"
        )
        db.add(project)
        await db.flush()
    
    # Optional: Save the raw answers to the DB (if you have a JSON column)
    # project.last_health_check_data = answers
    
    # Commit changes to DB before running the heavy agent
    await db.commit()

    # --- 3. THE HANDOFF (CRITICAL) ---
    print("\n" + "!"*50)
    print("🕵️ SERVICE IS HANDING THIS TO AGENT:")
    print(answers) 
    print("!"*50 + "\n")

    # --- 4. RUN THE AGENT ---
    try:
        # We pass the 'answers' dictionary directly to the agent
        agent_result = await run_health_check_agent(answers)
        
        # Extract the results from the agent's output state
        final_report = agent_result.get("final_report", "Report Generation Failed")
        analysis_data = agent_result.get("analysis_results", {})
        
        annual_bleed = analysis_data.get("total_annual_bleed", 0)
        formatted_bleed = f"₹{annual_bleed:,}" # Format as ₹1,50,000

        print("✅ AGENT FINISHED SUCCESSFULLY")
        
        return {
            "project_id": str(project.id),
            "report": final_report,
            "annual_bleed": formatted_bleed,
            "user_meta": {
                "name": full_name,
                "company": company,
                "role": role
            }
        }

    except Exception as e:
        print(f"❌ AGENT FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return a safe fallback so the frontend doesn't crash
        return {
             "project_id": str(project.id),
             "report": "## Analysis Failed\n\nOur intelligence engine encountered an error. Please try again.",
             "annual_bleed": "Error"
        }