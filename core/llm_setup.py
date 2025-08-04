from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from config.app_config import get_config

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
    """Set up ChromaDB vectorstore with specified collection"""
    embeddings = setup_embeddings()
    config = get_config()
    collection_config = config.vectorstore.get_collection_config(collection_key)
    
    vectorstore = Chroma(
        persist_directory=collection_config["persist_directory"],
        collection_name=collection_config["collection_name"],
        embedding_function=embeddings,
    )
    return vectorstore

def setup_retriever(collection_key: str = None):
    """Set up the retriever from vectorstore with specified collection"""
    vectorstore = setup_vectorstore(collection_key)
    config = get_config()
    collection_config = config.vectorstore.get_collection_config(collection_key)
    return vectorstore.as_retriever(search_kwargs=collection_config["search_kwargs"]) 