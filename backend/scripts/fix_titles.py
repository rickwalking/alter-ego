import asyncio
import asyncpg

async def fix():
    conn = await asyncpg.connect('postgresql://rag_user:EAd4u2v60WL14sXLAid2iP35TXapCUm9bXA1WZvaTZM=@postgres:5432/rag_db')
    rows = await conn.fetch('SELECT id, title FROM carousel_projects')
    for row in rows:
        old_title = row['title']
        # Extract just the first line (before any newline)
        first_line = old_title.split('\n')[0].strip()
        clean = first_line.strip()
        if clean != old_title:
            await conn.execute(
                'UPDATE carousel_projects SET title = $1 WHERE id = $2',
                clean, row['id']
            )
            print(f'Fixed: {clean[:60]}')
    await conn.close()

asyncio.run(fix())
