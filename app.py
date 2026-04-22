from flask import (Flask, render_template, session, redirect,
                   url_for, request, g, jsonify, flash)
import json
import sqlite3
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import requests
import os
import re
import uuid
import pickle
from datetime import datetime
import numpy as np
from werkzeug.utils import secure_filename
from tensorflow.keras.models import load_model
from nltk.stem import WordNetLemmatizer
import nltk
from translator import to_english, to_tamil
from googletrans import Translator

# ── App setup ────────────────────────────────────────────────
app = Flask(__name__,static_folder='static')
app.secret_key = "123"

translator    = Translator()
lemmatizer    = WordNetLemmatizer()

model   = load_model("chatbot_model.h5")
words   = pickle.load(open("words.pkl",   "rb"))
classes = pickle.load(open("classes.pkl", "rb"))

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")

DB             = "database.db"
SENDER_EMAIL   = "tnconnect.2k26@gmail.com"
SENDER_PASSWORD = "fpnpwqczchwrztuk"

# ── Language context ─────────────────────────────────────────
@app.before_request
def set_language_context():
    g.lang = session.get("lang", "en")

def at(text):
    return text

app.jinja_env.filters["at"] = at

# ── Intents for chatbot ──────────────────────────────────────
try:
    with open('intent.json', 'r', encoding='utf-8') as f:
        intents_data = json.load(f)
except FileNotFoundError:
    intents_data = {"intents": []}
    print("Warning: intent.json not found!")

# ── TN district data ─────────────────────────────────────────
with open('tamilnadu_updated.json', 'r', encoding='utf-8') as f:
    raw_json = json.load(f)

tn_data = {}
for item in raw_json['state']['districts']:
    if 'name' in item:
        tn_data[item['name']] = item
    elif 'districts' in item:
        for sub_item in item['districts']:
            name = sub_item.get('name') or sub_item.get('district')
            if name:
                tn_data[name] = sub_item


@app.template_filter('from_json')
def from_json_filter(value):
    try:
        return json.loads(value)
    except:
        return {}
    
