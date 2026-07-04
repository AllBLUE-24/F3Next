# Prompt: Extract infra_agent Server Knowledge from Previous Session

> **Purpose**: Send this prompt to the LLM that was active during the `infra_agent` development sessions. That LLM has context of every SSH command run, every manual change made on the EC2 server, every debugging session, and any decisions taken on the fly that are not written in the code. The goal is to extract all of that knowledge before migrating to a new server.

---

## The Prompt

---

You were present when I built and debugged the `infra_agent` — the Temporal-based workflow that SSHes into an EC2 server and provisions ERPNext stacks for clients. I need your full memory of everything that was done on that server **outside of the code** — all the manual SSH commands, manual configuration changes, one-time setups, and any fixes we applied directly on the machine.

I am migrating to a new server (new AWS account or a different cloud provider entirely). I need to reconstruct the **exact server state** so the infra_agent works the same way on a clean machine.

Please recall and provide:

---

### 1. Traefik Setup
- What version of Traefik was installed?
- How was it installed — via a `docker-compose.yml`, as a standalone binary, or some other way?
- What was the exact Traefik configuration? (entrypoints, certresolver name, Let's Encrypt email, ACME storage path, Docker provider settings)
- Was there a `traefik.yml` or `traefik.toml` static config? What was in it?
- What Docker network name was used (`traefik_default`)?
- Was Traefik set to restart automatically?
- Any dashboards or API endpoints that were enabled?

---

### 2. Docker Setup on the Server
- How was Docker installed — via `apt`, `snap`, official Docker script, or something else?
- Was Docker Compose V2 (plugin) or V1 (standalone binary) installed?
- Were there any Docker daemon configuration changes (`/etc/docker/daemon.json`)?
- Were there any post-install steps done (adding `ubuntu` to the `docker` group, etc.)?

---

### 3. Directory Structure & Permissions
- Was `/opt/erp/clients/` created manually? What permissions does it have?
- Was there any other directory structure set up under `/opt/erp/` or elsewhere?
- Were there any bind mounts, symlinks, or NFS mounts set up?

---

### 4. SSH & Security
- Was the `.pem` key the only way to SSH in, or were any additional SSH keys added to `~/.ssh/authorized_keys`?
- Was `fail2ban`, `ufw`, or any other firewall/security tool installed and configured?
- Were any ports opened or closed beyond 22, 80, 443?
- Was `sshd_config` modified in any way?

---

### 5. Manual Fixes and One-Off Commands
- Were there any manual fixes applied directly on the server (not in the code) to get ERPNext or Frappe working?
- Were any files edited manually on the server (configs, site configs, etc.)?
- Were any `bench` commands run manually that are not part of the provisioning workflow?
- Were there any issues with file permissions (chown/chmod) that required manual fixes beyond what the agent does?
- Were any environment variables set globally on the server (`/etc/environment`, `.bashrc`, etc.)?

---

### 6. Network & DNS
- How was the `*.f3next.in` wildcard DNS set up — was it a wildcard A record or individual records per client?
- Was Cloudflare proxy (orange cloud) enabled or was it DNS-only?
- Was there any SSL configuration done outside of Traefik (like certbot or nginx)?

---

### 7. Existing Client Stacks
- Which client slugs were successfully deployed and are currently running on the server?
- Were there any partial deployments or broken stacks that need to be cleaned up?
- Are there any clients whose data we care about preserving during migration?

---

### 8. Anything Else on the Server
- Was anything else installed on the server that the system depends on (nginx, certbot, supervisor, cron jobs, monitoring agents, etc.)?
- Were there any cron jobs set up (`crontab -e` or `/etc/cron.d/`)?
- Were there any systemd services created for any part of the stack?
- Was there anything done to handle server restarts (ensuring Docker and Traefik come back up automatically)?

---

### 9. Known Issues or Workarounds
- Were there any known bugs, hacks, or workarounds applied on the server to make things work that are NOT reflected in the code?
- Were there any commands we had to run every time after a deployment that should really be automated?
- Were there any timing issues, race conditions, or retry patterns we discovered manually?

---

**Additionally**: Please think beyond what I asked above. Based on everything you know about what we did in those sessions — is there anything you think I should know before I set up a fresh server? Any surprise gotchas, anything we did that I might forget, anything that was fragile or "worked but shouldn't have"? Anything that might seem obvious but will silently break if not done? Share whatever comes to mind — I'd rather have too much information than miss something critical.

---

> *This prompt is stored at `docs/INFRA_AGENT_SERVER_MEMORY_PROMPT.md` in the F3Next repository.*
