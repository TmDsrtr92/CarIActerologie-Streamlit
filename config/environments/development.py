"""
Development environment configuration overrides
"""

from dataclasses import dataclass, field
from config.app_config import AppConfig, LLMConfig, VectorStoreConfig, LoggingConfig, UIConfig
from typing import Dict, Any, List


@dataclass
class DevelopmentConfig(AppConfig):
    """Development environment configuration"""
    
    def __post_init__(self):
        
        # Development-specific overrides
        self.environment = "development"
        self.debug = True
        
        # More verbose logging in development
        self.logging.level = "DEBUG"
        self.logging.enable_file_logging = True
        self.logging.log_file = "logs/dev-app.log"
        
        # Development UI changes
        self.ui.app_title = "🧪 CarIActérologie (DEV)"
        self.ui.welcome_message = """👋 **Bienvenue dans CarIActérologie (Environnement de Développement) !**

⚠️ **Version de développement** - Cette version peut contenir des fonctionnalités expérimentales ou instables.

Je suis votre assistant expert en caractérologie, spécialisé dans les travaux de René Le Senne. Cette version de développement me permet de tester de nouvelles fonctionnalités avant leur déploiement en production.

Que vous soyez novice ou déjà initié, je peux vous aider à :
- **Comprendre les fondements** de la caractérologie
- **Explorer votre type de caractère** et ses spécificités  
- **Approfondir vos connaissances** sur les 8 types caractérologiques
- **Tester les nouvelles fonctionnalités** en avant-première

Pour commencer, vous pouvez choisir une des suggestions ci-dessous ou me poser directement votre question :"""

        # Development-specific features
        self.langgraph.enable_conversation_branching = True
        self.langgraph.enable_semantic_search = True
        
        # More permissive settings for testing
        self.auth.allow_guest_mode = True
        self.auth.require_email_verification = False
        
        # Development vector store settings
        self.vectorstore.search_kwargs = {"k": 8}  # Retrieve more chunks for testing


def get_development_config() -> DevelopmentConfig:
    """Get development-specific configuration"""
    return DevelopmentConfig()