# ════════════════════════════════════════════════════════════
#  DATABASE
# ════════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT,
            email               TEXT UNIQUE,
            password            TEXT,
            mobile              TEXT,
            dob                 TEXT,
            gender              TEXT,
            state               TEXT DEFAULT 'Tamil Nadu',
            district            TEXT,
            rural_urban         TEXT,
            village_city        TEXT,
            annual_income       TEXT,
            bpl_apl             TEXT,
            ration_card         TEXT,
            education           TEXT,
            currently_studying  TEXT,
            study_type          TEXT,
            employment_status   TEXT,
            occupation          TEXT,
            caste_category      TEXT,
            disability          TEXT,
            widow_single_parent TEXT,
            is_farmer           TEXT,
            land_ownership      TEXT,
            land_acres          TEXT,
            minority            TEXT,
            aadhar              TEXT,
            aadhar_verified     INTEGER DEFAULT 0,
            aadhar_verified_at  TEXT,
            status              TEXT DEFAULT 'Pending'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS grievances (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER,
            name             TEXT,
            aadhar           TEXT,
            mobile           TEXT,
            address          TEXT,
            reason           TEXT,
            district         TEXT,
            constituency     TEXT,
            scheme           TEXT,
            photo            TEXT,
            status           TEXT DEFAULT 'Pending',
            rejection_reason TEXT,
            applied_at       TEXT,
            viewed_at        TEXT,
            action_at        TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            citizen_name TEXT,
            category     TEXT,
            priority     TEXT DEFAULT 'Medium',
            subject      TEXT,
            description  TEXT,
            location     TEXT,
            photo        TEXT,
            status       TEXT DEFAULT 'Open',
            gov_reply    TEXT,
            submitted_at TEXT,
            updated_at   TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Default admin account
    conn.execute(
        "INSERT OR IGNORE INTO admins(id,username,password) VALUES(1,'admin','1234')"
    )
    conn.commit()
    conn.close()


def migrate_tables():
    """
    Safe migration — adds columns that may be missing in an
    existing database without touching existing data.
    """
    conn = get_db()
    safe_alters = [
        ("grievances", "rejection_reason",   "TEXT"),
        ("users",      "mobile",             "TEXT"),
        ("users",      "dob",                "TEXT"),
        ("users",      "gender",             "TEXT"),
        ("users",      "state",              "TEXT DEFAULT 'Tamil Nadu'"),
        ("users",      "district",           "TEXT"),
        ("users",      "rural_urban",        "TEXT"),
        ("users",      "village_city",       "TEXT"),
        ("users",      "annual_income",      "TEXT"),
        ("users",      "bpl_apl",            "TEXT"),
        ("users",      "ration_card",        "TEXT"),
        ("users",      "education",          "TEXT"),
        ("users",      "currently_studying", "TEXT"),
        ("users",      "study_type",         "TEXT"),
        ("users",      "employment_status",  "TEXT"),
        ("users",      "occupation",         "TEXT"),
        ("users",      "caste_category",     "TEXT"),
        ("users",      "disability",         "TEXT"),
        ("users",      "widow_single_parent","TEXT"),
        ("users",      "is_farmer",          "TEXT"),
        ("users",      "land_ownership",     "TEXT"),
        ("users",      "land_acres",         "TEXT"),
        ("users",      "minority",           "TEXT"),
        ("users",      "aadhar",             "TEXT"),
        ("users",      "aadhar_verified",    "INTEGER DEFAULT 0"),
        ("users",      "aadhar_verified_at", "TEXT"),
        ("users", "latitude", "TEXT"),
        ("users", "longitude", "TEXT"),
        ("users", "geo_district", "TEXT"),

    ]
    for table, col, col_type in safe_alters:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            conn.commit()
        except Exception:
            pass  
    conn.close()


create_tables()
migrate_tables()




def translate_text(text, source, target):
    try:
        result = translator.translate(text, src=source, dest=target)
        return result.text
    except Exception as e:
        print(f"Translation error: {e}")
        return text




def _smtp_send(to_email, subject, html_body):
    """Shared SMTP sender used by all email helpers."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"TN Welfare Portal <{SENDER_EMAIL}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Mail error ({subject[:30]}): {e}")
        return False


def send_otp_email(to_email, otp):
    transaction_id = f"TNeGA-{uuid.uuid4().hex[:8].upper()}-{datetime.now().year}"
    subject = f"ACTION REQUIRED: OTP for Citizen Welfare Portal [Ref: {transaction_id}]"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;background:#f4f7f6;">
      <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr><td align="center" style="padding:20px 0;">
          <table border="0" cellpadding="0" cellspacing="0" width="600"
                 style="background:#fff;border:1px solid #ddd;border-radius:8px;overflow:hidden;">
            <tr style="background:#003366;">
              <td align="center" style="padding:25px;">
                <h1 style="color:#fff;margin:0;font-size:18px;text-transform:uppercase;">தமிழ்நாடு அரசு</h1>
                <h2 style="color:#FFD700;margin:5px 0 0;font-size:14px;font-weight:400;">Government of Tamil Nadu</h2>
              </td>
            </tr>
            <tr style="background:#002244;">
              <td align="center" style="padding:10px;border-bottom:3px solid #FFD700;">
                <span style="color:#fff;font-size:12px;font-weight:bold;letter-spacing:.5px;">
                  Integrated Citizen Service Portal | ஒருங்கிணைந்த குடிமக்கள் சேவை மையம்
                </span>
              </td>
            </tr>
            <tr>
              <td style="padding:40px 30px;">
                <p style="font-size:15px;color:#333;"><strong>வணக்கம் (Dear Citizen),</strong></p>
                <p style="font-size:14px;color:#555;line-height:1.6;">
                  A request has been made to access your account. Use the OTP below —
                  valid for <b>100 seconds</b>.
                </p>
                <div style="text-align:center;margin:35px 0;">
                  <div style="background:#f9f9f9;border:2px dashed #003366;padding:20px;display:inline-block;border-radius:10px;">
                    <span style="font-size:32px;font-weight:bold;letter-spacing:8px;color:#003366;
                                 font-family:'Courier New',monospace;">{otp}</span>
                    <p style="font-size:11px;color:#888;margin-top:10px;">Transaction ID: {transaction_id}</p>
                  </div>
                </div>
                <div style="background:#fff9e6;border-left:4px solid #FFD700;padding:15px;margin-bottom:25px;">
                  <p style="font-size:13px;color:#444;margin:0;">
                    <b>பாதுகாப்பு எச்சரிக்கை:</b> இந்த OTP-ஐ யாரிடமும் பகிர வேண்டாம்.
                  </p>
                </div>
                <p style="font-size:12px;color:#777;">
                  If you did not initiate this, contact <b>support.citizen@tn.gov.in</b>.
                </p>
              </td>
            </tr>
            <tr style="background:#f8f9fa;border-top:1px solid #eee;">
              <td style="padding:20px 30px;">
                <table width="100%"><tr>
                  <td style="font-size:11px;color:#999;">
                    Department of e-Governance, TN<br>
                    Tamil Nadu e-Governance Agency (TNeGA)<br>
                    Chennai, Tamil Nadu - 600002.
                  </td>
                  <td align="right">
                    <img src="https://upload.wikimedia.org/wikipedia/en/2/22/Digital_India_logo.svg" width="70">
                  </td>
                </tr></table>
              </td>
            </tr>
            <tr style="background:#003366;">
              <td style="padding:15px;color:#fff;font-size:9px;text-align:center;opacity:.7;">
                &copy; {datetime.now().year} Government of Tamil Nadu. All Rights Reserved.
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """
    _smtp_send(to_email, subject, html_body)


def send_email(grievance_id, status, rejection_reason=None):
    """Send approve/reject notification to citizen, including rejection reason if provided."""
    conn = sqlite3.connect(DB)
    cur  = conn.cursor()
    cur.execute("SELECT user_id, scheme FROM grievances WHERE id=?", (grievance_id,))
    grievance = cur.fetchone()
    cur.execute("SELECT name, email FROM users WHERE id=?", (grievance[0],))
    user = cur.fetchone()
    conn.close()

    name         = user[0]
    email        = user[1]
    scheme       = grievance[1]
    status_color = "#1b5e20" if status == "APPROVED" else "#b71c1c"
    status_text  = "APPROVED" if status == "APPROVED" else "REJECTED"
    status_icon  = "✅" if status == "APPROVED" else "❌"
    ref_no       = f"TN-ACK-{uuid.uuid4().hex[:6].upper()}"
    current_year = datetime.now().year

    reason_block = ""
    if status == "REJECTED" and rejection_reason:
        reason_block = f"""
        <div style="background:#fef2f2;border-left:4px solid #b71c1c;padding:15px 20px;
                    border-radius:8px;margin:15px 0;">
          <strong style="color:#991b1b;">Reason for Rejection:</strong>
          <p style="color:#7f1d1d;margin:8px 0 0;font-style:italic;">"{rejection_reason}"</p>
          <p style="color:#9f1239;font-size:12px;margin-top:8px;">
            Please address the above issue and re-apply or contact the support desk.
          </p>
        </div>
        """

    html_body = f"""
    <!DOCTYPE html><html><head><style>
      .ec{{font-family:'Segoe UI',Arial,sans-serif;line-height:1.6;color:#333;
           max-width:600px;margin:auto;border:1px solid #eee;border-radius:10px;overflow:hidden;}}
      .gh{{background:#003366;color:white;padding:25px;text-align:center;border-bottom:4px solid #FFD700;}}
      .ct{{padding:30px;background:#fff;}}
      .sb{{background:{status_color};color:white;padding:15px;text-align:center;
           border-radius:8px;font-weight:bold;font-size:18px;margin:20px 0;}}
      .dt{{width:100%;border-collapse:collapse;margin:20px 0;}}
      .dt td{{padding:10px;border-bottom:1px solid #f1f1f1;font-size:14px;}}
      .lb{{color:#666;font-weight:bold;width:40%;}}
      .ft{{background:#f8f9fa;padding:20px;text-align:center;font-size:12px;color:#777;border-top:1px solid #eee;}}
      .btn{{display:inline-block;padding:12px 25px;background:#003366;color:white!important;
            text-decoration:none;border-radius:50px;font-weight:bold;margin-top:20px;}}
    </style></head><body>
      <div class="ec">
        <div class="gh">
          <h2 style="margin:0;">தமிழ்நாடு அரசு</h2>
          <div style="font-size:14px;opacity:.8;">Government of Tamil Nadu</div>
        </div>
        <div class="ct">
          <p>வணக்கம் (Dear <strong>{name}</strong>),</p>
          <p>Your application has been processed by the department.</p>
          <div class="sb">{status_icon} APPLICATION {status_text}</div>
          {reason_block}
          <table class="dt">
            <tr><td class="lb">Reference ID</td><td>#{grievance_id}</td></tr>
            <tr><td class="lb">Scheme Name</td><td>{scheme}</td></tr>
            <tr><td class="lb">Decision Date</td><td>{datetime.now().strftime('%d %B, %Y')}</td></tr>
            <tr><td class="lb">Ack No.</td><td>{ref_no}</td></tr>
          </table>
          <p style="font-size:14px;">
            {"Please visit your local Taluk office with original documents." if status=="APPROVED"
             else "Please review the reason above or contact the support desk."}
          </p>
          <div style="text-align:center;">
            <a href="http://127.0.0.1:360/user/dashboard" class="btn">View in Dashboard</a>
          </div>
        </div>
        <div class="ft">
          <strong>Tamil Nadu e-Governance Agency (TNeGA)</strong><br>
          This is a system-generated notification. Please do not reply.<br>
          &copy; {current_year} Government of Tamil Nadu.
        </div>
      </div>
    </body></html>
    """
    _smtp_send(email, f"Update: Application #{grievance_id} — {status_text}", html_body)


def send_complaint_update_email(to_email, citizen_name, complaint_id,
                                 subject, new_status, gov_reply):
    """Notify citizen when admin updates their complaint status or replies."""
    status_color = {
        "Open":        "#64748b",
        "In Progress": "#1d4ed8",
        "Resolved":    "#1b5e20",
        "Closed":      "#374151",
    }.get(new_status, "#063970")

    reply_block = ""
    if gov_reply:
        reply_block = f"""
        <div style="background:#f0fdf4;border-left:4px solid #16a34a;padding:15px 20px;
                    border-radius:8px;margin:15px 0;">
          <strong style="color:#166534;">Official Government Response:</strong>
          <p style="color:#166534;margin:8px 0 0;">{gov_reply}</p>
        </div>
        """

    html_body = f"""
    <!DOCTYPE html><html>
    <body style="font-family:'Segoe UI',Arial,sans-serif;background:#f4f7f6;margin:0;padding:20px;">
      <div style="max-width:580px;margin:auto;background:white;border-radius:10px;
                  overflow:hidden;border:1px solid #ddd;">
        <div style="background:#003366;color:white;padding:25px;text-align:center;border-bottom:4px solid #FFD700;">
          <h2 style="margin:0;font-size:18px;">தமிழ்நாடு அரசு</h2>
          <p style="margin:5px 0 0;font-size:13px;opacity:.8;">Complaint Status Update</p>
        </div>
        <div style="padding:30px;">
          <p>Dear <strong>{citizen_name}</strong>,</p>
          <p>Your complaint <strong>#{complaint_id}: "{subject}"</strong> has been updated.</p>
          <div style="background:{status_color};color:white;padding:14px;border-radius:8px;
                      text-align:center;font-weight:bold;font-size:16px;margin:20px 0;">
            Status: {new_status}
          </div>
          {reply_block}
          <p style="font-size:13px;color:#555;">
            Log in to your dashboard to track further updates.
          </p>
        </div>
        <div style="background:#f8f9fa;padding:15px;text-align:center;font-size:11px;color:#777;border-top:1px solid #eee;">
          Tamil Nadu e-Governance Agency (TNeGA)<br>
          &copy; {datetime.now().year} Government of Tamil Nadu. All Rights Reserved.
        </div>
      </div>
    </body></html>
    """
    _smtp_send(to_email,
               f"Complaint #{complaint_id} Update — {new_status}",
               html_body)


def _send_aadhaar_otp_email(to_email, otp, aadhar):
    ref    = f"AADH-{uuid.uuid4().hex[:8].upper()}"
    masked = f"XXXX-XXXX-{aadhar[-4:]}"
    year   = datetime.now().year

    html = f"""
    <!DOCTYPE html><html>
    <body style="margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;background:#f4f7f6;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td align="center" style="padding:20px 0;">
        <table width="600" style="background:#fff;border:1px solid #ddd;border-radius:8px;overflow:hidden;">
          <tr style="background:#003366;">
            <td align="center" style="padding:25px;">
              <h1 style="color:#fff;margin:0;font-size:18px;">தமிழ்நாடு அரசு</h1>
              <h2 style="color:#FFD700;margin:5px 0 0;font-size:13px;font-weight:400;">Government of Tamil Nadu</h2>
            </td>
          </tr>
          <tr><td style="padding:35px 30px;">
            <p style="font-size:15px;color:#333;"><strong>Dear Citizen,</strong></p>
            <p style="color:#555;font-size:14px;line-height:1.6;">
              A request was made to verify Aadhaar <strong>{masked}</strong>.
              Use the OTP below — valid for <b>120 seconds</b>.
            </p>
            <div style="text-align:center;margin:30px 0;">
              <div style="background:#f9f9f9;border:2px dashed #003366;padding:20px;
                          display:inline-block;border-radius:10px;">
                <div style="font-size:10px;letter-spacing:2px;color:#888;margin-bottom:6px;">AADHAAR VERIFICATION OTP</div>
                <span style="font-size:34px;font-weight:bold;letter-spacing:10px;color:#003366;
                             font-family:'Courier New',monospace;">{otp}</span>
                <p style="font-size:10px;color:#aaa;margin-top:8px;">Ref: {ref}</p>
              </div>
            </div>
            <div style="background:#fff9e6;border-left:4px solid #FFD700;padding:12px;margin-bottom:20px;">
              <p style="font-size:12px;color:#444;margin:0;">
                <b>Security Notice:</b> Never share this OTP with anyone.
              </p>
            </div>
          </td></tr>
          <tr style="background:#003366;">
            <td style="padding:12px;color:#fff;font-size:9px;text-align:center;opacity:.7;">
              &copy; {year} Government of Tamil Nadu.
            </td>
          </tr>
        </table>
      </td></tr>
    </table>
    </body></html>
    """
    _smtp_send(to_email,
               f"Aadhaar Verification OTP — TN Citizen Portal [Ref: {ref}]",
               html)




def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    return [lemmatizer.lemmatize(w.lower()) for w in sentence_words]


def bag_of_words(sentence):
    sentence_words = clean_up_sentence(sentence)
    bag = [0] * len(words)
    for s in sentence_words:
        for i, w in enumerate(words):
            if w == s:
                bag[i] = 1
    return np.array(bag)


def predict_class(sentence):
    bow = bag_of_words(sentence)
    res = model.predict(np.array([bow]), verbose=0)[0]
    return classes[int(np.argmax(res))]




@app.route("/set_language/<lang>")
def set_language(lang):
    session["lang"] = lang
    return redirect(request.referrer or "/")


@app.route("/get_lang")
def get_lang():
    return jsonify({"lang": session.get("lang", "en")})


@app.route("/")
def home():
    if "lang" not in session:
        session["lang"] = "en"
    return render_template("index.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))




@app.route("/user/register", methods=["GET", "POST"])
def user_register():
    if request.method == "POST":
        name     = request.form["name"]
        email    = request.form["email"]
        password = request.form["password"]
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users(name,email,password) VALUES(?,?,?)",
                (name, email, password)
            )
            conn.commit()
            return redirect(url_for("user_login_page"))
        except Exception:
            msg = ("மின்னஞ்சல் ஏற்கனவே பதிவு செய்யப்பட்டுள்ளது!"
                   if session.get("lang") == "ta"
                   else "Email already registered!")
            return msg
        finally:
            conn.close()
    return render_template("register.html")


@app.route("/user/login")
def user_login_page():
    return render_template("login.html", otp_stage=False)


@app.route("/user/login/check", methods=["POST"])
def login_check():
    email    = request.form["email"]
    password = request.form["password"]
    district = request.form.get("district", "")
    lang     = session.get("lang", "en")

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email=? AND password=?", (email, password)
    ).fetchone()
    conn.close()

    if user:
        if user["status"] != "Approved":
            return ("உங்கள் கணக்கு இன்னும் அங்கீகரிக்கப்படவில்லை!"
                    if lang == "ta"
                    else "Account not approved yet!")

        otp = str(random.randint(100000, 999999))
        session.update({
            "otp":       otp,
            "otp_time":  time.time(),
            "district":  district,
            "temp_user": user["id"],
            "temp_name": user["name"],
            "otp_email": email
        })
        send_otp_email(email, otp)
        print(f"[OTP] {otp}")
        return render_template("login.html", otp_stage=True, email=email)

    return ("தவறான மின்னஞ்சல் அல்லது கடவுச்சொல்"
            if lang == "ta"
            else "Invalid Email or Password")


