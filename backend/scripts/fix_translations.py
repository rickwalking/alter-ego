import asyncio
import asyncpg
import json
import os

async def fix():
    db_url = os.environ['DATABASE_URL'].replace('+asyncpg', '')
    conn = await asyncpg.connect(db_url)
    rows = await conn.fetch('SELECT id, blog_translations FROM carousel_projects')
    for row in rows:
        bt = json.loads(row['blog_translations']) if row['blog_translations'] else {}
        if not isinstance(bt, dict):
            bt = {}
        bt.setdefault('pt', '')
        bt.setdefault('en', '')
        bt = {k: (v if v is not None else '') for k, v in bt.items()}
        await conn.execute(
            'UPDATE carousel_projects SET blog_translations = $1 WHERE id = $2',
            json.dumps(bt), row['id']
        )
    await conn.close()
    print(f'Fixed DB translations for {len(rows)} projects')

asyncio.run(fix())
