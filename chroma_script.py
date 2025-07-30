from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
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

# Créer un nom de collection unique avec timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
collection_name = f"traite_{timestamp}"

# Créer la base Chroma avec les bons embeddings
vectorstore = Chroma.from_texts(
    chunks,
    embedding=embeddings,
    persist_directory="./index_stores",
    collection_name=collection_name
)
vectorstore.persist()

print(f"Indexation terminée. {len(chunks)} chunks indexés dans ./index_stores (collection '{collection_name}').")
print(f"Pour utiliser cette collection, modifiez config/settings.py avec: 'collection_name': '{collection_name}'")








