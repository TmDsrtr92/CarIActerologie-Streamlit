"""
Graceful degradation system with fallback responses for AI service failures
"""

import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re
from utils.logging_config import get_logger

logger = get_logger(__name__)

class CharacterologyFallbackSystem:
    """
    Provides meaningful fallback responses when AI service is unavailable
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Core characterology concepts for fallback responses
        self.character_types = {
            "nerveux": {
                "description": "Émotif, non-Actif, Primaire",
                "traits": ["sensible", "expressif", "spontané", "instable"],
                "examples": "artistes, créateurs impulsifs"
            },
            "sentimental": {
                "description": "Émotif, non-Actif, Secondaire", 
                "traits": ["introspectif", "mélancolique", "fidèle", "rancunier"],
                "examples": "poètes romantiques, penseurs solitaires"
            },
            "colérique": {
                "description": "Émotif, Actif, Primaire",
                "traits": ["énergique", "impulsif", "enthousiaste", "variable"],
                "examples": "leaders charismatiques, entrepreneurs"
            },
            "passionné": {
                "description": "Émotif, Actif, Secondaire",
                "traits": ["intense", "persévérant", "dominateur", "obstiné"],
                "examples": "révolutionnaires, grands dirigeants"
            },
            "sanguin": {
                "description": "non-Émotif, Actif, Primaire",
                "traits": ["pratique", "adaptable", "optimiste", "superficiel"],
                "examples": "hommes d'affaires, politiciens pragmatiques"
            },
            "flegmatique": {
                "description": "non-Émotif, Actif, Secondaire",
                "traits": ["méthodique", "persévérant", "froid", "efficace"],
                "examples": "administrateurs, techniciens rigoureux"
            },
            "amorphe": {
                "description": "non-Émotif, non-Actif, Primaire",
                "traits": ["indolent", "négligent", "bon vivant", "paresseux"],
                "examples": "personnes sans ambition particulière"
            },
            "apathique": {
                "description": "non-Émotif, non-Actif, Secondaire",
                "traits": ["indifférent", "stable", "routinier", "objectif"],
                "examples": "observateurs détachés, érudits"
            }
        }
        
        # Common characterology questions and responses
        self.faq_responses = {
            "qu'est-ce que la caractérologie": """
                **La Caractérologie selon René Le Senne**
                
                La caractérologie est la science qui étudie les **types de caractères** basée sur trois propriétés fondamentales :
                
                🔹 **L'Émotivité** : tendance à être affecté par les événements
                🔹 **L'Activité** : tendance à l'action et à la réalisation  
                🔹 **Le Retentissement** : impact durable (Secondaire) ou immédiat (Primaire) des impressions
                
                Ces trois dimensions se combinent pour former **8 types de caractères** distincts.
            """,
            
            "les 8 types": """
                **Les 8 Types Caractérologiques de René Le Senne**
                
                **Types Émotifs :**
                • **Nerveux** (É, nA, P) - Sensible et spontané
                • **Sentimental** (É, nA, S) - Introspectif et fidèle  
                • **Colérique** (É, A, P) - Énergique et impulsif
                • **Passionné** (É, A, S) - Intense et persévérant
                
                **Types non-Émotifs :**
                • **Sanguin** (nÉ, A, P) - Pratique et adaptable
                • **Flegmatique** (nÉ, A, S) - Méthodique et efficace
                • **Amorphe** (nÉ, nA, P) - Indolent et bon vivant
                • **Apathique** (nÉ, nA, S) - Indifférent et routinier
            """,
            
            "émotivité": """
                **L'Émotivité en Caractérologie**
                
                L'émotivité mesure la **tendance à être ému** par les événements, personnes ou situations.
                
                **Émotif (É) :**
                - Réagit fortement aux stimuli
                - Ressent intensément joies et peines
                - Expressif dans ses réactions
                - Vulnérable aux influences extérieures
                
                **Non-Émotif (nÉ) :**
                - Réactions mesurées et contrôlées
                - Stabilité émotionnelle
                - Objectivité face aux événements
                - Résistance aux influences
            """,
            
            "activité": """
                **L'Activité en Caractérologie**
                
                L'activité mesure la **tendance à l'action** et à la réalisation concrète.
                
                **Actif (A) :**
                - Besoin d'agir et de réaliser
                - Énergie dirigée vers l'extérieur
                - Goût pour l'entreprise
                - Difficulté à rester inactif
                
                **Non-Actif (nA) :**
                - Préférence pour la contemplation
                - Énergie dirigée vers l'intérieur
                - Goût pour la réflexion
                - Confort dans l'immobilité
            """,
            
            "retentissement": """
                **Le Retentissement en Caractérologie**
                
                Le retentissement mesure la **durée d'impact** des impressions sur la conscience.
                
                **Primaire (P) :**
                - Impressions immédiates et fugaces
                - Vit dans l'instant présent
                - Oublie rapidement
                - Adaptabilité et spontanéité
                
                **Secondaire (S) :**
                - Impressions durables et persistantes
                - Influence du passé sur le présent
                - Mémoire tenace
                - Persévérance et fidélité
            """
        }
        
        # Educational content for different user levels
        self.educational_content = {
            "beginner": [
                "La caractérologie étudie la **personnalité innée** de chaque individu",
                "Elle identifie **8 types de caractères** basés sur 3 propriétés fondamentales",
                "C'est un outil de **connaissance de soi** et de compréhension d'autrui",
                "René Le Senne est le père de cette discipline scientifique"
            ],
            
            "intermediate": [
                "La triade Émotivité-Activité-Retentissement forme le socle de la typologie",
                "Chaque type a ses **forces** et ses **zones de développement**",
                "La caractérologie aide à **adapter son comportement** selon les situations",
                "Elle éclaire les **relations interpersonnelles** et les choix de vie"
            ],
            
            "advanced": [
                "Les **formules caractérologiques** permettent une analyse précise",
                "Les **propriétés supplémentaires** enrichissent le portrait (largeur, ampleur...)",
                "La **psychodialectique** explore l'évolution des types",
                "L'application pratique concerne l'**orientation** et le **développement personnel**"
            ]
        }
        
        # Suggestions for further exploration
        self.exploration_suggestions = [
            "🔍 Découvrez votre type caractérologique avec les questions d'auto-analyse",
            "📚 Explorez les relations entre les différents types de caractères",
            "🎯 Apprenez à identifier les types dans votre entourage",
            "💡 Comprenez comment votre type influence vos choix de vie",
            "🌟 Développez vos points forts et travaillez vos zones d'amélioration"
        ]

    def detect_question_type(self, question: str) -> str:
        """
        Analyze question to determine the best fallback response type
        """
        question_lower = question.lower()
        
        # Remove accents for better matching
        question_normalized = (question_lower
                             .replace('é', 'e').replace('è', 'e').replace('ê', 'e')
                             .replace('à', 'a').replace('ç', 'c')
                             .replace('ô', 'o').replace('û', 'u'))
        
        # Question type detection patterns
        if any(word in question_normalized for word in ['qu\'est-ce', 'definition', 'c\'est quoi']):
            if 'caracterologie' in question_normalized:
                return 'definition_caracterologie'
            elif any(word in question_normalized for word in ['emotivite', 'emotif']):
                return 'definition_emotivite'
            elif any(word in question_normalized for word in ['activite', 'actif']):
                return 'definition_activite'
            elif 'retentissement' in question_normalized:
                return 'definition_retentissement'
        
        if any(word in question_normalized for word in ['types', '8 types', 'huit types']):
            return 'types_list'
            
        if any(word in question_normalized for word in ['mon type', 'quel type', 'je suis']):
            return 'type_identification'
            
        if any(word in question_normalized for word in ['comment', 'pourquoi', 'difference']):
            return 'explanation'
            
        # Default to general characterology info
        return 'general'

    def get_fallback_response(self, question: str, user_level: str = "beginner") -> Dict[str, str]:
        """
        Generate a helpful fallback response when AI service is unavailable
        
        Args:
            question: User's question
            user_level: User expertise level (beginner, intermediate, advanced)
            
        Returns:
            Dict with response content and metadata
        """
        question_type = self.detect_question_type(question)
        
        # Get specific response based on question type
        if question_type == 'definition_caracterologie':
            content = self.faq_responses["qu'est-ce que la caractérologie"]
        elif question_type == 'definition_emotivite':
            content = self.faq_responses["émotivité"]
        elif question_type == 'definition_activite':
            content = self.faq_responses["activité"]
        elif question_type == 'definition_retentissement':
            content = self.faq_responses["retentissement"]
        elif question_type == 'types_list':
            content = self.faq_responses["les 8 types"]
        elif question_type == 'type_identification':
            content = self._get_type_identification_guide()
        else:
            content = self._get_general_response(user_level)
        
        # Add educational context
        educational_tip = random.choice(self.educational_content.get(user_level, self.educational_content["beginner"]))
        exploration_tip = random.choice(self.exploration_suggestions)
        
        # Construct full response
        full_response = f"""
{content}

