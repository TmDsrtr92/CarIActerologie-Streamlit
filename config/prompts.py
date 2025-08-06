from langchain.prompts import PromptTemplate
from langfuse import Langfuse
from config.settings import get_langfuse_config
from config.traite_summary import TRAITE_SUMMARY
import streamlit as st

# Fallback prompt if Langfuse is unavailable
FALLBACK_SYSTEM_PROMPT = f"""
Tu es un assistant caractérologue expert, à la fois pédagogue et curieux. Ton rôle est de faire découvrir la caractérologie — la science des types de caractère — de manière à la fois précise, vivante et accessible.

Tu réponds aux questions des utilisateurs en t'appuyant rigoureusement sur les connaissances fournies par la base de données intégrée, notamment les travaux de René Le Senne et les typologies reconnues (émotivité, activité, retentissement). Si une réponse n'est pas disponible dans les sources, tu l'indiques honnêtement.

Tu adaptes ton langage et ton niveau d'explication selon le profil de l'utilisateur (novice ou initié). Tu cherches à l'accompagner dans sa compréhension de la caractérologie. S'il pose des questions simples ou générales, tu proposes des compléments pertinents pour approfondir.

Tu es capable d'orienter la conversation de façon naturelle, en suggérant des sujets liés à ce que l'utilisateur vient de dire. Par exemple, tu peux l'inviter à découvrir un autre type psychologique, une dimension caractérologique ou une mise en application concrète.

Tu peux aussi poser des questions ouvertes à l'utilisateur s'il semble curieux mais ne sait pas par où commencer.

Sois clair, structuré et rigoureux. Utilise des exemples concrets si cela peut aider à mieux comprendre. Ton objectif : éveiller l'intérêt, transmettre un savoir solide, et guider pas à pas dans l'univers de la caractérologie.

Adapte la longueur de ta réponse à la complexité de la question : réponse courte pour une question simple, plus développée pour une question complexe ou une demande d'explication détaillée. 

Tu integrera dans ta réflexion, quand c'est pertinent, les éléments suivants:
    {{context}} – éléments de contexte fournis

    {{question}} – question de l'utilisateur

    Résumé du Traité de caractérologie :
    {TRAITE_SUMMARY}

"""

@st.cache_data(ttl=60)  # Cache for 1 minute during testing
def get_langfuse_prompt(prompt_name: str = "caracterologie_qa", version: int = None):
    """
    Get prompt from Langfuse prompt management
    
    Args:
        prompt_name: Name of the prompt in Langfuse
        version: Specific version (optional, uses latest if None)
    
    Returns:
        str: Prompt template from Langfuse or fallback
    """
    try:
        config = get_langfuse_config()
        
        # Check if Langfuse keys are available
        if not config["secret_key"] or not config["public_key"]:
            raise ValueError("Langfuse keys not configured")
        
        langfuse = Langfuse(
            secret_key=config["secret_key"],
            public_key=config["public_key"],
            host=config["host"]
        )
        
        # Get prompt from Langfuse
        if version:
            prompt = langfuse.get_prompt(prompt_name, version=version)
        else:
            prompt = langfuse.get_prompt(prompt_name)
        
        # Replace traite summary placeholder with actual content
        prompt_text = prompt.prompt
        if "{TRAITE_SUMMARY}" in prompt_text:
            prompt_text = prompt_text.replace("{TRAITE_SUMMARY}", TRAITE_SUMMARY)
        
        # Ensure the prompt has the required placeholders
        if "{context}" not in prompt_text:
            prompt_text += "\n\nContext: {context}"
        if "{question}" not in prompt_text:
            prompt_text += "\n\nQuestion: {question}"
            
        return prompt_text
        
    except Exception as e:
        if "keys not configured" in str(e):
            # Silently use fallback when keys are not configured (expected in some environments)
            return FALLBACK_SYSTEM_PROMPT
        else:
            st.warning(f"Could not fetch prompt from Langfuse: {e}. Using fallback prompt.")
            return FALLBACK_SYSTEM_PROMPT

def get_qa_prompt(prompt_name: str = "caracterologie_qa", version: int = None):
    """Get the QA prompt template from Langfuse or fallback"""
    prompt_template = get_langfuse_prompt(prompt_name, version)
    
    # Extract variables from template or use defaults
    try:
        # Try to automatically detect variables
        template_obj = PromptTemplate.from_template(prompt_template)
        return template_obj
    except:
        # Fallback to explicit variables
        return PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )    