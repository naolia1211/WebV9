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


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.post("/blockchain", response_model=Dict[str, Any])
async def create_blockchain_transaction(
    transaction: BlockchainTransactionCreate,
    db: Connection = Depends(get_db)
):
    """Tạo giao dịch mới trên blockchain"""
    try:
       
        tx_repo = TransactionRepository(db)
        wallet_repo = WalletRepository(db)
        
   
        source_wallet = wallet_repo.get_wallet_by_address(transaction.from_wallet)
        if not source_wallet:
            raise HTTPException(status_code=404, detail="Source wallet not found")
        

        balance = wallet_repo.blockchain.get_balance(transaction.from_wallet)
        if balance < transaction.amount:
            raise HTTPException(status_code=400, detail=f"Insufficient balance: {balance} < {transaction.amount}")
        

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


@router.get("/{wallet_address}", response_model=List[Dict[str, Any]])
async def get_transactions(
    wallet_address: str,
    db: Connection = Depends(get_db)
):
    try:
     
        wallet_repo = WalletRepository(db)
        tx_repo = TransactionRepository(db)
        
    
        wallet = wallet_repo.get_wallet_by_address(wallet_address)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
    
        transactions = tx_repo.get_transactions_by_address(wallet_address)
        
        return transactions
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transactions: {str(e)}")
  