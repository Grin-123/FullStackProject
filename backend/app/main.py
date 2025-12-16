"""
FastAPI application entry point.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import timedelta, datetime
from typing import List

from .config import settings
from .database import create_db_and_tables, get_session
from .models import User, Transaction, TransactionType
from .schemas import (
    UserCreate,
    UserResponse,
    Token,
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionStats
)
from .auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_active_user
)


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Personal Finance Tracker API - Track income and expenses"
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create database tables on startup
@app.on_event("startup")
def on_startup():
    """Create database tables on application startup."""
    create_db_and_tables()
    print("✅ Database tables created")


# Root endpoint
@app.get("/", tags=["Root"])
def read_root():
    """Root endpoint - API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


# Health check endpoint
@app.get("/health", tags=["Root"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# ============================================
# Authentication Endpoints
# ============================================

@app.post("/api/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def register(
    user_data: UserCreate,
    session: Session = Depends(get_session)
):
    """Register a new user."""
    # Check if username exists
    statement = select(User).where(User.username == user_data.username)
    if session.exec(statement).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    statement = select(User).where(User.email == user_data.email)
    if session.exec(statement).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    return new_user


@app.post("/api/token", response_model=Token, tags=["Authentication"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """Login and get access token."""
    user = authenticate_user(session, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/users/me", response_model=UserResponse, tags=["Users"])
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user


# ============================================
# Transaction Endpoints
# ============================================

@app.post("/api/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED, tags=["Transactions"])
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Create a new transaction. Requires authentication."""
    new_transaction = Transaction(
        user_id=current_user.id,
        type=transaction_data.type,
        category=transaction_data.category,
        amount=transaction_data.amount,
        description=transaction_data.description,
        date=transaction_data.date
    )
    
    session.add(new_transaction)
    session.commit()
    session.refresh(new_transaction)
    
    return new_transaction


@app.get("/api/transactions", response_model=List[TransactionResponse], tags=["Transactions"])
async def read_transactions(
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
    type: str = None,
    category: str = None,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Get all transactions for current user."""
    statement = select(Transaction).where(Transaction.user_id == current_user.id)
    
    if not include_archived:
        statement = statement.where(Transaction.archived == False)
    
    if type:
        statement = statement.where(Transaction.type == type)
    
    if category:
        statement = statement.where(Transaction.category == category)
    
    statement = statement.order_by(Transaction.date.desc()).offset(skip).limit(limit)
    transactions = session.exec(statement).all()
    return transactions


@app.get("/api/transactions/{transaction_id}", response_model=TransactionResponse, tags=["Transactions"])
async def read_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Get a specific transaction by ID."""
    statement = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    )
    transaction = session.exec(statement).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return transaction


@app.put("/api/transactions/{transaction_id}", response_model=TransactionResponse, tags=["Transactions"])
async def update_transaction(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Update a transaction. Requires authentication."""
    statement = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    )
    transaction = session.exec(statement).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Update only provided fields
    if transaction_data.type is not None:
        transaction.type = transaction_data.type
    if transaction_data.category is not None:
        transaction.category = transaction_data.category
    if transaction_data.amount is not None:
        transaction.amount = transaction_data.amount
    if transaction_data.description is not None:
        transaction.description = transaction_data.description
    if transaction_data.date is not None:
        transaction.date = transaction_data.date
    
    transaction.updated_at = datetime.utcnow()
    
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    
    return transaction


@app.patch("/api/transactions/{transaction_id}/archive", tags=["Transactions"])
async def archive_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Archive a transaction (soft delete). Requires authentication."""
    statement = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    )
    transaction = session.exec(statement).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    transaction.archived = True
    transaction.updated_at = datetime.utcnow()
    
    session.add(transaction)
    session.commit()
    
    return {"message": "Transaction archived successfully"}


@app.delete("/api/transactions/{transaction_id}", tags=["Transactions"])
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Permanently delete a transaction. Requires authentication."""
    statement = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    )
    transaction = session.exec(statement).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    session.delete(transaction)
    session.commit()
    
    return {"message": "Transaction deleted successfully"}


@app.get("/api/transactions/stats/summary", response_model=TransactionStats, tags=["Statistics"])
async def get_transaction_stats(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Get transaction statistics summary."""
    statement = select(Transaction).where(
        Transaction.user_id == current_user.id,
        Transaction.archived == False
    )
    transactions = session.exec(statement).all()
    
    total_income = sum(t.amount for t in transactions if t.type == TransactionType.INCOME)
    total_expense = sum(t.amount for t in transactions if t.type == TransactionType.EXPENSE)
    balance = total_income - total_expense
    
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance,
        "transaction_count": len(transactions)
    }