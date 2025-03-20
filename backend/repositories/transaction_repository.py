from typing import Optional, List
from sqlite3 import Connection
from Models.transaction import TransactionCreate, Transaction

class TransactionRepository:
    def __init__(self, db: Connection):
        self.db = db

    def create_transaction(self, transaction: TransactionCreate) -> Optional[Transaction]:
        """Tạo giao dịch mới"""
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
            print(f"Error creating transaction: {e}")
            return None

    def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Lấy giao dịch theo ID"""
        cursor = self.db.cursor()
        cursor.execute(
            """SELECT id, from_wallet, to_wallet, amount, type, status, timestamp 
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
                timestamp=data[6]
            )
        return None

    @staticmethod
    async def get_wallet_transactions(conn: Connection, wallet_id: int) -> List[Transaction]:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE wallet_id = ? ORDER BY created_at DESC", 
            (wallet_id,)
        )
        transactions = cursor.fetchall()
        
        return [
            Transaction(
                id=t[0],
                wallet_id=t[1],
                from_wallet=t[2],
                recipient=t[3],
                status=t[4],
                transaction_type=t[5],
                amount=t[6],
                created_at=t[7],
                tx_hash=t[8]
            )
            for t in transactions
        ]