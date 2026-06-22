"""查看数据库表结构。用法：ENV=dev python scripts/show_table.py posts"""
import asyncio
import sys

from sqlalchemy import text

from src.config.db import mysql_engine


async def main(table: str):
    async with mysql_engine.connect() as conn:
        result = await conn.execute(text(f"SHOW CREATE TABLE {table}"))
        print(result.fetchone()[1])
    await mysql_engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python scripts/show_table.py <表名>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
