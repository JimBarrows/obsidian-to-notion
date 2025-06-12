"""Error handling utilities."""

import sys
import logging
import traceback
from typing import Optional, Type
from types import TracebackType


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


def setup_error_handling():
    """Set up global error handling."""
    def handle_exception(exc_type: Type[BaseException], 
                        exc_value: BaseException, 
                        exc_traceback: Optional[TracebackType]):
        """Handle uncaught exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow keyboard interrupt to work normally
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception


def safe_file_operation(func):
    """Decorator for safe file operations.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            raise FileNotFoundError(str(e))
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            raise MigrationError(f"Permission denied: {e}")
        except Exception as e:
            logger.error(f"File operation failed: {e}")
            raise MigrationError(f"File operation failed: {e}")
    
    return wrapper


def retry_on_api_error(max_retries: int = 3):
    """Decorator to retry on API errors.
    
    Args:
        max_retries: Maximum number of retries
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except NotionAPIError as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        logger.warning(f"API error (attempt {attempt + 1}/{max_retries}): {e}")
                        continue
                    else:
                        logger.error(f"API error after {max_retries} attempts: {e}")
                        raise
            
            if last_error:
                raise last_error
        
        return wrapper
    
    return decorator