@app.route("/user/verify_otp", methods=["POST"])
def verify_otp():
    entered_otp = request.form["otp"]
    if time.time() - session.get("otp_time", 0) > 100:
        session.clear()
        return "OTP Expired! Login again."

    if entered_otp == session.get("otp"):
        session["user_id"]   = session["temp_user"]
        session["user_name"] = session["temp_name"]
        session.pop("otp", None)
        session.pop("temp_user", None)
        session.pop("otp_time", None)
        return redirect(url_for("user_dashboard"))

    return render_template("login.html", otp_stage=True, error="Wrong OTP")




@app.route("/user/dashboard")
def user_dashboard():
    if "user_id" not in session:
        return redirect(url_for("home"))

    conn = get_db()
    uid  = session["user_id"]

    # Grievance stats
    grievance_rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM grievances WHERE user_id=? GROUP BY status",
        (uid,)
    ).fetchall()
    g_stats = {r["status"]: r["cnt"] for r in grievance_rows}

    complaint_rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM complaints WHERE user_id=? GROUP BY status",
        (uid,)
    ).fetchall()
    c_stats = {r["status"]: r["cnt"] for r in complaint_rows}
    recent_complaints = conn.execute(
        "SELECT * FROM complaints WHERE user_id=? ORDER BY id DESC LIMIT 3",
        (uid,)
    ).fetchall()

    unread_replies = conn.execute(
        """SELECT COUNT(*) FROM complaints
           WHERE user_id=? AND gov_reply IS NOT NULL
           AND gov_reply != '' AND status != 'Closed'""",
        (uid,)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "user_dashboard.html",
        name=session["user_name"],
        district=session.get("district", "Not Set"),
        g_stats=g_stats,
        c_stats=c_stats,
        recent_complaints=recent_complaints,
        unread_replies=unread_replies,
    )


