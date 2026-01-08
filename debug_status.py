import asyncio
from temporalio.client import Client

async def main():
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle("config-workflow-cnt_stock_101")
    
    state = await handle.query("get_state")
    
    print("\n🧐 TRUTH SERUM REPORT:")
    print(f"Status:    {state['status']}")  # <--- Should be "WAITING_FOR_USER"
    print(f"Layer:     {state['layer']}")   # <--- Should be 4
    print(f"Questions: {len(state['questions'])} pending")
    
    if state['status'] == "WAITING_FOR_USER":
        print("\n✅ SUCCESS: The workflow is waiting correctly!")
        print("If the Frontend is still stuck, the issue is in the Frontend React code.")
    elif "L4" in state['status']:
        print("\n❌ FAIL: It is still running the OLD CODE.")
        print("You did not Terminate the workflow correctly.")

if __name__ == "__main__":
    asyncio.run(main())