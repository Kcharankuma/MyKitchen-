import os
import random
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super_secret_kitchen_key_123')

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

class ContactInquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- SEED DATABASE ---

DEFAULT_FOOD_IMAGE = 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80'
FOOD_FALLBACKS = {
    'dosa': 'https://images.unsplash.com/photo-1668236543090-82eba5ee5976?auto=format&fit=crop&w=600&q=80',
    'biryani': 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80',
    'paneer': 'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=600&q=80',
    'chicken': 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=600&q=80',
    'idli': 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80',
    'momo': 'https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?auto=format&fit=crop&w=600&q=80',
    'salad': 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=600&q=80'
}

def get_valid_food_image(title, image_url):
    url = (image_url or '').strip()
    if not url.startswith('http') or 'google.com/url' in url or 'gstatic.com' in url or 'encrypted-tbn' in url:
        lower_title = (title or '').lower()
        for keyword, fallback_url in FOOD_FALLBACKS.items():
            if keyword in lower_title:
                return fallback_url
        return DEFAULT_FOOD_IMAGE
    return url

def seed_database():
    if MenuItem.query.count() == 0:
        initial_items = [
            MenuItem(title="Paneer Butter Masala", category="veg", description="Rich cottage cheese cubes in creamy tomato gravy.", price=280, image="https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Exotic Garden Salad", category="veg", description="Fresh organic veggies in lemon vinaigrette.", price=190, image="https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Steamed Idli & Chutney", category="veg", description="Soft steamed rice and lentil cakes served with fresh coconut chutney.", price=120, image="https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Dal Makhani", category="veg", description="Slow-cooked black lentils with butter and cream.", price=220, image="https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=600&q=80"),
            MenuItem(title="Veg Steamed Momos", category="veg", description="Steamed dumplings filled with vegetables.", price=150, image="https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Chicken Dum Biryani", category="nonveg", description="Basmati rice cooked with succulent chicken pieces.", price=340, image="https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Butter Chicken", category="nonveg", description="Tender chicken cooked in rich butter tomato gravy.", price=360, image="https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=500&q=80"),
            MenuItem(title="Chicken Tikka Kebab", category="nonveg", description="Smoky roasted chicken skewers in Indian spices.", price=310, image="https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?auto=format&fit=crop&w=500&q=80")
        ]
        db.session.bulk_save_objects(initial_items)
        db.session.commit()

@app.before_request
def initialize_database():
    db.create_all()
    if Order.query.count() == 0:
        import json
        from datetime import datetime, timedelta
        raw_samples = [
            {'order_number': 'ORD-1001', 'items_json': json.dumps([{'title': 'Chicken Dum Biryani', 'price': 340, 'qty': 2}, {'title': 'Butter Chicken', 'price': 360, 'qty': 1}]), 'subtotal': 1040.0, 'gst_amount': 52.0, 'total': 1092.0, 'grand_total': 1092.0, 'customer_name': 'Rahul Sharma', 'phone': '9876543210', 'address': '14-2, MG Road, Madanapalle', 'status': 'Delivered', 'created_at': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M')},
            {'order_number': 'ORD-1002', 'items_json': json.dumps([{'title': 'Paneer Butter Masala', 'price': 280, 'qty': 1}, {'title': 'Dal Makhani', 'price': 220, 'qty': 1}]), 'subtotal': 500.0, 'gst_amount': 25.0, 'total': 525.0, 'grand_total': 525.0, 'customer_name': 'Priya Reddy', 'phone': '9123456789', 'address': 'Plot 8, Angallu, Madanapalle', 'status': 'Delivered', 'created_at': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M')}
        ]
        valid_cols = ['order_number', 'customer_address', 'customer_email', 'customer_name', 'user_id', 'status', 'payment_status', 'items_json', 'customer_phone', 'id', 'total_amount', 'gst_amount', 'subtotal']
        for s in raw_samples:
            filtered = {k: v for k, v in s.items() if k in valid_cols}
            try:
                db.session.add(Order(**filtered))
                db.session.commit()
            except Exception:
                db.session.rollback()
    seed_database()

# --- TWILIO SMS & EMAIL HELPER FUNCTIONS ---
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

    if not formatted_phone or not account_sid or not auth_token or account_sid.startswith('your_'):
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

    if not formatted_phone or not account_sid or not auth_token or account_sid.startswith('your_'):
        return
    try:
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=f"MY KITCHEN: Order #{order_number} confirmed! Total Bill (incl. GST): Rs. {total:.2f}. Thank you!",
            from_=twilio_phone,
            to=formatted_phone
        )
    except Exception as e:
        print(f"Order SMS Error: {e}")

def send_delivered_sms(order):
    formatted_phone = format_phone_number(order.customer_phone)
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_phone = os.getenv('TWILIO_PHONE_NUMBER', '+17372508034')

    if not formatted_phone or not account_sid or not auth_token or account_sid.startswith('your_'):
        print(f"[SMS Mock] Delivered SMS skipped (Twilio keys missing) for {order.order_number}")
        return
    try:
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=f"MY KITCHEN: Hi {order.customer_name}, your Order #{order.order_number} (Rs. {order.total_amount:.2f}) has been DELIVERED! Enjoy your meal!",
            from_=twilio_phone,
            to=formatted_phone
        )
        print(f"Delivered SMS sent to {formatted_phone}")
    except Exception as e:
        print(f"Delivered SMS Error: {e}")

