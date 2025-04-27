from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Base model cho user"""
    name: str
    email: EmailStr

class UserCreate(UserBase):
    """Model cho việc tạo user mới"""
    password: str
    private_password: Optional[str] = None  # Thêm trường private_password (tùy chọn)
    profile_image: Optional[str] = None

class UserInDB(UserBase):
    """Model cho user trong database"""
    id: int
    password: str  # Lưu ý: Đây là mật khẩu đã băm
    private_password: Optional[str] = None  # Thêm trường private_password (đã băm)
    profileImage: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    """Model cho response trả về client"""
    id: int
    name: str
    email: str
    profileImage: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    """Model cho token response"""
    access_token: str
    token_type: str
    user_info: dict

class TokenData(BaseModel):
    """Model cho token data"""
    email: Optional[str] = None