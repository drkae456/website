# File created by Bryce Bacon in association with Hardhat Enterprises Company Website Backend team
# StudentID: 215076784 | Contact: brycedanielbacon@gmail.com | GitHub: https://github.com/drkae456
# Alot of manual inpuit, next job is to automate more, with better sorting and natural language algorithm
"""
chatbot_app/search_engine.py
ORM-based search implementation with dynamic model handling and security.
Enhanced with natural language processing and smart model identification.
"""
import re
from difflib import get_close_matches
import logging

from django.apps import apps
from django.db.models import Q
from django.db.models import CharField, TextField
from django.utils import timezone

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Define substrings of field names considered sensitive
SENSITIVE_FIELD_KEYWORDS = {'password', 'passkey', 'secret', 'token', 'email', 'user_details'}

# Common domain-specific terms for spell checking
DOMAIN_TERMS = {
    'cyber', 'cybersecurity', 'security', 'hacking', 'ethical', 'penetration',
    'pentest', 'malware', 'virus', 'trojan', 'ransomware', 'phishing', 'smishing',
    'firewall', 'network', 'encryption', 'decryption', 'authentication', 'authorization',
    'vulnerability', 'exploit', 'attack', 'defense', 'threat', 'risk', 'assessment',
    'audit', 'compliance', 'forensics', 'incident', 'response', 'mitigation',
    'deakin', 'hardhat', 'challenge', 'ctf', 'flag', 'course', 'skill', 'project',
    'appattack', 'threatmirror', 'visualization'
}

# Mapping for formatting title and URL by model
MODEL_FORMAT = {
    'cyberchallenge': {'emoji': '🎯', 'label': 'Challenge', 'url_pattern': '/challenges/{id}', 'append_difficulty': True},
    'skill':         {'emoji': '💪', 'label': 'Skill', 'url_pattern': '/skills/{id}'},
    'course':        {'emoji': '📚', 'label': 'Course', 'url_pattern': '/courses/{id}'},
    'project':       {'emoji': '🚀', 'label': 'Project', 'url_pattern': '/projects/{id}'},
    'announcement':  {'emoji': '📢', 'label': 'Announcement', 'url_pattern': '/announcements/{id}'},
}

def build_vocabulary():
    """
    Build a vocabulary from domain terms and database content.
    """
    vocab = set(DOMAIN_TERMS)
    
    # Add model names and their fields
    models = get_searchable_models()
    for model in models.values():
        # Add model name and its variations
        name = model.__name__.lower()
        vocab.add(name)
        vocab.add(name + 's')  # plural form
        words = split_camel(model.__name__)
        vocab.update(words)
        
        # Add field names
        fields = get_searchable_fields(model)
        vocab.update(field.lower() for field in fields)
        
    return vocab

def spell_correct(text, cutoff=0.8):
    """
    Attempt to correct spelling in the input text using domain-specific vocabulary.
    
    Args:
        text (str): Input text to correct
        cutoff (float): Similarity threshold for corrections (0.0 to 1.0)
        
    Returns:
        tuple: (corrected_text, was_corrected)
    """
    if not text:
        return text, False
        
    # Get or build vocabulary
    vocab = build_vocabulary()
    
    # Split into words and normalize
    words = text.lower().split()
    corrected = []
    was_corrected = False
    
    for word in words:
        # Skip short words and numbers
        if len(word) <= 3 or word.isdigit():
            corrected.append(word)
            continue
            
        # Skip if word is already in vocabulary
        if word in vocab:
            corrected.append(word)
            continue
            
        # Try to find close matches
        matches = get_close_matches(word, vocab, n=1, cutoff=cutoff)
        if matches:
            corrected.append(matches[0])
            was_corrected = True
        else:
            corrected.append(word)
            
    return ' '.join(corrected), was_corrected

def get_searchable_models(app_label='home'):
    """
    Dynamically retrieve all models from the specified app.
    Returns a dict mapping cleaned model keys to model classes.
    """
    app_config = apps.get_app_config(app_label)
    models = {}
    for model in app_config.get_models():
        key = model.__name__.lower()
        models[key] = model
    return models


def get_searchable_fields(model):
    """
    Return a list of CharField/TextField names on the model,
    excluding any whose names contain sensitive keywords.
    """
    fields = []
    for field in model._meta.get_fields():
        if getattr(field, 'concrete', False) and not field.many_to_many and not field.one_to_many:
            if isinstance(field, (CharField, TextField)):
                name = field.name.lower()
                if not any(keyword in name for keyword in SENSITIVE_FIELD_KEYWORDS):
                    fields.append(field.name)
    return fields


