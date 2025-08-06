"""
Demo script to show how the chunks display component works
"""

import streamlit as st
from utils.chunks_display import render_chunks_component, ChunksCollector
from langchain_core.documents import Document

# Sample documents to demonstrate the chunks display
sample_docs = [
    Document(
        page_content="""L'émotivité est la propriété en vertu de laquelle les événements exercent sur la conscience une répercussion plus ou moins forte et plus ou moins durable. Cette propriété, qui caractérise les individus émotifs, se manifeste par une sensibilité particulière aux impressions du monde extérieur.""",
        metadata={
            "source": "documents/traite_caracterologie.pdf",
            "page": 45,
            "section_title": "Les propriétés constitutives - L'émotivité",
            "section_type": "Section 1",
            "chunk_size": 289
        }
    ),
    Document(
        page_content="""L'activité est la propriété qui fait qu'un individu a tendance à agir, à se mouvoir, à entreprendre, à réaliser des projets. Elle se manifeste par une facilité naturelle à passer à l'action et une tendance à chercher des occupations actives plutôt que contemplatives.""",
        metadata={
            "source": "documents/traite_caracterologie.pdf", 
            "page": 52,
            "section_title": "Les propriétés constitutives - L'activité",
            "section_type": "Section 2", 
            "chunk_size": 267
        }
    ),
    Document(
        page_content="""Le retentissement est la propriété selon laquelle les impressions se prolongent plus ou moins longtemps dans la conscience après avoir cessé d'agir. Cette durée de résonance des impressions détermine si l'individu est primaire (impressions brèves) ou secondaire (impressions durables).""",
        metadata={
            "source": "documents/traite_caracterologie.pdf",
            "page": 58,
            "section_title": "Les propriétés constitutives - Le retentissement", 
            "section_type": "Section 3",
            "chunk_size": 312
        }
    )
]

def main():
    st.title("Demo: Affichage des chunks récupérés")
    
    st.markdown("""
    Ce demo montre comment les chunks récupérés de la base de connaissances seront affichés 
    à la fin de chaque réponse de l'assistant.
    """)
    
    # Simulate a question and response
    st.markdown("### Question de l'utilisateur:")
    st.info("Qu'est-ce que l'émotivité en caractérologie ?")
    
    st.markdown("### Réponse de l'assistant:")
    st.success("""
    L'émotivité est l'une des trois propriétés constitutives fondamentales de la caractérologie selon René Le Senne. 
    Elle définit la capacité d'un individu à être affecté par les événements extérieurs...
    
    [Réponse complète de l'assistant ici]
    """)
    
    st.markdown("### Sources consultées:")
    st.markdown("Voici comment les chunks récupérés apparaîtront :")
    
    # Show the chunks display component
    render_chunks_component(sample_docs, "Qu'est-ce que l'émotivité en caractérologie ?")
    
    st.markdown("---")
    st.markdown("### Utilisation du ChunksCollector:")
    
    # Demo with ChunksCollector
    collector = ChunksCollector()
    collector.set_question("Comment fonctionne l'activité ?")
    collector.add_chunks(sample_docs[:2])  # Only first 2 chunks
    
    st.markdown("Exemple avec moins de chunks :")
    collector.render_if_available()

if __name__ == "__main__":
    main()