from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from API.Routes import auth, wallets, transactions
from database import get_db, create_tables
import logging
import uvicorn

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Hiển thị log ra console
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Thêm CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các origin trong môi trường phát triển
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả các phương thức HTTP
    allow_headers=["*"],  # Cho phép tất cả các header
)

# Mount static files - cho phép truy cập trực tiếp vào uploaded files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Đăng ký các router
app.include_router(auth.router, prefix="/api/auth")
app.include_router(wallets.router, prefix="/api/wallets")
app.include_router(transactions.router, prefix="/api/transactions")

# Tạo bảng nếu chưa tồn tại
create_tables()

# Health check endpoint
@app.get("/")
async def root():
    return {"status": "API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Chạy ứng dụng
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
