from typing import Optional, List, Dict, Any
from sqlite3 import Connection
from Models.transaction import TransactionCreate, Transaction
from blockchain_service import BlockchainService
import logging
from datetime import datetime


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransactionRepository:
    def __init__(self, db: Connection):
        self.db = db
       
        self.blockchain = BlockchainService()
        self._ensure_table_exists()
        
    def _ensure_table_exists(self):
       
        try:
            cursor = self.db.cursor()
            
           
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
            logger.error(f"Error ensuring tables exist: {str(e)}")
            raise

    def create_transaction(self, transaction: TransactionCreate) -> Optional[Transaction]:
      
        cursor = self.db.cursor()
        try:
            cursor.execute(
                """INSERT INTO transactions 
                (from_wallet, to_wallet, amount, type, status) 
                VALUES (?, ?, ?, ?, ?)""",
                (
                    transaction.from_wallet,
                    transaction.to_wallet,
                    transaction.amount,
                    transaction.type,
                    transaction.status
                )
            )
            self.db.commit()
            return self.get_transaction_by_id(cursor.lastrowid)
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return None

    def create_blockchain_transaction(self, from_wallet: str, to_wallet: str, amount: float, private_key: str) -> Dict[str, Any]:
       
        try:
          
            result = self.blockchain.send_transaction(from_wallet, to_wallet, amount, private_key)
            
            if result.get("status") == "failed":
                logger.error(f"Failed to send transaction: {result.get('error')}")
                return {"status": "error", "message": result.get("error")}
            
          
            cursor = self.db.cursor()
            cursor.execute(
                """INSERT INTO transactions 
                (from_wallet, to_wallet, amount, timestamp, type, status, hash, block_number) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    from_wallet,
                    to_wallet,
                    amount,
                    datetime.now().isoformat(),
                    "transfer",
                    "completed",
                    result.get("hash"),
                    result.get("block_number")
                )
            )
            self.db.commit()
            
        
            transaction_id = cursor.lastrowid
            
       
            result["id"] = transaction_id
            
            return {"status": "success", "transaction": result}
        except Exception as e:
            logger.error(f"Error creating blockchain transaction: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
   
        cursor = self.db.cursor()
        cursor.execute(
            """SELECT id, from_wallet, to_wallet, amount, type, status, timestamp, hash, block_number 
            FROM transactions WHERE id = ?""",
            (transaction_id,)
        )
        data = cursor.fetchone()
        if data:
            return Transaction(
                id=data[0],
                from_wallet=data[1],
                to_wallet=data[2],
                amount=data[3],
                type=data[4],
                status=data[5],
                timestamp=data[6],
                hash=data[7] if len(data) > 7 else None,
                block_number=data[8] if len(data) > 8 else None
            )
        return None

    def get_transactions_by_address(self, address: str, limit: int = 50) -> List[Dict[str, Any]]:
     
        try:
   
            blockchain_txs = self.blockchain.get_transaction_history(address, limit)
            
       
            for tx in blockchain_txs:
         
                cursor = self.db.cursor()
                cursor.execute("SELECT id FROM transactions WHERE hash = ?", (tx["hash"],))
                
                if not cursor.fetchone():
             
                    cursor.execute(
                        """INSERT INTO transactions 
                        (from_wallet, to_wallet, amount, timestamp, type, status, hash, block_number) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            tx["from_wallet"],
                            tx["to_wallet"],
                            tx["amount"],
                            tx["timestamp"],
                            tx["type"],
                            tx["status"],
                            tx["hash"],
                            tx["block_number"]
                        )
                    )
                    self.db.commit()
            
           
            cursor = self.db.cursor()
            cursor.execute(
                """SELECT id, from_wallet, to_wallet, amount, timestamp, type, status, hash, block_number 
                FROM transactions 
                WHERE from_wallet = ? OR to_wallet = ? 
                ORDER BY timestamp DESC 
                LIMIT ?""",
                (address, address, limit)
            )
            
            transactions = []
            for tx_data in cursor.fetchall():
                transaction = {
                    "id": tx_data[0],
                    "from_wallet": tx_data[1],
                    "to_wallet": tx_data[2],
                    "amount": tx_data[3],
                    "timestamp": tx_data[4],
                    "type": tx_data[5],
                    "status": tx_data[6],
                    "hash": tx_data[7] if len(tx_data) > 7 else None,
                    "block_number": tx_data[8] if len(tx_data) > 8 else None
                }
                transactions.append(transaction)
            
            return transactions
        except Exception as e:
            logger.error(f"Error getting transactions by address: {str(e)}")
            return []