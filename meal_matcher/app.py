import os
import secrets
import smtplib
import time
import json
from functools import wraps
from email.message import EmailMessage
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_session import Session
from cs50 import SQL
from google import genai
from google.genai import types
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from .helpers import run_genetic_algorithm
except ImportError:
    from helpers import run_genetic_algorithm

# Set up reliable paths inside the current execution directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static"),
)

#  PASTE THIS CORRECTED BLOCKED CODE:
app.config["SESSION_PERMANENT"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# Points directly to BASE_DIR so it links with the terminal database file
db = SQL(f"sqlite:///{os.path.join(BASE_DIR, 'meal_matcher.db')}")

# Create user_profiles table if it does not exist
db.execute(
    """
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id INTEGER PRIMARY KEY,
        age INTEGER DEFAULT 30,
        gender TEXT DEFAULT 'male',
        weight_kg REAL DEFAULT 70.0,
        height_cm REAL DEFAULT 170.0,
        activity_level TEXT DEFAULT 'moderate',
        goal TEXT DEFAULT 'maintain',
        conditions TEXT DEFAULT '',
        preferences TEXT DEFAULT '',
        target_calories INTEGER DEFAULT 2000,
        target_protein INTEGER DEFAULT 130,
        target_carbs INTEGER DEFAULT 220,
        target_fat INTEGER DEFAULT 65,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """
)

# Insert standard food items if they aren't already present
default_foods = [
    ("Chicken Breast", 165, 31.0, 0.0, 3.6, 100, 74, 0, 85),
    ("White Rice", 130, 2.7, 28.0, 0.3, 100, 1, 1, 0),
    ("Whole Eggs", 155, 13.0, 1.1, 11.0, 100, 124, 0, 373),
    ("Oatmeal", 389, 16.9, 66.3, 6.9, 100, 2, 0, 0),
    ("Sweet Potato", 86, 1.6, 20.1, 0.1, 100, 55, 0, 0),
    ("Salmon", 208, 20.0, 0.0, 13.0, 100, 59, 0, 55),
    ("Broccoli", 34, 2.8, 7.0, 0.4, 100, 33, 0, 0),
    ("Olive Oil", 884, 0.0, 0.0, 100.0, 100, 2, 0, 0),
    ("Greek Yogurt (Non-Fat)", 59, 10.0, 3.6, 0.4, 100, 36, 0, 5),
    ("Almonds", 579, 21.2, 21.7, 49.9, 100, 1, 0, 0),
    ("Tofu (Firm)", 144, 17.3, 2.8, 8.7, 100, 12, 0, 0),
    ("Quinoa", 120, 4.4, 21.3, 1.9, 100, 7, 0, 0),
    ("Red Lentils (Cooked)", 116, 9.0, 20.0, 0.4, 100, 2, 0, 0),
    ("Black Beans (Cooked)", 132, 8.9, 23.7, 0.5, 100, 1, 0, 0),
    ("Spinach (Raw)", 23, 2.9, 3.6, 0.4, 100, 79, 0, 0),
    ("Avocado", 160, 2.0, 8.5, 14.7, 100, 7, 0, 0),
    ("Chia Seeds", 486, 16.5, 42.1, 30.7, 100, 16, 0, 0),
    ("Whey Protein Powder", 385, 80.0, 6.0, 5.0, 100, 160, 0, 100),
    ("Cod Fish", 82, 18.0, 0.0, 0.7, 100, 54, 0, 43),
    ("Turkey Breast (Cooked)", 135, 30.0, 0.0, 1.0, 100, 68, 0, 70),
    ("Whole Wheat Bread", 247, 13.0, 41.0, 3.4, 100, 400, 1, 0),
    ("Peanut Butter", 588, 25.0, 20.0, 50.0, 100, 350, 0, 0),
    ("Apple", 52, 0.3, 14.0, 0.2, 100, 1, 0, 0),
    ("Banana", 89, 1.1, 23.0, 0.3, 100, 1, 1, 0),
    ("Blueberries", 57, 0.7, 14.0, 0.3, 100, 1, 0, 0),
    ("Skim Milk", 35, 3.4, 5.0, 0.1, 100, 44, 0, 2),
    ("Cheddar Cheese", 403, 25.0, 1.3, 33.0, 100, 621, 0, 105),
    ("Brown Rice (Cooked)", 111, 2.6, 23.0, 0.9, 100, 5, 0, 0),
    ("Edamame", 122, 11.0, 9.8, 5.2, 100, 6, 0, 0),
    ("Cottage Cheese (Low Fat)", 82, 11.0, 4.3, 2.3, 100, 364, 0, 10)
]

for f_name, f_cal, f_pro, f_carb, f_fat, f_serving, f_sod, f_gi, f_chol in default_foods:
    db.execute(
        """
        INSERT OR IGNORE INTO foods (name, calories, protein, carbs, fat, serving_size_g, sodium_mg, glycemic_index_high, cholesterol_mg)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        f_name, f_cal, f_pro, f_carb, f_fat, f_serving, f_sod, f_gi, f_chol
    )

VALID_CONDITIONS = {"diabetes", "gestational_diabetes", "hypertension", "ckd", "cholesterol", "celiac", "ibs"}
VALID_PREFERENCES = {"high_protein", "high_fiber", "low_carb", "keto", "vegan", "vegetarian", "gluten_free", "dairy_free"}
RESET_TOKEN_MAX_AGE = 3600
PASSWORD_RESET_SALT = "password-reset"
RESET_CODE_MAX_AGE = 900

def get_ai_client():
    """Create the Gemini client safely only when a prompt is submitted."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to meal_matcher/.env before generating a plan.")
    return genai.Client()

def get_password_reset_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"])

def generate_password_reset_token(user_id):
    serializer = get_password_reset_serializer()
    return serializer.dumps({"user_id": user_id}, salt=PASSWORD_RESET_SALT)

def verify_password_reset_token(token, max_age=RESET_TOKEN_MAX_AGE):
    serializer = get_password_reset_serializer()
    data = serializer.loads(token, salt=PASSWORD_RESET_SALT, max_age=max_age)
    return data["user_id"]

def send_password_reset_email(email, reset_code, reset_url):
    """Send an authentic transactional password reset code via Google SMTP server."""
    mail_server = os.environ.get("MAIL_SERVER")
    mail_port = int(os.environ.get("MAIL_PORT", "587"))
    mail_username = os.environ.get("MAIL_USERNAME")
    mail_password = os.environ.get("MAIL_PASSWORD")
    sender = os.environ.get("MAIL_DEFAULT_SENDER", mail_username)
    use_tls = os.environ.get("MAIL_USE_TLS", "true").lower() in {"1", "true", "yes"}

    if not mail_server or not sender:
        app.logger.warning("Password reset code for %s: %s", email, reset_code)
        app.logger.warning("Password reset page: %s", reset_url)
        return False

    message = EmailMessage()
    message["Subject"] = "Reset your Meal Matcher password"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        "Use this code to reset your Meal Matcher password:\n\n"
        f"{reset_code}\n\n"
        "Enter it here:\n\n"
        f"{reset_url}\n\n"
        "This code expires in 15 minutes. If you did not request it, you can ignore this email."
    )

    with smtplib.SMTP(mail_server, mail_port) as smtp:
        if use_tls:
            smtp.starttls()
        if mail_username and mail_password:
            smtp.login(mail_username, mail_password)
        smtp.send_message(message)

    return True

