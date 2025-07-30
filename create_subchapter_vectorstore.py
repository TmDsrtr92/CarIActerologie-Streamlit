from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
import os
import re
from datetime import datetime
from typing import List, Tuple

# Configuration
PDF_PATH = "documents/traite_caracterologie.pdf"
PERSIST_DIRECTORY = "./index_stores"
COLLECTION_NAME = "traite_subchapters"

# Chunking parameters
MIN_CHUNK_SIZE = 500  # Merge chunks smaller than this
MAX_CHUNK_SIZE = 8000  # Split chunks larger than this
TARGET_CHUNK_SIZE = 3000  # Ideal chunk size

def get_openai_api_key():
    """Get OpenAI API key from environment or streamlit secrets"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            raise RuntimeError("OPENAI_API_KEY not found in environment variables or streamlit.secrets")
    return api_key

class SubChapterChunker:
    """Custom chunker that splits text based on numbered sections"""
    
    def __init__(self):
        # Primary pattern: numbered sections (1. Title)
        self.numbered_pattern = re.compile(r'^(\s*)(\d+)\.\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{10,100})', re.MULTILINE)
        # Secondary pattern: roman numerals (I. Title)
        self.roman_pattern = re.compile(r'^(\s*)([IVX]+)\.\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{10,100})', re.MULTILINE)
        # Major headings
        self.major_pattern = re.compile(r'^(\s*)(CHAPITRE|PARTIE|SECTION|INTRODUCTION|PRÉFACE|CONCLUSION)\s*([^\n]*)', re.MULTILINE)
    
    def find_section_breaks(self, text: str) -> List[Tuple[int, str, str]]:
        """Find all section breaks in the text"""
        breaks = []
        
        # Find numbered sections
        for match in self.numbered_pattern.finditer(text):
            start_pos = match.start()
            section_num = match.group(2)
            title = match.group(3).strip()
            breaks.append((start_pos, f"Section {section_num}", title))
        
        # Find roman numeral sections
        for match in self.roman_pattern.finditer(text):
            start_pos = match.start()
            roman_num = match.group(2)
            title = match.group(3).strip()
            breaks.append((start_pos, f"Chapter {roman_num}", title))
        
        # Find major headings
        for match in self.major_pattern.finditer(text):
            start_pos = match.start()
            heading_type = match.group(2)
            title = match.group(3).strip() if match.group(3) else ""
            breaks.append((start_pos, heading_type, title))
        
        # Sort by position
        breaks.sort(key=lambda x: x[0])
        return breaks
    
    def split_text_by_sections(self, text: str, source_metadata: dict = None) -> List[Document]:
        """Split text into documents based on section breaks"""
        breaks = self.find_section_breaks(text)
        
        if not breaks:
            # Fallback: return entire text as one document
            return [Document(
                page_content=text,
                metadata={
                    "section_type": "full_document",
                    "section_title": "Complete Document",
                    "chunk_size": len(text),
                    **(source_metadata or {})
                }
            )]
        
        documents = []
        
        for i, (start_pos, section_type, title) in enumerate(breaks):
            # Determine end position
            if i + 1 < len(breaks):
                end_pos = breaks[i + 1][0]
            else:
                end_pos = len(text)
            
            # Extract section content
            section_content = text[start_pos:end_pos].strip()
            
            if section_content:
                metadata = {
                    "section_type": section_type,
                    "section_title": title,
                    "section_number": i + 1,
                    "chunk_size": len(section_content),
                    **(source_metadata or {})
                }
                
                documents.append(Document(
                    page_content=section_content,
                    metadata=metadata
                ))
        
        return documents
    
    def optimize_chunk_sizes(self, documents: List[Document]) -> List[Document]:
        """Optimize chunk sizes by merging small chunks and splitting large ones"""
        optimized = []
        i = 0
        
        while i < len(documents):
            current_doc = documents[i]
            current_size = len(current_doc.page_content)
            
            # If chunk is too small, try to merge with next chunks
            if current_size < MIN_CHUNK_SIZE and i + 1 < len(documents):
                merged_content = current_doc.page_content
                merged_metadata = current_doc.metadata.copy()
                merged_sections = [merged_metadata.get("section_title", "")]
                
                j = i + 1
                while j < len(documents) and len(merged_content) < TARGET_CHUNK_SIZE:
                    next_doc = documents[j]
                    if len(merged_content) + len(next_doc.page_content) <= MAX_CHUNK_SIZE:
                        merged_content += "\n\n" + next_doc.page_content
                        merged_sections.append(next_doc.metadata.get("section_title", ""))
                        j += 1
                    else:
                        break
                
                # Update metadata for merged chunk
                merged_metadata.update({
                    "section_title": " | ".join(filter(None, merged_sections)),
                    "chunk_size": len(merged_content),
                    "merged_sections": len(merged_sections)
                })
                
                optimized.append(Document(page_content=merged_content, metadata=merged_metadata))
                i = j
            
            # If chunk is too large, split it at paragraph boundaries
            elif current_size > MAX_CHUNK_SIZE:
                split_docs = self.split_large_chunk(current_doc)
                optimized.extend(split_docs)
                i += 1
            
            # Chunk is good size, keep as is
            else:
                optimized.append(current_doc)
                i += 1
        
        return optimized
    
    def split_large_chunk(self, document: Document) -> List[Document]:
        """Split a large chunk at paragraph boundaries"""
        content = document.page_content
        paragraphs = content.split('\n\n')
        
        if len(paragraphs) <= 1:
            # Can't split further, return as is
            return [document]
        
        chunks = []
        current_chunk = ""
        chunk_num = 1
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 <= MAX_CHUNK_SIZE:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    # Save current chunk
                    metadata = document.metadata.copy()
                    metadata.update({
                        "chunk_size": len(current_chunk),
                        "split_part": chunk_num,
                        "section_title": f"{metadata.get('section_title', '')} (Part {chunk_num})"
                    })
                    chunks.append(Document(page_content=current_chunk, metadata=metadata))
                    chunk_num += 1
                
                current_chunk = paragraph
        
        # Add final chunk
        if current_chunk:
            metadata = document.metadata.copy()
            metadata.update({
                "chunk_size": len(current_chunk),
                "split_part": chunk_num,
                "section_title": f"{metadata.get('section_title', '')} (Part {chunk_num})"
            })
            chunks.append(Document(page_content=current_chunk, metadata=metadata))
        
        return chunks

def load_and_chunk_pdf() -> List[Document]:
    """Load PDF and create sub-chapter chunks"""
    print(f"Loading PDF from {PDF_PATH}...")
    
    # Load PDF
    loader = PyPDFLoader(PDF_PATH)
    pages = loader.load()
    
    print(f"Loaded {len(pages)} pages from PDF")
    
    # Combine all pages into one text
    full_text = "\n\n".join([page.page_content for page in pages])
    
    # Create metadata from first page
    source_metadata = {
        "source": PDF_PATH,
        "total_pages": len(pages),
        "processing_date": datetime.now().isoformat()
    }
    
    # Initialize chunker and process text
    chunker = SubChapterChunker()
    
    print("Splitting text by sections...")
    documents = chunker.split_text_by_sections(full_text, source_metadata)
    print(f"Created {len(documents)} initial chunks")
    
    print("Optimizing chunk sizes...")
    optimized_documents = chunker.optimize_chunk_sizes(documents)
    print(f"Optimized to {len(optimized_documents)} final chunks")
    
    # Print statistics
    sizes = [len(doc.page_content) for doc in optimized_documents]
    print(f"Chunk size statistics:")
    print(f"  Min: {min(sizes)} chars")
    print(f"  Max: {max(sizes)} chars")
    print(f"  Average: {sum(sizes) // len(sizes)} chars")
    print(f"  Total: {sum(sizes)} chars")
    
    return optimized_documents

def create_vectorstore(documents: List[Document]):
    """Create new ChromaDB collection with sub-chapter chunks"""
    print(f"Creating embeddings for {len(documents)} documents...")
    
    # Setup embeddings
    api_key = get_openai_api_key()
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    
    # Create empty vectorstore first
    print(f"Creating Chroma vectorstore with collection '{COLLECTION_NAME}'...")
    vectorstore = Chroma(
        persist_directory=PERSIST_DIRECTORY,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings
    )
    
    # Process documents in batches to avoid token limits
    batch_size = 20  # Process 20 documents at a time
    total_batches = (len(documents) + batch_size - 1) // batch_size
    
    for i in range(0, len(documents), batch_size):
        batch_num = (i // batch_size) + 1
        batch = documents[i:i + batch_size]
        
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)...")
        
        try:
            # Add batch to vectorstore
            texts = [doc.page_content for doc in batch]
            metadatas = [doc.metadata for doc in batch]
            
            vectorstore.add_texts(texts=texts, metadatas=metadatas)
            
        except Exception as e:
            print(f"Error processing batch {batch_num}: {e}")
            # Try smaller batch size
            if len(batch) > 1:
                print(f"Retrying with smaller chunks...")
                for doc in batch:
                    try:
                        vectorstore.add_texts(
                            texts=[doc.page_content], 
                            metadatas=[doc.metadata]
                        )
                    except Exception as e2:
                        print(f"Failed to add document: {e2}")
                        print(f"Document size: {len(doc.page_content)} chars")
    
    vectorstore.persist()
    print(f"Vectorstore created and persisted to {PERSIST_DIRECTORY}")
    
    return vectorstore

def main():
    """Main execution function"""
    print("=== PDF Sub-Chapter Vectorstore Creation ===")
    print(f"PDF: {PDF_PATH}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Persist directory: {PERSIST_DIRECTORY}")
    print()
    
    try:
        # Load and chunk PDF
        documents = load_and_chunk_pdf()
        
        # Create vectorstore
        vectorstore = create_vectorstore(documents)
        
        print()
        print("=== SUCCESS ===")
        print(f"Created vectorstore with {len(documents)} sub-chapter chunks")
        print(f"To use this collection, update config/settings.py:")
        print(f"  'collection_name': '{COLLECTION_NAME}'")
        
        # Test retrieval
        print("\n=== Testing retrieval ===")
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        test_query = "émotivité"
        results = retriever.get_relevant_documents(test_query)
        
        print(f"Test query: '{test_query}'")
        print(f"Retrieved {len(results)} documents:")
        for i, doc in enumerate(results, 1):
            title = doc.metadata.get("section_title", "Unknown")[:50]
            size = doc.metadata.get("chunk_size", len(doc.page_content))
            print(f"  {i}. {title}... ({size} chars)")
        
    except Exception as e:
        print(f"ERROR: {e}")
        raise

if __name__ == "__main__":
    main()