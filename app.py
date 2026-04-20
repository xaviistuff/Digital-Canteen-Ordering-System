from flask import Flask, render_template, request, redirect, session
import json
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

menu_file = "menu.json"
accounts_file = "accounts.json"
orders_file = "orders.json"

# ---------------- LOAD DATA ----------------
menu = json.load(open(menu_file)) if os.path.exists(menu_file) else {
    "zians_hotdog": 50,
    "chris_longganisa": 120,
    "liams_meatballs": 35
}

accounts = json.load(open(accounts_file)) if os.path.exists(accounts_file) else {
    "admin": {"password": "admin123", "balance": 0, "role": "admin"}
}

orders = json.load(open(orders_file)) if os.path.exists(orders_file) else []

def save_data():
    json.dump(menu, open(menu_file, "w"))
    json.dump(accounts, open(accounts_file, "w"))
    json.dump(orders, open(orders_file, "w"))

# ---------------- EMAIL ----------------
def send_email(username, item, qty, total):
    sender_email = "YOUR_EMAIL@gmail.com"
    app_password = "YOUR_APP_PASSWORD"
    receiver_email = "RECEIVER_EMAIL@gmail.com"

    body = f"""
ORDER RECEIPT

User: {username}

Item: {item}
Quantity: {qty}

Total: ₱{total}

Date: {datetime.now().strftime("%B %d, %Y")}
"""

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Digital Canteen Receipt"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, app_password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"].lower()
        p = request.form["password"]

        if u in accounts and accounts[u]["password"] == p:
            session["user"] = u
            return redirect("/admin" if accounts[u]["role"] == "admin" else "/user")

    return render_template("login.html")

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
        today=datetime.now().strftime("%B %d, %Y")
    )

# ---------------- ORDER (SINGLE ITEM) ----------------
@app.route("/order", methods=["POST"])
def order():
    u = session["user"]

    item = request.form["item"]
    qty = int(request.form["qty"])

    if item in menu and qty > 0:

        total = menu[item] * qty

        if accounts[u]["balance"] >= total:

            accounts[u]["balance"] -= total

            orders.append({
                "user": u,
                "item": item,
                "qty": qty,
                "total": total,
                "date": datetime.now().strftime("%B %d, %Y")
            })

            save_data()

            send_email(u, item, qty, total)

    return redirect("/user")

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if "user" not in session:
        return redirect("/")

    if accounts[session["user"]]["role"] != "admin":
        return redirect("/")

    return render_template(
        "admin.html",
        accounts=accounts,
        menu=menu,
        orders=orders
    )

# ---------------- USER MANAGEMENT ----------------
@app.route("/manage_user/<username>")
def manage_user(username):
    return render_template(
        "user_management.html",
        target=username,
        data=accounts[username],
        orders=[o for o in orders if o.get("user") == username]
    )

# ---------------- CHANGE BALANCE ----------------
@app.route("/change_balance/<username>", methods=["POST"])
def change_balance(username):
    accounts[username]["balance"] = int(request.form["balance"])
    save_data()
    return redirect(f"/manage_user/{username}")

# ---------------- RESET PASSWORD ----------------
@app.route("/reset_password/<username>", methods=["POST"])
def reset_password(username):
    accounts[username]["password"] = request.form["password"]
    save_data()
    return redirect(f"/manage_user/{username}")

# ---------------- DELETE USER ----------------
@app.route("/delete_user/<username>", methods=["POST"])
def delete_user(username):
    if username in accounts:
        del accounts[username]

    global orders
    orders = [o for o in orders if o.get("user") != username]

    save_data()
    return redirect("/admin")

# ---------------- MENU ----------------
@app.route("/add_item", methods=["POST"])
def add_item():
    menu[request.form["item"].lower().replace(" ", "_")] = int(request.form["price"])
    save_data()
    return redirect("/admin")

@app.route("/remove_item", methods=["POST"])
def remove_item():
    menu.pop(request.form["item"], None)
    save_data()
    return redirect("/admin")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)