import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv('c:/dev/F3Next/.env')

async def main():
    try:
        url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg', 'postgresql')
        conn = await asyncpg.connect(url)
        
        # Create Auth Trigger properly via asyncpg bypassing SQLAlchemy formatting exceptions
        trigger_func = """
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS trigger AS $$
        BEGIN
          INSERT INTO public.clients (id, email, full_name, role)
          VALUES (new.id, new.email, '', 'owner');
          RETURN new;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
        await conn.execute(trigger_func)
        await conn.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;")
        
        trigger_def = """
        CREATE TRIGGER on_auth_user_created
          AFTER INSERT ON auth.users
          FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
        """
        await conn.execute(trigger_def)
        print("Triggers created successfully via asyncpg!")
        
        # Check auth trigger
        res = await conn.fetch("SELECT trigger_name FROM information_schema.triggers WHERE event_object_schema = 'auth' AND event_object_table = 'users';")
        print("Triggers on auth.users:", [r['trigger_name'] for r in res])
        
        # Check tables
        rows = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        for r in rows:
            tname = r['table_name']
            if tname.startswith('is_'):
                print(f'-- {tname} --')
                cols = await conn.fetch(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{tname}'")
                for c in cols:
                    print(f"  {c['column_name']}: {c['data_type']}")
                    
        await conn.close()
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
