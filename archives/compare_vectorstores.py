"""
Compare the performance of the original and sub-chapter vectorstores
"""
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from config.settings import get_openai_api_key
import streamlit as st

def setup_vectorstore(collection_name: str):
    """Setup a vectorstore with given collection name"""
    api_key = get_openai_api_key()
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    
    vectorstore = Chroma(
        persist_directory="./index_stores",
        collection_name=collection_name,
        embedding_function=embeddings,
    )
    return vectorstore

def compare_retrievals(query: str, k: int = 5):
    """Compare retrieval results between collections"""
    print(f"\n=== Comparing retrievals for: '{query}' ===")
    
    # Setup both vectorstores
    try:
        legacy_vs = setup_vectorstore("traite")
        print("✓ Legacy collection loaded")
    except Exception as e:
        print(f"✗ Failed to load legacy collection: {e}")
        return
    
    try:
        subchapter_vs = setup_vectorstore("traite_subchapters")
        print("✓ Sub-chapter collection loaded")
    except Exception as e:
        print(f"✗ Failed to load sub-chapter collection: {e}")
        return
    
    # Get retrievers
    legacy_retriever = legacy_vs.as_retriever(search_kwargs={"k": k})
    subchapter_retriever = subchapter_vs.as_retriever(search_kwargs={"k": k})
    
    # Perform retrievals
    print(f"\nRetrieving top {k} results...")
    
    try:
        legacy_results = legacy_retriever.invoke(query)
        print(f"✓ Legacy retrieval: {len(legacy_results)} results")
    except Exception as e:
        print(f"✗ Legacy retrieval failed: {e}")
        return
    
    try:
        subchapter_results = subchapter_retriever.invoke(query)
        print(f"✓ Sub-chapter retrieval: {len(subchapter_results)} results")
    except Exception as e:
        print(f"✗ Sub-chapter retrieval failed: {e}")
        return
    
    # Display results
    print(f"\n{'='*80}")
    print(f"LEGACY COLLECTION (traite) - {len(legacy_results)} results:")
    print(f"{'='*80}")
    
    for i, doc in enumerate(legacy_results, 1):
        content_preview = doc.page_content[:200].replace('\n', ' ')
        print(f"{i}. {content_preview}...")
        print(f"   Size: {len(doc.page_content)} chars")
        if hasattr(doc, 'metadata') and doc.metadata:
            print(f"   Metadata: {doc.metadata}")
        print()
    
    print(f"\n{'='*80}")
    print(f"SUB-CHAPTER COLLECTION (traite_subchapters) - {len(subchapter_results)} results:")
    print(f"{'='*80}")
    
    for i, doc in enumerate(subchapter_results, 1):
        content_preview = doc.page_content[:200].replace('\n', ' ')
        print(f"{i}. {content_preview}...")
        print(f"   Size: {len(doc.page_content)} chars")
        if hasattr(doc, 'metadata') and doc.metadata:
            section_title = doc.metadata.get('section_title', 'Unknown')[:50]
            section_type = doc.metadata.get('section_type', 'Unknown')
            print(f"   Section: {section_title}")
            print(f"   Type: {section_type}")
        print()

def main():
    """Main comparison function"""
    print("=== Vectorstore Comparison Tool ===")
    
    # Test queries
    test_queries = [
        "émotivité",
        "caractère nerveux",
        "Le Senne",
        "typologie caractérologique",
        "passion"
    ]
    
    for query in test_queries:
        try:
            compare_retrievals(query, k=3)
            print("\n" + "="*100 + "\n")
        except Exception as e:
            print(f"Error comparing query '{query}': {e}")
    
    print("Comparison complete!")

if __name__ == "__main__":
    main()