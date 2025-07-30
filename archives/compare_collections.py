from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from config.settings import get_openai_api_key


def compare_collections(collection_names, test_queries):
    """Compare different collections with the same test queries"""
    embeddings = OpenAIEmbeddings(openai_api_key=get_openai_api_key())
    
    results = {}
    
    for collection_name in collection_names:
        try:
            # Charger la collection
            vectorstore = Chroma(
                persist_directory="./index_stores",
                collection_name=collection_name,
                embedding_function=embeddings,
            )
            
            collection_results = []
            for query in test_queries:
                # Rechercher dans la collection
                docs = vectorstore.similarity_search(query, k=3)
                
                # Extraire les métadonnées et scores si disponibles
                doc_info = []
                for i, doc in enumerate(docs):
                    doc_info.append({
                        "rank": i + 1,
                        "content_preview": doc.page_content[:100] + "...",
                        "metadata": doc.metadata
                    })
                
                collection_results.append({
                    "query": query,
                    "results": doc_info
                })
            
            results[collection_name] = collection_results
            print(f"✓ Collection '{collection_name}' analysée avec succès")
            
        except Exception as e:
            print(f"✗ Erreur avec la collection '{collection_name}': {e}")
            results[collection_name] = None
    
    return results

def print_comparison(results):
    """Afficher les résultats de comparaison"""
    print("\n" + "="*80)
    print("COMPARAISON DES COLLECTIONS")
    print("="*80)
    
    for collection_name, collection_results in results.items():
        if collection_results is None:
            continue
            
        print(f"\n📚 Collection: {collection_name}")
        print("-" * 50)
        
        for query_result in collection_results:
            print(f"\n🔍 Requête: '{query_result['query']}'")
            for doc_info in query_result['results']:
                print(f"  {doc_info['rank']}. {doc_info['content_preview']}")

if __name__ == "__main__":
    # Collections à comparer
    collections_to_compare = ["traite", "traite_v2"]  # Ajoutez vos collections ici
    
    # Requêtes de test
    test_queries = [
        "Qu'est-ce que l'émotivité en caractérologie ?",
        "Définissez les types de caractères principaux",
        "Quelle est la différence entre primarité et secondarité ?"
    ]
    
    print("🔍 Comparaison des collections d'embeddings...")
    results = compare_collections(collections_to_compare, test_queries)
    print_comparison(results) 