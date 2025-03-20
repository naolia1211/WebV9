from fastapi import APIRouter, Depends, HTTPException, status, Body, File, UploadFile
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional, Dict, Any
import json
import os
import secrets
import hashlib
from datetime import datetime
from sqlite3 import Connection
from Models.wallet import Wallet, WalletCreate, WalletResponse
from database import get_db
from repositories.wallet_repository import WalletRepository
from Models.user import UserInDB
from API.Routes.auth import get_current_user
import xml.etree.ElementTree as ET
import string
import logging
import time

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Tạo private key ngẫu nhiên
def generate_private_key(length=64):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Tạo địa chỉ ví ngẫu nhiên
def generate_wallet_address(length=42):
    alphabet = string.ascii_letters + string.digits
    return '0x' + ''.join(secrets.choice(alphabet) for _ in range(length-2))

# Tạo ví mới
@router.post("/", response_model=Dict[str, Any])
async def create_wallet(
    wallet_data: Dict[str, Any] = Body(...),
    db: Connection = Depends(get_db)
):
    try:
        logger.info(f"Creating wallet with data: {wallet_data}")
        
        # Validate required fields
        if "user_id" not in wallet_data:
            return {
                "status": "error",
                "message": "user_id is required"
            }
            
        wallet_repo = WalletRepository(db)
        
        # Generate wallet address and private key
        address = generate_wallet_address()
        private_key = generate_private_key()
        
        new_wallet = {
            "user_id": wallet_data["user_id"],
            "label": wallet_data.get("label", "My Wallet"),
            "address": address,
            "private_key": private_key,
            "balance": 0
        }
        
        wallet_id = wallet_repo.create_wallet(new_wallet)
        if not wallet_id:
            return {
                "status": "error",
                "message": "Failed to create wallet"
            }
            
        wallet = wallet_repo.get_wallet_by_id(wallet_id)
        
        return {
            "status": "success",
            "message": "Wallet created successfully",
            "wallet": wallet
        }
    except Exception as e:
        logger.error(f"Error creating wallet: {str(e)}")
        return {
            "status": "error",
            "message": "Failed to create wallet"
        }

# Lấy danh sách ví của user
@router.get("/user/{user_id}", response_model=Dict[str, Any])
async def get_user_wallets(
    user_id: int,
    db: Connection = Depends(get_db)
):
    try:
        logger.info(f"Getting wallets for user_id: {user_id}")
        
        wallet_repo = WalletRepository(db)
        wallets = wallet_repo.get_wallets_by_user_id(user_id)
        
        logger.info(f"Found {len(wallets)} wallets for user {user_id}")
        
        return {
            "status": "success",
            "wallets": wallets
        }
        
    except Exception as e:
        logger.error(f"Error getting user wallets: {str(e)}")
        return {
            "status": "error",
            "message": "Failed to get wallets",
            "wallets": []
        }

