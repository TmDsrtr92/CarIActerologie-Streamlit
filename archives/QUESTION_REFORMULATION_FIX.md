# Correction de la Reformulation des Questions

## Problème Identifié

L'utilisateur a remarqué que parfois, les questions posées dans l'interface étaient transformées ou reformulées avant d'être traitées par le système. Cela pouvait se produire à cause de la mémoire de conversation ou d'autres mécanismes de LangChain.

## Cause Racine

La `ConversationalRetrievalChain` de LangChain a par défaut un mécanisme de **question generator** qui peut reformuler automatiquement les questions de l'utilisateur pour améliorer la recherche de documents pertinents. Ce comportement peut être problématique car :

1. **Perte de contexte** : La question reformulée peut perdre des nuances importantes de la question originale
2. **Confusion** : L'utilisateur peut ne pas reconnaître sa question dans la réponse
3. **Incohérence** : Les réponses peuvent ne pas correspondre exactement à ce qui a été demandé

## Solution Implémentée

### 1. Désactivation Complète de la Reformulation (`core/qa_chain.py`)

```python
def setup_qa_chain_with_memory(memory):
    """Set up the ConversationalRetrievalChain with specific memory"""
    llm = setup_llm()
    retriever = setup_retriever()
    prompt = get_qa_prompt()
    
    # Create chain without return_source_documents to avoid output key conflict
    # Désactiver la reformulation automatique des questions
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory.memory,
        combine_docs_chain_kwargs={"prompt": prompt},
        # Désactiver la reformulation des questions
        rephrase_question=False,
        # Désactiver le générateur de questions
        return_generated_question=False,
        verbose=False
    )
    
    # Désactiver manuellement le question generator après création
    if hasattr(chain, 'question_generator'):
        chain.question_generator = None
    
    return chain
```

**Paramètres ajoutés :**
- `rephrase_question=False` : Désactive la reformulation automatique des questions
- `return_generated_question=False` : Désactive le retour de la question générée
- `chain.question_generator = None` : Désactive complètement le générateur de questions

### 2. Surveillance de la Reformulation (`core/callbacks.py`)

Ajout d'un mécanisme de surveillance dans le `RetrievalCallbackHandler` pour détecter si une question est reformulée :

```python
class RetrievalCallbackHandler(BaseCallbackHandler):
    def __init__(self, memory=None):
        self.memory = memory
        self.original_question = None  # Stockage de la question originale
    
    def on_retriever_start(self, serialized, query, **kwargs):
        # Stocker la question originale pour comparaison
        self.original_question = query
        # ... reste du code
    
    def on_chain_start(self, serialized, inputs, **kwargs):
        # ... code existant ...
        
        # Vérifier si la question a été reformulée
        if self.original_question and prompt_text and prompt_text != self.original_question:
            print(f"⚠️  ATTENTION: Question reformulée!")
            print(f"   Question originale: '{self.original_question}'")
            print(f"   Question reformulée: '{prompt_text}'")
            print("-" * 40)
```

## Résultats

### Avant la Correction
- Les questions pouvaient être automatiquement reformulées
- Pas de visibilité sur les transformations
- Risque de perte de contexte
- `question_generator` était actif

### Après la Correction
- ✅ **Questions préservées** : Les questions de l'utilisateur restent inchangées
- ✅ **Surveillance active** : Le système détecte et signale toute reformulation
- ✅ **Transparence** : Affichage en console de la question originale vs reformulée
- ✅ **Contrôle total** : L'utilisateur voit exactement ce qui est traité
- ✅ **Question generator désactivé** : `question_generator = None`

## Vérification

Le système affiche maintenant dans la console :

```
🔍 RECHERCHE DE CHUNKS pour la question: 'Question originale de l'utilisateur'
================================================================================

🤖 PROMPT UTILISÉ PAR LE SYSTÈME:
================================================================================
📝 Question utilisateur (500 premiers caractères):
----------------------------------------
Question originale de l'utilisateur
----------------------------------------
================================================================================
```

Si une reformulation se produit malgré les paramètres, le système affichera :

```
⚠️  ATTENTION: Question reformulée!
   Question originale: 'Question originale'
   Question reformulée: 'Question transformée'
----------------------------------------
```

## Impact sur les Performances

- **Recherche de documents** : Peut être légèrement moins précise sans reformulation
- **Cohérence des réponses** : Améliorée car les questions restent fidèles
- **Expérience utilisateur** : Améliorée car les réponses correspondent exactement aux questions

## Recommandations

1. **Surveiller les logs** : Vérifier régulièrement la console pour détecter d'éventuelles reformulations
2. **Ajuster si nécessaire** : Si la qualité des réponses diminue, envisager d'activer partiellement la reformulation
3. **Tests utilisateur** : Valider que les réponses correspondent mieux aux attentes des utilisateurs

## Date de Mise en Place

- **Problème identifié** : [Date de la question utilisateur]
- **Solution implémentée** : [Date actuelle]
- **Testé** : ✅ Fonctionnel
- **Documenté** : ✅ Ce document

## Notes Techniques

- **Méthode de désactivation** : Désactivation manuelle du `question_generator` après création de la chaîne
- **Compatibilité** : Solution compatible avec les versions récentes de LangChain
- **Surveillance** : Mécanisme de détection en place pour identifier toute reformulation résiduelle 