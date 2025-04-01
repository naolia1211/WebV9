from web3 import Web3
from eth_account import Account
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlockchainService:
    """Service class để tương tác với blockchain"""
    
    def __init__(self, blockchain_url=None):
        # Lấy URL từ biến môi trường hoặc sử dụng giá trị mặc định
        self.blockchain_url = blockchain_url or os.getenv("BLOCKCHAIN_URL", "http://localhost:7545")
        self.w3 = Web3(Web3.HTTPProvider(self.blockchain_url))
        
        # Kiểm tra kết nối
        if not self.w3.is_connected():
            logger.warning(f"Failed to connect to blockchain at {self.blockchain_url}")
        else:
            logger.info(f"Connected to blockchain at {self.blockchain_url}")
            logger.info(f"Chain ID: {self.w3.eth.chain_id}")
    
    def is_valid_eth_address(self, address: str) -> bool:
        """Kiểm tra xem địa chỉ Ethereum có hợp lệ không"""
        if not isinstance(address, str):
            return False
        return self.w3.is_address(address)  # Sử dụng hàm có sẵn từ web3.py

    def create_wallet(self) -> Dict[str, Any]:
        """Tạo ví mới trên blockchain"""
        try:
            # Tạo tài khoản mới
            account = Account.create()
            
            # Lấy thông tin tài khoản
            address = account.address
            
            # Đảm bảo private key có tiền tố 0x
            private_key = account.key.hex()
            if not private_key.startswith("0x"):
                private_key = "0x" + private_key
            
            logger.info(f"Created new wallet with address: {address}")
            
            return {
                "address": address,
                "private_key": private_key,
                "balance": 0
            }
        except Exception as e:
            logger.error(f"Error creating wallet: {str(e)}")
            raise
    
    def get_balance(self, address: str) -> float:
        """Lấy số dư của ví từ blockchain"""
        try:
            # Kiểm tra kết nối
            if not self.w3.is_connected():
                logger.warning("Not connected to blockchain")
                return 0
            
            # Lấy số dư
            balance_wei = self.w3.eth.get_balance(address)
            balance_eth = self.w3.from_wei(balance_wei, "ether")
            
            logger.info(f"Wallet {address} balance: {balance_eth} ETH")
            
            return float(balance_eth)
        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            return 0
    

    # Trong file blockchain_service.py, thêm phương thức này
    def is_valid_eth_address(self, address: str) -> bool:
        """Kiểm tra xem địa chỉ Ethereum có hợp lệ không"""
        if not isinstance(address, str):
            return False
        return self.w3.is_address(address)  # Sử dụng hàm có sẵn từ web3.py

    def send_transaction(self, from_address: str, to_address: str, amount: float, private_key: str) -> Dict[str, Any]:
        """Gửi giao dịch từ ví này sang ví khác"""
        try:
            # Kiểm tra kết nối
            if not self.w3.is_connected():
                logger.warning("Not connected to blockchain")
                return {"status": "failed", "error": "Not connected to blockchain"}
            
            # Chuẩn hóa private key
            private_key = private_key.strip()
            if not private_key.startswith("0x"):
                private_key = "0x" + private_key
            
            logger.info(f"Using private key format: {private_key[:4]}...{private_key[-4:]} (length: {len(private_key)})")
            
            # Kiểm tra định dạng private key
            if len(private_key) != 66:  # 0x + 64 ký tự hex
                logger.error(f"Invalid private key format: expected 66 chars (with 0x), got {len(private_key)}")
                return {"status": "failed", "error": "Invalid private key format"}
            
            # Kiểm tra nếu private key không phải chuỗi hex hợp lệ
            try:
                int(private_key[2:], 16)  # Thử chuyển đổi sang số hex
            except ValueError:
                logger.error("Private key contains invalid hex characters")
                return {"status": "failed", "error": "Private key contains invalid characters"}
            
            # Chuyển đổi số lượng từ ETH sang Wei
            amount_wei = self.w3.to_wei(amount, "ether")
            
            # Lấy nonce hiện tại của ví gửi
            nonce = self.w3.eth.get_transaction_count(from_address)
            
            # Lấy gas price hiện tại
            gas_price = self.w3.eth.gas_price
            
            # Tạo giao dịch
            tx = {
                "from": from_address,
                "to": to_address,
                "value": amount_wei,
                "gas": 21000,  # Gas cần thiết cho giao dịch ETH đơn giản
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": self.w3.eth.chain_id
            }
            
            try:
                # Ký giao dịch với private key
                signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
                
                # Gửi giao dịch đã ký lên blockchain
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                
                # Đợi giao dịch được xác nhận
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                
                logger.info(f"Transaction sent: {tx_hash.hex()}")
                
                # Trả về thông tin giao dịch
                return {
                    "hash": tx_hash.hex(),
                    "from_wallet": from_address,
                    "to_wallet": to_address,
                    "amount": amount,
                    "timestamp": datetime.now().isoformat(),
                    "type": "transfer",
                    "status": "completed" if receipt.status == 1 else "failed",
                    "block_number": receipt.blockNumber
                }
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error signing/sending transaction: {error_msg}")
                if "invalid sender" in error_msg.lower():
                    return {"status": "failed", "error": "Invalid private key for this address"}
                return {"status": "failed", "error": error_msg}
        except Exception as e:
            logger.error(f"Error sending transaction: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def get_transaction_history(self, address: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Lấy lịch sử giao dịch của một địa chỉ"""
        try:
            # Kiểm tra kết nối
            if not self.w3.is_connected():
                logger.warning("Not connected to blockchain")
                return []
            
            # Lấy block hiện tại
            latest_block = self.w3.eth.block_number
            
            # Lưu trữ các giao dịch
            transactions = []
            
            # Lặp qua các block từ mới nhất đến cũ hơn
            count = 0
            for block_number in range(latest_block, max(0, latest_block - 1000), -1):
                if count >= limit:
                    break
                    
                block = self.w3.eth.get_block(block_number, full_transactions=True)
                
                for tx in block["transactions"]:
                    # Kiểm tra xem địa chỉ có liên quan đến giao dịch không
                    if tx["from"].lower() == address.lower() or (tx["to"] and tx["to"].lower() == address.lower()):
                        transactions.append({
                            "hash": tx["hash"].hex(),
                            "from_wallet": tx["from"],
                            "to_wallet": tx["to"],
                            "amount": float(self.w3.from_wei(tx["value"], "ether")),
                            "timestamp": datetime.fromtimestamp(block["timestamp"]).isoformat(),
                            "type": "transfer",
                            "status": "completed",
                            "block_number": tx["blockNumber"]
                        })
                        count += 1
                        
                        if count >= limit:
                            break
            
            logger.info(f"Found {len(transactions)} transactions for address {address}")
            return transactions
        except Exception as e:
            logger.error(f"Error getting transaction history: {str(e)}")
            return []