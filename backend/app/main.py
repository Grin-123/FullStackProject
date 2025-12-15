from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import List
from datetime import timedelta

from .database import engine, get_session
from .models import User, Transaction, TransactionType
from .auth import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="Personal Finance Tracker API")

# Create tables
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

# Authentication Endpoints
@app.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    statement = select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    username: str,
    email: str,
    password: str,
    session: Session = Depends(get_session)
):
    # Check if user exists
    statement = select(User).where(
        (User.username == username) | (User.email == email)
    )
    existing_user = session.exec(statement).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    hashed_password = get_password_hash(password)
    user = User(username=username, email=email, hashed_password=hashed_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"message": "User created successfully", "user_id": user.id}

# Transaction CRUD Endpoints
@app.post("/transactions", status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction: Transaction,
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Get user
    statement = select(User).where(User.username == current_user)
    user = session.exec(statement).first()
    
    transaction.user_id = user.id
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction

@app.get("/transactions", response_model=List[Transaction])
async def read_transactions(
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(User).where(User.username == current_user)
    user = session.exec(statement).first()
    
    statement = select(Transaction).where(Transaction.user_id == user.id)
    
    if not include_archived:
        statement = statement.where(Transaction.archived == False)
    
    statement = statement.offset(skip).limit(limit)
    transactions = session.exec(statement).all()
    return transactions

@app.get("/transactions/{transaction_id}")
async def read_transaction(
    transaction_id: int,
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(User).where(User.username == current_user)
    user = session.exec(statement).first()
    
    statement = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user.id
    )
    transaction = session.exec(statement).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return transaction

@app.put("/transactions/{transaction_id}")
async def update_transaction(
    transaction_id: int,
    transaction_update: Transaction,
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(User).where(User.username == current_user)
    user = session.exec(statement).first()
    
    statement = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user.id
    )
    transaction = session.exec(statement).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    transaction.type = transaction_update.type
    transaction.category = transaction_update.category
    transaction.amount = transaction_update.amount
    transaction.description = transaction_update.description
    transaction.date = transaction_update.date
    transaction.updated_at = datetime.utcnow()
    
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction

@app.patch("/transactions/{transaction_id}/archive")
async def archive_transaction(
    transaction_id: int,
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(User).where(User.username == current_user)
    user = session.exec(statement).first()
    
    statement = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user.id
    )
    transaction = session.exec(statement).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    transaction.archived = True
    transaction.updated_at = datetime.utcnow()
    
    session.add(transaction)
    session.commit()
    return {"message": "Transaction archived successfully"}

@app.delete("/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(User).where(User.username == current_user)
    user = session.exec(statement).first()
    
    statement = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user.id
    )
    transaction = session.exec(statement).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    session.delete(transaction)
    session.commit()
    return {"message": "Transaction deleted successfully"}

# Statistics Endpoint
@app.get("/transactions/stats/summary")
async def get_transaction_summary(
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(User).where(User.username == current_user)
    user = session.exec(statement).first()
    
    statement = select(Transaction).where(
        Transaction.user_id == user.id,
        Transaction.archived == False
    )
    transactions = session.exec(statement).all()
    
    total_income = sum(t.amount for t in transactions if t.type == TransactionType.income)
    total_expense = sum(t.amount for t in transactions if t.type == TransactionType.expense)
    balance = total_income - total_expense
    
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance,
        "transaction_count": len(transactions)
    }