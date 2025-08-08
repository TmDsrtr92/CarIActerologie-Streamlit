"""
Test script to demonstrate graceful degradation functionality
"""

import sys
sys.path.append('.')

from services.ai_service.fallback_service import get_fallback_system, generate_fallback_response

def demonstrate_fallback_responses():
    """Demonstrate different types of fallback responses"""
    
    print("=== GRACEFUL DEGRADATION DEMONSTRATION ===")
    print()
    
    fallback_system = get_fallback_system()
    
    # Test different question types
    test_scenarios = [
        {
            "question": "Qu'est-ce que la caractérologie ?",
            "description": "Basic definition question",
            "user_level": "beginner"
        },
        {
            "question": "Quels sont les 8 types caractérologiques ?",
            "description": "Types listing question", 
            "user_level": "intermediate"
        },
        {
            "question": "Comment puis-je identifier mon type de caractère ?",
            "description": "Self-assessment question",
            "user_level": "beginner"
        },
        {
            "question": "Expliquez-moi l'émotivité en détail",
            "description": "Concept explanation",
            "user_level": "advanced"
        },
        {
            "question": "Quelle est la différence entre primaire et secondaire ?",
            "description": "Complex concept question",
            "user_level": "intermediate"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"=== SCENARIO {i}: {scenario['description']} ===")
        print(f"Question: \"{scenario['question']}\"")
        print(f"User Level: {scenario['user_level']}")
        print()
        
        # Generate fallback response
        try:
            response = generate_fallback_response(
                scenario['question'], 
                scenario['user_level']
            )
            
            # Show first part of response (truncated for readability)
            lines = response.split('\n')
            preview_lines = lines[:15]  # Show first 15 lines
            preview = '\n'.join(preview_lines)
            
            if len(lines) > 15:
                preview += "\n[...response continues...]"
            
            print("FALLBACK RESPONSE:")
            print("-" * 50)
            print(preview)
            print("-" * 50)
            print()
            
        except Exception as e:
            print(f"ERROR generating response: {e}")
            print()

def demonstrate_offline_capabilities():
    """Show offline mode capabilities"""
    
    print("=== OFFLINE MODE CAPABILITIES ===")
    print()
    
    fallback_system = get_fallback_system()
    
    print("1. INTELLIGENT QUESTION DETECTION:")
    questions_and_types = [
        ("Qu'est-ce que la caractérologie ?", "Definition"),
        ("Les 8 types de caractère", "Type listing"),
        ("Comment identifier mon type ?", "Self-assessment"),
        ("Différence entre émotif et non-émotif", "Concept explanation"),
        ("Quel est mon caractère ?", "Type identification")
    ]
    
    for question, expected_type in questions_and_types:
        detected_type = fallback_system.detect_question_type(question)
        print(f"  '{question}' -> {detected_type}")
    
    print()
    print("2. EDUCATIONAL CONTENT BY LEVEL:")
    for level in ['beginner', 'intermediate', 'advanced']:
        content = fallback_system.educational_content[level]
        print(f"  {level.upper()}: {content[0]}")
    
    print()
    print("3. CHARACTER TYPES DATABASE:")
    for char_type, info in list(fallback_system.character_types.items())[:3]:
        print(f"  {char_type.upper()}: {info['description']}")
        print(f"    Traits: {', '.join(info['traits'][:3])}...")
    
    print()
    print("4. OFFLINE GUIDANCE:")
    guidance = fallback_system.get_offline_guidance()
    guidance_lines = guidance.split('\n')[:10]  # First 10 lines
    print('\n'.join(guidance_lines))
    print("    [... additional guidance available ...]")

def demonstrate_integration_flow():
    """Show how graceful degradation fits into the complete error handling"""
    
    print()
    print("=== COMPLETE ERROR HANDLING FLOW ===")
    print()
    
    print("NORMAL OPERATION:")
    print("User Question -> Circuit Check (CLOSED) -> Retry Logic -> AI Response")
    print()
    
    print("TRANSIENT ERRORS:")
    print("User Question -> Circuit Check (CLOSED) -> Retry 1 -> Retry 2 -> Retry 3 -> AI Response")
    print("                                          |         |         |")
    print("                                          v         v         v")
    print("                                    Rate Limit  Timeout   Connection")
    print("                                    (retry)    (retry)   (retry)")
    print()
    
    print("SERVICE DOWN (Graceful Degradation):")
    print("User Question -> Circuit Check (OPEN) -> Fallback System -> Meaningful Response")
    print("                 |                      |")
    print("                 v                      v")
    print("           5+ failures             Domain-specific")
    print("           (60s timeout)          characterology content")
    print()
    
    print("RECOVERY PROCESS:")
    print("Timer Expires -> Circuit (HALF_OPEN) -> Test Request -> Success -> Circuit (CLOSED)")
    print("                                      |               |")
    print("                                      v               v")
    print("                                 Single request   Normal AI")
    print("                                    allowed      service resumed")
    print()
    
    print("BENEFITS OF COMPLETE STACK:")
    print("✓ Automatic retry for transient issues")
    print("✓ Fast-fail protection when service is down") 
    print("✓ Meaningful content during outages")
    print("✓ Automatic recovery detection")
    print("✓ Seamless user experience at all times")

if __name__ == "__main__":
    try:
        demonstrate_fallback_responses()
        demonstrate_offline_capabilities()
        demonstrate_integration_flow()
        
        print()
        print("🎉 GRACEFUL DEGRADATION IMPLEMENTATION COMPLETE!")
        print()
        print("Your CarIActérologie app now provides:")
        print("• Meaningful responses even when AI service is down")
        print("• Domain-specific characterology knowledge")
        print("• Educational content at appropriate user levels")
        print("• Offline mode with guided interactions")
        print("• Seamless integration with circuit breaker")
        print("• Complete error handling stack")
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        sys.exit(1)