from flask import Flask, jsonify, request, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import os
import random
import string
import re
import shutil
import math
import json

# ============================================================
# FINASSIST - FLASK BACKEND
# ============================================================

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "special_project.db"

app.secret_key = os.environ.get(
    "SPECIAL_PROJECT_SECRET_KEY",
    "local-finassist-development-key-change-before-deployment"
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)
)


# ============================================================
# 1. DATABASE CONNECTION AND SCHEMA HELPERS
# ============================================================

def get_db_connection():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def table_columns(db, table_name):
    return {
        row["name"]
        for row in db.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()
    }


def add_column_if_missing(db, table_name, column_name, definition):
    columns = table_columns(db, table_name)

    if column_name not in columns:
        db.execute(
            f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {definition}'
        )


def generate_customer_id(db):
    year = datetime.now().strftime("%y")
    alphabet = string.ascii_uppercase + string.digits

    for _ in range(100):
        code = "".join(random.choices(alphabet, k=3))
        number = random.randint(1000, 9999)
        customer_id = f"FA-{year}-{code}-{number}"

        if not db.execute(
            "SELECT 1 FROM customers WHERE customer_id = ?",
            (customer_id,)
        ).fetchone():
            return customer_id

    raise RuntimeError("Could not generate a unique customer ID.")


def create_account_number(db):
    for _ in range(100):
        number = "FA" + "".join(
            random.choices(string.digits, k=12)
        )

        if not db.execute(
            "SELECT 1 FROM accounts WHERE account_number = ?",
            (number,)
        ).fetchone():
            return number

    raise RuntimeError("Could not generate a unique account number.")


def create_ifsc_code():
    return "FNAS0" + "".join(
        random.choices(string.digits, k=6)
    )


def init_db():
    """Create missing tables and migrate existing columns without deleting data."""

    if DATABASE.exists():
        with sqlite3.connect(DATABASE) as check_db:
            existing_tables = {
                row[0]
                for row in check_db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }

        if existing_tables and "app_metadata" not in existing_tables:
            backup_path = DATABASE.with_name(
                "special_project_backup_before_update.db"
            )

            if not backup_path.exists():
                shutil.copy2(DATABASE, backup_path)

    with get_db_connection() as db:

        db.executescript("""
            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                mpin_hash TEXT NOT NULL,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                password_hash TEXT
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                account_number TEXT UNIQUE NOT NULL,
                account_type TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ifsc_code TEXT,
                nickname TEXT,
                branch TEXT,
                is_primary INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(customer_id)
                    REFERENCES customers(customer_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'Success',
                FOREIGN KEY(account_number)
                    REFERENCES accounts(account_number) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                card_type TEXT NOT NULL,
                last_four_digits TEXT NOT NULL,
                status TEXT DEFAULT 'Active',
                account_number TEXT,
                card_number TEXT,
                expiry_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(customer_id)
                    REFERENCES customers(customer_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS loan_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                loan_type TEXT NOT NULL,
                amount REAL NOT NULL,
                tenure_months INTEGER NOT NULL,
                status TEXT DEFAULT 'Pending',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(customer_id)
                    REFERENCES customers(customer_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(customer_id)
                    REFERENCES customers(customer_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chatbot_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(customer_id)
                    REFERENCES customers(customer_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chatbot_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(conversation_id)
                    REFERENCES chatbot_conversations(id) ON DELETE CASCADE
            );
        """)

        migrations = {
            "customers": [
                ("phone", "TEXT"),
                ("created_at", "TIMESTAMP"),
                ("password_hash", "TEXT")
            ],
            "accounts": [
                ("status", "TEXT NOT NULL DEFAULT 'Active'"),
                ("balance", "REAL NOT NULL DEFAULT 0"),
                ("created_at", "TIMESTAMP"),
                ("ifsc_code", "TEXT"),
                ("nickname", "TEXT"),
                ("branch", "TEXT"),
                ("is_primary", "INTEGER NOT NULL DEFAULT 0")
            ],
            "transactions": [
                ("description", "TEXT"),
                ("transaction_date", "TIMESTAMP"),
                ("status", "TEXT NOT NULL DEFAULT 'Success'")
            ],
            "cards": [
                ("status", "TEXT DEFAULT 'Active'"),
                ("account_number", "TEXT"),
                ("card_number", "TEXT"),
                ("expiry_date", "TEXT"),
                ("created_at", "TIMESTAMP")
            ],
            "loan_applications": [
                ("status", "TEXT DEFAULT 'Pending'"),
                ("applied_at", "TIMESTAMP")
            ],
            "complaints": [
                ("status", "TEXT DEFAULT 'Pending'"),
                ("created_at", "TIMESTAMP")
            ]
        }

        for table_name, columns in migrations.items():
            for column_name, definition in columns:
                add_column_if_missing(
                    db,
                    table_name,
                    column_name,
                    definition
                )

        customer_columns = table_columns(db, "customers")

        if "password" in customer_columns:
            old_rows = db.execute("""
                SELECT customer_id, password
                FROM customers
                WHERE password IS NOT NULL
                  AND (password_hash IS NULL OR password_hash = '')
            """).fetchall()

            for row in old_rows:
                old_password = str(row["password"])

                db.execute("""
                    UPDATE customers
                    SET password_hash = ?
                    WHERE customer_id = ?
                """, (
                    generate_password_hash(old_password),
                    row["customer_id"]
                ))

        accounts_without_ifsc = db.execute("""
            SELECT account_number
            FROM accounts
            WHERE ifsc_code IS NULL OR ifsc_code = ''
        """).fetchall()

        for row in accounts_without_ifsc:
            db.execute("""
                UPDATE accounts
                SET ifsc_code = ?
                WHERE account_number = ?
            """, (
                create_ifsc_code(),
                row["account_number"]
            ))

        employee = db.execute(
            "SELECT id FROM employees WHERE employee_id = ?",
            ("NOB12",)
        ).fetchone()

        if not employee:
            db.execute("""
                INSERT INTO employees (employee_id, password_hash)
                VALUES (?, ?)
            """, (
                "NOB12",
                generate_password_hash("nobita@123")
            ))

        test_email = "dheeraj@gmail.com"

        customer = db.execute("""
            SELECT customer_id
            FROM customers
            WHERE email = ? COLLATE NOCASE
        """, (test_email,)).fetchone()

        if not customer:
            customer_id = generate_customer_id(db)
            demo_hash = generate_password_hash("0296")

            db.execute("""
                INSERT INTO customers (
                    customer_id, full_name, email,
                    mpin_hash, password_hash
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                customer_id,
                "Dheeraj",
                test_email,
                demo_hash,
                demo_hash
            ))

        else:
            customer_id = customer["customer_id"]

        if not db.execute(
            "SELECT 1 FROM accounts WHERE customer_id = ?",
            (customer_id,)
        ).fetchone():

            account_number = create_account_number(db)

            db.execute("""
                INSERT INTO accounts (
                    customer_id, account_number, account_type,
                    balance, status, ifsc_code, is_primary
                )
                VALUES (?, ?, 'Savings', 50000, 'Active', ?, 1)
            """, (
                customer_id,
                account_number,
                create_ifsc_code()
            ))

        db.execute("""
            INSERT OR REPLACE INTO app_metadata (key, value)
            VALUES ('schema_version', '4')
        """)
        # ============================================================
# 2. COMMON HELPERS AND AUTHENTICATION
# ============================================================

def customer_required():
    return (
        session.get("role") == "customer"
        and bool(session.get("customer_id"))
    )


def employee_required():
    return (
        session.get("role") == "employee"
        and bool(session.get("employee_id"))
    )


def login_required_message():
    return jsonify({
        "success": False,
        "message": "Please log in again."
    }), 401


def employee_required_message():
    return jsonify({
        "success": False,
        "message": "Employee login required."
    }), 401


def rows_as_dicts(rows):
    return [dict(row) for row in rows]


def valid_mpin(value):
    return bool(re.fullmatch(r"\d{4}", str(value or "")))


def normalize_complaint_status(status):
    value = str(status or "Pending").strip().lower()
    mapping = {
        "open": "Pending",
        "pending": "Pending",
        "in progress": "In Progress",
        "in-progress": "In Progress",
        "resolved": "Resolved",
        "closed": "Resolved",
        "rejected": "Rejected"
    }
    return mapping.get(value, value.title())


def complaint_dict(row):
    result = dict(row)
    result["status"] = normalize_complaint_status(result.get("status"))
    return result


def get_customer_dashboard_data(db, customer_id):
    customer = db.execute("""
        SELECT customer_id, full_name, email, phone, created_at
        FROM customers
        WHERE customer_id = ?
    """, (customer_id,)).fetchone()

    accounts = db.execute("""
        SELECT account_number, account_type, balance, status,
               ifsc_code, nickname, branch, is_primary
        FROM accounts
        WHERE customer_id = ?
        ORDER BY is_primary DESC, id DESC
    """, (customer_id,)).fetchall()

    transactions = db.execute("""
        SELECT t.id, t.transaction_date, t.account_number,
               t.transaction_type, t.amount, t.description, t.status
        FROM transactions t
        JOIN accounts a ON a.account_number = t.account_number
        WHERE a.customer_id = ?
        ORDER BY t.transaction_date DESC, t.id DESC
        LIMIT 100
    """, (customer_id,)).fetchall()

    cards = db.execute("""
        SELECT id, card_type, last_four_digits, status,
               account_number, expiry_date, created_at
        FROM cards
        WHERE customer_id = ?
        ORDER BY id DESC
    """, (customer_id,)).fetchall()

    loans = db.execute("""
        SELECT id, loan_type, amount, tenure_months, status, applied_at
        FROM loan_applications
        WHERE customer_id = ?
        ORDER BY id DESC
    """, (customer_id,)).fetchall()

    complaints = db.execute("""
        SELECT id, customer_id, subject, message, status, created_at
        FROM complaints
        WHERE customer_id = ?
        ORDER BY id DESC
    """, (customer_id,)).fetchall()

    account_data = rows_as_dicts(accounts)
    active_balance = sum(
        float(item.get("balance") or 0)
        for item in account_data
        if str(item.get("status") or "Active").lower() == "active"
    )
    loan_data = rows_as_dicts(loans)

    return {
        "customer": dict(customer) if customer else None,
        "accounts": account_data,
        "account_balance": active_balance,
        "account_number": (
            account_data[0]["account_number"] if account_data else None
        ),
        "transactions": rows_as_dicts(transactions),
        "cards": rows_as_dicts(cards),
        "loans": loan_data,
        "applications": loan_data,
        "complaints": [complaint_dict(item) for item in complaints]
    }


def parse_positive_amount(value, field_name="amount"):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Enter a valid {field_name}.")

    if not math.isfinite(amount) or amount <= 0:
        raise ValueError(
            f"{field_name.capitalize()} must be greater than zero."
        )

    return amount


# ============================================================
# 3. WEBSITE FILES AND HEALTH
# ============================================================

@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "login.html")


@app.route("/<path:filename>")
def serve_project_file(filename):
    requested_file = (BASE_DIR / filename).resolve()

    if requested_file != BASE_DIR and BASE_DIR not in requested_file.parents:
        return "Not found", 404

    if requested_file.is_file():
        return send_from_directory(BASE_DIR, filename)

    return "Not found", 404


@app.route("/api/health")
def health():
    return jsonify({
        "success": True,
        "message": "FinAssist backend is running."
    })


# ============================================================
# 4. CUSTOMER REGISTRATION, LOGIN, LOGOUT AND SESSION
# ============================================================

@app.route("/api/register", methods=["POST"])
def register_customer():
    data = request.get_json(silent=True) or {}

    full_name = " ".join(
        str(data.get("name", data.get("full_name", ""))).strip().split()
    )
    email = str(data.get("email", "")).strip().lower()
    phone = re.sub(
        r"\D", "",
        str(data.get("phone", data.get("mobile", "")))
    )
    mpin = str(data.get("mpin", data.get("password", "")))
    confirm_mpin = str(
        data.get("confirm_mpin", data.get("confirmPassword", mpin))
    )
    account_type = str(
        data.get("account_type", "Savings")
    ).strip().title()

    if len(full_name) < 2 or len(full_name) > 80:
        return jsonify({
            "success": False,
            "message": "Enter a valid full name."
        }), 400

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({
            "success": False,
            "message": "Enter a valid email address."
        }), 400

    if len(phone) != 10:
        return jsonify({
            "success": False,
            "message": "Enter a valid 10-digit mobile number."
        }), 400

    if not valid_mpin(mpin):
        return jsonify({
            "success": False,
            "message": "MPIN must contain exactly 4 digits."
        }), 400

    if mpin != confirm_mpin:
        return jsonify({
            "success": False,
            "message": "MPIN entries do not match."
        }), 400

    if account_type not in ("Savings", "Current"):
        return jsonify({
            "success": False,
            "message": "Choose Savings or Current account."
        }), 400

    with get_db_connection() as db:
        if db.execute(
            "SELECT 1 FROM customers WHERE email = ? COLLATE NOCASE",
            (email,)
        ).fetchone():
            return jsonify({
                "success": False,
                "message": "An account with this email already exists."
            }), 409

        customer_id = generate_customer_id(db)
        hashed_mpin = generate_password_hash(mpin)

        db.execute("""
            INSERT INTO customers (
                customer_id, full_name, email, mpin_hash,
                password_hash, phone
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            full_name,
            email,
            hashed_mpin,
            hashed_mpin,
            phone
        ))

        account_number = create_account_number(db)
        ifsc_code = create_ifsc_code()

        db.execute("""
            INSERT INTO accounts (
                customer_id, account_number, account_type,
                balance, status, ifsc_code, is_primary
            )
            VALUES (?, ?, ?, 0, 'Active', ?, 1)
        """, (
            customer_id,
            account_number,
            account_type,
            ifsc_code
        ))

    return jsonify({
        "success": True,
        "message": "Your FinAssist profile has been created. Please sign in.",
        "customer": {
            "customer_id": customer_id,
            "name": full_name,
            "email": email,
            "account_number": account_number,
            "account_type": account_type
        },
        "redirect": "/login.html"
    }), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    role = str(data.get("role", "customer")).strip().lower()

    if role == "customer":
        full_name = " ".join(
            str(data.get("name", data.get("full_name", ""))).strip().split()
        )
        email = str(data.get("email", "")).strip().lower()
        mpin = str(data.get("mpin", data.get("password", "")))

        if not full_name or not email or not valid_mpin(mpin):
            return jsonify({
                "success": False,
                "message": "Enter your full name, email and 4-digit MPIN."
            }), 400

        with get_db_connection() as db:
            user = db.execute("""
                SELECT customer_id, full_name, email, mpin_hash
                FROM customers
                WHERE email = ? COLLATE NOCASE
            """, (email,)).fetchone()

        if (
            not user
            or user["full_name"].strip().casefold() != full_name.casefold()
            or not user["mpin_hash"]
            or not check_password_hash(user["mpin_hash"], mpin)
        ):
            return jsonify({
                "success": False,
                "message": "The name, email or MPIN is incorrect."
            }), 401

        session.clear()
        session.permanent = True
        session["role"] = "customer"
        session["customer_id"] = user["customer_id"]
        session["customer_name"] = user["full_name"]
        session["customer_email"] = user["email"]

        return jsonify({
            "success": True,
            "role": "customer",
            "redirect": "/dashboard.html",
            "customer": {
                "customer_id": user["customer_id"],
                "name": user["full_name"],
                "email": user["email"]
            }
        })

    if role == "employee":
        employee_id = str(
            data.get("user_id", data.get("employee_id", ""))
        ).strip().upper()
        password = str(data.get("password", ""))

        if not employee_id or not password:
            return jsonify({
                "success": False,
                "message": "Enter your employee ID and password."
            }), 400

        with get_db_connection() as db:
            user = db.execute("""
                SELECT employee_id, password_hash
                FROM employees
                WHERE employee_id = ?
            """, (employee_id,)).fetchone()

        if (
            not user
            or not check_password_hash(user["password_hash"], password)
        ):
            return jsonify({
                "success": False,
                "message": "Invalid employee ID or password."
            }), 401

        session.clear()
        session.permanent = True
        session["role"] = "employee"
        session["employee_id"] = user["employee_id"]

        return jsonify({
            "success": True,
            "role": "employee",
            "employee_id": user["employee_id"],
            "redirect": "/employee.html"
        })

    return jsonify({
        "success": False,
        "message": "Invalid login type."
    }), 400


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({
        "success": True,
        "redirect": "/login.html"
    })