def calculate_meal_risks(meal, conditions):
    totals = {
        "sodium_mg": 0,
        "cholesterol_mg": 0,
        "high_gi_count": 0,
        "protein": 0,
        "gluten_count": 0,
        "fodmap_count": 0
    }

    for item in meal:
        # Check if the item is a dictionary (for Genetic Algorithm) or custom object (from Gemini parsing)
        grams = item.get("grams", 100)
        factor = grams / 100.0
        
        totals["sodium_mg"] += item.get("sodium_mg", 0) * factor
        totals["cholesterol_mg"] += item.get("cholesterol_mg", 0) * factor
        totals["protein"] += item.get("protein", 0) * factor
        
        if item.get("glycemic_index_high", 0) == 1:
            totals["high_gi_count"] += 1
        
        name = item.get("name", "")
        if "Whole Wheat Bread" in name or "wheat" in name.lower() or "gluten" in name.lower():
            totals["gluten_count"] += 1
            
        if any(fodmap in name.lower() for fodmap in ["bean", "lentil", "onion", "garlic"]):
            totals["fodmap_count"] += 1

    risk_rules = {
        "diabetes": {
            "condition": "Type 2 Diabetes",
            "is_high": totals["high_gi_count"] > 0,
            "reason": "Contains high-glycemic ingredients." if totals["high_gi_count"] > 0 else "No high-glycemic ingredients selected.",
        },
        "gestational_diabetes": {
            "condition": "Gestational Diabetes",
            "is_high": totals["high_gi_count"] > 0,
            "reason": "Contains high-glycemic ingredients that can cause rapid blood glucose spikes." if totals["high_gi_count"] > 0 else "No high-glycemic ingredients selected.",
        },
        "hypertension": {
            "condition": "Hypertension",
            "is_high": totals["sodium_mg"] > 1500,
            "reason": f"Sodium is {int(totals['sodium_mg'])}mg; target is 1500mg or less.",
        },
        "ckd": {
            "condition": "Chronic Kidney Disease (CKD)",
            "is_high": totals["protein"] > 60,
            "reason": f"Protein is {round(totals['protein'], 1)}g; CKD cap is 60g or less.",
        },
        "cholesterol": {
            "condition": "High Cholesterol",
            "is_high": totals["cholesterol_mg"] > 200,
            "reason": f"Cholesterol is {int(totals['cholesterol_mg'])}mg; target is 200mg or less.",
        },
        "celiac": {
            "condition": "Celiac Disease",
            "is_high": totals["gluten_count"] > 0,
            "reason": "WARNING: Contains ingredients with gluten!" if totals["gluten_count"] > 0 else "Gluten-free ingredients selected.",
        },
        "ibs": {
            "condition": "IBS (High FODMAP)",
            "is_high": totals["fodmap_count"] > 0,
            "reason": "Contains high-FODMAP ingredients." if totals["fodmap_count"] > 0 else "Low-FODMAP ingredients selected.",
        }
    }

    return [
        {
            "condition": risk_rules[condition]["condition"],
            "level": "High Risk" if risk_rules[condition]["is_high"] else "Low Risk",
            "reason": risk_rules[condition]["reason"],
        }
        for condition in conditions
        if condition in risk_rules
    ]

