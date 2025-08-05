from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from datetime import datetime

# Clé API OpenAI (à adapter selon ton usage)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    try:
        import streamlit as st
        OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    except Exception:
        raise RuntimeError("OPENAI_API_KEY non trouvé dans les variables d'environnement ni dans streamlit.secrets")

# Charger le texte
with open("documents/traite_de_caracterologie.txt", "r", encoding="utf-8") as f:
    full_text = f.read()

# Découper le texte en chunks (par défaut 500 caractères, overlap 50)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = text_splitter.split_text(full_text)

# Créer les embeddings OpenAI
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# Créer un nom d'index FAISS unique avec timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
index_name = f"traite_{timestamp}_faiss"

# Créer la base FAISS avec les bons embeddings
vectorstore = FAISS.from_texts(
    chunks,
    embedding=embeddings
)

# Sauvegarder l'index FAISS
persist_directory = "./index_stores"
os.makedirs(persist_directory, exist_ok=True)
faiss_path = os.path.join(persist_directory, index_name)
vectorstore.save_local(faiss_path)

print(f"Indexation terminée. {len(chunks)} chunks indexés dans {faiss_path}.")
print(f"Pour utiliser cet index, modifiez config/settings.py avec: 'collection_name': '{index_name}'")








