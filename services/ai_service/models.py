"""
AI service data models for QA operations and responses.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document
import operator
from typing_extensions import Annotated


@dataclass
class AIResponse:
    """Response from AI processing"""
    answer: str
    context_documents: List[Document] = field(default_factory=list)
    token_count: int = 0
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QARequest:
    """Request for QA processing"""
    question: str
    collection_key: str = "default"
    chat_history: List[BaseMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGState(BaseModel):
    """State for the RAG workflow using Pydantic"""
    messages: Annotated[List[BaseMessage], operator.add] = Field(default_factory=list)
    question: str = ""
    context: List[Document] = Field(default_factory=list)
    answer: str = ""
    chat_history: List[BaseMessage] = Field(default_factory=list)