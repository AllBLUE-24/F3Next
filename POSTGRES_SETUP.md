# PostgreSQL Setup for F3Next

Standalone guide to set up PostgreSQL for this project. Use this with Google AI Studio or any environment.

---

## Option 1: Docker (Easiest)

### 1. Run PostgreSQL in Docker

```bash
docker run -d \
  --name f3next-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=f3next_db \
  -p 5432:5432 \
  postgres:16-alpine
```

### 2. Connection string for .env

```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/f3next_db
```

### 3. Stop/Start

```bash
docker stop f3next-postgres
docker start f3next-postgres
```

---

## Option 2: Local Install (Windows)

### 1. Download PostgreSQL

- Go to https://www.postgresql.org/download/windows/
- Download the installer (e.g. PostgreSQL 16)
- Run installer, set a password for `postgres` user
- Default port: 5432

### 2. Create database and user

Open **pgAdmin** or **psql** (Command Line Tools):

```sql
-- Create database
CREATE DATABASE f3next_db;

-- Optional: Create a dedicated user
CREATE USER f3next_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE f3next_db TO f3next_user;
```

### 3. Connection string

```
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/f3next_db
```

Or with dedicated user:
```
DATABASE_URL=postgresql+asyncpg://f3next_user:your_password@localhost:5432/f3next_db
```

---

## Option 3: Docker Compose (Project-integrated)

Create `docker-compose.yml` in project root:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16-alpine
    container_name: f3next-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: f3next_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Run:
```bash
docker-compose up -d
```

---

## After PostgreSQL is Running

### 1. Install asyncpg (Python)

```bash
pip install asyncpg
```

### 2. Run migration (add implementation columns)

```bash
# Using psql
psql -U postgres -d f3next_db -f backend/migrations/add_implementation_columns.sql

# Or connect and run manually:
# ALTER TABLE projects ADD COLUMN IF NOT EXISTS implementation_profile JSONB;
# ALTER TABLE hooks ADD COLUMN IF NOT EXISTS discovery_metadata JSONB;
```

### 3. Create tables (if fresh DB)

The backend creates tables on startup. If you have a **fresh** database with no tables, the backend will create them when you run:

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Connection String Format

```
postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DATABASE
```

| Part      | Example   |
|-----------|-----------|
| USER      | postgres  |
| PASSWORD  | password  |
| HOST      | localhost |
| PORT      | 5432      |
| DATABASE  | f3next_db |

**Important:** Use `postgresql+asyncpg://` (not `postgresql://`) — the project uses async PostgreSQL.

---

## Verify Connection

```bash
# Using psql
psql -U postgres -d f3next_db -c "SELECT 1;"

# Or Python
python -c "
import asyncio
import asyncpg
async def test():
    conn = await asyncpg.connect('postgresql://postgres:password@localhost:5432/f3next_db')
    print('Connected!')
    await conn.close()
asyncio.run(test())
"
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `connection refused` | PostgreSQL not running. Start Docker container or Windows service. |
| `password authentication failed` | Check username/password in DATABASE_URL |
| `database "f3next_db" does not exist` | Run `CREATE DATABASE f3next_db;` |
| `asyncpg` module not found | Run `pip install asyncpg` |
