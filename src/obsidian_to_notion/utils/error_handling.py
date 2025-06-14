"""Error handling utilities."""

import json
import logging
import sys
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Base exception for migration errors."""

    pass


class ConfigError(MigrationError):
    """Configuration-related errors."""

    pass


class ParseError(MigrationError):
    """Parsing-related errors."""

    pass


class NotionAPIError(MigrationError):
    """Notion API-related errors."""

    pass


class FileNotFoundError(MigrationError):
    """File not found errors."""

    pass


def log_error_with_context(
    logger_instance: logging.Logger,
    error: Exception,
    context: Dict[str, Any],
    include_traceback: bool = True,
) -> None:
    """Log error with comprehensive context information.

    Args:
        logger_instance: Logger instance to use
        error: The exception that occurred
        context: Dictionary containing context information
        include_traceback: Whether to include full traceback
    """
    # Build comprehensive error details
    error_details = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "error_module": error.__class__.__module__,
    }

    # Add file-specific context if available
    if "file_path" in context:
        file_path = Path(context["file_path"])
        if file_path.exists():
            try:
                stat = file_path.stat()
                context["file_metadata"] = {
                    "size_bytes": stat.st_size,
                    "modified_timestamp": stat.st_mtime,
                    "is_symlink": file_path.is_symlink(),
                    "absolute_path": str(file_path.absolute()),
                }
            except Exception:
                pass  # Don't fail logging due to metadata collection # nosec B110

    # Merge error details with context
    full_context = {**error_details, **context}

    # Format the log message
    message_parts = [f"{error.__class__.__name__}: {error}"]

    # Add phase information prominently
    if "phase" in context:
        message_parts.append(f"Phase: {context['phase']}")

    # Add file path prominently
    if "file_path" in context:
        message_parts.append(f"File: {context['file_path']}")

    # Add line number if available
    if "line_number" in context:
        message_parts.append(f"Line: {context['line_number']}")

    # Format context as indented JSON for readability
    context_json = json.dumps(full_context, indent=2, default=str)
    message_parts.append(f"Context:\n{context_json}")

    # Build the full message
    full_message = "\n".join(message_parts)

    # Log with appropriate method
    if include_traceback and sys.exc_info()[0] is not None:
        logger_instance.error(full_message, exc_info=True, extra=context)
    else:
        logger_instance.error(full_message, extra=context)


def create_error_context(
    file_path: Optional[Union[str, Path]] = None,
    phase: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create a standardized error context dictionary.

    Args:
        file_path: Path to the file being processed
        phase: Current processing phase
        **kwargs: Additional context fields

    Returns:
        Dictionary containing error context
    """
    context = {}

    if file_path:
        context["file_path"] = str(file_path)

    if phase:
        context["phase"] = phase

    # Add any additional context
    context.update(kwargs)

    return context


def setup_error_handling() -> None:
    """Set up global error handling."""

    def handle_exception(
        exc_type: Type[BaseException],
        exc_value: BaseException,
        exc_traceback: Optional[TracebackType],
    ) -> None:
        """Handle uncaught exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow keyboard interrupt to work normally
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Create context for uncaught exceptions
        context = create_error_context(
            phase="uncaught_exception",
            exception_type=exc_type.__name__,
            exception_module=exc_type.__module__,
        )

        # Log with full context
        # Cast to Exception for type compatibility
        if isinstance(exc_value, Exception):
            log_error_with_context(
                logger,
                exc_value,
                context,
                include_traceback=True,
            )
        else:
            # For non-Exception BaseExceptions, log directly
            logger.error(
                f"Uncaught {exc_type.__name__}: {exc_value}",
                exc_info=(exc_type, exc_value, exc_traceback),
                extra=context,
            )

    sys.excepthook = handle_exception


F = TypeVar("F", bound=Callable[..., Any])


def safe_file_operation(func: F) -> F:
    """Decorator for safe file operations.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            # Extract file path from args if possible
            file_path = None
            if args and isinstance(args[0], (str, Path)):
                file_path = args[0]

            context = create_error_context(
                file_path=file_path,
                phase="file_operation",
                operation=func.__name__,
                error_type="FileNotFoundError",
            )

            log_error_with_context(logger, e, context)
            raise FileNotFoundError(str(e)) from e
        except PermissionError as e:
            # Extract file path from args if possible
            file_path = None
            if args and isinstance(args[0], (str, Path)):
                file_path = args[0]

            context = create_error_context(
                file_path=file_path,
                phase="file_operation",
                operation=func.__name__,
                error_type="PermissionError",
            )

            log_error_with_context(logger, e, context)
            raise MigrationError(f"Permission denied: {e}") from e
        except Exception as e:
            # Extract file path from args if possible
            file_path = None
            if args and isinstance(args[0], (str, Path)):
                file_path = args[0]

            context = create_error_context(
                file_path=file_path,
                phase="file_operation",
                operation=func.__name__,
                error_type=type(e).__name__,
            )

            log_error_with_context(logger, e, context)
            raise MigrationError(f"File operation failed: {e}") from e

    return wrapper  # type: ignore[return-value]


def retry_on_api_error(max_retries: int = 3) -> Callable[[F], F]:
    """Decorator to retry on API errors.

    Args:
        max_retries: Maximum number of retries

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except NotionAPIError as e:
                    last_error = e

                    # Create context for API error
                    context = create_error_context(
                        phase="api_call",
                        operation=func.__name__,
                        retry_attempt=attempt + 1,
                        max_retries=max_retries,
                        error_type="NotionAPIError",
                    )

                    # Extract additional context from error if available
                    if hasattr(e, "status_code"):
                        context["api_status_code"] = e.status_code
                    if hasattr(e, "response"):
                        context["api_response"] = str(e.response)

                    if attempt < max_retries - 1:
                        # Log as warning for retryable attempts
                        logger.warning(
                            f"API error (attempt {attempt + 1}/{max_retries}): {e}",
                            extra=context,
                        )
                        continue
                    else:
                        # Log as error on final attempt
                        log_error_with_context(logger, e, context)
                        raise

            if last_error:
                raise last_error

        return wrapper  # type: ignore[return-value]

    return decorator
