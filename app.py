from flask import Flask, render_template, request, redirect, session,flash,jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "farmconnect"

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # USERS TABLE (phone + location added)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        password TEXT,
        role TEXT,
        phone TEXT,
        location TEXT
    )
    """)

    # CROPS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS crops(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER,
        quantity INTEGER,
        image TEXT,
        farmer TEXT,
        phone TEXT,
        location TEXT
    )
    """)

    # ORDERS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        crop TEXT,
        price INTEGER,
        image TEXT,
        farmer TEXT,
        quantity INTEGER,
        payment TEXT,
        status TEXT,
        phone TEXT,
        location TEXT,
        order_status TEXT DEFAULT 'Pending'

    )
    """)

    conn.commit()
    conn.close()
init_db()

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        # NEW fields
        phone = request.form.get("phone")
        location = request.form.get("location")

        conn = sqlite3.connect("farmer.db")
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()

        if user:
            conn.close()
            return "User already exists!"

        cur.execute("""
        INSERT INTO users(name,email,password,role,phone,location)
        VALUES(?,?,?,?,?,?)
        """, (name,email,password,role,phone,location))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

# ---------------- API FOR REGISTER ----------------
@app.route("/api/register", methods=["POST"])
def api_register():

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")
    phone = data.get("phone")
    location = data.get("location")

    if not name or not email or not password or not role:
        return jsonify({"status": "error", "message": "Missing fields"})

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email=?", (email,))
    if cur.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "User exists"})

    cur.execute("""
        INSERT INTO users(name,email,password,role,phone,location)
        VALUES(?,?,?,?,?,?)
    """, (name,email,password,role,phone,location))

    conn.commit()
    conn.close()

    return jsonify({"status": "success"})
# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("farmer.db")
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email,password)
        )

        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = user[1]
            session["role"] = user[4]
            return redirect("/market")

        return "Invalid Email or Password"

    return render_template("login.html")

# ---------------- LOGIN API ----------------
@app.route("/api/login", methods=["POST"])
def api_login():

    data = request.get_json()

    print("DATA RECEIVED:", data)

    if not data:
        return jsonify({"status": "error", "message": "No JSON received"})

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"status": "error", "message": "Missing fields"})

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, role 
        FROM users 
        WHERE email=? AND password=?
    """, (email, password))

    user = cur.fetchone()
    conn.close()

    if user:
        return jsonify({
            "status": "success",
            "id": user[0],
            "name": user[1],
            "role": user[2]
        })

    return jsonify({"status": "error", "message": "Invalid login"})
# ---------------- LOGOUT ----------------
from flask import flash   # make sure this is imported

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")   # 🔥 go to HOME page

# ---------------- ADD CROP ----------------
@app.route("/add_crop", methods=["GET","POST"])
def add_crop():

    if "user" not in session:
        return redirect("/login")

    if session["role"] != "farmer":
        return "Only farmers can add crops"

    if request.method == "POST":

        name = request.form["name"]
        price = request.form["price"]
        quantity = request.form["quantity"]

        image = request.files["image"]

        if image and image.filename != "":
            filename = image.filename
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        else:
            filename = ""

        conn = sqlite3.connect("farmer.db")
        cur = conn.cursor()

        # 🔥 GET farmer details automatically
        cur.execute("SELECT phone, location FROM users WHERE name=?", (session["user"],))
        user_data = cur.fetchone()

        phone = user_data[0] if user_data else ""
        location = user_data[1] if user_data else ""

        cur.execute("""
        INSERT INTO crops(name,price,quantity,image,farmer,phone,location)
        VALUES(?,?,?,?,?,?,?)
        """, (name,price,quantity,filename,session["user"],phone,location))

        conn.commit()
        conn.close()

        return redirect("/market")

    return render_template("add_crop.html")

