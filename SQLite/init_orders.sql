PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
  order_id     TEXT PRIMARY KEY,                           -- 订单号
  user_id      TEXT,
  user_name    TEXT,                                       -- 收货人姓名（存全量）
  email        TEXT,                                       -- 邮箱
  phone        TEXT,                                       -- 手机号
  status       TEXT NOT NULL,                              -- 订单状态
  tracking_no  TEXT,                                       -- 运单号
  item_summary TEXT,                                       -- 商品摘要
  total_amount NUMERIC NOT NULL DEFAULT 0 CHECK(total_amount >= 0),
  created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now')),
  address      TEXT                                        -- 收货地址
);

-- 常用检索索引
CREATE INDEX IF NOT EXISTS idx_orders_email      ON orders(email);
CREATE INDEX IF NOT EXISTS idx_orders_phone      ON orders(phone);
