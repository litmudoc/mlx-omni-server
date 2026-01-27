import argparse
import os
from pathlib import Path
import shutil

import uvicorn
from fastapi import FastAPI

from .middleware.logging import RequestResponseLoggingMiddleware
from .routers import api_router
from .utils.logger import logger, set_logger_level
# Import PresetManager for later use if needed
from .utils.mlx_preset import PresetManager

# Define lifespan handler function
async def app_lifespan(app: FastAPI):
    """Lifespan handler to run startup logic.

    - Ensure user config file exists.
    - Pre-load the PresetManager configuration as a sanity check.
    """
    # Startup events
    ensure_user_config()
    _ = PresetManager.get_default_preset()
    # Yield to signal that startup is complete and allow the app to run
    yield
    # Shutdown events can be added here if needed

# Create FastAPI app with lifespan handler
app = FastAPI(title="MLX Omni Server", lifespan=app_lifespan)

# Add request/response logging middleware with custom levels
app.add_middleware(
    RequestResponseLoggingMiddleware,
    # exclude_paths=["/health"]
)

from fastapi.middleware.cors import CORSMiddleware

app.include_router(api_router)


def ensure_user_config():
    """Ensure that the user config file exists at ``~/.mlx_preset/config.json``.

    If it does not exist, copy the default config from the package directory.
    """
    user_cfg_dir = Path.home() / ".mlx_preset"
    user_cfg_path = user_cfg_dir / "config.json"
    if not user_cfg_path.is_file():
        # Ensure directory exists
        user_cfg_dir.mkdir(parents=True, exist_ok=True)
        default_cfg_path = Path(__file__).parent / "mlx_preset" / "config.json"
        shutil.copy(default_cfg_path, user_cfg_path)
        logger.info(f"Copied default mlx preset config to {user_cfg_path}")
    else:
        logger.debug(f"User mlx preset config found at {user_cfg_path}")


def build_parser():
    """Create and configure the argument parser for the server."""
    parser = argparse.ArgumentParser(description="MLX Omni Server")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to, defaults to 0.0.0.0",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=10240,
        help="Port to bind the server to, defaults to 10240",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of workers to use, defaults to 1",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set the logging level, defaults to info",
    )
    parser.add_argument(
        "--cors-allow-origins",
        type=str,
        default="",
        help='Apply origins to CORSMiddleware. This is useful for accessing the local server directly from the browser (use --cors-allow-origins="*"). Defaults to disabled',
    )
    return parser


def configure_cors_middleware(cors_allow_origins: str | None):
    """Configure CORS middleware with the provided origins, if any."""
    # Remove existing CORS middleware
    app.user_middleware = [m for m in app.user_middleware if m.cls != CORSMiddleware]
    app.middleware_stack = None  # Reset middleware stack to force rebuild

    if cors_allow_origins is None:
        origins = []
    else:
        origins = (
            [origin.strip() for origin in cors_allow_origins.split(",")]
            if cors_allow_origins
            else []
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

configure_cors_middleware(os.environ.get("MLX_OMNI_CORS", None))


def start():
    """Start the MLX Omni Server."""
    parser = build_parser()
    args = parser.parse_args()

    # Set log level through environment variable
    os.environ["MLX_OMNI_LOG_LEVEL"] = args.log_level
    # Set CORS through environment variable
    os.environ["MLX_OMNI_CORS"] = args.cors_allow_origins

    set_logger_level(logger, args.log_level)
    configure_cors_middleware(args.cors_allow_origins)

    # Ensure user preset config exists before server starts (retained for direct script execution)
    ensure_user_config()

    uvicorn.run(
        "mlx_omni_server.main:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        use_colors=True,
        workers=args.workers,
        timeout_keep_alive=1800,
    )

if __name__ == "__main__":
    start()
