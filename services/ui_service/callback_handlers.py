"""
Callback handlers - handles LLM callbacks for UI interactions and debugging.
Migrated from core/callbacks.py into UI service for proper architectural separation.
"""

import time
from langchain.callbacks.base import BaseCallbackHandler
from infrastructure.monitoring.logging_service import get_logger
from services.ui_service.chunks_renderer import ChunksCollector
from typing import List, Optional
from langchain_core.documents import Document


class StreamlitCallbackHandler(BaseCallbackHandler):
    """Handler pour afficher le texte en streaming dans Streamlit"""
    
    def __init__(self, placeholder, update_every=1, delay=0.01):
        self.placeholder = placeholder
        self.text = ""
        self.counter = 0
        self.update_every = update_every
        self.delay = delay
        
        # Timing metrics
        self.llm_start_time = None
        self.first_token_time = None
        self.last_update_time = None
        self.total_tokens = 0
        
        # Logger for performance metrics
        self.logger = get_logger("streaming_metrics")
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Record when LLM processing starts"""
        self.llm_start_time = time.time()
        self.logger.info("[START] LLM processing started")
    
    def on_llm_new_token(self, token, **kwargs):
        current_time = time.time()
        
        # Record first token timing
        if self.first_token_time is None:
            self.first_token_time = current_time
            if self.llm_start_time:
                ttft = (self.first_token_time - self.llm_start_time) * 1000  # Convert to ms
                self.logger.info(f"[TTFT] Time to First Token (TTFT): {ttft:.1f}ms")
                # Show TTFT in the UI temporarily
                self.placeholder.markdown(f"_First token in {ttft:.1f}ms..._")
                time.sleep(0.3)  # Brief display of TTFT
        
        self.text += token
        self.counter += 1
        self.total_tokens += 1
        
        # Update display
        if self.counter % self.update_every == 0:
            self.placeholder.markdown(self.text + "▌")
            
            # Log streaming performance every 10 tokens
            if self.counter % 10 == 0 and self.first_token_time:
                elapsed = (current_time - self.first_token_time) * 1000
                tokens_per_sec = self.counter / ((current_time - self.first_token_time) + 0.001)
                self.logger.debug(f"[STREAMING] {self.counter} tokens in {elapsed:.1f}ms ({tokens_per_sec:.1f} tok/s)")
            
            time.sleep(self.delay)
        
        self.last_update_time = current_time
    
    def on_llm_end(self, *args, **kwargs):
        end_time = time.time()
        
        # Calculate final metrics
        if self.llm_start_time and self.first_token_time:
            total_time = (end_time - self.llm_start_time) * 1000
            ttft = (self.first_token_time - self.llm_start_time) * 1000
            generation_time = (end_time - self.first_token_time) * 1000
            avg_tokens_per_sec = self.total_tokens / ((end_time - self.first_token_time) + 0.001)
            
            self.logger.info(f"LLM Response Complete:")
            self.logger.info(f"   Total tokens: {self.total_tokens}")
            self.logger.info(f"   Time to First Token: {ttft:.1f}ms")
            self.logger.info(f"   Generation time: {generation_time:.1f}ms")
            self.logger.info(f"   Total time: {total_time:.1f}ms")
            self.logger.info(f"   Average speed: {avg_tokens_per_sec:.1f} tokens/sec")
        
        # Display final response without cursor
        self.placeholder.markdown(self.text)


class RetrievalCallbackHandler(BaseCallbackHandler):
    """Handler pour afficher les chunks récupérés dans la console et stocker pour l'UI"""
    
    def __init__(self, memory=None, chunks_collector: Optional[ChunksCollector] = None):
        self.memory = memory
        self.original_question = None
        self.chunks_collector = chunks_collector or ChunksCollector()
        self.retrieved_documents: List[Document] = []
    
    def on_retriever_start(self, serialized, query, **kwargs):
        # Stocker la question originale pour comparaison
        self.original_question = query
        # Stocker la question dans le collector pour l'affichage UI
        self.chunks_collector.set_question(query)
        
        print(f"\nRecherche de chunks pour la question: '{query}'")
        print("=" * 80)
        
        # Afficher la mémoire de conversation si disponible
        if self.memory and hasattr(self.memory, 'memory') and hasattr(self.memory.memory, 'chat_memory'):
            chat_memory = self.memory.memory.chat_memory
            messages = chat_memory.messages
            
            if messages:
                print(f"\nMemoire de conversation ({len(messages)} messages):")
                print("=" * 80)
                for i, msg in enumerate(messages, 1):
                    role = "Utilisateur" if msg.type == "human" else "Assistant"
                    print(f"\n{i}. {role}:")
                    print("-" * 40)
                    print(msg.content)
                    print("-" * 40)
                    print(f"Longueur: {len(msg.content)} caracteres")
                print("=" * 80)
            else:
                print("\nMemoire de conversation: (vide)")
        else:
            print("\nMemoire de conversation: (non disponible)")
    
    def on_retriever_end(self, documents, **kwargs):
        # Stocker les documents pour l'affichage UI
        self.retrieved_documents = documents.copy()
        self.chunks_collector.add_chunks(documents)
        
        print(f"{len(documents)} chunks recuperes:")
        print("-" * 80)
        for i, doc in enumerate(documents, 1):
            print(f"\nChunk {i}:")
            print(f"   Source: {getattr(doc.metadata, 'source', 'N/A')}")
            print(f"   Page: {getattr(doc.metadata, 'page', 'N/A')}")
            print(f"   Contenu: {doc.page_content[:200]}...")
            if len(doc.page_content) > 200:
                print(f"   (tronque, longueur totale: {len(doc.page_content)} caracteres)")
            print("-" * 40)
        print("=" * 80)
    
    def on_chain_start(self, serialized, inputs, **kwargs):
        """Affiche le prompt utilisé par le système"""
        print(f"\nPrompt utilise par le systeme:")
        print("=" * 80)
        
        # Chercher le prompt dans les inputs
        prompt_text = ""
        
        # Handle both dictionary inputs and RAGState objects
        try:
            # If inputs is a RAGState object, extract the question
            if hasattr(inputs, 'question'):
                prompt_text = inputs.question
            # If inputs is a dictionary
            elif isinstance(inputs, dict):
                # Essayer différentes façons de récupérer le prompt
                if "question" in inputs:
                    question = inputs["question"]
                    # Si c'est une chaîne simple
                    if isinstance(question, str):
                        prompt_text = question
                    # Si c'est une liste de messages (format chat)
                    elif isinstance(question, list) and len(question) > 0:
                        # Prendre le dernier message de l'utilisateur
                        last_message = question[-1]
                        if hasattr(last_message, 'content'):
                            prompt_text = last_message.content
                        elif isinstance(last_message, dict) and 'content' in last_message:
                            prompt_text = last_message['content']
                
                # Si on n'a pas trouvé dans "question", chercher dans d'autres clés possibles
                if not prompt_text:
                    for key in ["input", "query", "text", "prompt"]:
                        if key in inputs:
                            value = inputs[key]
                            if isinstance(value, str):
                                prompt_text = value
                                break
                            elif isinstance(value, list) and len(value) > 0:
                                last_item = value[-1]
                                if hasattr(last_item, 'content'):
                                    prompt_text = last_item.content
                                    break
                                elif isinstance(last_item, dict) and 'content' in last_item:
                                    prompt_text = last_item['content']
                                    break
        except Exception as e:
            print(f"Error processing inputs: {e}")
            prompt_text = ""
        
        # Vérifier si la question a été reformulée
        if self.original_question and prompt_text and prompt_text != self.original_question:
            print(f"ATTENTION: Question reformulee!")
            print(f"   Question originale: '{self.original_question}'")
            print(f"   Question reformulee: '{prompt_text}'")
            print("-" * 40)
        
        # Afficher les 500 premiers caractères
        if prompt_text:
            truncated_prompt = prompt_text[:500]
            print(f"Question utilisateur (500 premiers caracteres):")
            print("-" * 40)
            print(truncated_prompt)
            if len(prompt_text) > 500:
                print(f"... (tronque, longueur totale: {len(prompt_text)} caracteres)")
            print("-" * 40)
        else:
            print("Impossible de recuperer le prompt")
            try:
                available_keys = list(inputs.keys()) if hasattr(inputs, 'keys') else str(type(inputs))
                print("Type/cles disponibles dans inputs:", available_keys)
            except:
                print("Type d'inputs:", type(inputs))
        
        print("=" * 80)
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Affiche le prompt système complet utilisé par le LLM"""
        print(f"\nPrompt systeme complet utilise par le LLM:")
        print("=" * 80)
        
        if prompts and len(prompts) > 0:
            # Le premier prompt contient généralement le prompt système complet
            system_prompt = prompts[0]
            
            # Afficher les 1000 premiers caractères du prompt système
            truncated_system = system_prompt[:1000]
            print(f"Prompt systeme (1000 premiers caracteres):")
            print("-" * 40)
            print(truncated_system)
            if len(system_prompt) > 1000:
                print(f"... (tronque, longueur totale: {len(system_prompt)} caracteres)")
            print("-" * 40)
            
            # Si il y a plusieurs prompts, afficher le nombre
            if len(prompts) > 1:
                print(f"Nombre total de prompts: {len(prompts)}")
        else:
            print("Aucun prompt systeme trouve")
        
        print("=" * 80)
    
    def get_chunks_collector(self) -> ChunksCollector:
        """Get the chunks collector for UI display"""
        return self.chunks_collector
    
    def get_retrieved_documents(self) -> List[Document]:
        """Get the last retrieved documents"""
        return self.retrieved_documents.copy()


# Service convenience functions
def get_streamlit_callback_handler(placeholder, update_every=1, delay=0.01):
    """Get a Streamlit callback handler instance"""
    return StreamlitCallbackHandler(placeholder, update_every, delay)


def get_retrieval_callback_handler(memory=None, chunks_collector=None):
    """Get a retrieval callback handler instance"""
    return RetrievalCallbackHandler(memory, chunks_collector)