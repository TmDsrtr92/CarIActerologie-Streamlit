"""
Test script to demonstrate retry logic functionality
"""

import sys
sys.path.append('.')

import openai
import time
from utils.retry_utils import retry_with_backoff, RetryStatus

def simulate_api_calls():
    """Simulate different API error scenarios"""
    
    print("=== RETRY LOGIC DEMONSTRATION ===\n")
    
    # Test 1: Function that fails twice then succeeds
    print("1. Testing transient error (succeeds on 3rd attempt):")
    attempt_count = 0
    
    def flaky_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            # Create a simple exception that mimics RateLimitError behavior
            class MockRateLimitError(openai.RateLimitError):
                def __init__(self, message):
                    self.message = message
                    # Don't call super().__init__ to avoid the response issue
                def __str__(self):
                    return self.message
            raise MockRateLimitError("Rate limit exceeded")
        return f"Success on attempt {attempt_count}"
    
    try:
        result = retry_with_backoff(flaky_function, max_retries=3, base_delay=0.1)
        print(f"   Result: {result}")
        print()
    except Exception as e:
        print(f"   Failed: {e}")
        print()
    
    # Test 2: Non-retriable error
    print("2. Testing non-retriable error (AuthenticationError):")
    def auth_error_function():
        raise openai.AuthenticationError("Invalid API key", response=None, body=None)
    
    try:
        result = retry_with_backoff(auth_error_function, max_retries=3, base_delay=0.1)
        print(f"   Result: {result}")
    except openai.AuthenticationError as e:
        print(f"   Correctly failed immediately: {e}")
        print()
    
    # Test 3: RetryStatus tracking
    print("3. Testing RetryStatus for user feedback:")
    status = RetryStatus()
    status.start_retry(3)
    
    # Simulate retry progression
    for attempt in range(1, 4):
        error = openai.APIConnectionError("Connection failed", response=None, body=None)
        status.on_retry_attempt(attempt, error, 1.5)
        message = status.get_status_message()
        print(f"   Attempt {attempt}: {message}")
    
    status.finish_retry(success=True)
    print("   Final: Retry completed successfully")
    print()
    
    # Test 4: Exponential backoff delays
    print("4. Testing exponential backoff delays:")
    from utils.retry_utils import exponential_backoff_delay
    
    for attempt in range(4):
        delay = exponential_backoff_delay(attempt, base_delay=1.0)
        print(f"   Attempt {attempt + 1} delay: {delay:.2f}s")
    
    print()
    print("=== INTEGRATION BENEFITS ===")
    print("✅ Automatic retry for transient errors (rate limits, timeouts, connection issues)")
    print("✅ Smart error categorization (retry vs. permanent errors)")
    print("✅ User feedback during retry attempts")
    print("✅ Exponential backoff prevents overwhelming the API")
    print("✅ Configurable retry parameters (max attempts, delays)")
    print("✅ Proper logging and error tracking")

if __name__ == "__main__":
    simulate_api_calls()