def split_camel(name):
    """
    Split CamelCase model names into space-separated words.
    """
    parts = re.findall(r'[A-Z][a-z]*', name)
    return [p.lower() for p in parts]


def identify_model_from_prompt(prompt, models):
    """
    Identify the best model key in the prompt by matching full words or fuzzy matching.
    Now handles partial matches and common variations of model names as well as
    natural language questions.
    """
    prompt_lower = prompt.lower()
    normalized = re.sub(r"\W+", '', prompt_lower)
    
    # Expanded variations of model names with more natural language patterns
    model_variations = {
        # Challenge variations
        'challenge': 'cyberchallenge',
        'challenges': 'cyberchallenge',
        'cyberchallenges': 'cyberchallenge',
        'cyber': 'cyberchallenge', 
        
        # Announcement variations
        'announcement': 'announcement',
        'announcements': 'announcement',
        'news': 'announcement',
        'updates': 'announcement',
        
        # Skill variations
        'skill': 'skill',
        'skills': 'skill',
        'learn': 'skill',
        'learning': 'skill',
        'training': 'skill',
        'ability': 'skill',
        'abilities': 'skill',
        'competency': 'skill',
        'competencies': 'skill',
        
        # Course variations
        'course': 'course',
        'courses': 'course',
        'class': 'course',
        'classes': 'course',
        'training': 'course',
        
        # Project variations
        'project': 'project',
        'projects': 'project',
        'assignment': 'project',
        'assignments': 'project'
    }
    
    # Check for question patterns first
    question_patterns = {
        r'what skill': 'skill',
        r'which skill': 'skill',
        r'can i learn': 'skill',
        r'how (can|do) i learn': 'skill',
        r'what.+learn': 'skill',
        r'skills.+(can|available)': 'skill',
        r'available skills': 'skill',
        r'what courses': 'course',
        r'which courses': 'course',
        r'any new challenge': 'cyberchallenge',
        r'what challenge': 'cyberchallenge',
    }
    
    # First check for question patterns
    for pattern, model_key in question_patterns.items():
        if re.search(pattern, prompt_lower):
            return model_key
    
    # Then try exact matches from variations
    words = prompt_lower.split()
    for word in words:
        if word in model_variations:
            return model_variations[word]
    
    # Try direct substring match of model names
    for key, model in models.items():
        # Build phrase variants from CamelCase name
        words = split_camel(model.__name__)
        phrase = ' '.join(words)
        plural = phrase + 's'
        # Check phrase or plural in prompt, or key in normalized prompt
        if phrase in prompt_lower or plural in prompt_lower or key in normalized:
            return key
    
    # Fallback: fuzzy match against model variations
    best_match = None
    best_score = 0
    
    # Try to match against all words in the query
    for word in prompt_lower.split():
        matches = get_close_matches(word, list(model_variations.keys()), n=1, cutoff=0.6)
        if matches:
            score = len(matches[0]) / len(word)  # Favor longer matches
            if score > best_score:
                best_score = score
                best_match = model_variations[matches[0]]
    
    return best_match


