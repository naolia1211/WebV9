import sqlite3
import threading
import logging
import os
from datetime import datetime, timedelta
from jose import jwt
import bcrypt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

local_data = threading.local()

def get_db() -> sqlite3.Connection:
    if not hasattr(local_data, 'conn'):
        local_data.conn = sqlite3.connect('wallet.db', check_same_thread=False)
        local_data.conn.row_factory = sqlite3.Row
    return local_data.conn

def close_db():
    if hasattr(local_data, 'conn'):
        local_data.conn.close()
        del local_data.conn

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

async def async_get_db():
    conn = sqlite3.connect('wallet.db', check_same_thread=False)
    conn.row_factory = dict_factory
    return conn

def create_tables():
    try:
        conn = sqlite3.connect('wallet.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                private_password TEXT,
                profileImage TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                address TEXT NOT NULL,
                private_key TEXT NOT NULL,
                balance REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        
        conn.commit()
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

def register_user(name: str, email: str, password: str, private_password: str = None, profile_image_path: str = None):
    try:
        logger.info(f"Attempting to register user: {email}")
        
        conn = sqlite3.connect('wallet.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        hashed_private_password = bcrypt.hashpw(private_password.encode('utf-8'), bcrypt.gensalt()) if private_password else None
        
        try:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return False, "Email already registered"
            
            cursor.execute("""
                INSERT INTO users (name, email, password, private_password, profileImage, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (name, email, hashed_password, hashed_private_password, profile_image_path))
            
            conn.commit()
            
            cursor.execute("""
                SELECT id, name, email, profileImage, created_at
                FROM users
                WHERE email = ?
            """, (email,))
            user = cursor.fetchone()
            
            if user:
                user_data = dict(user)
                return True, user_data
            return False, "Failed to retrieve user data"
                
        except sqlite3.Error as e:
            logger.error(f"Database error during registration: {str(e)}")
            return False, str(e)
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        return False, str(e)

async def login_user(email: str, password: str):
    try:
        conn = sqlite3.connect('wallet.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = create_access_token(
                    data={"sub": user["email"]}, expires_delta=access_token_expires
                )
                
                profile_image = user["profileImage"] if "profileImage" in user.keys() else None
                
                return {
                    "status": "success",
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": {
                        "id": user["id"],
                        "name": user["name"],
                        "email": user["email"],
                        "profileImage": profile_image
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": "Invalid credentials"
                }

        except sqlite3.Error as e:
            logger.error(f"Database error during login: {str(e)}")
            return {
                "status": "error",
                "message": f"SQL Error: {str(e)}"  
            }
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        return {
            "status": "error",
            "message": f"Unexpected Error: {str(e)}"
        }

__all__ = ['get_db', 'async_get_db', 'login_user', 'register_user', 'create_tables']