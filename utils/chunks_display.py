"""
Utility module for displaying retrieved chunks in a collapsible component
"""

import streamlit as st
from typing import List, Optional
from langchain_core.documents import Document


def render_chunks_component(documents: List[Document], question: str = "") -> None:
    """
    Render a collapsible component showing retrieved chunks
    
    Args:
        documents: List of retrieved documents/chunks
        question: The original question that was asked
    """
    if not documents:
        return
    
    # Create expander for chunks display
    with st.expander(f"📚 Sources consultées ({len(documents)} chunks)", expanded=False):
        st.markdown("""
        <style>
        .chunk-container {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 12px;
            margin: 8px 0;
            background-color: #f8f9fa;
        }
        .chunk-header {
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
            font-size: 14px;
        }
        .chunk-metadata {
            font-size: 12px;
            color: #6c757d;
            margin-bottom: 8px;
        }
        .chunk-content {
            font-size: 13px;
            line-height: 1.4;
            color: #495057;
            max-height: 200px;
            overflow-y: auto;
            border-left: 3px solid #007bff;
            padding-left: 10px;
            background-color: white;
            border-radius: 4px;
            padding: 8px;
        }
        .chunk-stats {
            font-size: 11px;
            color: #868e96;
            margin-top: 6px;
            font-style: italic;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if question:
            st.markdown(f"**Question :** *{question}*")
            st.markdown("---")
        
        for i, doc in enumerate(documents, 1):
            # Extract metadata
            metadata = getattr(doc, 'metadata', {})
            source = metadata.get('source', 'Source inconnue')
            page = metadata.get('page', 'N/A')
            section_title = metadata.get('section_title', '')
            section_type = metadata.get('section_type', '')
            chunk_size = metadata.get('chunk_size', len(doc.page_content))
            
            # Create chunk container
            st.markdown(f"""
            <div class="chunk-container">
                <div class="chunk-header">
                    📄 Chunk {i}
                </div>
                <div class="chunk-metadata">
                    <strong>Source:</strong> {source}<br>
                    <strong>Page:</strong> {page}<br>
                    {"<strong>Section:</strong> " + section_title + "<br>" if section_title else ""}
                    {"<strong>Type:</strong> " + section_type + "<br>" if section_type else ""}
                </div>
                <div class="chunk-content">
                    {doc.page_content}
                </div>
                <div class="chunk-stats">
                    Longueur: {chunk_size} caractères
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Add summary statistics
        total_chars = sum(len(doc.page_content) for doc in documents)
        avg_chars = total_chars // len(documents) if documents else 0
        
        st.markdown("---")
        st.markdown(f"""
        **📊 Statistiques:**
        - **Nombre de chunks:** {len(documents)}
        - **Caractères totaux:** {total_chars:,}
        - **Longueur moyenne:** {avg_chars:,} caractères
        """)


def render_simple_chunks_list(documents: List[Document]) -> None:
    """
    Render a simple list of chunks (fallback for when full component doesn't work)
    
    Args:
        documents: List of retrieved documents/chunks
    """
    if not documents:
        return
    
    with st.expander(f"📚 {len(documents)} sources consultées", expanded=False):
        for i, doc in enumerate(documents, 1):
            st.write(f"**Chunk {i}:**")
            
            # Show metadata if available
            if hasattr(doc, 'metadata') and doc.metadata:
                metadata = doc.metadata
                if 'source' in metadata:
                    st.write(f"*Source: {metadata['source']}*")
                if 'page' in metadata:
                    st.write(f"*Page: {metadata['page']}*")
            
            # Show content preview
            content = doc.page_content
            if len(content) > 300:
                st.write(f"{content[:300]}...")
                st.write(f"*({len(content)} caractères au total)*")
            else:
                st.write(content)
            
            st.write("---")


class ChunksCollector:
    """
    Helper class to collect and store chunks from callback handlers
    """
    
    def __init__(self):
        self.chunks: List[Document] = []
        self.question: str = ""
    
    def set_question(self, question: str):
        """Set the current question"""
        self.question = question
    
    def add_chunks(self, documents: List[Document]):
        """Add retrieved chunks"""
        self.chunks = documents.copy()
    
    def clear(self):
        """Clear stored chunks and question"""
        self.chunks = []
        self.question = ""
    
    def render_if_available(self):
        """Render chunks component if chunks are available"""
        if self.chunks:
            render_chunks_component(self.chunks, self.question)
    
    def has_chunks(self) -> bool:
        """Check if chunks are available"""
        return len(self.chunks) > 0
    
    def get_chunk_count(self) -> int:
        """Get number of stored chunks"""
        return len(self.chunks)