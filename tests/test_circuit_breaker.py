"""
Test script to demonstrate circuit breaker functionality
"""

import sys
sys.path.append('.')

import time
from datetime import datetime
from utils.retry_utils import CircuitBreaker, CircuitBreakerError, CircuitState

def simulate_circuit_breaker_behavior():
    """Demonstrate circuit breaker state transitions"""
    
    print("=== CIRCUIT BREAKER BEHAVIOR DEMONSTRATION ===")
    print()
    
    # Create a test circuit breaker with low thresholds for demonstration
    cb = CircuitBreaker(
        failure_threshold=3,    # Open after 3 failures
        recovery_timeout=5,     # Wait 5 seconds before recovery attempt
        name="Demo_Circuit"
    )
    
    print("Circuit Breaker Configuration:")
    print(f"- Failure Threshold: {cb.failure_threshold}")
    print(f"- Recovery Timeout: {cb.recovery_timeout}s")
    print()
    
    # Simulate a function that sometimes fails
    failure_count = 0
    
    def sometimes_fails():
        nonlocal failure_count
        failure_count += 1
        
        # Fail for the first 4 attempts, then succeed
        if failure_count <= 4:
            # Simulate different types of failures
            import openai
            if failure_count <= 2:
                raise openai.APIConnectionError("Connection failed", response=None, body=None)
            else:
                raise openai.RateLimitError("Rate limit exceeded", response=None, body=None)
        else:
            return f"Success on attempt {failure_count}"
    
    print("Testing Circuit Breaker State Transitions:")
    print("-" * 50)
    
    # Test multiple requests to show state transitions
    for request_num in range(1, 8):
        print(f"Request {request_num}:")
        
        try:
            # Check if we can execute
            state = cb.get_state()
            print(f"  Circuit State: {state['state'].upper()}")
            print(f"  Failure Count: {state['failure_count']}")
            
            if state['state'] == 'open':
                remaining = state['remaining_timeout']
                print(f"  Recovery in: {remaining:.1f}s")
            
            # Try to execute the function
            if cb.can_execute():
                try:
                    result = cb.execute(sometimes_fails)
                    print(f"  Result: {result}")
                except Exception as e:
                    print(f"  Failed: {e.__class__.__name__}: {str(e)}")
            else:
                print("  Request blocked by circuit breaker")
                
        except CircuitBreakerError as e:
            print(f"  Circuit Breaker Error: {str(e)}")
        
        print()
        
        # Add delay to show recovery timeout behavior
        if request_num == 4:  # After circuit opens
            print("  Waiting for recovery timeout...")
            time.sleep(2)
        elif request_num == 6:  # During half-open testing
            print("  Testing recovery...")
            time.sleep(1)
    
    print("=== CIRCUIT BREAKER BENEFITS ===")
    print("✓ Prevents cascading failures")
    print("✓ Gives external services time to recover") 
    print("✓ Provides fast-fail responses when service is down")
    print("✓ Automatic recovery testing")
    print("✓ Reduces unnecessary load on failing systems")
    print("✓ Improves overall system resilience")
    
    print()
    print("=== USER EXPERIENCE IMPACT ===")
    print("Without Circuit Breaker:")
    print("- Every request waits for timeout")
    print("- Slow failure responses")
    print("- Continuous load on failing service")
    
    print()
    print("With Circuit Breaker:")
    print("- Fast-fail when service is down")
    print("- Clear status indication")
    print("- Automatic recovery attempts")
    print("- Reduced waiting time")

def demonstrate_integration_benefits():
    """Show how circuit breaker integrates with retry logic"""
    
    print()
    print("=== INTEGRATION WITH RETRY LOGIC ===")
    print()
    
    print("Complete Error Handling Stack:")
    print("1. Circuit Breaker Check -> Fast-fail if service down")
    print("2. Retry Logic -> 3 attempts with exponential backoff")
    print("3. Specific Error Messages -> Clear user guidance")
    print("4. Error Tracking -> Detailed logging and monitoring")
    
    print()
    print("Flow for a typical API call:")
    print("Request -> Circuit Check -> Retry 1 -> Retry 2 -> Retry 3 -> Final Error")
    print("         |              |         |         |         |")
    print("         |              v         v         v         v")
    print("         |           Log fail  Log fail  Log fail  Update circuit")
    print("         |")
    print("         v (if circuit open)")
    print("      Fast-fail with clear message")
    
    print()
    print("RESULT: Maximum reliability with optimal user experience")

if __name__ == "__main__":
    try:
        simulate_circuit_breaker_behavior()
        demonstrate_integration_benefits()
        print()
        print("🎉 CIRCUIT BREAKER PATTERN IMPLEMENTATION COMPLETE!")
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        sys.exit(1)