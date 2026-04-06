"""
payment_service.py — Core banking operations: deposit, withdraw, transfer.

The transfer function demonstrates ACID atomicity:
  - Either BOTH the debit and credit happen, or NEITHER does.
  - If simulate_failure=True, the transaction crashes midway on purpose
    so you can see SQLAlchemy roll back the debit automatically.
"""

import uuid
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.account import BankAccount
from models.transaction import Transaction
from models.user import User
from models.enums import TransactionType, TransactionStatus
from schemas.transaction import DepositRequest, WithdrawRequest, TransferRequest
from services.fraud_detection import run_fraud_check
from utils.logger import logger


def generate_reference_id() -> str:
    """Generate a unique reference ID like TXN-A1B2C3D4 for each transaction."""
    return f"TXN-{uuid.uuid4().hex[:8].upper()}"


class PaymentService:

    def deposit(self, db: Session, user: User, data: DepositRequest) -> Transaction:
        """
        Add money to an account.

        Steps:
        1. Find the account and verify it belongs to the user
        2. Add the deposit amount to the balance
        3. Record the transaction
        """
        account = db.query(BankAccount).filter(
            BankAccount.account_number == data.account_number
        ).first()

        if account is None:
            raise HTTPException(status_code=404, detail="Account not found.")
        if account.user_id != user.id:
            raise HTTPException(status_code=403, detail="You can only deposit into your own accounts.")
        if not account.is_active:
            raise HTTPException(status_code=400, detail="This account is inactive.")

        account.balance += data.amount

        transaction = Transaction(
            reference_id=generate_reference_id(),
            to_account_id=account.id,
            transaction_type=TransactionType.deposit,
            amount=data.amount,
            status=TransactionStatus.success,
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        logger.info(f"Deposit ₹{data.amount} → {data.account_number} | Ref: {transaction.reference_id}")
        return transaction

    def withdraw(self, db: Session, user: User, data: WithdrawRequest) -> Transaction:
        """
        Take money out of an account.

        Steps:
        1. Find the account and verify ownership
        2. Check balance won't fall below the minimum after withdrawal
        3. Deduct the amount and record the transaction
        """
        account = db.query(BankAccount).filter(
            BankAccount.account_number == data.account_number
        ).first()

        if account is None:
            raise HTTPException(status_code=404, detail="Account not found.")
        if account.user_id != user.id:
            raise HTTPException(status_code=403, detail="You can only withdraw from your own accounts.")
        if not account.is_active:
            raise HTTPException(status_code=400, detail="This account is inactive.")

        balance_after = account.balance - data.amount
        if balance_after < account.minimum_balance:
            available = account.balance - account.minimum_balance
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. You can withdraw at most ₹{available} (minimum balance: ₹{account.minimum_balance}).",
            )

        account.balance -= data.amount

        transaction = Transaction(
            reference_id=generate_reference_id(),
            from_account_id=account.id,
            transaction_type=TransactionType.withdraw,
            amount=data.amount,
            status=TransactionStatus.success,
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        logger.info(f"Withdrawal ₹{data.amount} ← {data.account_number} | Ref: {transaction.reference_id}")
        return transaction

    def transfer(self, db: Session, user: User, data: TransferRequest) -> Transaction:
        """
        Move money from one account to another atomically.

        ACID guarantee: if anything fails mid-transfer, SQLAlchemy rolls back
        BOTH the debit and the credit. The sender's money is never lost.

        Steps:
        1. Find sender and receiver accounts
        2. Verify sender owns the account and has enough balance
        3. Run fraud detection (sliding window check)
        4. Debit the sender
        5. [If simulate_failure=True → crash here → rollback undoes Step 4]
        6. Credit the receiver
        7. Commit everything together
        """
        # Step 1: Find both accounts
        from_account = db.query(BankAccount).filter(
            BankAccount.account_number == data.from_account_number
        ).first()
        to_account = db.query(BankAccount).filter(
            BankAccount.account_number == data.to_account_number
        ).first()

        if from_account is None:
            raise HTTPException(status_code=404, detail=f"Sender account '{data.from_account_number}' not found.")
        if to_account is None:
            raise HTTPException(status_code=404, detail=f"Receiver account '{data.to_account_number}' not found.")
        if from_account.id == to_account.id:
            raise HTTPException(status_code=400, detail="Cannot transfer to the same account.")

        # Step 2: Check ownership and balance
        if from_account.user_id != user.id:
            raise HTTPException(status_code=403, detail="You can only transfer from your own accounts.")

        available_to_transfer = from_account.balance - from_account.minimum_balance
        if data.amount > available_to_transfer:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. You can transfer at most ₹{available_to_transfer}.",
            )

        # Step 3: Fraud detection
        is_flagged, flagged_reason = run_fraud_check(db, from_account, data.amount)
        if is_flagged:
            logger.warning(f"Fraud flagged on {data.from_account_number}: {flagged_reason}")

        # Store IDs in plain variables NOW, before the try block.
        # After db.rollback(), SQLAlchemy expires all ORM objects — accessing
        # from_account.id inside the except block would trigger a lazy load
        # which can crash the except block itself, causing the whole request
        # to die without sending a response ("Failed to fetch" in the browser).
        from_account_id = from_account.id
        to_account_id   = to_account.id
        reference_id    = generate_reference_id()

        try:
            # Step 4: Debit the sender
            from_account.balance -= data.amount

            # Step 5: Intentional failure for ACID rollback demo
            if data.simulate_failure:
                raise RuntimeError("Simulated transaction failure — showing ACID rollback.")

            # Step 6: Credit the receiver
            to_account.balance += data.amount

            # Step 7: Record and commit
            transaction = Transaction(
                reference_id=reference_id,
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                transaction_type=TransactionType.transfer,
                amount=data.amount,
                status=TransactionStatus.success,
                is_flagged=is_flagged,
                flagged_reason=flagged_reason,
            )
            db.add(transaction)
            db.commit()
            db.refresh(transaction)

            logger.info(f"Transfer ₹{data.amount} {data.from_account_number}→{data.to_account_number} | Ref: {reference_id}")
            return transaction

        except RuntimeError as error:
            # Rollback undoes the debit in Step 4 — sender's balance is fully restored.
            db.rollback()
            logger.warning(f"Transfer rolled back | Ref: {reference_id} | Reason: {error}")

            # Open a FRESH session to save the failed record.
            # We cannot reuse `db` after db.rollback() — SQLite/SQLAlchemy marks the
            # session as dirty and a subsequent commit on it is unreliable.
            from database import SessionLocal
            fresh_db = SessionLocal()
            try:
                failed_tx = Transaction(
                    reference_id=reference_id,
                    from_account_id=from_account_id,
                    to_account_id=to_account_id,
                    transaction_type=TransactionType.transfer,
                    amount=data.amount,
                    status=TransactionStatus.failed,
                    failure_reason=str(error),
                )
                fresh_db.add(failed_tx)
                fresh_db.commit()
                fresh_db.refresh(failed_tx)
                return failed_tx
            except Exception as save_error:
                fresh_db.rollback()
                logger.error(f"Could not save failed transaction record: {save_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Transfer failed and rolled back. Reason: {str(error)}",
                )
            finally:
                fresh_db.close()

    def get_history(self, db: Session, account_number: str, user: User) -> list[Transaction]:
        """Return all transactions for an account (sent and received), newest first."""
        account = db.query(BankAccount).filter(
            BankAccount.account_number == account_number
        ).first()

        if account is None:
            raise HTTPException(status_code=404, detail="Account not found.")
        if account.user_id != user.id:
            raise HTTPException(status_code=403, detail="You can only view your own transaction history.")

        return (
            db.query(Transaction)
            .filter(
                (Transaction.from_account_id == account.id) |
                (Transaction.to_account_id == account.id)
            )
            .order_by(Transaction.created_at.desc())
            .all()
        )
