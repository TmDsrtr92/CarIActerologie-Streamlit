from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document
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
    
    # Build FAISS index path (collection_name already includes _faiss suffix)
    faiss_path = os.path.join(collection_config["persist_directory"], collection_config["collection_name"])
    
    try:
        # Check if FAISS index directory exists
        if not os.path.exists(faiss_path):
            print(f"WARNING: FAISS index not found at: {faiss_path}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Directory contents: {os.listdir('.')}")
            if os.path.exists('index_stores'):
                print(f"index_stores contents: {os.listdir('index_stores')}")
            raise FileNotFoundError(f"FAISS index directory not found: {faiss_path}")
        
        print(f"Loading FAISS index from: {faiss_path}")
        # Try to load existing FAISS index
        vectorstore = FAISS.load_local(
            faiss_path, 
            embeddings,
            allow_dangerous_deserialization=True
        )
        print(f"SUCCESS: FAISS index loaded successfully with {vectorstore.index.ntotal} vectors")
        
    except Exception as e:
        print(f"ERROR: Failed to load FAISS index: {str(e)}")
        print(f"   Path attempted: {faiss_path}")
        print(f"   Error type: {type(e).__name__}")
        
        # Check if we can create the index from the PDF
        pdf_path = "documents/traite_caracterologie.pdf"
        if os.path.exists(pdf_path):
            print(f"PDF found, attempting to create FAISS index from: {pdf_path}")
            try:
                vectorstore = create_faiss_index_from_pdf(pdf_path, faiss_path, embeddings)
                print(f"SUCCESS: Successfully created FAISS index with {vectorstore.index.ntotal} vectors")
            except Exception as create_error:
                print(f"ERROR: Failed to create FAISS index from PDF: {str(create_error)}")
                vectorstore = create_dummy_vectorstore(embeddings)
        else:
            print(f"ERROR: PDF not found at: {pdf_path}, using dummy vectorstore")
            vectorstore = create_dummy_vectorstore(embeddings)
    
    return vectorstore

def setup_retriever(collection_key: str = None):
    """Set up the retriever from vectorstore with specified collection"""
    vectorstore = setup_vectorstore(collection_key)
    config = get_config()
    collection_config = config.vectorstore.get_collection_config(collection_key)
    return vectorstore.as_retriever(search_kwargs=collection_config["search_kwargs"])


def create_dummy_vectorstore(embeddings):
    """Create a dummy vectorstore with placeholder content"""
    print("Creating dummy vectorstore as fallback")
    dummy_docs = [Document(
        page_content="CarIActérologie est un système d'aide à la caractérologie.", 
        metadata={"source": "default"}
    )]
    return FAISS.from_documents(dummy_docs, embeddings)


def create_faiss_index_from_pdf(pdf_path: str, faiss_path: str, embeddings):
    """Create FAISS index from PDF using the same logic as create_subchapter_vectorstore.py"""
    print(f"Creating FAISS index from PDF: {pdf_path}")
    
    # Import the chunker from the existing script
    import sys
    import importlib.util
    
    # Load the chunker class from create_subchapter_vectorstore.py
    spec = importlib.util.spec_from_file_location("subchapter_vectorstore", "create_subchapter_vectorstore.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Use the same logic as the original script
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    print(f"Loaded {len(pages)} pages from PDF")
    
    # Combine all pages into one text
    full_text = "\n\n".join([page.page_content for page in pages])
    
    # Create metadata
    source_metadata = {
        "source": pdf_path,
        "total_pages": len(pages),
        "processing_date": "runtime_generated"
    }
    
    # Initialize chunker and process text
    chunker = module.SubChapterChunker()
    documents = chunker.split_text_by_sections(full_text, source_metadata)
    print(f"Created {len(documents)} initial chunks")
    
    # Optimize chunk sizes
    optimized_documents = chunker.optimize_chunk_sizes(documents)
    print(f"Optimized to {len(optimized_documents)} final chunks")
    
    # Create FAISS vectorstore
    print("Creating embeddings and FAISS index...")
    vectorstore = FAISS.from_documents(optimized_documents, embeddings)
    
    # Try to save for future use
    try:
        os.makedirs(os.path.dirname(faiss_path), exist_ok=True)
        vectorstore.save_local(faiss_path)
        print(f"FAISS index saved to: {faiss_path}")
    except Exception as save_error:
        print(f"WARNING: Could not save FAISS index: {save_error}")
        print("   (Continuing with in-memory index)")
    
    return vectorstore