---

💡 **Le saviez-vous ?** {educational_tip}

{exploration_tip}

---

⚠️ **Mode dégradé** - Le service IA est temporairement indisponible. Cette réponse provient de notre base de connaissances caractérologiques. Pour une analyse personnalisée, réessayez dans quelques instants.
        """.strip()
        
        return {
            "content": full_response,
            "question_type": question_type,
            "user_level": user_level,
            "timestamp": datetime.now().isoformat(),
            "source": "fallback_system"
        }

    def _get_type_identification_guide(self) -> str:
        """Get guidance for type identification"""
        return """
        **Guide d'Auto-Identification de votre Type**
        
        Pour déterminer votre type caractérologique, posez-vous ces questions :
        
        **🔹 Émotivité :**
        - Êtes-vous facilement ému par les événements ?
        - Vos réactions sont-elles intenses et visibles ?
        - Êtes-vous sensible aux atmosphères ?
        
        **🔹 Activité :**
        - Avez-vous besoin d'agir, de réaliser des projets ?
        - Préférez-vous l'action à la contemplation ?
        - Êtes-vous entreprenant dans la vie ?
        
        **🔹 Retentissement :**
        - Gardez-vous longtemps en mémoire les événements marquants ?
        - Le passé influence-t-il fortement votre présent ?
        - Êtes-vous fidèle en amitié et en amour ?
        
        **Exemple :** Si vous répondez Oui-Oui-Non, vous pourriez être **Colérique** (Émotif, Actif, Primaire).
        """

    def _get_general_response(self, user_level: str) -> str:
        """Get a general characterology response"""
        type_example = random.choice(list(self.character_types.keys()))
        type_info = self.character_types[type_example]
        
        return f"""
        **Introduction à la Caractérologie**
        
        La caractérologie de René Le Senne étudie les **types de caractères innés** qui forment la structure permanente de notre personnalité.
        
        **Exemple : Le type {type_example.title()}**
        - **Formule :** {type_info['description']}
        - **Traits typiques :** {', '.join(type_info['traits'])}
        - **Souvent chez :** {type_info['examples']}
        
        La connaissance de votre type vous aide à :
        • Mieux vous comprendre
        • Optimiser vos relations
        • Orienter vos choix de vie
        • Développer votre potentiel
        """

    def get_service_status_message(self, circuit_state: Dict) -> str:
        """
        Get user-friendly service status message
        """
        state = circuit_state.get("state", "unknown")
        remaining_timeout = circuit_state.get("remaining_timeout", 0)
        
        if state == "open":
            if remaining_timeout > 60:
                return f"🔴 **Service IA indisponible** - Récupération prévue dans ~{remaining_timeout//60:.0f} minutes"
            else:
                return f"🔴 **Service IA indisponible** - Test de récupération dans {remaining_timeout:.0f} secondes"
        elif state == "half_open":
            return "🟡 **Service IA en cours de récupération** - Test en cours..."
        else:
            return "🟢 **Service IA disponible**"

    def get_offline_guidance(self) -> str:
        """
        Provide guidance for offline/degraded mode usage
        """
        return """
        **💡 Que faire pendant l'indisponibilité du service ?**
        
        **📚 Explorez les concepts de base :**
        - Posez des questions sur l'émotivité, l'activité, le retentissement
        - Demandez des informations sur les 8 types caractérologiques
        - Explorez les définitions et concepts fondamentaux
        
        **🔍 Auto-analyse :**
        - Utilisez les guides d'identification de type
        - Réfléchissez à vos traits caractérologiques
        - Observez les types dans votre entourage
        
        **⏰ Service complet bientôt disponible :**
        Le système reviendra automatiquement dès que le service IA sera rétabli pour des réponses personnalisées et approfondies.
        """


# Global fallback system instance
_fallback_system: Optional[CharacterologyFallbackSystem] = None


def get_fallback_system() -> CharacterologyFallbackSystem:
    """Get or create the global fallback system instance"""
    global _fallback_system
    if _fallback_system is None:
        _fallback_system = CharacterologyFallbackSystem()
    return _fallback_system


def generate_fallback_response(question: str, user_level: str = "beginner") -> str:
    """
    Generate a fallback response for when AI service is down
    
    Args:
        question: User's question
        user_level: User expertise level
        
    Returns:
        Formatted fallback response
    """
    fallback_system = get_fallback_system()
    
    try:
        response_data = fallback_system.get_fallback_response(question, user_level)
        logger.info(f"Generated fallback response for question type: {response_data['question_type']}")
        return response_data["content"]
        
    except Exception as e:
        logger.error(f"Error generating fallback response: {e}")
        
        # Ultra-simple fallback if even the fallback system fails
        return """
        **Service temporairement indisponible**
        
        Le service IA de CarIActérologie n'est pas disponible actuellement. 
        
        **En attendant :**
        - La caractérologie étudie les types de caractères innés
        - Elle se base sur 3 propriétés : Émotivité, Activité, Retentissement  
        - René Le Senne a identifié 8 types caractérologiques
        
        Réessayez dans quelques instants pour une analyse personnalisée.
        """