# ---------------- API FOR ADD CROP ----------------
@app.route("/api/add_crop", methods=["POST"])
def api_add_crop():
    name = request.form.get("name")
    price = request.form.get("price")
    quantity = request.form.get("quantity")
    farmer = request.form.get("farmer")

    image_file = request.files.get("image")

    filename = ""

    if image_file:
        filename = image_file.filename
        image_path = os.path.join("static/uploads", filename)
        image_file.save(image_path)

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # 🔥 SAME LOGIC AS WEB (AUTO FETCH USER DETAILS)
    cur.execute("SELECT phone, location FROM users WHERE name=?", (farmer,))
    user_data = cur.fetchone()

    phone = user_data[0] if user_data else ""
    location = user_data[1] if user_data else ""

    cur.execute("""
        INSERT INTO crops (name, price, quantity, farmer, phone, location, image)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, price, quantity, farmer, phone, location, filename))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Crop added successfully 🌾"
    })
# ---------------- MARKET ----------------
@app.route("/market")
def market():

    if "user" not in session:
        return redirect("/login")

    search = request.args.get("search")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # 👇 DIFFERENT VIEW BASED ON ROLE
    if session.get("role") == "farmer":

        # 👨‍🌾 Farmer → only his crops
        if search:
            cur.execute("""
                SELECT * FROM crops 
                WHERE farmer=? AND name LIKE ?
            """, (session["user"], '%' + search + '%'))
        else:
            cur.execute("""
                SELECT * FROM crops 
                WHERE farmer=?
            """, (session["user"],))

    else:
        # 🧑 Customer → all crops
        if search:
            cur.execute("""
                SELECT * FROM crops 
                WHERE name LIKE ?
            """, ('%' + search + '%',))
        else:
            cur.execute("SELECT * FROM crops")

    crops = cur.fetchall()
    conn.close()

    return render_template("market.html", crops=crops)
#-------------------uploads route----------------
from flask import send_from_directory
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)
#---------------- API FOR MARKET ----------------
@app.route('/api/market', methods=['POST'])
def api_market():
    from flask import request, jsonify, url_for
    import sqlite3

    data = request.get_json(silent=True) or {}

    role = data.get("role", "customer")
    username = data.get("username", "")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # ✅ ROLE BASED DATA
    if role == "farmer":
        cur.execute("""
            SELECT id, name, price, quantity, image, farmer, phone, location
            FROM crops
            WHERE farmer=?
        """, (username,))
    else:
        cur.execute("""
            SELECT id, name, price, quantity, image, farmer, phone, location
            FROM crops
        """)

    rows = cur.fetchall()
    conn.close()

    crops = []

    for row in rows:
        image_file = row[4]

        if image_file:
            image_url = f"http://10.0.2.2:5000/static/uploads/{image_file}"
        else:
            image_url = ""

        crops.append({
            "id": row[0],
            "name": row[1],
            "price": row[2],
            "quantity": row[3],
            "image": image_url,
            "farmer": row[5],
            "phone": row[6],
            "location": row[7],
        })

    return jsonify({"crops": crops})
# ---------------- BUY ----------------

@app.route("/buy/<int:id>", methods=["POST"])
def buy(id):

    if "user" not in session:
        return redirect("/login")

    # 🔒 Only customers can buy
    if session.get("role") != "customer":
        return redirect("/market")

    qty_to_buy = int(request.form["qty"])

    conn = sqlite3.connect("farmer.db", timeout=10)
    cur = conn.cursor()

    try:
        # 🔍 Get crop details
        cur.execute("SELECT name,price,quantity,image,farmer FROM crops WHERE id=?", (id,))
        crop = cur.fetchone()

        if not crop:
            return "❌ Crop not found"

        name, price, available_qty, image, farmer = crop

        if available_qty < qty_to_buy:
            return "❌ Not enough stock"

        # 🔽 Reduce stock
        new_qty = available_qty - qty_to_buy
        cur.execute("UPDATE crops SET quantity=? WHERE id=?", (new_qty, id))

        # 🔍 Get customer phone & location
        cur.execute("SELECT phone, location FROM users WHERE name=?", (session["user"],))
        user_data = cur.fetchone()

        phone = user_data[0] if user_data else ""
        location = user_data[1] if user_data else ""

        # 🔍 Check existing cart order
        cur.execute("""
            SELECT quantity FROM orders 
            WHERE user=? AND crop=? AND farmer=? AND status='cart'
        """, (session["user"], name, farmer))

        existing = cur.fetchone()

        if existing:
            # ✅ Update existing cart item
            updated_qty = existing[0] + qty_to_buy

            cur.execute("""
                UPDATE orders 
                SET quantity=? 
                WHERE user=? AND crop=? AND farmer=? AND status='cart'
            """, (updated_qty, session["user"], name, farmer))

        else:
            # ✅ Insert new cart item (UPDATED VERSION 🔥)
            cur.execute("""
                INSERT INTO orders(user,crop,price,image,quantity,payment,farmer,status,phone,location,order_status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """, (
                session["user"],
                name,
                price,
                image,
                qty_to_buy,
                "Cash on Delivery",
                farmer,
                "cart",
                phone,
                location,
                "Pending"   # 🔥 IMPORTANT FIX
            ))

        conn.commit()

    except sqlite3.OperationalError:
        return "⚠️ Try again (database busy)"

    finally:
        conn.close()

    return redirect("/orders")

# ---------------- API FOR BUY ----------------

@app.route("/api/buy", methods=["POST"])
def api_buy():
    data = request.get_json()

    crop_id = data.get("id")
    qty = int(data.get("qty", 0))
    user = data.get("user")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # 🔍 Get crop details
    cur.execute("SELECT name,price,quantity,image,farmer FROM crops WHERE id=?", (crop_id,))
    crop = cur.fetchone()

    if not crop:
        return jsonify({"status": "error", "message": "Crop not found"})

    name, price, available, image, farmer = crop

    if available < qty:
        return jsonify({"status": "error", "message": "Not enough stock"})

    # 🔽 reduce stock
    cur.execute("UPDATE crops SET quantity=? WHERE id=?", (available - qty, crop_id))

    # 🔍 GET USER PHONE + LOCATION 🔥🔥🔥
    cur.execute("SELECT phone, location FROM users WHERE name=?", (user,))
    user_data = cur.fetchone()

    phone = user_data[0] if user_data else ""
    location = user_data[1] if user_data else ""

    # 🔍 check existing cart
    cur.execute("""
        SELECT quantity FROM orders 
        WHERE user=? AND crop=? AND farmer=? AND status='cart'
    """, (user, name, farmer))

    existing = cur.fetchone()

    if existing:
        new_qty = existing[0] + qty
        cur.execute("""
            UPDATE orders SET quantity=? 
            WHERE user=? AND crop=? AND farmer=? AND status='cart'
        """, (new_qty, user, name, farmer))
    else:
        # ✅ FIXED INSERT
        cur.execute("""
            INSERT INTO orders(user,crop,price,image,quantity,payment,farmer,status,phone,location,order_status)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """, (
            user, name, price, image, qty,
            "Cash on Delivery", farmer,
            "cart",
            phone, location,   # 🔥 FIX HERE
            "Pending"
        ))

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Added to cart"})
# ---------------- API FOR GET CART ----------------

@app.route("/api/cart", methods=["POST"])
def get_cart():
    data = request.get_json()
    user = data.get("user")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT id, crop, price, quantity, image, farmer 
        FROM orders 
        WHERE user=? AND status='cart'
    """, (user,))

    rows = cur.fetchall()
    conn.close()

    cart = []

    for r in rows:
        cart.append({
            "id": r[0],
            "crop": r[1],   # ✅ FORCE SAME KEY
            "price": float(r[2]),
            "quantity": float(r[3]),
            "image": r[4] if r[4] else "",
            "farmer": r[5],
        })

    return jsonify({"cart": cart})
# ---------------- ORDERS ----------------
@app.route("/orders")
def orders():

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # ✅ ONLY CART ITEMS
    cur.execute("""
        SELECT crop,price,image,quantity,payment,phone,location,order_status
        FROM orders
        WHERE user=? AND status='cart'
    """, (session["user"],))

    orders = cur.fetchall()
    conn.close()

    total = 0
    order_list = []

    for order in orders:
        crop, price, image, qty, payment, phone, location, order_status = order

        subtotal = price * qty
        total += subtotal

        # ✅ keep all data (no feature loss)
        order_list.append((crop, price, image, qty, subtotal, payment, phone, location, order_status))

    return render_template("orders.html", orders=order_list, total=total)

# ---------------- API FOR ORDERS ----------------
@app.route("/api/orders", methods=["POST"])
def api_orders():
    data = request.get_json()
    user = data.get("user")

    if not user:
        return jsonify({"status": "error", "message": "User required"})

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT crop, price, quantity, payment, phone, location, order_status
        FROM orders
        WHERE user=? AND status='cart'
    """, (user,))

    rows = cur.fetchall()
    conn.close()

    result = []

    for o in rows:
        result.append({
            "crop": o[0],
            "price": o[1],
            "quantity": o[2],
            "payment": o[3],
            "phone": o[4],
            "location": o[5],
            "status": o[6]
        })

    return jsonify({"orders": result})

#---------------- api  MY ORDERS ----------------
@app.route("/api/my_orders", methods=["POST"])
def api_my_orders():
    data = request.get_json()
    user = data.get("user")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT crop, price, quantity, payment, phone, location, order_status, image
        FROM orders
        WHERE user=? AND status='placed'
    """, (user,))

    rows = cur.fetchall()
    conn.close()

    orders = []

    for r in rows:
        orders.append({
            "crop": r[0],        # ✅ FIXED
            "price": r[1],
            "quantity": r[2],
            "payment": r[3],
            "phone": r[4],
            "location": r[5],
            "status": r[6],      # ✅ FIXED
            "image": r[7]        # ✅ FIXED
        })

    return jsonify({"orders": orders})