# ════════════════════════════════════════════════════════════
#  USER PROFILE
# ════════════════════════════════════════════════════════════

##@app.route("/profile/update", methods=["POST"])
##def profile_update():
##    if "user_id" not in session:
##        return redirect(url_for("home"))
##
##    name     = request.form.get("name", "").strip()
##    mobile   = request.form.get("mobile", "").strip()
##    district = request.form.get("district", "").strip()
##    password = request.form.get("password", "").strip()
##
##    if mobile and not re.match(r"^\d{10}$", mobile):
##        flash("Invalid mobile number — must be exactly 10 digits.", "danger")
##        return redirect(url_for("profile_page"))
##
##    conn = get_db()
##    if password:
##        conn.execute(
##            "UPDATE users SET name=?,mobile=?,district=?,password=? WHERE id=?",
##            (name, mobile, district, password, session["user_id"])
##        )
##    else:
##        conn.execute(
##            "UPDATE users SET name=?,mobile=?,district=? WHERE id=?",
##            (name, mobile, district, session["user_id"])
##        )
##    conn.commit()
##    conn.close()
##    session["user_name"] = name
##    flash("Profile updated successfully!", "success")
##    return redirect(url_for("profile_page"))


##@app.route("/profile/send_aadhaar_otp", methods=["POST"])
##def send_aadhaar_otp():
##    if "user_id" not in session:
##        return jsonify({"success": False, "error": "Not logged in"}), 401
##
##    data   = request.get_json(silent=True) or {}
##    aadhar = str(data.get("aadhar", "")).strip()
##
##    if not re.match(r"^\d{12}$", aadhar):
##        return jsonify({"success": False, "error": "Invalid Aadhaar number"})
##
##    conn = get_db()
##    existing = conn.execute(
##        "SELECT id FROM users WHERE aadhar=? AND aadhar_verified=1 AND id!=?",
##        (aadhar, session["user_id"])
##    ).fetchone()
##    user = conn.execute(
##        "SELECT email FROM users WHERE id=?", (session["user_id"],)
##    ).fetchone()
##    conn.close()
##
##    if existing:
##        return jsonify({"success": False,
##                        "error": "This Aadhaar is already verified with another account."})
##
##    otp = str(random.randint(100000, 999999))
##    session["aadhaar_otp"]      = otp
##    session["aadhaar_otp_time"] = time.time()
##    session["aadhaar_pending"]  = aadhar
##    _send_aadhaar_otp_email(user["email"], otp, aadhar)
##    print(f"[AADHAAR OTP] {otp}")
##    return jsonify({"success": True})


##@app.route("/profile/verify_aadhaar_otp", methods=["POST"])
##def verify_aadhaar_otp():
##    if "user_id" not in session:
##        return redirect(url_for("home"))
##
##    entered  = request.form.get("otp", "").strip()
##    aadhar   = request.form.get("aadhar", "").strip()
##    stored   = session.get("aadhaar_otp")
##    otp_time = session.get("aadhaar_otp_time", 0)
##
##    if time.time() - otp_time > 120:
##        session.pop("aadhaar_otp", None)
##        session.pop("aadhaar_pending", None)
##        flash("OTP expired. Please try again.", "danger")
##        return redirect(url_for("profile_page"))
##
##    if entered != stored:
##        flash("Incorrect OTP. Please try again.", "danger")
##        return redirect(url_for("profile_page"))
##
##    verified_at = datetime.now().strftime("%d-%m-%Y %I:%M %p")
##    conn = get_db()
##    conn.execute(
##        "UPDATE users SET aadhar=?,aadhar_verified=1,aadhar_verified_at=? WHERE id=?",
##        (aadhar, verified_at, session["user_id"])
##    )
##    conn.commit()
##    conn.close()
##
##    session.pop("aadhaar_otp",      None)
##    session.pop("aadhaar_otp_time", None)
##    session.pop("aadhaar_pending",  None)
##
##    flash("Aadhaar verified successfully! ✓", "success")
##    return redirect(url_for("profile_page"))


# ════════════════════════════════════════════════════════════
#  LOCATION / DISTRICT
# ════════════════════════════════════════════════════════════

@app.route("/get_district")
def get_district():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
    try:
        r    = requests.get(url, headers={"User-Agent": "CitizenPortal/1.0"})
        data = r.json()
        addr = data.get("address", {})
        district = (addr.get("state_district")
                    or addr.get("county")
                    or addr.get("city") or "")
        district = district.replace(" district", "").replace(" District", "")
    except Exception:
        district = ""
    return {"district": district}


@app.route("/get_constituencies", methods=["POST"])
def get_constituencies():
    district_name = request.json.get("district")
    district_info = tn_data.get(district_name, {})
    taluks = [t['name'] for t in district_info.get('taluks', []) if 'name' in t]
    return jsonify(taluks)


@app.route("/get_schemes", methods=["POST"])
def get_schemes():
    district_name = request.json.get("district")
    district_info = tn_data.get(district_name, {})
    schemes = district_info.get('services_facilities', [])
    return jsonify(schemes)


# ════════════════════════════════════════════════════════════
#  GRIEVANCE (SCHEME APPLICATION)
# ════════════════════════════════════════════════════════════

