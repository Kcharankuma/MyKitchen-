import os
import random
import json
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super_secret_kitchen_key_123')

# --- ADMIN SECRET CONFIGURATION ---
ADMIN_SECRET_KEY = os.getenv('ADMIN_SECRET_KEY', 'mysecretkitchen123')

# --- DATABASE CONFIGURATION (Vercel Read-Only Fix) ---
if os.getenv('VERCEL'):
    db_path = '/tmp/kitchen.db'
else:
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'kitchen.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(500), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    items_json = db.Column(db.Text, nullable=False, default="[]")
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    gst_amount = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=True)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_address = db.Column(db.Text, nullable=False)
    payment_status = db.Column(db.String(20), default="Paid (Simulated)")
    status = db.Column(db.String(20), default="Pending")

# --- SEED DATABASE ---
def seed_database():
    if MenuItem.query.count() == 0:
        initial_items = [
            MenuItem(title="Paneer Butter Masala", category="veg", description="Rich cottage cheese cubes in creamy tomato gravy.", price=280, image="https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Exotic Garden Salad", category="veg", description="Fresh organic veggies in lemon vinaigrette.", price=190, image="https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Crispy Masala Dosa", category="veg", description="South Indian crepe stuffed with spiced potato filling.", price=120, image="https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Dal Makhani", category="veg", description="Slow-cooked black lentils with butter and cream.", price=220, image="https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Veg Steamed Momos", category="veg", description="Steamed dumplings filled with vegetables.", price=150, image="https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Chicken Dum Biryani", category="nonveg", description="Basmati rice cooked with succulent chicken pieces.", price=340, image="https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Butter Chicken", category="nonveg", description="Tender chicken cooked in rich butter tomato gravy.", price=360, image="https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Chicken Tikka Kebab", category="nonveg", description="Smoky roasted chicken skewers in Indian spices.", price=310, image="https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?auto=format&fit=crop&w=500&q=80")
        ]
        db.session.bulk_save_objects(initial_items)
        db.session.commit()

# Ensure database tables exist safely before requests
@app.before_request
def initialize_database():
    db.create_all()
    seed_database()

# --- TWILIO SMS HELPER FUNCTIONS ---
def format_phone_number(phone):
    if not phone:
        return None
    phone = phone.strip()
    if len(phone) == 10 and not phone.startswith('+'):
        return f"+91{phone}"
    return phone

def send_welcome_sms(name, phone_number):
    formatted_phone = format_phone_number(phone_number)
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_phone = os.getenv('TWILIO_PHONE_NUMBER', '+17372508034')

    if not formatted_phone or not account_sid or not auth_token:
        return
    try:
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=f"Welcome to MY KITCHEN, {name}! Account registered successfully.",
            from_=twilio_phone,
            to=formatted_phone
        )
    except Exception as e:
        print(f"Welcome SMS Error: {e}")

def send_order_sms(order_number, total, phone_number):
    formatted_phone = format_phone_number(phone_number)
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_phone = os.getenv('TWILIO_PHONE_NUMBER', '+17372508034')

    if not formatted_phone or not account_sid or not auth_token:
        return
    try:
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=f"MY KITCHEN: Order #{order_number} confirmed! Total Bill (incl. GST): Rs. {total:.2f}. Thank you!",
            from_=twilio_phone,
            to=formatted_phone
        )
    except Exception as e:
        # Catches Error 572006 or failed credentials safely without crashing the app
        print(f"Order SMS Error: {e}")

# --- FRONTEND & AUTH ROUTES ---
@app.route('/')
def home():
    user = User.query.get(session.get('user_id')) if session.get('user_id') else None
    return render_template('index.html', user=user)

