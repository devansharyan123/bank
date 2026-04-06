import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    customer = "customer"


class AccountType(str, enum.Enum):
    savings = "savings"
    current = "current"


class TransactionType(str, enum.Enum):
    deposit = "deposit"
    withdraw = "withdraw"
    transfer = "transfer"


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class LoanStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    active = "active"   # approved and EMI payments have started
    closed = "closed"   # fully repaid
