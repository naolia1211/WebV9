from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlite3 import Connection
from Models.user import UserCreate, UserResponse, UserInDB
from database import get_db, register_user, login_user, create_tables
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from repositories.user_repository import UserRepository
import shutil
import sqlite3
import os
from jose import JWTError, jwt
from fastapi import Depends, status
import time
import logging
import json
from pathlib import Path

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Cấu hình JWT
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Định nghĩa OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Tạo token truy cập
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Thêm các model response
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    profile_image: str
    created_at: str

class RegisterResponse(BaseModel):
    message: str
    user: UserResponse

# Hàm để lấy current user từ token
async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        # Tạo connection mới
        conn = sqlite3.connect("wallet.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
                
            return UserInDB(
                id=user["id"],
                name=user["name"],
                email=user["email"],
                password=user["password"],  # Sửa từ password_hash sang password
                profileImage=user["profileImage"] if "profileImage" in user.keys() else None,
                created_at=user["created_at"] if "created_at" in user.keys() else None
            )
        finally:
            cursor.close()
            conn.close()
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Tạo thư mục uploads nếu chưa tồn tại
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Tạo thư mục lưu ảnh nếu chưa tồn tại
PROFILE_IMAGES_DIR = "static/profile_images"
Path(PROFILE_IMAGES_DIR).mkdir(parents=True, exist_ok=True)

@router.post("/register")
async def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    profile_image: UploadFile = File(None)
):
    try:
        logger.info(f"Register endpoint hit! Received data: name={name}, email={email}")
        logger.info(f"Profile image: {profile_image.filename if profile_image else 'None'}")
        
        # Xử lý ảnh đại diện
        profile_image_path = None
        if profile_image and profile_image.filename:
            # Tạo tên file duy nhất
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            file_ext = os.path.splitext(profile_image.filename)[1]
            filename = f"{email}_{timestamp}{file_ext}"
            
            # Lưu đường dẫn tương đối cho DB - ĐƯỜNG DẪN CÓ TIỀN TỐ /static/
            profile_image_path = f"/static/profile_images/{filename}"
            
            # Lưu file ảnh với đường dẫn tuyệt đối
            full_path = os.path.join(PROFILE_IMAGES_DIR, filename)
            
            # Log đường dẫn để debug
            logger.info(f"Saving profile image to relative path: {profile_image_path}")
            logger.info(f"Full path on disk: {full_path}")
            
            # Đọc nội dung file
            file_content = await profile_image.read()
            logger.info(f"Read {len(file_content)} bytes from uploaded file")
            
            # Lưu file
            with open(full_path, "wb") as buffer:
                buffer.write(file_content)
            
            logger.info(f"Profile image saved successfully")
        else:
            logger.info("No profile image provided")
        
        # Gọi hàm register_user
        success, result = register_user(name, email, password, profile_image_path)
        
        if not success:
            logger.error(f"Registration failed: {result}")
            return {
                "status": "error",
                "message": result
            }
            
        logger.info(f"Registration successful for user: {email}")
        return {
            "status": "success",
            "message": "Registration successful",
            "user": result
        }
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login user"""
    try:
        logger.info(f"Login attempt for user: {form_data.username}")

        # Login user
        result = await login_user(form_data.username, form_data.password)

        if result["status"] == "success":
            logger.info(f"Login successful for user: {form_data.username}")
            return result
        else:
            logger.warning(f"Login failed for user: {form_data.username}, reason: {result.get('message', 'Unknown error')}")
            raise HTTPException(status_code=401, detail=result.get("message", "Invalid credentials"))

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/login-form")
async def login_form(
    username: str = Form(...),
    password: str = Form(...)
):
    """Login user with form data"""
    try:
        logger.info(f"Login attempt for user: {username}")
        
        # Login user
        result = await login_user(username, password)
        
        if result["status"] == "success":
            logger.info(f"Login successful for user: {username}")
            return result
        else:
            logger.warning(f"Login failed for user: {username}, reason: {result.get('message', 'Unknown error')}")
            return {
                "status": "error",
                "message": result.get("message", "Invalid credentials")
            }
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return {
            "status": "error",
            "message": "Login failed"
        }

@router.get("/me", response_model=dict)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    """Get current user info"""
    return {
        "status": "success",
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "profileImage": current_user.profileImage
        }
    }

@router.put("/update-profile")
async def update_profile(
    name: str = Form(...),
    email: str = Form(...),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        conn = sqlite3.connect("wallet.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET name = ?, email = ? WHERE id = ?",
                (name, email, current_user.id)
            )
            conn.commit()

            cursor.execute("SELECT * FROM users WHERE id = ?", (current_user.id,))
            user = cursor.fetchone()

            return {
                "status": "success",
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "profileImage": user["profileImage"] if "profileImage" in user.keys() else None
                }
            }
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/change-name")
async def change_name(
    new_name: str = Body(..., embed=True),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        conn = sqlite3.connect("wallet.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET name = ? WHERE id = ?",
                (new_name, current_user.id)
            )
            conn.commit()

            return {
                "status": "success",
                "message": "Name updated successfully",
                "user": {
                    "id": current_user.id,
                    "name": new_name,
                    "email": current_user.email,
                    "profileImage": current_user.profileImage
                }
            }
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Error updating name: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/change-email")
async def change_email(
    new_email: str = Body(..., embed=True),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        conn = sqlite3.connect("wallet.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", 
                         (new_email, current_user.id))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email already exists")

            cursor.execute(
                "UPDATE users SET email = ? WHERE id = ?",
                (new_email, current_user.id)
            )
            conn.commit()

            return {
                "status": "success",
                "message": "Email updated successfully",
                "user": {
                    "id": current_user.id,
                    "name": current_user.name,
                    "email": new_email,
                    "profileImage": current_user.profileImage
                }
            }
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"Error updating email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/change-image")
async def change_image(
    profile_image: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        # Tạo tên file duy nhất
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_ext = os.path.splitext(profile_image.filename)[1]
        filename = f"{current_user.email}_{timestamp}{file_ext}"
        
        # Lưu đường dẫn tương đối cho DB - ĐỔI SANG TIỀN TỐ /static/
        relative_path = f"/static/profile_images/{filename}"
        
        # Đường dẫn đầy đủ để lưu file
        full_path = os.path.join("static", "profile_images", filename)
        
        # Log thông tin
        logger.info(f"Saving profile image to relative path: {relative_path}")
        logger.info(f"Full path on disk: {full_path}")
        
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Lưu file
        with open(full_path, "wb+") as file_object:
            file_object.write(await profile_image.read())

        conn = sqlite3.connect("wallet.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET profileImage = ? WHERE id = ?",
                (relative_path, current_user.id)
            )
            conn.commit()

            return {
                "status": "success",
                "message": "Profile image updated successfully",
                "user": {
                    "id": current_user.id,
                    "name": current_user.name,
                    "email": current_user.email,
                    "profileImage": relative_path
                }
            }
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error updating profile image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))