@app.route("/api/session")
def check_session():
    if customer_required():
        return jsonify({
            "authenticated": True,
            "logged_in": True,
            "role": "customer",
            "customer_id": session.get("customer_id"),
            "customer_name": session.get("customer_name"),
            "customer_email": session.get("customer_email")
        })

    if employee_required():
        return jsonify({
            "authenticated": True,
            "logged_in": True,
            "role": "employee",
            "employee_id": session.get("employee_id")
        })

    return jsonify({
        "authenticated": False,
        "logged_in": False
    }), 401


# ============================================================
# 5. CUSTOMER DASHBOARD AND PROFILE
# ============================================================

@app.route("/api/dashboard")
def customer_dashboard():
    if not customer_required():
        return login_required_message()

    with get_db_connection() as db:
        result = get_customer_dashboard_data(
            db,
            session["customer_id"]
        )

    if not result["customer"]:
        session.clear()
        return jsonify({
            "success": False,
            "message": "Customer record not found. Please log in again."
        }), 404

    return jsonify({
        "success": True,
        **result
    })


@app.route("/api/my-profile")
def my_profile():
    if not customer_required():
        return login_required_message()

    with get_db_connection() as db:
        customer = db.execute("""
            SELECT customer_id, full_name, email, phone, created_at
            FROM customers
            WHERE customer_id = ?
        """, (session["customer_id"],)).fetchone()

    if not customer:
        return jsonify({
            "success": False,
            "message": "Customer not found."
        }), 404

    return jsonify({
        "success": True,
        "customer": dict(customer)
    })


# ============================================================
# 6. CUSTOMER ACCOUNTS
# ============================================================

@app.route("/api/my-accounts")
@app.route("/api/accounts")
def my_accounts():
    if not customer_required():
        return login_required_message()

    with get_db_connection() as db:
        accounts = db.execute("""
            SELECT account_number, account_type, balance, status,
                   ifsc_code, nickname, branch, is_primary, created_at
            FROM accounts
            WHERE customer_id = ?
            ORDER BY is_primary DESC, id DESC
        """, (session["customer_id"],)).fetchall()

    account_data = rows_as_dicts(accounts)

    return jsonify({
        "success": True,
        "accounts": account_data,
        "total_balance": sum(
            float(account.get("balance") or 0)
            for account in account_data
            if str(account.get("status") or "Active").lower() == "active"
        )
    })
# ============================================================
# 6A. ADD AND UPDATE CUSTOMER ACCOUNTS
# ============================================================

@app.route("/api/add-account", methods=["POST"])
def add_account():
    if not customer_required():
        return login_required_message()

    data = request.get_json(silent=True) or {}
    account_type = str(data.get("account_type", "")).strip().title()
    nickname = str(data.get("nickname", "")).strip()[:40] or None
    branch = str(data.get("branch", "")).strip()[:80] or None

    try:
        initial_deposit = float(data.get("initial_deposit", 0))
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Enter a valid initial deposit."
        }), 400

    if account_type not in ("Savings", "Current"):
        return jsonify({
            "success": False,
            "message": "Choose Savings or Current account."
        }), 400

    if not math.isfinite(initial_deposit) or not 0 <= initial_deposit <= 100000000:
        return jsonify({
            "success": False,
            "message": "Enter a valid deposit amount."
        }), 400

    with get_db_connection() as db:
        account_number = create_account_number(db)
        ifsc_code = create_ifsc_code()

        db.execute("""
            INSERT INTO accounts (
                customer_id, account_number, account_type, balance,
                status, ifsc_code, nickname, branch, is_primary
            )
            VALUES (?, ?, ?, ?, 'Active', ?, ?, ?, 0)
        """, (
            session["customer_id"],
            account_number,
            account_type,
            initial_deposit,
            ifsc_code,
            nickname,
            branch
        ))

        if initial_deposit > 0:
            db.execute("""
                INSERT INTO transactions (
                    account_number, transaction_type, amount,
                    description, status
                )
                VALUES (?, 'Credit', ?, 'Initial account deposit', 'Success')
            """, (account_number, initial_deposit))

    return jsonify({
        "success": True,
        "message": "Your new account has been created successfully.",
        "account": {
            "account_number": account_number,
            "account_type": account_type,
            "balance": initial_deposit,
            "status": "Active",
            "ifsc_code": ifsc_code,
            "nickname": nickname,
            "branch": branch
        }
    }), 201


@app.route("/api/account-status/<account_number>", methods=["PATCH"])
def update_account_status(account_number):
    if not customer_required():
        return login_required_message()

    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).strip().title()

    if status not in ("Active", "Inactive"):
        return jsonify({
            "success": False,
            "message": "Invalid account status."
        }), 400

    with get_db_connection() as db:
        account = db.execute("""
            SELECT account_number
            FROM accounts
            WHERE account_number = ? AND customer_id = ?
        """, (account_number, session["customer_id"])).fetchone()

        if not account:
            return jsonify({
                "success": False,
                "message": "Account not found."
            }), 404

        db.execute("""
            UPDATE accounts
            SET status = ?
            WHERE account_number = ? AND customer_id = ?
        """, (status, account_number, session["customer_id"]))

    return jsonify({
        "success": True,
        "message": f"Account successfully marked as {status}.",
        "status": status
    })


# ============================================================
# 7. CUSTOMER TRANSACTIONS
# ============================================================

@app.route("/api/my-transactions")
@app.route("/api/transactions")
def my_transactions():
    if not customer_required():
        return login_required_message()

    with get_db_connection() as db:
        transactions = db.execute("""
            SELECT t.id, t.account_number, t.transaction_type,
                   t.amount, t.description, t.transaction_date, t.status
            FROM transactions t
            JOIN accounts a ON a.account_number = t.account_number
            WHERE a.customer_id = ?
            ORDER BY t.transaction_date DESC, t.id DESC
        """, (session["customer_id"],)).fetchall()

    return jsonify({
        "success": True,
        "transactions": rows_as_dicts(transactions)
    })


# ============================================================
# 8. CUSTOMER CARDS
# ============================================================

@app.route("/api/my-cards")
@app.route("/api/cards", methods=["GET"])
def my_cards():
    if not customer_required():
        return login_required_message()

    with get_db_connection() as db:
        cards = db.execute("""
            SELECT id, card_type, last_four_digits, card_number,
                   status, account_number, expiry_date, created_at
            FROM cards
            WHERE customer_id = ?
            ORDER BY id DESC
        """, (session["customer_id"],)).fetchall()

    card_list = rows_as_dicts(cards)

    for card in card_list:
        if not card.get("card_number"):
            last_four = str(card.get("last_four_digits") or "")
            card["card_number"] = "000000000000" + last_four.zfill(4)

    return jsonify({
        "success": True,
        "cards": card_list
    })


@app.route("/api/my-cards", methods=["POST"])
@app.route("/api/cards", methods=["POST"])
def add_card():
    if not customer_required():
        return login_required_message()

    data = request.get_json(silent=True) or {}

    cardholder = " ".join(
        str(data.get(
            "cardholder_name",
            data.get("cardholder", "")
        )).strip().split()
    )

    card_number = re.sub(
        r"\D",
        "",
        str(data.get("card_number", ""))
    )

    card_type = str(data.get("card_type", "")).strip().title()
    expiry_date = str(data.get("expiry_date", "")).strip()
    cvv = str(data.get("cvv", "")).strip()
    account_number = str(data.get("account_number", "")).strip()

    if card_type not in ("Debit", "Credit"):
        return jsonify({
            "success": False,
            "message": "Choose Debit or Credit card."
        }), 400

    if not re.fullmatch(r"\d{13,19}", card_number):
        return jsonify({
            "success": False,
            "message": "Enter a valid 13 to 19 digit card number."
        }), 400

    if not re.fullmatch(r"\d{3,4}", cvv):
        return jsonify({
            "success": False,
            "message": "Enter a valid CVV."
        }), 400

    if not re.fullmatch(r"\d{4}-\d{2}", expiry_date):
        return jsonify({
            "success": False,
            "message": "Expiry date must use YYYY-MM format."
        }), 400

    try:
        expiry = datetime.strptime(expiry_date, "%Y-%m")

        if expiry < datetime(
            datetime.now().year,
            datetime.now().month,
            1
        ):
            return jsonify({
                "success": False,
                "message": "This card has expired."
            }), 400

    except ValueError:
        return jsonify({
            "success": False,
            "message": "Enter a valid expiry date."
        }), 400

    with get_db_connection() as db:
        customer = db.execute("""
            SELECT full_name
            FROM customers
            WHERE customer_id = ?
        """, (session["customer_id"],)).fetchone()

        if not customer:
            return jsonify({
                "success": False,
                "message": "Customer not found."
            }), 404

        if (
            cardholder
            and cardholder.casefold() != customer["full_name"].casefold()
        ):
            return jsonify({
                "success": False,
                "message": "Cardholder name must match your profile."
            }), 400

        account = db.execute("""
            SELECT account_number
            FROM accounts
            WHERE account_number = ?
              AND customer_id = ?
              AND LOWER(status) = 'active'
        """, (
            account_number,
            session["customer_id"]
        )).fetchone()

        if not account:
            return jsonify({
                "success": False,
                "message": "Choose one of your active accounts."
            }), 400

        # Never store the full card number or CVV.
        # This is a college-project simulation.

        last_four = card_number[-4:]
        demo_card_number = card_number

        db.execute("""
            INSERT INTO cards (
                customer_id,
                card_type,
                last_four_digits,
                card_number,
                status,
                account_number,
                expiry_date,
                created_at
            )
           VALUES (?, ?, ?, ?, 'Active', ?, ?, CURRENT_TIMESTAMP)
        """, (
            session["customer_id"],
            card_type,
            last_four,
            demo_card_number,
            account_number,
            expiry_date
        ))

    return jsonify({
        "success": True,
        "message": "Card added successfully.",
        "card": {
            "card_type": card_type,
            "last_four_digits": last_four,
            "status": "Active",
            "card_number": demo_card_number,
            "account_number": account_number,
            "expiry_date": expiry_date
        }
    }), 201


