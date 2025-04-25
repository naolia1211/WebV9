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
from blockchain_service import BlockchainService
from eth_account.account import Account

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WalletRepository:
    def __init__(self, db: Connection):
        self.db = db
        
        self.blockchain = BlockchainService()
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Đảm bảo bảng wallets tồn tại với cấu trúc đúng"""
        try:
            cursor = self.db.cursor()
            
        
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
            
      
            cursor.execute("PRAGMA table_info(wallets)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            logger.info(f"Wallet table columns: {column_names}")
            
       
            required_columns = ['id', 'user_id', 'label', 'address', 'private_key', 'balance', 'created_at']
            missing_columns = [col for col in required_columns if col not in column_names]
            
            if missing_columns:
                logger.warning(f"Missing columns in wallets table: {missing_columns}")
        
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
                    status TEXT NOT NULL,
                    hash TEXT,
                    block_number INTEGER
                )
                ''')
                self.db.commit()
                logger.info("Created transactions table")
            else:
                cursor.execute("PRAGMA table_info(transactions)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if "hash" not in columns:
                    logger.info("Adding hash column to transactions table")
                    cursor.execute("ALTER TABLE transactions ADD COLUMN hash TEXT")
                    self.db.commit()
                
                if "block_number" not in columns:
                    logger.info("Adding block_number column to transactions table")
                    cursor.execute("ALTER TABLE transactions ADD COLUMN block_number INTEGER")
                    self.db.commit()
                
        except Exception as e:
            logger.error(f"Error ensuring wallet table: {str(e)}")
            raise


    def create_wallet(self, wallet_data: Dict[str, Any]) -> int:
        try:
            logger.info(f"Creating new wallet with data: {wallet_data}")
            
            cursor = self.db.cursor()
            
            if "user_id" not in wallet_data:
                logger.error("Missing required field: user_id")
                return None
            
            blockchain_wallet = self.blockchain.create_wallet()
            
            private_key = blockchain_wallet["private_key"]
            if not private_key.startswith("0x"):
                private_key = "0x" + private_key
            
            new_wallet = {
                "user_id": wallet_data["user_id"],
                "label": wallet_data.get("label", "My Wallet"),  # Không lọc hoặc mã hóa label
                "address": blockchain_wallet["address"],
                "private_key": private_key, 
                "balance": 0
            }
            
            # Sử dụng parameterized query để tránh lỗi cú pháp SQL
            query = "INSERT INTO wallets (user_id, address, private_key, label, balance) VALUES (?, ?, ?, ?, ?)"
            cursor.execute(query, (new_wallet['user_id'], new_wallet['address'], new_wallet['private_key'], new_wallet['label'], new_wallet['balance']))
            self.db.commit()
            
            wallet_id = cursor.lastrowid
            logger.info(f"Created blockchain wallet with ID: {wallet_id}")
            
            return wallet_id
        except Exception as e:
            logger.error(f"Error creating wallet: {str(e)}")
            return None

    def get_wallet_by_id(self, wallet_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin ví theo ID và cập nhật số dư từ blockchain"""
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
            
   
            blockchain_balance = self.blockchain.get_balance(wallet["address"])
            

            if abs(float(blockchain_balance) - float(wallet["balance"])) > 0.0001:
                cursor.execute(
                    "UPDATE wallets SET balance = ? WHERE id = ?",
                    (blockchain_balance, wallet_id)
                )
                self.db.commit()
                wallet["balance"] = blockchain_balance
            
            logger.info(f"Found wallet: {wallet}")
            return wallet
        except Exception as e:
            logger.error(f"Error getting wallet by ID: {str(e)}")
            return None
    
    def get_wallets_by_user_id(self, user_id: int) -> List[Dict[str, Any]]:
     
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
                
       
                blockchain_balance = self.blockchain.get_balance(wallet["address"])
                
           
                if abs(blockchain_balance - wallet["balance"]) > 0.0001:
                    cursor.execute(
                        "UPDATE wallets SET balance = ? WHERE id = ?",
                        (blockchain_balance, wallet["id"])
                    )
                    self.db.commit()
                    wallet["balance"] = blockchain_balance
                
                wallets.append(wallet)
            
            return wallets
            
        except Exception as e:
            logger.error(f"Error getting wallets by user_id: {str(e)}")
            raise
    
    def get_wallet_by_address(self, address: str) -> Optional[Dict[str, Any]]:
      
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
            
  
            blockchain_balance = self.blockchain.get_balance(address)
            

            if abs(float(blockchain_balance) - float(wallet["balance"])) > 0.0001:
                cursor.execute(
                    "UPDATE wallets SET balance = ? WHERE id = ?",
                    (blockchain_balance, wallet["id"])
                )
                self.db.commit()
                wallet["balance"] = blockchain_balance
            
            logger.info(f"Found wallet: {wallet}")
            return wallet
        except Exception as e:
            logger.error(f"Error getting wallet by address: {str(e)}")
            return None
    
    def get_wallet_by_address_no_blockchain(self, address: str) -> Optional[Dict[str, Any]]:
       
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT id, user_id, address, private_key, label, balance, created_at FROM wallets WHERE address = ?",
                (address,)
            )
            
            wallet_data = cursor.fetchone()
            
            if not wallet_data:
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
            
            return wallet
        except Exception as e:
            logger.error(f"Error getting wallet by address (no blockchain): {str(e)}")
            return None
    
    def update_wallet(self, wallet_id: int, wallet_data: Dict[str, Any]) -> bool:

        try:
            logger.info(f"Updating wallet ID {wallet_id} with data: {wallet_data}")
            
    
            existing_wallet = self.get_wallet_by_id(wallet_id)
            if not existing_wallet:
                logger.warning(f"Wallet not found with ID: {wallet_id}")
                return False
            
           
            updates = []
            params = []
            
            if "label" in wallet_data:
                updates.append("label = ?")
                params.append(wallet_data["label"])
            
   
            
            if not updates:
                logger.warning("No fields to update")
                return False
            

            params.append(wallet_id)
            

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

        try:
            logger.info(f"Deleting wallet with ID: {wallet_id}")
            

            existing_wallet = self.get_wallet_by_id(wallet_id)
            if not existing_wallet:
                logger.warning(f"Wallet not found with ID: {wallet_id}")
                return False
            

            cursor = self.db.cursor()
            cursor.execute("DELETE FROM wallets WHERE id = ?", (wallet_id,))
            self.db.commit()
            
            logger.info(f"Wallet deleted successfully: {wallet_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting wallet: {str(e)}")
            return False
    
    def transfer(self, from_address: str, to_address: str, amount: float, private_key: str) -> tuple:
        try:
            logger.info(f"Transferring {amount} ETH from {from_address} to {to_address}")

            private_key = private_key.strip()
            if not private_key.startswith("0x"):
                private_key = "0x" + private_key

            blockchain_balance = self.blockchain.get_balance(from_address)
            if blockchain_balance < amount:
                return False, f"Insufficient balance: {blockchain_balance} < {amount}"
            

            result = self.blockchain.send_transaction(
                from_address,
                to_address,
                amount,
                private_key
            )
            
            if isinstance(result, dict) and result.get("status") == "failed":
                error_msg = result.get("error", "Unknown error")
                return False, error_msg
            
  
            transaction = {
                "from_wallet": from_address,
                "to_wallet": to_address,
                "amount": amount,
                "timestamp": datetime.now().isoformat(),
                "type": "transfer",
                "status": "success",
                "hash": result.get("hash"),
                "block_number": result.get("block_number")
            }
            

            self.save_transaction_history(transaction)

            self.update_wallet_balances([from_address, to_address])
            
            return True, result
        except Exception as e:
            return False, str(e)

    def deposit_from_ganache(self, to_address: str, amount: float) -> tuple:
    
        try:
            logger.info(f"Nạp {amount} ETH vào {to_address}")
            w3 = self.blockchain.w3
            

            if not w3.is_connected():
                return False, "Không kết nối được với blockchain"

            if not self.blockchain.is_valid_eth_address(to_address):
                return False, "Invalid Ethereum wallet address format"
   
            cursor = self.db.cursor()
            cursor.execute("SELECT * FROM wallets WHERE address = ?", (to_address,))
            if not cursor.fetchone():
                return False, f"Ví đích không tồn tại trong hệ thống"
            

            ganache_accounts = w3.eth.accounts
            if not ganache_accounts:
                return False, "Không tìm thấy tài khoản Ganache"

            amount_wei = w3.to_wei(amount, "ether")
            gas_estimate = 21000
            gas_price = w3.eth.gas_price
            total_needed = amount_wei + (gas_estimate * gas_price)
            

            sender_account = None
            for account in ganache_accounts:
                if w3.eth.get_balance(account) >= total_needed:
                    sender_account = account
                    break
            
            if not sender_account:
                return False, "Không có tài khoản Ganache nào có đủ số dư"

            tx = {
                "from": sender_account,
                "to": to_address,
                "value": amount_wei,
                "gas": gas_estimate,
                "gasPrice": gas_price,
                "nonce": w3.eth.get_transaction_count(sender_account),
                "chainId": w3.eth.chain_id
            }

            try:
                tx_hash = w3.eth.send_transaction(tx)
                tx_hash_hex = tx_hash.hex()
                

                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                
                if receipt.status != 1:
                    return False, "Giao dịch thất bại"

                new_balance = self.blockchain.get_balance(to_address)
                cursor.execute("UPDATE wallets SET balance = ? WHERE address = ?", (new_balance, to_address))
                self.db.commit()
                

                transaction_data = {
                    "from_wallet": sender_account,
                    "to_wallet": to_address,
                    "amount": amount,
                    "timestamp": datetime.now().isoformat(),
                    "type": "deposit",
                    "status": "success",
                    "hash": tx_hash_hex,
                    "block_number": receipt.blockNumber
                }
                
                self.save_transaction_history(transaction_data)
                
                return True, {
                    "hash": tx_hash_hex,
                    "from": sender_account,
                    "amount": amount,
                    "new_balance": new_balance
                }
            except Exception as tx_error:
                return False, f"Lỗi giao dịch: {str(tx_error)}"
        except Exception as e:
            return False, str(e)

    def update_wallet_balances(self, addresses: List[str]) -> dict:

        results = {}
        
        for address in addresses:
            try:

                if not self.blockchain.is_valid_eth_address(address):
                    logger.warning(f"Skipping invalid address: {address}")
                    results[address] = {"success": False, "error": "Invalid address"}
                    continue
                    

                wallet = self.get_wallet_by_address_no_blockchain(address) if hasattr(self, 'get_wallet_by_address_no_blockchain') else None
                
                if not wallet:
      
                    logger.info(f"Wallet {address} not found in database, skipping balance update")
                    results[address] = {"success": False, "error": "Wallet not in database"}
                    continue
                

                balance = self.blockchain.get_balance(address)
                

                if abs(float(balance) - float(wallet.get("balance", 0))) > 0.0001:
  
                    cursor = self.db.cursor()
                    cursor.execute(
                        "UPDATE wallets SET balance = ? WHERE address = ?",
                        (balance, address)
                    )
                    self.db.commit()
                    
                    logger.info(f"Updated balance for wallet {address}: {balance}")
                    results[address] = {"success": True, "balance": balance, "updated": True}
                else:
                    logger.info(f"Balance unchanged for wallet {address}: {balance}")
                    results[address] = {"success": True, "balance": balance, "updated": False}
                    
            except Exception as e:
                logger.error(f"Error updating balance for wallet {address}: {str(e)}")
                results[address] = {"success": False, "error": str(e)}
        
        return results
    
    
    def save_transaction_history(self, transaction_data: Dict[str, Any]) -> int:
        """Tạo giao dịch mới và trả về ID của giao dịch"""
        try:
            logger.info(f"Creating new transaction with data: {transaction_data}")

            required_fields = ["from_wallet", "to_wallet", "amount"]
            for field in required_fields:
                if field not in transaction_data:
                    logger.error(f"Missing required field: {field}")
                    return None
            

            from_wallet = transaction_data["from_wallet"]
            to_wallet = transaction_data["to_wallet"]
            amount = transaction_data["amount"]
            timestamp = transaction_data.get("timestamp", datetime.now().isoformat())
            tx_type = transaction_data.get("type", "transfer")
            status = transaction_data.get("status", "success")
            tx_hash = transaction_data.get("hash")
            block_number = transaction_data.get("block_number")
            

            cursor = self.db.cursor()
            cursor.execute("PRAGMA table_info(transactions)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if "hash" in columns and "block_number" in columns:
                cursor.execute(
                    """INSERT INTO transactions 
                    (from_wallet, to_wallet, amount, timestamp, type, status, hash, block_number) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (from_wallet, to_wallet, amount, timestamp, tx_type, status, tx_hash, block_number)
                )
            else:
                cursor.execute(
                    """INSERT INTO transactions 
                    (from_wallet, to_wallet, amount, timestamp, type, status) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (from_wallet, to_wallet, amount, timestamp, tx_type, status)
                )
            
            self.db.commit()

            transaction_id = cursor.lastrowid
            logger.info(f"Transaction created with ID: {transaction_id}")
            
            return transaction_id
        except Exception as e:
            logger.error(f"Error creating transaction: {str(e)}")
            return None

    @staticmethod
    def get_transactions_by_wallet(conn: Connection, wallet_address: str) -> List[Dict]:
        """Lấy tất cả giao dịch liên quan đến một địa chỉ ví"""
        cursor = conn.cursor()
        try:
 
            cursor.execute("""
                SELECT id, from_wallet, to_wallet, amount, type, hash, created_at 
                FROM transactions 
                WHERE from_wallet = ? OR to_wallet = ?
                ORDER BY created_at DESC
            """, (wallet_address, wallet_address))
            
            transactions = cursor.fetchall()

            result = []
            for tx in transactions:
                result.append({
                    "id": tx["id"],
                    "from_wallet": tx["from_wallet"],
                    "to_wallet": tx["to_wallet"],
                    "amount": tx["amount"],
                    "type": tx["type"],
                    "hash": tx["hash"],
                    "created_at": tx["created_at"]
                })
            
            return result
        except Exception as e:
            print(f"Error fetching transactions for wallet {wallet_address}: {e}")
            return []
        finally:
            cursor.close()

    def get_address_from_private_key(self, private_key: str) -> str:
        """Lấy địa chỉ từ private key"""
        try:

            if not private_key.startswith('0x'):
                private_key = '0x' + private_key

            private_key = private_key.strip()

            if len(private_key) > 66:
                private_key = private_key[:66]

            account = Account.from_key(private_key)
            return account.address
        except Exception as e:
            logger.error(f"Error deriving address from private key: {str(e)}")
            raise

    # def export_wallet_data(self, wallet_address: str) -> Dict[str, Any]:
    #     """

        
    #     Args:
    #         wallet_address (str): Địa chỉ ví để export
        
    #     Returns:

    #     try:
    #
    #         wallet = self.get_wallet_by_address(wallet_address)
            
    #         if not wallet:
    #             return None
            
    #     
    #         transactions = self.get_transactions_by_wallet(self.db, wallet_address)
            
    #     
    #         export_data = {
    #             "wallet": {
    #                 "id": wallet.get("id"),
    #                 "user_id": wallet.get("user_id"),
    #                 "address": wallet.get("address"),
    #                 "label": wallet.get("label"),
    #                 "balance": wallet.get("balance"),
    #                 "created_at": wallet.get("created_at")
    #             },
    #             "transactions": transactions,
    #             "blockchain_info": {
    #                 "network": self.blockchain.blockchain_url, 
    #                 "exported_at": datetime.now().isoformat()
    #             }
    #         }
            
    #         return export_data
        
    #     except Exception as e:
    #         logger.error(f"Error exporting wallet data: {str(e)}")
    #         return None

 