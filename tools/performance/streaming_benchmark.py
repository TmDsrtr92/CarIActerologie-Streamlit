#!/usr/bin/env python3
"""
Performance test for streaming functionality
This script helps identify bottlenecks in the streaming pipeline
"""

import time
import asyncio
from services.ai_service.llm_client import get_llm_client
from services.ai_service.qa_engine import get_qa_engine
from services.chat_service.memory_repository import get_memory_repository
from infrastructure.monitoring.logging_service import initialize_logging, get_logger

# Simple callback to measure streaming performance
class PerformanceTestHandler:
    def __init__(self):
        self.start_time = None
        self.first_token_time = None
        self.token_count = 0
        self.tokens = []
        
    def on_llm_start(self, *args, **kwargs):
        self.start_time = time.time()
        print(f"LLM Start: {time.strftime('%H:%M:%S.%f')[:-3]}")
        
    def on_llm_new_token(self, token, **kwargs):
        current_time = time.time()
        
        if self.first_token_time is None:
            self.first_token_time = current_time
            ttft = (current_time - self.start_time) * 1000
            print(f"First Token: {ttft:.1f}ms - Token: '{token}'")
        
        self.token_count += 1
        self.tokens.append((current_time, token))
        
        # Show progress every 10 tokens
        if self.token_count % 10 == 0:
            elapsed = (current_time - self.first_token_time) * 1000
            rate = self.token_count / ((current_time - self.first_token_time) + 0.001)
            print(f"Token {self.token_count}: {elapsed:.1f}ms ({rate:.1f} tok/s)")
            
    def on_llm_end(self, *args, **kwargs):
        end_time = time.time()
        if self.start_time and self.first_token_time:
            total_time = (end_time - self.start_time) * 1000
            ttft = (self.first_token_time - self.start_time) * 1000
            generation_time = (end_time - self.first_token_time) * 1000
            
            print(f"\nPerformance Summary:")
            print(f"   Total tokens: {self.token_count}")
            print(f"   Time to First Token: {ttft:.1f}ms")
            print(f"   Generation time: {generation_time:.1f}ms")
            print(f"   Total time: {total_time:.1f}ms")
            print(f"   Average speed: {self.token_count / ((end_time - self.first_token_time) + 0.001):.1f} tok/s")

def test_direct_llm_streaming():
    """Test direct LLM streaming without RAG"""
    print("=" * 60)
    print("Testing Direct LLM Streaming")
    print("=" * 60)
    
    llm = setup_llm()
    handler = PerformanceTestHandler()
    
    # Simple test question
    test_question = "Qu'est-ce que la caractérologie ?"
    
    print(f"Question: {test_question}")
    print("-" * 40)
    
    try:
        response = llm.invoke(
            test_question,
            config={"callbacks": [handler]}
        )
        print(f"\nResponse: {response.content[:100]}...")
    except Exception as e:
        print(f"Error: {e}")

def test_rag_chain_streaming():
    """Test RAG chain streaming"""
    print("\n" + "=" * 60)
    print("Testing RAG Chain Streaming")
    print("=" * 60)
    
    try:
        # Set up memory manager
        memory_manager = LangGraphMemoryManager()
        
        # Set up QA chain
        qa_chain = setup_qa_chain_with_memory(memory_manager)
        
        handler = PerformanceTestHandler()
        
        test_question = "Qu'est-ce que la caractérologie ?"
        print(f"Question: {test_question}")
        print("-" * 40)
        
        # Measure retrieval time
        retrieval_start = time.time()
        result = qa_chain.invoke(
            {"question": test_question},
            config={"callbacks": [handler]}
        )
        retrieval_time = (time.time() - retrieval_start) * 1000
        
        print(f"\nTotal pipeline time: {retrieval_time:.1f}ms")
        print(f"Response: {result['answer'][:100]}...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run streaming performance tests"""
    # Initialize logging
    initialize_logging()
    logger = get_logger(__name__)
    
    print("Streaming Performance Analysis")
    print("This test will help identify bottlenecks in the streaming pipeline\n")
    
    # Test 1: Direct LLM streaming (no RAG)
    test_direct_llm_streaming()
    
    # Test 2: Full RAG chain streaming
    test_rag_chain_streaming()
    
    print("\n" + "=" * 60)
    print("Analysis Complete")
    print("=" * 60)
    print("Check the output above to identify where delays occur:")
    print("• High TTFT (>2000ms) = Retrieval/prompt processing bottleneck")
    print("• Low TTFT but slow generation = Token generation bottleneck")
    print("• Direct LLM fast but RAG slow = Retrieval system bottleneck")

if __name__ == "__main__":
    main()