@app.route("/apply_grievance")
def apply_grievance():
    if "user_id" not in session:
        return redirect(url_for("home"))

    with open("tn_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    district_taluk = {
        d: list(details["constituencies"].keys())
        for d, details in data.items()
    }

    conn = get_db()
    user = conn.execute(
        "SELECT geo_district FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    # 🔥 IMPORTANT: normalize value
    user_district = (user["geo_district"].strip() if user and user["geo_district"] else "")

    return render_template(
        "apply_grievance.html",
        data=district_taluk,
        user_district=user_district,
        lat=session.get("latitude"),
        lon=session.get("longitude")
    )

@app.route("/apply_form")
def apply_form():
    if "user_id" not in session:
        return redirect(url_for("home"))
    return render_template(
        "apply_form.html",
        district=request.args.get("district"),
        constituency=request.args.get("constituency"),
        scheme=request.args.get("scheme"),
        error=None
    )


@app.route("/submit_grievance", methods=["POST"])
def submit_grievance():
    if "user_id" not in session:
        return redirect(url_for("home"))
    
    # 1. Collect form data
    name = session.get("user_name", "Unknown")
    aadhar_val = request.form.get("aadhar", "").strip() 
    mobile = request.form.get("mobile", "").strip()
    address = request.form.get("address", "").strip()
    reason = request.form.get("reason", "").strip()
    district = request.form.get("district", "").strip()
    constituency = request.form.get("constituency", "").strip()
    scheme_id = request.form.get("scheme", "").strip()
    
    conn = get_db()
    
    # 2. Check for duplicates
    existing = conn.execute(
        "SELECT id FROM grievances WHERE aadhar=? AND scheme=?",
        (aadhar_val, scheme_id)
    ).fetchone()
    
    if existing:
        conn.close()
        lang = session.get("lang", "en")
        error_msg = (
            "இந்த அடையாள எண்ணுடன் ஏற்கனவே விண்ணப்பிக்கப்பட்டுள்ளது!" if lang == "ta"
            else "An application already exists for this ID and scheme."
        )
        return render_template("apply_form.html", error=error_msg)
    
    # 3. Process all Document Uploads with METADATA
    documents_metadata = []
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    # Get all uploaded files in order (doc_0, doc_1, etc.)
    uploaded_keys = sorted(
        [k for k in request.files.keys() if k.startswith('doc_')],
        key=lambda x: int(x.split('_')[1])
    )
    
    print(f"Found {len(uploaded_keys)} file upload fields")
    
    for key in uploaded_keys:
        file = request.files[key]
        if file and file.filename != "":
            # Create unique filename
            original_name = secure_filename(file.filename)
            file_ext = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else 'pdf'
            doc_index = key.split('_')[1]
            unique_name = f"scheme{scheme_id}_doc{doc_index}_{timestamp}.{file_ext}"
            
            # Save physical file
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(file_path)
            
            # Store metadata
            documents_metadata.append({
                "index": doc_index,
                "filename": unique_name,
                "original_name": original_name,
                "uploaded_at": timestamp,
                "size": os.path.getsize(file_path)
            })
            
            print(f"Saved: {unique_name} ({os.path.getsize(file_path)} bytes)")
    
    # 4. Store as JSON for better structure
    documents_json = json.dumps(documents_metadata)
    
    # 5. Insert into Database
    applied_time = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    
    try:
        conn.execute("""
            INSERT INTO grievances
            (user_id, name, aadhar, mobile, address, reason,
             district, constituency, scheme, photo, applied_at, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (session["user_id"], name, aadhar_val, mobile, address, reason,
              district, constituency, scheme_id, documents_json, applied_time, 'Pending'))
        conn.commit()
        
        # Log successful submission
        print(f"✅ Application submitted: User {session['user_id']}, Scheme {scheme_id}, {len(documents_metadata)} documents")
        
    except Exception as e:
        print(f"❌ Error saving to database: {e}")
        conn.close()
        return render_template("apply_form.html", error="Database error occurred. Please try again.")
    finally:
        conn.close()
    
    # 6. Success Response
    lang = session.get("lang", "en")
    t = {
        "application_submitted": "Application Submitted" if lang == "en" else "விண்ணப்பம் சமர்ப்பிக்கப்பட்டது",
        "documents_uploaded": f"{len(documents_metadata)} documents uploaded successfully"
    }
    return render_template("submit_success.html", t=t, doc_count=len(documents_metadata))

@app.route("/view_documents/<int:grievance_id>")
def view_documents(grievance_id):
    if "user_id" not in session:
        return redirect(url_for("home"))
    
    conn = get_db()
    grievance = conn.execute(
        "SELECT * FROM grievances WHERE id=?", (grievance_id,)
    ).fetchone()
    conn.close()
    
    if not grievance:
        return "Application not found", 404
    
    # Parse documents JSON
    try:
        documents = json.loads(grievance["photo"])
    except:
        documents = []
    
    return render_template("view_documents.html", 
                         grievance=grievance, 
                         documents=documents)





@app.route("/my_grievances")
def my_grievances():
    if "user_id" not in session:
        return redirect(url_for("home"))

    conn = get_db()
    grievances = conn.execute(
        "SELECT * FROM grievances WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    lang = session.get("lang", "en")
    t = {
        "track_title": "எனது விண்ணப்பங்கள்" if lang == "ta" else "My Applications",
        "status":      "நிலை"               if lang == "ta" else "Status",
        "date":        "தேதி"               if lang == "ta" else "Date",
        "scheme":      "திட்டம்"            if lang == "ta" else "Scheme",
        "no_data":     "விண்ணப்பங்கள் எதுவும் இல்லை."
                       if lang == "ta" else "No applications found."
    }
    return render_template("my_grievances.html", grievances=grievances, t=t)


@app.route("/grievance_details/<int:gid>")
def grievance_details(gid):
    if "user_id" not in session:
        return redirect(url_for("home"))

    conn = get_db()
    grievance = conn.execute(
        "SELECT * FROM grievances WHERE id=? AND user_id=?",
        (gid, session["user_id"])
    ).fetchone()
    conn.close()

    if not grievance:
        return "Grievance Not Found", 404

    lang = session.get("lang", "en")
    t = {
        "title":  "விண்ணப்ப விவரங்கள்"  if lang == "ta" else "Application Details",
        "back":   "பின்செல்"             if lang == "ta" else "Back",
        "step1":  "விண்ணப்பிக்கப்பட்டது" if lang == "ta" else "Submitted",
        "step2":  "அதிகாரியின் பார்வை"   if lang == "ta" else "Under Review",
        "step3":  "முடிவு"               if lang == "ta" else "Final Decision",
        "reason": "விண்ணப்ப காரணம்"      if lang == "ta" else "Application Reason"
    }
    return render_template("grievance_details.html", g=grievance, t=t)


# ════════════════════════════════════════════════════════════
#  COMPLAINT SYSTEM
# ════════════════════════════════════════════════════════════

@app.route("/raise_complaint", methods=["GET"])
def raise_complaint():
    if "user_id" not in session:
        return redirect(url_for("home"))
    return render_template("raise_complaint.html")


@app.route("/submit_complaint", methods=["POST"])
def submit_complaint():
    if "user_id" not in session:
        return redirect(url_for("home"))

    category    = request.form.get("category", "").strip()
    priority    = request.form.get("priority", "Medium").strip()
    subject     = request.form.get("subject", "").strip()
    description = request.form.get("description", "").strip()
    location    = request.form.get("location", "").strip()

    if not all([category, priority, subject, description, location]):
        return render_template("raise_complaint.html",
                               error="Please fill all required fields.")

    file     = request.files.get("photo")
    filename = ""
    if file and file.filename != "":
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    conn = get_db()
    conn.execute("""
        INSERT INTO complaints
        (user_id, citizen_name, category, priority, subject,
         description, location, photo, submitted_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (session["user_id"], session.get("user_name", ""),
          category, priority, subject, description, location,
          filename, datetime.now().strftime("%d-%m-%Y %I:%M %p")))
    conn.commit()
    conn.close()

    return redirect(url_for("my_complaints"))


@app.route("/my_complaints")
def my_complaints():
    if "user_id" not in session:
        return redirect(url_for("home"))

    conn = get_db()
    complaints = conn.execute(
        "SELECT * FROM complaints WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("my_complaints.html", complaints=complaints)


# ════════════════════════════════════════════════════════════
#  CHATBOT
# ════════════════════════════════════════════════════════════

@app.route("/chatbot", methods=["POST"])
def chatbot():
    data         = request.get_json()
    user_message = data.get("message", "")
    target_lang  = data.get("lang") or session.get("lang", "en")

    english_input = user_message
    if target_lang != "en":
        try:
            english_input = translate_text(user_message, source=target_lang, target='en')
        except Exception:
            pass

    tag = predict_class(english_input)
    response_english = "I'm sorry, I don't understand."
    for intent in intents_data["intents"]:
        if intent["tag"] == tag:
            response_english = random.choice(intent["responses"])
            break

    final_reply = response_english
    if target_lang != "en":
        try:
            final_reply = translate_text(response_english, source='en', target=target_lang)
        except Exception:
            pass

    return jsonify({"reply": final_reply})


### ════════════════════════════════════════════════════════════
###  RECOMMENDATIONS
### ════════════════════════════════════════════════════════════
##
##@app.route("/recommendations")
##def recommendations():
##    if "user_id" not in session:
##        return redirect(url_for("home"))
##    return render_template("recommendations.html")
##

# ════════════════════════════════════════════════════════════
#  ADMIN AUTH
# ════════════════════════════════════════════════════════════

@app.route("/admin")
def admin():
    return render_template("admin_login.html")


@app.route("/admin/login", methods=["POST"])
def admin_login():
    username = request.form["username"]
    password = request.form["password"]
    conn  = get_db()
    admin = conn.execute(
        "SELECT * FROM admins WHERE username=? AND password=?",
        (username, password)
    ).fetchone()
    conn.close()

    if admin:
        session["admin"] = username
        return redirect(url_for("admin_dashboard"))
    return "Wrong Admin Credentials"


# ════════════════════════════════════════════════════════════
#  ADMIN DASHBOARD
# ════════════════════════════════════════════════════════════

@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("home"))

    conn = get_db()

    # ── Charts data ──────────────────────────────────────────
    status_data       = conn.execute("SELECT status, COUNT(*) as count FROM grievances GROUP BY status").fetchall()
    district_data     = conn.execute("SELECT district, COUNT(*) as count FROM grievances GROUP BY district LIMIT 10").fetchall()
    trend_data        = conn.execute("SELECT substr(applied_at,4,7) as month, COUNT(*) as count FROM grievances GROUP BY month ORDER BY month DESC LIMIT 6").fetchall()
    user_status       = conn.execute("SELECT status, COUNT(*) as count FROM users GROUP BY status").fetchall()
    scheme_data       = conn.execute("SELECT scheme, COUNT(*) as count FROM grievances GROUP BY scheme ORDER BY count DESC LIMIT 5").fetchall()
    constituency_data = conn.execute("SELECT district, COUNT(DISTINCT constituency) as count FROM grievances GROUP BY district LIMIT 6").fetchall()

    # Complaint charts
    complaint_status_data   = conn.execute("SELECT status, COUNT(*) as count FROM complaints GROUP BY status").fetchall()
    complaint_category_data = conn.execute("SELECT category, COUNT(*) as count FROM complaints GROUP BY category ORDER BY count DESC LIMIT 6").fetchall()

    # ── Summary counts ───────────────────────────────────────
    total_users        = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_grievances   = conn.execute("SELECT COUNT(*) FROM grievances").fetchone()[0]
    total_complaints   = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    pending_users      = conn.execute("SELECT COUNT(*) FROM users WHERE status='Pending'").fetchone()[0]
    pending_grievances = conn.execute("SELECT COUNT(*) FROM grievances WHERE status='Pending'").fetchone()[0]
    open_complaints    = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Open'").fetchone()[0]
    in_progress_complaints = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'").fetchone()[0]
    approved_grievances    = conn.execute("SELECT COUNT(*) FROM grievances WHERE status='Approved'").fetchone()[0]
    rejected_grievances    = conn.execute("SELECT COUNT(*) FROM grievances WHERE status='Rejected'").fetchone()[0]

    # ── Recent activity feeds ────────────────────────────────
    recent_grievances  = conn.execute(
        "SELECT * FROM grievances ORDER BY id DESC LIMIT 5"
    ).fetchall()
    recent_complaints  = conn.execute(
        "SELECT * FROM complaints ORDER BY id DESC LIMIT 5"
    ).fetchall()

    conn.close()

    translations = {
        "Admin Dashboard":        {"ta": "நிர்வாகத் டாஷ்போர்டு"},
        "Official Control Panel": {"ta": "அதிகாரப்பூர்வ கட்டுப்பாட்டு மையம்"},
        "Active":                 {"ta": "செயலில் உள்ளது"},
        "Pending Tasks":          {"ta": "நிலுவையில் உள்ள பணிகள்"},
    }

    def t(text):
        if session.get('lang') == 'ta':
            return translations.get(text, {}).get('ta', text)
        return text

    return render_template(
        "admin_dashboard.html",
        t=t,
        # charts
        status_data=status_data,
        district_data=district_data,
        trend_data=trend_data,
        user_status=user_status,
        scheme_data=scheme_data,
        constituency_data=constituency_data,
        complaint_status_data=complaint_status_data,
        complaint_category_data=complaint_category_data,
        # summary counts
        total_users=total_users,
        total_grievances=total_grievances,
        total_complaints=total_complaints,
        pending_users=pending_users,
        pending_grievances=pending_grievances,
        open_complaints=open_complaints,
        in_progress_complaints=in_progress_complaints,
        approved_grievances=approved_grievances,
        rejected_grievances=rejected_grievances,
        # feeds
        recent_grievances=recent_grievances,
        recent_complaints=recent_complaints,
    )


# ════════════════════════════════════════════════════════════
#  ADMIN — USER MANAGEMENT
# ════════════════════════════════════════════════════════════

@app.route("/admin/users")
def admin_users():
    if "admin" not in session:
        return redirect(url_for("home"))
    conn  = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template("admin_users.html", users=users)


@app.route("/admin/user/<int:uid>")
def user_details(uid):
    if "admin" not in session:
        return redirect(url_for("home"))
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return render_template("user_details.html", user=user)


@app.route("/admin/approve_user/<int:uid>", methods=["POST"])
def approve_user(uid):
    if "admin" not in session:
        return redirect(url_for("home"))
    conn = get_db()
    conn.execute("UPDATE users SET status='Approved' WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    return redirect(url_for("user_details", uid=uid))


@app.route("/admin/reject_user/<int:uid>", methods=["POST"])
def reject_user(uid):
    if "admin" not in session:
        return redirect(url_for("home"))
    conn = get_db()
    conn.execute("UPDATE users SET status='Rejected' WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    return redirect(url_for("user_details", uid=uid))


# ════════════════════════════════════════════════════════════
#  ADMIN — GRIEVANCE MANAGEMENT
# ════════════════════════════════════════════════════════════

@app.route("/admin/grievances")
def admin_grievances():
    if "admin" not in session:
        return redirect(url_for("home"))

    conn      = get_db()
    view_time = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    # Mark all unviewed grievances as viewed now
    conn.execute(
        "UPDATE grievances SET viewed_at=? WHERE viewed_at IS NULL",
        (view_time,)
    )
    conn.commit()

    grievances = conn.execute(
        "SELECT * FROM grievances ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template("admin_grievances.html", grievances=grievances)


@app.route("/admin/approve/<int:id>", methods=["POST"])
def approve_grievance(id):
    if "admin" not in session:
        return redirect(url_for("home"))

    action_time = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    conn = get_db()
    conn.execute(
        "UPDATE grievances SET status='Approved', action_at=? WHERE id=?",
        (action_time, id)
    )
    conn.commit()
    conn.close()
    send_email(id, "APPROVED")
    return redirect("/admin/grievances")


def migrate_users_table(conn):
    new_cols = [
        ("mobile",             "TEXT"),
        ("aadhar",             "TEXT"),
        ("aadhar_verified",    "INTEGER DEFAULT 0"),
        ("aadhar_verified_at", "TEXT"),
    ]
    for col, col_type in new_cols:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
        except Exception:
            pass   # Column already exists — safe to ignore


# ── 1. PROFILE PAGE (GET) ───────────────────────────────────────────
@app.route("/profile")
def profile_page():
    if "user_id" not in session:
        return redirect(url_for("home"))

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()

    if not user:
        return redirect(url_for("home"))

    return render_template("update_profile.html", user=user)
##

# ── 2. PROFILE UPDATE (POST) ────────────────────────────────────────
@app.route("/profile/update", methods=["POST"])
def profile_update():
    if "user_id" not in session:
        return redirect(url_for("home"))

    import re

    # ── Basic ────────────────────────────────────────────────
    name     = request.form.get("name",     "").strip()
    mobile   = request.form.get("mobile",   "").strip()
    dob      = request.form.get("dob",      "").strip() or None
    gender   = request.form.get("gender",   "").strip() or None
    password = request.form.get("password", "").strip()

    # ── Location ─────────────────────────────────────────────
    district     = request.form.get("district",    "").strip() or None
    rural_urban  = request.form.get("rural_urban", "").strip() or None
    village_city = request.form.get("village_city","").strip() or None

    # ── Economic ─────────────────────────────────────────────
    annual_income = request.form.get("annual_income","").strip() or None
    bpl_apl       = request.form.get("bpl_apl",      "").strip() or None
    ration_card   = request.form.get("ration_card",  "").strip() or None

    # ── Education ────────────────────────────────────────────
    education          = request.form.get("education",          "").strip() or None
    currently_studying = request.form.get("currently_studying", "").strip() or None
    study_type         = request.form.get("study_type",         "").strip() or None

    # ── Employment ───────────────────────────────────────────
    employment_status = request.form.get("employment_status","").strip() or None
    occupation        = request.form.get("occupation",       "").strip() or None

    # ── Special categories ───────────────────────────────────
    caste_category      = request.form.get("caste_category",      "").strip() or None
    disability          = request.form.get("disability",          "").strip() or None
    widow_single_parent = request.form.get("widow_single_parent", "").strip() or None
    is_farmer           = request.form.get("is_farmer",           "").strip() or None
    land_ownership      = request.form.get("land_ownership",      "").strip() or None
    land_acres          = request.form.get("land_acres",          "").strip() or None
    minority            = request.form.get("minority",            "").strip() or None
    latitude = request.form.get("latitude", "").strip() or None
    longitude = request.form.get("longitude", "").strip() or None
    geo_district = request.form.get("geo_district", "").strip() or None

    # ── Validation ───────────────────────────────────────────
    if mobile and not re.match(r"^\d{10}$", mobile):
        flash("Invalid mobile number — must be exactly 10 digits.", "danger")
        return redirect(url_for("profile_page"))

    if gender and gender not in ("Male", "Female", "Other"):
        flash("Invalid gender value.", "danger")
        return redirect(url_for("profile_page"))

    if land_acres:
        try:
            float(land_acres)
        except ValueError:
            flash("Land acres must be a number.", "danger")
            return redirect(url_for("profile_page"))

    # ── Persist ──────────────────────────────────────────────
    conn = get_db()
    sql = """
        UPDATE users SET
            name=?, mobile=?, dob=?, gender=?,
            district=?, rural_urban=?, village_city=?,
            annual_income=?, bpl_apl=?, ration_card=?,
            education=?, currently_studying=?, study_type=?,
            employment_status=?, occupation=?,
            caste_category=?, disability=?, widow_single_parent=?,
            is_farmer=?, land_ownership=?, land_acres=?, minority=?
            {pwd_clause}
        WHERE id=?
    """
    if password:
        sql = sql.replace("{pwd_clause}", ", password=?")
        params = (
            name, mobile, dob, gender,
            district, rural_urban, village_city,
            annual_income, bpl_apl, ration_card,
            education, currently_studying, study_type,
            employment_status, occupation,
            caste_category, disability, widow_single_parent,
            is_farmer, land_ownership, land_acres, minority,
            password, session["user_id"]
        )
    else:
        sql = sql.replace("{pwd_clause}", "")
        params = (
            name, mobile, dob, gender,
            district, rural_urban, village_city,
            annual_income, bpl_apl, ration_card,
            education, currently_studying, study_type,
            employment_status, occupation,
            caste_category, disability, widow_single_parent,
            is_farmer, land_ownership, land_acres, minority,
            session["user_id"]
        )
    conn.execute(sql, params)
    conn.commit()
    conn.close()

    session["user_name"] = name
    flash("Profile updated successfully!", "success")
    return redirect(url_for("profile_page"))

@app.route("/update_location", methods=["POST"])
def update_location():
    if "user_id" not in session:
        return jsonify({"status": "error"})

    data = request.get_json()

    lat = data.get("lat")
    lon = data.get("lon")
    district = data.get("district")

    conn = get_db()
    conn.execute("""
        UPDATE users
        SET latitude=?, longitude=?, geo_district=?
        WHERE id=?
    """, (lat, lon, district, session["user_id"]))
    conn.commit()
    conn.close()

    return jsonify({"status": "saved"})


# ── 3. SEND AADHAAR OTP (JSON endpoint) ─────────────────────────────
@app.route("/profile/send_aadhaar_otp", methods=["POST"])
def send_aadhaar_otp():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    data   = request.get_json(silent=True) or {}
    aadhar = str(data.get("aadhar", "")).strip()

    import re
    if not re.match(r"^\d{12}$", aadhar):
        return jsonify({"success": False, "error": "Invalid Aadhaar number"})

    # Check no other account is already verified with this Aadhaar
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM users WHERE aadhar=? AND aadhar_verified=1 AND id!=?",
        (aadhar, session["user_id"])
    ).fetchone()
    user = conn.execute("SELECT email FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()

    if existing:
        return jsonify({"success": False, "error": "This Aadhaar is already verified with another account."})

    # Generate & store OTP in session
    otp = str(random.randint(100000, 999999))
    session["aadhaar_otp"]        = otp
    session["aadhaar_otp_time"]   = time.time()
    session["aadhaar_pending"]    = aadhar

    # Send OTP email
    _send_aadhaar_otp_email(user["email"], otp, aadhar)
    print(f"[AADHAAR OTP] {otp}")   # dev console fallback

    return jsonify({"success": True})


def _send_aadhaar_otp_email(to_email, otp, aadhar):
    """Send a government-styled Aadhaar verification OTP email."""
    import uuid as _uuid
    from datetime import datetime as _dt
    from email.mime.multipart import MIMEMultipart as _MIME
    from email.mime.text import MIMEText as _MText

    ref = f"AADH-{_uuid.uuid4().hex[:8].upper()}"
    masked = f"XXXX-XXXX-{aadhar[-4:]}"
    year = _dt.now().year

    html = f"""
    <!DOCTYPE html><html><body style="margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;background:#f4f7f6;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td align="center" style="padding:20px 0;">
        <table width="600" style="background:#fff;border:1px solid #ddd;border-radius:8px;overflow:hidden;">
          <tr style="background:#003366;">
            <td align="center" style="padding:25px;">
              <h1 style="color:#fff;margin:0;font-size:18px;">தமிழ்நாடு அரசு</h1>
              <h2 style="color:#FFD700;margin:5px 0 0;font-size:13px;font-weight:400;">Government of Tamil Nadu</h2>
            </td>
          </tr>
          <tr><td style="padding:35px 30px;">
            <p style="font-size:15px;color:#333;"><strong>Dear Citizen,</strong></p>
            <p style="color:#555;font-size:14px;line-height:1.6;">
              A request was made to verify Aadhaar <strong>{masked}</strong> on the
              Citizen Welfare Portal. Use the OTP below — valid for <b>120 seconds</b>.
            </p>
            <div style="text-align:center;margin:30px 0;">
              <div style="background:#f9f9f9;border:2px dashed #003366;padding:20px;display:inline-block;border-radius:10px;">
                <div style="font-size:10px;letter-spacing:2px;color:#888;margin-bottom:6px;">AADHAAR VERIFICATION OTP</div>
                <span style="font-size:34px;font-weight:bold;letter-spacing:10px;color:#003366;font-family:'Courier New',monospace;">{otp}</span>
                <p style="font-size:10px;color:#aaa;margin-top:8px;">Ref: {ref}</p>
              </div>
            </div>
            <div style="background:#fff9e6;border-left:4px solid #FFD700;padding:12px;margin-bottom:20px;">
              <p style="font-size:12px;color:#444;margin:0;"><b>Security Notice:</b> Never share this OTP with anyone. Government officials will never ask for your OTP.</p>
            </div>
          </td></tr>
          <tr style="background:#003366;"><td style="padding:12px;color:#fff;font-size:9px;text-align:center;opacity:.7;">
            &copy; {year} Government of Tamil Nadu. This is an automated message — do not reply.
          </td></tr>
        </table>
      </td></tr>
    </table>
    </body></html>
    """

    try:
        msg = _MIME("alternative")
        msg["Subject"] = f"Aadhaar Verification OTP — TN Citizen Portal [Ref: {ref}]"
        msg["From"]    = f"TN Citizen Portal <{SENDER_EMAIL}>"
        msg["To"]      = to_email
        msg.attach(_MText(f"Your Aadhaar OTP is {otp}. Ref: {ref}", "plain"))
        msg.attach(_MText(html, "html"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("Aadhaar OTP mail error:", e)
        return False


# ── 4. VERIFY AADHAAR OTP (POST form) ───────────────────────────────
@app.route("/profile/verify_aadhaar_otp", methods=["POST"])
def verify_aadhaar_otp():
    if "user_id" not in session:
        return redirect(url_for("home"))

    from flask import flash

    entered  = request.form.get("otp", "").strip()
    aadhar   = request.form.get("aadhar", "").strip()
    stored   = session.get("aadhaar_otp")
    otp_time = session.get("aadhaar_otp_time", 0)

    # ── Expiry check (120 seconds) ──
    if time.time() - otp_time > 120:
        session.pop("aadhaar_otp", None)
        session.pop("aadhaar_pending", None)
        flash("OTP expired. Please try again.", "danger")
        return redirect(url_for("profile_page"))

    # ── OTP match check ──
    if entered != stored:
        flash("Incorrect OTP. Please try again.", "danger")
        return redirect(url_for("profile_page"))

    # ── All good — mark as verified ──
    from datetime import datetime
    verified_at = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    conn = get_db()
    conn.execute(
        "UPDATE users SET aadhar=?, aadhar_verified=1, aadhar_verified_at=? WHERE id=?",
        (aadhar, verified_at, session["user_id"])
    )
    conn.commit()
    conn.close()

    # Clean up session keys
    session.pop("aadhaar_otp",      None)
    session.pop("aadhaar_otp_time", None)
    session.pop("aadhaar_pending",  None)

    flash("Aadhaar verified successfully! ✓", "success")
    return redirect(url_for("profile_page"))

@app.route("/recommendations")
def recommendations():
    if "user_id" not in session:
        return redirect(url_for("home"))
    return render_template("recommendations.html")

@app.route("/admin/reject/<int:id>", methods=["POST"])
def reject_grievance(id):
    if "admin" not in session:
        return redirect(url_for("home"))

    rejection_reason = request.form.get("rejection_reason", "").strip()
    action_time      = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    conn = get_db()
    conn.execute(
        "UPDATE grievances SET status='Rejected', action_at=?, rejection_reason=? WHERE id=?",
        (action_time, rejection_reason, id)
    )
    conn.commit()
    conn.close()
    send_email(id, "REJECTED", rejection_reason=rejection_reason)
    return redirect("/admin/grievances")


# ════════════════════════════════════════════════════════════
#  ADMIN — COMPLAINT MANAGEMENT
# ════════════════════════════════════════════════════════════

@app.route("/admin/complaints")
def admin_complaints():
    if "admin" not in session:
        return redirect(url_for("home"))

    conn       = get_db()
    complaints = conn.execute(
        "SELECT * FROM complaints ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return render_template("admin_complaints.html", complaints=complaints)


@app.route("/admin/update_complaint/<int:cid>", methods=["POST"])
def update_complaint(cid):
    if "admin" not in session:
        return redirect(url_for("home"))

    new_status = request.form.get("status", "Open")
    gov_reply  = request.form.get("gov_reply", "").strip()
    updated_at = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    conn = get_db()
    conn.execute(
        "UPDATE complaints SET status=?, gov_reply=?, updated_at=? WHERE id=?",
        (new_status, gov_reply, updated_at, cid)
    )
    conn.commit()

    # Notify citizen via email
    complaint = conn.execute(
        "SELECT * FROM complaints WHERE id=?", (cid,)
    ).fetchone()
    if complaint:
        user = conn.execute(
            "SELECT email, name FROM users WHERE id=?",
            (complaint["user_id"],)
        ).fetchone()
        if user:
            send_complaint_update_email(
                to_email=user["email"],
                citizen_name=user["name"],
                complaint_id=cid,
                subject=complaint["subject"],
                new_status=new_status,
                gov_reply=gov_reply
            )
    conn.close()
    return redirect(url_for("admin_complaints"))


# ════════════════════════════════════════════════════════════
#  RUN
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run()
