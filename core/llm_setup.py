from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from config.app_config import get_config
import os

def setup_llm():
    """Set up the OpenAI LLM"""
    config = get_config()
    return ChatOpenAI(
        openai_api_key=config.api.openai_api_key,
        **config.llm.to_dict()
    )

def setup_embeddings():
    """Set up OpenAI embeddings"""
    config = get_config()
    return OpenAIEmbeddings(openai_api_key=config.api.openai_api_key)

def setup_vectorstore(collection_key: str = None):
    """Set up FAISS vectorstore with specified collection"""
    embeddings = setup_embeddings()
    config = get_config()
    collection_config = config.vectorstore.get_collection_config(collection_key)
    
    # Build FAISS index path
    faiss_path = os.path.join(collection_config["persist_directory"], f"{collection_config['collection_name']}_faiss")
    
    try:
        # Try to load existing FAISS index
        vectorstore = FAISS.load_local(
            faiss_path, 
            embeddings,
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        # If loading fails, create a simple in-memory vectorstore with dummy data
        # This is a fallback for cloud environments where the index files might not exist
        from langchain.schema import Document
        
        # Create a minimal vectorstore with a dummy document
        dummy_docs = [Document(page_content="CarIActérologie est un système d'aide à la caractérologie.", metadata={"source": "default"})]
        vectorstore = FAISS.from_documents(dummy_docs, embeddings)
        
        # Try to save it for future use
        try:
            os.makedirs(os.path.dirname(faiss_path), exist_ok=True)
            vectorstore.save_local(faiss_path)
        except:
            pass  # Ignore save errors in read-only environments
    
    return vectorstore

def setup_retriever(collection_key: str = None):
    """Set up the retriever from vectorstore with specified collection"""
    vectorstore = setup_vectorstore(collection_key)
    config = get_config()
    collection_config = config.vectorstore.get_collection_config(collection_key)
    return vectorstore.as_retriever(search_kwargs=collection_config["search_kwargs"]) 