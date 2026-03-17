import aiohttp
from temporalio import activity

@activity.defn
async def validate_payload(payload: dict) -> dict:
    """Check all required fields exist before firing anything"""
    required_connection = ["site_url", "api_key", "api_secret"]
    required_operation  = ["type", "doctype", "data"]

    for field in required_connection:
        if field not in payload["connection"]:
            raise ValueError(f"Missing connection field: {field}")

    for field in required_operation:
        if field not in payload["operation"]:
            raise ValueError(f"Missing operation field: {field}")

    activity.logger.info(f"✅ Payload valid for {payload['operation']['doctype']}")
    return payload


@activity.defn
async def execute_erpnext_operation(payload: dict) -> dict:
    """Fire the actual REST call to ERPNext"""
    conn    = payload["connection"]
    op      = payload["operation"]

    site_url  = conn["site_url"]
    api_key   = conn["api_key"]
    api_secret = conn["api_secret"]
    doctype   = op["doctype"]
    op_type   = op["type"]
    data      = op["data"]

    headers = {
        "Authorization": f"token {api_key}:{api_secret}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:

        if op_type == "create":
            url = f"{site_url}/api/resource/{doctype}"
            async with session.post(url, json=data, headers=headers) as resp:
                result = await resp.json()
                status = resp.status

        elif op_type == "update":
            name = op["document_name"]
            url  = f"{site_url}/api/resource/{doctype}/{name}"
            async with session.put(url, json=data, headers=headers) as resp:
                result = await resp.json()
                status = resp.status

        elif op_type == "delete":
            name = op["document_name"]
            url  = f"{site_url}/api/resource/{doctype}/{name}"
            async with session.delete(url, headers=headers) as resp:
                result = await resp.json()
                status = resp.status

        elif op_type == "fetch":
            name = op["document_name"]
            url  = f"{site_url}/api/resource/{doctype}/{name}"
            async with session.get(url, headers=headers) as resp:
                result = await resp.json()
                status = resp.status

    if status == 200:
        activity.logger.info(f"✅ {op_type} on {doctype} succeeded")
        return {"status": "success", "data": result.get("data", result)}
    else:
        activity.logger.error(f"❌ ERPNext error: {result}")
        raise Exception(f"ERPNext returned {status}: {result}")


@activity.defn
async def save_execution_log(log_data: dict) -> dict:
    """Save what happened — useful for debugging and audit trail"""
    # For now just log it, later you can save to your DB
    activity.logger.info(f"📋 Execution log: {log_data}")
    return {"logged": True}