@app.route("/api/my-cards/<int:card_id>/status", methods=["PATCH"])
def update_card_status(card_id):
    if not customer_required():
        return login_required_message()

    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).strip().title()

    if status not in ("Active", "Blocked"):
        return jsonify({
            "success": False,
            "message": "Choose Active or Blocked."
        }), 400

    with get_db_connection() as db:
        cursor = db.execute("""
            UPDATE cards
            SET status = ?
            WHERE id = ? AND customer_id = ?
        """, (
            status,
            card_id,
            session["customer_id"]
        ))

        if cursor.rowcount == 0:
            return jsonify({
                "success": False,
                "message": "Card not found."
            }), 404

    return jsonify({
        "success": True,
        "message": f"Card marked as {status}.",
        "status": status
    })
# ============================================================
# 9. CUSTOMER LOANS AND APPLICATION TRACKING
# ============================================================

@app.route("/api/my-loans")
@app.route("/api/loans")
def my_loans():
    if not customer_required():
        return login_required_message()

    with get_db_connection() as db:
        loans = db.execute("""
            SELECT id, loan_type, amount, tenure_months, status, applied_at
            FROM loan_applications
            WHERE customer_id = ?
            ORDER BY id DESC
        """, (session["customer_id"],)).fetchall()

    loan_data = rows_as_dicts(loans)
    return jsonify({
        "success": True,
        "loans": loan_data,
        "applications": loan_data
    })


@app.route("/api/apply-loan", methods=["POST"])
@app.route("/api/loan-application", methods=["POST"])
@app.route("/api/my-loans", methods=["POST"])
def apply_loan():
    if not customer_required():
        return login_required_message()

    data = request.get_json(silent=True) or {}
    loan_type = str(data.get("loan_type", "")).strip()

    loan_types = {
        "personal loan": "Personal",
        "personal": "Personal",
        "gold loan": "Gold",
        "gold": "Gold",
        "vehicle loan": "Vehicle",
        "vehicle": "Vehicle",
        "home loan": "Home",
        "home": "Home",
        "loan against property (lap)": "Property",
        "property": "Property",
        "education loan": "Education",
        "education": "Education",
        "business loan": "Business",
        "business": "Business"
    }

    normalized_type = loan_types.get(loan_type.lower())

    if not normalized_type:
        return jsonify({
            "success": False,
            "message": "Select a valid loan type."
        }), 400

    try:
        amount = parse_positive_amount(
            data.get("amount"),
            "loan amount"
        )
        tenure = int(data.get("tenure_months", 0))
    except (ValueError, TypeError) as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    if amount > 100000000:
        return jsonify({
            "success": False,
            "message": "Loan amount is too high."
        }), 400

    if tenure < 1 or tenure > 360:
        return jsonify({
            "success": False,
            "message": "Tenure must be between 1 and 360 months."
        }), 400

    with get_db_connection() as db:
        cursor = db.execute("""
            INSERT INTO loan_applications (
                customer_id, loan_type, amount, tenure_months, status
            )
            VALUES (?, ?, ?, ?, 'Pending')
        """, (
            session["customer_id"],
            normalized_type,
            amount,
            tenure
        ))

        application_id = cursor.lastrowid

    return jsonify({
        "success": True,
        "message": "Loan application submitted successfully.",
        "application_id": application_id,
        "status": "Pending"
    }), 201


@app.route("/api/my-applications")
def my_applications():
    if not customer_required():
        return login_required_message()

    with get_db_connection() as db:
        applications = db.execute("""
            SELECT id, loan_type, amount, tenure_months, status, applied_at
            FROM loan_applications
            WHERE customer_id = ?
            ORDER BY id DESC
        """, (session["customer_id"],)).fetchall()

    return jsonify({
        "success": True,
        "applications": rows_as_dicts(applications)
    })


# ============================================================
# 10. EMI CALCULATOR
# ============================================================

@app.route("/api/emi", methods=["POST"])
@app.route("/api/emi-calculator", methods=["POST"])
def calculate_emi():
    data = request.get_json(silent=True) or {}

    try:
        principal = parse_positive_amount(
            data.get("principal", data.get("amount")),
            "loan amount"
        )
        annual_rate = float(
            data.get("interest_rate", data.get("rate", 0))
        )
        months = int(
            data.get("tenure_months", data.get("months", 0))
        )
    except (ValueError, TypeError) as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    if (
        not math.isfinite(annual_rate)
        or annual_rate < 0
        or annual_rate > 100
    ):
        return jsonify({
            "success": False,
            "message": "Enter a valid annual interest rate."
        }), 400

    if months < 1 or months > 600:
        return jsonify({
            "success": False,
            "message": "Tenure must be between 1 and 600 months."
        }), 400

    monthly_rate = annual_rate / 12 / 100

    if monthly_rate == 0:
        emi = principal / months
    else:
        factor = (1 + monthly_rate) ** months
        emi = (
            principal * monthly_rate * factor
            / (factor - 1)
        )

    total_payment = emi * months
    total_interest = total_payment - principal

    return jsonify({
        "success": True,
        "emi": round(emi, 2),
        "monthly_emi": round(emi, 2),
        "principal": round(principal, 2),
        "total_interest": round(total_interest, 2),
        "total_payment": round(total_payment, 2),
        "tenure_months": months,
        "interest_rate": annual_rate
    })


# ============================================================
# 11. CUSTOMER COMPLAINTS
# ============================================================

@app.route("/api/my-complaints")
@app.route("/api/complaints", methods=["GET"])
def my_complaints():
    if not customer_required():
        return login_required_message()

    with get_db_connection() as db:
        complaints = db.execute("""
            SELECT id, customer_id, subject, message, status, created_at
            FROM complaints
            WHERE customer_id = ?
            ORDER BY id DESC
        """, (session["customer_id"],)).fetchall()

    return jsonify({
        "success": True,
        "complaints": [
            complaint_dict(item) for item in complaints
        ]
    })


@app.route("/api/submit-complaint", methods=["POST"])
@app.route("/api/complaints", methods=["POST"])
def submit_complaint():
    if not customer_required():
        return login_required_message()

    data = request.get_json(silent=True) or {}
    subject = str(data.get("subject", "")).strip()
    message = str(data.get("message", "")).strip()

    if not subject or not message:
        return jsonify({
            "success": False,
            "message": "Please enter both subject and message."
        }), 400

    if len(subject) > 150:
        return jsonify({
            "success": False,
            "message": "Subject must be 150 characters or less."
        }), 400

    if len(message) > 5000:
        return jsonify({
            "success": False,
            "message": "Message must be 5000 characters or less."
        }), 400

    with get_db_connection() as db:
        cursor = db.execute("""
            INSERT INTO complaints (
                customer_id, subject, message, status
            )
            VALUES (?, ?, ?, 'Pending')
        """, (
            session["customer_id"],
            subject,
            message
        ))

        complaint_id = cursor.lastrowid

    return jsonify({
        "success": True,
        "message": "Complaint submitted successfully.",
        "complaint_id": complaint_id,
        "status": "Pending"
    }), 201


# ============================================================
# 12. EMPLOYEE DASHBOARD AND CUSTOMER MANAGEMENT
# ============================================================

@app.route("/api/employee/dashboard")
def employee_dashboard():
    if not employee_required():
        return employee_required_message()

    with get_db_connection() as db:

        complaint_stats = db.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN LOWER(status) IN ('pending', 'open') THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN LOWER(status) = 'in progress' THEN 1 ELSE 0 END) AS in_progress,
            SUM(CASE WHEN LOWER(status) = 'resolved' THEN 1 ELSE 0 END) AS resolved
        FROM complaints
    """).fetchone()

    loan_stats = db.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN LOWER(status) = 'pending' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN LOWER(status) = 'in progress' THEN 1 ELSE 0 END) AS in_progress,
            SUM(CASE WHEN LOWER(status) = 'approved' THEN 1 ELSE 0 END) AS approved
        FROM loan_applications
    """).fetchone()

    return jsonify({
    "success": True,
    "employee": {
        "employee_id": session.get("employee_id"),
        "name": session.get("employee_name")
    },
    "complaints": {
        "total": complaint_stats["total"],
        "pending": complaint_stats["pending"],
        "in_progress": complaint_stats["in_progress"],
        "resolved": complaint_stats["resolved"]
    },
    "loans": {
        "total": loan_stats["total"],
        "pending": loan_stats["pending"],
        "in_progress": loan_stats["in_progress"],
        "approved": loan_stats["approved"]
    }
})


@app.route("/api/employee/customers")
def employee_customers():
    if not employee_required():
        return employee_required_message()

    search_term = request.args.get("search", "").strip()

    with get_db_connection() as db:
        if search_term:
            pattern = f"%{search_term}%"

            customers = db.execute("""
                SELECT customer_id, full_name, email, phone, created_at
                FROM customers
                WHERE customer_id LIKE ?
                   OR full_name LIKE ?
                   OR email LIKE ?
                ORDER BY id DESC
            """, (
                pattern,
                pattern,
                pattern
            )).fetchall()

        else:
            customers = db.execute("""
                SELECT customer_id, full_name, email, phone, created_at
                FROM customers
                ORDER BY id DESC
            """).fetchall()

    return jsonify({
        "success": True,
        "customers": rows_as_dicts(customers)
    })


@app.route("/api/employee/customer/<customer_id>")
@app.route("/api/employee/customers/<customer_id>")
def employee_customer_details(customer_id):
    if not employee_required():
        return employee_required_message()

    with get_db_connection() as db:
        customer = db.execute("""
            SELECT customer_id, full_name, email, phone, created_at
            FROM customers
            WHERE customer_id = ?
        """, (customer_id,)).fetchone()

        if not customer:
            return jsonify({
                "success": False,
                "message": "Customer not found."
            }), 404

        accounts = db.execute("""
            SELECT account_number, account_type, balance, status,
                   ifsc_code, nickname, branch, is_primary
            FROM accounts
            WHERE customer_id = ?
            ORDER BY id DESC
        """, (customer_id,)).fetchall()

        cards = db.execute("""
            SELECT id, card_type, last_four_digits, status,
                   account_number, expiry_date
            FROM cards
            WHERE customer_id = ?
            ORDER BY id DESC
        """, (customer_id,)).fetchall()

        transactions = db.execute("""
            SELECT t.id, t.account_number, t.transaction_type,
                   t.amount, t.description, t.transaction_date, t.status
            FROM transactions t
            JOIN accounts a ON a.account_number = t.account_number
            WHERE a.customer_id = ?
            ORDER BY t.id DESC
        """, (customer_id,)).fetchall()

        loans = db.execute("""
            SELECT id, loan_type, amount, tenure_months, status, applied_at
            FROM loan_applications
            WHERE customer_id = ?
            ORDER BY id DESC
        """, (customer_id,)).fetchall()

        complaints = db.execute("""
            SELECT id, subject, message, status, created_at
            FROM complaints
            WHERE customer_id = ?
            ORDER BY id DESC
        """, (customer_id,)).fetchall()

    return jsonify({
        "success": True,
        "customer": dict(customer),
        "accounts": rows_as_dicts(accounts),
        "cards": rows_as_dicts(cards),
        "transactions": rows_as_dicts(transactions),
        "loans": rows_as_dicts(loans),
        "applications": rows_as_dicts(loans),
        "complaints": [
            complaint_dict(item) for item in complaints
        ]
    })


