# -*- coding: utf-8 -*-
# tools/dbtools.py
"""
DB 工具：按 id / phone / email 查询订单 & 修改地址。
与当前表结构对齐：orders(order_id,user_id,user_name,email,phone,status,tracking_no,item_summary,total_amount,created_at,address)
统一输出结构，便于与 doc_qa 协作。
"""

import sqlite3
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, EmailStr, constr
from langchain_core.tools import tool

_DB_PATH = "SQLite/orders.db"


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(_DB_PATH, timeout=5)
    con.row_factory = sqlite3.Row
    # 可选：更稳的写入模式
    try:
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return con


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """把一行记录映射成统一输出字段；不存在的字段给 None。"""
    d = dict(row)

    def g(key: str, default=None):
        return d.get(key, default)

    return {
        # 统一的“事实”字段（Agent 主要用这些）
        "order_id": g("order_id"),
        "status": g("status"),
        "item": g("item_summary"),          # ✅ 你的表里叫 item_summary
        "total_amount": g("total_amount"),
        "created_at": g("created_at"),
        "address": g("address"),
        "phone": g("phone"),
        "email": g("email"),
        "tracking_no": g("tracking_no"),
        "last_updated": g("last_updated", None),   # 你的表目前没有该列，保持 None
        # 额外携带字段（有用就用，不用也不影响）
        "user_id": g("user_id"),
        "user_name": g("user_name"),
    }


# -------------------- 按订单号查询 --------------------
class OrderIdIn(BaseModel):
    order_id: str = Field(..., description="订单号，如 OD2408150001")


@tool("orders.get_by_id", args_schema=OrderIdIn)
def orders_get_by_id(order_id: str) -> Dict[str, Any]:
    """
    当用户给出订单号并想查询订单信息/状态时调用。
    输出：{"found": bool, "data": {...} 或 None, "meta": {...}}
    """
    with _connect() as con:
        cur = con.execute(
            "SELECT * FROM orders WHERE order_id=? LIMIT 1",
            (order_id,),
        )
        row = cur.fetchone()
    if not row:
        return {"found": False, "data": None, "meta": {"source": "sqlite/orders"}}
    return {"found": True, "data": _row_to_dict(row), "meta": {"source": "sqlite/orders"}}


# -------------------- 按手机号查询 --------------------
class PhoneIn(BaseModel):
    phone: constr(strip_whitespace=True, min_length=5, max_length=32) = Field(..., description="手机号")
    limit: int = Field(10, ge=1, le=50, description="返回条数（默认10）")


@tool("orders.search_by_phone", args_schema=PhoneIn)
def orders_search_by_phone(phone: str, limit: int = 10) -> Dict[str, Any]:
    """
    当用户只有手机号时调用；返回最近 N 笔订单摘要供用户确认。
    输出：{"total": int, "items": [{...}], "meta": {...}}
    """
    with _connect() as con:
        cur = con.execute(
            "SELECT * FROM orders WHERE phone=? ORDER BY created_at DESC LIMIT ?",
            (phone, limit),
        )
        rows = cur.fetchall()
    items = [_row_to_dict(r) for r in rows]
    return {"total": len(items), "items": items, "meta": {"source": "sqlite/orders", "phone": phone}}


# -------------------- 按邮箱查询 --------------------
class EmailIn(BaseModel):
    email: EmailStr = Field(..., description="邮箱地址")
    limit: int = Field(10, ge=1, le=50, description="返回条数（默认10）")


@tool("orders.search_by_email", args_schema=EmailIn)
def orders_search_by_email(email: EmailStr, limit: int = 10) -> Dict[str, Any]:
    """
    当用户只有邮箱时调用；返回最近 N 笔订单摘要供用户确认。
    """
    with _connect() as con:
        cur = con.execute(
            "SELECT * FROM orders WHERE email=? ORDER BY created_at DESC LIMIT ?",
            (email, limit),
        )
        rows = cur.fetchall()
    items = [_row_to_dict(r) for r in rows]
    return {"total": len(items), "items": items, "meta": {"source": "sqlite/orders", "email": email}}


# -------------------- 修改地址 --------------------
class AddressUpdateIn(BaseModel):
    order_id: str = Field(..., description="订单号")
    new_address: str = Field(..., description="新的收货地址")


@tool("orders.address_update", args_schema=AddressUpdateIn)
def orders_address_update(order_id: str, new_address: str) -> Dict[str, Any]:
    """
    当用户明确要求修改地址时调用。
    注意：已发货/已签收订单通常不可直接改，应先由 doc_qa 给出流程说明与备选方案后再决定是否调用。
    输出：{"ok": bool, "affected": int, "data": {...} 或 None, "meta": {...}}
    """
    with _connect() as con:
        cur = con.execute("UPDATE orders SET address=? WHERE order_id=?", (new_address, order_id))
        affected = cur.rowcount
        con.commit()

        cur = con.execute("SELECT * FROM orders WHERE order_id=? LIMIT 1", (order_id,))
        row = cur.fetchone()

    if affected == 0 or not row:
        return {"ok": False, "affected": 0, "data": None, "meta": {"source": "sqlite/orders"}}

    return {
        "ok": True,
        "affected": affected,
        "data": _row_to_dict(row),
        "meta": {"source": "sqlite/orders"},
    }
