import secrets
import asyncssh
import asyncio
import json
import os
import sys
import re
from temporalio import activity
from jinja2 import Template
from sqlalchemy import update

# 1. IMPORT MODELS & DB
from shared.models.core import Project, ProjectStatus
from shared.database.db import AsyncSessionLocal as async_session

# --- CONFIGURATION ---
EC2_HOST = "65.2.125.86"
EC2_USER = "ubuntu"
# Using raw string (r"...") to handle Windows backslashes correctly
SSH_KEY_PATH = r"C:\Users\Mayur Laxman Aldar\Downloads\f3.pem"

TIERS = {
    "standard": {"db_mem": "1G", "app_mem": "1G", "cpu": "1.0"},
    "premium":  {"db_mem": "2G", "app_mem": "4G", "cpu": "2.0"}
}

# --- TEMPLATES ---
NGINX_ASSETS_CONFIG = """
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log debug;
    location / {
        try_files $uri $uri/ =404;
        add_header Access-Control-Allow-Origin *;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
"""

DOCKER_COMPOSE_TEMPLATE = """
services:
  backend:
    image: frappe/erpnext:v15
    container_name: {{ stack_name }}-app
    restart: always
    deploy:
      resources:
        limits:
          memory: {{ app_memory_limit }}
          cpus: '{{ app_cpu_limit }}'
    environment:
      - DB_HOST=db
      - DB_PORT=3306
      - MYSQL_ROOT_PASSWORD={{ db_root_password }}
      - MARIADB_ROOT_PASSWORD={{ db_root_password }}
      - FRAPPE_ENV=production
    volumes:
      - ./sites:/home/frappe/frappe-bench/sites
    networks:
      - internal-net
      - traefik-public
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.{{ stack_name }}-app.rule=Host(`{{ site_url }}`)"
      - "traefik.http.routers.{{ stack_name }}-app.priority=10"
      - "traefik.http.routers.{{ stack_name }}-app.entrypoints=websecure"
      - "traefik.http.routers.{{ stack_name }}-app.tls=true"
      - "traefik.http.routers.{{ stack_name }}-app.tls.certresolver=letsencrypt"
      - "traefik.http.services.{{ stack_name }}-app.loadbalancer.server.port=8000"
      - "traefik.docker.network=traefik_default"

  assets:
    image: nginx:alpine
    container_name: {{ stack_name }}-assets
    restart: always
    volumes:
      - ./sites/assets:/usr/share/nginx/html:ro
      - ./nginx-assets.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - traefik-public
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.{{ stack_name }}-assets.rule=Host(`{{ site_url }}`) && PathPrefix(`/assets`)"
      - "traefik.http.routers.{{ stack_name }}-assets.priority=100"
      - "traefik.http.routers.{{ stack_name }}-assets.entrypoints=websecure"
      - "traefik.http.routers.{{ stack_name }}-assets.tls=true"
      - "traefik.http.routers.{{ stack_name }}-assets.tls.certresolver=letsencrypt"
      - "traefik.http.services.{{ stack_name }}-assets.loadbalancer.server.port=80"
      - "traefik.http.middlewares.{{ stack_name }}-strip.stripprefix.prefixes=/assets"
      - "traefik.http.routers.{{ stack_name }}-assets.middlewares={{ stack_name }}-strip"
      - "traefik.docker.network=traefik_default"

  db:
    image: mariadb:10.6
    container_name: {{ stack_name }}-db
    restart: always
    environment:
      - MYSQL_ROOT_PASSWORD={{ db_root_password }}
      - MYSQL_DATABASE=erpnext
    volumes:
      - ./mysql-data:/var/lib/mysql
    networks:
      - internal-net
    deploy:
      resources:
        limits:
          memory: {{ db_memory_limit }}

  redis:
    image: redis:6.2-alpine
    container_name: {{ stack_name }}-redis
    restart: always
    networks:
      - internal-net

networks:
  internal-net:
    internal: true
  traefik-public:
    external: true
    name: traefik_default
"""

