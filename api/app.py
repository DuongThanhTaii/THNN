"""FastAPI application factory and configuration."""

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from config.logging_config import configure_logging
from config.settings import get_settings
from providers.exceptions import ProviderError
from storage.migrations.runner import run_migrations

from .dependencies import cleanup_provider
from .observability import metrics_registry
from .rate_limit import enforce_rate_limits
from .rbac import enforce_rbac
from .routes import router
from .v1.router import root_webhook_router, v1_router

# Opt-in to future behavior for python-telegram-bot
os.environ["PTB_TIMEDELTA"] = "1"

# Configure logging first (before any module logs)
_settings = get_settings()
configure_logging(_settings.log_file)


_SHUTDOWN_TIMEOUT_S = 5.0


async def _best_effort(
    name: str, awaitable, timeout_s: float = _SHUTDOWN_TIMEOUT_S
) -> None:
    """Run a shutdown step with timeout; never raise to callers."""
    try:
        await asyncio.wait_for(awaitable, timeout=timeout_s)
    except TimeoutError:
        logger.warning(f"Shutdown step timed out: {name} ({timeout_s}s)")
    except Exception as e:
        logger.warning(f"Shutdown step failed: {name}: {type(e).__name__}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    logger.info("Starting Claude Code Proxy...")
    database_url = getattr(settings, "database_url", "").strip()

    if database_url:
        try:
            applied_count = run_migrations()
            logger.info(f"Database migrations ready (applied={applied_count})")
        except Exception as e:
            logger.error(f"Failed to apply DB migrations: {e}")
            raise

    # Initialize messaging platform if configured
    messaging_platforms = []
    message_handlers = []
    cli_manager = None
    automation_scheduler = None

    try:
        # Use the messaging factory to create one or more configured platforms.
        from messaging.platforms.factory import create_messaging_platforms

        messaging_platforms = create_messaging_platforms(
            platform_types=settings.messaging_platform,
            bot_token=settings.telegram_bot_token,
            allowed_user_id=settings.allowed_telegram_user_id,
            discord_bot_token=settings.discord_bot_token,
            allowed_discord_channels=settings.allowed_discord_channels,
            web_workspace_id=1,
            enable_esp32=getattr(settings, "enable_esp32", False),
            esp32_mqtt_broker_url=getattr(settings, "esp32_mqtt_broker_url", None),
            esp32_mqtt_username=getattr(settings, "esp32_mqtt_username", None),
            esp32_mqtt_password=getattr(settings, "esp32_mqtt_password", None),
            esp32_mqtt_topic_prefix=getattr(
                settings, "esp32_mqtt_topic_prefix", "agent"
            ),
            esp32_device_shared_secret=getattr(
                settings, "esp32_device_shared_secret", None
            ),
        )

        if messaging_platforms:
            from cli.manager import CLISessionManager
            from messaging.handler import ClaudeMessageHandler
            from messaging.session import SessionStore

            # Setup workspace - CLI runs in allowed_dir if set (e.g. project root)
            workspace = (
                os.path.abspath(settings.allowed_dir)
                if settings.allowed_dir
                else os.getcwd()
            )
            os.makedirs(workspace, exist_ok=True)

            # Session data stored in agent_workspace
            data_path = os.path.abspath(settings.claude_workspace)
            os.makedirs(data_path, exist_ok=True)

            api_url = f"http://{settings.host}:{settings.port}/v1"
            allowed_dirs = [workspace] if settings.allowed_dir else []
            plans_dir_abs = os.path.abspath(
                os.path.join(settings.claude_workspace, "plans")
            )
            plans_directory = os.path.relpath(plans_dir_abs, workspace)
            cli_manager = CLISessionManager(
                workspace_path=workspace,
                api_url=api_url,
                allowed_dirs=allowed_dirs,
                plans_directory=plans_directory,
            )

            # Initialize session store
            if database_url:
                from messaging.postgres_session import PostgresSessionStore

                session_store = PostgresSessionStore(database_url)
                logger.info("Using PostgreSQL session store")
            else:
                session_store = SessionStore(
                    storage_path=os.path.join(data_path, "sessions.json")
                )
                logger.info("Using file-based session store")

            # Restore tree state once and reuse for each platform handler.
            saved_trees = session_store.get_all_trees()
            saved_node_map = session_store.get_node_mapping()

            for messaging_platform in messaging_platforms:
                message_handler = ClaudeMessageHandler(
                    platform=messaging_platform,
                    cli_manager=cli_manager,
                    session_store=session_store,
                )

                if saved_trees:
                    logger.info(
                        f"Restoring {len(saved_trees)} conversation trees for {messaging_platform.name}..."
                    )
                    from messaging.trees.queue_manager import TreeQueueManager

                    message_handler.replace_tree_queue(
                        TreeQueueManager.from_dict(
                            {
                                "trees": saved_trees,
                                "node_to_tree": saved_node_map,
                            },
                            queue_update_callback=message_handler.update_queue_positions,
                            node_started_callback=message_handler.mark_node_processing,
                        )
                    )
                    # Reconcile restored state - anything PENDING/IN_PROGRESS is lost across restart
                    if message_handler.tree_queue.cleanup_stale_nodes() > 0:
                        tree_data = message_handler.tree_queue.to_dict()
                        session_store.sync_from_tree_data(
                            tree_data["trees"], tree_data["node_to_tree"]
                        )

                messaging_platform.on_message(message_handler.handle_message)
                await messaging_platform.start()
                message_handlers.append(message_handler)
                logger.info(
                    f"{messaging_platform.name} platform started with message handler"
                )

    except ImportError as e:
        logger.warning(f"Messaging module import error: {e}")
    except Exception as e:
        logger.error(f"Failed to start messaging platform: {e}")
        import traceback

        logger.error(traceback.format_exc())

    # Store in app state for access in routes
    app.state.messaging_platforms = messaging_platforms
    app.state.message_handlers = message_handlers
    # Backward-compatible aliases used in existing routes/tests.
    app.state.messaging_platform = (
        messaging_platforms[0] if messaging_platforms else None
    )
    app.state.message_handler = message_handlers[0] if message_handlers else None
    app.state.cli_manager = cli_manager

    if database_url and settings.automation_scheduler_enabled:
        try:
            from api.automation import AutomationScheduler

            automation_scheduler = AutomationScheduler(
                poll_seconds=settings.automation_scheduler_poll_seconds,
                max_batch=settings.automation_scheduler_max_batch,
                worker_queue_size=settings.automation_worker_queue_size,
                worker_concurrency=settings.automation_worker_concurrency,
            )
            await automation_scheduler.start()
        except Exception as e:
            logger.warning(f"Failed to start automation scheduler: {e}")

    app.state.automation_scheduler = automation_scheduler

    yield

    # Cleanup
    flushed_session_store_ids = set()
    for message_handler in message_handlers:
        if not hasattr(message_handler, "session_store"):
            continue
        session_store_obj = message_handler.session_store
        marker = id(session_store_obj)
        if marker in flushed_session_store_ids:
            continue
        flushed_session_store_ids.add(marker)
        try:
            session_store_obj.flush_pending_save()
        except Exception as e:
            logger.warning(f"Session store flush on shutdown: {e}")
    logger.info("Shutdown requested, cleaning up...")
    for messaging_platform in messaging_platforms:
        await _best_effort(
            f"{messaging_platform.name}.stop",
            messaging_platform.stop(),
        )
    if cli_manager:
        await _best_effort("cli_manager.stop_all", cli_manager.stop_all())
    if automation_scheduler is not None:
        await _best_effort("automation_scheduler.stop", automation_scheduler.stop())
    await _best_effort("cleanup_provider", cleanup_provider())

    # Ensure background limiter worker doesn't keep the loop alive.
    try:
        from messaging.limiter import MessagingRateLimiter

        await _best_effort(
            "MessagingRateLimiter.shutdown_instance",
            MessagingRateLimiter.shutdown_instance(),
            timeout_s=2.0,
        )
    except Exception:
        # Limiter may never have been imported/initialized.
        pass

    logger.info("Server shut down cleanly")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Claude Code Proxy",
        version="2.0.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def trace_context_middleware(request: Request, call_next):
        request_id = (request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:12]}").strip()
        correlation_id = (
            request.headers.get("x-correlation-id") or f"corr_{uuid.uuid4().hex[:12]}"
        ).strip()
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        status_code = 500
        with logger.contextualize(
            request_id=request_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        ):
            try:
                response = await call_next(request)
                status_code = response.status_code
            except Exception:
                await metrics_registry.observe(
                    path=request.url.path,
                    method=request.method,
                    status_code=status_code,
                    latency_seconds=time.perf_counter() - start,
                )
                raise

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        await metrics_registry.observe(
            path=request.url.path,
            method=request.method,
            status_code=status_code,
            latency_seconds=time.perf_counter() - start,
        )
        return response

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        return await enforce_rate_limits(request, call_next)

    @app.middleware("http")
    async def rbac_middleware(request: Request, call_next):
        return await enforce_rbac(request, call_next)

    # Register routes
    app.include_router(router)
    app.include_router(v1_router)
    app.include_router(root_webhook_router)

    # Exception handlers
    @app.exception_handler(ProviderError)
    async def provider_error_handler(request: Request, exc: ProviderError):
        """Handle provider-specific errors and return Anthropic format."""
        logger.error(f"Provider Error: {exc.error_type} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_anthropic_format(),
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        """Handle general errors and return Anthropic format."""
        logger.error(f"General Error: {exc!s}")
        import traceback

        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": "An unexpected error occurred.",
                },
            },
        )

    return app


# Default app instance for uvicorn
app = create_app()
