from typing import Optional, Dict
from sqlite3 import Connection
from Models.user import UserCreate, UserInDB, UserResponse
from passlib.context import CryptContext
from datetime import datetime

# Khởi tạo CryptContext để sử dụng bcrypt cho việc mã hóa mật khẩu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRepository:
    @staticmethod
    def create_user(db: Connection, name: str, email: str, password: str, profile_image: str) -> Optional[Dict]:
        """Create a new user"""
        cursor = db.cursor()
        try:
            # Check if email exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return None
                
            # Insert user
            cursor.execute(
                "INSERT INTO users (name, email, password, profileImage) VALUES (?, ?, ?, ?)",
                (name, email, password, profile_image)
            )
            db.commit()
            
            # Get created user
            cursor.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,))
            user = cursor.fetchone()
            
            return dict(user) if user else None
        except Exception as e:
            print(f"Error creating user: {e}")
            db.rollback()
            return None
    
    @staticmethod
    async def get_user_by_email(conn: Connection, email: str) -> Optional[UserInDB]:
        """Lấy thông tin người dùng từ email"""
        cursor = conn.cursor()
        query = "SELECT id, name, email, password, profileImage, created_at FROM users WHERE email = ?"
        cursor.execute(query, (email,))
        user_data = cursor.fetchone()

        if user_data:
            return UserInDB(
                id=user_data[0],
                name=user_data[1],
                email=user_data[2],
                password=user_data[3],
                profileImage=user_data[4],
                created_at=user_data[5]
            )
        return None
    
    @staticmethod
    async def checkLoginInfo(conn: Connection, email: str, password: str) -> Optional[UserInDB]:
        """Kiểm tra thông tin đăng nhập"""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, password, profileImage, created_at FROM users WHERE email = ? AND password = ?",
            (email, password)
        )
        user_data = cursor.fetchone()
        if user_data:
            return UserInDB(
                id=user_data[0],
                name=user_data[1],
                email=user_data[2],
                password=user_data[3],
                profileImage=user_data[4],
                created_at=user_data[5]
            )
        return None
        

    @staticmethod
    def get_user_by_id(conn: Connection, user_id: int) -> Optional[UserResponse]:
        """Lấy thông tin người dùng từ ID"""
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
            cursor.execute(
                "UPDATE users SET name = ?, email = ?, password = ?, profileImage = ? WHERE id = ?",
                (user.name, user.email, user.password, user.profile_image, user_id)
            )
            conn.commit()
            
            return UserRepository.get_user_by_id(conn, user_id)
        except Exception as e:
            print(f"Error updating user: {e}")
            conn.rollback()  # Quay lại nếu có lỗi
            return None

    @staticmethod
    def delete_user(conn: Connection, user_id: int) -> bool:
        """Xóa người dùng"""
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            conn.rollback()  # Quay lại nếu có lỗi
            return False