#----------------- MY ORDERS (FARMER) ----------------
@app.route("/my_orders")
def my_orders():

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # ✅ ONLY PLACED ORDERS
    cur.execute("""
        SELECT crop,price,image,quantity,payment,phone,location,order_status
        FROM orders
        WHERE user=? AND status='placed'
    """, (session["user"],))

    orders = cur.fetchall()
    conn.close()

    total = 0
    order_list = []

    for order in orders:
        crop, price, image, qty, payment, phone, location, status = order

        subtotal = price * qty
        total += subtotal

        order_list.append((crop, price, image, qty, subtotal, payment, phone, location, status))

    return render_template("my_orders.html", orders=order_list, total=total)

# ---------------- API FOR FARMER ORDERS ----------------
@app.route("/api/farmer_orders", methods=["POST"])
def api_farmer_orders():
    data = request.get_json()
    farmer = data.get("farmer")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT user, crop, quantity, price, payment, image, phone, location, order_status
        FROM orders
        WHERE farmer=? AND status='placed'
    """, (farmer,))

    rows = cur.fetchall()
    conn.close()

    orders = []

    for r in rows:
        orders.append({
            "user": r[0],
            "crop": r[1],
            "quantity": r[2],
            "price": r[3],
            "payment": r[4],
            "image": r[5],
            "phone": r[6],
            "location": r[7],
            "status": r[8]
        })

    return jsonify({"orders": orders})

# ---------------- UPDATE ORDER STATUS ----------------
@app.route("/api/update_status", methods=["POST"])
def api_update_status():
    data = request.get_json()
    crop = data.get("crop")
    status = data.get("status")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    cur.execute("""
        UPDATE orders
        SET order_status=?
        WHERE crop=? AND status='placed'
    """, (status, crop))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Status updated ✅"
    })
#---------dashboard----------
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    if session["role"] != "farmer":
        return "Access denied"

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # 🌱 Get all crops of this farmer
    cur.execute("""
        SELECT name, quantity, price 
        FROM crops 
        WHERE farmer=?
    """, (session["user"],))

    crops = cur.fetchall()

    total_crops = len(crops)   # ✅ FIX ADDED

    crop_data = []
    total_revenue = 0

    for crop in crops:
        name, available_qty, price = crop

        cur.execute("""
            SELECT SUM(quantity) 
            FROM orders 
            WHERE crop=? AND farmer=?
        """, (name, session["user"]))

        sold_qty = cur.fetchone()[0] or 0
        revenue = sold_qty * price

        total_revenue += revenue

        crop_data.append((name, available_qty, sold_qty, revenue))

    conn.close()

    return render_template("dashboard.html",
                           crop_data=crop_data,
                           total_revenue=total_revenue,
                           total_crops=total_crops)   # ✅ PASS TO HTML

conn = sqlite3.connect("farmer.db")
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE orders ADD COLUMN phone TEXT")
    print("phone added")
except:
    print("phone already exists")

try:
    cur.execute("ALTER TABLE orders ADD COLUMN location TEXT")
    print("location added")
except:
    print("location already exists")

conn.commit()
conn.close()

#---------------- API FOR DASHBOARD ----------------

@app.route("/api/farmer_dashboard", methods=["POST"])
def farmer_dashboard():
    data = request.get_json()
    farmer = data.get("farmer")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # total crops
    cur.execute("SELECT COUNT(*) FROM crops WHERE farmer=?", (farmer,))
    total_crops = cur.fetchone()[0]

    # crop wise data (available)
    cur.execute("""
        SELECT name, quantity FROM crops WHERE farmer=?
    """, (farmer,))
    crops = cur.fetchall()

    # sold + revenue
    cur.execute("""
        SELECT crop, SUM(quantity), SUM(price * quantity)
        FROM orders
        WHERE farmer=? AND status='placed'
        GROUP BY crop
    """, (farmer,))
    orders = cur.fetchall()

    # map for sold data
    sold_map = {}
    for o in orders:
        sold_map[o[0]] = {
            "sold": o[1],
            "revenue": o[2]
        }

    crop_stats = []
    total_revenue = 0

    for c in crops:
        name = c[0]
        available = c[1]

        sold = sold_map.get(name, {}).get("sold", 0)
        revenue = sold_map.get(name, {}).get("revenue", 0)

        total_revenue += revenue

        crop_stats.append({
            "crop": name,
            "available": available,
            "sold": sold,
            "revenue": revenue
        })

    conn.close()

    return jsonify({
        "total_crops": total_crops,
        "total_revenue": total_revenue,
        "crop_stats": crop_stats
    })

#---------------- UPDATE ORDER STATUS ----------------
@app.route("/update_status/<crop>/<status>")
def update_status(crop, status):

    if "user" not in session:
        return redirect("/login")

    if session.get("role") != "farmer":
        return "Access denied"

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # 🔁 Update order status
    cur.execute("""
        UPDATE orders
        SET order_status=?
        WHERE crop=? AND farmer=? AND status='placed'
    """, (status, crop, session["user"]))

    conn.commit()
    conn.close()

    return redirect("/farmer_orders")
#---------------place order----------------
@app.route("/place_order", methods=["POST"])
def place_order():

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    cur.execute("""
        UPDATE orders 
        SET status='placed' 
        WHERE user=? AND status='cart'
    """, (session["user"],))

    conn.commit()
    conn.close()

    # ✅ CORRECT PLACE
    flash("✅ Order placed successfully!")

    return redirect("/orders")
# ---------------- API FOR PLACE ORDER ----------------
@app.route("/api/place_order", methods=["POST"])
def api_place_order():
    data = request.get_json()
    user = data.get("user")

    if not user:
        return jsonify({
            "status": "error",
            "message": "User required"
        })

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # 🔁 move cart → placed + set farmer + status
    cur.execute("""
        UPDATE orders
        SET 
            status='placed',
            order_status='Pending',
            farmer = (
                SELECT farmer FROM crops 
                WHERE crops.name = orders.crop
            )
        WHERE user=? AND status='cart'
    """, (user,))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Order placed successfully ✅"
    })
#--------------farmers orders----------------
@app.route("/farmer_orders")
def farmer_orders():

    if "user" not in session:
        return redirect("/login")

    if session.get("role") != "farmer":
        return "Access denied"

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    cur.execute("""
       SELECT user, crop, quantity, price, payment, image, phone , location, order_status
       FROM orders
       WHERE farmer=? AND status='placed'
    """, (session["user"],))

    orders = cur.fetchall()

    conn.close()

    # ✅ ONLY SHOW PAGE (NO FLASH, NO REDIRECT)
    return render_template("farmer_orders.html", orders=orders)

# ---------------- API FOR UPDATE ORDER STATUS ----------------
@app.route("/api/update_order_status", methods=["POST"])
def update_order_status():
    data = request.get_json()

    order_id = data.get("order_id")
    status = data.get("status")

    if not order_id or not status:
        return jsonify({
            "status": "error",
            "message": "Missing data"
        })

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    cur.execute("""
        UPDATE orders
        SET order_status=?
        WHERE id=?
    """, (status, order_id))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Order status updated ✅"
    })

# ---------------- UPDATE ----------------
@app.route("/update/<int:id>", methods=["GET","POST"])
def update(id):

    if "user" not in session:
        return redirect("/login")

    if session.get("role") != "farmer":
        return "❌ Only farmers can update crops"

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # 🔒 Check ownership
    cur.execute("SELECT farmer FROM crops WHERE id=?", (id,))
    owner = cur.fetchone()

    if not owner:
        conn.close()
        return "❌ Crop not found"

    if owner[0] != session["user"]:
        conn.close()
        return "❌ Not allowed"

    # 🔄 UPDATE LOGIC
    if request.method == "POST":
        price = request.form["price"]
        quantity = request.form["quantity"]

        cur.execute(
            "UPDATE crops SET price=?, quantity=? WHERE id=?",
            (price, quantity, id)
        )

        conn.commit()
        conn.close()

        return redirect("/market")

    # 📦 GET crop data for form
    cur.execute("SELECT * FROM crops WHERE id=?", (id,))
    crop = cur.fetchone()

    conn.close()

    return render_template("update_crop.html", crop=crop)
# ---------------- API FOR UPDATE ----------------
@app.route('/api/update_crop', methods=['POST'])
def api_update_crop():
    data = request.json

    crop_id = data.get("crop_id")
    user = data.get("user")
    name = data.get("name")
    price = data.get("price")
    quantity = data.get("quantity")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    cur.execute("SELECT farmer FROM crops WHERE id=?", (crop_id,))
    owner = cur.fetchone()

    if owner and owner[0] == user:
        cur.execute(
            "UPDATE crops SET name=?, price=?, quantity=? WHERE id=?",
            (name, price, quantity, crop_id)
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    else:
        conn.close()
        return jsonify({"status": "error", "message": "Not allowed"})
# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    cur.execute("SELECT farmer FROM crops WHERE id=?", (id,))
    owner = cur.fetchone()

    if owner[0] != session["user"]:
        conn.close()
        return "❌ Not allowed"

    cur.execute("DELETE FROM crops WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/market")

# ---------------- API FOR DELETE CROP ----------------
@app.route("/api/delete_crop", methods=["POST"])
def api_delete_crop():
    data = request.get_json()
    crop_id = data.get("id")

    if not crop_id:
        return jsonify({
            "status": "error",
            "message": "Crop ID required"
        })

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # check if crop exists
    cur.execute("SELECT * FROM crops WHERE id=?", (crop_id,))
    crop = cur.fetchone()

    if not crop:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Crop not found"
        })

    # delete crop
    cur.execute("DELETE FROM crops WHERE id=?", (crop_id,))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Crop deleted successfully 🗑"
    })
# ---------------- CANCEL ORDER ----------------
@app.route("/cancel_order/<crop>")
def cancel_order(crop):

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # Get order details
    cur.execute("""
        SELECT quantity FROM orders 
        WHERE user=? AND crop=?
    """, (session["user"], crop))

    order = cur.fetchone()

    if order:
        qty = order[0]

        # Restore crop quantity
        cur.execute("""
            UPDATE crops 
            SET quantity = quantity + ? 
            WHERE name=?
        """, (qty, crop))

        # Delete order
        cur.execute("""
            DELETE FROM orders 
            WHERE user=? AND crop=?
        """, (session["user"], crop))

        conn.commit()

    conn.close()

    return redirect("/orders")
# ---------------- API FOR CANCEL ORDER ----------------
@app.route("/api/cancel_order", methods=["POST"])
def api_cancel_order():
    data = request.get_json()
    user = data.get("user")
    crop = data.get("crop")

    conn = sqlite3.connect("farmer.db")
    cur = conn.cursor()

    # get quantity
    cur.execute("""
        SELECT quantity FROM orders 
        WHERE user=? AND crop=? AND status='cart'
    """, (user, crop))

    order = cur.fetchone()

    if order:
        qty = order[0]

        # restore stock
        cur.execute("""
            UPDATE crops 
            SET quantity = quantity + ? 
            WHERE name=?
        """, (qty, crop))

        # delete order
        cur.execute("""
            DELETE FROM orders 
            WHERE user=? AND crop=? AND status='cart'
        """, (user, crop))

        conn.commit()

    conn.close()

    return jsonify({
        "status": "success",
        "message": "Order cancelled ❌"
    })
#home page
@app.route("/")
def home():
    return render_template("index.html")

#new api
@app.route("/api/test")
def test_api():
    return jsonify({"message": "API working"})




# ---------------- RUN ----------------
import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)   