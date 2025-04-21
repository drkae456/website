import logging
logger = logging.getLogger(__name__)

from django.db.models import Q, F, Value, FloatField, Case, When, IntegerField
from django.db.models.functions import Length
import re
import string
from functools import reduce
import operator
# Import local models first
from .models import FAQ, PageContent, ChatSession, ChatMessage, CompanyInformation, Project, ProductService 
# Then import models from other apps
from home.models import (
    CyberChallenge, 
    Course,
    Skill,
    Progress,
    Contact,
    ContactSubmission,
    Experience,
    Webpage,
    DDT_contact,
    Job,
    JobApplication,
    Article,
    Smishingdetection_join_us,
    Projects_join_us,
    UserChallenge,
    Announcement,
    SecurityEvent,
    LeaderBoardTable
)
from django.db import models
from django.db import connection
from django.db.utils import OperationalError

# List of common English stopwords
STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what', 
    'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than', 'such',
    'when', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other',
    'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
    'too', 'very', 'can', 'will', 'should', 'now', 'do', 'does', 'did',
    'has', 'have', 'had', 'is', 'am', 'are', 'was', 'were', 'be', 'been',
    'being', 'into', 'about', 'between', 'during', 'before', 'after', 'above',
    'below', 'at', 'by', 'for', 'with', 'of', 'on', 'in', 'to', 'from',
    'get', 'gets', 'getting', 'got', 'would', 'could', 'should', 'shall',
    'tell', 'about', 'show', 'explain', 'give', 'please', 'thanks', 'help',
    'need', 'information', 'info', 'know', 'learn', 'understand', 'want'
}

# Project-specific keywords dictionary
PROJECT_KEYWORDS = {
    'appattack': ['appattack', 'app attack', 'app-attack', 'web security', 'web app', 'vulnerability'],
    'deakin_threatmirror': ['deakinthreatmirror', 'deakin threatmirror', 'threatmirror', 'threat mirror', 
                           'deakin_threatmirror', 'threat intelligence', 'threat visualization'],
    'smishing_detection': ['smishing', 'sms', 'phishing', 'smishing detection', 'smishing_detection', 
                          'text message', 'mobile security'],
    'malware_visualization': ['malware', 'malware visualization', 'malware_visualization', 
                             'malware visualisation', 'malware analysis'],
    'vr': ['vr', 'virtual reality', 'vr security', 'vr project', 'virtual training'],
    'pt_gui': ['pt gui', 'ptgui', 'penetration testing', 'pt_gui', 'deakin detonator', 'ddt', 
               'pen testing', 'pentest']
}

# Fields to exclude from search (answers, explanations subcategories)
EXCLUDED_FIELDS = [
    'answer',
    'explanation',
    'password',
    'secret',
    'token',
    'api_key'
]

def calculate_relevance(content, keywords):
    """Calculate relevance score based on keyword matches in content"""
    if not content or not keywords:
        return 0
    return sum(1 for keyword in keywords if keyword.lower() in content.lower())

def preprocess_query(query):
    """
    Preprocess the user query:
    1. Convert to lowercase
    2. Remove punctuation
    3. Remove extra whitespace
    
    Args:
        query (str): The user's query string
        
    Returns:
        str: Preprocessed query
    """
    # Handle None or empty query
    if not query:
        return ""
        
    # Convert to lowercase
    query = query.lower()
    
    # Remove punctuation (except hyphens which might be part of terms like "app-attack")
    punctuation_to_remove = string.punctuation.replace('-', '')
    translator = str.maketrans('', '', punctuation_to_remove)
    query = query.translate(translator)
    
    # Remove extra whitespace
    query = ' '.join(query.split())
    
    return query

def remove_stopwords(query):
    """
    Remove common stopwords from the query
    
    Args:
        query (str): Preprocessed query
        
    Returns:
        str: Query with stopwords removed
    """
    words = query.split()
    filtered_words = [word for word in words if word.lower() not in STOPWORDS]
    
    # If all words were stopwords, return the original query
    if not filtered_words and words:
        return query
        
    return ' '.join(filtered_words)

def extract_project_keywords(query):
    """
    Extract project-specific keywords from the query
    
    Args:
        query (str): The preprocessed user query
        
    Returns:
        list: List of project keywords found in the query
    """
    found_keywords = []
    
    # Check if any project keyword is in the query
    for project, variations in PROJECT_KEYWORDS.items():
        if any(variation in query for variation in variations):
            found_keywords.append(project)
            
    return found_keywords

def extract_general_keywords(query):
    """
    Extract general keywords from the query after removing stopwords
    
    Args:
        query (str): The user's query
        
    Returns:
        list: List of general keywords
    """
    # Preprocess and remove stopwords
    processed_query = preprocess_query(query)
    no_stopwords = remove_stopwords(processed_query)
    
    # Extract words of at least 3 characters as keywords
    keywords = [word for word in no_stopwords.split() if len(word) >= 3]
    
    # Special handling for important model names that might be filtered by stopwords
    special_keywords = ['experience', 'experiences']
    for special in special_keywords:
        if special in processed_query and special not in keywords:
            keywords.append(special)
    
    return keywords

