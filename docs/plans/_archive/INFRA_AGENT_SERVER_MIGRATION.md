# Infra Agent — Server Migration Guide

> **Written**: 2026-06-30
> **Updated**: 2026-06-30 — Enriched with verified session memory from the LLM that was present during all `infra_agent` development and debugging sessions. Everything in this document is confirmed, not speculated.

---

## Short Answer

The `infra_agent` code is portable — it reads the target server IP, SSH key, and user from `.env`. But it **assumes a very specific server state** that was built up through manual SSH sessions, one-off fixes, and debugging commands that are not recorded in any code file. This document is the complete record of that state.

---

## 🔴 Critical: What WILL Break on a New Server

### 1. Hardcoded Fallback IP — `65.2.125.86`

**File**: `containers/erpnext/infra_agent/activities.py` — Line 17

```python
EC2_HOST = os.environ.get("EC2_HOST", "65.2.125.86")  # ← old server IP as fallback!
EC2_USER = os.environ.get("EC2_USER", "ubuntu")
SSH_KEY_PATH = os.environ.get("SSH_KEY_PATH", "/app/secrets/f3.pem")
```

If `EC2_HOST` is ever missing from `.env`, the agent **silently SSHes into the old server**.

**Action**: Update `.env`. Remove the hardcoded IP fallback in the code — make it raise loudly if the env var is missing.

---

### 2. SSH Key (`.pem` File) — Account-Specific, Not in Repo

**File**: `docker-compose.yml` — Line 76

```yaml
volumes:
  - ./secrets:/app/secrets   # f3.pem is volume-mounted from here
```

- `f3.pem` is the Key Pair tied to the **current AWS account**. A new account = new key pair.
- `./secrets/` directory in the repo is **empty** — the file only lives on the running server.
- Access was **strictly key-based**. Password authentication was **disabled by default** on the server (`sshd_config`). If a new server or provider requires password auth, you must manually set `PasswordAuthentication yes` in `/etc/ssh/sshd_config` and restart `sshd`.

**Action**:
1. Generate a Key Pair on the new server/provider.
2. Place the `.pem` in `./secrets/`.
3. Update `SSH_KEY_PATH` in `.env`.

---

### 3. Traefik — Manually Installed, NOT Deployed by infra_agent

**This is the most complex dependency.** Traefik runs as a standalone Docker container on the server, completely separate from all client ERPNext stacks. The `infra_agent` code assumes it already exists — if it doesn't, every provisioned client will have no routing and no TLS.

#### Confirmed Traefik Config from the Current Server

| Setting | Value |
|---|---|
| Version | `traefik:v2.10` |
| Installation | Standalone Docker container (not inside any client compose stack) |
| Port 80 entrypoint | `web` |
| Port 443 entrypoint | **`websecure`** ← exact name used in all client labels |
| TLS Cert Resolver | **`myresolver`** ← exact name used in all client labels |
| TLS Provider | Let's Encrypt (auto, no manual Certbot needed) |
| Traefik API/Dashboard | Enabled on port `8080` |
| Docker network | **`traefik_default`** ← all client containers attach to this |

> ⚠️ **If you rename `websecure` or `myresolver` to anything else on the new server, every single client deployment will silently fail.** Traefik will respond with `404 page not found` because the router labels in the client `docker-compose.yml` files won't match.

#### The Network Gotcha (Easy to Miss)

**Manually create the Docker network BEFORE starting Traefik:**

```bash
docker network create traefik_default
```

If you let Docker Compose auto-create it, Docker may **prefix the network with the folder name** (e.g., `traefik_traefik_default`). The `infra_agent` hardcodes `name: traefik_default` in every client's compose file — if the actual network name is different, client containers can't attach to it and Traefik can't reach them.

---

### 4. Docker — Must Be Installed (V2 Plugin, Not V1 Binary)

The server was running **Docker Compose V2** (the plugin). All agent commands use `docker compose` (with a space), not `docker-compose`.

- Install Docker Engine via the official Docker script, not `snap`.
- Install the **Compose V2 plugin** (`docker-compose-plugin` package), not the standalone V1 binary.

> ⚠️ **If only V1 is installed, the agent's SSH commands (`docker compose up`, `docker compose exec`) will all fail with `command not found`.**

#### The K3s Warning — Keep the New Server Clean

On the current server, **K3s (lightweight Kubernetes) and Flux were secretly running alongside Docker**. K3s has its own internal Traefik controller that was stealing ports 80 and 443, and the K3s pods were starving ERPNext containers of RAM. It took a nuclear uninstall to fix:

```bash
/usr/local/bin/k3s-uninstall.sh
rm -rf ~/.kube
sudo rm /usr/local/bin/flux
sudo systemctl restart docker   # ← to restore Docker's iptables routing
```

