"""
Structured logging configuration and utilities
"""

import logging
import logging.handlers
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager
import streamlit as st

from config.app_config import get_config


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # Base log structure
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from record
        extra_fields = {
            key: value for key, value in record.__dict__.items()
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                'filename', 'module', 'lineno', 'funcName', 'created', 
                'msecs', 'relativeCreated', 'thread', 'threadName', 
                'processName', 'process', 'getMessage', 'exc_info', 
                'exc_text', 'stack_info'
            }
        }
        
        if extra_fields:
            log_data["extra"] = extra_fields
            
        return json.dumps(log_data, ensure_ascii=False, default=str)


class StreamlitLogHandler(logging.Handler):
    """
    Custom log handler that displays logs in Streamlit interface
    """
    
    def emit(self, record: logging.LogRecord):
        """Emit log record to Streamlit interface"""
        try:
            msg = self.format(record)
            
            # Display based on log level
            if record.levelno >= logging.ERROR:
                st.error(f"🚨 {record.getMessage()}")
            elif record.levelno >= logging.WARNING:
                st.warning(f"⚠️ {record.getMessage()}")
            elif record.levelno >= logging.INFO:
                st.info(f"ℹ️ {record.getMessage()}")
            else:
                st.text(f"🐛 {record.getMessage()}")
                
        except Exception:
            self.handleError(record)


def setup_logging() -> logging.Logger:
    """
    Set up structured logging for the application
    
    Returns:
        logging.Logger: Configured root logger
    """
    config = get_config()
    
    # Create logs directory if it doesn't exist
    if config.logging.enable_file_logging:
        log_file_path = Path(config.logging.log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.logging.level))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with structured formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.logging.level))
    
    if config.debug:
        # Human-readable format for development
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]'
        )
    else:
        # Structured JSON format for production
        console_formatter = StructuredFormatter()
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with structured formatting (if enabled)
    if config.logging.enable_file_logging:
        file_handler = logging.handlers.RotatingFileHandler(
            config.logging.log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)  # Always debug level for files
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
    
    # Streamlit handler for development
    if config.debug and config.environment == "development":
        try:
            streamlit_handler = StreamlitLogHandler()
            streamlit_handler.setLevel(logging.WARNING)  # Only warnings and errors
            streamlit_handler.setFormatter(logging.Formatter('%(message)s'))
            root_logger.addHandler(streamlit_handler)
        except Exception:
            # Ignore if Streamlit not available
            pass
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger: Configured logger
    """
    return logging.getLogger(name)


@contextmanager
def log_execution_time(logger: logging.Logger, operation: str, **extra_fields):
    """
    Context manager to log execution time of operations
    
    Args:
        logger: Logger instance
        operation: Description of the operation
        **extra_fields: Additional fields to include in log
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Starting {operation}", extra={
            "operation": operation,
            "start_time": start_time.isoformat(),
            **extra_fields
        })
        
        yield
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Completed {operation}", extra={
            "operation": operation,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "status": "success",
            **extra_fields
        })
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.error(f"Failed {operation}: {str(e)}", extra={
            "operation": operation,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            **extra_fields
        }, exc_info=True)
        
        raise


def log_user_interaction(logger: logging.Logger, interaction_type: str, **details):
    """
    Log user interactions for analytics
    
    Args:
        logger: Logger instance
        interaction_type: Type of interaction (e.g., "query", "button_click")
        **details: Additional interaction details
    """
    logger.info("User interaction", extra={
        "event_type": "user_interaction",
        "interaction_type": interaction_type,
        "timestamp": datetime.now().isoformat(),
        **details
    })


def log_model_usage(logger: logging.Logger, model: str, tokens_used: int, **details):
    """
    Log AI model usage for monitoring
    
    Args:
        logger: Logger instance
        model: Model name
        tokens_used: Number of tokens consumed
        **details: Additional usage details
    """
    logger.info("Model usage", extra={
        "event_type": "model_usage",
        "model": model,
        "tokens_used": tokens_used,
        "timestamp": datetime.now().isoformat(),
        **details
    })


def log_conversation_event(logger: logging.Logger, event_type: str, conversation_id: str, **details):
    """
    Log conversation-related events
    
    Args:
        logger: Logger instance
        event_type: Type of event (e.g., "created", "message_added", "cleared")
        conversation_id: Conversation identifier
        **details: Additional event details
    """
    logger.info("Conversation event", extra={
        "event_type": "conversation_event",
        "conversation_event_type": event_type,
        "conversation_id": conversation_id,
        "timestamp": datetime.now().isoformat(),
        **details
    })


class ErrorTracker:
    """
    Centralized error tracking and reporting
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.error_counts: Dict[str, int] = {}
    
    def track_error(self, error: Exception, context: str = "", **extra_info):
        """
        Track and log an error with context
        
        Args:
            error: Exception that occurred
            context: Context where error occurred
            **extra_info: Additional error information
        """
        error_type = type(error).__name__
        error_key = f"{error_type}:{context}"
        
        # Increment error count
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log structured error
        self.logger.error(f"Error in {context}: {str(error)}", extra={
            "event_type": "error",
            "error_type": error_type,
            "error_message": str(error),
            "context": context,
            "error_count": self.error_counts[error_key],
            "timestamp": datetime.now().isoformat(),
            **extra_info
        }, exc_info=True)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of tracked errors
        
        Returns:
            Dict with error statistics
        """
        return {
            "total_errors": sum(self.error_counts.values()),
            "unique_errors": len(self.error_counts),
            "error_breakdown": dict(self.error_counts),
            "timestamp": datetime.now().isoformat()
        }


# Global instances
_logger_setup = False
_error_tracker: Optional[ErrorTracker] = None


def initialize_logging() -> ErrorTracker:
    """
    Initialize logging system and return error tracker
    
    Returns:
        ErrorTracker: Global error tracker instance
    """
    global _logger_setup, _error_tracker
    
    if not _logger_setup:
        setup_logging()
        _logger_setup = True
    
    if _error_tracker is None:
        root_logger = logging.getLogger()
        _error_tracker = ErrorTracker(root_logger)
    
    return _error_tracker


def get_error_tracker() -> ErrorTracker:
    """
    Get the global error tracker instance
    
    Returns:
        ErrorTracker: Global error tracker
    """
    if _error_tracker is None:
        return initialize_logging()
    return _error_tracker