# ============================================================
# 13. EMPLOYEE LOAN MANAGEMENT
# ============================================================

@app.route("/api/employee/loans")
def employee_loans():
    if not employee_required():
        return employee_required_message()

    with get_db_connection() as db:
        loans = db.execute("""
            SELECT l.id, l.customer_id, c.full_name, l.loan_type,
                   l.amount, l.tenure_months, l.status, l.applied_at
            FROM loan_applications l
            JOIN customers c ON c.customer_id = l.customer_id
            ORDER BY l.id DESC
        """).fetchall()

    return jsonify({
        "success": True,
        "loans": rows_as_dicts(loans)
    })


@app.route(
    "/api/employee/loans/<int:loan_id>",
    methods=["PATCH", "POST"]
)
def update_loan_status(loan_id):
    if not employee_required():
        return employee_required_message()

    data = request.get_json(silent=True) or {}

    status = " ".join(
        str(data.get("status", "")).strip().lower().split()
    ).title()

    allowed = {
        "Pending",
        "Documents Pending",
        "In Progress",
        "Approved",
        "Rejected"
    }

    if status not in allowed:
        return jsonify({
            "success": False,
            "message": (
                "Choose Pending, Documents Pending, "
                "In Progress, Approved, or Rejected."
            )
        }), 400

    with get_db_connection() as db:
        cursor = db.execute("""
            UPDATE loan_applications
            SET status = ?
            WHERE id = ?
        """, (status, loan_id))

        if cursor.rowcount == 0:
            return jsonify({
                "success": False,
                "message": "Loan application not found."
            }), 404

    return jsonify({
        "success": True,
        "message": "Loan status updated successfully.",
        "status": status
    })


# ============================================================
# 14. EMPLOYEE COMPLAINT MANAGEMENT
# ============================================================

@app.route("/api/employee/complaints")
def employee_complaints():
    if not employee_required():
        return employee_required_message()

    with get_db_connection() as db:
        complaints = db.execute("""
            SELECT cp.id, cp.customer_id, c.full_name,
                   cp.subject, cp.message, cp.status, cp.created_at
            FROM complaints cp
            LEFT JOIN customers c
                ON c.customer_id = cp.customer_id
            ORDER BY cp.id DESC
        """).fetchall()

    return jsonify({
        "success": True,
        "complaints": [
            complaint_dict(item) for item in complaints
        ]
    })


@app.route(
    "/api/employee/complaints/<int:complaint_id>",
    methods=["PATCH", "POST"]
)
def update_complaint_status(complaint_id):
    if not employee_required():
        return employee_required_message()

    data = request.get_json(silent=True) or {}
    status = normalize_complaint_status(data.get("status"))

    allowed = {
        "Pending",
        "In Progress",
        "Resolved",
        "Rejected"
    }

    if status not in allowed:
        return jsonify({
            "success": False,
            "message": (
                "Choose Pending, In Progress, Resolved, or Rejected."
            )
        }), 400

    with get_db_connection() as db:
        cursor = db.execute("""
            UPDATE complaints
            SET status = ?
            WHERE id = ?
        """, (status, complaint_id))

        if cursor.rowcount == 0:
            return jsonify({
                "success": False,
                "message": "Complaint not found."
            }), 404

    return jsonify({
        "success": True,
        "message": "Complaint status updated.",
        "status": status
    })


# ============================================================
# 15. EMPLOYEE DATABASE SUMMARY
# ============================================================

@app.route("/api/employee/database-summary")
def employee_database_summary():
    if not employee_required():
        return employee_required_message()

    with get_db_connection() as db:
        summary = {
            "cards_count": db.execute(
                "SELECT COUNT(*) FROM cards"
            ).fetchone()[0],

            "transactions_count": db.execute(
                "SELECT COUNT(*) FROM transactions"
            ).fetchone()[0],

            "loans_count": db.execute(
                "SELECT COUNT(*) FROM loan_applications"
            ).fetchone()[0],

            "customers_count": db.execute(
                "SELECT COUNT(*) FROM customers"
            ).fetchone()[0],

            "accounts_count": db.execute(
                "SELECT COUNT(*) FROM accounts"
            ).fetchone()[0],

            "complaints_count": db.execute(
                "SELECT COUNT(*) FROM complaints"
            ).fetchone()[0]
        }

    return jsonify({
        "success": True,
        **summary
    })
# ============================================================
# 15. FINASSIST AI CHATBOT
# Read-only banking intelligence + confirmed demo operations
# ============================================================

def chatbot_emi(principal, annual_rate, months):
    if principal <= 0 or annual_rate < 0 or months <= 0:
        return None

    monthly_rate = annual_rate / 1200

    if monthly_rate == 0:
        return round(principal / months, 2)

    factor = (1 + monthly_rate) ** months

    return round(
        principal * monthly_rate * factor / (factor - 1),
        2
    )


def chatbot_customer_data(customer_id):
    """Fetch records belonging only to the logged-in customer."""

    with get_db_connection() as db:

        customer = db.execute("""
            SELECT customer_id, full_name
            FROM customers
            WHERE customer_id = ?
        """, (customer_id,)).fetchone()

        accounts = db.execute("""
            SELECT id, account_number, account_type, nickname,
                   balance, status, is_primary
            FROM accounts
            WHERE customer_id = ?
            ORDER BY is_primary DESC, id DESC
        """, (customer_id,)).fetchall()

        transactions = db.execute("""
            SELECT t.id, t.transaction_type, t.amount,
                   t.description, t.transaction_date,
                   t.status, t.account_number
            FROM transactions t
            JOIN accounts a
                ON a.account_number = t.account_number
            WHERE a.customer_id = ?
            ORDER BY t.id DESC
            LIMIT 50
        """, (customer_id,)).fetchall()

        cards = db.execute("""
            SELECT id, card_type, last_four_digits,
                   status, expiry_date
            FROM cards
            WHERE customer_id = ?
            ORDER BY id DESC
        """, (customer_id,)).fetchall()

        loans = db.execute("""
            SELECT id, loan_type, amount, tenure_months,
                   status, applied_at
            FROM loan_applications
            WHERE customer_id = ?
            ORDER BY id DESC
        """, (customer_id,)).fetchall()

        complaints = db.execute("""
            SELECT id, subject, message, status, created_at
            FROM complaints
            WHERE customer_id = ?
            ORDER BY id DESC
        """, (customer_id,)).fetchall()

    account_list = [dict(x) for x in accounts]

    active_total = sum(
        float(x["balance"] or 0)
        for x in account_list
        if str(x["status"] or "Active").lower() == "active"
    )

    return {
        "customer": dict(customer) if customer else {},

        "accounts": [
            {
                "account_type": x["account_type"],
                "nickname": x["nickname"],
                "last_four": str(x["account_number"])[-4:],
                "balance": float(x["balance"] or 0),
                "status": x["status"],
                "is_primary": bool(x["is_primary"])
            }
            for x in account_list
        ],

        "total_active_balance": active_total,

        "transactions": [
            {
                "type": x["transaction_type"],
                "amount": float(x["amount"] or 0),
                "description": x["description"],
                "date": x["transaction_date"],
                "status": x["status"],
                "account_last_four": str(x["account_number"])[-4:]
            }
            for x in transactions
        ],

        "cards": [
            {
                "card_id": x["id"],
                "type": x["card_type"],
                "last_four": x["last_four_digits"],
                "status": x["status"],
                "expiry_date": x["expiry_date"]
            }
            for x in cards
        ],

        "loan_applications": [
            dict(x) for x in loans
        ],

        "complaints": [
            dict(x) for x in complaints
        ]
    }


def chatbot_json(success, reply, status=200, **extra):
    return jsonify({
        "success": success,
        "reply": reply,
        "response": reply,
        **extra
    }), status


