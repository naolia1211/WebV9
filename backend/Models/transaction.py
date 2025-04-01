from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TransactionBase(BaseModel):
    """Base model cho transaction"""
    from_wallet: str = Field(..., description="Địa chỉ ví gửi")
    to_wallet: str = Field(..., description="Địa chỉ ví nhận")
    amount: float = Field(..., description="Số tiền giao dịch", gt=0)
    type: str = Field(..., description="Loại giao dịch")
    status: str = Field(..., description="Trạng thái giao dịch")

class TransactionCreate(TransactionBase):
    """Model cho việc tạo transaction mới"""
    pass

class Transaction(TransactionBase):
    """Model đầy đủ cho transaction"""
    id: int
    # Thêm các trường mới cho blockchain
    hash: Optional[str] = None
    block_number: Optional[int] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "from_wallet": "0x1234567890abcdef",
                "to_wallet": "0xabcdef1234567890",
                "amount": 1.5,
                "type": "transfer",
                "status": "completed",
                "timestamp": "2024-03-20 10:30:00",
                "hash": "0x9a55f0a7ec80b90993352d3352d1c95e11bb785d9952e092059f068adb48fc8f",
                "block_number": 12345678
            }
        }

class TransactionResponse(BaseModel):
    """Model cho response trả về client"""
    status: str = "success"
    transactions: list[Transaction]

    class Config:
        from_attributes = True

# Mới: Model cho blockchain transaction
class BlockchainTransactionCreate(BaseModel):
    """Model cho việc tạo blockchain transaction"""
    from_wallet: str = Field(..., description="Địa chỉ ví gửi")
    to_wallet: str = Field(..., description="Địa chỉ ví nhận")
    amount: float = Field(..., description="Số tiền giao dịch", gt=0)
    private_key: str = Field(..., description="Private key của ví gửi")