import sqlite3
import threading
import logging
import os
from datetime import datetime, timedelta
from jose import jwt

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cấu hình JWT
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# Thread-local storage for database connections
local_data = threading.local()

def get_db() -> sqlite3.Connection:
    """Get a database connection for the current thread"""
    if not hasattr(local_data, 'conn'):
        local_data.conn = sqlite3.connect('wallet.db', check_same_thread=False)
        local_data.conn.row_factory = sqlite3.Row
    return local_data.conn

def close_db():
    """Close the database connection for the current thread"""
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
    """Tạo connection cho async functions"""
    conn = sqlite3.connect('wallet.db', check_same_thread=False)
    conn.row_factory = dict_factory
    return conn

def create_tables():
    """Create database tables if they don't exist"""
    try:
        conn = sqlite3.connect('wallet.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    profileImage TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create wallets table
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
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        raise

def register_user(name: str, email: str, password: str, profile_image_path: str = None):
    """Register a new user"""
    try:
        logger.info(f"Attempting to register user: {email}")
        logger.info(f"Profile image path: {profile_image_path}")
        
        conn = sqlite3.connect('wallet.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Kiểm tra email đã tồn tại chưa
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                logger.warning(f"Email already exists: {email}")
                return False, "Email already registered"
            
            # Thêm user mới
            cursor.execute("""
                INSERT INTO users (name, email, password, profileImage, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (name, email, password, profile_image_path))
            
            conn.commit()
            logger.info(f"User registered successfully: {email}")
            
            # Lấy thông tin user vừa đăng ký
            cursor.execute("""
                SELECT id, name, email, profileImage, created_at
                FROM users
                WHERE email = ?
            """, (email,))
            
            user = cursor.fetchone()
            
            if user:
                user_data = {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "profileImage": user["profileImage"],
                    "created_at": user["created_at"]
                }
                logger.info(f"User data after registration: {user_data}")
                return True, user_data
            else:
                logger.error(f"Failed to retrieve user data: {email}")
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
    """Login user with intentional error-based SQLi vulnerability"""
    try:
        conn = sqlite3.connect('wallet.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Nối chuỗi trực tiếp để tạo lỗ hổng
            query = f"SELECT * FROM users WHERE email = '{email}' AND password = '{password}'"
            cursor.execute(query)
            user = cursor.fetchone()

            if user:
                # Tạo access token
                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = create_access_token(
                    data={"sub": user["email"]}, expires_delta=access_token_expires
                )

                # Xử lý trường hợp nếu không có profileImage
                profile_image = None
                if "profileImage" in user.keys():
                    profile_image = user["profileImage"]
                
                logger.info(f"User profile image during login: {profile_image}")

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
            # Trả về lỗi chi tiết để hỗ trợ error-based SQLi
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

# Export các functions
__all__ = ['get_db', 'async_get_db', 'login_user', 'register_user', 'create_tables']