def extract_search_term(prompt, model_key, models):
    """
    Remove the identified model phrase from the prompt and clean up filler words.
    Returns a clean search term or empty string for listing all.
    Enhanced to handle more complex natural language queries.
    """
    model = models[model_key]
    words = split_camel(model.__name__)
    phrase = ' '.join(words)
    plural = phrase + 's'
    
    # Expanded list of filler words to remove
    filler_words = {
        # Common verbs and auxiliaries
        'show', 'me', 'tell', 'find', 'search', 'look', 'looking', 'want', 'need',
        'would', 'could', 'should', 'can', 'may', 'might', 'will', 'shall', 'do', 'does',
        'did', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'get', 'got', 'getting',
        
        # Prepositions and articles
        'about', 'at', 'by', 'for', 'from', 'in', 'of', 'on', 'to', 'with',
        'the', 'a', 'an', 'this', 'that', 'these', 'those', 
        
        # Question words
        'what', 'which', 'who', 'whom', 'whose', 'when', 'where', 'why', 'how',
        
        # Common adjectives and adverbs
        'all', 'any', 'each', 'every', 'some', 'few', 'many', 'much',
        'recent', 'latest', 'new', 'available', 'current', 'existing',
        'today', 'yesterday', 'tomorrow', 'now', 'soon', 'later',
        'related', 'relevant', 'similar', 'different',
        
        # Pronouns
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their', 'my', 'your',
        'his', 'her', 'its', 'our', 'your', 'their',
        
        # Misc
        'involve', 'involving', 'trending', 'hot', 'popular', 'whats', "what's", 'right',
        'please', 'thank', 'thanks', 'would', 'like', 'know', 'more'
    }
    
    # Phrases to completely remove
    phrases_to_remove = [
        'are there any', 'do you have', 'can i see', 'can you show me',
        'i want to see', 'i want to learn', 'i need to know', 'tell me about',
        'what are the', 'what is the', 'is there any', 'can i learn', 'can i find'
    ]
    
    # Convert to lowercase and remove punctuation
    term = prompt.lower()
    term = re.sub(r'[?.!,;:]', ' ', term)
    
    # Remove common phrases first
    for phrase in phrases_to_remove:
        term = term.replace(phrase, ' ')
    
    # Split into words
    words = term.split()
    
    # Remove model name and its variations
    model_words = set(phrase.lower().split() + plural.lower().split())
    
    # Add more model-specific words to remove
    if model_key == 'skill':
        model_words.update(['skill', 'skills', 'learn', 'learning', 'teach', 'training'])
    elif model_key == 'course':
        model_words.update(['course', 'courses', 'class', 'classes', 'training'])
    elif model_key == 'cyberchallenge':
        model_words.update(['challenge', 'challenges', 'cyber', 'cybersecurity'])
    
    words = [w for w in words if w not in model_words]
    
    # Remove filler words
    words = [w for w in words if w not in filler_words]
    
    # Remove possessive 's and punctuation from individual words
    words = [re.sub(r'[\'"]s$', '', w) for w in words]
    words = [re.sub(r'[^\w\s]', '', w) for w in words]
    
    # Remove empty strings after cleaning
    words = [w for w in words if w]
    
    # Rejoin and strip
    return ' '.join(words).strip()


def search_model(model, term='', limit=3):
    """
    If term is empty, return the most recent entries by primary key DESC.
    Otherwise, search across all searchable fields.
    """
    qs = model.objects.all()
    if not term:
        return qs.order_by('-id')[:limit]

    fields = get_searchable_fields(model)
    if not fields:
        return []

    query = Q()
    for field in fields:
        query |= Q(**{f"{field}__icontains": term})

    return qs.filter(query).distinct()[:limit]


def search_engine(prompt):
    """
    Main entry point for dynamic model-based search.

    Examples:
      "what cyber challenges are today?"
      "list all announcements"
      "skills firewall"
    """
    models = get_searchable_models('home')

    # Identify model and extract search term
    key = identify_model_from_prompt(prompt, models)
    if not key:
        return {
            'error': ("Could not identify a model in your query. "
                      f"Available models: {', '.join(models.keys())}")
        }

    term = extract_search_term(prompt, key, models)
    results = search_model(models[key], term)
    
    # Format results with metadata
    return format_model_response(results, {
        'query': prompt,
        'identified_model': key,
        'search_term': term,
        'timestamp': timezone.now().isoformat()
    })


