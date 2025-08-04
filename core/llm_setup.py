from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from config.app_config import get_config
import streamlit as st
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

@st.cache_resource
def setup_vectorstore(collection_key: str = None):
    """Set up FAISS vectorstore with document content"""
    embeddings = setup_embeddings()
    
    # Load document content
    try:
        # Read the main document
        doc_path = "documents/traite_de_caracterologie.txt"
        if os.path.exists(doc_path):
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            # Fallback content for cloud deployment
            content = """René LE SENNE - Traité de Caractérologie
            
            Ce document traite de la caractérologie selon les travaux de René Le Senne.
            La caractérologie étudie les types de caractères humains et leurs manifestations.
            
            Les principaux concepts incluent:
            - Les types caractériels
            - L'analyse psychologique  
            - Les traits de personnalité
            - Les comportements humains
            
            Cette science permet de mieux comprendre la nature humaine et ses variations."""
        
        # Split the document into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        texts = text_splitter.split_text(content)
        documents = [Document(page_content=text) for text in texts]
        
        # Create FAISS vectorstore
        vectorstore = FAISS.from_documents(documents, embeddings)
        return vectorstore
        
    except Exception as e:
        st.error(f"Error creating vectorstore: {e}")
        # Return empty vectorstore as fallback
        documents = [Document(page_content="Contenu de caractérologie non disponible.")]
        return FAISS.from_documents(documents, embeddings)

def setup_retriever(collection_key: str = None):
    """Set up the retriever from vectorstore with specified collection"""
    vectorstore = setup_vectorstore(collection_key)
    config = get_config()
    collection_config = config.vectorstore.get_collection_config(collection_key)
    return vectorstore.as_retriever(search_kwargs=collection_config["search_kwargs"]) 