# Lấy thông tin ví theo ID
@router.get("/{wallet_id}", response_model=Dict[str, Any])
async def get_wallet(
    wallet_id: int,
    db: Connection = Depends(get_db)
):
    try:
        wallet_repo = WalletRepository(db)
        wallet = wallet_repo.get_wallet_by_id(wallet_id)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        return {
            "status": "success",
            "wallet": wallet
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting wallet: {str(e)}")

# Xóa ví
@router.delete("/{wallet_id}", response_model=Dict[str, Any])
async def delete_wallet(
    wallet_id: int,
    db: Connection = Depends(get_db)
):
    try:
        wallet_repo = WalletRepository(db)
        
        # Kiểm tra ví tồn tại
        wallet = wallet_repo.get_wallet_by_id(wallet_id)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Xóa ví
        success = wallet_repo.delete_wallet(wallet_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete wallet")
        
        return {
            "status": "success",
            "message": "Wallet deleted successfully"
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting wallet: {str(e)}")

# Lấy thông tin ví theo địa chỉ
@router.get("/address/{address}", response_model=dict)
async def get_wallet_by_address(
    address: str,
    db: Connection = Depends(get_db)
):
    try:
        wallet_repo = WalletRepository(db)
        wallet = wallet_repo.get_wallet_by_address(address)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        return {
            "status": "success",
            "wallet": wallet
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Reveal private key
@router.post("/reveal", response_model=dict)
async def reveal_wallet(
    wallet_data: Dict[str, Any] = Body(...),
    db: Connection = Depends(get_db)
):
    try:
        wallet_address = wallet_data.get("wallet_address")
        if not wallet_address:
            raise HTTPException(status_code=400, detail="wallet_address is required")
        
        wallet_repo = WalletRepository(db)
        wallet = wallet_repo.get_wallet_by_address(wallet_address)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Trả về private key
        return {
            "status": "success",
            "address": wallet["address"],
            "private_key": wallet["private_key"]
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Chuyển tiền giữa các ví
@router.post("/transfer", response_model=dict)
async def transfer_money(
    transfer_data: Dict[str, Any] = Body(...),
    db: Connection = Depends(get_db)
):
    try:
        from_wallet = transfer_data.get("from_wallet")
        to_wallet = transfer_data.get("to_wallet")
        amount = transfer_data.get("amount")
        
        if not from_wallet or not to_wallet or amount is None:
            raise HTTPException(status_code=400, detail="from_wallet, to_wallet, and amount are required")
        
        wallet_repo = WalletRepository(db)
        
        # Kiểm tra ví nguồn
        source_wallet = wallet_repo.get_wallet_by_address(from_wallet)
        if not source_wallet:
            return {"status": "error", "message": "Source wallet not found"}
        
        # Kiểm tra ví đích
        dest_wallet = wallet_repo.get_wallet_by_address(to_wallet)
        if not dest_wallet:
            return {"status": "error", "message": "Destination wallet not found"}
        
        # Kiểm tra số dư
        if float(source_wallet["balance"]) < float(amount):
            return {"status": "error", "message": "Insufficient balance"}
        
        # Thực hiện chuyển tiền
        success = wallet_repo.transfer(from_wallet, to_wallet, float(amount))
        if not success:
            return {"status": "error", "message": "Transfer failed"}
        
        # Tạo giao dịch
        transaction = {
            "from_wallet": from_wallet,
            "to_wallet": to_wallet,
            "amount": amount,
            "timestamp": datetime.now().isoformat(),
            "type": "transfer",
            "status": "success"
        }
        
        # Lưu giao dịch vào database
        wallet_repo.create_transaction(transaction)
        
        return {"status": "success", "message": "Transfer completed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Nạp tiền vào ví
@router.post("/deposit", response_model=dict)
async def deposit_money(
    deposit_data: Dict[str, Any] = Body(...),
    db: Connection = Depends(get_db)
):
    try:
        wallet_address = deposit_data.get("wallet_address")
        amount = deposit_data.get("amount")
        
        if not wallet_address or amount is None:
            raise HTTPException(status_code=400, detail="wallet_address and amount are required")
        
        wallet_repo = WalletRepository(db)
        
        # Kiểm tra ví
        wallet = wallet_repo.get_wallet_by_address(wallet_address)
        if not wallet:
            return {"status": "error", "message": "Wallet not found"}
        
        # Thực hiện nạp tiền
        success = wallet_repo.deposit(wallet_address, float(amount))
        if not success:
            return {"status": "error", "message": "Deposit failed"}
        
        # Tạo giao dịch
        transaction = {
            "from_wallet": "external",
            "to_wallet": wallet_address,
            "amount": amount,
            "timestamp": datetime.now().isoformat(),
            "type": "deposit",
            "status": "success"
        }
        
        # Lưu giao dịch vào database
        wallet_repo.create_transaction(transaction)
        
        return {"status": "success", "message": "Deposit completed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Xuất dữ liệu ví
@router.get("/export", response_model=dict)
async def export_wallet_data(
    wallet_address: str, 
    format: str = "json", 
    db: Connection = Depends(get_db)
):
    try:
        # Khởi tạo WalletRepository với tham số db
        wallet_repo = WalletRepository(db)
        
        # Kiểm tra ví
        wallet = wallet_repo.get_wallet_by_address(wallet_address)
        if not wallet:
            return {"status": "error", "message": "Wallet not found"}
        
        # Lấy giao dịch của ví
        transactions = wallet_repo.get_transactions_by_wallet(wallet_address)
        
        # Tạo dữ liệu xuất
        export_data = {
            "wallet": wallet,
            "transactions": transactions
        }
        
        # Tạo tên file
        filename = f"wallet_{wallet_address}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{format}"
        
        # Lưu file
        with open(filename, "w") as f:
            json.dump(export_data, f, indent=4)
        
        return {"status": "success", "file": filename}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Nhập dữ liệu ví
@router.post("/import", response_model=dict)
async def import_wallet_data(
    file: str = Body(...), 
    db: Connection = Depends(get_db)
):
    try:
        # Khởi tạo WalletRepository với tham số db
        wallet_repo = WalletRepository(db)
        
        # Đọc file
        with open(file, "r") as f:
            data = json.load(f)
        
        # Kiểm tra dữ liệu
        if "wallet" not in data:
            return {"status": "error", "message": "Invalid wallet data"}
        
        # Nhập ví
        wallet = data["wallet"]
        wallet_repo.create_wallet(Wallet(**wallet))
        
        # Nhập giao dịch
        if "transactions" in data:
            for transaction in data["transactions"]:
                wallet_repo.create_transaction(transaction)
        
        return {"status": "success", "message": "Wallet imported successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