def send_delivered_email(order):
    # Get recipient email from Order, or fallback to linked User account email
    recipient_email = order.customer_email
    if not recipient_email and order.user_id:
        user = User.query.get(order.user_id)
        if user:
            recipient_email = user.email

    sender_email = os.getenv('SMTP_EMAIL')        # Your Gmail address
    sender_password = os.getenv('SMTP_PASSWORD')  # Your 16-char Gmail App Password

    if not recipient_email or not sender_email or not sender_password:
        print(f"[Email Mock] Delivered Email skipped (Email/SMTP missing) for {order.order_number}")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = f"MY KITCHEN <{sender_email}>"
        msg['To'] = recipient_email
        msg['Subject'] = f"Order #{order.order_number} Delivered! - MY KITCHEN"

        items_list = json.loads(order.items_json) if order.items_json else []
        items_html = "".join(
            f"<li>{item['title']} (x{item['qty']}) - ₹{item['price'] * item['qty']}</li>"
            for item in items_list
        )

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 550px; margin: auto; border: 1px solid #eee; border-radius: 8px; padding: 20px;">
            <h2 style="color: #ff5252;">🍳 MY KITCHEN - Order Delivered!</h2>
            <p>Hi <strong>{order.customer_name}</strong>,</p>
            <p>Great news! Your order <strong>#{order.order_number}</strong> has been successfully delivered to:</p>
            <p style="background: #f9f9f9; padding: 10px; border-radius: 5px;">{order.customer_address}</p>
            <h4>Order Summary:</h4>
            <ul>{items_html}</ul>
            <p><strong>Subtotal:</strong> ₹{order.subtotal:.2f}<br>
            <strong>GST (5%):</strong> ₹{order.gst_amount:.2f}<br>
            <strong style="font-size: 1.1em; color: #2e7d32;">Grand Total Paid: ₹{order.total_amount:.2f}</strong></p>
            <hr style="border: none; border-top: 1px solid #eee;">
            <p style="font-size: 0.85em; color: #777;">Thank you for ordering from MY KITCHEN. Enjoy your meal!</p>
        </div>
        """
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"Delivered Email sent to {recipient_email}")
    except Exception as e:
        print(f"Delivered Email Error: {e}")



def _send_gmail_html(recipient_email, subject, html_body):
    sender_email = (os.getenv('SMTP_EMAIL') or '').strip()
    sender_password = (os.getenv('SMTP_PASSWORD') or '').replace(' ', '').strip()
    admin_email = (os.getenv('ADMIN_EMAIL') or sender_email).strip()

    if not recipient_email or not sender_email or not sender_password:
        print(f"[Email Skipped] recipient={recipient_email}, sender_set={bool(sender_email)}, pass_set={bool(sender_password)}")
        return False

    msg = MIMEMultipart()
    msg['From'] = f"MY KITCHEN <{sender_email}>"
    msg['To'] = recipient_email
    if admin_email and admin_email.lower() != recipient_email.lower():
        msg['Bcc'] = admin_email
    msg['Reply-To'] = sender_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"[Email Sent via 587] To={recipient_email}, Bcc={admin_email}")
        return True
    except Exception as e587:
        print(f"[SMTP 587 Failed] {e587} -> trying 465...")
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
            print(f"[Email Sent via 465] To={recipient_email}, Bcc={admin_email}")
            return True
        except Exception as e465:
            print(f"[SMTP 465 Failed] {e465}")
            return False

def send_order_email(order):
    recipient_email = (order.customer_email or '').strip()
    if not recipient_email and order.user_id:
        user = db.session.get(User, order.user_id)
        if user:
            recipient_email = (user.email or '').strip()
    if not recipient_email:
        print(f"[Order Email Skipped] No email found for order #{order.order_number}")
        return

    items_list = json.loads(order.items_json) if order.items_json else []
    items_html = "".join(f"<li>{i['title']} (x{i['qty']}) - Rs. {i['price'] * i['qty']:.2f}</li>" for i in items_list)
    half_gst = order.gst_amount / 2
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 550px; margin: auto; border: 1px solid #eee; border-radius: 8px; padding: 20px;">
        <h2 style="color: #ff5252;">MY KITCHEN - Order Confirmed!</h2>
        <p>Hi <strong>{order.customer_name}</strong>, thank you for your order <strong>#{order.order_number}</strong>.</p>
        <ul>{items_html}</ul>
        <p>Items Subtotal: Rs. {order.subtotal:.2f}<br>
        CGST (2.5%): Rs. {half_gst:.2f}<br>
        SGST (2.5%): Rs. {half_gst:.2f}<br>
        <strong>Total Paid: Rs. {order.total_amount:.2f}</strong></p>
        <p>Delivery Address: {order.customer_address}</p>
    </div>
    """
    _send_gmail_html(recipient_email, f"Order #{order.order_number} Confirmed - MY KITCHEN", html_body)

