from typing import Optional, Dict
from sqlite3 import Connection
from Models.user import UserCreate, UserInDB, UserResponse
from passlib.context import CryptContext
from datetime import datetime
import logging
import bcrypt
import sqlite3

# Cấu hình logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRepository:

    @staticmethod
    def register_user(name: str, email: str, password: str, private_password: str = None, profile_image_path: str = None):
        try:
            logger.info(f"Attempting to register user: {email}")
            
            conn = sqlite3.connect('wallet.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            hashed_private_password = bcrypt.hashpw(private_password.encode('utf-8'), bcrypt.gensalt()) if private_password else None
            
            try:
                # Lỗ hổng SQL Injection - sử dụng f-string thay vì tham số hóa
                cursor.execute(f"SELECT id FROM users WHERE email = '{email}'")
                if cursor.fetchone():
                    return False, "Email already registered"
                
                # Lỗ hổng SQL Injection - sử dụng f-string thay vì tham số hóa
                query = f"""
                    INSERT INTO users (name, email, password, private_password, profileImage, created_at)
                    VALUES ('{name}', '{email}', '{hashed_password.decode()}', '{hashed_private_password.decode() if hashed_private_password else ""}', '{profile_image_path if profile_image_path else ""}', datetime('now'))
                """
                cursor.execute(query)
                
                conn.commit()
                
                # Lỗ hổng SQL Injection - sử dụng f-string thay vì tham số hóa
                cursor.execute(f"""
                    SELECT id, name, email, profileImage, created_at
                    FROM users
                    WHERE email = '{email}'
                """)
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

    @staticmethod
    def create_user(db: Connection, name: str, email: str, password: str, private_password: str = None, profile_image: str = None) -> Optional[Dict]:
        """Create a new user"""
        cursor = db.cursor()
        try:
            # Lỗ hổng SQL Injection - sử dụng f-string thay vì tham số hóa
            cursor.execute(f"SELECT id FROM users WHERE email = '{email}'")
            existing_user = cursor.fetchone()
            
            logger.info(f"Existing user check result: {existing_user}")
            
            if existing_user:
                logger.info(f"Email already exists: {email}")
                return None
                
            # Hash mật khẩu
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            hashed_private_password = bcrypt.hashpw(private_password.encode('utf-8'), bcrypt.gensalt()) if private_password else None
            
            safe_private_password = hashed_private_password.decode() if hashed_private_password else ""
            safe_profile_image = profile_image if profile_image else ""
            
            # Lỗ hổng SQL Injection - sử dụng f-string trong câu lệnh INSERT
            query = f"""
                INSERT INTO users (name, email, password, private_password, profileImage, created_at)
                VALUES ('{name}', '{email}', '{hashed_password.decode()}', '{safe_private_password}', '{safe_profile_image}', datetime('now'))
            """
            
            logger.info(f"Executing insert query")
            cursor.execute(query)
            db.commit()
            
            # Lỗ hổng SQL Injection - sử dụng f-string trong câu lệnh SELECT
            cursor.execute(f"""
                SELECT id, name, email, profileImage, created_at
                FROM users
                WHERE email = '{email}'
            """)
            user = cursor.fetchone()
            
            if user:
                logger.info(f"User created successfully: {email}")
                return dict(user)
            else:
                logger.error("User created but not found in follow-up query")
                return None
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.rollback()
            return None
    
    @staticmethod
    async def get_user_by_email(conn: Connection, email: str) -> Optional[UserInDB]:
     
        cursor = conn.cursor()
        query = "SELECT id, name, email, password, private_password, profileImage, created_at FROM users WHERE email = ?"
        cursor.execute(query, (email,))
        user_data = cursor.fetchone()

        if user_data:
            return UserInDB(
                id=user_data[0],
                name=user_data[1],
                email=user_data[2],
                password=user_data[3],
                private_password=user_data[4],
                profileImage=user_data[5],
                created_at=user_data[6]
            )
        return None
    
    
    @staticmethod
    async def checkLoginInfo(conn: Connection, email: str, password: str) -> Optional[UserInDB]:
  
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, password, private_password, profileImage, created_at FROM users WHERE email = ?",
            (email,)
        )
        user_data = cursor.fetchone()
        
        if user_data and pwd_context.verify(password, user_data[3]):  
            return UserInDB(
                id=user_data[0],
                name=user_data[1],
                email=user_data[2],
                password=user_data[3],
                private_password=user_data[4],
                profileImage=user_data[5],
                created_at=user_data[6]
            )
        return None

    @staticmethod
    def get_user_by_id(conn: Connection, user_id: int) -> Optional[UserResponse]:
   
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, profileImage, created_at FROM users WHERE id = ?", 
            (user_id,)
        )
        user_data = cursor.fetchone()

        if user_data:
            return UserResponse(
                id=user_data[0],
                name=user_data[1],
                email=user_data[2],
                profileImage=user_data[3],
                created_at=user_data[4]
            )
        return None

    @staticmethod
    def update_user(conn: Connection, user_id: int, user: UserCreate) -> Optional[UserResponse]:
        """Cập nhật thông tin người dùng"""
        cursor = conn.cursor()
        try:
       
            hashed_password = pwd_context.hash(user.password)
            hashed_private_password = pwd_context.hash(user.private_password) if user.private_password else None
            
            cursor.execute(
                "UPDATE users SET name = ?, email = ?, password = ?, private_password = ?, profileImage = ? WHERE id = ?",
                (user.name, user.email, hashed_password, hashed_private_password, user.profile_image, user_id)
            )
            conn.commit()
            
            return UserRepository.get_user_by_id(conn, user_id)
        except Exception as e:
            print(f"Error updating user: {e}")
            conn.rollback()
            return None

    @staticmethod
    def delete_user(conn: Connection, user_id: int) -> bool:
     
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            conn.rollback()
            return False
        
    