def search_database(query):
    """
    Search the database for relevant content using Django's ORM capabilities.
    
    Args:
        query (str): The search query
        
    Returns:
        dict: Dictionary containing search results and metadata
    """
    try:
        # Initialize response
        response = {
            'query': query,
            'results': [],
            'total_results': 0,
            'categories': set()  # Using set to avoid duplicates
        }
        
        # Handle empty query case
        if not query or query.strip() == "":
            return response
            
        # Extract keywords for searching
        keywords = [k.strip() for k in query.split() if k.strip()]
        if not keywords:
            return response
            
        # Search PageContent
        try:
            page_q = Q()
            for keyword in keywords:
                page_q |= (
                    Q(title__icontains=keyword) |
                    Q(content__icontains=keyword) |
                    Q(keywords__icontains=keyword) |
                    Q(page_category__icontains=keyword)
                )
            
            page_results = PageContent.objects.filter(page_q).annotate(
                relevance=Case(
                    When(title__icontains=query, then=Value(10)),
                    When(keywords__icontains=query, then=Value(8)),
                    When(content__icontains=query, then=Value(5)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            ).order_by('-relevance', '-priority')

            for result in page_results:
                response['results'].append({
                    'category': 'page_content',
                    'title': result.title,
                    'content': result.content,
                    'page_path': result.page_path,
                    'priority': result.priority,
                    'relevance_score': result.relevance
                })
                response['categories'].add('page_content')
        except Exception as e:
            logger.error(f"Error searching PageContent: {str(e)}")

        # Search FAQ
        try:
            faq_q = Q()
            for keyword in keywords:
                faq_q |= (
                    Q(question__icontains=keyword) |
                    Q(answer__icontains=keyword) |
                    Q(keywords__icontains=keyword) |
                    Q(category__icontains=keyword)
                )
            
            faq_results = FAQ.objects.filter(faq_q).annotate(
                relevance=Case(
                    When(question__icontains=query, then=Value(10)),
                    When(keywords__icontains=query, then=Value(8)),
                    When(answer__icontains=query, then=Value(5)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )

            for result in faq_results:
                response['results'].append({
                    'category': 'faq',
                    'title': result.question,
                    'content': result.answer,
                    'relevance_score': result.relevance
                })
                response['categories'].add('faq')
        except Exception as e:
            logger.error(f"Error searching FAQ: {str(e)}")

        # Search Project
        try:
            project_q = Q()
            for keyword in keywords:
                project_q |= (
                    Q(name__icontains=keyword) |
                    Q(description__icontains=keyword) |
                    Q(keywords__icontains=keyword)
                )
            
            project_results = Project.objects.filter(project_q).annotate(
                relevance=Case(
                    When(name__icontains=query, then=Value(10)),
                    When(keywords__icontains=query, then=Value(8)),
                    When(description__icontains=query, then=Value(5)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )

            for result in project_results:
                response['results'].append({
                    'category': 'projects',
                    'title': result.name,
                    'content': result.description,
                    'relevance_score': result.relevance
                })
                response['categories'].add('projects')
        except Exception as e:
            logger.error(f"Error searching Project: {str(e)}")

        # Update total results
        response['total_results'] = len(response['results'])
        
        # Sort results by relevance score in descending order
        response['results'].sort(key=lambda x: (-x['relevance_score'], x.get('priority', 0)))
        
        # Convert categories set to list for JSON serialization
        response['categories'] = list(response['categories'])
        
        return response
        
    except Exception as e:
        logger.error(f"Error in search_database: {str(e)}")
        return {
            'query': query,
            'results': [],
            'total_results': 0,
            'categories': []
        }

def rank_results(results, query, keywords):
    """
    Rank search results based on relevance to the query
    
    Args:
        results (dict): The search results dictionary
        query (str): The user query
        keywords (list): Keywords extracted from the query
        
    Returns:
        dict: Ranked search results
    """
    ranked_results = {}
    
    # Process each result category
    for category, items in results.items():
        try:
            if items:
                ranked_items = list(items)
                
                # Apply category-specific ranking logic
                if category == 'page_content':
                    # Sort by priority first (descending), then by relevance score
                    ranked_items.sort(key=lambda x: (-getattr(x, 'priority', 0), get_relevance_score(x, query, keywords, category)))
                    
                elif category == 'challenges':
                    # For challenges, prioritize by difficulty level (easy first) then by relevance
                    try:
                        ranked_items.sort(
                            key=lambda x: (
                                0 if getattr(x, 'difficulty', '') == 'easy' else (1 if getattr(x, 'difficulty', '') == 'medium' else 2),
                                get_relevance_score(x, query, keywords, category)
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Error sorting challenges by difficulty: {str(e)}")
                        # Fallback to just relevance sorting
                        ranked_items.sort(key=lambda x: get_relevance_score(x, query, keywords, category))
                    
                elif category == 'announcements':
                    # For announcements, only show active ones and sort by date
                    if hasattr(items[0], 'isActive'):
                        ranked_items = [item for item in ranked_items if getattr(item, 'isActive', True)]
                    if hasattr(items[0], 'created_at'):
                        ranked_items.sort(key=lambda x: getattr(x, 'created_at', 0), reverse=True)
                    else:
                        ranked_items.sort(key=lambda x: get_relevance_score(x, query, keywords, category))
                    
                elif category == 'jobs':
                    # For jobs, prioritize more recent postings
                    if hasattr(items[0], 'posted_date'):
                        ranked_items.sort(key=lambda x: getattr(x, 'posted_date', 0), reverse=True)
                    else:
                        ranked_items.sort(key=lambda x: get_relevance_score(x, query, keywords, category))
                    
                else:
                    # Default sorting by relevance score
                    ranked_items.sort(key=lambda x: get_relevance_score(x, query, keywords, category))
                
                ranked_results[category] = ranked_items
            else:
                ranked_results[category] = []
        except Exception as e:
            logger.error(f"Error ranking {category} results: {str(e)}")
            ranked_results[category] = []
    
    return ranked_results

def get_relevance_score(item, query, keywords, item_type):
    """
    Calculate relevance score for a result item
    
    Args:
        item: The database item
        query (str): The user query
        keywords (list): Keywords extracted from the query
        item_type (str): Type of item (category from results dict)
        
    Returns:
        float: Relevance score (higher is more relevant)
    """
    score = 0
    
    try:
        # Different scoring based on item type
        if item_type == 'page_content':
            # Title match is most important
            if hasattr(item, 'title') and any(keyword in item.title.lower() for keyword in keywords):
                score += 5
            
            # Keyword field match is next most important
            if hasattr(item, 'keywords') and item.keywords:
                item_keywords = item.keywords.lower().split(',')
                for keyword in keywords:
                    if any(keyword in kw for kw in item_keywords):
                        score += 3
            
            # Content match is least important but still counts
            if hasattr(item, 'content'):
                for keyword in keywords:
                    if keyword in item.content.lower():
                        score += 1
            
            # Boost by priority field
            score += getattr(item, 'priority', 0) * 2
            
        elif item_type == 'faqs':
            # Question match is most important
            if hasattr(item, 'question') and any(keyword in item.question.lower() for keyword in keywords):
                score += 5
            
            # Keyword field match
            if hasattr(item, 'keywords') and item.keywords:
                item_keywords = item.keywords.lower().split(',')
                for keyword in keywords:
                    if any(keyword in kw for kw in item_keywords):
                        score += 3
            
            # Category match
            if hasattr(item, 'category') and any(keyword in item.category.lower() for keyword in keywords):
                score += 2
                    
        elif item_type == 'challenges':
            # Title match is most important
            if hasattr(item, 'title') and any(keyword in item.title.lower() for keyword in keywords):
                score += 5
            
            # Category match
            if hasattr(item, 'category') and any(keyword in item.category.lower() for keyword in keywords):
                score += 3
            
            # Description match
            if hasattr(item, 'description'):
                for keyword in keywords:
                    if keyword in item.description.lower():
                        score += 1
                    
        elif item_type == 'projects':
            # Name match is most important
            if hasattr(item, 'name') and any(keyword in item.name.lower() for keyword in keywords):
                score += 5
                
            # Description match
            if hasattr(item, 'description'):
                for keyword in keywords:
                    if keyword in item.description.lower():
                        score += 2
                    
            # Status match
            if hasattr(item, 'status') and any(keyword in item.status.lower() for keyword in keywords):
                score += 1
                
            # Keywords match
            if hasattr(item, 'keywords') and item.keywords:
                item_keywords = item.keywords.lower().split(',')
                for keyword in keywords:
                    if any(keyword in kw for kw in item_keywords):
                        score += 3
                        
        elif item_type == 'courses':
            # Name match is most important
            if hasattr(item, 'name') and any(keyword in item.name.lower() for keyword in keywords):
                score += 5
                
            # Description match
            if hasattr(item, 'description'):
                for keyword in keywords:
                    if keyword in item.description.lower():
                        score += 2
                        
            # Category match
            if hasattr(item, 'category') and any(keyword in item.category.lower() for keyword in keywords):
                score += 3
                
        elif item_type == 'skills':
            # Name match is most important
            if hasattr(item, 'name') and any(keyword in item.name.lower() for keyword in keywords):
                score += 5
                
            # Description match
            if hasattr(item, 'description'):
                for keyword in keywords:
                    if keyword in item.description.lower():
                        score += 2
                        
            # Category match
            if hasattr(item, 'category') and any(keyword in item.category.lower() for keyword in keywords):
                score += 3
                
        elif item_type == 'jobs':
            # Title match is most important
            if hasattr(item, 'title') and any(keyword in item.title.lower() for keyword in keywords):
                score += 5
                
            # Description match
            if hasattr(item, 'description'):
                for keyword in keywords:
                    if keyword in item.description.lower():
                        score += 2
                        
            # Location and job_type match
            if hasattr(item, 'location') and any(keyword in item.location.lower() for keyword in keywords):
                score += 3
                
            if hasattr(item, 'job_type') and any(keyword in item.job_type.lower() for keyword in keywords):
                score += 3
                
        elif item_type == 'articles':
            # Title match is most important
            if hasattr(item, 'title') and any(keyword in item.title.lower() for keyword in keywords):
                score += 5
                
            # Content match
            if hasattr(item, 'content'):
                for keyword in keywords:
                    if keyword in item.content.lower():
                        score += 2
                        
            # Category and tags match
            if hasattr(item, 'category') and any(keyword in item.category.lower() for keyword in keywords):
                score += 3
                
            if hasattr(item, 'tags') and item.tags:
                item_tags = item.tags.lower().split(',')
                for keyword in keywords:
                    if any(keyword in tag for tag in item_tags):
                        score += 3
                        
        elif item_type == 'announcements':
            # Message match
            if hasattr(item, 'message'):
                for keyword in keywords:
                    if keyword in item.message.lower():
                        score += 3
                    
            # Recent announcements get higher score
            if hasattr(item, 'created_at'):
                # This is a simplistic approach - you might want to use actual date comparison
                score += 2
                
        elif item_type == 'experiences':
            # Name match
            if hasattr(item, 'name') and any(keyword in item.name.lower() for keyword in keywords):
                score += 3
                
            # Feedback match
            if hasattr(item, 'feedback'):
                for keyword in keywords:
                    if keyword in item.feedback.lower():
                        score += 2
                        
        elif item_type == 'contact_info' or item_type == 'join_requests':
            # Generic scoring for these categories
            # Name match
            if hasattr(item, 'name') and any(keyword in item.name.lower() for keyword in keywords):
                score += 3
                
            # Subject match
            if hasattr(item, 'subject') and any(keyword in item.subject.lower() for keyword in keywords):
                score += 4
                
            # Message match
            if hasattr(item, 'message'):
                for keyword in keywords:
                    if keyword in item.message.lower():
                        score += 1
    except Exception as e:
        logger.error(f"Error calculating relevance score for {item_type}: {str(e)}")
        # Return a minimal score so it still appears in results
        score = 0.1
    
    return score

def process_query(query):
    """
    Process a search query and return formatted results
    
    Args:
        query (str): The search query
        
    Returns:
        dict: Formatted search results
    """
    try:
        # Preprocess the query
        processed_query = preprocess_query(query)
        if not processed_query:
            return {
                'query': query,
                'results': [],
                'total_results': 0,
                'categories': []
            }
            
        # Extract keywords
        general_keywords = extract_general_keywords(processed_query)
        project_keywords = extract_project_keywords(processed_query)
        
        # If no valid keywords found, return empty results
        if not general_keywords and not project_keywords:
            return {
                'query': query,
                'results': [],
                'total_results': 0,
                'categories': []
            }
            
        # Search the database
        search_results = search_database(processed_query)
        
        # Ensure total_results is 0 if no results found
        if not search_results.get('results'):
            search_results['total_results'] = 0
            
        return search_results
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {
            'query': query,
            'results': [],
            'total_results': 0,
            'categories': []
        }

def get_best_response(query_results):
    """
    Determine the best response based on search results
    
    Args:
        query_results (dict): The output from process_query()
        
    Returns:
        tuple: (response_text, response_type, source_items)
    """
    try:
        # Define a priority order for result types we actually have
        priority_order = [
            'projects',  # Projects first
            'experiences',
            'challenges',
            'articles',  # Articles before courses
            'courses',
            'skills',
            'jobs',
            'announcements',
            'page_content'
        ]
        
        # Find the category with the highest relevance score
        best_category = None
        best_score = -1
        best_items = None
        
        # Group results by category
        results_by_category = {}
        for item in query_results.get('results', []):
            category = item['category']
            if category not in results_by_category:
                results_by_category[category] = []
            results_by_category[category].append(item)
        
        # Find the best category based on priority order and relevance
        for category in priority_order:
            items = results_by_category.get(category, [])
            if items:
                # Get the highest relevance score for this category
                category_score = max(
                    float(item.get('relevance_score', 0) or 0)
                    for item in items
                )
                
                # If this category has a higher score, or it's the first valid category
                if category_score > best_score or best_category is None:
                    best_score = category_score
                    best_category = category
                    best_items = items
        
        if best_category:
            return (None, best_category, best_items)
        
        # No good matches
        return (None, 'no_match', None)
        
    except Exception as e:
        logger.error(f"Error in get_best_response: {str(e)}")
        return (None, 'no_match', None)

def format_search_results(search_results, query):
    """
    Format search results into a conversational response

    Args:
        search_results (dict): The search results from process_query
        query (str): The original search query

    Returns:
        str: Formatted conversational response string
    """
    try:
        results_list = search_results.get('results', [])
        if not results_list:
            return f"""I couldn't find specific information for '{query}'. Can you try rephrasing or asking about one of our main projects?<br><br>Here are some popular topics you might be interested in:<br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about AppAttack')">AppAttack</button><br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about PT GUI')">PT GUI</button><br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about Smishing Detection')">Smishing Detection</button>"""

        # Sort results by relevance score to get the most relevant result
        results_list.sort(key=lambda x: (-x.get('relevance_score', 0), -x.get('priority', 0)))
        best_result = results_list[0]
        category = best_result.get('category', 'unknown')

        # Format response based on the category
        if category == 'page_content':
            response = f"""Let me tell you about {best_result['title']}! 🚀<br><br>{best_result['content']}<br><br>"""
            if best_result.get('page_path'):
                response += f"""🔗 <a href="{best_result['page_path']}" class="learn-more-link">Learn more here</a><br><br>"""
            response += """Want to know more? Try asking about:<br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about AppAttack')">AppAttack</button><br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about PT GUI')">PT GUI</button><br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about Smishing Detection')">Smishing Detection</button>"""
            return response

        elif category == 'faq':
            return f"""Here's what I found about that! 💡<br><br>{best_result['content']}<br><br>Want to know more? Try asking about:<br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about AppAttack')">AppAttack</button><br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about PT GUI')">PT GUI</button><br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about Smishing Detection')">Smishing Detection</button>"""

        elif category == 'projects':
            response = f"""Oh, you're interested in {best_result['title']}? That's fantastic! 🛠️<br><br>{best_result['content']}<br><br>"""
            response += f"""Want to get involved? Try asking:<br>
            <button class="suggestion-btn" onclick="sendMessage('how to join {best_result['title']}')">How to join {best_result['title']}</button><br><br>
            Or learn about other projects:<br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about AppAttack')">AppAttack</button><br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about PT GUI')">PT GUI</button><br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about Smishing Detection')">Smishing Detection</button>"""
            return response

        else:
            # Default response for other categories
            response = f"""Here's what I found about {best_result.get('title', 'this topic')}! 🔍<br><br>{best_result.get('content', 'No specific content available')}<br><br>"""
            response += """Want to know more? Try asking about:<br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about AppAttack')">AppAttack</button><br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about PT GUI')">PT GUI</button><br>
            • <button class="suggestion-btn" onclick="sendMessage('Tell me about Smishing Detection')">Smishing Detection</button>"""
            return response

    except Exception as e:
        logger.error(f"Error formatting search results: {str(e)}")
        return """I'm sorry, I encountered an error while processing your request. Please try asking about our main projects like AppAttack, PT GUI, or Smishing Detection."""

def format_model_response(items, model_type):
    """
    Format search results into a readable HTML response based on the model type.
    
    Args:
        items (list): List of search result items
        model_type (str): Type of model being formatted
        
    Returns:
        str: Formatted HTML response
    """
    if not items:
        return f"No {model_type} found matching your query."
        
    try:
        response_text = ""
        
        # Sort items by relevance score if available
        if isinstance(items, list) and items and 'relevance_score' in items[0]:
            items = sorted(items, key=lambda x: -x['relevance_score'])
        
        # Limit to top 5 results for each category
        items = items[:5]
        
        if model_type == 'page_content':
            response_text = "Here are the most relevant pages I found:<br><br>"
            for item in items:
                response_text += f"<strong>{item.get('title', 'Untitled')}</strong><br>"
                # Truncate content if too long
                content = item.get('content', '')
                if len(content) > 300:
                    content = content[:300] + "..."
                response_text += f"{content}<br>"
                if item.get('page_path'):
                    response_text += f'<a href="{item["page_path"]}" class="learn-more-link">Learn more</a><br><br>'
                
        elif model_type == 'faq':
            response_text = "Here are some relevant FAQs:<br><br>"
            for item in items:
                response_text += f"<strong>Q: {item.get('title', 'No question provided')}</strong><br>"
                response_text += f"A: {item.get('content', 'No answer provided')}<br>"
                if item.get('category'):
                    response_text += f"Category: {item['category']}<br><br>"
                
        elif model_type == 'challenges':
            response_text = "Here are some cybersecurity challenges you might be interested in:<br><br>"
            for item in items:
                response_text += f"<strong>{item.get('title', 'Untitled Challenge')}</strong>"
                if item.get('difficulty'):
                    response_text += f" ({item['difficulty']})"
                response_text += "<br>"
                response_text += f"{item.get('description', 'No description available')}<br>"
                if item.get('category'):
                    response_text += f"Category: {item['category']}<br><br>"
                
        elif model_type == 'experiences':
            response_text = "Here are some relevant user experiences:<br><br>"
            for item in items:
                response_text += f"<strong>{item.get('name', 'Anonymous User')}</strong><br>"
                response_text += f"{item.get('feedback', 'No feedback provided')}<br>"
                if item.get('created_at'):
                    try:
                        response_text += f"Shared on: {item['created_at'].strftime('%B %d, %Y')}<br><br>"
                    except (AttributeError, TypeError):
                        response_text += f"Shared on: {item['created_at']}<br><br>"
                
        else:
            # Generic formatter for other types
            response_text = f"Here are the relevant {model_type}:<br><br>"
            for item in items:
                # Get the first field that could serve as a title
                title_field = next((field for field in ['title', 'name', 'question'] if field in item), None)
                if title_field:
                    response_text += f"<strong>{item[title_field]}</strong><br>"
                
                # Add other relevant fields
                for key, value in item.items():
                    if key not in ['title', 'name', 'question', 'relevance_score', 'category'] and value:
                        # Format the key nicely
                        formatted_key = key.replace('_', ' ').title()
                        # Handle different value types
                        if isinstance(value, (list, tuple)):
                            value = ', '.join(str(v) for v in value)
                        elif isinstance(value, dict):
                            value = ', '.join(f"{k}: {v}" for k, v in value.items())
                        response_text += f"{formatted_key}: {value}<br>"
                response_text += "<br>"
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error formatting {model_type} response: {str(e)}")
        return f"An error occurred while formatting the {model_type} results. Please try again."

def search(query):
    """
    Search function that searches across all content types and returns relevant results
    
    Args:
        query (str): The user's search query
        
    Returns:
        dict: A dictionary containing search results for different content types
    """
    import logging
    import operator
    from functools import reduce
    from django.db.models import Q
    
    # Set up logging
    logger = logging.getLogger(__name__)
    
    # Initialize empty results dict with all possible content types
    results = {
        'ranked_results': {
            'page_content': [],
            'projects': [],  # Changed from 'project' to 'projects'
            'faqs': [],
            'challenges': [],
            'courses': [],
            'skills': [],
            'jobs': [],
            'articles': [],
            'announcements': [],
            'experiences': [],
            'contact_info': [],
            'join_requests': []
        },
        'project_keywords': []
    }
    
    try:
        # Log the search query
        logger.info(f"Searching for: {query}")
        
        # Process query: convert to lowercase and extract keywords
        query = query.lower()
        # Remove common stop words for better keyword extraction
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'of', 'for', 'to', 'and', 'or', 'is', 'are'}
        keywords = [word for word in query.split() if word not in stop_words and len(word) > 2]
        
        # If no valid keywords found, use the original query words as fallback
        if not keywords and query:
            keywords = query.split()
        
        # Log the extracted keywords
        logger.info(f"Search keywords: {keywords}")
        
        # Building query filter conditions
        # This creates a complex Q object that will match any of the keywords in any of the specified fields
        if keywords:
            # Search in Page model
            try:
                from .models import Page
                page_q_objects = [Q(title__icontains=keyword) | Q(content__icontains=keyword) | Q(keywords__icontains=keyword) for keyword in keywords]
                if page_q_objects:
                    page_query = reduce(operator.or_, page_q_objects)
                    pages = Page.objects.filter(page_query)
                    # Add relevance score to each result
                    for page in pages:
                        page.relevance_score = get_relevance_score(page, query, keywords, 'page_content')
                    results['ranked_results']['page_content'] = pages
            except Exception as e:
                logger.error(f"Error searching Page model: {str(e)}")
                results['ranked_results']['page_content'] = []
            
            # Search in FAQ model
            try:
                from .models import FAQ
                faq_q_objects = [Q(question__icontains=keyword) | Q(answer__icontains=keyword) | Q(category__icontains=keyword) | Q(keywords__icontains=keyword) for keyword in keywords]
                if faq_q_objects:
                    faq_query = reduce(operator.or_, faq_q_objects)
                    faqs = FAQ.objects.filter(faq_query)
                    # Add relevance score to each result
                    for faq in faqs:
                        faq.relevance_score = get_relevance_score(faq, query, keywords, 'faqs')
                    results['ranked_results']['faqs'] = faqs
            except Exception as e:
                logger.error(f"Error searching FAQ model: {str(e)}")
                results['ranked_results']['faqs'] = []
            
            # Search in Challenge model
            try:
                from .models import Challenge
                challenge_q_objects = [Q(title__icontains=keyword) | Q(description__icontains=keyword) | Q(category__icontains=keyword) for keyword in keywords]
                if challenge_q_objects:
                    challenge_query = reduce(operator.or_, challenge_q_objects)
                    challenges = Challenge.objects.filter(challenge_query)
                    # Add relevance score to each result
                    for challenge in challenges:
                        challenge.relevance_score = get_relevance_score(challenge, query, keywords, 'challenges')
                    results['ranked_results']['challenges'] = challenges
            except Exception as e:
                logger.error(f"Error searching Challenge model: {str(e)}")
                results['ranked_results']['challenges'] = []
            
            # Search in Project model
            try:
                project_query = Q()
                for keyword in keywords:
                    # Project model uses title with choices
                    project_query |= Q(title__icontains=keyword)
                
                if project_query:
                    project_results = Project.objects.filter(project_query)
                    # Add relevance score to each result
                    for project in project_results:
                        project.relevance_score = get_relevance_score(project, query, keywords, 'project')
                    results['ranked_results']['projects'] = project_results  # Note: Changed from 'project' to 'projects'
            except Exception as e:
                logger.error(f"Error searching Projects: {str(e)}")
                results['ranked_results']['projects'] = []  # Note: Changed from 'project' to 'projects'
            
            # Search in Course model
            try:
                from .models import Course
                course_q_objects = [Q(name__icontains=keyword) | Q(description__icontains=keyword) | Q(category__icontains=keyword) for keyword in keywords]
                if course_q_objects:
                    course_query = reduce(operator.or_, course_q_objects)
                    courses = Course.objects.filter(course_query)
                    # Add relevance score to each result
                    for course in courses:
                        course.relevance_score = get_relevance_score(course, query, keywords, 'courses')
                    results['ranked_results']['courses'] = courses
            except Exception as e:
                logger.error(f"Error searching Course model: {str(e)}")
                results['ranked_results']['courses'] = []
            
            # Search in Skill model
            try:
                from .models import Skill
                skill_q_objects = [Q(name__icontains=keyword) | Q(description__icontains=keyword) | Q(category__icontains=keyword) for keyword in keywords]
                if skill_q_objects:
                    skill_query = reduce(operator.or_, skill_q_objects)
                    skills = Skill.objects.filter(skill_query)
                    # Add relevance score to each result
                    for skill in skills:
                        skill.relevance_score = get_relevance_score(skill, query, keywords, 'skills')
                    results['ranked_results']['skills'] = skills
            except Exception as e:
                logger.error(f"Error searching Skill model: {str(e)}")
                results['ranked_results']['skills'] = []
            
            # Search in Job model
            try:
                from .models import Job
                job_q_objects = [Q(title__icontains=keyword) | Q(description__icontains=keyword) | Q(location__icontains=keyword) | Q(job_type__icontains=keyword) for keyword in keywords]
                if job_q_objects:
                    job_query = reduce(operator.or_, job_q_objects)
                    jobs = Job.objects.filter(job_query)
                    # Add relevance score to each result
                    for job in jobs:
                        job.relevance_score = get_relevance_score(job, query, keywords, 'jobs')
                    results['ranked_results']['jobs'] = jobs
            except Exception as e:
                logger.error(f"Error searching Job model: {str(e)}")
                results['ranked_results']['jobs'] = []
            
            # Search in Article model
            try:
                from .models import Article
                article_q_objects = [Q(title__icontains=keyword) | Q(content__icontains=keyword) | Q(category__icontains=keyword) | Q(tags__icontains=keyword) for keyword in keywords]
                if article_q_objects:
                    article_query = reduce(operator.or_, article_q_objects)
                    articles = Article.objects.filter(article_query)
                    # Add relevance score to each result
                    for article in articles:
                        article.relevance_score = get_relevance_score(article, query, keywords, 'articles')
                    results['ranked_results']['articles'] = articles
            except Exception as e:
                logger.error(f"Error searching Article model: {str(e)}")
                results['ranked_results']['articles'] = []
            
            # Search in Announcement model
            try:
                from .models import Announcement
                announcement_q_objects = [Q(message__icontains=keyword) for keyword in keywords]
                if announcement_q_objects:
                    announcement_query = reduce(operator.or_, announcement_q_objects)
                    announcements = Announcement.objects.filter(announcement_query)
                    # Filter only active announcements
                    announcements = [a for a in announcements if getattr(a, 'isActive', True)]
                    # Add relevance score to each result
                    for announcement in announcements:
                        announcement.relevance_score = get_relevance_score(announcement, query, keywords, 'announcements')
                    results['ranked_results']['announcements'] = announcements
            except Exception as e:
                logger.error(f"Error searching Announcement model: {str(e)}")
                results['ranked_results']['announcements'] = []
            
            # Search in Experience model
            try:
                # Use the already imported Experience model from home.models
                experience_q_objects = [Q(name__icontains=keyword) | Q(feedback__icontains=keyword) for keyword in keywords]
                if experience_q_objects:
                    experience_query = reduce(operator.or_, experience_q_objects)
                    experiences = Experience.objects.filter(experience_query)
                    # Add relevance score to each result
                    for experience in experiences:
                        experience.relevance_score = get_relevance_score(experience, query, keywords, 'experiences')
                    results['ranked_results']['experiences'] = experiences
            except Exception as e:
                logger.error(f"Error searching Experience model: {str(e)}")
                results['ranked_results']['experiences'] = []
            
            # Search in Contact model
            try:
                from .models import Contact, DDT_contact
                # Combine searches from both contact models into one list
                contact_q_objects = [Q(name__icontains=keyword) | Q(subject__icontains=keyword) | Q(message__icontains=keyword) for keyword in keywords]
                if contact_q_objects:
                    contact_query = reduce(operator.or_, contact_q_objects)
                    contacts = list(Contact.objects.filter(contact_query))
                    
                    # Add DDT contacts
                    ddt_contact_q_objects = [Q(name__icontains=keyword) | Q(subject__icontains=keyword) | Q(message__icontains=keyword) for keyword in keywords]
                    if ddt_contact_q_objects:
                        ddt_contact_query = reduce(operator.or_, ddt_contact_q_objects)
                        ddt_contacts = DDT_contact.objects.filter(ddt_contact_query)
                        contacts.extend(ddt_contacts)
                    
                    # Add relevance score to each result
                    for contact in contacts:
                        contact.relevance_score = get_relevance_score(contact, query, keywords, 'contact_info')
                    results['ranked_results']['contact_info'] = contacts
            except Exception as e:
                logger.error(f"Error searching Contact models: {str(e)}")
                results['ranked_results']['contact_info'] = []
            
            # Search in Join Request models
            try:
                from .models import Smishingdetection_join_us, Projects_join_us
                # Combine searches from both join request models into one list
                join_req_list = []
                
                smishing_q_objects = [Q(name__icontains=keyword) | Q(subject__icontains=keyword) | Q(message__icontains=keyword) for keyword in keywords]
                if smishing_q_objects:
                    smishing_query = reduce(operator.or_, smishing_q_objects)
                    smishing_requests = Smishingdetection_join_us.objects.filter(smishing_query)
                    join_req_list.extend(smishing_requests)
                
                projects_q_objects = [Q(name__icontains=keyword) | Q(subject__icontains=keyword) | Q(message__icontains=keyword) for keyword in keywords]
                if projects_q_objects:
                    projects_query = reduce(operator.or_, projects_q_objects)
                    project_requests = Projects_join_us.objects.filter(projects_query)
                    join_req_list.extend(project_requests)
                
                # Add relevance score to each result
                for join_req in join_req_list:
                    join_req.relevance_score = get_relevance_score(join_req, query, keywords, 'join_requests')
                
                results['ranked_results']['join_requests'] = join_req_list
            except Exception as e:
                logger.error(f"Error searching Join Request models: {str(e)}")
                results['ranked_results']['join_requests'] = []
                
    except Exception as e:
        logger.error(f"General error in search function: {str(e)}")
        # If a general error occurs, ensure all result categories are set to empty lists
        for key in results['ranked_results']:
            results['ranked_results'][key] = []
    
    # Rank the results
    return rank_results(results['ranked_results'], query, keywords) 

def verify_search_connection():
    """
    Verifies the database connection for the search engine.
    Attempts to query a couple of tables to ensure DB access is working.
    
    Returns:
        dict: Dictionary containing status of database connection and diagnostics
    """
    try:
        # Check connection by querying multiple tables (to verify all model access)
        diagnostic_info = {}
        
        # Start with a simple query to check basic database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            connection_ok = cursor.fetchone()[0] == 1
            diagnostic_info["base_connection"] = connection_ok
        
        # Test FAQ model
        faq_count = FAQ.objects.count()
        diagnostic_info["faq_access"] = True
        diagnostic_info["faq_count"] = faq_count
        
        # Test PageContent model
        page_content_count = PageContent.objects.count()
        diagnostic_info["page_content_access"] = True
        diagnostic_info["page_content_count"] = page_content_count
        
        # Test models from external app (home)
        try:
            cyber_challenge_count = CyberChallenge.objects.count()
            diagnostic_info["cyber_challenge_access"] = True
            diagnostic_info["cyber_challenge_count"] = cyber_challenge_count
        except Exception as e:
            diagnostic_info["cyber_challenge_access"] = False
            diagnostic_info["cyber_challenge_error"] = str(e)
        
        try:
            project_count = Project.objects.count()
            diagnostic_info["project_access"] = True
            diagnostic_info["project_count"] = project_count
        except Exception as e:
            diagnostic_info["project_access"] = False
            diagnostic_info["project_error"] = str(e)
        
        logger.info(f"Search connection verified: {diagnostic_info}")
        
        # If we can access local models but not external ones, there's a cross-app issue
        if (diagnostic_info.get("faq_access", False) and 
            diagnostic_info.get("page_content_access", False) and
            not diagnostic_info.get("cyber_challenge_access", False) and
            not diagnostic_info.get("project_access", False)):
            return {
                "status": "partial",
                "message": "Connected to database but cannot access models from other apps. Cross-app issues detected.",
                "diagnostics": diagnostic_info
            }
            
        # All checks passed
        return {
            "status": "success",
            "message": "Search connection verified successfully",
            "diagnostics": diagnostic_info
        }
        
    except OperationalError as e:
        logger.error(f"Database connection error: {e}")
        return {
            "status": "error",
            "message": f"Database connection error: {e}",
            "diagnostics": {"error_type": "OperationalError", "error_message": str(e)}
        }
    except Exception as e:
        logger.error(f"Search connection error: {e}")
        return {
            "status": "error",
            "message": f"Search connection error: {e}",
            "diagnostics": {"error_type": type(e).__name__, "error_message": str(e)}
        } 