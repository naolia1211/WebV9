from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from API.Routes import auth, wallets, transactions
from database import get_db, create_tables
import logging
import uvicorn



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(auth.router, prefix="/api/auth")
app.include_router(wallets.router, prefix="/api/wallets")
app.include_router(transactions.router, prefix="/api/transactions")


create_tables()


@app.get("/")
async def root():
    return {"status": "API is running"}

@app.get("/health")
async def health_check():
    try:
      
        db = get_db()
        db.execute("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}  


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")