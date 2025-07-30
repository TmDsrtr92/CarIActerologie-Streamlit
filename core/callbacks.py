import time
from langchain.callbacks.base import BaseCallbackHandler

class StreamlitCallbackHandler(BaseCallbackHandler):
    """Handler pour afficher le texte en streaming dans Streamlit"""
    
    def __init__(self, placeholder, update_every=3, delay=0.15):
        self.placeholder = placeholder
        self.text = ""
        self.counter = 0
        self.update_every = update_every
        self.delay = delay
    
    def on_llm_new_token(self, token, **kwargs):
        self.text += token
        self.counter += 1
        if self.counter % self.update_every == 1:
            self.placeholder.markdown(self.text + "▌")
            time.sleep(self.delay)
    
    def on_llm_end(self, *args, **kwargs):
        self.placeholder.markdown(self.text)

class RetrievalCallbackHandler(BaseCallbackHandler):
    """Handler pour afficher les chunks récupérés dans la console"""
    
    def __init__(self, memory=None):
        self.memory = memory
        self.original_question = None
    
    def on_retriever_start(self, serialized, query, **kwargs):
        # Stocker la question originale pour comparaison
        self.original_question = query
        
        print(f"\n🔍 RECHERCHE DE CHUNKS pour la question: '{query}'")
        print("=" * 80)
        
        # Afficher la mémoire de conversation si disponible
        if self.memory and hasattr(self.memory, 'memory') and hasattr(self.memory.memory, 'chat_memory'):
            chat_memory = self.memory.memory.chat_memory
            messages = chat_memory.messages
            
            if messages:
                print(f"\n💬 MÉMOIRE DE CONVERSATION ({len(messages)} messages):")
                print("=" * 80)
                for i, msg in enumerate(messages, 1):
                    role = "👤 Utilisateur" if msg.type == "human" else "🤖 Assistant"
                    print(f"\n{i}. {role}:")
                    print("-" * 40)
                    print(msg.content)
                    print("-" * 40)
                    print(f"📊 Longueur: {len(msg.content)} caractères")
                print("=" * 80)
            else:
                print("\n💬 MÉMOIRE DE CONVERSATION: (vide)")
        else:
            print("\n💬 MÉMOIRE DE CONVERSATION: (non disponible)")
    
    def on_retriever_end(self, documents, **kwargs):
        print(f"📄 {len(documents)} chunks récupérés:")
        print("-" * 80)
        for i, doc in enumerate(documents, 1):
            print(f"\n📄 Chunk {i}:")
            print(f"   Source: {getattr(doc.metadata, 'source', 'N/A')}")
            print(f"   Page: {getattr(doc.metadata, 'page', 'N/A')}")
            print(f"   Contenu: {doc.page_content[:200]}...")
            if len(doc.page_content) > 200:
                print(f"   (tronqué, longueur totale: {len(doc.page_content)} caractères)")
            print("-" * 40)
        print("=" * 80)
    
    def on_chain_start(self, serialized, inputs, **kwargs):
        """Affiche le prompt utilisé par le système"""
        print(f"\n🤖 PROMPT UTILISÉ PAR LE SYSTÈME:")
        print("=" * 80)
        
        # Chercher le prompt dans les inputs
        prompt_text = ""
        
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
        
        # Vérifier si la question a été reformulée
        if self.original_question and prompt_text and prompt_text != self.original_question:
            print(f"⚠️  ATTENTION: Question reformulée!")
            print(f"   Question originale: '{self.original_question}'")
            print(f"   Question reformulée: '{prompt_text}'")
            print("-" * 40)
        
        # Afficher les 500 premiers caractères
        if prompt_text:
            truncated_prompt = prompt_text[:500]
            print(f"📝 Question utilisateur (500 premiers caractères):")
            print("-" * 40)
            print(truncated_prompt)
            if len(prompt_text) > 500:
                print(f"... (tronqué, longueur totale: {len(prompt_text)} caractères)")
            print("-" * 40)
        else:
            print("❌ Impossible de récupérer le prompt")
            print("🔍 Clés disponibles dans inputs:", list(inputs.keys()) if inputs else "Aucune")
        
        print("=" * 80)
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Affiche le prompt système complet utilisé par le LLM"""
        print(f"\n🤖 PROMPT SYSTÈME COMPLET UTILISÉ PAR LE LLM:")
        print("=" * 80)
        
        if prompts and len(prompts) > 0:
            # Le premier prompt contient généralement le prompt système complet
            system_prompt = prompts[0]
            
            # Afficher les 1000 premiers caractères du prompt système
            truncated_system = system_prompt[:1000]
            print(f"📝 Prompt système (1000 premiers caractères):")
            print("-" * 40)
            print(truncated_system)
            if len(system_prompt) > 1000:
                print(f"... (tronqué, longueur totale: {len(system_prompt)} caractères)")
            print("-" * 40)
            
            # Si il y a plusieurs prompts, afficher le nombre
            if len(prompts) > 1:
                print(f"📊 Nombre total de prompts: {len(prompts)}")
        else:
            print("❌ Aucun prompt système trouvé")
        
        print("=" * 80) 