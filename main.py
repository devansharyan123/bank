from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine, get_settings

# Import all models so SQLAlchemy registers them before creating tables
import models.user        # noqa: F401
import models.account     # noqa: F401
import models.transaction # noqa: F401
import models.loan        # noqa: F401

from routes import auth, account, transaction, loan

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables when the server starts."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    description=(
        "A simple banking system for learning — "
        "covers JWT auth, KYC, accounts, atomic transactions, "
        "fraud detection (sliding window), and loans (EMI formula)."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
def health_check():
    """Quick check to confirm the server is running."""
    return {"status": "ok", "app": settings.app_name}


# Register all route groups
app.include_router(auth.router,        prefix="/auth")
app.include_router(account.router,     prefix="/accounts")
app.include_router(transaction.router, prefix="/transactions")
app.include_router(loan.router,        prefix="/loans")
