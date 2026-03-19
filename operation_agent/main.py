"""Operation Agent - FastAPI app."""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from config import ERPNEXT_URL
from agents.orchestrator import run_create_sales_order

app = FastAPI(title="Operation Agent", version="0.1.0")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Suppress favicon 404."""
    return Response(status_code=204)


class CommandRequest(BaseModel):
    prompt: str


UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Operation Agent | ERP-OS</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0f0f12;
      --surface: #18181b;
      --surface-hover: #27272a;
      --border: #3f3f46;
      --text: #fafafa;
      --text-muted: #a1a1aa;
      --accent: #6366f1;
      --accent-hover: #818cf8;
      --success: #22c55e;
      --error: #ef4444;
      --warning: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'DM Sans', system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
    .layout { display: flex; min-height: 100vh; }
    .sidebar { width: 240px; background: var(--surface); border-right: 1px solid var(--border); padding: 1.5rem 0; }
    .sidebar-brand { padding: 0 1.5rem 1.5rem; border-bottom: 1px solid var(--border); margin-bottom: 1rem; }
    .sidebar-brand h1 { font-size: 1rem; font-weight: 600; color: var(--text); }
    .sidebar-brand span { font-size: 0.75rem; color: var(--text-muted); font-weight: 400; }
    .nav-item { display: block; padding: 0.6rem 1.5rem; color: var(--text-muted); text-decoration: none; font-size: 0.9rem; transition: all 0.15s; }
    .nav-item:hover { background: var(--surface-hover); color: var(--text); }
    .nav-item.active { background: rgba(99,102,241,0.15); color: var(--accent); border-left: 3px solid var(--accent); padding-left: calc(1.5rem - 3px); }
    .nav-item .badge { font-size: 0.65rem; padding: 0.15rem 0.4rem; border-radius: 4px; margin-left: 0.5rem; background: var(--border); color: var(--text-muted); }
    .main { flex: 1; padding: 2rem; max-width: 720px; }
    .section { display: none; }
    .section.active { display: block; }
    .section h2 { font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem; }
    .section-desc { color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.5rem; }
    .status-bar { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .status-pill { font-size: 0.75rem; padding: 0.35rem 0.75rem; border-radius: 999px; background: var(--surface); border: 1px solid var(--border); }
    .status-pill.demo { border-color: var(--warning); color: var(--warning); }
    .status-pill.live { border-color: var(--success); color: var(--success); }
    label { display: block; font-size: 0.85rem; font-weight: 500; margin-bottom: 0.5rem; color: var(--text-muted); }
    textarea, input { width: 100%; padding: 0.75rem 1rem; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 0.95rem; font-family: inherit; }
    textarea { min-height: 100px; resize: vertical; }
    textarea::placeholder, input::placeholder { color: var(--text-muted); opacity: 0.7; }
    textarea:focus, input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px rgba(99,102,241,0.2); }
    .btn { padding: 0.6rem 1.25rem; border-radius: 8px; font-size: 0.9rem; font-weight: 500; cursor: pointer; border: none; font-family: inherit; transition: all 0.15s; }
    .btn-primary { background: var(--accent); color: white; }
    .btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    #result { margin-top: 1.25rem; padding: 1rem 1.25rem; border-radius: 8px; white-space: pre-wrap; font-size: 0.9rem; line-height: 1.5; min-height: 80px; }
    #result.success { background: rgba(34,197,94,0.15); border: 1px solid rgba(34,197,94,0.4); color: #4ade80; }
    #result.error { background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.4); color: #f87171; }
    #result.pending { background: var(--surface); border: 1px solid var(--border); color: var(--text-muted); }
    .placeholder-section { padding: 2rem; background: var(--surface); border: 1px dashed var(--border); border-radius: 8px; text-align: center; color: var(--text-muted); font-size: 0.9rem; }
    .placeholder-section strong { color: var(--text); display: block; margin-bottom: 0.5rem; }
    .examples { margin-top: 1rem; font-size: 0.8rem; color: var(--text-muted); }
    .examples span { display: inline-block; margin: 0.25rem 0.25rem 0 0; padding: 0.25rem 0.5rem; background: var(--surface); border-radius: 4px; cursor: pointer; }
    .examples span:hover { background: var(--surface-hover); color: var(--text); }
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <h1>Operation Agent</h1>
        <span>ERP-OS · Natural language → ERP</span>
      </div>
      <a href="#" class="nav-item active" data-section="command">Command <span class="badge">Ready</span></a>
      <a href="#" class="nav-item" data-section="infra">Infra Agent <span class="badge">Coming</span></a>
      <a href="#" class="nav-item" data-section="settings">Settings <span class="badge">Soon</span></a>
    </aside>
    <main class="main">
      <div id="status-bar" class="status-bar"></div>

      <section id="section-command" class="section active">
        <h2>Create Sales Order</h2>
        <p class="section-desc">Type a natural language command. The agent will parse it and create a Sales Order in ERPNext.</p>
        <form id="form">
          <label for="prompt">Command</label>
          <textarea id="prompt" name="prompt" placeholder="e.g. Create SO for ABC Industries for 100 pieces of Product-001 at Rs 500 each"></textarea>
          <div class="examples">
            Try: <span data-cmd="Create SO for ABC Industries for 100 pieces of Product-001 at Rs 500 each">Single item</span>
            <span data-cmd="Create sales order for Tech Solutions Ltd: 50 units of Laptop-X at 45000, 20 units of Mouse-Pro at 800">Multi-item</span>
          </div>
          <button type="submit" id="btn" class="btn btn-primary" style="margin-top: 1rem;">Run</button>
        </form>
        <div id="result"></div>
      </section>

      <section id="section-infra" class="section">
        <h2>Infra Agent</h2>
        <p class="section-desc">Deploy and manage ERPNext instances on cloud. Hook for Parth's infra agent.</p>
        <div class="placeholder-section">
          <strong>Infra Agent — Extension Point</strong>
          Deploy ERPNext on cloud, get instance URL, manage environments.<br>
          Parth: Add your infra agent UI and API integration here.
        </div>
      </section>

      <section id="section-settings" class="section">
        <h2>Settings</h2>
        <p class="section-desc">Configure ERPNext URL, API credentials, demo mode.</p>
        <div class="placeholder-section">
          <strong>Settings — Extension Point</strong>
          Edit .env for now. Future: form to set ERPNEXT_URL, API keys, DEMO_MODE.
        </div>
      </section>
    </main>
  </div>

  <script>
    const form = document.getElementById("form");
    const promptEl = document.getElementById("prompt");
    const btn = document.getElementById("btn");
    const result = document.getElementById("result");
    const statusBar = document.getElementById("status-bar");

    async function loadStatus() {
      try {
        const r = await fetch("/config");
        const c = await r.json();
        statusBar.innerHTML = '<span class="status-pill ' + (c.erpnext_url === "configured" ? "live" : "demo") + '">' +
          (c.erpnext_url === "configured" ? "ERPNext Live" : "Demo Mode") + '</span>';
      } catch { statusBar.innerHTML = '<span class="status-pill demo">Demo Mode</span>'; }
    }
    loadStatus();

    document.querySelectorAll(".nav-item").forEach(el => {
      el.addEventListener("click", e => {
        e.preventDefault();
        document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
        document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
        el.classList.add("active");
        document.getElementById("section-" + el.dataset.section).classList.add("active");
      });
    });

    document.querySelectorAll(".examples span").forEach(el => {
      el.addEventListener("click", () => { promptEl.value = el.dataset.cmd; });
    });

    form.onsubmit = async (e) => {
      e.preventDefault();
      const text = promptEl.value.trim();
      if (!text) return;
      btn.disabled = true;
      result.className = "pending";
      result.textContent = "Running...";
      try {
        const r = await fetch("/command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text })
        });
        const data = await r.json();
        result.className = data.success ? "success" : "error";
        result.textContent = data.message || JSON.stringify(data);
      } catch (err) {
        result.className = "error";
        result.textContent = "Error: " + err.message;
      }
      btn.disabled = false;
    };
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
@app.get("/ui", response_class=HTMLResponse)
def ui():
    """Sample UI for natural language commands."""
    return UI_HTML


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


@app.get("/config")
def config_check():
    """Check if ERPNext is configured (for debugging)."""
    return {
        "erpnext_url": "configured" if ERPNEXT_URL else "NOT SET - add ERPNEXT_URL to .env",
        "hint": "Edit d:\\ERPNext\\operation_agent\\.env with your ERPNext URL and API keys, then restart the server.",
    }


@app.post("/command")
def command(req: CommandRequest):
    """Process natural language command → create Sales Order in ERPNext."""
    result = run_create_sales_order(req.prompt)
    return {
        "success": result["success"],
        "message": result["message"],
        "data": result.get("data"),
    }


if __name__ == "__main__":
    import uvicorn
    # Use 8001 to avoid conflict with ERPNext (typically on 8000)
    uvicorn.run(app, host="0.0.0.0", port=8001)
