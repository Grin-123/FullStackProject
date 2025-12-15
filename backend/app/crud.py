"""
CRUD operations (Create, Read, Update, Delete) for database models.
This file is optional - you can do operations directly in main.py instead.
"""

from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime

from .models import User, Transaction, TransactionType
from .auth import get_password_hash


# ============================================
# User CRUD Operations
# ============================================

def create_user(session: Session, username: str, email: str, password: str) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    """Get user by username."""
    statement = select(User).where(User.username == username)
    return session.exec(statement).first()


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    """Get user by email."""
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


# ============================================
# Transaction CRUD Operations
# ============================================

def create_transaction(
    session: Session,
    user_id: int,
    type: TransactionType,
    category: str,
    amount: float,
    description: str,
    date
) -> Transaction:
    """Create a new transaction."""
    transaction = Transaction(
        user_id=user_id,
        type=type,
        category=category,
        amount=amount,
        description=description,
        date=date
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


def get_transactions_by_user(
    session: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False
) -> List[Transaction]:
    """Get all transactions for a user."""
    statement = select(Transaction).where(Transaction.user_id == user_id)
    
    if not include_archived:
        statement = statement.where(Transaction.archived == False)
    
    statement = statement.order_by(Transaction.date.desc()).offset(skip).limit(limit)
    return session.exec(statement).all()


def get_transaction_by_id(
    session: Session,
    transaction_id: int,
    user_id: int
) -> Optional[Transaction]:
    """Get a specific transaction."""
    statement = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    )
    return session.exec(statement).first()


def update_transaction(
    session: Session,
    transaction: Transaction,
    **kwargs
) -> Transaction:
    """Update a transaction."""
    for key, value in kwargs.items():
        if value is not None:
            setattr(transaction, key, value)
    
    transaction.updated_at = datetime.utcnow()
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


def archive_transaction(session: Session, transaction: Transaction) -> Transaction:
    """Archive a transaction (soft delete)."""
    transaction.archived = True
    transaction.updated_at = datetime.utcnow()
    session.add(transaction)
    session.commit()
    return transaction


def delete_transaction(session: Session, transaction: Transaction) -> None:
    """Permanently delete a transaction."""
    session.delete(transaction)
    session.commit()