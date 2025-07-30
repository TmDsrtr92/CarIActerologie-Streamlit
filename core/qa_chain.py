from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.retrieval import create_retrieval_chain
from core.llm_setup import setup_llm, setup_retriever
from config.prompts import get_qa_prompt
import re

def clean_response(response: str, user_question: str) -> str:
    """
    Clean the response to remove any repetition of the user's question
    """
    # Remove the user's question if it appears at the beginning of the response
    question_clean = re.escape(user_question.strip())
    pattern = f"^{question_clean}[\\s\\n]*"
    cleaned = re.sub(pattern, "", response.strip(), flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove common prefixes that might repeat the question
    prefixes_to_remove = [
        r"^.*question.*:.*\n*",
        r"^.*demande.*:.*\n*",
        r"^.*vous demandez.*:.*\n*",
        r"^.*concernant votre question.*:.*\n*"
    ]
    
    for prefix in prefixes_to_remove:
        cleaned = re.sub(prefix, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    
    return cleaned.strip()


def setup_qa_chain_with_memory(memory, collection_key: str = None, prompt_name: str = "caracterologie_qa", prompt_version: int = None):
    """Set up a modern RAG chain with proper conversation history integration"""
    llm = setup_llm()
    retriever = setup_retriever(collection_key)
    
    # Create contextualize prompt that includes chat history
    contextualize_q_system_prompt = """Étant donné un historique de conversation et la dernière question de l'utilisateur qui pourrait faire référence au contexte de l'historique de conversation, formulez une question autonome qui peut être comprise sans l'historique de conversation. Ne répondez PAS à la question, reformulez-la uniquement si nécessaire, sinon retournez-la telle quelle."""
    
    contextualize_q_prompt = PromptTemplate.from_template(
        contextualize_q_system_prompt + "\n\nHistorique de conversation:\n{chat_history}\n\nQuestion: {input}"
    )
    
    # Create history-aware retriever
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )
    
    # Create a new prompt template that includes chat history
    # Since the original template uses {context} and {question}, we need to adapt it
    base_prompt = get_qa_prompt(prompt_name, prompt_version)
    base_template = base_prompt.template
    
    # Debug: print the template to see what we're working with
    print(f"DEBUG - Original template: {base_template[:200]}...")
    
    # Create a completely new template that works with the new chain format
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

    enhanced_prompt = PromptTemplate(
        template=enhanced_template,
        input_variables=["context", "input", "chat_history"]
    )
    
    # Create document chain
    question_answer_chain = create_stuff_documents_chain(llm, enhanced_prompt)
    
    # Create RAG chain
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    # Wrap in a class that maintains memory compatibility
    class MemoryAwareRAGChain:
        def __init__(self, rag_chain, memory):
            self.rag_chain = rag_chain
            self.memory = memory
            self.stream_handler = None
        
        def invoke(self, inputs, config=None):
            # Get chat history from memory
            chat_history = self.memory.get_chat_history()
            
            # Print debug info for console logging
            print(f"\n🔍 RECHERCHE DE CHUNKS pour la question: '{inputs['question']}'")
            print("=" * 80)
            
            # Display memory content
            if chat_history:
                print(f"\n💬 MÉMOIRE DE CONVERSATION ({len(chat_history)} messages):")
                print("=" * 80)
                for i, msg in enumerate(chat_history, 1):
                    role = "👤 Utilisateur" if msg.type == "human" else "🤖 Assistant"
                    print(f"\n{i}. {role}:")
                    print("-" * 40)
                    print(msg.content)
                    print("-" * 40)
                    print(f"📊 Longueur: {len(msg.content)} caractères")
                print("=" * 80)
            else:
                print("\n💬 MÉMOIRE DE CONVERSATION: (vide)")
            
            # Prepare inputs for the RAG chain
            rag_inputs = {
                "input": inputs["question"],
                "chat_history": chat_history
            }
            
            # Extract and store streaming handler separately to avoid threading issues
            stream_handler = None
            safe_callbacks = []
            
            if config and "callbacks" in config:
                for cb in config["callbacks"]:
                    if hasattr(cb, '__class__') and 'StreamlitCallbackHandler' in cb.__class__.__name__:
                        stream_handler = cb
                    elif hasattr(cb, '__class__') and 'Streamlit' not in cb.__class__.__name__:
                        safe_callbacks.append(cb)
                
                config = {**config, "callbacks": safe_callbacks}
            
            # Invoke the RAG chain (without problematic streaming callbacks)
            if stream_handler:
                # For streaming, we'll simulate the streaming by chunking the response
                result = self.rag_chain.invoke(rag_inputs, config=config)
                answer = result["answer"]
                
                # Simulate streaming by updating the placeholder progressively
                import time
                words = answer.split()
                displayed_text = ""
                
                for i, word in enumerate(words):
                    displayed_text += word + " "
                    if i % 3 == 0:  # Update every 3 words
                        try:
                            stream_handler.placeholder.markdown(displayed_text + "▌")
                            time.sleep(0.05)
                        except:
                            # If streaming fails, just continue
                            pass
                
                # Final update without cursor
                try:
                    stream_handler.placeholder.markdown(displayed_text.strip())
                except:
                    pass
            else:
                # No streaming, just invoke normally
                result = self.rag_chain.invoke(rag_inputs, config=config)
            
            # Print retrieved documents
            if "context" in result:
                docs = result["context"] if isinstance(result["context"], list) else []
                print(f"📄 {len(docs)} chunks récupérés:")
                print("-" * 80)
                for i, doc in enumerate(docs, 1):
                    print(f"\n📄 Chunk {i}:")
                    if hasattr(doc, 'metadata'):
                        print(f"   Source: {doc.metadata.get('source', 'N/A')}")
                        print(f"   Page: {doc.metadata.get('page', 'N/A')}")
                    content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                    print(f"   Contenu: {content[:200]}...")
                    if len(content) > 200:
                        print(f"   (tronqué, longueur totale: {len(content)} caractères)")
                    print("-" * 40)
                print("=" * 80)
            
            # Print system prompt info
            print(f"\n🤖 PROMPT SYSTÈME UTILISÉ:")
            print("=" * 80)
            print("✅ Prompt avec historique de conversation intégré")
            print("✅ Priorité donnée à l'historique pour les références")
            print("=" * 80)
            
            # Save context to memory
            self.memory.save_context(
                {"question": inputs["question"]},
                {"answer": result["answer"]}
            )
            
            return {"answer": result["answer"]}
    
    return MemoryAwareRAGChain(rag_chain, memory) 