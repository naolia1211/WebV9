from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class WalletBase(BaseModel):
    """Base model cho wallet"""
    user_id: int
    address: str = Field(..., description="Địa chỉ ví trên blockchain")
    label: str = Field(default="My Wallet", description="Tên/nhãn của ví")

class WalletCreate(BaseModel):
    """Model cho việc tạo wallet mới"""
    user_id: int
    label: Optional[str] = "My Wallet"

class Wallet(WalletBase):
    """Model đầy đủ cho wallet"""
    id: int
    balance: float = Field(default=0.0, description="Số dư của ví trên blockchain", ge=0)
    created_at: Optional[str] = None
    private_key: Optional[str] = None  # Chỉ trả về khi cần thiết

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "label": "My First Wallet",
                "address": "0x1234567890abcdef",
                "balance": 0.0,
                "created_at": "2024-03-20 10:30:00"
            }
        }

class WalletResponse(BaseModel):
    """Model cho response trả về client"""
    status: str = "success"
    wallets: list[Wallet]

    class Config:
        from_attributes = True

class BlockchainTransfer(BaseModel):
    """Model cho việc chuyển tiền trên blockchain"""
    from_wallet: str
    to_wallet: str
    amount: float
    confirm: bool = True