# --- HELPER: LOGGED COMMAND EXECUTION ---
async def run_logged(conn, cmd: str, check: bool = True, description: str = None):
    """Execute SSH command with detailed logging"""
    desc = description or "Command"
    activity.logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    activity.logger.info(f"🔹 {desc}")
    activity.logger.info(f"📝 CMD: {cmd}")
    
    result = await conn.run(cmd, check=False)
    
    activity.logger.info(f"📊 EXIT STATUS: {result.exit_status}")
    if result.stdout:
        activity.logger.info(f"📤 STDOUT:\n{result.stdout}")
    if result.stderr:
        activity.logger.warning(f"⚠️  STDERR:\n{result.stderr}")
    
    if check and result.exit_status != 0:
        activity.logger.error(f"❌ Command failed with exit status {result.exit_status}")
        raise asyncssh.ProcessError(
            result.env, result.command, result.subsystem,
            result.exit_status, result.exit_signal,
            result.returncode, result.stdout, result.stderr
        )
    
    activity.logger.info(f"✅ {desc} completed successfully")
    return result

# --- ACTIVITY 1: DEPLOY ---

@activity.defn
async def deploy_inventory_container(input_data: dict) -> dict:
    activity.logger.info("=" * 70)
    activity.logger.info("🚀 DEPLOY INVENTORY CONTAINER - STARTING")
    activity.logger.info("=" * 70)
    
    slug = input_data.get("company_slug", "test-client-14")
    tier = TIERS.get(input_data.get("tier", "standard"))
    
    activity.logger.info(f"📋 Input Parameters:")
    activity.logger.info(f"   Company Slug: {slug}")
    activity.logger.info(f"   Tier: {input_data.get('tier', 'standard')}")
    
    # 1. Generate Secrets
    activity.logger.info("🔐 Generating Secrets...")
    db_root_pass = secrets.token_urlsafe(16)
    admin_pass = secrets.token_urlsafe(12)
    site_url = f"{slug}.f3next.in" 
    container_name = f"{slug}-app"
    
    # --- PRINT PASSWORDS TO LOGS ---
    activity.logger.info("------------------------------------------------------")
    activity.logger.info(f"🔑 Admin Password:    {admin_pass}")
    activity.logger.info(f"🔑 DB Root Password:  {db_root_pass}")
    activity.logger.info("------------------------------------------------------")
    
    # 2. Render Template
    activity.logger.info("📝 Rendering Docker Compose Template...")
    template = Template(DOCKER_COMPOSE_TEMPLATE)
    compose_content = template.render(
        stack_name=slug,
        db_root_password=db_root_pass,
        site_url=site_url,
        db_memory_limit=tier["db_mem"],
        app_memory_limit=tier["app_mem"],
        app_cpu_limit=tier["cpu"]
    )

    site_config = {
        "db_host": "db",
        "redis_cache": "redis://redis:6379",
        "redis_queue": "redis://redis:6379",
        "redis_socketio": "redis://redis:6379",
    }
    
    apps_content = "frappe\nerpnext\n"

    # 3. Deploy via SSH
    activity.logger.info("=" * 70)
    activity.logger.info(f"🔌 CONNECTING TO REMOTE SERVER: {EC2_HOST}")
    activity.logger.info("=" * 70)
    
    async with asyncssh.connect(EC2_HOST, username=EC2_USER, client_keys=[SSH_KEY_PATH]) as conn:
        base_dir = f"/opt/erp/clients/{slug}"
        
        # A. Clean Slate
        activity.logger.info(f"🚀 Initializing Client: {slug}")
        await run_logged(conn, f"cd {base_dir} && docker compose down", check=False, description="Cleanup: Docker Compose Down")
        
        # ⚠️ DESTRUCTIVE ACTION: Ensure we are only deleting the specific client directory
        if not base_dir.startswith("/opt/erp/clients/"):
            raise ValueError(f"Safety Check Failed: Attempting to delete unsafe path {base_dir}")
        await run_logged(conn, f"sudo rm -rf {base_dir}", check=True, description="Cleanup: Remove Base Directory")
        
        # Create directories
        await run_logged(conn, f"mkdir -p {base_dir}/mysql-data {base_dir}/sites {base_dir}/temp_app/f3next/f3next", check=True, description="Create Directory Structure")
        await run_logged(conn, f"sudo chown -R 1000:1000 {base_dir}/sites", check=True, description="Set Sites Directory Permissions")
        
        # B. Upload Configs via SFTP
        activity.logger.info("📤 Uploading Configuration Files via SFTP...")
        async with conn.start_sftp_client() as sftp:
            # Docker Configs
            async with sftp.open(f"{base_dir}/docker-compose.yml", 'w') as f:
                await f.write(compose_content)
            
            async with sftp.open(f"{base_dir}/sites/common_site_config.json", 'w') as f:
                await f.write(json.dumps(site_config))
            
            async with sftp.open(f"{base_dir}/sites/apps.txt", 'w') as f:
                await f.write(apps_content)
            
            async with sftp.open(f"{base_dir}/sites/currentsite.txt", 'w') as f:
                await f.write(site_url)
            
            async with sftp.open(f"{base_dir}/nginx-assets.conf", 'w') as f:
                await f.write(NGINX_ASSETS_CONFIG)

            # --- F3NEXT APP FILES (CRITICAL FIX HERE) ---
            activity.logger.info("📦 Uploading F3Next App Files...")
            
            # setup.py
            setup_py_content = (
                "from setuptools import setup, find_packages\n"
                "setup(name='f3next', version='0.0.1', packages=find_packages())"
            )
            async with sftp.open(f"{base_dir}/temp_app/f3next/setup.py", 'w') as f:
                await f.write(setup_py_content)
            
            # hooks.py - FIXED: Added required metadata to prevent 'NoneType' error
            hooks_content = (
                "app_name = 'f3next'\n"
                "app_title = 'Connector'\n"
                "app_publisher = 'F3Next'\n"
                "app_description = 'F3Next Connector App'\n"
                "app_email = 'support@f3next.in'\n"
                "app_license = 'MIT'\n"
            )
            async with sftp.open(f"{base_dir}/temp_app/f3next/f3next/hooks.py", 'w') as f:
                await f.write(hooks_content)
            
            # __init__.py
            async with sftp.open(f"{base_dir}/temp_app/f3next/f3next/__init__.py", 'w') as f:
                await f.write("__version__ = '0.0.1'")
            
            # api.py
            api_code = """
import frappe
@frappe.whitelist()
def apply_config(**kwargs):
    frappe.log(f"Config Received: {kwargs}")
    return {"status": "success", "message": "Config Applied"}
"""
            async with sftp.open(f"{base_dir}/temp_app/f3next/f3next/api.py", 'w') as f:
                await f.write(api_code)
        
        activity.logger.info("✅ All SFTP uploads completed")
        
        # C. EXTRACT ASSETS
        await run_logged(conn, f"mkdir -p {base_dir}/sites/assets", check=True, description="Create Assets Directory")
        
        # We ignore errors here because if the image changed, tar might complain, but usually it works enough.
        cmd_extract = (
            f"docker run --rm frappe/erpnext:v15 "
            f"tar c -h -C /home/frappe/frappe-bench/sites/assets . | "
            f"tar x -C {base_dir}/sites/assets"
        )
        await run_logged(conn, cmd_extract, check=False, description="Extract Assets")
        
        # Set permissions for assets
        await run_logged(conn, f"sudo chown -R 1000:1000 {base_dir}/sites/assets", check=True, description="Set Assets Ownership")

        # D. Start Stack
        await run_logged(conn, "docker network create traefik_default || true", check=True, description="Ensure Traefik Network")
        
        activity.logger.info("🐳 Starting DB and Redis...")
        await run_logged(conn, f"cd {base_dir} && docker compose up -d db redis", check=True)
        await asyncio.sleep(10)
        
        activity.logger.info("🐳 Starting Backend...")
        await run_logged(conn, f"cd {base_dir} && docker compose up -d backend assets", check=True)
        
        activity.logger.info("⏳ Waiting 25s for DB wakeup...")
        await asyncio.sleep(25) 

        # E. Install Site
        cmd_install = (
            f"cd {base_dir} && "
            f"docker compose exec -T backend bash -c \""
            f"bench new-site {site_url} "
            f"--force "
            f"--mariadb-root-password '{db_root_pass}' "
            f"--admin-password '{admin_pass}' "
            f"--mariadb-user-host-login-scope='%' "
            f"--install-app erpnext\""
        )
        
        activity.logger.info("🛠️ Installing ERPNext Site...")
        await run_logged(conn, cmd_install, check=True, description="Install ERPNext Site")

        # ==================================================================
        # 🤖 AUTOMATION: INJECT APP (The "Runtime Injection" Method)
        # ==================================================================
        activity.logger.info("🔌 Injecting F3Next Connector App...")
        try:
            # 1. Prepare Destination
            await run_logged(conn, f"docker exec {container_name} mkdir -p /home/frappe/frappe-bench/apps/f3next", check=True, description="Create App Dir")
            
            # 2. Copy Files
            await run_logged(conn, f"docker cp {base_dir}/temp_app/f3next/. {container_name}:/home/frappe/frappe-bench/apps/f3next/", check=True, description="Copy App Files")
            
            # 3. Fix Ownership
            await run_logged(conn, f"docker exec -u root {container_name} chown -R frappe:frappe /home/frappe/frappe-bench/apps/f3next", check=True, description="Fix App Permissions")
            
            # 4. Pip Install
            activity.logger.info("📦 Pip installing App...")
            await run_logged(conn, f"docker exec -u frappe {container_name} ./env/bin/pip install -e apps/f3next", check=True, description="Pip Install F3Next")
            
            # 5. Add to apps.txt (Crucial step often missed)
            # We verify if it exists first to avoid duplicates
            await run_logged(
                conn, 
                f"docker exec -u frappe {container_name} grep -qF 'f3next' sites/apps.txt || "
                f"docker exec -u frappe {container_name} bash -c \"echo 'f3next' >> sites/apps.txt\"",
                check=True,
                description="Update apps.txt"
            )

            # 6. Bench Install App on Site
            activity.logger.info(f"💾 Installing App on {site_url}...")
            await run_logged(conn, f"docker exec -u frappe {container_name} bench --site {site_url} install-app f3next", check=True, description="Bench Install App")
            
            activity.logger.info("✅ App Injected Successfully.")
            
        except Exception as e:
             activity.logger.error(f"❌ App Injection Failed: {e}")
             raise e
        # ==================================================================

        # F. Final Restart to ensure loaded code
        activity.logger.info("🔄 Final restart...")
        await run_logged(conn, f"cd {base_dir} && docker compose restart backend", check=True, description="Restart Backend")
        activity.logger.info("⏳ Waiting 15s for services...")
        await asyncio.sleep(15)

    # 🏁 THE HANDOFF
    activity.logger.info("=" * 70)
    activity.logger.info("✅ DEPLOYMENT COMPLETED")
    activity.logger.info(f"   Site URL: {site_url}")
    activity.logger.info(f"   Admin Password: {admin_pass}")
    activity.logger.info("=" * 70)
    
    return {
        "status": "infrastructure_ready",
        "project_id": input_data.get("project_id", "unknown"),
        "company_slug": slug,
        "infrastructure": {
            "ip_address": EC2_HOST,
            "ssh_user": EC2_USER,
            "db_root_password": db_root_pass,
            "admin_password": admin_pass,
            "base_dir": f"/opt/erp/clients/{slug}", 
            "site_url": site_url
        }
    }

