from flask import Flask, render_template, request, redirect, session
import json, os, smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- FILES ----------------
menu_file = "menu.json"
accounts_file = "accounts.json"
orders_file = "orders.json"

# ---------------- SAFE LOAD ----------------
def load(file, default):
    if os.path.exists(file):
        try:
            return json.load(open(file, "r"))
        except:
            return default
    return default

menu = load(menu_file, {})
accounts = load(accounts_file, {
    "admin": {
        "password": "admin123",
        "balance": 1000,
        "role": "admin"
    }
})
orders = load(orders_file, [])

# ---------------- SAVE ----------------
def save():
    json.dump(menu, open(menu_file, "w"))
    json.dump(accounts, open(accounts_file, "w"))
    json.dump(orders, open(orders_file, "w"))

# ---------------- EMAIL ----------------
def send_email(user, items, total):
    try:
        sender = "xavi.chris.make.dcost@gmail.com"
        app_password = "jdcsmtruxkvwhknb"
        receiver = "xavisolis2011@gmail.com"

        body = f"ORDER RECEIPT\n\nUser: {user}\n\nItems:\n" + "\n".join(items) + f"\n\nTotal: ₱{total}"

        msg = MIMEText(body)
        msg["Subject"] = "Canteen Receipt"
        msg["From"] = sender
        msg["To"] = receiver

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, app_password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

    except Exception as e:
        print("Email error:", e)

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        u = request.form["username"].lower()
        p = request.form["password"]

        if u in accounts and accounts[u]["password"] == p:
            session["user"] = u
            return redirect("/admin" if accounts[u]["role"] == "admin" else "/user")
        else:
            error = "Invalid username or password"

    return render_template("login.html", error=error)

# ---------------- USER PAGE ----------------
@app.route("/user")
def user():
    if "user" not in session:
        return redirect("/")

    u = session["user"]

    return render_template(
        "user.html",
        menu=menu,
        balance=accounts[u]["balance"],
        username=u,
        today=datetime.now().strftime("%B %d, %Y"),
        message=session.pop("message", "")
    )

# ---------------- PLACE ORDER (CART SYSTEM FIXED) ----------------
@app.route("/place_order", methods=["POST"])
def place_order():
    if "user" not in session:
        return redirect("/")

    u = session["user"]
    total = 0
    items_list = []

    for cat, items in menu.items():
        for item, price in items.items():

            qty = request.form.get(item)

            try:
                qty = int(qty)
            except:
                qty = 0

            if qty > 0:
                cost = qty * price
                total += cost
                items_list.append(f"{qty}x {item.replace('_',' ').title()} = ₱{cost}")

    # ❌ no items selected
    if total == 0:
        session["message"] = "Please select at least one item."
        return redirect("/user")

    # ❌ not enough balance
    if total > accounts[u]["balance"]:
        session["message"] = "Not enough balance for this order."
        return redirect("/user")

    # ✅ deduct balance
    accounts[u]["balance"] -= total

    # ✅ save order properly
    orders.append({
        "user": u,
        "items": items_list,
        "total": total,
        "date": datetime.now().strftime("%B %d, %Y")
    })

    save()

    send_email(u, items_list, total)

    session["message"] = "Order Confirmed!"

    return redirect("/user")

# ---------------- CHANGE PASSWORD ----------------
@app.route("/change_password", methods=["POST"])
def change_password():
    if "user" in session:
        accounts[session["user"]]["password"] = request.form["password"]
        save()
    return redirect("/user")

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if "user" not in session:
        return redirect("/")

    if accounts[session["user"]]["role"] != "admin":
        return redirect("/")

    search = request.args.get("search", "").lower()

    # FILTER USERS
    filtered_accounts = {}

    for user, data in accounts.items():
        if search == "" or search in user.lower():
            filtered_accounts[user] = data

    return render_template(
        "admin.html",
        accounts=accounts,
        menu=menu,
        orders=orders,
        search=request.args.get("search", ""),
        message=session.pop("message", None)  
    )
# ---------------- USER MANAGEMENT ----------------
@app.route("/manage_user/<username>")
def manage_user(username):
    user_orders = [o for o in orders if o["user"] == username]

    return render_template(
        "user_management.html",
        target=username,
        data=accounts[username],
        orders=user_orders,
        total_orders=len(user_orders)
    )

# ---------------- BALANCE ----------------
@app.route("/change_balance/<username>", methods=["POST"])
def change_balance(username):
    accounts[username]["balance"] = int(request.form["balance"])
    save()
    return redirect(f"/manage_user/{username}")

# ---------------- PASSWORD RESET ----------------
@app.route("/reset_password/<username>", methods=["POST"])
def reset_password(username):
    accounts[username]["password"] = request.form["password"]
    save()
    return redirect(f"/manage_user/{username}")

# ---------------- DELETE USER ----------------
@app.route("/delete_user/<username>", methods=["POST"])
def delete_user(username):

    #  BLOCK ADMIN DELETE
    if username == "admin":
        session["message"] = "You cant delete the admin account."
        return redirect("/admin")

    if username in accounts:
        del accounts[username]

        global orders
        orders = [o for o in orders if o.get("user") != username]

        save()

        session["message"] = f"User '{username}' deleted successfully!"

    return redirect("/admin")
# ---------------- ADD USER ----------------
@app.route("/add_user", methods=["POST"])
def add_user():
    username = request.form["username"].lower()
    password = request.form["password"]

    if username in accounts:
        session["message"] = "User already exists!"
        return redirect("/admin")

    accounts[username] = {
        "password": password,
        "balance": 0,
        "role": "user"
    }

    save()
    return redirect("/admin")

# ---------------- MENU ----------------
@app.route("/add_item", methods=["POST"])
def add_item():
    item = request.form["item"].lower().replace(" ", "_")
    price = int(request.form["price"])
    category = request.form["category"]

    if category not in menu:
        menu[category] = {}

    menu[category][item] = price

    save()
    return redirect("/admin")

@app.route("/remove_item", methods=["POST"])
def remove_item():
    item_to_remove = request.form["item"].lower().replace(" ", "_")

    for category in menu:
        if item_to_remove in menu[category]:
            del menu[category][item_to_remove]
            save()
            break

    return redirect("/admin")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)