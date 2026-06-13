"""Verify xinxi schema tables"""
import psycopg
conn = psycopg.connect('postgresql://langfuse:langfuse@localhost:5433/langfuse', autocommit=True)
cur = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='xinxi' ORDER BY tablename")
tables = [r[0] for r in cur.fetchall()]
print(f"xinxi schema tables ({len(tables)}): {tables}")
for t in tables:
    cur = conn.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='xinxi' AND table_name='{t}' ORDER BY ordinal_position")
    cols = cur.fetchall()
    print(f"\n  [{t}] ({len(cols)} columns)")
    for col_name, dtype in cols:
        print(f"    {col_name}: {dtype}")
conn.close()
