import sqlite3
import random
import datetime

# 1) 初始化数据库（读取 init_orders.sql 并执行）
with open("SQLite/init_orders.sql", "r", encoding="utf-8") as f:
    sql = f.read()

con = sqlite3.connect("SQLite/orders.db")
con.executescript(sql)

# 2) 准备生成伪造订单数据
STATUS_LIST = ["待支付", "已支付待发货", "已发货", "已签收"]
NAMES = ["张三", "李四", "王五", "赵六", "孙七", "周八", "吴九", "郑十",
         "钱一", "刘二", "陈三", "杨四", "黄五", "高六", "林七", "何八",
         "马九", "罗十", "唐一", "冯二"]
ITEMS = [
    "蓝牙耳机x1, 保护壳x1",
    "机械键盘x1, 鼠标垫x1",
    "27寸显示器x1",
    "游戏手柄x2",
    "笔记本支架x1, 散热器x1",
    "智能手表x1",
    "U盘64Gx3",
    "路由器x1, 网线x2",
    "无线鼠标x1, 键盘x1",
    "平板电脑x1, 保护套x1"
]

def random_phone():
    return "1" + str(random.randint(3000000000, 3999999999))

def random_email(name):
    domains = ["@example.com", "@mail.com", "@test.cn"]
    return f"{name.lower()}{random.randint(1,99)}{random.choice(domains)}"

def random_datetime():
    start = datetime.datetime(2025, 1, 1)
    end = datetime.datetime(2025, 8, 15)
    delta = end - start
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86400)
    dt = start + datetime.timedelta(days=random_days, seconds=random_seconds)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# 3) 插入 20 条伪造数据
for i in range(1, 21):
    order_id = f"OD2408{150000+i:04d}"
    user_id = f"U{random.randint(100000, 999999)}"
    name = random.choice(NAMES)
    email = random_email(name)
    phone = random_phone()
    status = random.choice(STATUS_LIST)
    tracking_no = f"SF{random.randint(100000000, 999999999)}CN" if status in ["已发货", "已签收"] else None
    item_summary = random.choice(ITEMS)
    total_amount = round(random.uniform(50, 2000), 2)
    created_at = random_datetime()
    address = f"{random.choice(['北京市', '上海市', '广州市', '深圳市', '杭州市'])}" \
              f"{random.choice(['朝阳区', '浦东新区', '天河区', '南山区', '西湖区'])}某街道{random.randint(1,99)}号"

    con.execute("""
        INSERT INTO orders (order_id,user_id,user_name,email,phone,status,tracking_no,item_summary,total_amount,created_at,address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (order_id, user_id, name, email, phone, status, tracking_no, item_summary, total_amount, created_at, address))

con.commit()
con.close()

print("orders.db 已创建并初始化完成，并插入 20 条随机订单数据！")
