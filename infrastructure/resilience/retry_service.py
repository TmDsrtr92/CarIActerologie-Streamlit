"""
Resilience service for retry logic, circuit breakers, and fault tolerance.
Moved from utils/retry_utils.py into infrastructure layer for proper architectural separation.
"""

import time
import random
from typing import Callable, Any, Tuple, Type, Optional
from functools import wraps
from datetime import datetime, timedelta
from enum import Enum
import threading
import openai

from infrastructure.monitoring.logging_service import get_logger

logger = get_logger(__name__)

# Define which errors should trigger retries (transient errors)
RETRIABLE_ERRORS = (
    openai.RateLimitError,
    openai.APIConnectionError, 
    openai.APITimeoutError,
    openai.InternalServerError,  # Server-side issues
)

# Define which errors should NOT be retried (permanent errors)
NON_RETRIABLE_ERRORS = (
    openai.AuthenticationError,  # API key issues
    openai.BadRequestError,      # User input issues
    openai.ContentFilterFinishReasonError,  # Content policy violations
)


def exponential_backoff_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """
    Calculate exponential backoff delay with jitter
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * 2^attempt
    delay = base_delay * (2 ** attempt)
    
    # Cap at maximum delay
    delay = min(delay, max_delay)
    
    # Add jitter to avoid thundering herd effect
    jitter = random.uniform(0, 0.1 * delay)
    
    return delay + jitter


class RetryStatus:
    """Helper class to track retry status for UI feedback"""
    
    def __init__(self):
        self.is_retrying = False
        self.current_attempt = 0
        self.max_attempts = 0
        self.last_error = None
        self.next_delay = 0.0
    
    def start_retry(self, max_attempts: int):
        """Start a new retry sequence"""
        self.is_retrying = True
        self.current_attempt = 0
        self.max_attempts = max_attempts
        self.last_error = None
        self.next_delay = 0.0
    
    def on_retry_attempt(self, attempt: int, error: Exception, next_delay: float = 0.0):
        """Update status for a retry attempt"""
        self.current_attempt = attempt
        self.last_error = error
        self.next_delay = next_delay
    
    def finish_retry(self, success: bool = True):
        """Finish the retry sequence"""
        self.is_retrying = False
        if success:
            self.current_attempt = 0
            self.last_error = None
    
    def get_status_message(self) -> str:
        """Get a user-friendly status message"""
        if not self.is_retrying:
            return ""
        
        error_name = self.last_error.__class__.__name__ if self.last_error else "Error"
        
        if self.next_delay > 0:
            return f"🔄 **Nouvelle tentative** ({error_name}) - Tentative {self.current_attempt}/{self.max_attempts} dans {self.next_delay:.1f}s"
        else:
            return f"🔄 **Nouvelle tentative** ({error_name}) - Tentative {self.current_attempt}/{self.max_attempts}"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Circuit is open, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreakerError(Exception):
    """Custom exception for circuit breaker failures"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for external API calls
    
    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Circuit is open, requests fail fast without hitting the API
    - HALF_OPEN: Testing recovery, limited requests allowed through
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: tuple = RETRIABLE_ERRORS,
        name: str = "CircuitBreaker"
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exceptions that count as failures
            name: Name for logging and identification
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        # State tracking
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        
        # Thread safety
        self._lock = threading.Lock()
        
        logger.info(f"CircuitBreaker '{name}' initialized with threshold={failure_threshold}, timeout={recovery_timeout}s")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return False
        
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    def _record_success(self):
        """Record a successful operation"""
        with self._lock:
            self.failure_count = 0
            self.success_count += 1
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                # Recovery successful, close the circuit
                self.state = CircuitBreakerState.CLOSED
                logger.info(f"CircuitBreaker '{self.name}' recovered - state: CLOSED")
    
    def _record_failure(self, exception: Exception):
        """Record a failed operation"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                # Recovery attempt failed, open circuit again
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"CircuitBreaker '{self.name}' recovery failed - state: OPEN")
            
            elif self.state == CircuitBreakerState.CLOSED and self.failure_count >= self.failure_threshold:
                # Threshold reached, open the circuit
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"CircuitBreaker '{self.name}' opened - failures: {self.failure_count}")
    
    def can_execute(self) -> bool:
        """Check if a request can be executed"""
        with self._lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            
            elif self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    # Time to test recovery
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info(f"CircuitBreaker '{self.name}' attempting recovery - state: HALF_OPEN")
                    return True
                return False
            
            elif self.state == CircuitBreakerState.HALF_OPEN:
                # Only allow one request in half-open state
                return True
            
            return False
    
    def execute(self, func: Callable) -> Any:
        """
        Execute a function with circuit breaker protection
        
        Args:
            func: Function to execute
            
        Returns:
            Function result if successful
            
        Raises:
            CircuitBreakerError: If circuit is open
            Original exception: If function fails
        """
        if not self.can_execute():
            remaining_time = self.recovery_timeout
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                remaining_time = max(0, self.recovery_timeout - elapsed)
            
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service appears to be down. Retry in {remaining_time:.0f}s."
            )
        
        try:
            result = func()
            self._record_success()
            return result
            
        except self.expected_exception as e:
            self._record_failure(e)
            raise e
        except Exception as e:
            # Non-expected exceptions don't count as circuit failures
            logger.warning(f"CircuitBreaker '{self.name}' encountered non-tracked exception: {e.__class__.__name__}")
            raise e
    
    def get_state(self) -> dict:
        """Get current circuit breaker state for monitoring"""
        with self._lock:
            remaining_timeout = 0
            if self.last_failure_time and self.state == CircuitBreakerState.OPEN:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                remaining_timeout = max(0, self.recovery_timeout - elapsed)
            
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "failure_threshold": self.failure_threshold,
                "remaining_timeout": remaining_timeout,
                "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
            }
    
    def reset(self):
        """Manually reset the circuit breaker to CLOSED state"""
        with self._lock:
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            logger.info(f"CircuitBreaker '{self.name}' manually reset - state: CLOSED")


class RetryService:
    """
    Service for handling retry logic and circuit breakers.
    Provides infrastructure-level fault tolerance capabilities.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
    
    def create_circuit_breaker(
        self, 
        name: str, 
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: tuple = RETRIABLE_ERRORS
    ) -> CircuitBreaker:
        """Create a new circuit breaker"""
        circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=name
        )
        self._circuit_breakers[name] = circuit_breaker
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get an existing circuit breaker by name"""
        return self._circuit_breakers.get(name)
    
    def retry_with_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        on_retry: Optional[Callable[[int, Exception], None]] = None
    ) -> Any:
        """
        Execute a function with retry logic and exponential backoff
        
        Args:
            func: Function to execute
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            on_retry: Optional callback for retry events (attempt_number, exception)
            
        Returns:
            Function result if successful
            
        Raises:
            The last exception if all retries are exhausted
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                result = func()
                
                if attempt > 0:
                    self.logger.info(f"Function succeeded after {attempt} retries")
                
                return result
                
            except RETRIABLE_ERRORS as e:
                last_exception = e
                
                if attempt == max_retries:
                    # Last attempt failed, raise the exception
                    self.logger.error(f"Function failed after {max_retries} retries: {str(e)}")
                    raise e
                
                # Calculate delay for next attempt
                delay = exponential_backoff_delay(attempt, base_delay, max_delay)
                
                self.logger.warning(f"Attempt {attempt + 1} failed ({e.__class__.__name__}), retrying in {delay:.2f}s")
                
                # Call retry callback if provided
                if on_retry:
                    on_retry(attempt + 1, e)
                
                time.sleep(delay)
                
            except NON_RETRIABLE_ERRORS as e:
                # Don't retry these errors
                self.logger.warning(f"Non-retriable error encountered: {e.__class__.__name__}: {str(e)}")
                raise e
                
            except Exception as e:
                # For unknown exceptions, don't retry by default
                self.logger.error(f"Unknown exception encountered (not retrying): {e.__class__.__name__}: {str(e)}")
                raise e
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
    
    def retry_with_circuit_breaker(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
        on_retry: Optional[Callable[[int, Exception], None]] = None
    ) -> Any:
        """
        Execute a function with both retry logic and circuit breaker protection
        
        Args:
            func: Function to execute
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            circuit_breaker: Circuit breaker instance
            on_retry: Optional callback for retry events
            
        Returns:
            Function result if successful
            
        Raises:
            CircuitBreakerError: If circuit breaker is open
            The last exception if all retries are exhausted
        """
        if circuit_breaker is None:
            circuit_breaker = self.get_openai_circuit_breaker()
        
        def wrapped_func():
            return circuit_breaker.execute(func)
        
        try:
            return self.retry_with_backoff(
                wrapped_func,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                on_retry=on_retry
            )
        except CircuitBreakerError:
            # Don't retry circuit breaker errors
            raise
    
    def get_openai_circuit_breaker(self) -> CircuitBreaker:
        """Get or create the OpenAI circuit breaker"""
        if "openai" not in self._circuit_breakers:
            self._circuit_breakers["openai"] = self.create_circuit_breaker(
                name="OpenAI_API",
                failure_threshold=5,
                recovery_timeout=60,
                expected_exception=RETRIABLE_ERRORS
            )
        return self._circuit_breakers["openai"]


# Global retry service instance
_retry_service: Optional[RetryService] = None


def get_retry_service() -> RetryService:
    """Get the global retry service instance"""
    global _retry_service
    if _retry_service is None:
        _retry_service = RetryService()
    return _retry_service


# Legacy compatibility functions
def get_openai_circuit_breaker() -> CircuitBreaker:
    """Get OpenAI circuit breaker (legacy compatibility)"""
    service = get_retry_service()
    return service.get_openai_circuit_breaker()


def retry_with_circuit_breaker(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    circuit_breaker: Optional[CircuitBreaker] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None
) -> Any:
    """Execute function with retry and circuit breaker (legacy compatibility)"""
    service = get_retry_service()
    return service.retry_with_circuit_breaker(
        func, max_retries, base_delay, max_delay, circuit_breaker, on_retry
    )