def ensure_chatbot_action_table(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS chatbot_pending_actions (
            token TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            executed_at TEXT
        )
    """)


def create_chatbot_pending_action(customer_id, action_type, payload):

    token = "".join(
        random.choices(
            string.ascii_letters + string.digits,
            k=32
        )
    )

    with get_db_connection() as db:

        ensure_chatbot_action_table(db)

        db.execute("""
            INSERT INTO chatbot_pending_actions
                (token, customer_id, action_type, payload, status)
            VALUES (?, ?, ?, ?, 'Pending')
        """, (
            token,
            customer_id,
            action_type,
            json.dumps(payload)
        ))

    session["finassist_pending_token"] = token

    return token


def execute_chatbot_pending_action(customer_id, token):
    """Execute a pending action once after confirmation."""

    with get_db_connection() as db:

        db.execute("BEGIN IMMEDIATE")

        ensure_chatbot_action_table(db)

        pending = db.execute("""
            SELECT token, action_type, payload, status
            FROM chatbot_pending_actions
            WHERE token = ? AND customer_id = ?
        """, (token, customer_id)).fetchone()

        if not pending:
            return "I couldn't find that pending request. Please start again.", False

        if pending["status"] != "Pending":
            return "That request has already been processed or cancelled.", False

        payload = json.loads(pending["payload"])
        action = pending["action_type"]

        # BLOCK CARD
        if action == "block_card":

            cur = db.execute("""
                UPDATE cards
                SET status = 'Blocked'
                WHERE id = ? AND customer_id = ?
            """, (
                payload["card_id"],
                customer_id
            ))

            if cur.rowcount != 1:
                return "I couldn't find that card in your profile.", False

            result = (
                f"Your card ending {payload['last_four']} "
                "is now blocked."
            )

        # UNBLOCK CARD
        elif action == "unblock_card":

            cur = db.execute("""
                UPDATE cards
                SET status = 'Active'
                WHERE id = ? AND customer_id = ?
            """, (
                payload["card_id"],
                customer_id
            ))

            if cur.rowcount != 1:
                return "I couldn't find that card in your profile.", False

            result = (
                f"Your card ending {payload['last_four']} "
                "is now active."
            )

        # DEACTIVATE ACCOUNT
        elif action == "deactivate_account":

            cur = db.execute("""
                UPDATE accounts
                SET status = 'Inactive'
                WHERE account_number = ?
                  AND customer_id = ?
                  AND LOWER(status) = 'active'
            """, (
                payload["account_number"],
                customer_id
            ))

            if cur.rowcount != 1:
                return "That active account could not be found.", False

            result = (
                f"Your account ending {payload['last_four']} "
                "is now inactive."
            )

        # ACTIVATE ACCOUNT
        elif action == "activate_account":

            cur = db.execute("""
                UPDATE accounts
                SET status = 'Active'
                WHERE account_number = ?
                  AND customer_id = ?
                  AND LOWER(status) = 'inactive'
            """, (
                payload["account_number"],
                customer_id
            ))

            if cur.rowcount != 1:
                return "That inactive account could not be found.", False

            result = (
                f"Your account ending {payload['last_four']} "
                "is now active."
            )

        # SUBMIT COMPLAINT
        elif action == "submit_complaint":

            cur = db.execute("""
                INSERT INTO complaints (
                    customer_id, subject, message, status
                )
                VALUES (?, ?, ?, 'Pending')
            """, (
                customer_id,
                payload["subject"],
                payload["message"]
            ))

            result = (
                f"Your complaint was submitted. "
                f"Complaint ID: {cur.lastrowid}. "
                "Status: Pending."
            )

        # APPLY FOR LOAN
        elif action == "apply_loan":

            cur = db.execute("""
                INSERT INTO loan_applications (
                    customer_id, loan_type, amount,
                    tenure_months, status
                )
                VALUES (?, ?, ?, ?, 'Pending')
            """, (
                customer_id,
                payload["loan_type"],
                payload["amount"],
                payload["tenure_months"]
            ))

            result = (
                f"Your {payload['loan_type']} loan application "
                f"was submitted. Application ID: {cur.lastrowid}. "
                "Status: Pending. This is not an approval."
            )

                # DEPOSIT, DEBIT OR TRANSFER

        elif action in ("credit", "debit", "transfer"):

            amount = float(payload["amount"])
            source = payload["source_account"]

            description = payload.get("description") or "Customer transaction"

            source_row = db.execute("""
                SELECT balance, status
                FROM accounts
                WHERE account_number = ?
                  AND customer_id = ?
            """, (source, customer_id)).fetchone()

            if (
                not source_row
                or str(source_row["status"] or "").lower() != "active"
            ):
                return "The selected account is inactive or unavailable. No money was changed.", False

            current_balance = float(source_row["balance"] or 0)

            # DEPOSIT / CREDIT

            if action == "credit":

                cur = db.execute("""
                    UPDATE accounts
                    SET balance = balance + ?
                    WHERE account_number = ?
                      AND customer_id = ?
                      AND LOWER(COALESCE(status, '')) = 'active'
                """, (amount, source, customer_id))

                if cur.rowcount != 1:
                    return "The deposit could not be completed.", False

                db.execute("""
                    INSERT INTO transactions (
                        account_number, transaction_type, amount,
                        description, status
                    )
                    VALUES (?, 'Credit', ?, ?, 'Success')
                """, (source, amount, description))

                result = (
                    f"₹{amount:,.2f} was added successfully "
                    f"to account ending {source[-4:]}. "
                    f"New balance: ₹{current_balance + amount:,.2f}."
                )

            # TRANSFER

            elif action == "transfer":

                destination = payload["destination_account"]

                dest_row = db.execute("""
                    SELECT balance, status
                    FROM accounts
                    WHERE account_number = ?
                      AND customer_id = ?
                """, (destination, customer_id)).fetchone()

                if (
                    not dest_row
                    or str(dest_row["status"] or "").lower() != "active"
                    or destination == source
                ):
                    return "The destination account is unavailable.", False

                debit_cur = db.execute("""
                    UPDATE accounts
                    SET balance = balance - ?
                    WHERE account_number = ?
                      AND customer_id = ?
                      AND LOWER(COALESCE(status, '')) = 'active'
                      AND balance >= ?
                """, (amount, source, customer_id, amount))

                if debit_cur.rowcount != 1:
                    return "The transfer could not be completed. Insufficient funds.", False

                db.execute("""
                    UPDATE accounts
                    SET balance = balance + ?
                    WHERE account_number = ?
                      AND customer_id = ?
                """, (amount, destination, customer_id))

                db.execute("""
                    INSERT INTO transactions (
                        account_number, transaction_type, amount,
                        description, status
                    )
                    VALUES (?, 'Debit', ?, ?, 'Success')
                """, (source, amount, f"Transfer to account ending {destination[-4:]}"))

                db.execute("""
                    INSERT INTO transactions (
                        account_number, transaction_type, amount,
                        description, status
                    )
                    VALUES (?, 'Credit', ?, ?, 'Success')
                """, (destination, amount, f"Transfer from account ending {source[-4:]}"))

                result = (
                    f"₹{amount:,.2f} transferred successfully "
                    f"from account ending {source[-4:]} "
                    f"to account ending {destination[-4:]}."
                )

            # DEBIT / WITHDRAWAL

            else:

                debit_cur = db.execute("""
                    UPDATE accounts
                    SET balance = balance - ?
                    WHERE account_number = ?
                      AND customer_id = ?
                      AND LOWER(COALESCE(status, '')) = 'active'
                      AND balance >= ?
                """, (amount, source, customer_id, amount))

                if debit_cur.rowcount != 1:
                    return "The debit could not be completed. Insufficient funds.", False

                db.execute("""
                    INSERT INTO transactions (
                        account_number, transaction_type, amount,
                        description, status
                    )
                    VALUES (?, 'Debit', ?, ?, 'Success')
                """, (source, amount, description))

                result = (
                    f"₹{amount:,.2f} was debited successfully "
                    f"from account ending {source[-4:]}. "
                    f"Remaining balance: ₹{current_balance - amount:,.2f}."
                )

        else:
            return "This action is not supported.", False

        db.execute("""
            UPDATE chatbot_pending_actions
            SET status = 'Completed',
                executed_at = CURRENT_TIMESTAMP
            WHERE token = ? AND customer_id = ?
        """, (token, customer_id))

        session.pop("finassist_pending_token", None)

        return result, True
    # ============================================================
# 15A. CHATBOT ACTION PREPARATION
# ============================================================

def chatbot_prepare_action(customer_id, message):

    text = message.strip()
    lower = text.lower()
   

        # Allow read-only card enquiries to reach the card lookup section.
    if "card" in lower and not re.search(
        r"\b(block|freeze|unblock|activate)\b", lower
    ):
        return None, None

    # UNBLOCK / ACTIVATE CARD
    if re.search(r"\b(unblock|activate)\b", lower) and "card" in lower:

        with get_db_connection() as db:
            cards = db.execute("""
                SELECT id, last_four_digits, card_type, status
                FROM cards
                WHERE customer_id = ?
                ORDER BY id DESC
            """, (customer_id,)).fetchall()

        blocked = [
            dict(x) for x in cards
            if str(x["status"] or "").lower() == "blocked"
        ]

        match = re.search(
            r"(?:ending(?:\s+with)?|last\s*4|last\s+four)\s*(\d{4})\b",
            lower
        )

        requested_type = (
            "credit" if "credit" in lower
            else "debit" if "debit" in lower
            else None
        )

        candidates = blocked

        if requested_type:
            candidates = [
                x for x in candidates
                if requested_type in str(x["card_type"]).lower()
            ]

        if match:
            candidates = [
                x for x in candidates
                if str(x["last_four_digits"]).zfill(4) == match.group(1)
            ]

        if len(candidates) != 1:
            return (
                "Please specify the card type and last four digits "
                "of the blocked card."
                if not candidates else
                "More than one card matches. Please specify its type "
                "and last four digits."
            ), None

        selected = candidates[0]

        token = create_chatbot_pending_action(
            customer_id,
            "unblock_card",
            {
                "card_id": selected["id"],
                "last_four": selected["last_four_digits"]
            }
        )

        return (
            f"Please confirm: unblock your {selected['card_type']} "
            f"card ending {selected['last_four_digits']}? "
            "Reply CONFIRM or CANCEL."
        ), token

    # BLOCK CARD
    if (
        re.search(r"\b(block|freeze)\b", lower)
        and "card" in lower
    ):

        with get_db_connection() as db:
            cards = db.execute("""
                SELECT id, last_four_digits, card_type, status
                FROM cards
                WHERE customer_id = ?
                ORDER BY id DESC
            """, (customer_id,)).fetchall()

        active = [
            dict(x) for x in cards
            if str(x["status"] or "").lower() == "active"
        ]

        if not active:
            return "I couldn't find an active card to block.", None

        match = re.search(
            r"(?:ending(?:\s+with)?|last\s*4|last\s+four)\s*(\d{4})\b",
            lower
        )

        requested_type = (
            "credit" if "credit" in lower
            else "debit" if "debit" in lower
            else None
        )

        candidates = active

        if requested_type:
            candidates = [
                x for x in candidates
                if requested_type in str(x["card_type"]).lower()
            ]

        if match:
            candidates = [
                x for x in candidates
                if str(x["last_four_digits"]).zfill(4) == match.group(1)
            ]

        if len(candidates) != 1:
            return (
                "Please specify the card type and last four digits "
                "of the card you want to block."
                if not candidates else
                "More than one card matches. Please specify its type "
                "and last four digits."
            ), None

        selected = candidates[0]

        token = create_chatbot_pending_action(
            customer_id,
            "block_card",
            {
                "card_id": selected["id"],
                "last_four": selected["last_four_digits"]
            }
        )

        return (
            f"Please confirm: block your {selected['card_type']} "
            f"card ending {selected['last_four_digits']}? "
            "Reply CONFIRM to proceed or CANCEL."
        ), token

    # DEACTIVATE ACCOUNT
    if (
        ("deactivate" in lower or "close" in lower)
        and "account" in lower
    ):

        with get_db_connection() as db:
            accounts = db.execute("""
                SELECT account_number, nickname, account_type, status
                FROM accounts
                WHERE customer_id = ?
                ORDER BY is_primary DESC, id DESC
            """, (customer_id,)).fetchall()

        active = [
            dict(x) for x in accounts
            if str(x["status"] or "").lower() == "active"
        ]

        match = re.search(r"(\d{4})", lower)

        selected = next(
            (
                x for x in active
                if match and x["account_number"].endswith(match.group(1))
            ),
            None
        )

        if not selected and len(active) == 1:
            selected = active[0]

        if not selected:
            choices = ", ".join(
                f"{x['nickname'] or x['account_type']} "
                f"ending {str(x['account_number'])[-4:]}"
                for x in active
            )

            return (
                "Which active account should I deactivate? "
                f"{choices or 'No active accounts found.'} "
                "Tell me its last four digits."
            ), None

        token = create_chatbot_pending_action(
            customer_id,
            "deactivate_account",
            {
                "account_number": selected["account_number"],
                "last_four": selected["account_number"][-4:]
            }
        )

        return (
            f"Please confirm: mark your account ending "
            f"{selected['account_number'][-4:]} inactive? "
            "This demo action may affect account access. "
            "Reply CONFIRM or CANCEL."
        ), token

    # ACTIVATE ACCOUNT
    if "activate" in lower and "account" in lower:

        with get_db_connection() as db:
            accounts = db.execute("""
                SELECT account_number, nickname, account_type, status
                FROM accounts
                WHERE customer_id = ?
                ORDER BY id DESC
            """, (customer_id,)).fetchall()

        inactive = [
            dict(x) for x in accounts
            if str(x["status"] or "").lower() == "inactive"
        ]

        match = re.search(r"(\d{4})", lower)

        selected = next(
            (
                x for x in inactive
                if match and x["account_number"].endswith(match.group(1))
            ),
            None
        )

        if not selected and len(inactive) == 1:
            selected = inactive[0]

        if not selected:
            return (
                "Tell me the last four digits of the "
                "inactive account you want to activate."
            ), None

        token = create_chatbot_pending_action(
            customer_id,
            "activate_account",
            {
                "account_number": selected["account_number"],
                "last_four": selected["account_number"][-4:]
            }
        )

        return (
            f"Please confirm: activate your account ending "
            f"{selected['account_number'][-4:]}? Reply CONFIRM or CANCEL."
        ), token

    # SUBMIT COMPLAINT
    if any(
        x in lower
        for x in (
            "submit complaint",
            "raise complaint",
            "file complaint",
            "register complaint"
        )
    ):

        details = re.sub(
            r"^(please\s+)?(submit|raise|file|register)\s+"
            r"(a\s+)?complaint\s*[:,-]?\s*",
            "",
            text,
            flags=re.I
        ).strip()

        if " - " not in details:
            return (
                "Please provide the complaint like this:\n"
                "Complaint: UPI payment issue - "
                "₹2,000 was debited but the payment failed."
            ), None

        subject, body = details.split(" - ", 1)

        subject = subject.strip()
        body = body.strip()

        if not subject or not body:
            return (
                "Please provide both a short complaint subject "
                "and its details."
            ), None

        token = create_chatbot_pending_action(
            customer_id,
            "submit_complaint",
            {
                "subject": subject[:150],
                "message": body[:5000]
            }
        )

        return (
            f"Please confirm submitting this complaint:\n"
            f"Subject: {subject}\n"
            f"Details: {body}\n"
            "Reply CONFIRM or CANCEL."
        ), token

    # APPLY FOR LOAN
    if re.search(
        r"^(?:please\s+)?(?:apply for|apply loan|submit loan|i want to apply|i want a loan)\b",
        lower
    ):

        loan_match = re.search(
            r"(home|personal|education|vehicle|gold|business)\s+loan",
            lower
        )

        numbers = re.findall(
            r"\d+(?:,\d{3})*(?:\.\d+)?",
            text
        )

        if not loan_match or len(numbers) < 2:
            return (
                "To apply, send the loan type, amount and tenure "
                "in months. Example: Apply for home loan of "
                "500000 for 60 months."
            ), None

        loan_type = loan_match.group(1).title()
        amount = float(numbers[0].replace(",", ""))
        tenure = int(float(numbers[1].replace(",", "")))

        if (
            amount <= 0
            or amount > 100000000
            or tenure < 1
            or tenure > 360
        ):
            return (
                "Please enter a valid loan amount and a tenure "
                "between 1 and 360 months."
            ), None

        token = create_chatbot_pending_action(
            customer_id,
            "apply_loan",
            {
                "loan_type": loan_type,
                "amount": amount,
                "tenure_months": tenure
            }
        )

        return (
            f"Please confirm your {loan_type} loan application "
            f"for ₹{amount:,.2f} over {tenure} months. "
            "It will be submitted as Pending, not approved. "
            "Reply CONFIRM or CANCEL."
        ), token

                    # DEPOSIT, DEBIT OR TRANSFER

    is_card_query = any(term in lower for term in (
        "debit card",
        "debit cards",
        "show cards",
        "show my cards",
        "my cards",
        "card details",
        "card information",
        "list cards"
    ))

    is_deposit = any(term in lower for term in (
        "deposit",
        "add money",
        "add funds",
        "credit",
        "credit amount"
    ))

    is_transfer = any(term in lower for term in (
        "transfer",
        "send money"
    ))

    is_debit = any(term in lower for term in (
        "deduct",
        "withdraw",
        "pay from my account",
        "spend",
        "debit ₹",
        "debit rs",
        "debit amount"
    ))

    is_money_action = is_deposit or is_transfer or is_debit

    if is_money_action and not is_card_query:

        # Check for conflicting operation types
        if sum((is_deposit, is_transfer, is_debit)) > 1:
            return "Please request only one banking operation at a time.", None

        # Extract amount
        amounts = re.findall(
            r"(?:₹|rs\.?\s*)?([0-9][0-9,]*(?:\.\d{1,2})?)",
            text,
            flags=re.I
        )

        if not amounts:
            return (
                "Please specify the amount. Example: Deposit 1000 "
                "or Deduct 500 from account ending 1234."
            ), None

        amount = float(amounts[0].replace(",", ""))

        if amount <= 0 or amount > 100000000:
            return "Please enter a valid amount.", None

        # Load customer accounts
        with get_db_connection() as db:
            accounts = db.execute("""
                SELECT account_number, balance, status
                FROM accounts
                WHERE customer_id = ?
            """, (customer_id,)).fetchall()

        active = [
            dict(x) for x in accounts
            if str(x["status"] or "").strip().lower() == "active"
        ]

        if not active:
            return "You don't have any active accounts.", None

        # Identify source/account
        if is_deposit:
            account_match = re.search(
                r"(?:to|into|in)\s+(?:my\s+)?"
                r"(?:account\s+)?(?:ending\s+)?(\d{4})",
                lower
            )
        else:
            account_match = re.search(
                r"(?:from|source)\s+(?:my\s+)?"
                r"(?:account\s+)?(?:ending\s+)?(\d{4})",
                lower
            )

        account = None

        if account_match:
            account = next(
                (
                    x for x in active
                    if str(x["account_number"]).endswith(
                        account_match.group(1)
                    )
                ),
                None
            )

            if not account:
                return (
                    "I couldn't find that active account. "
                    "Please check the last four digits."
                ), None

        elif is_deposit:
            account = active[0]

        else:
            account = next(
                (
                    x for x in active
                    if float(x["balance"] or 0) >= amount
                ),
                None
            )

        if not account:
            return (
                "I couldn't find an active account with enough funds."
            ), None

        # DEPOSIT
        if is_deposit:

            action_type = "credit"

            payload = {
                "amount": amount,
                "source_account": account["account_number"],
                "description": "Customer deposit"
            }

            preview = (
                f"deposit ₹{amount:,.2f} into account ending "
                f"{account['account_number'][-4:]}"
            )

        # TRANSFER
        elif is_transfer:

            dest_match = re.search(
                r"(?:to|destination)\s+(?:my\s+)?"
                r"(?:account\s+)?(?:ending\s+)?(\d{4})",
                lower
            )

            if not dest_match:
                return (
                    "Please specify the destination account's last "
                    "four digits. Example: Transfer 1000 from account "
                    "ending 1234 to account ending 5678."
                ), None

            destination = next(
                (
                    x for x in active
                    if str(x["account_number"]).endswith(
                        dest_match.group(1)
                    )
                ),
                None
            )

            if not destination:
                return (
                    "I couldn't find that destination account. "
                    "Please check its last four digits."
                ), None

            if destination["account_number"] == account["account_number"]:
                return "Choose two different accounts for a transfer.", None

            if float(account["balance"] or 0) < amount:
                return "Insufficient balance for this transfer.", None

            action_type = "transfer"

            payload = {
                "amount": amount,
                "source_account": account["account_number"],
                "destination_account": destination["account_number"],
                "description": "Transfer between own accounts"
            }

            preview = (
                f"transfer ₹{amount:,.2f} from account ending "
                f"{account['account_number'][-4:]} to account ending "
                f"{destination['account_number'][-4:]}"
            )

        # DEBIT / DEDUCTION
        else:

            if float(account["balance"] or 0) < amount:
                return "Insufficient balance for this deduction.", None

            action_type = "debit"

            description_match = re.search(
                r"\b(?:for|at|on)\s+(.+)$",
                text,
                re.I
            )

            description = (
                description_match.group(1).strip()[:120]
                if description_match
                else "Customer-requested debit"
            )

            payload = {
                "amount": amount,
                "source_account": account["account_number"],
                "description": description
            }

            preview = (
                f"deduct ₹{amount:,.2f} from account ending "
                f"{account['account_number'][-4:]}"
            )

        # Create confirmation request
        token = create_chatbot_pending_action(
            customer_id,
            action_type,
            payload
        )

        return (
            "Please confirm this banking operation: "
            f"{preview}. Reply CONFIRM to proceed or CANCEL."
        ), token

    return None, None

# ============================================================
# 15B. CHATBOT API
# ============================================================

loan_bank_offers = {
    "personal": [
        {"bank": "SBI", "type": "Personal Loan", "min_rate": 10.00, "max_rate": 15.00, "source": "https://sbi.bank.in"},
        {"bank": "HDFC Bank", "type": "Personal Loan", "min_rate": 10.50, "max_rate": 18.00, "source": "https://www.hdfcbank.com"},
        {"bank": "ICICI Bank", "type": "Personal Loan", "min_rate": 9.99, "max_rate": 16.50, "source": "https://www.icicibank.com"},
        {"bank": "Axis Bank", "type": "Personal Loan", "min_rate": 10.49, "max_rate": 18.00, "source": "https://www.axisbank.com"},
        {"bank": "IDFC FIRST Bank", "type": "Personal Loan", "min_rate": 9.99, "max_rate": 20.00, "source": "https://www.idfcfirstbank.com"}
    ],

    "home": [
        {"bank": "SBI", "type": "Home Loan", "min_rate": 7.25, "max_rate": 9.50, "source": "https://sbi.bank.in"},
        {"bank": "HDFC Bank", "type": "Home Loan", "min_rate": 7.90, "max_rate": 10.00, "source": "https://www.hdfcbank.com"},
        {"bank": "ICICI Bank", "type": "Home Loan", "min_rate": 7.70, "max_rate": 9.80, "source": "https://www.icicibank.com"},
        {"bank": "Axis Bank", "type": "Home Loan", "min_rate": 8.35, "max_rate": 10.25, "source": "https://www.axisbank.com"},
        {"bank": "Bank of Baroda", "type": "Home Loan", "min_rate": 7.45, "max_rate": 9.50, "source": "https://bankofbaroda.bank.in"}
    ],

    "education": [
        {"bank": "SBI", "type": "Education Loan", "min_rate": 8.15, "max_rate": 11.50, "source": "https://sbi.bank.in"},
        {"bank": "HDFC Bank", "type": "Education Loan", "min_rate": 9.50, "max_rate": 13.00, "source": "https://www.hdfcbank.com"},
        {"bank": "ICICI Bank", "type": "Education Loan", "min_rate": 9.50, "max_rate": 13.50, "source": "https://www.icicibank.com"},
        {"bank": "Axis Bank", "type": "Education Loan", "min_rate": 10.00, "max_rate": 14.00, "source": "https://www.axisbank.com"},
        {"bank": "Bank of Baroda", "type": "Education Loan", "min_rate": 8.50, "max_rate": 11.00, "source": "https://bankofbaroda.bank.in"}
    ],

    "vehicle": [
        {"bank": "SBI", "type": "Car Loan", "min_rate": 8.75, "max_rate": 11.00, "source": "https://sbi.bank.in"},
        {"bank": "HDFC Bank", "type": "Car Loan", "min_rate": 8.80, "max_rate": 12.00, "source": "https://www.hdfcbank.com"},
        {"bank": "ICICI Bank", "type": "Car Loan", "min_rate": 8.75, "max_rate": 11.50, "source": "https://www.icicibank.com"},
        {"bank": "Axis Bank", "type": "Car Loan", "min_rate": 9.00, "max_rate": 12.00, "source": "https://www.axisbank.com"},
        {"bank": "Bank of Baroda", "type": "Vehicle Loan", "min_rate": 8.80, "max_rate": 11.25, "source": "https://bankofbaroda.bank.in"}
    ],

    "gold": [
        {"bank": "SBI", "type": "Gold Loan", "min_rate": 8.75, "max_rate": 10.50, "source": "https://sbi.bank.in"},
        {"bank": "HDFC Bank", "type": "Gold Loan", "min_rate": 9.00, "max_rate": 12.00, "source": "https://www.hdfcbank.com"},
        {"bank": "ICICI Bank", "type": "Gold Loan", "min_rate": 9.00, "max_rate": 12.50, "source": "https://www.icicibank.com"},
        {"bank": "Axis Bank", "type": "Gold Loan", "min_rate": 9.50, "max_rate": 14.00, "source": "https://www.axisbank.com"},
        {"bank": "Bank of Baroda", "type": "Gold Loan", "min_rate": 8.60, "max_rate": 10.50, "source": "https://bankofbaroda.bank.in"}
    ],

    "business": [
        {"bank": "SBI", "type": "Business Loan", "min_rate": 10.00, "max_rate": 15.00, "source": "https://sbi.bank.in"},
        {"bank": "HDFC Bank", "type": "Business Loan", "min_rate": 11.00, "max_rate": 18.00, "source": "https://www.hdfcbank.com"},
        {"bank": "ICICI Bank", "type": "Business Loan", "min_rate": 10.50, "max_rate": 17.00, "source": "https://www.icicibank.com"},
        {"bank": "Axis Bank", "type": "Business Loan", "min_rate": 11.00, "max_rate": 18.50, "source": "https://www.axisbank.com"},
        {"bank": "IDFC FIRST Bank", "type": "Business Loan", "min_rate": 10.25, "max_rate": 19.00, "source": "https://www.idfcfirstbank.com"}
    ]
}

@app.route("/api/chatbot", methods=["POST"])
@app.route("/api/chat", methods=["POST"])
def chatbot():
    """Rule-based banking assistant. No external AI/API dependency."""

    if not customer_required():
        return login_required_message()

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", data.get("query", ""))).strip()

    if not message:
        return chatbot_json(False, "Please enter a message.", 400)

    if len(message) > 2000:
        return chatbot_json(False, "Message is too long.", 400)

    customer_id = session["customer_id"]
    lower = message.lower().strip()
    normalized = re.sub(r"\s+", " ", lower)

    try:
        # CONFIRM OR CANCEL A PENDING ACTION
        pending_token = session.get("finassist_pending_token")

        if pending_token and normalized in (
            "confirm", "yes", "confirm it", "proceed",
            "do it", "yes confirm"
        ):
            reply, ok = execute_chatbot_pending_action(
                customer_id,
                pending_token
            )

            return chatbot_json(
                ok,
                reply,
                200 if ok else 400
            )

        if pending_token and normalized in (
            "cancel", "no", "don't", "do not",
            "cancel it", "no cancel"
        ):
            with get_db_connection() as db:
                ensure_chatbot_action_table(db)

                db.execute("""
                    UPDATE chatbot_pending_actions
                    SET status = 'Cancelled'
                    WHERE token = ?
                      AND customer_id = ?
                      AND status = 'Pending'
                """, (pending_token, customer_id))

            session.pop("finassist_pending_token", None)

            return chatbot_json(
                True,
                "Okay, I cancelled that request. No changes were made."
            )

        # GREETINGS
        greetings = {
            "hi", "hii", "hello", "hey", "hey there",
            "good morning", "good afternoon",
            "good evening", "good night"
        }

        if normalized in greetings or normalized in (
            "hi finassist", "hello finassist", "hey finassist"
        ):
            customer_name = session.get("customer_name") or "there"

            return chatbot_json(
                True,
                f"Hello {customer_name}! Welcome to FinAssist. "
                "I can help with accounts, cards, transactions, "
                "loans and complaints."
            )

        if normalized in (
            "thanks", "thank you", "thankyou", "thanks finassist"
        ):
            return chatbot_json(
                True,
                "You're welcome! Let me know if you need help with anything else."
            )

        if normalized in (
            "bye", "goodbye", "see you", "goodbye finassist"
        ):
            return chatbot_json(
                True,
                "Goodbye! Thank you for using FinAssist."
            )

        # HELP
        if normalized in (
            "help", "what can you do",
            "what can you help me with", "services"
        ):
            return chatbot_json(
                True,
                "I can help you with:\n"
                "• View accounts and balances\n"
                "• Activate or deactivate an account\n"
                "• View cards, block or unblock a card\n"
                "• View transactions and make confirmed demo debits\n"
                "• View loan types and your loan applications\n"
                "• Register and track complaints\n"
                "• Explain common banking terms"
            )

        # LOAD AUTHENTICATED CUSTOMER RECORDS
        ctx = chatbot_customer_data(customer_id)
        
        
        # TRANSACTION HISTORY
        transaction_keywords = (
            "transaction",
            "payment history",
            "payment record",
            "bank statement",
            "account statement",
            "recent activity",
            "money received",
            "money sent"
        )

        if any(term in normalized for term in transaction_keywords):

            transactions = ctx["transactions"]

            if not transactions:
                return chatbot_json(
                    True,
                    "You don't have any transactions recorded yet."
                )

            # Extract the requested transaction count.
            count_match = re.search(
                r"\b(?:last|latest|recent)\s+(\d+)\s+transactions?\b",
                normalized
            )

            if count_match:
                requested_count = int(count_match.group(1))
            else:
                requested_count = 20  # Default limit

            # Prevent invalid or excessive requests.
            requested_count = max(1, min(requested_count, 50))

            # Display only the requested number.
            transactions = transactions[:requested_count]

            transaction_lines = []

            for index, transaction in enumerate(transactions, start=1):

                transaction_type = transaction["type"] or "Transaction"
                amount = float(transaction["amount"] or 0)
                description = transaction["description"] or "Bank transaction"
                date = transaction["date"] or "Date unavailable"
                status = transaction["status"] or "Unknown"
                account = transaction["account_last_four"] or "N/A"

                transaction_lines.append(
                    f"{index}. {transaction_type}\n"
                    f"   Amount: ₹{amount:,.2f}\n"
                    f"   Description: {description}\n"
                    f"   Date: {date}\n"
                    f"   Account: Ending {account}\n"
                    f"   Status: {status}"
                )

            return chatbot_json(
                True,
                f"Here are your latest {len(transactions)} transactions:\n\n"
                + "\n\n".join(transaction_lines)
            )

        # EMI CALCULATION
        if "emi" in normalized:
            numbers = re.findall(
                r"\d+(?:,\d{3})*(?:\.\d+)?",
                message
            )

            if len(numbers) >= 3:
                principal = float(numbers[0].replace(",", ""))
                rate = float(numbers[1].replace(",", ""))
                months = int(float(numbers[2].replace(",", "")))

                if (
                    principal > 0
                    and 0 <= rate <= 100
                    and 1 <= months <= 600
                ):
                    emi = chatbot_emi(
                        principal,
                        rate,
                        months
                    )

                    total = emi * months

                    return chatbot_json(
                        True,
                        f"Estimated EMI: ₹{emi:,.2f} per month\n"
                        f"Loan amount: ₹{principal:,.2f}\n"
                        f"Interest rate: {rate}% per year\n"
                        f"Tenure: {months} months\n"
                        f"Total interest: ₹{total-principal:,.2f}\n"
                        f"Total payment: ₹{total:,.2f}\n\n"
                        "This is an estimate, not a bank quote."
                    )

            return chatbot_json(
                True,
                "To calculate EMI, provide the loan amount, annual interest rate "
                "and tenure in months. Example: EMI for 500000 at 9% for 60 months."
            )

        # ACCOUNT GUIDANCE
        if any(term in normalized for term in (
            "how to add account",
            "add a new account",
            "open another account",
            "how can i open an account"
        )):
            return chatbot_json(
                True,
                "To add an account, open the Accounts section of this website "
                "and choose Add Account. The current form supports Savings "
                "and Current accounts."
            )

        # CARD GUIDANCE
        if any(term in normalized for term in (
            "how to add card",
            "add a new card",
            "request a new card",
            "how can i get a card"
        )):
            return chatbot_json(
                True,
                "To add a card in this demo, open the Cards section and choose "
                "Add Card. Select one of your active linked accounts and "
                "complete the form."
            )

        # ACCOUNT TYPES
        if any(term in normalized for term in (
            "what are the types of accounts",
            "types of bank accounts",
            "different types of accounts",
            "account types"
        )):
            return chatbot_json(
                True,
                "Common bank account types include Savings (for personal saving), "
                "Current (for frequent business transactions), Salary (for salary "
                "deposits), Fixed Deposit/FD (a lump sum kept for a fixed term), "
                "and Recurring Deposit/RD (regular deposits over a fixed term). "
                "The account types available depend on the bank."
            )

        # BANKING DEFINITIONS
        quick_definitions = [
            (
                ("what is upi", "upi meaning"),
                "UPI (Unified Payments Interface) lets you make instant "
                "bank-to-bank payments using a UPI app or ID."
            ),
            (
                ("what is ifsc", "ifsc meaning"),
                "IFSC is an 11-character code that identifies a bank branch "
                "for electronic fund transfers."
            ),
            (
                ("what is a savings account", "savings account meaning"),
                "A Savings Account is intended for saving money, making "
                "deposits and withdrawals, and earning interest according "
                "to the bank's terms."
            ),
            (
                ("what is a current account", "current account meaning"),
                "A Current Account is generally designed for businesses "
                "and customers who need frequent transactions."
            ),
            (
                ("what is fixed deposit", "what is an fd", "fixed deposit meaning"),
                "A Fixed Deposit lets you deposit a lump sum for a chosen "
                "period at an agreed interest rate. Premature withdrawal "
                "rules vary by bank."
            ),
            (
                ("what is debit card", "debit card meaning"),
                "A Debit Card lets you pay using funds available in its "
                "linked bank account."
            ),
            (
                ("what is credit card", "credit card meaning"),
                "A Credit Card lets you borrow up to a lender-approved "
                "limit and repay according to the billing terms."
            ),
            (
                ("what is minimum balance", "minimum balance meaning"),
                "Minimum balance is the amount an account may need to "
                "maintain. The requirement and charges depend on the "
                "bank and account type."
            )
        ]

        for phrases, answer in quick_definitions:
            if any(phrase in normalized for phrase in phrases):
                return chatbot_json(True, answer)

            
        # PREPARE SUPPORTED WRITE ACTIONS
        action_reply, action_token = chatbot_prepare_action(
            customer_id,
            message
        )

        if action_reply:
            return chatbot_json(
                True,
                action_reply,
                action_token=bool(action_token)
            )

        
        # ACCOUNT AND BALANCE QUERIES
        account_query = any(term in normalized for term in (
            "account",
            "balance",
            "available funds",
            "how much money",
            "how much have i got",
            "my savings",
            "my current"
        ))

        if account_query:
            accounts = ctx["accounts"]

            if not accounts:
                return chatbot_json(
                    True,
                    "You don't have any accounts linked to your profile."
                )

            # Detect account type.
            wanted_type = None

            for account_type in (
                "savings",
                "current",
                "salary",
                "fixed deposit",
                "fd",
                "recurring deposit"
            ):
                if account_type in normalized:
                    wanted_type = (
                        "fixed deposit"
                        if account_type == "fd"
                        else account_type
                    )
                    break

            # Detect requested account's last four digits.
            last4_match = re.search(
                r"(?:ending(?:\s+with)?|last\s+four|last\s+4)"
                r"\s*(?:in\s+)?(\d{4})",
                normalized
            )

            selected_accounts = accounts

            # Filter by account type.
            if wanted_type:
                selected_accounts = [
                    account for account in selected_accounts
                    if wanted_type in str(
                        account["account_type"]
                    ).lower()
                    or (
                        wanted_type == "fixed deposit"
                        and "fd" in str(
                            account["account_type"]
                        ).lower()
                    )
                ]

            # Filter by exact account number suffix.
            if last4_match:
                requested_last4 = last4_match.group(1)

                selected_accounts = [
                    account for account in selected_accounts
                    if account["last_four"] == requested_last4
                ]

            if not selected_accounts:
                return chatbot_json(
                    True,
                    "I couldn't find an account matching those details. "
                    "Please check the account type and last four digits."
                )

            lines = [
                f"{a['account_type']} (ending {a['last_four']}): "
                f"₹{a['balance']:,.2f} — "
                f"{a['status'] or 'Active'}"
                for a in selected_accounts
            ]

            total = sum(
                a["balance"]
                for a in selected_accounts
                if str(a["status"] or "Active").lower() == "active"
            )

            heading = (
                "Your requested account:"
                if last4_match
                else (
                    f"Your {wanted_type.title()} account(s):"
                    if wanted_type
                    else "Your accounts:"
                )
            )

            return chatbot_json(
                True,
                heading + "\n"
                + "\n".join(lines)
                + f"\n\nTotal active balance shown: ₹{total:,.2f}"
            )

        # CARD INFORMATION
        
        # CARD INFORMATION
        if "card" in normalized:

            cards = ctx["cards"]

            if not cards:
                return chatbot_json(
                    True,
                    "You don't have any cards linked to your profile."
                )

            # Detect whether the user asks for a count.
            count_query = any(term in normalized for term in (
                "how many",
                "count",
                "number of"
            ))

            # Detect requested card type.
            requested_card_type = None

            if "credit" in normalized:
                requested_card_type = "credit"

            elif "debit" in normalized:
                requested_card_type = "debit"

            # Filter cards by type.
            selected_cards = cards

            if requested_card_type:
                selected_cards = [
                    card for card in cards
                    if str(card["type"]).lower() == requested_card_type
                ]

            # Count cards.
            if count_query:
                card_count = len(selected_cards)

                if requested_card_type:
                    return chatbot_json(
                        True,
                        f"You have {card_count} "
                        f"{requested_card_type} card(s)."
                    )

                return chatbot_json(
                    True,
                    f"You have {card_count} card(s) in total: "
                    f"{sum(1 for c in cards if str(c['type']).lower() == 'credit')} "
                    "credit card(s) and "
                    f"{sum(1 for c in cards if str(c['type']).lower() == 'debit')} "
                    "debit card(s)."
                )

            if not selected_cards:
                return chatbot_json(
                    True,
                    f"You don't have any {requested_card_type or ''} "
                    "cards registered."
                )

            card_lines = [
                f"{c['type']} card ending {c['last_four']}: "
                f"{c['status']} "
                f"(Expiry: {c['expiry_date'] or 'Not available'})"
                for c in selected_cards
            ]

            heading = (
                f"Your {requested_card_type} cards:"
                if requested_card_type
                else "Your cards:"
            )

            return chatbot_json(
                True,
                heading + "\n" + "\n".join(card_lines)
            )


                      # LOAN APPLICATION INFORMATION

        if any(term in normalized for term in (
            "loan application",
            "loan applications",
            "my loans",
            "show loans",
            "loan status",
            "application status",
            "check my loans"
        )):
            loans = ctx["loan_applications"]

            if not loans:
                return chatbot_json(
                    True,
                    "You don't have any loan applications yet."
                )

            loan_lines = []

            for loan in loans:
                loan_lines.append(
                    f"Application ID: {loan['id']}\n"
                    f"Loan Type: {loan['loan_type']}\n"
                    f"Amount: ₹{float(loan['amount'] or 0):,.2f}\n"
                    f"Tenure: {loan['tenure_months']} months\n"
                    f"Status: {loan['status']}\n"
                    f"Applied On: {loan['applied_at']}"
                )

            return chatbot_json(
                True,
                "Your loan applications:\n\n"
                + "\n\n".join(loan_lines)
            )

        # LOAN OFFERS AND RECOMMENDATIONS

        loan_categories = {
            "personal": {
                "name": "Personal Loan",
                "purpose": "Medical expenses, travel, emergencies and personal needs."
            },
            "home": {
                "name": "Home Loan",
                "purpose": "Buying, constructing or renovating a house."
            },
            "education": {
                "name": "Education Loan",
                "purpose": "Tuition fees, higher studies and education expenses."
            },
            "vehicle": {
                "name": "Vehicle Loan",
                "purpose": "Buying a new or used car, bike or other vehicle."
            },
            "gold": {
                "name": "Gold Loan",
                "purpose": "Borrowing against eligible gold jewellery."
            },
            "business": {
                "name": "Business Loan",
                "purpose": "Business expansion, equipment and working capital."
            }
        }

        # EXTRACT LOAN AMOUNT AND TENURE

        def get_loan_details(text):

            amount_match = re.search(
                r"(?:₹|rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
                text,
                re.I
            )

            tenure_match = re.search(
                r"(\d+)\s*(months?|years?)",
                text,
                re.I
            )

            amount = None
            months = None

            if amount_match:
                amount = float(
                    amount_match.group(1).replace(",", "")
                )

            if tenure_match:
                tenure_value = int(tenure_match.group(1))
                tenure_unit = tenure_match.group(2).lower()

                months = (
                    tenure_value * 12
                    if tenure_unit.startswith("year")
                    else tenure_value
                )

            return amount, months

        # CALCULATE EMI

        def calculate_offer_emi(principal, annual_rate, months):

            monthly_rate = annual_rate / 1200

            if monthly_rate == 0:
                return principal / months

            factor = (1 + monthly_rate) ** months

            return (
                principal * monthly_rate * factor
                / (factor - 1)
            )

        # COMPARE BANK OFFERS

        def build_loan_comparison(category, amount, months):

            offers = loan_bank_offers.get(category, [])

            if not offers:
                session.pop("loan_offer_category", None)

                return chatbot_json(
                    True,
                    f"No lender information is currently available "
                    f"for {loan_categories[category]['name']}."
                )

            eligible_offers = []

            for offer in offers:

                min_rate = float(offer["min_rate"])
                max_rate = float(offer["max_rate"])

                eligible_offers.append(
                    (offer, min_rate, max_rate)
                )

                eligible_offers.append(
                    (offer, min_rate, max_rate)
                )

            session.pop("loan_offer_category", None)

            if not eligible_offers:
                return chatbot_json(
                    True,
                    "No available lender entries match your "
                    "requested amount and repayment period. "
                    "Please try a different amount or tenure."
                )

            eligible_offers.sort(
                key=lambda item: item[1]
            )

            result_lines = [
                f"Loan Comparison: {loan_categories[category]['name']}",
                f"Required Amount: ₹{amount:,.2f}",
                f"Repayment Period: {months} months",
                "",
                "Available lender options:"
            ]

            for index, (offer, min_rate, max_rate) in enumerate(
                eligible_offers,
                start=1
            ):

                emi_low = calculate_offer_emi(
                    amount, min_rate, months
                )

                emi_high = calculate_offer_emi(
                    amount, max_rate, months
                )

                total_low = emi_low * months
                total_high = emi_high * months

                if min_rate == max_rate:

                    rate_text = f"{min_rate:.2f}%"
                    emi_text = f"₹{emi_low:,.2f}"
                    total_text = f"₹{total_low:,.2f}"

                else:

                    rate_text = (
                        f"{min_rate:.2f}% - {max_rate:.2f}%"
                    )

                    emi_text = (
                        f"₹{emi_low:,.2f} - ₹{emi_high:,.2f}"
                    )

                    total_text = (
                        f"₹{total_low:,.2f} - ₹{total_high:,.2f}"
                    )

                max_amount_text = (
                    f"₹{offer['max_amount']:,.2f}"
                    if offer.get("max_amount") is not None
                    else "Not specified"
                )

                max_tenure_text = (
                    f"{offer['max_tenure']} months"
                    if offer.get("max_tenure") is not None
                    else "Not specified"
                )

                result_lines.extend([
                    "",
                    f"{index}. {offer['bank']}",
                    f"Loan Type: {offer['type']}",
                    f"Interest Rate: {rate_text}",
                    f"Estimated Monthly EMI: {emi_text}",
                    f"Estimated Total Repayment: {total_text}",
                    f"Source: {offer.get('source', 'Check lender website')}"
                ])

            result_lines.extend([
                "",
                "Recommendation: "
                f"{eligible_offers[0][0]['bank']} has the lowest "
                "listed starting interest rate among these options."
            ])
            return chatbot_json(
                True,
                "\n".join(result_lines)
            )

        # PROCESS CUSTOMER'S AMOUNT AND TENURE FOLLOW-UP

        pending_loan = session.get("loan_offer_category")

        if pending_loan:

            amount, months = get_loan_details(normalized)

            if amount is not None or months is not None:

                if (
                    amount is None
                    or months is None
                    or amount <= 0
                    or months <= 0
                ):
                    return chatbot_json(
                        True,
                        "Please provide both the loan amount "
                        "and repayment period. Example: "
                        "500000 for 60 months."
                    )

                return build_loan_comparison(
                    pending_loan,
                    amount,
                    months
                )

        # IDENTIFY LOAN REQUESTS

        loan_offer_query = any(term in normalized for term in (
            "loan offer",
            "loan offers",
            "loan option",
            "loan options",
            "available loans",
            "types of loans",
            "best loan",
            "recommend a loan",
            "suggest a loan",
            "which loan",
            "loan for",
            "personal loan",
            "home loan",
            "housing loan",
            "education loan",
            "student loan",
            "vehicle loan",
            "car loan",
            "bike loan",
            "gold loan",
            "business loan",
            "college",
            "university",
            "tuition",
            "medical expenses",
            "emergency loan",
            "working capital"
        ))

        if loan_offer_query:

            requested_category = None

            category_keywords = {
                "personal": ("personal",),
                "home": ("home", "house", "housing", "property", "flat"),
                "education": ("education", "student", "study", "college", "university", "tuition"),
                "vehicle": ("vehicle", "car", "bike", "automobile"),
                "gold": ("gold", "jewellery"),
                "business": ("business", "startup", "working capital", "shop")
            }

            # IDENTIFY LOAN CATEGORY

            for category, keywords in category_keywords.items():

                if any(word in normalized for word in keywords):
                    requested_category = category
                    break

            # RECOMMEND CATEGORY BASED ON PURPOSE

            if not requested_category:

                purpose_recommendations = (
                    (("house", "home", "property", "flat"), "home"),
                    (("college", "university", "tuition", "studies", "education"), "education"),
                    (("car", "bike", "vehicle"), "vehicle"),
                    (("gold", "jewellery"), "gold"),
                    (("business", "startup", "shop", "working capital"), "business"),
                    (("medical", "travel", "emergency", "personal"), "personal")
                )

                for keywords, category in purpose_recommendations:

                    if any(word in normalized for word in keywords):
                        requested_category = category
                        break

            # CUSTOMER SELECTED A LOAN CATEGORY

            if requested_category:

                selected = loan_categories[requested_category]

                amount, months = get_loan_details(normalized)

                if amount is not None and months is not None:

                    if amount <= 0 or months <= 0:
                        return chatbot_json(
                            True,
                            "Please provide a valid loan amount "
                            "and repayment period."
                        )

                    return build_loan_comparison(
                        requested_category,
                        amount,
                        months
                    )

                session["loan_offer_category"] = requested_category

                return chatbot_json(
                    True,
                    f"{selected['name']}\n"
                    f"Suitable for: {selected['purpose']}\n\n"
                    "Please enter your required loan amount "
                    "and repayment period.\n\n"
                    "Example: 500000 for 60 months."
                )

            # DISPLAY ALL LOAN CATEGORIES

            offer_lines = [
                f"{item['name']}: {item['purpose']}"
                for item in loan_categories.values()
            ]

            return chatbot_json(
                True,
                "Available loan categories:\n\n"
                + "\n".join(offer_lines)
                + "\n\nTell me your purpose or select a loan category. "
                "Then provide your required amount and repayment period."
            )
        
        # ACCOUNT AND BALANCE QUERIES
        account_query = any(term in normalized for term in (
            "account",
            "balance",
            "available funds",
            "how much money",
            "how much have i got",
            "my savings",
            "my current"
        ))

        if account_query:
            accounts = ctx["accounts"]

            if not accounts:
                return chatbot_json(
                    True,
                    "You don't have any accounts linked to your profile."
                )

            # Detect account type.
            wanted_type = None

            for account_type in (
                "savings",
                "current",
                "salary",
                "fixed deposit",
                "fd",
                "recurring deposit"
            ):
                if account_type in normalized:
                    wanted_type = (
                        "fixed deposit"
                        if account_type == "fd"
                        else account_type
                    )
                    break

            # Detect requested account's last four digits.
            last4_match = re.search(
                r"(?:ending(?:\s+with)?|last\s+four|last\s+4)"
                r"\s*(?:in\s+)?(\d{4})",
                normalized
            )

            selected_accounts = accounts

            # Filter by account type.
            if wanted_type:
                selected_accounts = [
                    account for account in selected_accounts
                    if wanted_type in str(
                        account["account_type"]
                    ).lower()
                    or (
                        wanted_type == "fixed deposit"
                        and "fd" in str(
                            account["account_type"]
                        ).lower()
                    )
                ]

            # Filter by exact account number suffix.
            if last4_match:
                requested_last4 = last4_match.group(1)

                selected_accounts = [
                    account for account in selected_accounts
                    if account["last_four"] == requested_last4
                ]

            if not selected_accounts:
                return chatbot_json(
                    True,
                    "I couldn't find an account matching those details. "
                    "Please check the account type and last four digits."
                )

            lines = [
                f"{a['account_type']} (ending {a['last_four']}): "
                f"₹{a['balance']:,.2f} — "
                f"{a['status'] or 'Active'}"
                for a in selected_accounts
            ]

            total = sum(
                a["balance"]
                for a in selected_accounts
                if str(a["status"] or "Active").lower() == "active"
            )

            heading = (
                "Your requested account:"
                if last4_match
                else (
                    f"Your {wanted_type.title()} account(s):"
                    if wanted_type
                    else "Your accounts:"
                )
            )

            return chatbot_json(
                True,
                heading + "\n"
                + "\n".join(lines)
                + f"\n\nTotal active balance shown: ₹{total:,.2f}"
            )


        # COMPLAINT TRACKING
        if any(term in normalized for term in (
            "complaint status",
            "my complaints",
            "complaint details",
            "track complaint",
            "complaints",
            "show complaint"
        )):
            complaints = ctx["complaints"]

            if not complaints:
                return chatbot_json(
                    True,
                    "You don't have any complaints registered."
                )

            complaint_lines = [
                f"#{x['id']} {x['subject']} — "
                f"{x['status']} ({x['created_at']})"
                for x in complaints
            ]

            return chatbot_json(
                True,
                "Your complaints:\n" + "\n".join(complaint_lines)
            )

        if "complaint" in normalized:
            return chatbot_json(
                True,
                "To register a complaint, type:\n"
                "Register complaint: UPI payment issue - "
                "₹500 was debited but payment failed.\n"
                "I'll show you the details and ask for confirmation "
                "before submitting."
            )

        # BANKING FAQS
        banking_faqs = [
            (
                (
                    "how to add account",
                    "add a new account",
                    "open another account"
                ),
                "To add an account in FinAssist, open the Accounts "
                "section and choose Add Account. The current website "
                "form supports Savings and Current accounts."
            ),
            (
                (
                    "how to add card",
                    "add a new card",
                    "request a new card"
                ),
                "To add a card in this demo, open the Cards section "
                "and choose Add Card. You will need to select an "
                "active linked account and enter the requested "
                "card details."
            ),
            (
                (
                    "how to apply for loan",
                    "how do i apply for loan",
                    "apply for a loan"
                ),
                "Open the Loans section, choose the loan type, "
                "enter the requested amount and tenure, and submit "
                "the application. It will be recorded as Pending "
                "until reviewed."
            )
        ]

        for phrases, answer in banking_faqs:
            if any(phrase in normalized for phrase in phrases):
                return chatbot_json(True, answer)

        # DEFAULT RESPONSE
        return chatbot_json(
            True,
            "I'm FinAssist, your banking assistant. I can help with "
            "accounts, balances, cards, transactions, loan information, "
            "EMI calculations and complaints. Type 'help' to see "
            "what I can do."
        )

    except Exception:
        app.logger.exception("FinAssist chatbot error")

        return jsonify({
            "success": False,
            "message": "FinAssist encountered an error. Please try again."
        }), 500


# ============================================================
# 16. START APPLICATION
# ============================================================

if __name__ == "__main__":
    init_db()

    print("=" * 48)
    print("FINASSIST BANKING SYSTEM")
    print("=" * 48)
    print("Employee login:")
    print("Employee ID: NOB12")
    print("Password: nobita@123")
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG", "1") == "1",
        use_reloader=False
    )
    if __name__ == "__main__":
        init_db()

    print("=" * 48)
    print("FINASSIST BANKING SYSTEM")
    print("=" * 48)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG", "1") == "1",
        use_reloader=False
    )