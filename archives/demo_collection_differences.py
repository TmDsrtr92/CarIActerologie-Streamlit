"""
Demo script to show the differences between the two collections
"""
from core.llm_setup import setup_retriever
from config.settings import AVAILABLE_COLLECTIONS

def compare_collections_demo():
    """Compare results from both collections for a sample query"""
    query = "nerveux"
    
    print(f"=== Comparing Collections for Query: '{query}' ===\n")
    
    for collection_key, collection_info in AVAILABLE_COLLECTIONS.items():
        print(f"Collection: {collection_key}")
        print(f"Description: {collection_info['description']}")
        print("-" * 60)
        
        try:
            retriever = setup_retriever(collection_key)
            results = retriever.invoke(query)
            
            print(f"Results: {len(results)} documents retrieved")
            
            for i, result in enumerate(results[:3], 1):  # Show top 3 results
                print(f"\n{i}. Content ({len(result.page_content)} chars):")
                # Clean preview
                preview = result.page_content[:300].replace('\n', ' ').strip()
                print(f"   {preview}...")
                
                if hasattr(result, 'metadata') and result.metadata:
                    if 'section_title' in result.metadata:
                        title = result.metadata['section_title'][:50]
                        print(f"   Section: {title}")
                    if 'section_type' in result.metadata:
                        print(f"   Type: {result.metadata['section_type']}")
            
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    compare_collections_demo()