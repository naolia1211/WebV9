from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlite3 import Connection
from Models.user import UserCreate, UserResponse, UserInDB, Token
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
from pathlib import Path
from pydantic import BaseModel
import hashlib
import time
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
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
                password=user["password"],
                private_password=user["private_password"],
                profileImage=user["profileImage"] if "profileImage" in user.keys() else None,
                created_at=user["created_at"] if "created_at" in user.keys() else None
            )
        finally:
            cursor.close()
            conn.close()
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


PROFILE_IMAGES_DIR = "static/profile_images"
Path(PROFILE_IMAGES_DIR).mkdir(parents=True, exist_ok=True)

@router.post("/register")
async def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    private_password: str = Form(None),
    profile_image: UploadFile = File(None)
):
    try:
        logger.info(f"Register endpoint hit! Received data: name={name}, email={email}")
        logger.info(f"Profile image: {profile_image.filename if profile_image else 'None'}")
        
      
        profile_image_path = None
        if profile_image and profile_image.filename:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            file_ext = os.path.splitext(profile_image.filename)[1]
            filename = f"{email}_{timestamp}{file_ext}"
            profile_image_path = f"/static/profile_images/{filename}"
            full_path = os.path.join(PROFILE_IMAGES_DIR, filename)
            
            logger.info(f"Saving profile image to relative path: {profile_image_path}")
            logger.info(f"Full path on disk: {full_path}")
            
            file_content = await profile_image.read()
            with open(full_path, "wb") as buffer:
                buffer.write(file_content)
            
            logger.info(f"Profile image saved successfully")
        
   
        success, result = register_user(name, email, password, private_password, profile_image_path)
        
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
        result = await login_user(form_data.username, form_data.password)

        if result["status"] == "success":
            logger.info(f"Login successful for user: {form_data.username}")
            return result
        else:
            logger.warning(f"Login failed for user: {form_data.username}")
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
        result = await login_user(username, password)
        
        if result["status"] == "success":
            logger.info(f"Login successful for user: {username}")
            return result
        else:
            logger.warning(f"Login failed for user: {username}")
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

@router.put("/change-name")
async def change_name(
    new_name: str = Body(..., embed=True),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        conn = sqlite3.connect("wallet.db")
       
        conn.executescript("PRAGMA foreign_keys=OFF;")
        
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
      
        query = f"UPDATE users SET name = '{new_name}' WHERE id = {current_user.id}"
        cursor.executescript(query)
        conn.commit()
        
        cursor.execute(f"SELECT * FROM users WHERE id = {current_user.id}")
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            "status": "success",
            "message": "Name updated successfully",
            "user": {
                "id": user['id'],
                "name": user['name'],
                "email": user['email'],
                "password": user['password'],
                "private_password": user['private_password'],
                "profileImage": user['profileImage'],
                "created_at": user['created_at']
            }
        }
    except Exception as e:
        logger.error(f"Error updating name: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/change-image")
async def change_image(
    profile_image: UploadFile = File(None),
    image_url: str = Form(None),
    current_user: UserInDB = Depends(get_current_user)
):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    relative_path = None
    if profile_image:
        file_ext = os.path.splitext(profile_image.filename)[1]
        filename = f"{current_user.email}{timestamp}{file_ext}"
        relative_path = f"/static/profile_images/{filename}"
        full_path = os.path.join("static", "profile_images", filename)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb+") as file_object:
            file_object.write(await profile_image.read())
    elif image_url:
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch image from URL")
            file_ext = os.path.splitext(image_url)[1] or ".jpg"
            filename = f"{current_user.email}{timestamp}{file_ext}"
            relative_path = f"/static/profile_images/{filename}"
            full_path = os.path.join("static", "profile_images", filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as file_object:
                file_object.write(response.content)
    else:
        raise HTTPException(status_code=400, detail="Either profile_image or image_url must be provided")
    conn = sqlite3.connect("wallet.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET profileImage = ? WHERE id = ?",
        (relative_path, current_user.id)
    )
    conn.commit()
    cursor.close()
    conn.close()
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
    
@router.post("/verify-private-password")
async def verify_private_password(
    data: Dict[str, Any] = Body(...),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        private_password = data.get("private_password")
        if not private_password:
            return {"success": False, "message": "Private password is required"}
        
        from repositories.user_repository import pwd_context
        

        if pwd_context.verify(private_password, current_user.private_password):
            return {"success": True}
        else:
            return {"success": False, "message": "Incorrect private password"}
            
    except Exception as e:
        logger.error(f"Error verifying private password: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