@app.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            return redirect(url_for('home'))
        else:
            error = "Invalid Email or Password!"
    return render_template('auth.html', error=error, mode='login', is_admin=False)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            error = "Email address already registered!"
        else:
            hashed_pw = generate_password_hash(password)
            new_user = User(name=name, email=email, phone=phone, address=address, password_hash=hashed_pw)
            db.session.add(new_user)
            db.session.commit()

            session['user_id'] = new_user.id
            session['user_name'] = new_user.name
            send_welcome_sms(name, phone)
            return redirect(url_for('home'))
    return render_template('auth.html', error=error, mode='register', is_admin=False)

@app.route('/customer/logout')
def customer_logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('home'))

@app.route('/my-orders')
def my_orders():
    if not session.get('user_id'):
        return redirect(url_for('customer_login'))
    orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.id.desc()).all()
    return render_template('orders.html', orders=orders)

@app.route('/admin/order/status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login', key=ADMIN_SECRET_KEY))
    
    order = Order.query.get_or_404(order_id)
    status = request.form.get('status')
    if status:
        order.status = status
        db.session.commit()
        
    return redirect(url_for('admin_panel'))

# --- API ROUTES ---
@app.route('/api/user-data')
def get_user_data():
    if session.get('user_id'):
        user = User.query.get(session['user_id'])
        return jsonify({
            "logged_in": True,
            "name": user.name,
            "phone": user.phone,
            "address": user.address,
            "email": user.email
        })
    return jsonify({"logged_in": False})

@app.route('/api/menu', methods=['GET'])
def get_menu():
    items = MenuItem.query.all()
    menu_data = [{
        "id": i.id,
        "title": i.title,
        "category": i.category,
        "description": i.description,
        "price": i.price,
        "image": i.image
    } for i in items]
    return jsonify({"success": True, "count": len(menu_data), "data": menu_data})

@app.route('/api/order', methods=['POST'])
def place_order():
    data = request.get_json()
    cart = data.get('cart', [])
    name = data.get('name')
    phone = data.get('phone')
    address = data.get('address')
    email = data.get('email', '')

    if not cart or not name or not phone or not address:
        return jsonify({"success": False, "message": "Please fill in all checkout details."}), 400

    subtotal = sum(item['price'] * item['qty'] for item in cart)
    gst_amount = round(subtotal * 0.05, 2)
    grand_total = round(subtotal + gst_amount, 2)

    order_num = f"ORD-{random.randint(100000, 999999)}"
    user_id = session.get('user_id')

    new_order = Order(
        order_number=order_num,
        user_id=user_id,
        items_json=json.dumps(cart),
        subtotal=subtotal,
        gst_amount=gst_amount,
        total_amount=grand_total,
        customer_name=name,
        customer_email=email,
        customer_phone=phone,
        customer_address=address,
        payment_status="Paid (Simulated)"
    )
    db.session.add(new_order)
    db.session.commit()

    # Safely triggers SMS notification
    send_order_sms(order_num, grand_total, phone)

    return jsonify({
        "success": True,
        "orderId": order_num,
        "subtotal": subtotal,
        "gst": gst_amount,
        "grandTotal": grand_total,
        "items": cart,
        "customerName": name,
        "customerPhone": phone,
        "customerAddress": address
    })

# --- ADMIN ROUTES ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    access_key = request.args.get('key') or request.form.get('secret_key')
    if access_key != ADMIN_SECRET_KEY and not session.get('admin_logged_in'):
        return "Not Found: The requested URL was not found on the server.", 404

    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'adminpassword':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            error = 'Invalid Admin Credentials!'
            
    return render_template('auth.html', error=error, mode='login', is_admin=True, secret_key=ADMIN_SECRET_KEY)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

@app.route('/admin')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login', key=ADMIN_SECRET_KEY))
        
    items = MenuItem.query.all()
    orders = Order.query.order_by(Order.id.desc()).all()
    total_sales = sum(o.total_amount for o in orders)
    
    return render_template('admin.html', items=items, orders=orders, total_sales=total_sales, total_orders=len(orders), total_dishes=len(items))

if __name__ == "__main__":
    app.run()