def filter_food_library(food_library, preferences, conditions):
    filtered = []
    meat_fish = {"Chicken Breast", "Salmon", "Cod Fish", "Turkey Breast"}
    dairy_eggs = {"Whole Eggs", "Greek Yogurt (Non-Fat)", "Whey Protein Powder", "Skim Milk", "Cheddar Cheese", "Cottage Cheese (Low Fat)"}
    animal_products = meat_fish.union(dairy_eggs)
    gluten_containing = {"Whole Wheat Bread"}
    high_fodmap = {"Black Beans (Cooked)", "Red Lentils (Cooked)"}
    
    for food in food_library:
        name = food["name"]
        if "vegan" in preferences and name in animal_products:
            continue
        if "vegetarian" in preferences and name in meat_fish:
            continue
        if ("gluten_free" in preferences or "celiac" in conditions) and name in gluten_containing:
            continue
        if "dairy_free" in preferences and name in dairy_eggs:
            dairy_only = {"Greek Yogurt (Non-Fat)", "Whey Protein Powder", "Skim Milk", "Cheddar Cheese", "Cottage Cheese (Low Fat)"}
            if name in dairy_only:
                continue
        if "ibs" in conditions and name in high_fodmap:
            continue
        filtered.append(food)
    return filtered

def get_or_create_profile(user_id):
    profile = db.execute("SELECT * FROM user_profiles WHERE user_id = ?", user_id)
    if not profile:
        db.execute(
            """
            INSERT INTO user_profiles 
            (user_id, age, gender, weight_kg, height_cm, activity_level, goal, conditions, preferences, target_calories, target_protein, target_carbs, target_fat) 
            VALUES (?, 30, 'male', 70.0, 170.0, 'moderate', 'maintain', '', '', 2000, 130, 220, 65)
            """,
            user_id
        )
        profile = db.execute("SELECT * FROM user_profiles WHERE user_id = ?", user_id)
    return profile[0]

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return view(*args, **kwargs)
    return wrapped_view

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user and safely store credentials."""
    if "user_id" in session:
        return redirect("/")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not email:
            return render_template("register.html", error="Please enter your email address."), 400
        if not password:
            return render_template("register.html", error="Please choose a password."), 400
        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters long."), 400
        if password != confirmation:
            return render_template("register.html", error="Passwords do not match."), 400

        existing_email = db.execute("SELECT id FROM users WHERE email = ? OR username = ?", email, email)
        if existing_email:
            return render_template("register.html", error="That email is already registered."), 400

        # Save email in username field too
        user_id = db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            email,
            email,
            generate_password_hash(password),
        )

        session.clear()
        session["user_id"] = user_id
        session["username"] = email.split("@")[0]
        return redirect("/")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log an existing user in."""
    if "user_id" in session:
        return redirect("/")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        
        # Support logging in via email or legacy username
        rows = db.execute("SELECT * FROM users WHERE email = ? OR username = ?", email, email)

        if len(rows) != 1 or not check_password_hash(rows[0]["password_hash"], password):
            return render_template("login.html", error="Invalid email or password."), 400

        session.clear()
        session["user_id"] = rows[0]["id"]
        
        display_name = rows[0]["email"].split("@")[0] if rows[0]["email"] else rows[0]["username"]
        session["username"] = display_name
        return redirect("/")

    return render_template("login.html")

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    """Email a six-digit password reset code if the account exists."""
    if "user_id" in session:
        return redirect("/")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        rows = db.execute("SELECT id, email FROM users WHERE email = ?", email)

        if len(rows) != 1:
            return render_template(
                "forgot_password.html",
                error="That email is not registered yet. Please register first.",
            ), 404

        reset_code = f"{secrets.randbelow(1000000):06d}"
        reset_url = url_for("reset_password_with_code", _external=True)
        sent = send_password_reset_email(rows[0]["email"], reset_code, reset_url)
        
        db.execute(
            "UPDATE users SET reset_code_hash = ?, reset_code_expires_at = ? WHERE id = ?",
            generate_password_hash(reset_code),
            int(time.time()) + RESET_CODE_MAX_AGE,
            rows[0]["id"],
        )

        dev_code = None if sent else reset_code
        return render_template(
            "reset_password.html",
            email=email,
            dev_code=dev_code,
            success="Password reset code sent. Check your email and enter the code below.",
        )

    return render_template("forgot_password.html")

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password_with_code():
    """Reset a password using an emailed six-digit code."""
    if "user_id" in session:
        return redirect("/")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        reset_code = request.form.get("reset_code", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")
        rows = db.execute(
            "SELECT id, reset_code_hash, reset_code_expires_at FROM users WHERE email = ?",
            email,
        )

        if len(rows) != 1:
            return render_template("reset_password.html", email=email, error="That email is not registered yet. Please register first."), 404
        if not rows[0]["reset_code_hash"] or not rows[0]["reset_code_expires_at"]:
            return render_template("reset_password.html", email=email, error="Request a reset code before changing your password."), 400
        if rows[0]["reset_code_expires_at"] < int(time.time()):
            return render_template("reset_password.html", email=email, error="That reset code has expired. Request a new one."), 400
        if not check_password_hash(rows[0]["reset_code_hash"], reset_code):
            return render_template("reset_password.html", email=email, error="Invalid reset code."), 400
        if not password:
            return render_template("reset_password.html", email=email, error="Please choose a new password."), 400
        if len(password) < 8:
            return render_template("reset_password.html", email=email, error="Password must be at least 8 characters long."), 400
        if password != confirmation:
            return render_template("reset_password.html", email=email, error="Passwords do not match."), 400

        db.execute(
            "UPDATE users SET password_hash = ?, reset_code_hash = NULL, reset_code_expires_at = NULL WHERE id = ?",
            generate_password_hash(password),
            rows[0]["id"],
        )
        
        # Log the user in automatically after reset
        session.clear()
        session["user_id"] = rows[0]["id"]
        session["username"] = email.split("@")[0] if email else "User"
        return redirect("/")

    return render_template("reset_password.html")

@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset a password using a signed one-hour token link."""
    if "user_id" in session:
        return redirect("/")

    try:
        user_id = verify_password_reset_token(token)
    except SignatureExpired:
        return render_template("forgot_password.html", error="That reset link has expired. Request a new one."), 400
    except BadSignature:
        return render_template("forgot_password.html", error="That reset link is invalid. Request a new one."), 400

    rows = db.execute("SELECT id, email FROM users WHERE id = ?", user_id)
    if len(rows) != 1:
        return render_template("forgot_password.html", error="That reset link is invalid. Request a new one."), 400

    if request.method == "POST":
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not password:
            return render_template("reset_password.html", token=token, error="Please choose a new password."), 400
        if len(password) < 8:
            return render_template("reset_password.html", token=token, error="Password must be at least 8 characters long."), 400
        if password != confirmation:
            return render_template("reset_password.html", token=token, error="Passwords do not match."), 400

        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            generate_password_hash(password),
            user_id,
        )
        
        # Log the user in automatically after reset
        session.clear()
        session["user_id"] = user_id
        email_val = rows[0]["email"] if rows[0]["email"] else "User"
        session["username"] = email_val.split("@")[0] if email_val else "User"
        return redirect("/")

    return render_template("reset_password.html", token=token)

@app.route("/logout")
def logout():
    """Log the current user out."""
    session.clear()
    return redirect("/login")

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session["user_id"]
    if request.method == "POST":
        try:
            age = int(request.form.get("age", 30))
            gender = request.form.get("gender", "male")
            weight_kg = float(request.form.get("weight_kg", 70.0))
            height_cm = float(request.form.get("height_cm", 170.0))
            activity_level = request.form.get("activity_level", "moderate")
            goal = request.form.get("goal", "maintain")
            
            conditions_list = request.form.getlist("conditions")
            conditions = ",".join([c for c in conditions_list if c in VALID_CONDITIONS])
            
            preferences_list = request.form.getlist("preferences")
            preferences = ",".join([p for p in preferences_list if p in VALID_PREFERENCES])
            
            target_calories = int(request.form.get("target_calories", 2000))
            target_protein = int(request.form.get("target_protein", 130))
            target_carbs = int(request.form.get("target_carbs", 220))
            target_fat = int(request.form.get("target_fat", 65))
            
            db.execute(
                """
                INSERT OR REPLACE INTO user_profiles 
                (user_id, age, gender, weight_kg, height_cm, activity_level, goal, conditions, preferences, target_calories, target_protein, target_carbs, target_fat)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                user_id, age, gender, weight_kg, height_cm, activity_level, goal, conditions, preferences, target_calories, target_protein, target_carbs, target_fat
            )
            
            profile_data = get_or_create_profile(user_id)
            conds = [c for c in profile_data["conditions"].split(",") if c]
            prefs = [p for p in profile_data["preferences"].split(",") if p]
            
            return render_template("profile.html", success="Your wellness profile has been updated successfully!", profile=profile_data, conditions=conds, preferences=prefs)
        except Exception as e:
            profile_data = get_or_create_profile(user_id)
            conds = [c for c in profile_data["conditions"].split(",") if c]
            prefs = [p for p in profile_data["preferences"].split(",") if p]
            return render_template("profile.html", error=f"Error updating profile: {e}", profile=profile_data, conditions=conds, preferences=prefs)

    profile_data = get_or_create_profile(user_id)
    conds = [c for c in profile_data["conditions"].split(",") if c]
    prefs = [p for p in profile_data["preferences"].split(",") if p]
    return render_template("profile.html", profile=profile_data, conditions=conds, preferences=prefs)

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Display the main dashboard input form and handle meal planning requests."""
    user_id = session["user_id"]
    user_profile = get_or_create_profile(user_id)
    
    if request.method == "POST":
        user_prompt = request.form.get("user_prompt", "").strip()
        engine = request.form.get("engine", "gemini")
        
        conditions = [c for c in request.form.getlist("conditions") if c in VALID_CONDITIONS]
        preferences = [p for p in request.form.getlist("preferences") if p in VALID_PREFERENCES]
        
        try:
            target_calories = int(request.form.get("target_calories", user_profile["target_calories"]))
            target_protein = int(request.form.get("target_protein", user_profile["target_protein"]))
            target_carbs = int(request.form.get("target_carbs", user_profile["target_carbs"]))
            target_fat = int(request.form.get("target_fat", user_profile["target_fat"]))
        except ValueError:
            target_calories = user_profile["target_calories"]
            target_protein = user_profile["target_protein"]
            target_carbs = user_profile["target_carbs"]
            target_fat = user_profile["target_fat"]
            
        targets = {
            "calories": target_calories,
            "protein": target_protein,
            "carbs": target_carbs,
            "fat": target_fat
        }
        
        condition_labels = {
            "diabetes": "Type 2 Diabetes",
            "gestational_diabetes": "Gestational Diabetes",
            "hypertension": "Hypertension",
            "ckd": "Chronic Kidney Disease (CKD)",
            "cholesterol": "High Cholesterol",
            "celiac": "Celiac Disease",
            "ibs": "IBS / Low-FODMAP"
        }
        
        preference_labels = {
            "high_protein": "High Protein",
            "high_fiber": "High Fiber",
            "low_carb": "Low Carb",
            "keto": "Keto",
            "vegan": "Vegan",
            "vegetarian": "Vegetarian",
            "gluten_free": "Gluten-Free",
            "dairy_free": "Dairy-Free"
        }
        
        selected_condition_text = ", ".join(condition_labels[c] for c in conditions) or "none"
        selected_preference_text = ", ".join(preference_labels[p] for p in preferences) or "none"
        
        if engine == "gemini":
            system_instruction = f"""
            You are a clinical nutrition and custom meal planning engine.
            The user wants a customized, daily meal plan based on these preferences and medical guidelines:
            - Conditions: {selected_condition_text}.
            - Preferences: {selected_preference_text}.
            - Targets: Calories {targets['calories']} kcal, Protein {targets['protein']}g, Carbs {targets['carbs']}g, Fat {targets['fat']}g.
            - Custom Instructions/Prompt: "{user_prompt}"
            
            Produce a beautiful single-day meal plan containing exactly: breakfast, lunch, dinner, snack.
            Ensure you follow these safety parameters:
            1. Type 2 Diabetes: Low glycemic index ingredients, no added refined sugars, moderate complex carbs.
            2. Hypertension: Under 1500mg sodium daily across all meals.
            3. Chronic Kidney Disease (CKD): Protein MUST be capped at 60g max daily, even if their target or prompt is higher.
            4. High Cholesterol: Under 200mg cholesterol daily, use heart-healthy fats (olive oil, avocados) and lean proteins.
            5. Celiac Disease: STRICTLY GLUTEN-FREE. Check ingredients carefully.
            6. IBS (Low FODMAP): No garlic, onions, beans, wheat, heavy dairy.
            7. Vegan: Only plant-based.
            8. Vegetarian: Plant-based, eggs/dairy allowed.
            9. Gluten-Free / Dairy-Free: Respect as requested.
            10. Gestational Diabetes: Safe, pregnancy-friendly complex carbohydrate portioning distributed throughout the day, low glycemic index, zero refined sugars, paired with adequate proteins and healthy fats to prevent glucose spikes.
            
            CRITICAL PERFORMANCE RULE (FOR GENERATION SPEED):
            To minimize latency and ensure near-instant output, keep the text extremely concise:
            - "description" MUST be exactly one brief sentence (max 12 words).
            - "ingredients" MUST be limited to a maximum of 4 essential items.
            - "instructions" MUST be limited to a maximum of 3 short, direct steps.
            
            Output a valid JSON object matching this exact schema:
            {{
                "breakfast": {{
                    "title": "Dish Title",
                    "description": "Appetizing summary of the breakfast",
                    "prep_time": "Prep/cook time",
                    "ingredients": ["ingredient details", "ingredient details"],
                    "instructions": ["Step 1...", "Step 2..."],
                    "calories": integer,
                    "protein": number,
                    "carbs": number,
                    "fat": number
                }},
                "lunch": {{
                    "title": "Dish Title",
                    "description": "Appetizing summary of the lunch",
                    "prep_time": "Prep/cook time",
                    "ingredients": ["ingredient details", "ingredient details"],
                    "instructions": ["Step 1...", "Step 2..."],
                    "calories": integer,
                    "protein": number,
                    "carbs": number,
                    "fat": number
                }},
                "dinner": {{
                    "title": "Dish Title",
                    "description": "Appetizing summary of the dinner",
                    "prep_time": "Prep/cook time",
                    "ingredients": ["ingredient details", "ingredient details"],
                    "instructions": ["Step 1...", "Step 2..."],
                    "calories": integer,
                    "protein": number,
                    "carbs": number,
                    "fat": number
                }},
                "snack": {{
                    "title": "Dish Title",
                    "description": "Appetizing summary of the snack",
                    "prep_time": "Prep/cook time",
                    "ingredients": ["ingredient details", "ingredient details"],
                    "instructions": ["Step 1...", "Step 2..."],
                    "calories": integer,
                    "protein": number,
                    "carbs": number,
                    "fat": number
                }},
                "actual_totals": {{
                    "calories": integer,
                    "protein": number,
                    "carbs": number,
                    "fat": number,
                    "sodium_mg": integer,
                    "cholesterol_mg": integer
                }}
            }}
            Output ONLY the raw JSON string. Do not include markdown code blocks.
            """
            try:
                ai_client = get_ai_client()
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_prompt if user_prompt else "Plan my day",
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json"
                    )
                )
                meal_plan = json.loads(response.text)
                
                # Format to session
                session["engine"] = "gemini"
                session["meal_plan"] = meal_plan
                session["targets"] = targets
                session["original_prompt"] = user_prompt or "Custom AI Balanced Plan"
                session["conditions"] = conditions
                session["preferences"] = preferences
                return redirect("/results")
            except Exception as e:
                # Log the error for debugging
                app.logger.error(f"Gemini generation/parsing failed: {e}")
                
                # Fall back to Genetic Portion Optimizer for ANY failure (resilience)
                try:
                    food_library = db.execute("SELECT * FROM foods")
                    filtered_library = filter_food_library(food_library, preferences, conditions)
                    if filtered_library:
                        best_meal_plan = run_genetic_algorithm(filtered_library, targets, conditions)
                        session["engine"] = "genetic"
                        session["meal_plan"] = best_meal_plan
                        session["targets"] = targets
                        session["original_prompt"] = user_prompt or "Custom Balanced Plan"
                        session["conditions"] = conditions
                        session["preferences"] = preferences
                        
                        flash("The Personal Wellness Assistant is temporarily experiencing high demand or formatting issues. We have automatically optimized a portion-balanced meal plan for you using our Genetic Optimizer!")
                        return redirect("/results")
                except Exception as fallback_err:
                    app.logger.error(f"Fallback optimizer failed: {fallback_err}")
                    
                return render_template(
                    "index.html",
                    error="The Personal Wellness Assistant is currently experiencing high demand. Please try again in a few moments, or select different goals.",
                    profile=user_profile,
                    conditions=conditions,
                    preferences=preferences
                )
                
        else:  # genetic
            food_library = db.execute("SELECT * FROM foods")
            filtered_library = filter_food_library(food_library, preferences, conditions)
            
            if not filtered_library:
                return render_template(
                    "index.html",
                    error="No foods in the database match your combination of dietary preferences. Try unchecking some preferences or using the Personal Wellness Assistant!",
                    profile=user_profile,
                    conditions=conditions,
                    preferences=preferences
                )
                
            best_meal_plan = run_genetic_algorithm(filtered_library, targets, conditions)
            
            session["engine"] = "genetic"
            session["meal_plan"] = best_meal_plan
            session["targets"] = targets
            session["original_prompt"] = user_prompt or "Genetic Optimization"
            session["conditions"] = conditions
            session["preferences"] = preferences
            return redirect("/results")
            
    conds = [c for c in user_profile["conditions"].split(",") if c]
    prefs = [p for p in user_profile["preferences"].split(",") if p]
    return render_template("index.html", profile=user_profile, conditions=conds, preferences=prefs)

@app.route("/results")
@login_required
def results():
    """Display the generated meal plan output."""
    if "meal_plan" not in session:
        return redirect("/")
        
    engine = session.get("engine", "gemini")
    conditions = session.get("conditions", [])
    targets = session.get("targets")
    prompt = session.get("original_prompt")
    
    if engine == "gemini":
        meal_plan = session["meal_plan"]
        actual_totals = meal_plan.get("actual_totals", {
            "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "sodium_mg": 0, "cholesterol_mg": 0
        })
        
        # Calculate risk assessments based on the meals
        meal_list = []
        for meal_key in ["breakfast", "lunch", "dinner", "snack"]:
            if meal_key in meal_plan:
                item = meal_plan[meal_key]
                meal_list.append({
                    "name": item.get("title", meal_key),
                    "grams": 100, # default factor of 1.0
                    "calories": item.get("calories", 0),
                    "protein": item.get("protein", 0),
                    "carbs": item.get("carbs", 0),
                    "fat": item.get("fat", 0),
                    "sodium_mg": actual_totals.get("sodium_mg", 0) / 4.0, # distribute for risk check
                    "cholesterol_mg": actual_totals.get("cholesterol_mg", 0) / 4.0
                })
        
        risk_assessments = calculate_meal_risks(meal_list, conditions)
        
        return render_template(
            "results.html",
            engine=engine,
            targets=targets,
            meal_plan=meal_plan,
            totals=actual_totals,
            prompt=prompt,
            risk_assessments=risk_assessments
        )
        
    else:  # genetic
        meal_plan = session["meal_plan"]
        actual_totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "sodium_mg": 0, "cholesterol_mg": 0}
        
        for item in meal_plan:
            factor = item["grams"] / 100.0
            actual_totals["calories"] += int(item["calories"] * factor)
            actual_totals["protein"] += round(item["protein"] * factor, 1)
            actual_totals["carbs"] += round(item["carbs"] * factor, 1)
            actual_totals["fat"] += round(item["fat"] * factor, 1)
            actual_totals["sodium_mg"] += int(item.get("sodium_mg", 0) * factor)
            actual_totals["cholesterol_mg"] += int(item.get("cholesterol_mg", 0) * factor)
            
        risk_assessments = calculate_meal_risks(meal_plan, conditions)
        
        return render_template(
            "results.html",
            engine=engine,
            targets=targets,
            meal_plan=meal_plan,
            totals=actual_totals,
            prompt=prompt,
            risk_assessments=risk_assessments
        )