**Action**: On the new server, install ONLY Docker. Nothing else that manages containers or networking (no K3s, no Podman, no anything). If Docker's networking ever seems broken, `sudo systemctl restart docker` resets iptables.

---

### 5. Directory Structure on the Target Server

The agent creates client directories at `/opt/erp/clients/<slug>/`. Each client folder contains:

```
/opt/erp/clients/<slug>/
├── docker-compose.yml        # Generated and SFTP'd by infra_agent
├── nginx-assets.conf         # Static nginx config for ERPNext assets
├── mysql-data/               # MariaDB persistent data
├── sites/                    # Frappe sites volume
│   ├── common_site_config.json
│   ├── apps.txt
│   ├── currentsite.txt
│   ├── assets/               # Extracted ERPNext static assets
│   └── keygen.py             # Temporary script (written during key gen step)
└── temp_app/                 # Used during F3Next app injection via SFTP
    └── f3next/
        ├── setup.py
        └── f3next/
            ├── __init__.py
            ├── hooks.py
            └── api.py
```

> **Important**: There are NO `.env` files on the server. Passwords are generated dynamically in Temporal, injected into `docker-compose.yml` and `common_site_config.json` via Jinja templating, and SFTP'd directly. Don't look for `.env` files on the new server — they're not supposed to exist.

#### Frappe Logs Directory Bug

Inside the Frappe (`backend`) container, `/home/frappe/logs` **does not exist by default**. If you ever run raw Python scripts via SSH (bypassing `bench`), Frappe crashes with a `FileNotFoundError`. Fix:

```bash
docker compose exec -T backend mkdir -p /home/frappe/logs
```

---

### 6. Domain DNS — `*.f3next.in` → Current Server's IP

**File**: `activities.py` — Line 173

```python
site_url = f"{slug}.f3next.in"   # domain suffix is hardcoded
```

DNS is managed in Cloudflare. The wildcard `*.f3next.in` (or individual A records) currently points to the old server's IP.

**Action**: Update the `A` record in Cloudflare to the new server's IP **before** any client is provisioned (Traefik needs to be reachable to issue Let's Encrypt certs for new subdomains).

---

## 🟡 Existing Client State on the Current Server

These slugs were deployed and are currently running (or were successfully tested):

| Slug | Status | Notes |
|---|---|---|
| `green-surface` | ✅ Active | Real client — preserve data if migrating |
| `tesla` | ✅ Active | Tested and functional |
| `f3` | ✅ Active | Tested and functional |
| `apollo` | 🗑️ Burner | Test deployment — safe to delete |
| `f4` | 🗑️ Burner | Test deployment — safe to delete |
| `f5` | 🗑️ Burner | Test deployment — safe to delete |
| `f6` | 🗑️ Burner | Test deployment — safe to delete |
| `test-client-99` | 🗑️ Burner | Test deployment — safe to delete |

**Burner cleanup** (run on old server to free disk space):
```bash
cd /opt/erp/clients/apollo && docker compose down -v && cd / && sudo rm -rf /opt/erp/clients/apollo
# repeat for f4, f5, f6, test-client-99
```

**The `infra_agent` only creates new stacks — it cannot migrate existing ones.** If you want `green-surface`, `tesla`, or `f3` on the new server, they must be manually migrated:

```bash
# On old server — stop and tar the client data
cd /opt/erp/clients/green-surface
docker compose down
sudo tar czf /tmp/green-surface-backup.tar.gz .

# Transfer to new server
scp -i f3.pem /tmp/green-surface-backup.tar.gz ubuntu@<new-ip>:/opt/erp/clients/

# On new server — restore and start
cd /opt/erp/clients/
sudo mkdir green-surface && cd green-surface
sudo tar xzf ../green-surface-backup.tar.gz
docker compose up -d
```

---

## ⚠️ Known Bugs & Workarounds (Confirmed from Debug Sessions)

### 1. `admin_password` Drop in Temporal Workflow

The Temporal workflow (`workflows.py`) was initially dropping `admin_password` before saving to DB. The fix is already in `STEP 3` of the workflow — `"admin_password": keys_result.get("admin_password")` must be mapped in `save_input`. Verify this exists before running on the new server.

### 2. Temporal Worker Does NOT Hot-Reload

Every time you change `activities.py` or `workflows.py`, you **must manually kill and restart the worker**. It will silently continue running old code otherwise. There is no file-watching or hot-reload.

```bash
# Kill the running worker container and restart
docker compose restart erpnext_infra_worker
```

### 3. Do NOT Use `bench console` for Python Scripts

Piping multi-line Python into `bench console` (IPython) mangles indentation and drops variables, resulting in `NameError` and empty JSON output. **Always inject the script into the `f3next` app folder and use `bench execute` instead.**

