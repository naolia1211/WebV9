from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import List, Dict, Any
from sqlite3 import Connection
from database import get_db
from repositories.wallet_repository import WalletRepository
from datetime import datetime
import logging

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.get("/{wallet_address}", response_model=List[Dict[str, Any]])
async def get_transactions(
    wallet_address: str,
    db: Connection = Depends(get_db)
):
    try:
        # Khởi tạo WalletRepository với tham số db
        wallet_repo = WalletRepository(db)
        
        # Kiểm tra ví tồn tại
        wallet = wallet_repo.get_wallet_by_address(wallet_address)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Lấy giao dịch
        transactions = wallet_repo.get_transactions_by_wallet(wallet_address)
        
        return transactions
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transactions: {str(e)}")

@router.get("/wallet/{keyword}", response_model=List[Dict[str, Any]])
async def search_transactions(
    keyword: str, 
    db: Connection = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Tìm kiếm giao dịch theo từ khóa"""
    try:
        # Khởi tạo WalletRepository với tham số db
        wallet_repo = WalletRepository(db)
        
        # Tìm kiếm ví theo địa chỉ
        wallet = wallet_repo.get_wallet_by_address(keyword)
        if wallet:
            # Nếu tìm thấy ví, lấy danh sách giao dịch của ví đó
            transactions = wallet_repo.get_transactions_by_wallet(keyword)
            return transactions
        
        # Nếu không tìm thấy ví, trả về danh sách rỗng
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/", response_model=List[Dict[str, Any]])
async def get_all_transactions(
    db: Connection = Depends(get_db)
):
    try:
        # Khởi tạo WalletRepository với tham số db
        wallet_repo = WalletRepository(db)
        
        # Lấy tất cả giao dịch
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, from_wallet, to_wallet, amount, timestamp, type, status FROM transactions ORDER BY timestamp DESC"
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
        
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transactions: {str(e)}")

@router.get("/user/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_transactions(
    user_id: int,
    db: Connection = Depends(get_db)
):
    try:
        # Khởi tạo WalletRepository với tham số db
        wallet_repo = WalletRepository(db)
        
        # Lấy danh sách ví của user
        cursor = db.cursor()
        cursor.execute("SELECT address FROM wallets WHERE user_id = ?", (user_id,))
        wallet_addresses = [row[0] for row in cursor.fetchall()]
        
        if not wallet_addresses:
            return []
        
        # Lấy giao dịch cho mỗi ví
        all_transactions = []
        for address in wallet_addresses:
            transactions = wallet_repo.get_transactions_by_wallet(address)
            all_transactions.extend(transactions)
        
        # Sắp xếp theo thời gian
        all_transactions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return all_transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user transactions: {str(e)}")

@router.get("/date/{date}", response_model=List[Dict[str, Any]])
async def get_transactions_by_date(
    date: str,
    db: Connection = Depends(get_db)
):
    try:
        # Lấy giao dịch theo ngày
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, from_wallet, to_wallet, amount, timestamp, type, status FROM transactions WHERE date(timestamp) = ? ORDER BY timestamp DESC",
            (date,)
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
        
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transactions by date: {str(e)}")

@router.get("/type/{transaction_type}", response_model=List[Dict[str, Any]])
async def get_transactions_by_type(
    transaction_type: str,
    db: Connection = Depends(get_db)
):
    try:
        # Lấy giao dịch theo loại
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, from_wallet, to_wallet, amount, timestamp, type, status FROM transactions WHERE type = ? ORDER BY timestamp DESC",
            (transaction_type,)
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
        
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transactions by type: {str(e)}")

@router.get("/amount/{min_amount}/{max_amount}", response_model=List[Dict[str, Any]])
async def get_transactions_by_amount_range(
    min_amount: float,
    max_amount: float,
    db: Connection = Depends(get_db)
):
    try:
        # Lấy giao dịch theo khoảng số tiền
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, from_wallet, to_wallet, amount, timestamp, type, status FROM transactions WHERE amount BETWEEN ? AND ? ORDER BY timestamp DESC",
            (min_amount, max_amount)
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
        
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transactions by amount range: {str(e)}")

@router.get("/status/{status}", response_model=List[Dict[str, Any]])
async def get_transactions_by_status(
    status: str,
    db: Connection = Depends(get_db)
):
    try:
        # Lấy giao dịch theo trạng thái
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, from_wallet, to_wallet, amount, timestamp, type, status FROM transactions WHERE status = ? ORDER BY timestamp DESC",
            (status,)
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
        
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transactions by status: {str(e)}")

@router.get("/search/{keyword}", response_model=List[Dict[str, Any]])
async def search_transactions_by_keyword(
    keyword: str,
    db: Connection = Depends(get_db)
):
    try:
        # Tìm kiếm giao dịch theo từ khóa
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, from_wallet, to_wallet, amount, timestamp, type, status FROM transactions WHERE from_wallet LIKE ? OR to_wallet LIKE ? ORDER BY timestamp DESC",
            (f"%{keyword}%", f"%{keyword}%")
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
        
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching transactions: {str(e)}")

@router.get("/period/{start_date}/{end_date}", response_model=List[Dict[str, Any]])
async def get_transactions_by_period(
    start_date: str,
    end_date: str,
    db: Connection = Depends(get_db)
):
    try:
        # Lấy giao dịch theo khoảng thời gian
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, from_wallet, to_wallet, amount, timestamp, type, status FROM transactions WHERE date(timestamp) BETWEEN ? AND ? ORDER BY timestamp DESC",
            (start_date, end_date)
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
        
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transactions by period: {str(e)}")

@router.get("/count/{wallet_address}", response_model=Dict[str, Any])
async def get_transaction_count(
    wallet_address: str,
    db: Connection = Depends(get_db)
):
    try:
        # Khởi tạo WalletRepository với tham số db
        wallet_repo = WalletRepository(db)
        
        # Kiểm tra ví tồn tại
        wallet = wallet_repo.get_wallet_by_address(wallet_address)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Đếm số giao dịch
        cursor = db.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE from_wallet = ? OR to_wallet = ?",
            (wallet_address, wallet_address)
        )
        
        count = cursor.fetchone()[0]
        
        return {
            "wallet_address": wallet_address,
            "transaction_count": count
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transaction count: {str(e)}")

@router.get("/stats/{wallet_address}", response_model=Dict[str, Any])
async def get_transaction_stats(
    wallet_address: str,
    db: Connection = Depends(get_db)
):
    try:
        # Khởi tạo WalletRepository với tham số db
        wallet_repo = WalletRepository(db)
        
        # Kiểm tra ví tồn tại
        wallet = wallet_repo.get_wallet_by_address(wallet_address)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Lấy thống kê giao dịch
        cursor = db.cursor()
        
        # Tổng số giao dịch
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE from_wallet = ? OR to_wallet = ?",
            (wallet_address, wallet_address)
        )
        total_count = cursor.fetchone()[0]
        
        # Tổng số tiền gửi
        cursor.execute(
            "SELECT SUM(amount) FROM transactions WHERE to_wallet = ?",
            (wallet_address,)
        )
        total_received = cursor.fetchone()[0] or 0
        
        # Tổng số tiền gửi
        cursor.execute(
            "SELECT SUM(amount) FROM transactions WHERE from_wallet = ?",
            (wallet_address,)
        )
        total_sent = cursor.fetchone()[0] or 0
        
        # Giao dịch gần đây nhất
        cursor.execute(
            "SELECT timestamp FROM transactions WHERE from_wallet = ? OR to_wallet = ? ORDER BY timestamp DESC LIMIT 1",
            (wallet_address, wallet_address)
        )
        latest_transaction = cursor.fetchone()
        latest_transaction_date = latest_transaction[0] if latest_transaction else None
        
        return {
            "wallet_address": wallet_address,
            "total_transactions": total_count,
            "total_received": total_received,
            "total_sent": total_sent,
            "latest_transaction": latest_transaction_date
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transaction stats: {str(e)}")

@router.get("/summary/{user_id}", response_model=Dict[str, Any])
async def get_transaction_summary(
    user_id: int,
    db: Connection = Depends(get_db)
):
    try:
        # Lấy danh sách ví của user
        cursor = db.cursor()
        cursor.execute("SELECT address FROM wallets WHERE user_id = ?", (user_id,))
        wallet_addresses = [row[0] for row in cursor.fetchall()]
        
        if not wallet_addresses:
            return {
                "user_id": user_id,
                "total_transactions": 0,
                "total_received": 0,
                "total_sent": 0,
                "latest_transaction": None
            }
        
        # Tạo điều kiện IN cho các địa chỉ ví
        placeholders = ', '.join(['?'] * len(wallet_addresses))
        
        # Tổng số giao dịch
        cursor.execute(
            f"SELECT COUNT(*) FROM transactions WHERE from_wallet IN ({placeholders}) OR to_wallet IN ({placeholders})",
            wallet_addresses + wallet_addresses
        )
        total_count = cursor.fetchone()[0]
        
        # Tổng số tiền gửi
        cursor.execute(
            f"SELECT SUM(amount) FROM transactions WHERE to_wallet IN ({placeholders})",
            wallet_addresses
        )
        total_received = cursor.fetchone()[0] or 0
        
        # Tổng số tiền gửi
        cursor.execute(
            f"SELECT SUM(amount) FROM transactions WHERE from_wallet IN ({placeholders})",
            wallet_addresses
        )
        total_sent = cursor.fetchone()[0] or 0
        
        # Giao dịch gần đây nhất
        cursor.execute(
            f"SELECT timestamp FROM transactions WHERE from_wallet IN ({placeholders}) OR to_wallet IN ({placeholders}) ORDER BY timestamp DESC LIMIT 1",
            wallet_addresses + wallet_addresses
        )
        latest_transaction = cursor.fetchone()
        latest_transaction_date = latest_transaction[0] if latest_transaction else None
        
        return {
            "user_id": user_id,
            "total_transactions": total_count,
            "total_received": total_received,
            "total_sent": total_sent,
            "latest_transaction": latest_transaction_date
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transaction summary: {str(e)}")

@router.get("/history/{wallet_address}/{limit}", response_model=List[Dict[str, Any]])
async def get_transaction_history(
    wallet_address: str,
    limit: int = 10,
    db: Connection = Depends(get_db)
):
    try:
        # Khởi tạo WalletRepository với tham số db
        wallet_repo = WalletRepository(db)
        
        # Kiểm tra ví tồn tại
        wallet = wallet_repo.get_wallet_by_address(wallet_address)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Lấy lịch sử giao dịch
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, from_wallet, to_wallet, amount, timestamp, type, status FROM transactions WHERE from_wallet = ? OR to_wallet = ? ORDER BY timestamp DESC LIMIT ?",
            (wallet_address, wallet_address, limit)
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
        
        return transactions
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transaction history: {str(e)}")

@router.get("/chart/{wallet_address}/{period}", response_model=Dict[str, Any])
async def get_transaction_chart_data(
    wallet_address: str,
    period: str,
    db: Connection = Depends(get_db)
):
    try:
        # Khởi tạo WalletRepository với tham số db
        wallet_repo = WalletRepository(db)
        
        # Kiểm tra ví tồn tại
        wallet = wallet_repo.get_wallet_by_address(wallet_address)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Xác định khoảng thời gian
        today = datetime.now().date()
        
        if period == "day":
            # Dữ liệu theo giờ trong ngày
            cursor = db.cursor()
            cursor.execute(
                "SELECT strftime('%H', timestamp) as hour, SUM(CASE WHEN to_wallet = ? THEN amount ELSE 0 END) as received, SUM(CASE WHEN from_wallet = ? THEN amount ELSE 0 END) as sent FROM transactions WHERE date(timestamp) = date('now') AND (from_wallet = ? OR to_wallet = ?) GROUP BY hour ORDER BY hour",
                (wallet_address, wallet_address, wallet_address, wallet_address)
            )
            
            data = cursor.fetchall()
            
            labels = []
            received = []
            sent = []
            
            for row in data:
                labels.append(f"{row[0]}:00")
                received.append(float(row[1]))
                sent.append(float(row[2]))
            
            return {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Received",
                        "data": received
                    },
                    {
                        "label": "Sent",
                        "data": sent
                    }
                ]
            }
            
        elif period == "week":
            # Dữ liệu theo ngày trong tuần
            cursor = db.cursor()
            cursor.execute(
                "SELECT strftime('%w', timestamp) as day, SUM(CASE WHEN to_wallet = ? THEN amount ELSE 0 END) as received, SUM(CASE WHEN from_wallet = ? THEN amount ELSE 0 END) as sent FROM transactions WHERE date(timestamp) >= date('now', '-6 days') AND (from_wallet = ? OR to_wallet = ?) GROUP BY day ORDER BY day",
                (wallet_address, wallet_address, wallet_address, wallet_address)
            )
            
            data = cursor.fetchall()
            
            days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            labels = []
            received = []
            sent = []
            
            for row in data:
                day_index = int(row[0])
                labels.append(days[day_index])
                received.append(float(row[1]))
                sent.append(float(row[2]))
            
            return {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Received",
                        "data": received
                    },
                    {
                        "label": "Sent",
                        "data": sent
                    }
                ]
            }
            
        elif period == "month":
            # Dữ liệu theo ngày trong tháng
            cursor = db.cursor()
            cursor.execute(
                "SELECT strftime('%d', timestamp) as day, SUM(CASE WHEN to_wallet = ? THEN amount ELSE 0 END) as received, SUM(CASE WHEN from_wallet = ? THEN amount ELSE 0 END) as sent FROM transactions WHERE date(timestamp) >= date('now', 'start of month') AND (from_wallet = ? OR to_wallet = ?) GROUP BY day ORDER BY day",
                (wallet_address, wallet_address, wallet_address, wallet_address)
            )
            
            data = cursor.fetchall()
            
            labels = []
            received = []
            sent = []
            
            for row in data:
                labels.append(row[0])
                received.append(float(row[1]))
                sent.append(float(row[2]))
            
            return {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Received",
                        "data": received
                    },
                    {
                        "label": "Sent",
                        "data": sent
                    }
                ]
            }
            
        elif period == "year":
            # Dữ liệu theo tháng trong năm
            cursor = db.cursor()
            cursor.execute(
                "SELECT strftime('%m', timestamp) as month, SUM(CASE WHEN to_wallet = ? THEN amount ELSE 0 END) as received, SUM(CASE WHEN from_wallet = ? THEN amount ELSE 0 END) as sent FROM transactions WHERE date(timestamp) >= date('now', 'start of year') AND (from_wallet = ? OR to_wallet = ?) GROUP BY month ORDER BY month",
                (wallet_address, wallet_address, wallet_address, wallet_address)
            )
            
            data = cursor.fetchall()
            
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            labels = []
            received = []
            sent = []
            
            for row in data:
                month_index = int(row[0]) - 1
                labels.append(months[month_index])
                received.append(float(row[1]))
                sent.append(float(row[2]))
            
            return {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Received",
                        "data": received
                    },
                    {
                        "label": "Sent",
                        "data": sent
                    }
                ]
            }
            
        else:
            raise HTTPException(status_code=400, detail="Invalid period. Valid values are: day, week, month, year")
            
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transaction chart data: {str(e)}")
