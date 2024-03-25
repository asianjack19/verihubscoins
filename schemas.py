from pydantic import BaseModel

class CreateUserRequest(BaseModel):
    email: str
    password: str
    password_confirm: str

class LoginRequest(BaseModel):
    email: str
    password: str

# ================================
class CoinsListResponse(BaseModel):
    id : str
    symbol : str
    price : float

class CoinRequest(BaseModel):
    id : str
    symbol : str
    price : float
    
class UserCoinResponse(BaseModel):
    id : str
    symbol : str
    price : float

class DeleteCoinRequest(BaseModel):
    coin_id: str
# ================================
class TokenData(BaseModel):
    email: str