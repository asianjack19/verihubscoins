from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Numeric
from sqlalchemy.orm import relationship


from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    coins = relationship("Coin", back_populates="users")


class Coin(Base):
    __tablename__ = "coins"

    id = Column(String, primary_key=True)
    symbol = Column(String, index=True)
    price = Column(Numeric(10, 2))
    owner_id = Column(Integer, ForeignKey("users.id"))

    users = relationship("User", back_populates="coins")

class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"
    token = Column(String, primary_key=True)
    is_active = Column(Boolean, default=True)