"""
Test script to verify collection switching functionality
"""
from config.settings import AVAILABLE_COLLECTIONS, get_vectorstore_config
from core.llm_setup import setup_vectorstore, setup_retriever

def test_collections():
    """Test that both collections can be loaded and queried"""
    print("=== Testing Collection Switching ===\n")
    
    for collection_key, collection_info in AVAILABLE_COLLECTIONS.items():
        print(f"Testing collection: {collection_key}")
        print(f"Description: {collection_info['description']}")
        
        try:
            # Test vectorstore creation
            vectorstore = setup_vectorstore(collection_key)
            print(f"[OK] Vectorstore loaded successfully")
            
            # Test retriever creation
            retriever = setup_retriever(collection_key)
            print(f"[OK] Retriever created successfully")
            
            # Test simple query
            test_query = "emotivite"
            results = retriever.invoke(test_query)
            print(f"[OK] Query '{test_query}' returned {len(results)} results")
            
            if results:
                first_result = results[0]
                preview = first_result.page_content[:100].replace('\n', ' ')
                print(f"  First result preview: {preview}...")
                if hasattr(first_result, 'metadata') and first_result.metadata:
                    print(f"  Metadata keys: {list(first_result.metadata.keys())}")
            
            print(f"[OK] Collection '{collection_key}' working correctly\n")
            
        except Exception as e:
            print(f"[ERROR] Error with collection '{collection_key}': {e}\n")

def test_config_function():
    """Test the get_vectorstore_config function"""
    print("=== Testing Configuration Function ===\n")
    
    # Test default config
    default_config = get_vectorstore_config()
    print(f"Default config: {default_config}")
    
    # Test specific collections
    for collection_key in AVAILABLE_COLLECTIONS.keys():
        config = get_vectorstore_config(collection_key)
        print(f"Config for '{collection_key}': {config['collection_name']}")
    
    # Test invalid collection
    invalid_config = get_vectorstore_config("NonExistent")
    print(f"Invalid collection fallback: {invalid_config['collection_name']}")
    print()

if __name__ == "__main__":
    try:
        test_config_function()
        test_collections()
        print("=== All tests completed! ===")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()