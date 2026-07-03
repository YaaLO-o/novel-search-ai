"""
查询 novels.sqlite 数据库
"""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "novels.sqlite"


def query_db():
    if not DB_PATH.exists():
        print(f"数据库不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 总数
    cursor.execute("SELECT COUNT(*) FROM novels")
    total = cursor.fetchone()[0]
    print(f"数据库中共有 {total} 本小说\n")

    # 按性向统计
    cursor.execute("""
        SELECT category, COUNT(*) as cnt
        FROM novels
        GROUP BY json_extract(category, '$.channel')
        ORDER BY cnt DESC
    """)
    print("按性向统计:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    # 示例数据
    print("\n示例数据:")
    cursor.execute("SELECT * FROM novels LIMIT 3")
    columns = [desc[0] for desc in cursor.description]
    for row in cursor.fetchall():
        print("\n" + "=" * 50)
        for col, val in zip(columns, row):
            if col in ("raw_tags", "category", "metrics"):
                try:
                    val = json.loads(val)
                    val = json.dumps(val, ensure_ascii=False, indent=2)
                except:
                    pass
            print(f"{col}: {val}")

    conn.close()


if __name__ == "__main__":
    query_db()