def verify_search_connection():
    """
    Verify the search engine's connection to required services.
    Returns a dict with status information.
    """
    try:
        # Test database connection by trying to get searchable models
        models = get_searchable_models()
        if not models:
            return {
                "status": "partial",
                "message": "Connected but no searchable models found",
                "diagnostics": {
                    "database": "ok",
                    "models_found": 0
                }
            }
        
        return {
            "status": "success",
            "message": "Search engine is fully operational",
            "diagnostics": {
                "database": "ok",
                "models_found": len(models),
                "timestamp": timezone.now().isoformat()
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Search engine connection error: {str(e)}",
            "diagnostics": {
                "error_type": type(e).__name__,
                "timestamp": timezone.now().isoformat()
            }
        }


def format_model_response(model_results, query_info=None):
    """
    Format model search results into a standardized response format.
    
    Args:
        model_results: QuerySet or list of model instances
        query_info: Optional dict with query metadata
        
    Returns:
        dict: Formatted response with results and metadata
    """
    formatted = {
        "total": len(model_results) if model_results else 0,
        "results": [],
        "query_info": query_info or {}
    }
    
    if not model_results:
        return formatted
        
    # Convert model instances to dicts
    for instance in model_results:
        result = {
            "id": instance.id,
            "model": instance.__class__.__name__,
        }
        
        # Add searchable fields
        fields = get_searchable_fields(instance.__class__)
        for field in fields:
            result[field] = getattr(instance, field, None)
            
        formatted["results"].append(result)
        
    return formatted

def search(query, user=None):
    """
    Main search function that integrates model identification, term extraction,
    and database querying.
    
    Args:
        query (str): The search query from the user
        user (str, optional): User identifier for logging/tracking
        
    Returns:
        dict: Search results with metadata
    """
    # First try spell correction
    corrected_query, was_corrected = spell_correct(query)
    if was_corrected:
        logger.info(f"Corrected query '{query}' to '{corrected_query}'")
        query = corrected_query
    
    # Get available models
    models = get_searchable_models('home')
    
    # Try to identify which model the user is asking about
    model_key = identify_model_from_prompt(query, models)
    if not model_key:
        return {
            'error': 'Could not understand what type of information you are looking for.',
            'query': query,
            'timestamp': timezone.now().isoformat()
        }
    
    # Extract the actual search term
    search_term = extract_search_term(query, model_key, models)
    
    # Get the results
    results = search_model(models[model_key], search_term)
    
    # Format the response
    return format_model_response(results, {
        'query': query,
        'corrected_query': corrected_query if was_corrected else None,
        'identified_model': model_key,
        'search_term': search_term,
        'user': user,
        'timestamp': timezone.now().isoformat()
    })

def format_search_results(search_results, query):
    """
    Format search results into a chatbot-friendly response format.
    
    Args:
        search_results (dict): Results from the search function
        query (str): Original search query
        
    Returns:
        dict: Formatted results with title, description, and URL for each result
    """
    formatted = {
        'total': 0,
        'results': [],
        'query': query,
        'timestamp': timezone.now().isoformat()
    }
    
    # Handle error case
    if isinstance(search_results, dict) and 'error' in search_results:
        formatted['error'] = search_results['error']
        return formatted
    
    # Get results from the model_response format
    if isinstance(search_results, dict) and 'results' in search_results:
        results = search_results['results']
        formatted['total'] = len(results)
        
        for result in results:
            formatted['results'].append(_format_result_item(result))
    
    return formatted

def _format_result_item(result):
    model_name = result.get('model', '').lower()
    id_str = str(result.get('id', ''))
    cfg = MODEL_FORMAT.get(model_name)
    if cfg:
        name_or_title = result.get('name') or result.get('title') or f'#{id_str}'
        title = f"{cfg['emoji']} {cfg['label']}: {name_or_title}"
        if cfg.get('append_difficulty') and 'difficulty' in result:
            title += f" ({result['difficulty']})"
        url = cfg['url_pattern'].format(id=result.get('id'))
    else:
        title_fields = ['title', 'name', 'subject', 'heading']
        title = next((result.get(f) for f in title_fields if f in result), f"{model_name.title()} #{id_str}")
        url = f"/{model_name}/{result.get('id')}"
    # Build description (include 'message' for announcements)
    desc_fields = ['message', 'description', 'content', 'text', 'body', 'summary']
    description = next((result.get(f) for f in desc_fields if f in result), "No description available").strip()
    if len(description) > 200:
        description = description[:197] + "..."
    return {
        'title': title,
        'description': description,
        'url': url,
        'model': model_name,
        'id': result.get('id')
    }

def extract_project_keywords(message):
    """
    Extract project-related keywords from a message.
    This is a legacy function that uses our new search functionality.
    """
    # Get available models
    models = get_searchable_models('home')
    
    # Try to identify which model the user is asking about
    model_key = identify_model_from_prompt(message, models)
    if not model_key:
        return []
    
    # Extract the search term
    search_term = extract_search_term(message, model_key, models)
    
    # Return both the model key and any additional terms
    keywords = [model_key]
    if search_term:
        keywords.extend(search_term.split())
    
    return keywords

def extract_keywords(message):
    """
    Legacy function that now uses extract_project_keywords.
    """
    return extract_project_keywords(message)

# Example usage:
# >>> search_engine('cyber challenges')
# Returns top 3 CyberChallenge objects
# >>> search_engine('announcement')
# Returns latest 3 Announcement objects
