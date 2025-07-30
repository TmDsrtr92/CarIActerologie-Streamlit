from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from config.settings import get_openai_api_key, LLM_CONFIG, get_vectorstore_config

def setup_llm():
    """Set up the OpenAI LLM"""
    openai_api_key = get_openai_api_key()
    return ChatOpenAI(
        openai_api_key=openai_api_key,
        **LLM_CONFIG
    )

def setup_embeddings():
    """Set up OpenAI embeddings"""
    openai_api_key = get_openai_api_key()
    return OpenAIEmbeddings(openai_api_key=openai_api_key)

def setup_vectorstore(collection_key: str = None):
    """Set up ChromaDB vectorstore with specified collection"""
    embeddings = setup_embeddings()
    config = get_vectorstore_config(collection_key)
    
    vectorstore = Chroma(
        persist_directory=config["persist_directory"],
        collection_name=config["collection_name"],
        embedding_function=embeddings,
    )
    return vectorstore

def setup_retriever(collection_key: str = None):
    """Set up the retriever from vectorstore with specified collection"""
    vectorstore = setup_vectorstore(collection_key)
    config = get_vectorstore_config(collection_key)
    return vectorstore.as_retriever(search_kwargs=config["search_kwargs"]) 