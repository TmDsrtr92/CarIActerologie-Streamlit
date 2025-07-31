from typing import Dict, Any, List, Optional, Callable
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
import operator
from typing_extensions import Annotated

from core.llm_setup import setup_llm, setup_retriever
from core.langgraph_memory import LangGraphMemoryManager
from config.prompts import get_qa_prompt
import re


class RAGState(BaseModel):
    """State for the RAG workflow"""
    messages: Annotated[List[BaseMessage], operator.add] = Field(default_factory=list)
    question: str = ""
    context: List[Document] = Field(default_factory=list)
    answer: str = ""
    chat_history: List[BaseMessage] = Field(default_factory=list)


def clean_response(response: str, user_question: str) -> str:
    """Clean the response to remove any repetition of the user's question"""
    question_clean = re.escape(user_question.strip())
    pattern = f"^{question_clean}[\\s\\n]*"
    cleaned = re.sub(pattern, "", response.strip(), flags=re.IGNORECASE | re.MULTILINE)
    
    prefixes_to_remove = [
        r"^.*question.*:.*\n*",
        r"^.*demande.*:.*\n*",
        r"^.*vous demandez.*:.*\n*",
        r"^.*concernant votre question.*:.*\n*"
    ]
    
    for prefix in prefixes_to_remove:
        cleaned = re.sub(prefix, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    
    return cleaned.strip()


class LangGraphRAGChain:
    """
    LangGraph-based RAG chain that replaces ConversationalRetrievalChain
    with enhanced memory management and workflow control
    """
    
    def __init__(self, memory_manager: LangGraphMemoryManager, collection_key: str = None, 
                 prompt_name: str = "caracterologie_qa", prompt_version: int = None):
        """
        Initialize LangGraph RAG chain
        
        Args:
            memory_manager: LangGraph memory manager instance
            collection_key: Vector store collection key
            prompt_name: Prompt template name
            prompt_version: Prompt version
        """
        self.memory_manager = memory_manager
        self.llm = setup_llm()
        self.retriever = setup_retriever(collection_key)
        self.prompt_name = prompt_name
        self.prompt_version = prompt_version
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for RAG"""
        workflow = StateGraph(RAGState)
        
        # Create wrapper functions that can access the config
        def generate_answer_wrapper(state: RAGState):
            # Access the stored config
            config = getattr(self, '_current_config', None)
            return self._generate_answer(state, config)
        
        # Add nodes
        workflow.add_node("retrieve_context", self._retrieve_context)
        workflow.add_node("contextualize_question", self._contextualize_question)
        workflow.add_node("generate_answer", generate_answer_wrapper)
        
        # Add edges
        workflow.add_edge(START, "retrieve_context")
        workflow.add_edge("retrieve_context", "contextualize_question")
        workflow.add_edge("contextualize_question", "generate_answer")
        workflow.add_edge("generate_answer", END)
        
        return workflow
    
    def _retrieve_context(self, state: RAGState) -> Dict[str, Any]:
        """Retrieve relevant documents based on the question"""
        print(f"\nRecherche de chunks pour la question: '{state.question}'")
        print("=" * 80)
        
        # Use the original question for retrieval (before contextualization)
        docs = self.retriever.invoke(state.question)
        
        print(f"{len(docs)} chunks recuperes:")
        print("-" * 80)
        for i, doc in enumerate(docs, 1):
            print(f"\nChunk {i}:")
            if hasattr(doc, 'metadata'):
                print(f"   Source: {doc.metadata.get('source', 'N/A')}")
                print(f"   Page: {doc.metadata.get('page', 'N/A')}")
            content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            print(f"   Contenu: {content[:200]}...")
            if len(content) > 200:
                print(f"   (tronque, longueur totale: {len(content)} caracteres)")
            print("-" * 40)
        print("=" * 80)
        
        return {"context": docs}
    
    def _contextualize_question(self, state: RAGState) -> Dict[str, Any]:
        """Contextualize the question using chat history if needed"""
        # If no chat history, return question as-is
        if not state.chat_history:
            return {"question": state.question}
        
        # Create contextualization prompt
        contextualize_prompt = """Étant donné un historique de conversation et la dernière question de l'utilisateur qui pourrait faire référence au contexte de l'historique de conversation, formulez une question autonome qui peut être comprise sans l'historique de conversation. Ne répondez PAS à la question, reformulez-la uniquement si nécessaire, sinon retournez-la telle quelle.

Historique de conversation:
{chat_history}

Question: {question}

Question contextualisée:"""
        
        # Format chat history
        history_text = ""
        for msg in state.chat_history[-6:]:  # Last 6 messages for context
            role = "Utilisateur" if isinstance(msg, HumanMessage) else "Assistant"
            history_text += f"{role}: {msg.content}\n"
        
        prompt = contextualize_prompt.format(
            chat_history=history_text,
            question=state.question
        )
        
        # Get contextualized question
        contextualized_question = self.llm.invoke(prompt).content
        
        return {"question": contextualized_question}
    
    def _generate_answer(self, state: RAGState, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate answer using retrieved context and chat history"""
        # Display memory content
        if state.chat_history:
            print(f"\nMemoire de conversation ({len(state.chat_history)} messages):")
            print("=" * 80)
            for i, msg in enumerate(state.chat_history, 1):
                role = "Utilisateur" if isinstance(msg, HumanMessage) else "Assistant"
                print(f"\n{i}. {role}:")
                print("-" * 40)
                print(msg.content)
                print("-" * 40)
                print(f"Longueur: {len(msg.content)} caracteres")
            print("=" * 80)
        else:
            print("\nMemoire de conversation: (vide)")
        
        # Create enhanced prompt template
        enhanced_template = """Tu es un assistant caractérologue expert, à la fois pédagogue et curieux. Ton rôle est de faire découvrir la caractérologie — la science des types de caractère — de manière à la fois précise, vivante et accessible.

Tu réponds aux questions des utilisateurs en t'appuyant rigoureusement sur les connaissances fournies par la base de données intégrée, notamment les travaux de René Le Senne et les typologies reconnues (émotivité, activité, retentissement). Si une réponse n'est pas disponible dans les sources, tu l'indiques honnêtement.

Tu adaptes ton langage et ton niveau d'explication selon le profil de l'utilisateur (novice ou initié). Tu cherches à l'accompagner dans sa compréhension de la caractérologie. S'il pose des questions simples ou générales, tu proposes des compléments pertinents pour approfondir.

Tu es capable d'orienter la conversation de façon naturelle, en suggérant des sujets liés à ce que l'utilisateur vient de dire. Par exemple, tu peux l'inviter à découvrir un autre type psychologique, une dimension caractérologique ou une mise en application concrète.

Tu peux aussi poser des questions ouvertes à l'utilisateur s'il semble curieux mais ne sait pas par où commencer.

Sois clair, structuré et rigoureux. Utilise des exemples concrets si cela peut aider à mieux comprendre. Ton objectif : éveiller l'intérêt, transmettre un savoir solide, et guider pas à pas dans l'univers de la caractérologie.

Adapte la longueur de ta réponse à la complexité de la question : réponse courte pour une question simple, plus développée pour une question complexe ou une demande d'explication détaillée.

IMPORTANT - Utilise les informations suivantes dans cet ordre de priorité :

1. HISTORIQUE DE CONVERSATION (priorité absolue pour comprendre les références comme "ça", "ils", "cette notion") :
{chat_history}

2. CONTEXTE DOCUMENTAIRE (sources pour informations factuelles) :
{context}

3. QUESTION ACTUELLE :
{input}"""
        
        # Format chat history for prompt
        history_text = ""
        if state.chat_history:
            for msg in state.chat_history:
                role = "Utilisateur" if isinstance(msg, HumanMessage) else "Assistant"
                history_text += f"{role}: {msg.content}\n"
        else:
            history_text = "(Aucun historique)"
        
        # Format context
        context_text = ""
        for doc in state.context:
            context_text += doc.page_content + "\n\n"
        
        # Create final prompt
        final_prompt = enhanced_template.format(
            chat_history=history_text,
            context=context_text,
            input=state.question
        )
        
        print(f"\nPrompt systeme utilise:")
        print("=" * 80)
        print("Prompt avec historique de conversation integre")
        print("Priorite donnee a l'historique pour les references")
        print("=" * 80)
        
        # Generate response with streaming support
        # Use the passed config directly for streaming
        if config and "callbacks" in config:
            print("Streaming callbacks detected - using real streaming")
            response = self.llm.invoke(final_prompt, config=config)
        else:
            response = self.llm.invoke(final_prompt)
            
        answer = response.content
        
        return {"answer": answer}
    
    def invoke(self, inputs: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Invoke the RAG chain with memory management
        
        Args:
            inputs: Input dictionary containing "question"
            config: Optional configuration for callbacks
            
        Returns:
            Dictionary containing "answer"
        """
        question = inputs["question"]
        thread_id = self.memory_manager.get_current_thread()
        
        # Get chat history from memory manager
        chat_history = self.memory_manager.get_chat_history()
        
        # Prepare initial state
        initial_state = RAGState(
            question=question,
            chat_history=chat_history
        )
        
        # Store config for use in workflow nodes
        self._current_config = config
        
        # Run the workflow with config
        try:
            if config:
                final_state = self.app.invoke(initial_state, config=config)
            else:
                final_state = self.app.invoke(initial_state)
        finally:
            # Clean up stored config
            self._current_config = None
        
        answer = final_state["answer"]
        
        # Save context to memory
        self.memory_manager.save_context(
            {"question": question},
            {"answer": answer}
        )
        
        return {"answer": answer}


def setup_langgraph_qa_chain(memory_manager: LangGraphMemoryManager, collection_key: str = None, 
                            prompt_name: str = "caracterologie_qa", prompt_version: int = None) -> LangGraphRAGChain:
    """
    Set up a LangGraph-based RAG chain with memory management
    
    Args:
        memory_manager: LangGraph memory manager instance
        collection_key: Vector store collection key
        prompt_name: Prompt template name
        prompt_version: Prompt version
        
    Returns:
        LangGraphRAGChain instance
    """
    return LangGraphRAGChain(memory_manager, collection_key, prompt_name, prompt_version)


# Backward compatibility function
def setup_qa_chain_with_memory(memory, collection_key: str = None, prompt_name: str = "caracterologie_qa", prompt_version: int = None):
    """
    Setup QA chain with memory - now only supports LangGraph memory system
    """
    # Check if it's the new LangGraph memory manager wrapper
    if hasattr(memory, 'manager') and hasattr(memory.manager, '_is_langgraph_memory'):
        return setup_langgraph_qa_chain(memory.manager, collection_key, prompt_name, prompt_version)
    
    # Check if it's a direct LangGraph memory manager
    if hasattr(memory, '_is_langgraph_memory'):
        return setup_langgraph_qa_chain(memory, collection_key, prompt_name, prompt_version)
    
    # If we get here, something is wrong with the memory system
    raise ValueError(f"Unsupported memory type: {type(memory)}. Only LangGraph memory managers are supported.")