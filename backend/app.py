"""
Zaykaveda - backend API (Flask + SQLite)
Free to run on PythonAnywhere / Render free tier.

Environment variables (set these on your host, never commit real values):
  ADMIN_PASSWORD   password for the admin panel        (default: change-me-now)
  UPI_ID           owner's UPI id, e.g. arish@okhdfcbank (default: yourname@upi)
  UPI_NAME         name shown in the UPI app           (default: Zaykaveda)
  WHATSAPP_NUMBER  digits only, with country code      (default: 919669219030)
  ALLOWED_ORIGIN   your GitHub Pages URL, e.g. https://zaykaveda.github.io
  DB_PATH          sqlite file path                    (default: zaykaveda.db)
"""
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "zaykaveda.db"))
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGIN}})


# ----------------------------------------------------------------- database
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


SCHEMA = """
CREATE TABLE IF NOT EXISTS dishes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  cuisine TEXT NOT NULL,            -- Indian | Chinese
  category TEXT NOT NULL,           -- Starters, Main Course, ...
  is_veg INTEGER NOT NULL DEFAULT 1,
  spice INTEGER NOT NULL DEFAULT 1, -- 0..3
  price REAL NOT NULL,
  description TEXT DEFAULT '',
  emoji TEXT DEFAULT '🍽️',
  available INTEGER NOT NULL DEFAULT 1,
  featured INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  address TEXT DEFAULT '',
  note TEXT DEFAULT '',
  total REAL NOT NULL,
  -- payment_status: unpaid | submitted | approved | denied
  payment_status TEXT NOT NULL DEFAULT 'unpaid',
  -- order_status: placed | confirmed | preparing | completed | cancelled
  order_status TEXT NOT NULL DEFAULT 'placed',
  utr TEXT DEFAULT '',
  created_at TEXT NOT NULL,
  paid_at TEXT
);
CREATE TABLE IF NOT EXISTS order_items(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  dish_id INTEGER,
  name TEXT NOT NULL,
  price REAL NOT NULL,
  qty INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT DEFAULT '',
  phone TEXT DEFAULT '',
  message TEXT NOT NULL,
  is_read INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS staff(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  phone TEXT DEFAULT '',
  salary_type TEXT NOT NULL DEFAULT 'monthly', -- monthly | daily
  rate REAL NOT NULL DEFAULT 0,
  joined_on TEXT DEFAULT '',
  active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS sessions(
  token TEXT PRIMARY KEY,
  expires REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

# (name, cuisine, category, veg, spice, price, description, emoji, featured)
SEED = [
    # ---- Indian
    ("Paneer Tikka", "Indian", "Starters", 1, 2, 249, "Char-grilled cottage cheese marinated in yoghurt and spices.", "🧀", 1),
    ("Hara Bhara Kebab", "Indian", "Starters", 1, 1, 199, "Spinach, peas and potato patties, pan-seared.", "🥬", 0),
    ("Veg Samosa (2 pcs)", "Indian", "Starters", 1, 1, 60, "Crisp pastry with spiced potato and peas.", "🥟", 0),
    ("Chicken Tikka", "Indian", "Starters", 0, 2, 299, "Tandoor-roasted chicken, smoky and juicy.", "🍗", 0),
    ("Tandoori Chicken (Half)", "Indian", "Starters", 0, 2, 329, "Classic bone-in chicken from the clay oven.", "🍗", 0),
    ("Seekh Kebab", "Indian", "Starters", 0, 2, 319, "Minced mutton kebabs with herbs.", "🍢", 0),
    ("Dal Makhani", "Indian", "Main Course", 1, 1, 229, "Slow-cooked black lentils finished with cream and butter.", "🍲", 1),
    ("Paneer Butter Masala", "Indian", "Main Course", 1, 1, 269, "Cottage cheese in a silky tomato-butter gravy.", "🍛", 1),
    ("Kadai Paneer", "Indian", "Main Course", 1, 2, 269, "Paneer with bell peppers in roasted kadai masala.", "🍛", 0),
    ("Palak Paneer", "Indian", "Main Course", 1, 1, 249, "Paneer in smooth spinach gravy.", "🥬", 0),
    ("Chole Masala", "Indian", "Main Course", 1, 2, 199, "Punjabi chickpea curry with tangy spices.", "🫘", 0),
    ("Mix Veg Curry", "Indian", "Main Course", 1, 1, 209, "Seasonal vegetables in a home-style gravy.", "🥕", 0),
    ("Butter Chicken", "Indian", "Main Course", 0, 1, 349, "Tandoori chicken in rich tomato-cream sauce.", "🍗", 1),
    ("Chicken Curry", "Indian", "Main Course", 0, 2, 319, "Home-style chicken curry with whole spices.", "🍛", 0),
    ("Mutton Rogan Josh", "Indian", "Main Course", 0, 2, 429, "Kashmiri-style slow-braised mutton.", "🍖", 0),
    ("Egg Curry", "Indian", "Main Course", 0, 2, 189, "Boiled eggs in spicy onion-tomato gravy.", "🥚", 0),
    ("Veg Biryani", "Indian", "Rice & Biryani", 1, 2, 249, "Fragrant basmati layered with vegetables and saffron.", "🍚", 0),
    ("Chicken Biryani", "Indian", "Rice & Biryani", 0, 2, 329, "Dum-cooked biryani with tender chicken.", "🍚", 1),
    ("Mutton Biryani", "Indian", "Rice & Biryani", 0, 2, 429, "Slow dum biryani with succulent mutton.", "🍚", 0),
    ("Jeera Rice", "Indian", "Rice & Biryani", 1, 0, 129, "Basmati tempered with cumin.", "🍚", 0),
    ("Steamed Rice", "Indian", "Rice & Biryani", 1, 0, 99, "Plain basmati rice.", "🍚", 0),
    ("Butter Naan", "Indian", "Breads", 1, 0, 49, "Soft tandoor naan brushed with butter.", "🫓", 0),
    ("Garlic Naan", "Indian", "Breads", 1, 0, 59, "Naan topped with garlic and coriander.", "🫓", 0),
    ("Tandoori Roti", "Indian", "Breads", 1, 0, 25, "Whole wheat roti from the tandoor.", "🫓", 0),
    ("Lachha Paratha", "Indian", "Breads", 1, 0, 49, "Flaky layered paratha.", "🫓", 0),
    ("Masala Dosa", "Indian", "South Indian", 1, 1, 149, "Crisp dosa with spiced potato filling, sambar and chutneys.", "🥞", 0),
    ("Idli Sambar (3 pcs)", "Indian", "South Indian", 1, 0, 99, "Steamed rice cakes with sambar.", "🍥", 0),
    ("Pav Bhaji", "Indian", "Street Food", 1, 2, 159, "Mumbai-style mashed vegetable curry with buttered pav.", "🍞", 0),
    ("Pani Puri (6 pcs)", "Indian", "Street Food", 1, 2, 70, "Crisp puris with spicy mint water.", "🥣", 0),
    ("Dahi Bhalla Chaat", "Indian", "Street Food", 1, 1, 119, "Lentil dumplings in yoghurt with chutneys.", "🥣", 0),
    ("Veg Thali", "Indian", "Thali", 1, 1, 249, "Dal, 2 sabzis, rice, roti, salad, raita, sweet.", "🍱", 1),
    ("Non-Veg Thali", "Indian", "Thali", 0, 1, 349, "Chicken curry, dal, rice, roti, salad, raita, sweet.", "🍱", 0),
    ("Boondi Raita", "Indian", "Sides", 1, 0, 79, "Chilled yoghurt with crisp boondi.", "🥛", 0),
    ("Masala Papad", "Indian", "Sides", 1, 1, 59, "Roasted papad with onion-tomato topping.", "🫓", 0),
    ("Gulab Jamun (2 pcs)", "Indian", "Desserts", 1, 0, 89, "Warm milk dumplings in saffron syrup.", "🍮", 0),
    ("Rasmalai (2 pcs)", "Indian", "Desserts", 1, 0, 119, "Soft cheese discs in chilled cardamom milk.", "🍮", 0),
    ("Gajar Halwa", "Indian", "Desserts", 1, 0, 109, "Slow-cooked carrot pudding with nuts.", "🥕", 0),
    ("Masala Chai", "Indian", "Beverages", 1, 0, 40, "Spiced Indian tea.", "🍵", 0),
    ("Sweet Lassi", "Indian", "Beverages", 1, 0, 89, "Thick, chilled yoghurt drink.", "🥛", 0),
    ("Fresh Lime Soda", "Indian", "Beverages", 1, 0, 69, "Sweet, salted or mixed.", "🍋", 0),
    # ---- Chinese (as eaten in India)
    ("Veg Manchurian (Dry)", "Chinese", "Starters", 1, 2, 189, "Crisp vegetable balls tossed in Manchurian sauce.", "🥡", 1),
    ("Gobi Manchurian", "Chinese", "Starters", 1, 2, 179, "Fried cauliflower in tangy-spicy sauce.", "🥦", 0),
    ("Chilli Paneer (Dry)", "Chinese", "Starters", 1, 3, 229, "Paneer with capsicum and green chillies.", "🌶️", 1),
    ("Veg Spring Roll (4 pcs)", "Chinese", "Starters", 1, 1, 159, "Crunchy rolls stuffed with cabbage and carrot.", "🥟", 0),
    ("Crispy Corn", "Chinese", "Starters", 1, 1, 169, "Golden corn tossed with pepper and spring onion.", "🌽", 0),
    ("Honey Chilli Potato", "Chinese", "Starters", 1, 2, 179, "Crispy fries glazed in honey-chilli sauce.", "🍟", 0),
    ("Chilli Chicken (Dry)", "Chinese", "Starters", 0, 3, 259, "Crispy chicken with peppers in chilli sauce.", "🌶️", 1),
    ("Chicken Lollipop (6 pcs)", "Chinese", "Starters", 0, 2, 279, "Frenched wings, fried and tossed in Schezwan glaze.", "🍗", 0),
    ("Chicken 65", "Chinese", "Starters", 0, 3, 259, "Spicy, curry-leaf fried chicken.", "🍗", 0),
    ("Veg Hakka Noodles", "Chinese", "Noodles", 1, 1, 179, "Wok-tossed noodles with crunchy vegetables.", "🍜", 1),
    ("Schezwan Noodles", "Chinese", "Noodles", 1, 3, 199, "Fiery noodles in Schezwan sauce.", "🍜", 0),
    ("Chicken Hakka Noodles", "Chinese", "Noodles", 0, 1, 219, "Hakka noodles with shredded chicken and egg.", "🍜", 0),
    ("Singapore Noodles", "Chinese", "Noodles", 1, 2, 209, "Thin rice noodles with curry flavour.", "🍜", 0),
    ("Veg Fried Rice", "Chinese", "Rice", 1, 1, 169, "Wok-fried rice with fresh vegetables.", "🍚", 0),
    ("Egg Fried Rice", "Chinese", "Rice", 0, 1, 189, "Fried rice with scrambled egg.", "🍚", 0),
    ("Chicken Fried Rice", "Chinese", "Rice", 0, 1, 219, "Fried rice with chicken and egg.", "🍚", 0),
    ("Schezwan Fried Rice", "Chinese", "Rice", 1, 3, 189, "Spicy fried rice in Schezwan sauce.", "🍚", 0),
    ("Veg Manchurian Gravy", "Chinese", "Gravy", 1, 2, 209, "Vegetable balls in rich Manchurian gravy.", "🍲", 0),
    ("Chilli Chicken Gravy", "Chinese", "Gravy", 0, 3, 279, "Chicken in spicy soy-chilli gravy.", "🍲", 0),
    ("Paneer in Hot Garlic Sauce", "Chinese", "Gravy", 1, 3, 249, "Paneer in punchy garlic sauce.", "🧄", 0),
    ("Veg Manchow Soup", "Chinese", "Soups", 1, 2, 119, "Spicy soup topped with crispy noodles.", "🥣", 0),
    ("Sweet Corn Chicken Soup", "Chinese", "Soups", 0, 0, 139, "Creamy corn soup with chicken.", "🥣", 0),
    ("Hot & Sour Soup (Veg)", "Chinese", "Soups", 1, 2, 119, "Tangy, peppery classic.", "🥣", 0),
    ("Veg Momos (8 pcs)", "Chinese", "Momos", 1, 1, 129, "Steamed dumplings with red chilli chutney.", "🥟", 1),
    ("Chicken Momos (8 pcs)", "Chinese", "Momos", 0, 1, 159, "Juicy chicken dumplings, steamed or fried.", "🥟", 0),
    ("Paneer Momos (8 pcs)", "Chinese", "Momos", 1, 1, 149, "Spiced paneer-filled dumplings.", "🥟", 0),
    ("Chocolate Brownie with Ice Cream", "Chinese", "Desserts", 1, 0, 169, "Warm brownie with vanilla ice cream.", "🍫", 0),
    ("Honey Noodles with Ice Cream", "Chinese", "Desserts", 1, 0, 149, "Crispy noodles drizzled with honey.", "🍨", 0),
]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    cur = conn.execute("SELECT COUNT(*) FROM dishes")
    if cur.fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO dishes(name,cuisine,category,is_veg,spice,price,description,emoji,featured) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            SEED,
        )
    if conn.execute("SELECT COUNT(*) FROM staff").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO staff(name,role,phone,salary_type,rate,joined_on) VALUES(?,?,?,?,?,?)",
            [
                ("Sample Chef", "Head Chef", "", "monthly", 30000, "2026-01-01"),
                ("Sample Waiter", "Waiter", "", "daily", 600, "2026-01-01"),
            ],
        )
    defaults = {
        "upi_id": os.environ.get("UPI_ID", "yourname@upi"),
        "upi_name": os.environ.get("UPI_NAME", "Zaykaveda"),
        "whatsapp": os.environ.get("WHATSAPP_NUMBER", "919669219030"),
        "owner_name": "Arish Shah",
        "admin_hash": generate_password_hash(os.environ.get("ADMIN_PASSWORD", "change-me-now")),
    }
    for k, v in defaults.items():
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
    conn.commit()
    conn.close()


def setting(key):
    row = db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else ""


# --------------------------------------------------------------------- auth
def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else ""
        row = db().execute("SELECT expires FROM sessions WHERE token=?", (token,)).fetchone()
        if not row or row["expires"] < time.time():
            return jsonify(error="Unauthorized"), 401
        return fn(*a, **kw)

    return wrapper


_attempts = {}


@app.post("/api/admin/login")
def admin_login():
    ip = request.remote_addr or "x"
    tries = [t for t in _attempts.get(ip, []) if t > time.time() - 600]
    if len(tries) >= 8:
        return jsonify(error="Too many attempts. Try again in 10 minutes."), 429
    pw = (request.get_json(silent=True) or {}).get("password", "")
    if not check_password_hash(setting("admin_hash"), pw):
        tries.append(time.time())
        _attempts[ip] = tries
        return jsonify(error="Wrong password"), 401
    token = secrets.token_urlsafe(32)
    db().execute("INSERT INTO sessions(token,expires) VALUES(?,?)", (token, time.time() + 12 * 3600))
    db().execute("DELETE FROM sessions WHERE expires < ?", (time.time(),))
    db().commit()
    return jsonify(token=token)


@app.post("/api/admin/logout")
@admin_required
def admin_logout():
    token = request.headers["Authorization"][7:]
    db().execute("DELETE FROM sessions WHERE token=?", (token,))
    db().commit()
    return jsonify(ok=True)


@app.post("/api/admin/change-password")
@admin_required
def change_password():
    d = request.get_json(silent=True) or {}
    if not check_password_hash(setting("admin_hash"), d.get("current", "")):
        return jsonify(error="Current password is wrong"), 400
    new = d.get("new", "")
    if len(new) < 8:
        return jsonify(error="New password must be at least 8 characters"), 400
    db().execute("UPDATE settings SET value=? WHERE key='admin_hash'", (generate_password_hash(new),))
    db().commit()
    return jsonify(ok=True)


# ------------------------------------------------------------------- public
def rows(cur):
    return [dict(r) for r in cur.fetchall()]


@app.get("/api/health")
def health():
    return jsonify(ok=True)


@app.get("/api/config")
def public_config():
    return jsonify(
        upi_id=setting("upi_id"),
        upi_name=setting("upi_name"),
        whatsapp=setting("whatsapp"),
        owner_name=setting("owner_name"),
    )


@app.get("/api/dishes")
def list_dishes():
    return jsonify(rows(db().execute("SELECT * FROM dishes WHERE available=1 ORDER BY cuisine, category, name")))


@app.post("/api/orders")
def create_order():
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()[:80]
    phone = re.sub(r"\D", "", d.get("phone") or "")[-10:]
    items = d.get("items") or []
    if not name or len(phone) != 10:
        return jsonify(error="Please enter your name and a valid 10-digit phone number."), 400
    if not items or not isinstance(items, list):
        return jsonify(error="Your cart is empty."), 400
    conn = db()
    total, lines = 0.0, []
    for it in items:
        try:
            dish_id, qty = int(it["id"]), int(it["qty"])
        except (KeyError, ValueError, TypeError):
            return jsonify(error="Invalid cart."), 400
        if not 1 <= qty <= 50:
            return jsonify(error="Invalid quantity."), 400
        dish = conn.execute("SELECT * FROM dishes WHERE id=? AND available=1", (dish_id,)).fetchone()
        if not dish:
            return jsonify(error="A dish in your cart is no longer available."), 400
        total += dish["price"] * qty  # price always comes from the database
        lines.append((dish["id"], dish["name"], dish["price"], qty))
    cur = conn.execute(
        "INSERT INTO orders(customer_name,phone,address,note,total,created_at) VALUES(?,?,?,?,?,?)",
        (name, phone, (d.get("address") or "")[:300], (d.get("note") or "")[:300], total, now()),
    )
    oid = cur.lastrowid
    conn.executemany(
        "INSERT INTO order_items(order_id,dish_id,name,price,qty) VALUES(?,?,?,?,?)",
        [(oid, *l) for l in lines],
    )
    conn.commit()
    return jsonify(order_id=oid, total=total)


def order_dict(oid):
    o = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not o:
        return None
    o = dict(o)
    o["items"] = rows(db().execute("SELECT name,price,qty FROM order_items WHERE order_id=?", (oid,)))
    return o


@app.post("/api/orders/<int:oid>/payment")
def submit_payment(oid):
    """Customer says 'I have paid' and gives the UPI reference (UTR) number."""
    d = request.get_json(silent=True) or {}
    utr = re.sub(r"[^A-Za-z0-9]", "", d.get("utr") or "")[:30]
    phone = re.sub(r"\D", "", d.get("phone") or "")[-10:]
    o = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not o or o["phone"] != phone:
        return jsonify(error="Order not found"), 404
    if len(utr) < 6:
        return jsonify(error="Please enter the UPI reference / UTR number (12 digits) from your payment app."), 400
    if o["payment_status"] == "approved":
        return jsonify(error="Payment is already approved."), 400
    db().execute("UPDATE orders SET payment_status='submitted', utr=? WHERE id=?", (utr, oid))
    db().commit()
    return jsonify(ok=True)


@app.get("/api/orders/<int:oid>")
def track_order(oid):
    phone = re.sub(r"\D", "", request.args.get("phone", ""))[-10:]
    o = order_dict(oid)
    if not o or o["phone"] != phone:
        return jsonify(error="Order not found. Check the order number and phone."), 404
    o.pop("note", None)
    return jsonify(o)


@app.post("/api/contact")
def contact():
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()[:80]
    msg = (d.get("message") or "").strip()[:2000]
    if not name or len(msg) < 3:
        return jsonify(error="Please enter your name and a message."), 400
    db().execute(
        "INSERT INTO messages(name,email,phone,message,created_at) VALUES(?,?,?,?,?)",
        (name, (d.get("email") or "")[:120], (d.get("phone") or "")[:20], msg, now()),
    )
    db().commit()
    return jsonify(ok=True)


# -------------------------------------------------------------------- admin
@app.get("/api/admin/orders")
@admin_required
def admin_orders():
    status = request.args.get("payment")
    q = "SELECT * FROM orders"
    args = []
    if status:
        q += " WHERE payment_status=?"
        args.append(status)
    q += " ORDER BY id DESC LIMIT 300"
    out = []
    for o in rows(db().execute(q, args)):
        o["items"] = rows(db().execute("SELECT name,price,qty FROM order_items WHERE order_id=?", (o["id"],)))
        out.append(o)
    return jsonify(out)


@app.post("/api/admin/orders/<int:oid>/approve")
@admin_required
def approve(oid):
    db().execute(
        "UPDATE orders SET payment_status='approved', order_status='confirmed', paid_at=? WHERE id=?",
        (now(), oid),
    )
    db().commit()
    return jsonify(ok=True)


@app.post("/api/admin/orders/<int:oid>/deny")
@admin_required
def deny(oid):
    db().execute(
        "UPDATE orders SET payment_status='denied', order_status='cancelled', paid_at=NULL WHERE id=?",
        (oid,),
    )
    db().commit()
    return jsonify(ok=True)


@app.post("/api/admin/orders/<int:oid>/status")
@admin_required
def set_status(oid):
    s = (request.get_json(silent=True) or {}).get("status")
    if s not in ("confirmed", "preparing", "completed"):
        return jsonify(error="Bad status"), 400
    o = db().execute("SELECT payment_status FROM orders WHERE id=?", (oid,)).fetchone()
    if not o or o["payment_status"] != "approved":
        return jsonify(error="Approve the payment first."), 400
    db().execute("UPDATE orders SET order_status=? WHERE id=?", (s, oid))
    db().commit()
    return jsonify(ok=True)


# dishes
@app.get("/api/admin/dishes")
@admin_required
def admin_dishes():
    return jsonify(rows(db().execute("SELECT * FROM dishes ORDER BY cuisine, category, name")))


def dish_payload(d):
    name = (d.get("name") or "").strip()
    cuisine = d.get("cuisine") if d.get("cuisine") in ("Indian", "Chinese") else None
    try:
        price = float(d.get("price"))
    except (TypeError, ValueError):
        price = -1
    if not name or not cuisine or price < 0:
        return None
    return (
        name[:100], cuisine, (d.get("category") or "Main Course").strip()[:40],
        1 if d.get("is_veg") else 0, max(0, min(3, int(d.get("spice") or 0))), price,
        (d.get("description") or "")[:300], (d.get("emoji") or "🍽️")[:8],
        1 if d.get("available", True) else 0, 1 if d.get("featured") else 0,
    )


@app.post("/api/admin/dishes")
@admin_required
def add_dish():
    p = dish_payload(request.get_json(silent=True) or {})
    if not p:
        return jsonify(error="Name, cuisine and a valid price are required."), 400
    cur = db().execute(
        "INSERT INTO dishes(name,cuisine,category,is_veg,spice,price,description,emoji,available,featured) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)", p)
    db().commit()
    return jsonify(id=cur.lastrowid)


@app.put("/api/admin/dishes/<int:did>")
@admin_required
def edit_dish(did):
    p = dish_payload(request.get_json(silent=True) or {})
    if not p:
        return jsonify(error="Name, cuisine and a valid price are required."), 400
    db().execute(
        "UPDATE dishes SET name=?,cuisine=?,category=?,is_veg=?,spice=?,price=?,description=?,emoji=?,"
        "available=?,featured=? WHERE id=?", (*p, did))
    db().commit()
    return jsonify(ok=True)


@app.delete("/api/admin/dishes/<int:did>")
@admin_required
def del_dish(did):
    db().execute("DELETE FROM dishes WHERE id=?", (did,))
    db().commit()
    return jsonify(ok=True)


# staff
@app.get("/api/admin/staff")
@admin_required
def staff_list():
    return jsonify(rows(db().execute("SELECT * FROM staff ORDER BY active DESC, name")))


def staff_payload(d):
    name = (d.get("name") or "").strip()
    try:
        rate = float(d.get("rate"))
    except (TypeError, ValueError):
        rate = -1
    if not name or rate < 0:
        return None
    st = d.get("salary_type") if d.get("salary_type") in ("monthly", "daily") else "monthly"
    return (name[:80], (d.get("role") or "Staff")[:40], (d.get("phone") or "")[:20], st, rate,
            (d.get("joined_on") or "")[:10], 1 if d.get("active", True) else 0)


@app.post("/api/admin/staff")
@admin_required
def staff_add():
    p = staff_payload(request.get_json(silent=True) or {})
    if not p:
        return jsonify(error="Name and a valid salary rate are required."), 400
    db().execute("INSERT INTO staff(name,role,phone,salary_type,rate,joined_on,active) VALUES(?,?,?,?,?,?,?)", p)
    db().commit()
    return jsonify(ok=True)


@app.put("/api/admin/staff/<int:sid>")
@admin_required
def staff_edit(sid):
    p = staff_payload(request.get_json(silent=True) or {})
    if not p:
        return jsonify(error="Name and a valid salary rate are required."), 400
    db().execute("UPDATE staff SET name=?,role=?,phone=?,salary_type=?,rate=?,joined_on=?,active=? WHERE id=?", (*p, sid))
    db().commit()
    return jsonify(ok=True)


@app.delete("/api/admin/staff/<int:sid>")
@admin_required
def staff_del(sid):
    db().execute("DELETE FROM staff WHERE id=?", (sid,))
    db().commit()
    return jsonify(ok=True)


# messages
@app.get("/api/admin/messages")
@admin_required
def msgs():
    return jsonify(rows(db().execute("SELECT * FROM messages ORDER BY id DESC LIMIT 200")))


@app.post("/api/admin/messages/<int:mid>/read")
@admin_required
def msg_read(mid):
    db().execute("UPDATE messages SET is_read=1 WHERE id=?", (mid,))
    db().commit()
    return jsonify(ok=True)


@app.delete("/api/admin/messages/<int:mid>")
@admin_required
def msg_del(mid):
    db().execute("DELETE FROM messages WHERE id=?", (mid,))
    db().commit()
    return jsonify(ok=True)


# settings
@app.get("/api/admin/settings")
@admin_required
def get_settings():
    return jsonify({k: setting(k) for k in ("upi_id", "upi_name", "whatsapp", "owner_name")})


@app.put("/api/admin/settings")
@admin_required
def put_settings():
    d = request.get_json(silent=True) or {}
    for k in ("upi_id", "upi_name", "whatsapp", "owner_name"):
        if k in d and str(d[k]).strip():
            v = str(d[k]).strip()[:80]
            if k == "whatsapp":
                v = re.sub(r"\D", "", v)
            db().execute("UPDATE settings SET value=? WHERE key=?", (v, k))
    db().commit()
    return jsonify(ok=True)


# stats
@app.get("/api/admin/stats")
@admin_required
def stats():
    days = max(1, min(90, int(request.args.get("days", 14))))
    conn = db()
    today = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    def one(q, *a):
        return conn.execute(q, a).fetchone()[0] or 0

    daily = rows(conn.execute(
        "SELECT substr(paid_at,1,10) AS day, SUM(total) AS income, COUNT(*) AS orders "
        "FROM orders WHERE payment_status='approved' AND substr(paid_at,1,10)>=? GROUP BY day ORDER BY day", (start,)))
    by_day = {r["day"]: r for r in daily}
    series = []
    for i in range(days):
        day = (datetime.now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        r = by_day.get(day)
        series.append({"day": day, "income": r["income"] if r else 0, "orders": r["orders"] if r else 0})

    top = rows(conn.execute(
        "SELECT oi.name, SUM(oi.qty) AS qty FROM order_items oi JOIN orders o ON o.id=oi.order_id "
        "WHERE o.payment_status='approved' GROUP BY oi.name ORDER BY qty DESC LIMIT 5"))
    monthly_payroll = one("SELECT SUM(rate) FROM staff WHERE active=1 AND salary_type='monthly'") + \
        30 * one("SELECT SUM(rate) FROM staff WHERE active=1 AND salary_type='daily'")
    return jsonify(
        today_income=one("SELECT SUM(total) FROM orders WHERE payment_status='approved' AND substr(paid_at,1,10)=?", today),
        today_orders=one("SELECT COUNT(*) FROM orders WHERE payment_status='approved' AND substr(paid_at,1,10)=?", today),
        month_income=one("SELECT SUM(total) FROM orders WHERE payment_status='approved' AND substr(paid_at,1,7)=?", today[:7]),
        total_income=one("SELECT SUM(total) FROM orders WHERE payment_status='approved'"),
        pending_payments=one("SELECT COUNT(*) FROM orders WHERE payment_status='submitted'"),
        unread_messages=one("SELECT COUNT(*) FROM messages WHERE is_read=0"),
        monthly_payroll=monthly_payroll,
        series=series,
        top_dishes=top,
    )


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
