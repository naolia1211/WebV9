from fastapi import APIRouter, Depends, HTTPException, status, Body, File, UploadFile
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional, Dict, Any
import json
import os
from datetime import datetime
from sqlite3 import Connection
from Models.wallet import Wallet, WalletCreate, WalletResponse, BlockchainTransfer
from database import get_db
from repositories.wallet_repository import WalletRepository
from Models.user import UserInDB
from API.Routes.auth import get_current_user
import logging
import time



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.post("/create", response_model=Dict[str, Any])
async def create_wallet(
    wallet_data: WalletCreate = Body(...),
    db: Connection = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        logger.info(f"Creating wallet with data: {wallet_data}")
        
        if not wallet_data.user_id:
            return {"status": "error", "message": "user_id is required"}
        if wallet_data.user_id != current_user.id:
            return {"status": "error", "message": "Unauthorized: user_id does not match current user"}
            
        wallet_repo = WalletRepository(db)
        
        
        wallet_id = wallet_repo.create_wallet({
            "user_id": wallet_data.user_id,
            "label": wallet_data.label or "New Wallet"
        })
        
        if not wallet_id:
            return {"status": "error", "message": "Failed to create wallet"}
            
       
        wallet = wallet_repo.get_wallet_by_id(wallet_id)
        return {
            "status": "success",
            "message": "Wallet created successfully",
            "wallet": wallet
        }
    except Exception as e:
        logger.error(f"Error creating wallet: {str(e)}")
        return {"status": "error", "message": f"Failed to create wallet: {str(e)}"}


@router.get("/user/{user_id}", response_model=Dict[str, Any])
async def get_user_wallets(
    user_id: int,
    db: Connection = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        if user_id != current_user.id:
            return {"status": "error", "message": "Unauthorized: cannot access other user's wallets"}
        
        wallet_repo = WalletRepository(db)
        wallets = wallet_repo.get_wallets_by_user_id(user_id)
        
        return {"status": "success", "wallets": wallets}
    except Exception as e:
        logger.error(f"Error getting user wallets: {str(e)}")
        return {"status": "error", "message": "Failed to get wallets", "wallets": []}


@router.get("/{wallet_id}", response_model=Dict[str, Any])
async def get_wallet(
    wallet_id: int,
    db: Connection = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        wallet_repo = WalletRepository(db)
        wallet = wallet_repo.get_wallet_by_id(wallet_id)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        if wallet["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized: you do not own this wallet")
        
        return {"status": "success", "wallet": wallet}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting wallet: {str(e)}")
    
@router.delete("/{wallet_id}", response_model=Dict[str, Any])
async def delete_wallet(
   wallet_id: int,
   db: Connection = Depends(get_db),
   current_user: UserInDB = Depends(get_current_user)
):
   try:
       wallet_repo = WalletRepository(db)
       wallet = wallet_repo.get_wallet_by_id(wallet_id)
       
       if not wallet:
           raise HTTPException(status_code=404, detail="Wallet not found")
       
       success = wallet_repo.delete_wallet(wallet_id)
       if not success:
           raise HTTPException(status_code=500, detail="Failed to delete wallet")
       
       return {"status": "success", "message": "Wallet deleted successfully"}
   except HTTPException as he:
       raise he
   except Exception as e:
       raise HTTPException(status_code=500, detail=f"Error deleting wallet: {str(e)}")

@router.get("/address/{address}", response_model=dict)
async def get_wallet_by_address(
    address: str,
    db: Connection = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        wallet_repo = WalletRepository(db)
        wallet = wallet_repo.get_wallet_by_address(address)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        if wallet["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized: you do not own this wallet")
        
        return {"status": "success", "wallet": wallet}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
@router.post("/reveal", response_model=dict)
async def reveal_wallet(
    wallet_data: Dict[str, Any] = Body(...),
    db: Connection = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        wallet_address = wallet_data.get("wallet_address")
        if not wallet_address:
            raise HTTPException(status_code=400, detail="wallet_address is required")
        
        wallet_repo = WalletRepository(db)
        wallet = wallet_repo.get_wallet_by_address(wallet_address)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        
        user_has_access = False
      
        if wallet["user_id"] == current_user.id:
            user_has_access = True
        else:
        
            shared_with = wallet_data.get("shared_with", [])
            if current_user.email in shared_with:
                user_has_access = True
        
        if not user_has_access:
            raise HTTPException(status_code=403, detail="Unauthorized: you do not own this wallet")
        
        return {
            "status": "success",
            "address": wallet["address"],
            "private_key": wallet["private_key"],
            "warning": "WARNING: Your private key grants full access to your funds. Never share it with anyone!"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/deposit", response_model=dict)
async def deposit_money(
    deposit_data: Dict[str, Any] = Body(...),
    db: Connection = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        wallet_address = deposit_data.get("wallet_address")
        amount = float(deposit_data.get("amount", 0))
        
        logger.info(f"API: Deposit request received for wallet: {wallet_address}, amount: {amount} ETH")
        logger.info(f"API: User: {current_user.id}, name: {current_user.name}")
        
        # Validate inputs
        if not wallet_address:
            logger.error("API: Missing wallet_address in request")
            return {"status": "error", "message": "wallet_address is required"}
        
        if amount <= 0:
            logger.error(f"API: Invalid amount {amount}")
            return {"status": "error", "message": "amount must be greater than 0"}
        
     
        wallet_repo = WalletRepository(db)
        

        logger.info(f"API: Blockchain URL: {wallet_repo.blockchain.blockchain_url}")
        logger.info(f"API: Web3 provider: {wallet_repo.blockchain.w3.provider}")
        

        if not wallet_repo.blockchain.is_valid_eth_address(wallet_address):
            logger.error(f"API: Invalid Ethereum address format: {wallet_address}")
            return {"status": "error", "message": "Invalid Ethereum wallet address format"}
        
   
        if not wallet_repo.blockchain.w3.is_connected():
            logger.error("API: Blockchain connection error - not connected to Ganache")
            return {"status": "error", "message": "Cannot connect to blockchain node (Ganache). Please verify that Ganache is running."}
            
      
        try:
            accounts = wallet_repo.blockchain.w3.eth.accounts
            logger.info(f"API: Found {len(accounts)} accounts in Ganache")
            
            if len(accounts) == 0:
                logger.error("API: No accounts found in Ganache")
                return {"status": "error", "message": "No accounts found in Ganache. Please check your Ganache configuration."}
                
         
            for idx, account in enumerate(accounts[:3]):
                balance = wallet_repo.blockchain.w3.eth.get_balance(account)
                balance_eth = wallet_repo.blockchain.w3.from_wei(balance, "ether")
                logger.info(f"API: Ganache account #{idx}: {account} - {balance_eth} ETH")
        except Exception as acc_error:
            logger.error(f"API: Error accessing Ganache accounts: {str(acc_error)}")
            return {"status": "error", "message": f"Error accessing Ganache accounts: {str(acc_error)}"}
        
      
        logger.info(f"API: Checking wallet {wallet_address} in database")
        wallet = wallet_repo.get_wallet_by_address(wallet_address)
        
        if not wallet:
            logger.error(f"API: Wallet {wallet_address} not found in database")
            return {"status": "error", "message": "Wallet not found in database"}
            
        if wallet["user_id"] != current_user.id:
            logger.error(f"API: Unauthorized wallet access by user {current_user.id}")
            return {"status": "error", "message": "Unauthorized: you do not own this wallet"}
        
      
        try:
            previous_balance = wallet_repo.blockchain.get_balance(wallet_address)
            logger.info(f"API: Current balance for {wallet_address}: {previous_balance} ETH")
        except Exception as balance_error:
            logger.error(f"API: Error checking current balance: {str(balance_error)}")
            previous_balance = float(wallet.get("balance", 0))
            logger.info(f"API: Using database balance: {previous_balance} ETH")
        
        
        logger.info(f"API: Initiating deposit from Ganache to {wallet_address} for {amount} ETH")
        success, result = wallet_repo.deposit_from_ganache(wallet_address, amount)
        
        if not success:
            logger.error(f"API: Deposit failed: {result}")
            return {"status": "error", "message": f"Deposit failed: {result}"}
        
     
        import time
        time.sleep(2) 
        
      
        try:
            updated_balance = wallet_repo.blockchain.get_balance(wallet_address)
            logger.info(f"API: Balance after deposit: {previous_balance} -> {updated_balance}")
        except Exception as balance_error:
            logger.error(f"API: Error updating balance after deposit: {str(balance_error)}")
         
            updated_balance = result.get("new_balance", previous_balance)
            logger.info(f"API: Using transaction result balance: {updated_balance}")
            
       
        response = {
            "status": "success",
            "message": "Deposit completed successfully",
            "transaction_hash": result.get("hash", ""),
            "from_account": result.get("from", "Unknown sender"),
            "gas_used": result.get("gas_used", 0),
            "wallet": {
                "address": wallet_address,
                "previous_balance": previous_balance,
                "current_balance": updated_balance,
                "change": float(updated_balance) - float(previous_balance)
            }
        }
        logger.info(f"API: Deposit response prepared: {response}")
        return response
    except Exception as e:
        logger.error(f"API: Error depositing funds: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.get("/balance/{address}", response_model=dict)
async def get_wallet_balance(
    address: str,
    db: Connection = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        
        cache_key = f"balance_{address}"
        current_time = time.time()
        
       
        cursor = db.cursor()
        cursor.execute("PRAGMA temp.table_info(response_cache)")
        if cursor.fetchone():
            cursor.execute("SELECT data, timestamp FROM response_cache WHERE key = ?", (cache_key,))
            cache_row = cursor.fetchone()
            
            if cache_row and (current_time - cache_row[1]) < 10.0:  
                
               
                logger.info(f"Using cached balance for address {address}")
                return json.loads(cache_row[0])
        
       
        wallet_repo = WalletRepository(db)
        wallet = wallet_repo.get_wallet_by_address(address)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        if wallet["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized: you do not own this wallet")
        
        balance = wallet_repo.blockchain.get_balance(address)
        if abs(float(balance) - float(wallet["balance"])) > 0.0001:
            cursor = wallet_repo.db.cursor()
            cursor.execute("UPDATE wallets SET balance = ? WHERE address = ?", (balance, address))
            wallet_repo.db.commit()
        
        result = {"status": "success", "address": address, "balance": balance}
        
        
        cursor.execute(
            "INSERT OR REPLACE INTO response_cache (key, data, timestamp) VALUES (?, ?, ?)",
            (cache_key, json.dumps(result), current_time)
        )
        db.commit()
        
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting wallet balance: {str(e)}")

@router.post("/transfer", response_model=dict)
async def transfer_money(
    transfer_data: Dict[str, Any] = Body(...),
    db: Connection = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    try:
        from_wallet = transfer_data.get("from_wallet")
        to_wallet = transfer_data.get("to_wallet")
        amount = float(transfer_data.get("amount", 0))
        confirm = transfer_data.get("confirm", False)

        bypass_auth = transfer_data.get("bypass_auth", False)
       
        logger.info(f"Transfer request from user {current_user.id}: {from_wallet} -> {to_wallet}, amount: {amount}")
       
        if not all([from_wallet, to_wallet, amount]):
            return {"status": "error", "message": "Missing required fields: from_wallet, to_wallet, amount"}
       
        if not confirm:
            return {"status": "error", "message": "Transaction must be confirmed"}
       
        if amount <= 0:
            return {"status": "error", "message": "Amount must be greater than 0"}
       
        wallet_repo = WalletRepository(db)
       
        source_wallet = wallet_repo.get_wallet_by_address(from_wallet)
        if not source_wallet:
            return {"status": "error", "message": "Source wallet not found"}

        if not bypass_auth and source_wallet["user_id"] != current_user.id:
            return {"status": "error", "message": "Unauthorized: you do not own this wallet"}
       
        private_key = source_wallet["private_key"]

        if not bypass_auth:
            balance = wallet_repo.blockchain.get_balance(from_wallet)
            if balance < amount:
                return {"status": "error", "message": f"Insufficient balance: {balance} < {amount}"}
       
        success, result = wallet_repo.transfer(
            from_wallet,
            to_wallet,
            amount,
            private_key
        )
       
        if not success:
            return {"status": "error", "message": f"Transfer failed: {result}"}
       
        updated_balance = wallet_repo.blockchain.get_balance(from_wallet)
       
        return {
            "status": "success",
            "message": "Transfer completed successfully",
            "transaction_hash": result.get("hash", ""),
            "updated_balance": updated_balance
        }
       
    except Exception as e:
        # A08 Vulnerability: Revealing detailed error messages
        return {"status": "error", "message": str(e)}
    