Wrong:
```bash
echo "import frappe; ..." | docker compose exec backend bench console
```

Right:
```bash
# Write script to volume, then execute via bench
docker compose exec backend bench --site <site_url> execute f3next.your_script
```

### 4. App Injection — `temp_app` Must Be Wiped Clean on Every Run

The `infra_agent` copies the `f3next` custom app into `temp_app/` via SFTP before injecting into the container. If a previous failed deployment left stale files there, those files will contaminate the new client's app. The agent already does `sudo rm -rf {base_dir}` at the start of every provisioning — don't remove this safety step.

### 5. Manual Password Reset (Break-Glass Procedure)

If a deployment succeeds but the admin password isn't saved to DB (workflow bug), reset it manually:

```bash
docker compose exec backend bench --site <site_url> set-admin-password <new_password>
```

### 6. Heredoc Script Injection (Alternative to SFTP)

To inject Python scripts into a running container without SFTP (e.g., for data extraction without triggering Frappe's standalone logging bugs):

```bash
docker exec -i <container_name> bash -c "cat << 'EOF' > /path/to/script.py
# your python code here
EOF"
```

---

## ✅ New Server Setup Checklist

```
[ ] 1.  Launch a new Ubuntu server (EC2, DigitalOcean, Hetzner, etc.)
         Open ports: 22 (SSH), 80 (HTTP), 443 (HTTPS), 8080 (Traefik dashboard)

[ ] 2.  Install Docker Engine via official Docker script (NOT snap)
         Install Docker Compose V2 plugin (docker-compose-plugin)
         Add ubuntu user to docker group: sudo usermod -aG docker ubuntu

[ ] 3.  Do NOT install K3s, Podman, or any other container orchestrator.
         The server must be Docker-only.

[ ] 4.  Manually create the Traefik network BEFORE starting anything:
         docker network create traefik_default

[ ] 5.  Install and start Traefik v2.10 as a standalone Docker container with:
         - entrypoint "web" on port 80
         - entrypoint "websecure" on port 443   ← exact name matters
         - certresolver named "myresolver"       ← exact name matters
         - Let's Encrypt ACME (automatic TLS)
         - Docker provider with socket access (/var/run/docker.sock)
         - Attached to the traefik_default network
         - Dashboard enabled on port 8080 (optional but useful)
         - restart: always

[ ] 6.  Update DNS in Cloudflare:
         *.f3next.in  A  <new-server-public-ip>
         Wait for propagation before provisioning any client.

[ ] 7.  Generate SSH Key Pair for the new server.
         Place the .pem file in ./secrets/ on your local dev machine.

[ ] 8.  Update .env:
         EC2_HOST=<new-server-public-ip>
         EC2_USER=ubuntu
         SSH_KEY_PATH=/app/secrets/<new-key-name>.pem
         (also update TEMPORAL_HOST, NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SITE_URL)

[ ] 9.  Fix activities.py L17:
         Remove "65.2.125.86" hardcoded fallback.
         Let it crash loudly if EC2_HOST env var is missing.

[ ] 10. Deploy all F3Next services on the new app server:
         docker compose up -d

[ ] 11. Decide fate of existing clients on old server:
         - Burner slugs (apollo, f4, f5, f6, test-client-99): delete them
         - Real clients (green-surface, tesla, f3): migrate manually or
           keep old server alive until clients are re-provisioned

[ ] 12. Test end-to-end: provision a throwaway slug on the new server.
         Verify Traefik routes it correctly and TLS cert is issued.
```

---

## 🟢 What Is Portable (Nothing Changes)

| Component | Why it's fine |
|---|---|
| Workflow logic (`workflows.py`) | Pure Temporal orchestration, zero server coupling |
| Activity code (`activities.py`) | Fully env-var driven (except the one fallback IP) |
| Docker images (`frappe/erpnext:v15`, `mariadb:10.6`) | Pulled from Docker Hub |
| Supabase (Auth + DB) | External SaaS, unaffected |
| LLM API Keys (OpenAI/Gemini) | External, unaffected |
| S3 / Cloudflare R2 | External, unaffected |
| Temporal server | Runs in Docker, moves with the app server |
| All other agents (Discovery, OS, CVS, IS) | Don't SSH into the server — only `infra_agent` does |

---

## Note on Cloud Provider Lock-in

The `infra_agent` is **not AWS-specific**. It uses plain SSH (`asyncssh`) to any Linux server. The only AWS coupling is:

- The `.pem` key format (also standard on DigitalOcean, Hetzner, etc.)
- The old IP in the hardcoded fallback (which should be removed)

You can migrate to any Ubuntu VPS on any cloud and it works identically — as long as the checklist above is complete.
