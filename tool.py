# pip install langchain-core pydantic
from langchain_core.tools import tool
from pydantic import BaseModel, Field, EmailStr
import sqlite3

DB_PATH = "SQLite/orders.db"

# ============ 极简入参模型 ============
class ById(BaseModel):
    order_id: str = Field(..., description="订单号")

class ByPhone(BaseModel):
    phone: str = Field(..., description="手机号")

class ByEmail(BaseModel):
    email: EmailStr = Field(..., description="邮箱")

class AddressUpdate(BaseModel):
    order_id: str = Field(..., description="订单号")
    new_address: str = Field(..., description="新地址")

# ============ Tool 1：按订单号查询 ============
@tool(
    name="orders.get_by_id",
    args_schema=ById,
    description="当用户提供订单号时使用，返回该订单的关键信息。"
)
def orders_get_by_id(order_id: str) -> str:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT order_id, status, item_summary, total_amount, created_at, address, tracking_no
        FROM orders WHERE order_id = ?
    """, (order_id,))
    row = cur.fetchone()
    con.close()
    if not row:
        return f"未找到订单 {order_id}"
    oid, status, items, amt, created, addr, tracking = row
    return (f"订单{oid}｜状态：{status}｜商品：{items}｜金额：¥{amt}｜"
            f"下单：{created}｜地址：{addr}｜运单：{tracking or '—'}")

# ============ Tool 2：按手机号查询 ============
@tool(
    name="orders.search_by_phone",
    args_schema=ByPhone,
    description="当用户只有手机号时使用，列出该手机号下的最近若干订单。"
)
def orders_search_by_phone(phone: str) -> str:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT order_id, status, total_amount, created_at
        FROM orders WHERE phone = ?
        ORDER BY created_at DESC LIMIT 10
    """, (phone,))
    rows = cur.fetchall()
    con.close()
    if not rows:
        return f"号码 {phone} 下未找到订单"
    lines = [f"{i+1}. {r[0]}｜{r[1]}｜¥{r[2]}｜{r[3]}" for i, r in enumerate(rows)]
    return "该手机号下的订单（最多10条）：\n" + "\n".join(lines)

# ============ Tool 3：按邮箱查询 ============
@tool(
    name="orders.search_by_email",
    args_schema=ByEmail,
    description="当用户只有邮箱时使用，列出该邮箱下的最近若干订单。"
)
def orders_search_by_email(email: str) -> str:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT order_id, status, total_amount, created_at
        FROM orders WHERE email = ?
        ORDER BY created_at DESC LIMIT 10
    """, (email,))
    rows = cur.fetchall()
    con.close()
    if not rows:
        return f"邮箱 {email} 下未找到订单"
    lines = [f"{i+1}. {r[0]}｜{r[1]}｜¥{r[2]}｜{r[3]}" for i, r in enumerate(rows)]
    return "该邮箱下的订单（最多10条）：\n" + "\n".join(lines)

# ============ Tool 4：修改收货地址 ============
@tool(
    name="orders.address_update",
    args_schema=AddressUpdate,
    description="当用户明确要改地址且给出订单号与新地址时使用。更新后回显新地址。"
)
def orders_address_update(order_id: str, new_address: str) -> str:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("UPDATE orders SET address = ? WHERE order_id = ?", (new_address, order_id))
    con.commit()
    cur.execute("SELECT order_id, address FROM orders WHERE order_id = ?", (order_id,))
    row = cur.fetchone()
    con.close()
    if not row:
        return f"未找到订单 {order_id}，未更新"
    return f"订单 {row[0]} 的地址已更新为：{row[1]}"