# --- ACTIVITY 2: GENERATE API KEYS ---
@activity.defn
async def generate_erpnext_keys(input_data: dict) -> dict:
    infra = input_data["infrastructure"]
    base_dir = infra["base_dir"]
    site_url = infra["site_url"]
    
    # 🟢 1. CAPTURE THE PASSWORD (It was generated in the previous step)
    admin_password = infra.get("admin_password", "Not Set")

    activity.logger.info("=" * 70)
    activity.logger.info(f"🔑 STARTING KEY GENERATION: {site_url}")
    activity.logger.info("=" * 70)

    async with asyncssh.connect(EC2_HOST, username=EC2_USER, client_keys=[SSH_KEY_PATH]) as conn:
        
        # A. Fix Permissions
        await run_logged(conn, f"sudo chown -R 1000:1000 {base_dir}/sites", check=True, description="Fix Sites Permissions")

        # B. Python Script
        key_gen_script = f"""
import sys
import frappe
import os

try:
    if not os.path.exists('{site_url}/logs'):
        os.makedirs('{site_url}/logs', exist_ok=True)

    frappe.init(site='{site_url}', sites_path='.') 
    frappe.connect()
    
    user = frappe.get_doc('User', 'Administrator')
    
    api_key = frappe.generate_hash(length=15)
    api_secret = frappe.generate_hash(length=15)
    
    user.api_key = api_key
    user.api_secret = api_secret
    
    user.save(ignore_permissions=True)
    frappe.db.commit()
    
    print(f'KEY:{{api_key}}:SECRET:{{api_secret}}')

except Exception as e:
    print(f'ERROR:{{str(e)}}')
    sys.exit(0)
"""
        # C. Execution
        cmd_keygen = (
            f"cd {base_dir} && "
            f"docker compose exec -T --user frappe backend "
            f"bash -c \"cd /home/frappe/frappe-bench/sites && "
            f"mkdir -p {site_url}/logs && "
            f"../env/bin/python -u\""
        )
        
        activity.logger.info("⚡ Executing KeyGen...")
        try:
            result = await conn.run(cmd_keygen, input=key_gen_script, check=False)
            
            if result.exit_status != 0:
                activity.logger.error(f"❌ KeyGen failed: {result.stderr}")
                raise asyncssh.ProcessError(
                    result.env, result.command, result.subsystem,
                    result.exit_status, result.exit_signal,
                    result.returncode, result.stdout, result.stderr
                )
            
            output = result.stdout.strip()
            
            if "ERROR:" in output:
                raise Exception(f"Script Internal Error: {output}")

            match = re.search(r"KEY:(\w+):SECRET:(\w+)", output)
            if match:
                activity.logger.info("✅ Keys captured.")
                
                # 🟢 2. RETURN THE PASSWORD (So it gets saved to DB)
                return {
                    "api_key": match.group(1),
                    "api_secret": match.group(2),
                    "site_url": f"https://{site_url}",
                    "container_id": f"cnt_{input_data.get('company_slug', 'unknown')}", # Good to have
                    "admin_password": admin_password 
                }
            else:
                raise ValueError(f"Could not parse keys. Output: {output}")

        except Exception as e:
            activity.logger.error(f"❌ KeyGen Failed: {str(e)}")
            raise e

# --- ACTIVITY 3: SAVE TO DB ---
@activity.defn
async def save_deployment_details(input_data: dict) -> str:
    project_id = input_data["project_id"]
    details_to_save = input_data["deployment_details"]

    activity.logger.info(f"💾 Saving to DB for Project: {project_id}...")

    async with async_session() as session:
        async with session.begin():
            stmt = (
                update(Project)
                .where(Project.id == project_id)
                .values(
                    deployment_details=details_to_save,
                    status=ProjectStatus.DEPLOYMENT_COMPLETED
                )
            )
            result = await session.execute(stmt)
            
            if result.rowcount == 0:
                raise ValueError("Project ID not found in database")

    activity.logger.info("✅ Database updated.")
    return "Saved to DB"