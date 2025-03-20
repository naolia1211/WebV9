from typing import Optional, List, Dict, Any
from sqlite3 import Connection
from Models.wallet import Wallet
from decimal import Decimal
from datetime import datetime
from web3 import Web3
import decimal
import uuid
import sqlite3
import os
import logging
import time
import threading
from contextlib import contextmanager

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WalletRepository:
    def __init__(self, db: Connection):
        self.db = db
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Đảm bảo bảng wallets tồn tại với cấu trúc đúng"""
        try:
            cursor = self.db.cursor()
            
            # Kiểm tra bảng wallets có tồn tại không
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wallets'")
            if not cursor.fetchone():
                logger.info("Creating wallets table")
                cursor.execute('''
                CREATE TABLE wallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    address TEXT NOT NULL,
                    private_key TEXT NOT NULL,
                    balance REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
                ''')
                self.db.commit()
            
            # Kiểm tra cấu trúc bảng
            cursor.execute("PRAGMA table_info(wallets)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            logger.info(f"Wallet table columns: {column_names}")
            
            # Kiểm tra các cột cần thiết
            required_columns = ['id', 'user_id', 'label', 'address', 'private_key', 'balance', 'created_at']
            missing_columns = [col for col in required_columns if col not in column_names]
            
            if missing_columns:
                logger.warning(f"Missing columns in wallets table: {missing_columns}")
                # Thêm các cột còn thiếu
                for col in missing_columns:
                    if col == 'balance':
                        cursor.execute("ALTER TABLE wallets ADD COLUMN balance REAL DEFAULT 0")
                    elif col == 'created_at':
                        cursor.execute("ALTER TABLE wallets ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    elif col == 'label':
                        cursor.execute("ALTER TABLE wallets ADD COLUMN label TEXT DEFAULT 'My Wallet'")
                    elif col == 'private_key':
                        cursor.execute("ALTER TABLE wallets ADD COLUMN private_key TEXT")
                    elif col == 'address':
                        cursor.execute("ALTER TABLE wallets ADD COLUMN address TEXT")
                self.db.commit()
                logger.info("Added missing columns to wallets table")
            
            # Kiểm tra bảng transactions có tồn tại không
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
            if not cursor.fetchone():
                logger.info("Creating transactions table")
                cursor.execute('''
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_wallet TEXT NOT NULL,
                    to_wallet TEXT NOT NULL,
                    amount REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                ''')
                self.db.commit()
                logger.info("Created transactions table")
                
        except Exception as e:
            logger.error(f"Error ensuring wallet table: {str(e)}")
            raise

    def create_wallet(self, wallet_data: Dict[str, Any]) -> int:
        """Tạo ví mới"""
        try:
            logger.info(f"Creating new wallet with data: {wallet_data}")
            
            cursor = self.db.cursor()
            
            # Kiểm tra dữ liệu đầu vào
            required_fields = ["user_id", "address", "private_key", "label"]
            for field in required_fields:
                if field not in wallet_data:
                    logger.error(f"Missing required field: {field}")
                    return None
                
            cursor.execute(
                "INSERT INTO wallets (user_id, address, private_key, label, balance) VALUES (?, ?, ?, ?, ?)",
                (
                    wallet_data["user_id"],
                    wallet_data["address"],
                    wallet_data["private_key"],
                    wallet_data["label"],
                    wallet_data.get("balance", 0)
                )
            )
            self.db.commit()
            
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating wallet: {str(e)}")
            return None
    
    def get_wallet_by_id(self, wallet_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin ví theo ID"""
        try:
            logger.info(f"Getting wallet by ID: {wallet_id}")
            
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT id, user_id, address, private_key, label, balance, created_at FROM wallets WHERE id = ?",
                (wallet_id,)
            )
            
            wallet_data = cursor.fetchone()
            
            if not wallet_data:
                logger.warning(f"Wallet not found with ID: {wallet_id}")
                return None
            
            wallet = {
                "id": wallet_data[0],
                "user_id": wallet_data[1],
                "address": wallet_data[2],
                "private_key": wallet_data[3],
                "label": wallet_data[4],
                "balance": wallet_data[5],
                "created_at": wallet_data[6]
            }
            
            logger.info(f"Found wallet: {wallet}")
            return wallet
        except Exception as e:
            logger.error(f"Error getting wallet by ID: {str(e)}")
            return None
    
    def get_wallets_by_user_id(self, user_id: int) -> List[Dict[str, Any]]:
        """Lấy danh sách ví của user"""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT id, user_id, label, address, private_key, balance, created_at
                FROM wallets
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            
            wallets = []
            for row in cursor.fetchall():
                wallet = {
                    "id": row[0],
                    "user_id": row[1],
                    "label": row[2],
                    "address": row[3],
                    "private_key": row[4],
                    "balance": float(row[5]),
                    "created_at": row[6]
                }
                wallets.append(wallet)
            
            return wallets
            
        except Exception as e:
            logger.error(f"Error getting wallets by user_id: {str(e)}")
            raise
    
    def get_wallet_by_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin ví theo địa chỉ"""
        try:
            logger.info(f"Getting wallet by address: {address}")
            
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT id, user_id, address, private_key, label, balance, created_at FROM wallets WHERE address = ?",
                (address,)
            )
            
            wallet_data = cursor.fetchone()
            
            if not wallet_data:
                logger.warning(f"Wallet not found with address: {address}")
                return None
            
            wallet = {
                "id": wallet_data[0],
                "user_id": wallet_data[1],
                "address": wallet_data[2],
                "private_key": wallet_data[3],
                "label": wallet_data[4],
                "balance": wallet_data[5],
                "created_at": wallet_data[6]
            }
            
            logger.info(f"Found wallet: {wallet}")
            return wallet
        except Exception as e:
            logger.error(f"Error getting wallet by address: {str(e)}")
            return None
    
    def update_wallet(self, wallet_id: int, wallet_data: Dict[str, Any]) -> bool:
        """Cập nhật thông tin ví"""
        try:
            logger.info(f"Updating wallet ID {wallet_id} with data: {wallet_data}")
            
            # Kiểm tra ví tồn tại
            existing_wallet = self.get_wallet_by_id(wallet_id)
            if not existing_wallet:
                logger.warning(f"Wallet not found with ID: {wallet_id}")
                return False
            
            # Chuẩn bị dữ liệu cập nhật
            updates = []
            params = []
            
            if "label" in wallet_data:
                updates.append("label = ?")
                params.append(wallet_data["label"])
            
            if "balance" in wallet_data:
                updates.append("balance = ?")
                params.append(wallet_data["balance"])
            
            if not updates:
                logger.warning("No fields to update")
                return False
            
            # Thêm wallet_id vào params
            params.append(wallet_id)
            
            # Cập nhật vào database
            cursor = self.db.cursor()
            cursor.execute(
                f"UPDATE wallets SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )
            self.db.commit()
            
            logger.info(f"Wallet updated successfully: {wallet_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating wallet: {str(e)}")
            return False
    
    def delete_wallet(self, wallet_id: int) -> bool:
        """Xóa ví"""
        try:
            logger.info(f"Deleting wallet with ID: {wallet_id}")
            
            # Kiểm tra ví tồn tại
            existing_wallet = self.get_wallet_by_id(wallet_id)
            if not existing_wallet:
                logger.warning(f"Wallet not found with ID: {wallet_id}")
                return False
            
            # Xóa khỏi database
            cursor = self.db.cursor()
            cursor.execute("DELETE FROM wallets WHERE id = ?", (wallet_id,))
            self.db.commit()
            
            logger.info(f"Wallet deleted successfully: {wallet_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting wallet: {str(e)}")
            return False
    
    def transfer(self, from_address: str, to_address: str, amount: float) -> bool:
        """Chuyển tiền giữa các ví"""
        try:
            logger.info(f"Transferring {amount} from {from_address} to {to_address}")
            
            # Kiểm tra ví nguồn
            source_wallet = self.get_wallet_by_address(from_address)
            if not source_wallet:
                logger.warning(f"Source wallet not found: {from_address}")
                return False
            
            # Kiểm tra ví đích
            dest_wallet = self.get_wallet_by_address(to_address)
            if not dest_wallet:
                logger.warning(f"Destination wallet not found: {to_address}")
                return False
            
            # Kiểm tra số dư
            if float(source_wallet["balance"]) < amount:
                logger.warning(f"Insufficient balance: {source_wallet['balance']} < {amount}")
                return False
            
            # Cập nhật số dư
            cursor = self.db.cursor()
            
            # Trừ tiền từ ví nguồn
            cursor.execute(
                "UPDATE wallets SET balance = balance - ? WHERE address = ?",
                (amount, from_address)
            )
            
            # Cộng tiền vào ví đích
            cursor.execute(
                "UPDATE wallets SET balance = balance + ? WHERE address = ?",
                (amount, to_address)
            )
            
            self.db.commit()
            
            logger.info(f"Transfer completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error transferring funds: {str(e)}")
            return False
    
    def deposit(self, wallet_address: str, amount: float) -> bool:
        """Nạp tiền vào ví"""
        try:
            logger.info(f"Depositing {amount} to {wallet_address}")
            
            # Kiểm tra ví
            wallet = self.get_wallet_by_address(wallet_address)
            if not wallet:
                logger.warning(f"Wallet not found: {wallet_address}")
                return False
            
            # Cập nhật số dư
            cursor = self.db.cursor()
            cursor.execute(
                "UPDATE wallets SET balance = balance + ? WHERE address = ?",
                (amount, wallet_address)
            )
            self.db.commit()
            
            logger.info(f"Deposit completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error depositing funds: {str(e)}")
            return False
    
    def get_transactions_by_wallet(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Lấy danh sách giao dịch của ví"""
        try:
            logger.info(f"Getting transactions for wallet: {wallet_address}")
            
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT id, from_wallet, to_wallet, amount, timestamp, type, status FROM transactions WHERE from_wallet = ? OR to_wallet = ? ORDER BY timestamp DESC",
                (wallet_address, wallet_address)
            )
            
            transactions_data = cursor.fetchall()
            
            transactions = []
            for tx_data in transactions_data:
                transaction = {
                    "id": tx_data[0],
                    "from_wallet": tx_data[1],
                    "to_wallet": tx_data[2],
                    "amount": tx_data[3],
                    "timestamp": tx_data[4],
                    "type": tx_data[5],
                    "status": tx_data[6]
                }
                transactions.append(transaction)
            
            logger.info(f"Found {len(transactions)} transactions for wallet {wallet_address}")
            return transactions
        except Exception as e:
            logger.error(f"Error getting transactions by wallet: {str(e)}")
            return []
    
    def create_transaction(self, transaction_data: Dict[str, Any]) -> int:
        """Tạo giao dịch mới và trả về ID của giao dịch"""
        try:
            logger.info(f"Creating new transaction with data: {transaction_data}")
            
            # Kiểm tra dữ liệu đầu vào
            required_fields = ["from_wallet", "to_wallet", "amount"]
            for field in required_fields:
                if field not in transaction_data:
                    logger.error(f"Missing required field: {field}")
                    return None
            
            # Chuẩn bị dữ liệu
            from_wallet = transaction_data["from_wallet"]
            to_wallet = transaction_data["to_wallet"]
            amount = transaction_data["amount"]
            timestamp = transaction_data.get("timestamp", datetime.now().isoformat())
            tx_type = transaction_data.get("type", "transfer")
            status = transaction_data.get("status", "success")
            
            # Thêm vào database
            cursor = self.db.cursor()
            cursor.execute(
                "INSERT INTO transactions (from_wallet, to_wallet, amount, timestamp, type, status) VALUES (?, ?, ?, ?, ?, ?)",
                (from_wallet, to_wallet, amount, timestamp, tx_type, status)
            )
            self.db.commit()
            
            # Lấy ID của giao dịch vừa tạo
            transaction_id = cursor.lastrowid
            logger.info(f"Transaction created with ID: {transaction_id}")
            
            return transaction_id
        except Exception as e:
            logger.error(f"Error creating transaction: {str(e)}")
            return None

    @staticmethod
    async def get_all_wallets_by_user_id(conn: Connection, user_id: int):
        try:
            cursor = conn.cursor()
            
            # In ra câu lệnh SQL để debug
            print("Checking table structure before query...")
            cursor.execute("PRAGMA table_info(wallets)")
            columns = cursor.fetchall()
            print(f"Table columns: {columns}")
            
            cursor.execute("SELECT * FROM wallets WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            wallet_data = cursor.fetchall()
            
            print(f"Raw wallet data: {wallet_data}")
            
            wallets = []
            for data in wallet_data:
                try:
                    # Tạo dictionary từ dữ liệu wallet theo cấu trúc thực tế
                    # id | address | private_key | user_id | balance | created_at
                    wallet_dict = {
                        "id": data[0],
                        "address": data[1],
                        "private_key": data[2],
                        "user_id": data[3],
                        "balance": float(data[4]) if data[4] is not None else 0.0,
                        "created_at": data[5]
                    }
                    wallets.append(wallet_dict)
                except Exception as e:
                    print(f"Error processing wallet data: {e}")
                    print(f"Problematic data: {data}")
            
            return wallets
        except Exception as e:
            print(f"Error fetching wallets by user_id: {e}")
            return []

    @staticmethod
    async def get_wallet_by_user_id(conn: Connection, user_id: int) -> Optional[Wallet]:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM wallets WHERE user_id = ?", (user_id,))
            wallet_data = cursor.fetchone()
            
            if wallet_data:
                # Ensure private_key is converted to string
                private_key = str(wallet_data[3]) if wallet_data[3] is not None else ""
                return Wallet(
                    id=wallet_data[0],
                    address=wallet_data[1],
                    balance=Decimal(str(wallet_data[2] or '0.00')),
                    private_key=private_key,  # Convert to string
                    user_id=wallet_data[4],
                    created_at=wallet_data[5]
                )
            return None
        except Exception as e:
            print(f"Error fetching wallet by user_id: {e}")
            return None