import models
import requests
from db import SessionLocal, engine
from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import hashlib
from jwt_utils import create_access_token, verify_token
import schemas

app = FastAPI()
models.Base.metadata.create_all(bind=engine)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/")
def home():
    return {"message": "Welcome to VeriHubs Coins API"}
# ====================
def blacklist_token(db: Session, token: str):
    db_token = models.BlacklistedToken(token=token, is_active=False)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)

def check_blacklist(db: Session, token: str):
    blacklisted_token = db.query(models.BlacklistedToken).filter(models.BlacklistedToken.token == token).first()
    return blacklisted_token
# ====================

@app.get("/protected/")
def protected_route(token: str = Depends(oauth2_scheme)):
    db = SessionLocal()
    blacklisted_token = db.query(models.BlacklistedToken).filter(models.BlacklistedToken.token == token).first()
    db.close()

    if blacklisted_token:
        return JSONResponse(status_code=401, content={"error": "You have been signed out"})

    token_data = verify_token(token)
    return {"message": "You are logged in", "email": token_data.email}


@app.post("/login")
def login(user_request: schemas.LoginRequest):
    db = SessionLocal()
    user = db.query(models.User).filter(models.User.email == user_request.email).first()
    if not user:
        return JSONResponse(status_code=400, content={"error": "Invalid credentials"})
    
    hashed_password = hashlib.sha256(user_request.password.encode()).hexdigest()
    if hashed_password != user.hashed_password:
        return JSONResponse(status_code=400, content={"error": "Invalid credentials"})
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/user")
def create_user(user_request: schemas.CreateUserRequest):

    db = SessionLocal()
    user = db.query(models.User).filter(models.User.email == user_request.email).first()
    if user:
        return JSONResponse(status_code=400, content={"error": "User already exists"})
    
    if user_request.password != user_request.password_confirm:
        return JSONResponse(status_code=400, content={"error": "Passwords do not match"})
    
    hashed_password = hashlib.sha256(user_request.password.encode()).hexdigest()
    
    if not user_request.email:
        return JSONResponse(status_code=400, content={"error": "Email is required"})
    
    db = SessionLocal()
    user = models.User(email=user_request.email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user    


@app.post("/signout")
def signout(token: str = Depends(oauth2_scheme)):

    db = SessionLocal()
    blacklist_token(db, token)
    db.close()

    return {"message": "You have been signed out"}


@app.get("/coins")
def get_coins(token: str = Depends(oauth2_scheme)):

    token_data=verify_token(token)

    db = SessionLocal()
    is_blacklist=check_blacklist(db, token)
    if is_blacklist:
        return JSONResponse(status_code=401, content={"error": "You have been signed out"})
    
    db.close()  
    
    currency_response = requests.get("https://api.coincap.io/v2/rates")
    if currency_response.status_code == 200:
        data = currency_response.json()
        assets = data.get("data", [])
        for asset in assets:
            if asset["symbol"] == "IDR":
                idr_rate = asset["rateUsd"]

    response = requests.get("https://api.coincap.io/v2/assets")
    if response.status_code == 200:
        data = response.json()
        assets = data.get("data", [])
        coins = []
        for asset in assets:
            price  = float(asset["priceUsd"]) / float(idr_rate)
            coin = schemas.CoinsListResponse(id=asset["id"], symbol=asset["symbol"], price=price)
            coins.append(coin)
        return {"coins": coins}
    else:
        return {"error": "Failed to fetch coins", "status_code": response.status_code},token_data.email
    
@app.post("/addcoin")
def add_coin(coin_request: schemas.CoinRequest, token: str = Depends(oauth2_scheme)):
    token_data=verify_token(token)

    db = SessionLocal()
    is_blacklist=check_blacklist(db, token)
    if is_blacklist:
        return JSONResponse(status_code=401, content={"error": "You have been signed out"})



    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if not user:
        return JSONResponse(status_code=400, content={"error": "User does not exist"})
    
    coin = db.query(models.Coin).filter(models.Coin.symbol == coin_request.symbol).first()
    if coin:
        return JSONResponse(status_code=400, content={"error": "Coin already exists"})
    
    coin = models.Coin(id=coin_request.id, symbol=coin_request.symbol, price=coin_request.price, owner_id=user.id)
    db.add(coin)
    db.commit()
    db.refresh(coin)
    return {"message": "Coin added successfully"}

@app.get("/coins/owned/")
def get_user_coins(token: str = Depends(oauth2_scheme)):
    token_data=verify_token(token)

    db = SessionLocal()
    is_blacklist=check_blacklist(db, token)
    if is_blacklist:
        return JSONResponse(status_code=401, content={"error": "You have been signed out"})

    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if not user:
        return JSONResponse(status_code=400, content={"error": "User does not exist"})
    
    data = db.query(models.Coin).filter(models.Coin.owner_id == user.id).all()
    
    coins = []
    for asset in data:
        coin = schemas.UserCoinResponse(id=asset.id, symbol=asset.symbol, price=asset.price)
        coins.append(coin)
        
    if not coins:
        return JSONResponse(status_code=400, content={"error": "No coins found"})
    return {"coins": coins}

@app.post("/deletecoin/")
def delete_user_coin(delete_request = schemas.DeleteCoinRequest, token: str = Depends(oauth2_scheme)):
    token_data=verify_token(token)

    db = SessionLocal()
    is_blacklist=check_blacklist(db, token)
    if is_blacklist:
        return JSONResponse(status_code=401, content={"error": "You have been signed out"})

    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if not user:
        return JSONResponse(status_code=400, content={"error": "User does not exist"})
    
    coin = db.query(models.Coin).filter(models.Coin.owner_id == user.id and models.Coin.id == delete_request.coin_id).first()
    if not coin:
        return JSONResponse(status_code=400, content={"error": "Coin does not exist"})
    
    db.delete(coin)
    db.commit()
    return {"message": "Coin deleted successfully"}
