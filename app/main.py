import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api import config as config_router
from app.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log", mode="a")],
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for the FastAPI application."""
    # Startup
    logger.info("Starting up Config Store API")
    if not settings.github_token:
        logger.error("GitHub token not found in environment variables")
        raise RuntimeError("GitHub token not configured")
    logger.info("Configuration validated")

    yield

    # Shutdown
    logger.info("Shutting down Config Store API")


# Create FastAPI app
app = FastAPI(
    title="Config Store API",
    description="""
    A service for managing versioned configuration files stored in GitHub.

    ## Key Features
    - Store and retrieve configuration files in JSON, TOML, and XML formats
    - Automatic version control using Git
    - Project-based organization
    - Full history tracking with version recovery
    - Rate limiting and input validation
    - Access control via GitHub authentication

    ## Authentication
    All endpoints require authentication using a GitHub personal access token.
    The token should have repository access permissions.

    ## Supported File Formats
    - JSON (.json)
    - YAML (.yaml)
    - TOML (.toml)
    - XML (.xml)

    ## Rate Limiting
    API endpoints are rate-limited to prevent abuse.
    Please ensure to handle rate limit responses appropriately.

    ## Versioning
    - Each change creates a new version automatically
    - Version history is maintained in Git
    - Previous versions can be listed and recovered
    - Version numbers are sequential and start from 1
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Include routers
app.include_router(config_router.router, tags=["configs"])
