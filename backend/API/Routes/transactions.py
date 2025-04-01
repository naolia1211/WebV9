from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer
from typing import List, Dict, Any
from database import get_db
from repositories.wallet_repository import WalletRepository
from repositories.transaction_repository import TransactionRepository
from Models.transaction import BlockchainTransactionCreate
from datetime import datetime
import logging
import sqlite3
from sqlite3 import Connection
from Models.user import UserInDB
from API.Routes.auth import get_current_user

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Thêm endpoint mới để tạo giao dịch blockchain
@router.post("/blockchain", response_model=Dict[str, Any])
async def create_blockchain_transaction(
    transaction: BlockchainTransactionCreate,
    db: Connection = Depends(get_db)
):
    """Tạo giao dịch mới trên blockchain"""
    try:
        # Khởi tạo TransactionRepository
        tx_repo = TransactionRepository(db)
        wallet_repo = WalletRepository(db)
        
        # Kiểm tra ví nguồn tồn tại
        source_wallet = wallet_repo.get_wallet_by_address(transaction.from_wallet)
        if not source_wallet:
            raise HTTPException(status_code=404, detail="Source wallet not found")
        
        # Kiểm tra số dư
        balance = wallet_repo.blockchain.get_balance(transaction.from_wallet)
        if balance < transaction.amount:
            raise HTTPException(status_code=400, detail=f"Insufficient balance: {balance} < {transaction.amount}")
        
        # Tạo giao dịch blockchain
        result = tx_repo.create_blockchain_transaction(
            transaction.from_wallet,
            transaction.to_wallet,
            transaction.amount,
            transaction.private_key
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return {
            "status": "success",
            "message": "Transaction sent successfully to blockchain",
            "transaction": result["transaction"]
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating blockchain transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating blockchain transaction: {str(e)}")

# Cập nhật endpoint lấy giao dịch theo địa chỉ ví
@router.get("/{wallet_address}", response_model=List[Dict[str, Any]])
async def get_transactions(
    wallet_address: str,
    db: Connection = Depends(get_db)
):
    try:
        # Khởi tạo repositories
        wallet_repo = WalletRepository(db)
        tx_repo = TransactionRepository(db)
        
        # Kiểm tra ví tồn tại
        wallet = wallet_repo.get_wallet_by_address(wallet_address)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Lấy giao dịch từ blockchain và database
        transactions = tx_repo.get_transactions_by_address(wallet_address)
        
        return transactions
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transactions: {str(e)}")
    
@router.get("/wallet/{wallet_address}")
async def get_transactions_by_wallet(
    wallet_address: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Lấy tất cả giao dịch liên quan đến một địa chỉ ví"""
    try:
        logger.info(f"Searching transactions for wallet: {wallet_address}")
        
        conn = sqlite3.connect("wallet.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Kiểm tra xem bảng transactions có tồn tại không
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
            if not cursor.fetchone():
                logger.warning("Transactions table does not exist")
                return []
                
            # Lấy thông tin về cấu trúc bảng transactions
            cursor.execute("PRAGMA table_info(transactions)")
            columns = [col[1] for col in cursor.fetchall()]
            logger.info(f"Transaction table columns: {columns}")
            
            # Xây dựng truy vấn dựa trên các cột có sẵn
            select_columns = []
            required_columns = ["from_wallet", "to_wallet", "amount"]
            optional_columns = ["id", "type", "hash", "timestamp", "created_at", "status", "block_number"]
            
            # Đảm bảo các cột bắt buộc có trong bảng
            for col in required_columns:
                if col not in columns:
                    logger.error(f"Required column {col} not found in transactions table")
                    return []
                select_columns.append(col)
            
            # Thêm các cột tùy chọn nếu có
            for col in optional_columns:
                if col in columns:
                    select_columns.append(col)
            
            # Xây dựng và thực hiện truy vấn
            select_clause = ", ".join(select_columns)
            query = f"""
                SELECT {select_clause}
                FROM transactions 
                WHERE from_wallet = ? OR to_wallet = ?
                ORDER BY {"created_at" if "created_at" in columns else "timestamp"} DESC
            """
            logger.info(f"Executing query: {query}")
            cursor.execute(query, (wallet_address, wallet_address))
            
            transactions = cursor.fetchall()
            
            # Chuyển đổi kết quả thành list
            result = []
            for tx in transactions:
                tx_dict = dict(tx)
                # Thêm các trường mặc định nếu không tồn tại
                if "type" not in tx_dict:
                    tx_dict["type"] = "transfer"
                if "created_at" not in tx_dict and "timestamp" in tx_dict:
                    tx_dict["created_at"] = tx_dict["timestamp"]
                
                result.append(tx_dict)
            
            logger.info(f"Found {len(result)} transactions for wallet {wallet_address}")
            return result
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error getting transactions for wallet {wallet_address}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))