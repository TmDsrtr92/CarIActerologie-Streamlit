#!/usr/bin/env python3
"""
Test script to verify LangGraph memory migration functionality
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_memory_creation():
    """Test creating LangGraph memory manager"""
    print("Testing LangGraph memory manager creation...")
    
    try:
        from core.langgraph_memory import create_langgraph_memory_manager, create_memory_manager
        
        # Test new memory manager
        manager = create_langgraph_memory_manager()
        print("[OK] LangGraph memory manager created successfully")
        
        # Test backward compatibility wrapper
        compat_manager = create_memory_manager()
        print("[OK] Backward compatibility wrapper created successfully")
        
        return True
    except Exception as e:
        print(f"[ERROR] Error creating memory managers: {e}")
        return False

def test_conversation_operations():
    """Test conversation operations"""
    print("\nTesting conversation operations...")
    
    try:
        from core.langgraph_memory import create_langgraph_memory_manager
        
        manager = create_langgraph_memory_manager()
        
        # Create conversation
        thread_id = manager.create_conversation("Test Conversation")
        print(f"[OK] Created conversation with thread ID: {thread_id}")
        
        # Save some context
        manager.save_context(
            {"question": "What is caractérologie?"},
            {"answer": "Caractérologie is the science of character types."}
        )
        print("[OK] Saved conversation context")
        
        # Get chat history
        history = manager.get_chat_history()
        print(f"[OK] Retrieved chat history: {len(history)} messages")
        
        # Get token count
        token_count = manager.get_token_count()
        print(f"[OK] Token count: {token_count}")
        
        # Test memory variables
        memory_vars = manager.get_memory_variables()
        print(f"[OK] Memory variables: {len(memory_vars['chat_history'])} messages")
        
        return True
    except Exception as e:
        print(f"[ERROR] Error in conversation operations: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test backward compatibility with old interface"""
    print("\nTesting backward compatibility...")
    
    try:
        from core.langgraph_memory import ConversationMemory
        
        # Create using old interface
        memory = ConversationMemory(max_token_limit=2000)
        print("[OK] Created memory with old interface")
        
        # Test old methods
        memory.save_context(
            {"question": "Test question"},
            {"answer": "Test answer"}
        )
        print("[OK] save_context() works")
        
        history = memory.get_chat_history()
        print(f"[OK] get_chat_history() works: {len(history)} messages")
        
        memory_vars = memory.get_memory_variables()
        print("[OK] get_memory_variables() works")
        
        token_count = memory.get_token_count()
        print(f"[OK] get_token_count() works: {token_count} tokens")
        
        memory.clear()
        print("[OK] clear() works")
        
        return True
    except Exception as e:
        print(f"[ERROR] Error in backward compatibility: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_qa_chain_integration():
    """Test QA chain integration"""
    print("\nTesting QA chain integration...")
    
    try:
        from core.langgraph_memory import create_memory_manager
        from core.langgraph_qa_chain import setup_qa_chain_with_memory
        
        # Create memory manager
        memory = create_memory_manager()
        print("[OK] Memory manager created")
        
        # Try to create QA chain (this might fail if OpenAI key is not set)
        try:
            qa_chain = setup_qa_chain_with_memory(memory)
            print("[OK] QA chain created successfully")
            return True
        except Exception as e:
            if "OPENAI_API_KEY" in str(e) or "secrets" in str(e):
                print("[SKIP] QA chain creation skipped (OpenAI API key not configured)")
                return True
            else:
                raise e
    except Exception as e:
        print(f"[ERROR] Error in QA chain integration: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_conversation_manager():
    """Test conversation manager functions"""
    print("\nTesting conversation manager...")
    
    try:
        # Mock streamlit session state
        class MockSessionState:
            def __init__(self):
                self.data = {}
            
            def __contains__(self, key):
                return key in self.data
            
            def __getitem__(self, key):
                return self.data[key]
            
            def __setitem__(self, key, value):
                self.data[key] = value
        
        # Mock streamlit
        import streamlit as st
        st.session_state = MockSessionState()
        
        from utils.conversation_manager import initialize_conversations, create_new_conversation
        
        # Initialize conversations
        initialize_conversations()
        print("[OK] Conversations initialized")
        
        # Create new conversation
        new_name = create_new_conversation()
        print(f"[OK] New conversation created: {new_name}")
        
        return True
    except Exception as e:
        print(f"[ERROR] Error in conversation manager: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("Starting LangGraph migration tests...\n")
    
    tests = [
        test_memory_creation,
        test_conversation_operations, 
        test_backward_compatibility,
        test_qa_chain_integration,
        test_conversation_manager
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! Migration is ready.")
        return 0
    else:
        print("Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)