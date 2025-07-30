"""
Welcome message and templated prompts configuration
"""

# Welcome message content
WELCOME_MESSAGE = """👋 **Bienvenue dans CarIActérologie !**

Je suis votre assistant expert en caractérologie, spécialisé dans les travaux de René Le Senne. Je suis là pour vous accompagner dans la découverte de la science des types de caractère.

Que vous soyez novice ou déjà initié, je peux vous aider à :
- **Comprendre les fondements** de la caractérologie
- **Explorer votre type de caractère** et ses spécificités  
- **Approfondir vos connaissances** sur les 8 types caractérologiques
- **Appliquer ces concepts** dans votre développement personnel

Pour commencer, vous pouvez choisir une des suggestions ci-dessous ou me poser directement votre question :"""

# Templated prompts for different user types
TEMPLATED_PROMPTS = [
    {
        "id": "beginner",
        "title": "🌱 Débutant",
        "prompt": "Qu'est-ce que la caractérologie et comment peut-elle m'aider ?",
        "description": "Découvrir les bases de la caractérologie",
        "icon": "🌱"
    },
    {
        "id": "practical", 
        "title": "🔍 Pratique",
        "prompt": "Pouvez-vous m'aider à comprendre mon type de caractère ?",
        "description": "Explorer votre profil caractérologique",
        "icon": "🔍"
    },
    {
        "id": "advanced",
        "title": "📚 Avancé", 
        "prompt": "Expliquez-moi en détail le système typologique de René Le Senne",
        "description": "Approfondir la théorie caractérologique",
        "icon": "📚"
    }
]

# Welcome message styling
WELCOME_STYLE = {
    "background_color": "#f0f2f6",
    "border_color": "#d1d5db", 
    "border_radius": "10px",
    "padding": "20px",
    "margin_bottom": "20px"
}

# Prompt button styling
PROMPT_BUTTON_STYLE = {
    "width": "100%",
    "margin": "5px 0",
    "padding": "10px 15px",
    "border_radius": "8px",
    "border": "1px solid #e5e7eb",
    "background": "white",
    "hover_background": "#f9fafb"
}