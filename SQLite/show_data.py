import sqlite3

def connect():
    con = sqlite3.connect("SQLite/orders.db")
    con.row_factory = sqlite3.Row  # 查询结果支持 dict 访问
    return con

# 查询全部
with connect() as con:
    rows = con.execute("SELECT * FROM orders LIMIT 5").fetchall()
    for r in rows:
        print(dict(r))