import secrets
import asyncssh
import asyncio
import json
from temporalio import activity
from jinja2 import Template

# Configuration
EC2_HOST = "65.2.125.86"
EC2_USER = "ubuntu"
SSH_KEY_PATH = r"C:\Users\Mayur Laxman Aldar\Downloads\f3.pem"

TIERS = {
    "standard": {"db_mem": "1G", "app_mem": "1G", "cpu": "1.0"},
    "premium":  {"db_mem": "2G", "app_mem": "4G", "cpu": "2.0"}
}

# 1. CUSTOM NGINX CONFIG
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

# 2. DOCKER TEMPLATE
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

@activity.defn
async def deploy_inventory_container(input_data: dict) -> dict:
    slug = input_data.get("company_slug", "test-client-11")
    tier = TIERS.get(input_data.get("tier", "standard"))
    
    # 1. Generate Secrets
    db_root_pass = secrets.token_urlsafe(16)
    db_user_pass = secrets.token_urlsafe(16)
    admin_pass = secrets.token_urlsafe(12)
    site_url = f"{slug}.f3next.in" 

    # 2. Render Template
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
    activity.logger.info(f"Connecting to {EC2_HOST}...")
    
    async with asyncssh.connect(EC2_HOST, username=EC2_USER, client_keys=[SSH_KEY_PATH]) as conn:
        base_dir = f"/opt/erp/clients/{slug}"
        
        # A. Clean Slate
        activity.logger.info(f"🚀 Initializing Client: {slug}")
        await conn.run(f"cd {base_dir} && docker compose down", check=False)
        await conn.run(f"sudo rm -rf {base_dir}", check=True)
        await conn.run(f"mkdir -p {base_dir}/mysql-data {base_dir}/sites", check=True)
        await conn.run(f"sudo chown -R 1000:1000 {base_dir}/sites", check=True)
        
        # B. Upload Configs
        async with conn.start_sftp_client() as sftp:
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
        
        # C. EXTRACT ASSETS (The Zero-RAM Method)
        # We start a temporary container (no volumes!) to read the pristine image.
        # We pipe 'tar' output directly to the host.
        # '-h' flag Dereferences symlinks (Turns links into real files).
        activity.logger.info("📦 Smart Extracting Assets (No Build)...")
        
        # Create destination
        await conn.run(f"mkdir -p {base_dir}/sites/assets", check=True)
        
        # Run the extraction
        cmd_extract = (
            f"docker run --rm frappe/erpnext:v15 "
            f"tar c -h -C /home/frappe/frappe-bench/sites/assets . | "
            f"tar x -C {base_dir}/sites/assets"
        )
        await conn.run(cmd_extract, check=True)
        
        # Fix Permissions
        await conn.run(f"sudo chown -R 1000:1000 {base_dir}/sites/assets", check=True)
        await conn.run(f"sudo chmod -R 755 {base_dir}/sites/assets", check=True)

        # D. Start Stack
        await conn.run("docker network create traefik_default || true", check=True)
        activity.logger.info("🐳 Starting Full Stack...")
        # Start DB and Redis first
        await conn.run(f"cd {base_dir} && docker compose up -d db redis", check=True)
        await asyncio.sleep(10)
        # Start Backend and Assets
        await conn.run(f"cd {base_dir} && docker compose up -d backend assets", check=True)
        
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
        
        activity.logger.info("🛠️ Installing ERPNext...")
        try:
            await conn.run(cmd_install, check=True)
            
            # F. Final Restart
            activity.logger.info("🔄 Final restart...")
            await conn.run(f"cd {base_dir} && docker compose restart backend", check=True)
            activity.logger.info("⏳ Waiting 30s for services to stabilize...")
            await asyncio.sleep(30)

        except asyncssh.ProcessError as e:
            activity.logger.error(f"❌ Deployment Failed! STDERR: {e.stderr}")
            raise e

    return {
        "status": "success",
        "company_slug": slug,
        "site_url": f"https://{site_url}",
        "erp_admin_password": admin_pass,
        "db_root_password": db_root_pass,
        "ip_address": EC2_HOST
    }