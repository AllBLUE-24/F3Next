import os
import subprocess
import sys

# Define directories
root_dir = r"c:\dev\F3Next"
backend_dir = os.path.join(root_dir, "backend")
containers_dir = os.path.join(root_dir, "containers")
shared_dir = os.path.join(root_dir, "shared")

# Install pipreqs
subprocess.run([sys.executable, "-m", "pip", "install", "pipreqs"], check=True)

def get_pipreqs(directory):
    # Run pipreqs to stdout using its module
    print(f"Scanning {directory}...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pipreqs.pipreqs", "--print", "--ignore", "venv,__pycache__", directory], 
            capture_output=True, 
            text=True,
            encoding='utf-8'
        )
        if result.returncode != 0:
            print(f"Error on {directory}: {result.stderr}")
            return []
        lines = result.stdout.strip().split("\n")
        reqs = []
        for line in lines:
            line = line.strip()
            # pipreqs --print outputs line by line, but may include INFO logs
            if line and not line.startswith("INFO:") and not line.startswith("WARNING:"):
                reqs.append(line)
        return reqs
    except Exception as e:
        print(f"Failed to scan {directory}: {e}")
        return []

print("Getting shared dependencies...")
shared_reqs = get_pipreqs(shared_dir)
print(f"Shared requirements: {shared_reqs}")

base_implicit_deps = [
    "python-dotenv==0.21.0",
    "pydantic==2.11.7",
    "pydantic-core==2.33.2"
]

worker_implicit_deps = [
    "temporalio==1.21.1",
]

backend_implicit_deps = [
    "fastapi==0.115.14",
    "uvicorn==0.35.0",
    "asyncpg==0.31.0",
    "psycopg2-binary==2.9.11",
    "alembic==1.17.2",
    "SQLAlchemy==2.0.44",
]

all_shared = set(shared_reqs + base_implicit_deps)

def write_reqs(target_dir, extra_deps):
    print(f"Processing {target_dir}...")
    if not os.path.exists(os.path.join(target_dir, "requirements.txt")):
        print(f"No requirements.txt found in {target_dir}, skipping.")
        return

    local_reqs = get_pipreqs(target_dir)
    final_reqs = set(local_reqs).union(all_shared).union(extra_deps)
    
    # Clean up empty strings or weird lines
    final_reqs = {r.split('==')[0] + "==" + r.split('==')[1] if '==' in r else r for r in final_reqs if r}
    
    req_file = os.path.join(target_dir, "requirements.txt")
    with open(req_file, "w", encoding='utf-8') as f:
        # Sort ignoring case
        lines = sorted(list(final_reqs), key=lambda x: x.lower())
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {len(final_reqs)} dependencies to {req_file}")

# Process Backend
write_reqs(backend_dir, backend_implicit_deps)

# Process Containers
for c in ["discovery", "erpnext", "health_check", "implementation", "knowledge_base", "os"]:
    cdir = os.path.join(containers_dir, c)
    if os.path.exists(cdir):
         write_reqs(cdir, worker_implicit_deps)

print("Done generating fresh requirements.txt!")
