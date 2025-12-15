"""
Pydantic schemas for API request/response validation.
Separate from models to control what data is exposed via API.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime, date
from typing import Optional
from enum import Enum


class TransactionType(str, Enum):
    """Transaction type enum."""
    INCOME = "income"
    EXPENSE = "expense"


# ============================================
# User Schemas
# ============================================

class UserCreate(BaseModel):
    """Schema for user registration."""
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    
    @validator('username')
    def username_alphanumeric(cls, v):
        """Validate username is alphanumeric."""
        if not v.replace('_', '').isalnum():
            raise ValueError('Username must be alphanumeric (underscore allowed)')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response (no password)."""
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True  # Allow ORM models


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload."""
    username: Optional[str] = None


# ============================================
# Transaction Schemas
# ============================================

class TransactionBase(BaseModel):
    """Base transaction schema."""
    type: TransactionType
    category: str = Field(min_length=1, max_length=50)
    amount: float = Field(gt=0, description="Amount must be greater than 0")
    description: str = Field(min_length=1, max_length=500)
    date: date


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction."""
    pass


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction (all fields optional)."""
    type: Optional[TransactionType] = None
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    date: Optional[date] = None


class TransactionResponse(TransactionBase):
    """Schema for transaction response."""
    id: int
    user_id: int
    archived: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TransactionStats(BaseModel):
    """Schema for transaction statistics."""
    total_income: float
    total_expense: float
    balance: float
    transaction_count: int