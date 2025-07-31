#!/usr/bin/env python3
"""
Simple streaming performance test without Unicode issues
"""

import time
import os
from langchain.callbacks.base import BaseCallbackHandler

# Simple callback handler that properly inherits from BaseCallbackHandler
class SimpleStreamingHandler(BaseCallbackHandler):
    def __init__(self):
        super().__init__()
        self.start_time = None
        self.first_token_time = None
        self.token_count = 0
        
    def on_chat_model_start(self, *args, **kwargs):
        self.start_time = time.time()
        print("LLM processing started...")
        
    def on_llm_new_token(self, token, **kwargs):
        current_time = time.time()
        
        if self.first_token_time is None:
            self.first_token_time = current_time
            if self.start_time:
                ttft = (current_time - self.start_time) * 1000
                print(f"FIRST TOKEN received in {ttft:.1f}ms: '{token[:20]}...'")
        
        self.token_count += 1
        
        # Show progress every 20 tokens to avoid spam
        if self.token_count % 20 == 0:
            elapsed = (current_time - self.first_token_time) * 1000
            rate = self.token_count / ((current_time - self.first_token_time) + 0.001)
            print(f"Token {self.token_count}: {elapsed:.1f}ms total ({rate:.1f} tok/s)")
            
    def on_llm_end(self, *args, **kwargs):
        if self.start_time and self.first_token_time:
            end_time = time.time()
            total_time = (end_time - self.start_time) * 1000
            ttft = (self.first_token_time - self.start_time) * 1000
            generation_time = (end_time - self.first_token_time) * 1000
            
            print(f"\n=== PERFORMANCE RESULTS ===")
            print(f"Total tokens: {self.token_count}")
            print(f"Time to First Token (TTFT): {ttft:.1f}ms")
            print(f"Generation time: {generation_time:.1f}ms") 
            print(f"Total time: {total_time:.1f}ms")
            if generation_time > 0:
                print(f"Average speed: {self.token_count / (generation_time/1000):.1f} tokens/sec")

def test_direct_llm():
    """Test direct LLM streaming"""
    print("=" * 50)
    print("TESTING DIRECT LLM STREAMING")
    print("=" * 50)
    
    try:
        from core.llm_setup import setup_llm
        
        llm = setup_llm()
        handler = SimpleStreamingHandler()
        
        test_question = "What is characterology in one paragraph?"
        print(f"Question: {test_question}")
        print("-" * 40)
        
        response = llm.invoke(
            test_question,
            config={"callbacks": [handler]}
        )
        
        print(f"\nResponse length: {len(response.content)} characters")
        
    except Exception as e:
        print(f"Error in direct LLM test: {e}")
        import traceback
        traceback.print_exc()

def test_simple_streaming():
    """Very simple streaming test with just OpenAI"""
    print("\n" + "=" * 50)
    print("TESTING BASIC OPENAI STREAMING") 
    print("=" * 50)
    
    try:
        from openai import OpenAI
        from config.app_config import get_config
        
        config = get_config()
        client = OpenAI(api_key=config.api.openai_api_key)
        
        test_question = "What is characterology? Give a brief explanation."
        print(f"Question: {test_question}")
        print("-" * 40)
        
        start_time = time.time()
        first_token_time = None
        token_count = 0
        
        print("Response: ", end="", flush=True)
        
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": test_question}],
            stream=True,
            temperature=0.5
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                current_time = time.time()
                token = chunk.choices[0].delta.content
                
                if first_token_time is None:
                    first_token_time = current_time
                    ttft = (current_time - start_time) * 1000
                    print(f"\n[TTFT: {ttft:.1f}ms] ", end="", flush=True)
                
                print(token, end="", flush=True)
                token_count += 1
        
        print()  # New line after response
        
        if first_token_time:
            end_time = time.time()
            total_time = (end_time - start_time) * 1000
            ttft = (first_token_time - start_time) * 1000
            generation_time = (end_time - first_token_time) * 1000
            
            print(f"\n=== BASIC STREAMING RESULTS ===")
            print(f"Time to First Token: {ttft:.1f}ms")
            print(f"Total generation time: {generation_time:.1f}ms")
            print(f"Total chunks: {token_count}")
            if generation_time > 0:
                print(f"Streaming rate: {token_count / (generation_time/1000):.1f} chunks/sec")
                
    except Exception as e:
        print(f"Error in basic streaming test: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("STREAMING PERFORMANCE ANALYSIS")
    print("This will help identify where streaming delays occur\n")
    
    # Test 1: Basic OpenAI streaming (fastest possible)
    test_simple_streaming()
    
    # Test 2: Through LangChain (adds some overhead)
    test_direct_llm()
    
    print("\n" + "=" * 50)
    print("ANALYSIS COMPLETE")
    print("=" * 50)
    print("If TTFT > 2000ms = Processing/retrieval bottleneck")
    print("If TTFT < 500ms but slow rate = Network/token generation issue")
    print("Compare results to identify where delays occur")

if __name__ == "__main__":
    main()