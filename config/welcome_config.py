"""
Welcome message and templated prompts configuration
Legacy module - now imports from unified configuration system.
"""

import warnings
from config.app_config import get_config

# Issue deprecation warning
warnings.warn(
    "config.welcome_config is deprecated. Use config.app_config.ui instead.",
    DeprecationWarning,
    stacklevel=2
)

# Get configuration instance
_config = get_config()

# Backward compatibility exports
WELCOME_MESSAGE = _config.ui.welcome_message
TEMPLATED_PROMPTS = _config.ui.templated_prompts

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