def send_delivered_notifications(order):
    # 1. SMS
    formatted_phone = format_phone_number(order.customer_phone)
    account_sid = (os.getenv('TWILIO_ACCOUNT_SID') or '').strip()
    auth_token = (os.getenv('TWILIO_AUTH_TOKEN') or '').strip()
    twilio_phone = os.getenv('TWILIO_PHONE_NUMBER', '+17372508034')

    if formatted_phone and account_sid and auth_token and not account_sid.startswith('your_'):
        try:
            client = Client(account_sid, auth_token)
            client.messages.create(
                body=f"MY KITCHEN: Hi {order.customer_name}, your Order #{order.order_number} (Rs. {order.total_amount:.2f}) has been DELIVERED! Enjoy your meal!",
                from_=twilio_phone,
                to=formatted_phone
            )
        except Exception as e:
            print(f"Delivered SMS Error: {e}")

    # 2. Email
    recipient_email = (order.customer_email or '').strip()
    if not recipient_email and order.user_id:
        user = db.session.get(User, order.user_id)
        if user:
            recipient_email = (user.email or '').strip()
    if not recipient_email:
        print(f"[Delivered Email Skipped] No email found for order #{order.order_number}")
        return

    items_list = json.loads(order.items_json) if order.items_json else []
    items_html = "".join(f"<li>{i['title']} (x{i['qty']}) - Rs. {i['price'] * i['qty']:.2f}</li>" for i in items_list)
    half_gst = order.gst_amount / 2
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 550px; margin: auto; border: 1px solid #eee; border-radius: 8px; padding: 20px;">
        <h2 style="color: #2e7d32;">MY KITCHEN - Order Delivered!</h2>
        <p>Hi <strong>{order.customer_name}</strong>,</p>
        <p>Your order <strong>#{order.order_number}</strong> has been delivered to: {order.customer_address}</p>
        <ul>{items_html}</ul>
        <p>Items Subtotal: Rs. {order.subtotal:.2f}<br>
        CGST (2.5%): Rs. {half_gst:.2f}<br>
        SGST (2.5%): Rs. {half_gst:.2f}<br>
        <strong>Total Paid: Rs. {order.total_amount:.2f}</strong></p>
        <p>*** Thank you for dining with MY KITCHEN! ***</p>
    </div>
    """
    _send_gmail_html(recipient_email, f"Order #{order.order_number} Delivered! - MY KITCHEN", html_body)

# --- FRONTEND & AUTH ROUTES ---
    raw_url = str(raw_url).strip()
    if "imgurl=" in raw_url:
        parsed = parse_qs(urlparse(raw_url).query)
        if "imgurl" in parsed and parsed["imgurl"]:
            return unquote(parsed["imgurl"][0])
    if raw_url.startswith(("http://", "https://", "/static/")):
        return raw_url
    return default_img

    raw_url = str(raw_url).strip()
    if "imgurl=" in raw_url:
        parsed = parse_qs(urlparse(raw_url).query)
        if "imgurl" in parsed and parsed["imgurl"]:
            return unquote(parsed["imgurl"][0])
    if raw_url.startswith(("http://", "https://", "/static/")):
        return raw_url
    return default_img


def clean_image_url(raw_url):
    from urllib.parse import urlparse, parse_qs, unquote
    if not raw_url or not str(raw_url).strip():
        return ""
    raw_url = str(raw_url).strip()
    if "imgurl=" in raw_url:
        parsed = parse_qs(urlparse(raw_url).query)
        if "imgurl" in parsed and parsed["imgurl"]:
            return unquote(parsed["imgurl"][0])
    return raw_url


def validate_registration_fields(name, email, phone, address, password):
    import re
    if not name or not re.match(r'^[A-Za-z][A-Za-z\s]{2,49}$', name.strip()):
        return "Full Name must contain only letters and spaces (min 3 characters)."
    if not email or not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email.strip()):
        return "Please enter a valid Email Address."
    if not phone or not re.match(r'^[6-9][0-9]{9}$', phone.strip()):
        return "Phone Number must be a valid 10-digit mobile number."
    if not address or len(address.strip()) < 10 or not re.search(r'[A-Za-z]{3,}', address) or not re.search(r'[\s,]', address.strip()):
        return "Please enter a complete Delivery Address (street, area, and city)."
    if not password or len(password) < 6:
        return "Password must be at least 6 characters long."
    return None

@app.route('/')
def home():
    if not session.get('user_id'):
        return redirect(url_for('customer_login'))
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.pop('user_id', None)
        session.pop('user_name', None)
        return redirect(url_for('customer_login'))
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


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('admin_logged_in', None)
    return redirect(url_for('customer_login'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    error = None
    success = None
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        new_password = (request.form.get('new_password') or '').strip()

        user = User.query.filter_by(email=email).first()
        if not user:
            error = "No account found with that email address."
        elif phone not in (user.phone or '') and (user.phone or '') not in phone:
            error = "Registered phone number does not match this account."
        elif len(new_password) < 4:
            error = "Please enter a new password (at least 4 characters)."
        else:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            success = "Password updated successfully! You can now log in."

    msg_html = ""
    if error:
        msg_html = f'<div style="background:#ffebee;color:#c62828;padding:10px;border-radius:6px;margin-bottom:12px;font-size:0.9rem;">{error}</div>'
    elif success:
        msg_html = f'<div style="background:#e8f5e9;color:#2e7d32;padding:10px;border-radius:6px;margin-bottom:12px;font-size:0.9rem;">{success}</div>'

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reset Password - MY KITCHEN</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Poppins', sans-serif; background: #fffafa; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 1rem; }}
            .box {{ background: #fff; padding: 2rem; border-radius: 12px; box-shadow: 0 8px 25px rgba(0,0,0,0.08); width: 100%; max-width: 400px; }}
            h2 {{ color: #ff5252; margin-top: 0; text-align: center; }}
            p.sub {{ color: #666; font-size: 0.88rem; text-align: center; margin-bottom: 1.2rem; }}
            label {{ display: block; font-size: 0.85rem; font-weight: 600; margin-top: 0.8rem; color: #333; }}
            input {{ width: 100%; padding: 0.7rem; margin-top: 0.3rem; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 0.95rem; }}
            button {{ width: 100%; background: #ff5252; color: #fff; border: none; padding: 0.85rem; border-radius: 8px; font-weight: 600; font-size: 1rem; cursor: pointer; margin-top: 1.3rem; }}
            button:hover {{ background: #e04343; }}
            .back {{ display: block; text-align: center; margin-top: 1rem; color: #555; text-decoration: none; font-size: 0.9rem; }}
            .back:hover {{ color: #ff5252; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h2>Reset Password</h2>
            <p class="sub">Verify your registered email and phone number to set a new password.</p>
            {msg_html}
            <form method="POST">
                <label>Registered Email</label>
                <input type="email" name="email" placeholder="you@example.com" required>
                <label>Registered Phone Number</label>
                <input type="tel" name="phone" placeholder="e.g. 7075575715" required>
                <label>New Password</label>
                <input type="password" name="new_password" placeholder="Enter new password" required>
                <button type="submit">Update Password</button>
            </form>
            <a href="/customer/login" class="back">← Back to Customer Login</a>
        </div>
    </body>
    </html>
    '''

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

# --- ADMIN ROUTES ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'adminpassword':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            error = 'Invalid Admin Credentials!'
            
    return render_template('auth.html', error=error, mode='login', is_admin=True)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

@app.route('/admin/export-orders')
def export_orders_excel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    import csv, io, json
    from flask import Response
    orders = Order.query.order_by(Order.id.desc()).all()
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(['Order ID', 'Order Number', 'Customer Name', 'Phone', 'Address', 'Items Ordered', 'Subtotal (INR)', 'GST 5% (INR)', 'Grand Total (INR)', 'Status', 'Order Date'])
    for o in orders:
        try:
            parsed_items = json.loads(o.items_json or '[]')
            items_summary = '; '.join([f"{i.get('title', i.get('name', 'Item'))} x{i.get('qty', i.get('quantity', 1))}" for i in parsed_items])
        except Exception:
            items_summary = str(o.items_json or '')
        cust_name = getattr(o, 'customer_name', '') or (o.user.name if getattr(o, 'user', None) else 'Guest')
        cust_phone = getattr(o, 'phone', '') or (getattr(o, 'user', None).phone if getattr(o, 'user', None) else '')
        cust_addr = getattr(o, 'address', '') or (getattr(o, 'user', None).address if getattr(o, 'user', None) else '')
        grand_total = getattr(o, 'total', None) or getattr(o, 'grand_total', None) or round(float(o.subtotal or 0) + float(o.gst_amount or 0), 2)
        status = getattr(o, 'status', 'Confirmed')
        created = str(getattr(o, 'created_at', '') or getattr(o, 'order_date', ''))
        writer.writerow([o.id, o.order_number, cust_name, cust_phone, cust_addr, items_summary, o.subtotal, o.gst_amount, grand_total, status, created])
    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=MyKitchen_Customer_Orders_Report.csv'}
    )

@app.route('/admin')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    items = MenuItem.query.all()
    orders = Order.query.order_by(Order.id.desc()).all()
    inquiries = ContactInquiry.query.order_by(ContactInquiry.id.desc()).all()
    total_sales = sum(o.total_amount for o in orders)
    
    return render_template(
        'admin.html', 
        items=items, 
        orders=orders, 
        inquiries=inquiries,
        total_sales=total_sales, 
        total_orders=len(orders), 
        total_dishes=len(items)
    )

@app.route('/admin/add', methods=['GET', 'POST'])
def admin_add_item():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        title = request.form.get('title')
        category = (request.form.get('category') or 'Non-Veg').strip() or 'Non-Veg'
        description = request.form.get('description')
        price = int(request.form.get('price', 0))
        image = clean_image_url(request.form.get('image'))

        new_dish = MenuItem(title=title, category=category, description=description, price=price, image=image)
        db.session.add(new_dish)
        db.session.commit()
        return redirect(url_for('admin_panel'))

    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Add Menu Dish - MY KITCHEN</title>
        <style>
            body { font-family: sans-serif; background: #fffafa; padding: 2rem; display: flex; justify-content: center; }
            .form-box { background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); width: 100%; max-width: 450px; }
            h2 { margin-bottom: 1.5rem; color: #ff5252; }
            label { display: block; margin-top: 1rem; font-weight: bold; font-size: 0.9rem; }
            input, select, textarea { width: 100%; padding: 0.6rem; margin-top: 0.3rem; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
            .btn-submit { background: #ff5252; color: white; border: none; padding: 0.8rem 1.5rem; border-radius: 6px; cursor: pointer; font-weight: bold; margin-top: 1.2rem; }
            .cancel-link { margin-left: 1rem; color: #666; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="form-box">
            <h2>Add New Menu Dish</h2>
            <form method="POST">
                <label>Dish Name:</label>
                <input type="text" name="title" placeholder="e.g. Hyderabad Dum Biryani" required>
                <label>Category:</label>
                <select name="category" required>
                    <option value="veg">Pure Veg</option>
                    <option value="nonveg">Non-Veg</option>
                </select>
                <label>Description:</label>
                <textarea name="description" rows="3" placeholder="Brief description of ingredients..." required></textarea>
                <label>Price (Rs.):</label>
                <input type="number" name="price" placeholder="320" required>
                <label>Image URL:</label>
                <input type="text" name="image" placeholder="Leave blank for auto food image or paste URL">
                <div>
                    <button type="submit" class="btn-submit">Add Dish</button>
                    <a href="/admin" class="cancel-link">Cancel</a>
                </div>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/admin/delete/<int:item_id>', methods=['GET', 'POST'])
def admin_delete_item(item_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    item = MenuItem.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/order/status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    order = Order.query.get_or_404(order_id)
    previous_status = order.status
    status = request.form.get('status')
    
    if status:
        order.status = status
        db.session.commit()
        
        # Trigger SMS & Email only when status changes to 'Delivered'
        if status.lower() == 'delivered' and previous_status.lower() != 'delivered':
            send_delivered_sms(order)
            send_delivered_email(order)
        
    return redirect(url_for('admin_panel'))

# --- API ROUTES ---
@app.route('/api/user-data')
def get_user_data():
    if session.get('user_id'):
        user = db.session.get(User, session['user_id'])
        if user:
            return jsonify({
                "logged_in": True,
                "name": user.name,
                "phone": user.phone,
                "address": user.address,
                "email": user.email
            })
        session.pop('user_id', None)
        session.pop('user_name', None)
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
    email = (data.get('email') or '').strip()

    if not cart or not name or not phone or not address:
        return jsonify({"success": False, "message": "Please fill in all checkout details."}), 400

    # Auto-fill email from logged-in account if checkout form didn't pass one
    user_id = session.get('user_id')
    if not email and user_id:
        user = User.query.get(user_id)
        if user:
            email = user.email

    subtotal = sum(item['price'] * item['qty'] for item in cart)
    gst_amount = round(subtotal * 0.05, 2)
    grand_total = round(subtotal + gst_amount, 2)

    order_num = f"ORD-{random.randint(100000, 999999)}"

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

    try:
        send_order_sms(order_num, grand_total, phone)
        send_order_email(new_order)
    except Exception as e:
        print(f'Notification Error: {e}')

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

# --- DYNAMIC CONTACT FORM API ROUTE ---
@app.route('/api/contact', methods=['POST'])
def submit_contact_inquiry():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = (data.get('email') or '').strip().strip()
    phone = data.get('phone', '').strip()
    message = data.get('message', '').strip()

    if not name or not email or not phone or not message:
        return jsonify({"success": False, "message": "Please fill out all fields."}), 400

    inquiry = ContactInquiry(name=name, email=email, phone=phone, message=message)
    db.session.add(inquiry)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Thank you, {name}! Your message has been saved. We'll be in touch soon."
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)