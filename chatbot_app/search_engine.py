import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG level to see all logs

from django.db.models import Q, F, Value, FloatField, Case, When, IntegerField
from django.db.models.functions import Length
import re
import string
from functools import reduce
import operator
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
# Import difflib for fuzzy matching
import difflib
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
from django.db import models, connection
from django.db.utils import OperationalError
import time

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
    logger.debug(f"Preprocessing query: '{query}'")
    
    # Handle None or empty query
    if not query:
        logger.debug("Empty query received")
        return ""
        
    # Convert to lowercase
    query = query.lower()
    logger.debug(f"Converted to lowercase: '{query}'")
    
    # Remove punctuation (except hyphens which might be part of terms like "app-attack")
    punctuation_to_remove = string.punctuation.replace('-', '')
    translator = str.maketrans('', '', punctuation_to_remove)
    query = query.translate(translator)
    logger.debug(f"Removed punctuation: '{query}'")
    
    # Remove extra whitespace
    query = ' '.join(query.split())
    logger.debug(f"Final preprocessed query: '{query}'")
    
    return query

def remove_stopwords(query):
    """
    Remove common stopwords from the query
    
    Args:
        query (str): Preprocessed query
        
    Returns:
        str: Query with stopwords removed
    """
    logger.debug(f"Removing stopwords from: '{query}'")
    words = query.split()
    filtered_words = [word for word in words if word.lower() not in STOPWORDS]
    
    # If all words were stopwords, return the original query
    if not filtered_words and words:
        logger.debug("All words were stopwords, returning original query")
        return query
        
    result = ' '.join(filtered_words)
    logger.debug(f"After stopword removal: '{result}'")
    return result

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

def execute_sqlite_query(query):
    """
    Execute a direct SQLite query and return results
    
    Args:
        query (str): The SQL query to execute
        
    Returns:
        list: List of dictionaries containing query results
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
    except Exception as e:
        logger.error(f"Error executing SQLite query: {str(e)}")
        return []

def preprocess_text(text):
    """
    Preprocess text for TF-IDF vectorization
    """
    if not text:
        return ""
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation
    text = re.sub(r'[^\w\s]', ' ', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

def get_document_corpus():
    """
    Get all documents from the database for TF-IDF vectorization
    Returns a list of tuples (id, type, text)
    """
    documents = []
    
    try:
        # Get projects
        projects = Project.objects.all()
        for project in projects:
            text = f"{project.name} {project.description} {project.keywords}"
            if text.strip():  # Only add non-empty documents
                documents.append((project.id, 'project', preprocess_text(text)))
        logger.info(f"Added {len(projects)} projects to corpus")
        
        # Get challenges
        challenges = CyberChallenge.objects.all()
        for challenge in challenges:
            text = f"{challenge.question} {challenge.description} {challenge.category}"
            if text.strip():  # Only add non-empty documents
                documents.append((challenge.id, 'challenge', preprocess_text(text)))
        logger.info(f"Added {len(challenges)} challenges to corpus")
        
        # Get courses
        courses = Course.objects.all()
        for course in courses:
            text = f"{course.title} {course.code}"
            if text.strip():  # Only add non-empty documents
                documents.append((course.id, 'course', preprocess_text(text)))
        logger.info(f"Added {len(courses)} courses to corpus")
        
        # Get skills
        skills = Skill.objects.all()
        for skill in skills:
            text = f"{skill.name} {skill.description}"
            if text.strip():  # Only add non-empty documents
                documents.append((skill.id, 'skill', preprocess_text(text)))
        logger.info(f"Added {len(skills)} skills to corpus")
        
        # Get progress
        progresses = Progress.objects.all()
        for prog in progresses:
            text = (
                f"{prog.student.username if hasattr(prog.student, 'username') else prog.student} "
                f"{prog.skill.name} {prog.progress}% {'completed' if prog.completed else ''}"
            )
            if text.strip():
                documents.append((prog.id, 'progress', preprocess_text(text)))
        logger.info(f"Added {len(progresses)} progress records to corpus")

        # Get contacts
        contacts = Contact.objects.all()
        for contact in contacts:
            text = f"{contact.name} {contact.email} {contact.message}"
            if text.strip():
                documents.append((contact.id, 'contact', preprocess_text(text)))
        logger.info(f"Added {len(contacts)} contacts to corpus")

        # Get contact submissions
        submissions = ContactSubmission.objects.all()
        for sub in submissions:
            text = f"{sub.first_name} {sub.last_name} {sub.email} {sub.message}"
            if text.strip():
                documents.append((sub.id, 'contactsubmission', preprocess_text(text)))
        logger.info(f"Added {len(submissions)} contact submissions to corpus")

        # Get experiences
        experiences = Experience.objects.all()
        for exp in experiences:
            text = exp.feedback if hasattr(exp, 'feedback') else str(exp)
            if text.strip():
                documents.append((exp.id, 'experience', preprocess_text(text)))
        logger.info(f"Added {len(experiences)} experiences to corpus")

        # Get webpages
        pages = Webpage.objects.all()
        for page in pages:
            text = f"{page.title} {page.url}"
            if text.strip():
                documents.append((page.id, 'webpage', preprocess_text(text)))
        logger.info(f"Added {len(pages)} webpages to corpus")

        # Get DDT contacts
        ddt_contacts = DDT_contact.objects.all()
        for ddt in ddt_contacts:
            text = f"{ddt.name} {ddt.email} {ddt.message}"
            if text.strip():
                documents.append((ddt.id, 'ddt_contact', preprocess_text(text)))
        logger.info(f"Added {len(ddt_contacts)} DDT contacts to corpus")

        # Get jobs
        jobs = Job.objects.all()
        for job in jobs:
            text = f"{job.title} {job.location} {job.job_type}"
            if text.strip():
                documents.append((job.id, 'job', preprocess_text(text)))
        logger.info(f"Added {len(jobs)} jobs to corpus")

        # Get job applications
        apps = JobApplication.objects.all()
        for app in apps:
            text = f"{app.name} {getattr(app, 'email', '')} applied for {app.job.title}"
            if text.strip():
                documents.append((app.id, 'jobapplication', preprocess_text(text)))
        logger.info(f"Added {len(apps)} job applications to corpus")

        # Get articles
        articles = Article.objects.all()
        for art in articles:
            text = f"{art.title} {getattr(art.author, 'username', '')}"
            if text.strip():
                documents.append((art.id, 'article', preprocess_text(text)))
        logger.info(f"Added {len(articles)} articles to corpus")

        # Get Smishing detection sign-ups
        smishes = Smishingdetection_join_us.objects.all()
        for sm in smishes:
            text = f"{sm.name} {sm.email} {sm.message}"
            if text.strip():
                documents.append((sm.id, 'smishingdetection_join_us', preprocess_text(text)))
        logger.info(f"Added {len(smishes)} smishing detection sign-ups to corpus")

        # Get project join records
        project_joins = Projects_join_us.objects.all()
        for pj in project_joins:
            text = f"{pj.name} {pj.email} {pj.page_name}"
            if text.strip():
                documents.append((pj.id, 'projects_join_us', preprocess_text(text)))
        logger.info(f"Added {len(project_joins)} project join records to corpus")

        # Get user challenges
        user_chals = UserChallenge.objects.all()
        for uc in user_chals:
            text = (
                f"{uc.user.username if hasattr(uc.user, 'username') else uc.user} "
                f"{uc.challenge.question} {'completed' if uc.completed else 'not completed'}"
            )
            if text.strip():
                documents.append((uc.id, 'userchallenge', preprocess_text(text)))
        logger.info(f"Added {len(user_chals)} user challenges to corpus")

        # Get announcements
        announcements = Announcement.objects.filter(isActive=True)
        for ann in announcements:
            text = ann.message
            if text.strip():
                documents.append((ann.id, 'announcement', preprocess_text(text)))
        logger.info(f"Added {len(announcements)} active announcements to corpus")

        # Get security events
        events = SecurityEvent.objects.all()
        for ev in events:
            text = f"{ev.event_type} {ev.ip_address}"
            if text.strip():
                documents.append((ev.id, 'securityevent', preprocess_text(text)))
        logger.info(f"Added {len(events)} security events to corpus")

        # Get leaderboard entries
        lbs = LeaderBoardTable.objects.all()
        for lb in lbs:
            text = f"{lb.user.username if hasattr(lb.user,'username') else lb.user} {lb.category} {lb.total_points}"
            if text.strip():
                documents.append((lb.id, 'leaderboard', preprocess_text(text)))
        logger.info(f"Added {len(lbs)} leaderboard records to corpus")
        
        logger.info(f"Total documents in corpus: {len(documents)}")
        return documents
    except Exception as e:
        logger.error(f"Error building document corpus: {str(e)}")
        return []

def build_tfidf_index():
    """
    Build TF-IDF index for all documents
    Returns vectorizer and document vectors
    """
    logger.info("Building TF-IDF index")
    documents = get_document_corpus()
    
    if not documents:
        logger.warning("No documents found for TF-IDF indexing")
        return None, None, None
    
    # Extract texts for vectorization
    texts = [doc[2] for doc in documents]
    
    # Create TF-IDF vectorizer with more lenient parameters
    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 2),  # Use both single words and word pairs
        min_df=1,  # Allow terms that appear in at least 1 document
        max_df=1.0,  # Allow terms that appear in all documents
        norm='l2'  # Normalize vectors
    )
    
    try:
        # Fit and transform documents
        logger.info("Fitting TF-IDF vectorizer")
        tfidf_matrix = vectorizer.fit_transform(texts)
        logger.info(f"TF-IDF matrix shape: {tfidf_matrix.shape}")
        
        # Verify the matrix is not empty
        if tfidf_matrix.shape[0] == 0 or tfidf_matrix.shape[1] == 0:
            logger.warning("Empty TF-IDF matrix generated")
            return None, None, None
            
        # Log some statistics
        logger.info(f"Vocabulary size: {len(vectorizer.get_feature_names_out())}")
        logger.info("TF-IDF index built successfully")
        
        return vectorizer, tfidf_matrix, documents
    except Exception as e:
        logger.error(f"Error building TF-IDF index: {str(e)}")
        return None, None, None

def search_with_tfidf(query, vectorizer, tfidf_matrix, documents, top_n=3):
    """
    Search using TF-IDF and cosine similarity
    """
    if vectorizer is None or tfidf_matrix is None or documents is None:
        logger.warning("TF-IDF index not available, falling back to basic search")
        return []
    
    try:
        # Preprocess query
        processed_query = preprocess_text(query)
        logger.info(f"Processed query: {processed_query}")
        
        # Transform query into TF-IDF vector
        query_vector = vectorizer.transform([processed_query])
        logger.info(f"Query vector shape: {query_vector.shape}")
        
        # Calculate cosine similarity
        similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
        logger.info(f"Similarities shape: {similarities.shape}")
        logger.info(f"Max similarity: {similarities.max()}, Min similarity: {similarities.min()}")
        
        # Get top N results
        top_indices = similarities.argsort()[-top_n:][::-1]
        logger.info(f"Top indices: {top_indices}")
        
        results = []
        for idx in top_indices:
            doc_id, doc_type, _ = documents[idx]
            score = float(similarities[idx])  # Convert numpy float to Python float
            
            # Only include results with significant similarity
            if score < 0.1:  # Threshold for minimum similarity
                continue
                
            # Get the actual document based on type
            try:
                if doc_type == 'project':
                    doc = Project.objects.get(id=doc_id)
                    results.append({
                        'type': 'project',
                        'id': doc.id,
                        'title': doc.name,
                        'description': doc.description,
                        'url': f"/projects/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'challenge':
                    doc = CyberChallenge.objects.get(id=doc_id)
                    results.append({
                        'type': 'challenge',
                        'id': doc.id,
                        'title': doc.question,
                        'description': doc.description,
                        'url': f"/challenges/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'course':
                    doc = Course.objects.get(id=doc_id)
                    results.append({
                        'type': 'course',
                        'id': doc.id,
                        'title': doc.title,
                        'description': doc.code,
                        'url': f"/courses/{doc.id}/",
                        'score': score
                    })
                # Additional document types
                elif doc_type == 'faq':
                    doc = FAQ.objects.get(id=doc_id)
                    results.append({
                        'type': 'faq',
                        'id': doc.id,
                        'title': doc.question,
                        'description': doc.answer,
                        'url': f"/faqs/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'page_content':
                    doc = PageContent.objects.get(id=doc_id)
                    results.append({
                        'type': 'page_content',
                        'id': doc.id,
                        'title': doc.title,
                        'description': doc.content,
                        'url': doc.page_path,
                        'score': score
                    })
                elif doc_type == 'companyinformation':
                    doc = CompanyInformation.objects.get(id=doc_id)
                    results.append({
                        'type': 'companyinformation',
                        'id': doc.id,
                        'title': doc.title,
                        'description': doc.content,
                        'url': f"/companyinformation/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'productservice':
                    doc = ProductService.objects.get(id=doc_id)
                    results.append({
                        'type': 'productservice',
                        'id': doc.id,
                        'title': doc.name,
                        'description': doc.description,
                        'url': f"/productservices/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'webpage':
                    doc = Webpage.objects.get(id=doc_id)
                    results.append({
                        'type': 'webpage',
                        'id': doc.id,
                        'title': doc.title,
                        'description': doc.url,
                        'url': doc.url,
                        'score': score
                    })
                elif doc_type == 'skill':
                    doc = Skill.objects.get(id=doc_id)
                    results.append({
                        'type': 'skill',
                        'id': doc.id,
                        'title': doc.name,
                        'description': doc.description,
                        'url': f"/skills/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'progress':
                    doc = Progress.objects.get(id=doc_id)
                    results.append({
                        'type': 'progress',
                        'id': doc.id,
                        'title': f"Progress for {doc.student.username if hasattr(doc.student, 'username') else doc.student}",
                        'description': f"{doc.progress}% {'complete' if doc.completed else 'incomplete'} on {doc.skill.name}",
                        'url': f"/progress/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'contact':
                    doc = Contact.objects.get(id=doc_id)
                    results.append({
                        'type': 'contact',
                        'id': doc.id,
                        'title': doc.name,
                        'description': doc.message,
                        'url': f"/contacts/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'contactsubmission':
                    doc = ContactSubmission.objects.get(id=doc_id)
                    results.append({
                        'type': 'contactsubmission',
                        'id': doc.id,
                        'title': f"{doc.first_name} {doc.last_name}",
                        'description': doc.message,
                        'url': f"/contactsubmissions/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'experience':
                    doc = Experience.objects.get(id=doc_id)
                    results.append({
                        'type': 'experience',
                        'id': doc.id,
                        'title': doc.name,
                        'description': doc.feedback,
                        'url': f"/experiences/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'ddt_contact':
                    doc = DDT_contact.objects.get(id=doc_id)
                    results.append({
                        'type': 'ddt_contact',
                        'id': doc.id,
                        'title': doc.fullname,
                        'description': doc.message,
                        'url': f"/ddt_contacts/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'job':
                    doc = Job.objects.get(id=doc_id)
                    results.append({
                        'type': 'job',
                        'id': doc.id,
                        'title': doc.title,
                        'description': f"{doc.job_type} in {doc.location}",
                        'url': f"/jobs/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'jobapplication':
                    doc = JobApplication.objects.get(id=doc_id)
                    results.append({
                        'type': 'jobapplication',
                        'id': doc.id,
                        'title': doc.name,
                        'description': doc.cover_letter,
                        'url': f"/jobapplications/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'article':
                    doc = Article.objects.get(id=doc_id)
                    results.append({
                        'type': 'article',
                        'id': doc.id,
                        'title': doc.title,
                        'description': doc.content,
                        'url': f"/articles/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'smishingdetection_join_us':
                    doc = Smishingdetection_join_us.objects.get(id=doc_id)
                    results.append({
                        'type': 'smishingdetection_join_us',
                        'id': doc.id,
                        'title': doc.name,
                        'description': doc.message,
                        'url': f"/join/smishing/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'projects_join_us':
                    doc = Projects_join_us.objects.get(id=doc_id)
                    results.append({
                        'type': 'projects_join_us',
                        'id': doc.id,
                        'title': doc.name,
                        'description': doc.message,
                        'url': f"/join/projects/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'userchallenge':
                    doc = UserChallenge.objects.get(id=doc_id)
                    results.append({
                        'type': 'userchallenge',
                        'id': doc.id,
                        'title': doc.challenge.question,
                        'description': f"Score: {doc.score}",
                        'url': f"/userchallenges/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'announcement':
                    doc = Announcement.objects.get(id=doc_id)
                    results.append({
                        'type': 'announcement',
                        'id': doc.id,
                        'title': 'Announcement',
                        'description': doc.message,
                        'url': f"/announcements/{doc.id}/",
                        'score': score
                    })
                elif doc_type == 'securityevent':
                    doc = SecurityEvent.objects.get(id=doc_id)
                    results.append({
                        'type': 'securityevent',
                        'id': doc.id,
                        'title': doc.event_type,
                        'description': doc.details,
                        'url': f"/securityevents/{doc.id}/",
                        'score': score
                    })  
                elif doc_type == 'leaderboard':
                    doc = LeaderBoardTable.objects.get(id=doc_id)
                    results.append({
                        'type': 'leaderboard',
                        'id': doc.id,
                        'title': f"{doc.user.first_name} {doc.user.last_name} ({doc.category})",
                        'description': f"Total points: {doc.total_points}",
                        'url': f"/leaderboards/{doc.id}/",
                        'score': score
                    })
            except Exception as e:
                logger.warning(f"Error retrieving document {doc_id} of type {doc_type}: {str(e)}")
                continue
        
        logger.info(f"Found {len(results)} relevant results")
        return results
        
    except Exception as e:
        logger.error(f"Error in TF-IDF search: {str(e)}")
        return []

def search_model(model, query, name_field='title', desc_field='description', keywords_field=None):
    """
    Search a specific model for matches with the query
    
    Args:
        model: Django model to search
        query (str): The search query
        name_field (str): Field to search for title/name matches
        desc_field (str): Field to search for description matches
        keywords_field (str, optional): Field containing keywords to match
        
    Returns:
        list: List of search results
    """
    try:
        # Build the search query
        search_query = Q()
        
        # Add name field search
        if name_field:
            search_query |= Q(**{f"{name_field}__icontains": query})
            
        # Add description field search
        if desc_field:
            search_query |= Q(**{f"{desc_field}__icontains": query})
            
        # Add keywords field search if provided
        if keywords_field:
            search_query |= Q(**{f"{keywords_field}__icontains": query})
            
        # Execute the search
        results = model.objects.filter(search_query)
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_result = {
                'id': result.id,
                'title': getattr(result, name_field, ''),
                'description': getattr(result, desc_field, ''),
                'score': calculate_relevance(
                    f"{getattr(result, name_field, '')} {getattr(result, desc_field, '')}",
                    [query]
                ),
                'type': model.__name__.lower(),
                'url': f"/{model.__name__.lower()}s/{result.id}/"
            }
            formatted_results.append(formatted_result)
            
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error searching {model.__name__}: {str(e)}")
        return []

def search_database(query):
    """
    Search for relevant results from the database using multiple methods

    Args:
        query (str): The search query string

    Returns:
        dict: Dictionary of search results with metadata
    """
    start_time = time.time()
    cleaned_query = preprocess_query(query)
    logger.info(f"Searching database for query: '{query}' (cleaned: '{cleaned_query}')")
    
    # Check if this is a show more query
    show_more_match = re.search(r'show\s+more\s+(\w+)', query.lower())
    show_more_category = None
    if show_more_match:
        show_more_category = show_more_match.group(1)
        logger.info(f"Detected 'show more' query for category: {show_more_category}")
    
    # Initialize results dictionary
    results = {
        'total_results': 0,
        'categories': [],
        'results': [],
        'debug_info': {
            'query_info': {
                'original': query,
                'cleaned': cleaned_query,
                'method': 'basic_search',
                'matched_table': None,
                'show_more': show_more_category is not None
            },
            'execution_time': None
        }
    }
    
    try:
        # First check if this is a direct query for a specific model/table
        # Map of query keywords to model names
        model_name_map = {
            'course': 'Course',
            'courses': 'Course',
            'project': 'Project',
            'projects': 'Project',
            'challenge': 'CyberChallenge',
            'challenges': 'CyberChallenge',
            'cyber challenge': 'CyberChallenge',
            'cyber challenges': 'CyberChallenge',
            'leaderboard': 'LeaderBoardTable',
            'leaderboards': 'LeaderBoardTable',
            'leader board': 'LeaderBoardTable',
            'leader boards': 'LeaderBoardTable',
            'job': 'Job',
            'jobs': 'Job',
            'career': 'Job',
            'careers': 'Job',
            'position': 'Job',
            'positions': 'Job',
            'progress': 'Progress',
            'student progress': 'Progress',
            'skill progress': 'Progress',
            'contact': 'Contact',
            'contacts': 'Contact',
            'contact us': 'Contact',
            'message': 'Contact',
            'submission': 'ContactSubmission',
            'contact submission': 'ContactSubmission',
            'submissions': 'ContactSubmission',
            'contact submissions': 'ContactSubmission',
            'experience': 'Experience',
            'experiences': 'Experience',
            'user experience': 'Experience',
            'feedback': 'Experience',
            'webpage': 'Webpage',
            'webpages': 'Webpage',
            'page': 'Webpage',
            'pages': 'Webpage',
            'ddt contact': 'DDT_contact',
            'ddt': 'DDT_contact',
            'deakin detonator': 'DDT_contact',
            'article': 'Article',
            'articles': 'Article',
            'blog': 'Article',
            'blogs': 'Article',
            'smishing': 'Smishingdetection_join_us',
            'smishing detection': 'Smishingdetection_join_us',
            'join smishing': 'Smishingdetection_join_us',
            'join projects': 'Projects_join_us',
            'projects join': 'Projects_join_us',
            'user challenge': 'UserChallenge',
            'user challenges': 'UserChallenge',
            'announcement': 'Announcement',
            'announcements': 'Announcement',
            'security event': 'SecurityEvent',
            'security events': 'SecurityEvent',
            'events': 'SecurityEvent',
            'skill': 'Skill',
            'skills': 'Skill',
            'student skill': 'Skill',
            'learning skill': 'Skill',
            'training skill': 'Skill'
        }
        
        # Try matching on cleaned query - exact match first
        matched_model = model_name_map.get(cleaned_query)
        table_match_type = 'exact'
        
        # If no exact match, try partial matching
        if not matched_model:
            for key, model in model_name_map.items():
                # Check if the cleaned query is part of a model name or vice versa
                if key in cleaned_query or cleaned_query in key:
                    matched_model = model
                    table_match_type = 'partial'
                    logger.info(f"Partial table match: '{cleaned_query}' matches '{key}' for model '{model}'")
                    break
        
        # --- FORCE CHALLENGE CATEGORY FOR CHALLENGE-RELATED QUERIES ---
        # If the query contains 'challenge' or 'challenges', force CyberChallenge model
        if not matched_model and re.search(r'challenge', cleaned_query):
            matched_model = 'CyberChallenge'
            table_match_type = 'forced_challenge_keyword'
            logger.info(f"Forcing CyberChallenge model for query containing 'challenge': '{cleaned_query}'")
        # --- END FORCE ---
        
        # If this is a show more query and we have a category, use that to determine the model
        if show_more_category and not matched_model:
            # Map the category name to model name
            category_to_model = {
                'courses': 'Course',
                'course': 'Course',
                'projects': 'Project', 
                'project': 'Project',
                'challenges': 'CyberChallenge',
                'challenge': 'CyberChallenge',
                'jobs': 'Job',
                'job': 'Job',
                'skills': 'Skill',
                'skill': 'Skill',
                'progress': 'Progress',
                'contacts': 'Contact',
                'contact': 'Contact',
                'experiences': 'Experience',
                'experience': 'Experience',
                'articles': 'Article',
                'article': 'Article',
                'announcements': 'Announcement',
                'announcement': 'Announcement',
                'leaderboards': 'LeaderBoardTable',
                'leaderboard': 'LeaderBoardTable'
            }
            
            matched_model = category_to_model.get(show_more_category.lower())
            if matched_model:
                logger.info(f"Show more query matched category '{show_more_category}' to model '{matched_model}'")
                table_match_type = 'show_more'
                results['debug_info']['query_info']['method'] = 'show_more'
        
        # If we found a direct model match, query that model directly
        if matched_model:
            logger.info(f"Found {table_match_type} table match for query '{cleaned_query}' to model: {matched_model}")
            results['debug_info']['query_info']['method'] = 'direct_table_match' if table_match_type != 'show_more' else 'show_more'
            results['debug_info']['query_info']['matched_table'] = matched_model
            
            # Determine the result limit based on whether this is a show more query
            limit = 6 if table_match_type == 'show_more' else 3  # Show more: 6 results, regular: 3 results
            offset = 3 if table_match_type == 'show_more' else 0  # Show more: skip first 3, regular: start from beginning
            
            if matched_model == 'Course':
                # Check for numeric ID lookup (e.g., 'course 444')
                id_match = re.search(r"\b(\d+)\b", cleaned_query)
                if id_match:
                    try:
                        cid = int(id_match.group(1))
                        rec = Course.objects.get(id=cid)
                        # Return only this course
                        results['results'] = [{
                            'id': rec.id,
                            'title': rec.title,
                            'description': rec.code,
                            'type': 'course',
                            'url': f"/courses/{rec.id}/"
                        }]
                        results['categories'] = ['courses']
                        results['total_results'] = 1
                        results['debug_info']['query_info']['method'] = 'id_lookup'
                        results['debug_info']['execution_time'] = time.time() - start_time
                        return results
                    except Course.DoesNotExist:
                        pass
                if table_match_type == 'show_more':
                    # For "show more" queries, skip the first 3 records
                    recent_records = Course.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = Course.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent Course records (offset={offset}, limit={limit})")
                
                # Format course results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': record.title,
                        'description': f"Course Code: {record.code}",
                        'score': 100,  # High score for direct matches
                        'type': 'course',
                        'url': f"/courses/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('courses')
                
            elif matched_model == 'Project':
                if table_match_type == 'show_more':
                    recent_records = Project.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = Project.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent Project records (offset={offset}, limit={limit})")
                
                # Format project results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': record.name,
                        'description': record.description,
                        'score': 100,  # High score for direct matches
                        'type': 'project',
                        'url': f"/projects/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('projects')
                
            elif matched_model == 'CyberChallenge':
                # Retrieve all challenges so the engine finds all results
                recent_records = CyberChallenge.objects.all().order_by('-id')

                logger.info(f"Retrieved {len(recent_records)} recent CyberChallenge records (offset={offset}, limit={limit})")

                # Format challenge results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': record.question,  # Use the question field for challenge prompt
                        'description': record.description,
                        'difficulty': record.difficulty.title() if hasattr(record, 'difficulty') and record.difficulty else 'Medium',
                        'points': record.points if hasattr(record, 'points') else 0,
                    }
                    results['challenges'] = results.get('challenges', [])
                    results['challenges'].append(result)

                if recent_records:
                    results['categories'].append('challenges')

                # Early return for CyberChallenge direct matches
                results['results'] = results.get('challenges', [])
                results['total_results'] = len(results['results'])
                results['debug_info']['execution_time'] = time.time() - start_time
                logger.info(f"Returning CyberChallenge direct match results: {results['total_results']} items")
                return results
            
            elif matched_model == 'LeaderBoardTable':
                if table_match_type == 'show_more':
                    recent_records = LeaderBoardTable.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = LeaderBoardTable.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent LeaderBoardTable records (offset={offset}, limit={limit})")
                
                # Format leaderboard results
                for record in recent_records:
                    # Create a title using the ID since LeaderBoardTable might not have a title field
                    title = f"Leaderboard {record.id}"
                    
                    # Try to get entries count if possible
                    description = "Leaderboard details"
                    try:
                        entries_count = getattr(record, 'entries_count', None)
                        if entries_count is not None:
                            description = f"Entries: {entries_count}"
                    except AttributeError:
                        pass
                    
                    result = {
                        'id': record.id,
                        'title': title,
                        'description': description,
                        'score': 100,  # High score for direct matches
                        'type': 'leaderboard',
                        'url': f"/leaderboards/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('leaderboards')
                    
            elif matched_model == 'Job':
                # Get open jobs (where closing_date is in the future or None)
                from django.utils import timezone
                today = timezone.now().date()
                
                # Get jobs that are either still open or have no closing date
                job_query = Q(closing_date__gte=today) | Q(closing_date__isnull=True)
                
                if table_match_type == 'show_more':
                    recent_records = Job.objects.filter(job_query).order_by('-posted_date')[offset:offset+limit]
                else:
                    recent_records = Job.objects.filter(job_query).order_by('-posted_date')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} open Job records (offset={offset}, limit={limit})")
                
                # Format job results
                for record in recent_records:
                    job_type = getattr(record, 'job_type', 'Not specified')
                    location = getattr(record, 'location', 'Not specified')
                    
                    result = {
                        'id': record.id,
                        'title': record.title,
                        'description': f"{job_type} in {location}",
                        'score': 100,  # High score for direct matches
                        'type': 'job',
                        'url': f"/jobs/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('jobs')
            
            elif matched_model == 'Progress':
                if table_match_type == 'show_more':
                    recent_records = Progress.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = Progress.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent Progress records (offset={offset}, limit={limit})")
                
                # Format progress results
                for record in recent_records:
                    student_name = getattr(record.student, 'username', str(record.student)) if hasattr(record, 'student') else 'Student'
                    skill_name = getattr(record.skill, 'name', 'Skill') if hasattr(record, 'skill') else 'Skill'
                    
                    result = {
                        'id': record.id,
                        'title': f"Progress for {student_name}",
                        'description': f"{record.progress}% {'completed' if record.completed else 'in progress'} on {skill_name}",
                        'score': 100,  # High score for direct matches
                        'type': 'progress',
                        'url': f"/progress/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('progress')
                    
            elif matched_model == 'Contact':
                if table_match_type == 'show_more':
                    recent_records = Contact.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = Contact.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent Contact records (offset={offset}, limit={limit})")
                
                # Format contact results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': record.name,
                        'description': record.message,
                        'score': 100,  # High score for direct matches
                        'type': 'contact',
                        'url': f"/contacts/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('contacts')
                    
            elif matched_model == 'ContactSubmission':
                if table_match_type == 'show_more':
                    recent_records = ContactSubmission.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = ContactSubmission.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent ContactSubmission records (offset={offset}, limit={limit})")
                
                # Format contact submission results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': f"{record.first_name} {record.last_name}",
                        'description': record.message,
                        'score': 100,  # High score for direct matches
                        'type': 'contactsubmission',
                        'url': f"/contactsubmissions/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('contactsubmissions')
                    
            elif matched_model == 'Experience':
                if table_match_type == 'show_more':
                    recent_records = Experience.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = Experience.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent Experience records (offset={offset}, limit={limit})")
                
                # Format experience results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': record.name if hasattr(record, 'name') else "User Experience",
                        'description': record.feedback if hasattr(record, 'feedback') else str(record),
                        'score': 100,  # High score for direct matches
                        'type': 'experience',
                        'url': f"/experiences/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('experiences')
                    
            elif matched_model == 'Webpage':
                if table_match_type == 'show_more':
                    recent_records = Webpage.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = Webpage.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent Webpage records (offset={offset}, limit={limit})")
                
                # Format webpage results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': record.title,
                        'description': record.url,
                        'score': 100,  # High score for direct matches
                        'type': 'webpage',
                        'url': record.url
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('webpages')
                    
            elif matched_model == 'DDT_contact':
                if table_match_type == 'show_more':
                    recent_records = DDT_contact.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = DDT_contact.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent DDT_contact records (offset={offset}, limit={limit})")
                
                # Format DDT contact results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': record.fullname,
                        'description': record.message,
                        'score': 100,  # High score for direct matches
                        'type': 'ddt_contact',
                        'url': f"/ddt_contacts/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('ddt_contacts')
                    
            elif matched_model == 'Article':
                if table_match_type == 'show_more':
                    recent_records = Article.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = Article.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent Article records (offset={offset}, limit={limit})")
                
                # Format article results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': record.title,
                        'description': record.content[:150] + "..." if len(record.content) > 150 else record.content,
                        'score': 100,  # High score for direct matches
                        'type': 'article',
                        'url': f"/articles/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('articles')
                    
            elif matched_model == 'Smishingdetection_join_us':
                if table_match_type == 'show_more':
                    recent_records = Smishingdetection_join_us.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = Smishingdetection_join_us.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent Smishingdetection_join_us records (offset={offset}, limit={limit})")
                
                # Format smishing join results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': record.name,
                        'description': record.message,
                        'score': 100,  # High score for direct matches
                        'type': 'smishingdetection_join_us',
                        'url': f"/join/smishing/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('smishingdetection_join_us')
                    
            elif matched_model == 'Projects_join_us':
                if table_match_type == 'show_more':
                    recent_records = Projects_join_us.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = Projects_join_us.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent Projects_join_us records (offset={offset}, limit={limit})")
                
                # Format projects join results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': record.name,
                        'description': f"Page: {record.page_name}" + (f" - {record.message}" if record.message else ""),
                        'score': 100,  # High score for direct matches
                        'type': 'projects_join_us',
                        'url': f"/join/projects/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('projects_join_us')
                    
            elif matched_model == 'UserChallenge':
                if table_match_type == 'show_more':
                    recent_records = UserChallenge.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = UserChallenge.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent UserChallenge records (offset={offset}, limit={limit})")
                
                # Format user challenge results
                for record in recent_records:
                    user_name = getattr(record.user, 'username', str(record.user)) if hasattr(record, 'user') else 'User'
                    challenge_title = getattr(record.challenge, 'question', 'Challenge') if hasattr(record, 'challenge') else 'Challenge'
                    
                    result = {
                        'id': record.id,
                        'title': challenge_title,
                        'description': f"User: {user_name}, Score: {getattr(record, 'score', 'N/A')}, {'Completed' if getattr(record, 'completed', False) else 'In Progress'}",
                        'score': 100,  # High score for direct matches
                        'type': 'userchallenge',
                        'url': f"/userchallenges/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('userchallenges')
                    
            elif matched_model == 'Announcement':
                if table_match_type == 'show_more':
                    recent_records = Announcement.objects.filter(isActive=True).order_by('-id')[offset:offset+limit]
                else:
                    recent_records = Announcement.objects.filter(isActive=True).order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent active Announcement records (offset={offset}, limit={limit})")
                
                # Format announcement results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': 'Announcement',
                        'description': record.message,
                        'score': 100,  # High score for direct matches
                        'type': 'announcement',
                        'url': f"/announcements/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('announcements')
                    
            elif matched_model == 'SecurityEvent':
                if table_match_type == 'show_more':
                    recent_records = SecurityEvent.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = SecurityEvent.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent SecurityEvent records (offset={offset}, limit={limit})")
                
                # Format security event results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': record.event_type,
                        'description': getattr(record, 'details', f"IP: {getattr(record, 'ip_address', 'Unknown')}"),
                        'score': 100,  # High score for direct matches
                        'type': 'securityevent',
                        'url': f"/securityevents/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('securityevents')
                    
            elif matched_model == 'Skill':
                if table_match_type == 'show_more':
                    recent_records = Skill.objects.all().order_by('-id')[offset:offset+limit]
                else:
                    recent_records = Skill.objects.all().order_by('-id')[:limit]
                    
                logger.info(f"Retrieved {len(recent_records)} recent Skill records (offset={offset}, limit={limit})")
                
                # Format skill results
                for record in recent_records:
                    result = {
                        'id': record.id,
                        'title': record.name,
                        'description': record.description,
                        'score': 100,  # High score for direct matches
                        'type': 'skill',
                        'url': f"/skills/{record.id}/"
                    }
                    results['results'].append(result)
                    
                if recent_records:
                    results['categories'].append('skills')

            # Add show_more info to results to help format_search_results
            if table_match_type == 'show_more':
                results['show_more'] = True
                results['show_more_category'] = show_more_category
            
            # If we got results from a direct table match or show more, return them
            if results['results']:
                results['total_results'] = len(results['results'])
                logger.info(f"{table_match_type} match found {results['total_results']} results from {matched_model}")
                results['debug_info']['execution_time'] = time.time() - start_time
                return results
        
        # If no direct table match or no results from direct match, try TF-IDF search first
        logger.info("No direct table match, trying TF-IDF search")
        try:
            documents, vectorizer, tfidf_matrix = build_tfidf_index()
            tfidf_results = search_with_tfidf(cleaned_query, vectorizer, tfidf_matrix, documents)
            
            if tfidf_results:
                results['debug_info']['query_info']['method'] = 'tfidf_search'
                # Start with TF-IDF matches
                combined = list(tfidf_results)
                # Also include any direct Skill matches
                skill_results = search_model(Skill, cleaned_query, name_field='name', desc_field='description')
                if skill_results:
                    combined.extend(skill_results)
                # Assign combined results
                results['results'] = combined
                results['total_results'] = len(combined)
                # Extract categories from all results
                categories = set()
                for res in combined:
                    typ = res.get('type')
                    if typ:
                        categories.add(f"{typ}s")
                results['categories'] = list(categories)
                logger.info(f"TF-IDF search found {results['total_results']} results (including skills)")
                results['debug_info']['execution_time'] = time.time() - start_time
                return results
        except Exception as e:
            logger.warning(f"TF-IDF search failed: {str(e)}. Falling back to basic search.")
        
        # Fall back to basic search if TF-IDF fails or finds no results
        logger.info("Attempting basic search")
        results['debug_info']['query_info']['method'] = 'basic_search'
        
        # Search in Project model
        project_results = search_model(Project, cleaned_query, 
                               name_field='name', 
                               desc_field='description',
                               keywords_field='keywords')
        
        # Search in CyberChallenge model
        challenge_results = search_model(CyberChallenge, cleaned_query,
                                 name_field='question',
                                 desc_field='description',
                                 keywords_field='category')
        
        # Search in Course model
        course_results = search_model(Course, cleaned_query,    
                              name_field='title',
                              desc_field='code')
        # Search in Skill model
        skill_results = search_model(Skill, cleaned_query,
                             name_field='name',
                             desc_field='description')
                              
        # Search in LeaderBoardTable model
        leaderboard_results = search_model(LeaderBoardTable, cleaned_query,
                                  name_field='id',  # Using ID as name since it might not have a name field
                                  desc_field=None)  # No description field assumed
                                    
        # Search in Job model
        job_results = []
        try:
            from django.utils import timezone
            today = timezone.now().date()
            
            # Build job query for title, location, and job_type matching
            job_query = (
                Q(title__icontains=cleaned_query) |
                Q(location__icontains=cleaned_query) |
                Q(job_type__icontains=cleaned_query)
            )
            
            # Only show open jobs (closing date in future or null)
            open_jobs_filter = Q(closing_date__gte=today) | Q(closing_date__isnull=True)
            matching_jobs = Job.objects.filter(job_query & open_jobs_filter).distinct()
            
            logger.info(f"Found {matching_jobs.count()} matching jobs")
            
            for job in matching_jobs:
                # Calculate relevance score
                job_text = f"{job.title} {job.location} {job.job_type}"
                relevance_score = calculate_relevance(job_text, extract_general_keywords(cleaned_query))
                
                job_results.append({
                    'id': job.id,
                    'title': job.title,
                    'description': f"{job.job_type} in {job.location}",
                    'score': relevance_score,
                    'type': 'job',
                    'url': f"/jobs/{job.id}/"
                })
        except Exception as e:
            logger.error(f"Error searching jobs: {str(e)}")
        
        # Combine all results
        all_results = []
        if project_results:
            all_results.extend(project_results)
            results['categories'].append('projects')
        
        if challenge_results:
            all_results.extend(challenge_results)
            results['categories'].append('challenges')
        
        if course_results:
            all_results.extend(course_results)
            results['categories'].append('courses')
        if skill_results:
            all_results.extend(skill_results)
            results['categories'].append('skills')
        
        if leaderboard_results:
            all_results.extend(leaderboard_results)
            results['categories'].append('leaderboards')
            
        if job_results:
            all_results.extend(job_results)
            results['categories'].append('jobs')
        
        # Sort results by relevance score
        all_results.sort(key=lambda x: -x.get('score', 0))
        
        results['results'] = all_results
        results['total_results'] = len(all_results)
        
        # Check for spelling errors in the query
        if len(all_results) == 0:
            corrected_query = correct_spelling(cleaned_query)
            if corrected_query != cleaned_query:
                logger.info(f"No results found. Trying spelling correction: {corrected_query}")
                results['corrected_query'] = corrected_query
                corrected_results = search_database(corrected_query)
                
                # Merge results
                if corrected_results['total_results'] > 0:
                    results['results'] = corrected_results['results']
                    results['categories'] = corrected_results['categories']
                    results['total_results'] = corrected_results['total_results']
                    results['debug_info']['query_info']['corrected'] = corrected_query
        
        logger.info(f"Search completed with {results['total_results']} results in {time.time() - start_time:.2f}s")
        results['debug_info']['execution_time'] = time.time() - start_time
        return results
        
    except Exception as e:
        error_msg = f"Error during search: {str(e)}"
        logger.error(error_msg)
        results['error'] = error_msg
        results['debug_info']['execution_time'] = time.time() - start_time
        return results

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
    Calculate relevance score for an item based on query and keywords
    
    Args:
        item: The item to score
        query (str): Original query
        keywords (list): Keywords extracted from query
        item_type (str): Type of item being scored
        
    Returns:
        int: Relevance score
    """
    logger.debug(f"Calculating relevance score for {item_type} item")
    score = 0
    
    try:
        # Different scoring based on item type
        if item_type == 'page_content':
            # Title match is most important
            if hasattr(item, 'title') and any(keyword.lower() in item.title.lower() for keyword in keywords):
                score += 5
            
            # Keyword field match is next most important
            if hasattr(item, 'keywords') and item.keywords:
                item_keywords = item.keywords.lower().split(',')
                for keyword in keywords:
                    if any(keyword.lower() in kw.lower() for kw in item_keywords):
                        score += 3
            
            # Content match is least important but still counts
            if hasattr(item, 'content'):
                for keyword in keywords:
                    if keyword.lower() in item.content.lower():
                        score += 1
            
            # Boost by priority field
            score += getattr(item, 'priority', 0) * 2
            
        elif item_type == 'faqs':
            # Question match is most important
            if hasattr(item, 'question') and any(keyword.lower() in item.question.lower() for keyword in keywords):
                score += 5
            
            # Keyword field match
            if hasattr(item, 'keywords') and item.keywords:
                item_keywords = item.keywords.lower().split(',')
                for keyword in keywords:
                    if any(keyword.lower() in kw.lower() for kw in item_keywords):
                        score += 3
            
            # Category match
            if hasattr(item, 'category') and any(keyword.lower() in item.category.lower() for keyword in keywords):
                score += 2
                    
        elif item_type == 'challenges':
            # Title match is most important
            if hasattr(item, 'title') and any(keyword.lower() in item.title.lower() for keyword in keywords):
                score += 5
            
            # Category match
            if hasattr(item, 'category') and any(keyword.lower() in item.category.lower() for keyword in keywords):
                score += 3
            
            # Description match
            if hasattr(item, 'description'):
                for keyword in keywords:
                    if keyword.lower() in item.description.lower():
                        score += 1
                    
        elif item_type == 'projects':
            # Name/title match is most important
            if hasattr(item, 'title') and any(keyword.lower() in item.title.lower() for keyword in keywords):
                score += 5
            # Use get_title_display if available to check the display value
            if hasattr(item, 'get_title_display'):
                display_title = item.get_title_display()
                if any(keyword.lower() in display_title.lower() for keyword in keywords):
                    score += 5
                
            # Description match
            if hasattr(item, 'description'):
                for keyword in keywords:
                    if keyword.lower() in item.description.lower():
                        score += 2
                    
        elif item_type == 'courses':
            # Title match is most important
            if hasattr(item, 'title') and any(keyword.lower() in item.title.lower() for keyword in keywords):
                score += 5
                
            # Code match is also important
            if hasattr(item, 'code') and any(keyword.lower() in item.code.lower() for keyword in keywords):
                score += 4
                
        elif item_type == 'skills':
            # Name match is most important
            if hasattr(item, 'name') and any(keyword.lower() in item.name.lower() for keyword in keywords):
                score += 5
                
            # Description match
            if hasattr(item, 'description'):
                for keyword in keywords:
                    if keyword.lower() in item.description.lower():
                        score += 2
                        
            # Slug match
            if hasattr(item, 'slug') and any(keyword.lower() in item.slug.lower() for keyword in keywords):
                score += 3
                
        elif item_type == 'jobs':
            # Title match is most important
            if hasattr(item, 'title') and any(keyword.lower() in item.title.lower() for keyword in keywords):
                score += 5
                
            # Description match
            if hasattr(item, 'description'):
                for keyword in keywords:
                    if keyword.lower() in item.description.lower():
                        score += 2
                        
            # Location and job_type match
            if hasattr(item, 'location') and any(keyword.lower() in item.location.lower() for keyword in keywords):
                score += 3
                
            if hasattr(item, 'job_type') and any(keyword.lower() in item.job_type.lower() for keyword in keywords):
                score += 3
                
        elif item_type == 'articles':
            # Title match is most important
            if hasattr(item, 'title') and any(keyword.lower() in item.title.lower() for keyword in keywords):
                score += 5
                
            # Content match
            if hasattr(item, 'content'):
                for keyword in keywords:
                    if keyword.lower() in item.content.lower():
                        score += 2
                        
        elif item_type == 'announcements':
            # Message match
            if hasattr(item, 'message'):
                for keyword in keywords:
                    if keyword.lower() in item.message.lower():
                        score += 3
                    
        elif item_type == 'experiences':
            # Name match
            if hasattr(item, 'name') and any(keyword.lower() in item.name.lower() for keyword in keywords):
                score += 3
                
            # Feedback match
            if hasattr(item, 'feedback'):
                for keyword in keywords:
                    if keyword.lower() in item.feedback.lower():
                        score += 2
                        
        elif item_type == 'contact_info':
            # Name match
            if hasattr(item, 'name') and any(keyword.lower() in item.name.lower() for keyword in keywords):
                score += 3
            elif hasattr(item, 'fullname') and any(keyword.lower() in item.fullname.lower() for keyword in keywords):
                score += 3
                
            # Email match
            if hasattr(item, 'email') and any(keyword.lower() in item.email.lower() for keyword in keywords):
                score += 2
                
            # Message match
            if hasattr(item, 'message'):
                for keyword in keywords:
                    if keyword.lower() in item.message.lower():
                        score += 1
                        
        elif item_type == 'join_requests':
            # Name match
            if hasattr(item, 'name') and any(keyword.lower() in item.name.lower() for keyword in keywords):
                score += 3
                
            # Email match
            if hasattr(item, 'email') and any(keyword.lower() in item.email.lower() for keyword in keywords):
                score += 2
                
            # Message match
            if hasattr(item, 'message'):
                for keyword in keywords:
                    if keyword.lower() in item.message.lower():
                        score += 1
                        
            # Page name match (for Projects_join_us)
            if hasattr(item, 'page_name') and any(keyword.lower() in item.page_name.lower() for keyword in keywords):
                score += 3
    except Exception as e:
        logger.error(f"Error calculating relevance score for {item_type}: {str(e)}")
        # Return a minimal score so it still appears in results
        score = 0.1
    
    logger.debug(f"Final relevance score for {item_type}: {score}")
    return score

def spell_correct(query):
    """
    Attempt to correct spelling errors in the query
    
    Args:
        query (str): The user's query
        
    Returns:
        str: Corrected query
        bool: Whether correction was made
    """
    logger.info(f"Starting spell correction for query: '{query}'")
    # Create a vocabulary from project keywords
    vocabulary = []
    
    # Add project names
    try:
        projects = Project.objects.all()
        logger.debug(f"Building vocabulary from {len(projects)} projects")
        for project in projects:
            if project.name:
                vocabulary.append(project.name.lower())
            if project.keywords:
                keywords = [k.strip().lower() for k in project.keywords.split(',')]
                vocabulary.extend(keywords)
                logger.debug(f"Added project '{project.name}' with keywords: {keywords}")
    except Exception as e:
        logger.warning(f"Error getting project vocabulary: {str(e)}")
    
    # Add challenge questions and categories
    try:
        challenges = CyberChallenge.objects.all()
        logger.debug(f"Adding {len(challenges)} challenges to vocabulary")
        for challenge in challenges:
            if challenge.question:
                vocabulary.append(challenge.question.lower())
            if challenge.category:
                vocabulary.append(challenge.category.lower())
    except Exception as e:
        logger.warning(f"Error getting challenge vocabulary: {str(e)}")
    
    # Add course titles and codes
    try:
        courses = Course.objects.all()
        logger.debug(f"Adding {len(courses)} courses to vocabulary")
        for course in courses:
            if course.title:
                vocabulary.append(course.title.lower())
            if course.code:
                vocabulary.append(course.code.lower())
    except Exception as e:
        logger.warning(f"Error getting course vocabulary: {str(e)}")
    
    # Add common domain-specific terms
    domain_terms = [
        'security', 'cyber', 'cyberattack', 'cybersecurity', 'attack', 'defense',
        'vulnerability', 'exploit', 'malware', 'virus', 'trojan', 'ransomware',
        'phishing', 'smishing', 'authentication', 'authorization', 'encryption',
        'decryption', 'penetration', 'testing', 'pentest', 'hacking', 'ethical',
        'firewall', 'intrusion', 'detection', 'prevention', 'deakin', 'university',
        'course', 'project', 'challenge', 'ctf', 'capture', 'flag'
    ]
    vocabulary.extend(domain_terms)
    logger.debug(f"Added {len(domain_terms)} domain-specific terms to vocabulary")
    
    # Create a unique vocabulary
    vocabulary = list(set(vocabulary))
    logger.info(f"Total vocabulary size: {len(vocabulary)}")
    if len(vocabulary) > 0:
        logger.debug(f"Sample vocabulary items: {vocabulary[:10]}...")
    
    # Split the query into words and try to correct each word
    words = query.split()
    corrected_words = []
    was_corrected = False
    
    logger.info(f"Processing {len(words)} words from query")
    for i, word in enumerate(words):
        logger.debug(f"Word {i+1}: '{word}'")
        # Only try to correct words longer than 3 characters
        if len(word) <= 3:
            logger.debug(f"  Skipping '{word}' (too short)")
            corrected_words.append(word)
            continue
            
        # Skip stopwords
        if word.lower() in STOPWORDS:
            logger.debug(f"  Skipping '{word}' (stopword)")
            corrected_words.append(word)
            continue
            
        # Find closest matches in vocabulary
        cutoff = 0.7  # Match threshold
        matches = difflib.get_close_matches(word.lower(), vocabulary, n=3, cutoff=cutoff)
        
        if matches:
            # Found a close match
            best_match = matches[0]
            match_score = difflib.SequenceMatcher(None, word.lower(), best_match).ratio()
            logger.debug(f"  Found matches for '{word}': {matches}")
            logger.debug(f"  Best match: '{best_match}' with score {match_score:.2f}")
            
            if best_match != word.lower():
                was_corrected = True
                logger.info(f"  Corrected '{word}' to '{best_match}' (score: {match_score:.2f})")
                corrected_words.append(best_match)
            else:
                logger.debug(f"  No correction needed for '{word}' (exact match in vocabulary)")
                corrected_words.append(word)
        else:
            logger.debug(f"  No matches found for '{word}' above threshold {cutoff}")
            corrected_words.append(word)
    
    corrected_query = ' '.join(corrected_words)
    logger.info(f"Spell correction complete - Original: '{query}', Corrected: '{corrected_query}', Was corrected: {was_corrected}")
    
    return corrected_query, was_corrected

def process_query(query):
    """
    Process a search query and return formatted results
    
    Args:
        query (str): The search query
        
    Returns:
        dict: Formatted search results
    """
    logger.info(f"\n{'='*50}\nProcessing query: '{query}'")
    try:
        # Check if this is a "show more" query
        show_more_match = re.search(r'show\s+more\s+(\w+)', query.lower())
        if show_more_match:
            category_name = show_more_match.group(1)
            logger.info(f"Detected 'show more' query for category: {category_name}")
            
            # Map the category name to model name
            category_to_model = {
                'courses': 'Course',
                'course': 'Course',
                'projects': 'Project', 
                'project': 'Project',
                'challenges': 'CyberChallenge',
                'challenge': 'CyberChallenge',
                'jobs': 'Job',
                'job': 'Job',
                'skills': 'Skill',
                'skill': 'Skill',
                'progress': 'Progress',
                'contacts': 'Contact',
                'contact': 'Contact',
                'experiences': 'Experience',
                'experience': 'Experience',
                'articles': 'Article',
                'article': 'Article',
                'announcements': 'Announcement',
                'announcement': 'Announcement',
                'leaderboards': 'LeaderBoardTable',
                'leaderboard': 'LeaderBoardTable'
            }
            
            model_name = category_to_model.get(category_name.lower())
            
            if model_name:
                logger.info(f"Matched category '{category_name}' to model '{model_name}'")
                # Create a result with special flag for show more
                return {
                    'query': query,
                    'show_more': True,
                    'model_name': model_name,
                    'category_name': category_name
                }
        
        # If not a show more query, continue with regular processing
        # Try to correct spelling in the query
        corrected_query, was_corrected = spell_correct(query)
        
        # Preprocess the query
        processed_query = preprocess_query(corrected_query)
        logger.info(f"Preprocessed query: '{processed_query}'")
        
        if not processed_query:
            logger.warning("Empty processed query")
            return {
                'query': query,
                'corrected_query': corrected_query if was_corrected else None,
                'results': [],
                'total_results': 0,
                'categories': []
            }
            
        # Extract keywords
        general_keywords = extract_general_keywords(processed_query)
        project_keywords = extract_project_keywords(processed_query)
        logger.info(f"Extracted keywords - General: {general_keywords}, Project: {project_keywords}")
        
        # If no valid keywords found, return empty results
        if not general_keywords and not project_keywords:
            logger.warning("No valid keywords found after extraction")
            return {
                'query': query,
                'corrected_query': corrected_query if was_corrected else None,
                'results': [],
                'total_results': 0,
                'categories': []
            }
            
        # Search the database
        logger.info("Starting database search")
        results = search_database(processed_query)
        
        # Add corrected query information
        if was_corrected:
            results['corrected_query'] = corrected_query
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {
            'query': query,
            'results': [],
            'total_results': 0,
            'categories': []
        }

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
        if isinstance(items, list) and items and 'score' in items[0]:
            items = sorted(items, key=lambda x: -x['score'])
        
        # Limit to top 5 results for each category
        items = items[:5]
        
        if model_type == 'page_content':
            response_text = "Here are the most relevant pages I found:<br><br>"
            for item in items:
                response_text += f"<strong>{item.get('title', 'Untitled')}</strong><br>"
                # Truncate content if too long
                content = item.get('description', '')
                if len(content) > 300:
                    content = content[:300] + "..."
                response_text += f"{content}<br>"
                if item.get('url'):
                    response_text += f'<a href="{item["url"]}" class="learn-more-link">Learn more</a><br><br>'
                
        elif model_type == 'faq':
            response_text = "Here are some relevant FAQs:<br><br>"
            for item in items:
                response_text += f"<strong>Q: {item.get('title', 'No question provided')}</strong><br>"
                response_text += f"A: {item.get('description', 'No answer provided')}<br>"
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
                    if key not in ['title', 'name', 'question', 'score', 'category'] and value:
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
        logger.error(f"Error formatting model response: {str(e)}")
        return f"Error formatting {model_type} results." 

def format_search_results(search_results, query):
    """Format search results into a readable response for the chatbot/web UI"""
    response = ""
    if not search_results:
        return "I couldn't find any relevant information matching your query. Could you try rephrasing it or ask about something else?"

    # Check for spell correction notice
    corrected_query = search_results.get('corrected_query')
    if corrected_query and corrected_query != query:
        response += f"Showing results for <em>{corrected_query}</em> instead of '{query}'.<br><br>"

    # Build category grouping from raw results list
    raw_results = search_results.get('results', [])
    items_by_category = {}
    for item in raw_results:
        typ = item.get('type')
        if not typ:
            continue
        cat_key = typ if typ.endswith('s') else typ + 's'
        items_by_category.setdefault(cat_key, []).append(item)

    # --- CYBER CHALLENGES SPECIAL FORMATTING ---
    # Use either explicit 'challenges' key or grouped items
    challenges = search_results.get('challenges') or items_by_category.get('challenges', [])
    if challenges:
        # Limit to first 3
        top_challenges = challenges[:3]
        response += f"Hardhat Assistant:<br>👋 Hi {{USER}} Here are the top {len(top_challenges)} Cyber Challenges ready for you to tackle:<br><br>"
        for ch in top_challenges:
            response += "⸻<br><br>"
            difficulty = ch.get('difficulty', 'Medium')
            points = ch.get('points', 0)
            color = {'Easy':'🟩','Medium':'🟨','Hard':'🟥'}.get(difficulty, '🟨')
            response += f"📘 {ch.get('title', '')}<br>"
            response += f"{ch.get('description','')}<br>"
            response += f"{color} Difficulty: {difficulty}<br>"
            response += f"🔥 {points}<br>"
            response += f"🔗 <a href='/challenges/detail/{ch.get('id')}' class='learn-more-link'>Take Challenge</a><br>"
        response += "⸻<br><br>"
        response += "💬 Would you like to see more cyber challenges?<br>"
        response += "<button class='suggestion-btn' onclick=\"sendMessage('Show me more cyber challenges')\">👉 Show me more cyber challenges</button><br><br>"
        return response.strip()
    # --- END CYBER CHALLENGES SPECIAL FORMATTING ---

    # Default formatting for other categories
    for category, items in items_by_category.items():
        if category == 'challenges':
            continue
        # Show only up to 3 items
        slice_items = items[:3]
        response += f"👋 Hi! Here are some {category.title()} related to your query:<br><br>"
        response += "⸻<br><br>"
        for it in slice_items:
            title = it.get('title','')
            desc = it.get('description','')
            response += f"📌 {title}<br>"
            response += f"{desc}<br>"
            cid = it.get('id')
            if cid is not None:
                response += f"🔗 <a href='/{category}/detail/{cid}' class='learn-more-link'>Learn More</a><br><br>"
            response += "⸻<br><br>"
        response += f"💬 Want to see more {category}?<br>"
        response += f"<button class='suggestion-btn' onclick=\"sendMessage('Show me more {category}')\">👉 Show me more {category}</button><br><br>"

    return response.strip()

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

def search(query, user_email=None):
    """
    Main search function that takes a user query and returns formatted results
    
    Args:
        query (str): The user's search query
        user_email (str, optional): The email of the current user, for personalized results
        
    Returns:
        str: A formatted response based on the query results
    """
    logger.info(f"\n{'='*50}\nStarting search for query: '{query}'")
    try:
        # Process the query through our search pipeline
        logger.info("Processing query through search pipeline")
        search_results = process_query(query)
        
        # If user email is provided and query might be about jobs/applications
        if user_email and ('job' in query.lower() or 'apply' in query.lower() or 'application' in query.lower()):
            logger.info(f"User email provided, checking for job applications: {user_email}")
            
            # Search for user's job applications
            job_applications = search_job_applications(query, user_email)
            
            if job_applications:
                logger.info(f"Found {len(job_applications)} job applications for user {user_email}")
                
                # Add job applications to results
                if 'results' not in search_results:
                    search_results['results'] = []
                
                search_results['results'].extend(job_applications)
                
                if 'categories' not in search_results:
                    search_results['categories'] = []
                
                if 'jobapplications' not in search_results['categories']:
                    search_results['categories'].append('jobapplications')
                    
                search_results['total_results'] = len(search_results['results'])
        
        # Format the results into a conversational response
        logger.info("Formatting search results")
        response = format_search_results(search_results, query)
        
        logger.info("Search completed successfully")
        return response
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return f"I'm sorry, but I encountered an error while searching for '{query}'. Please try again with a different query."

def search_job_applications(query, user_email=None):
    """
    Search for job applications, but only return results if they belong to the current user.
    
    Args:
        query (str): The search query
        user_email (str): The email of the current user
        
    Returns:
        list: List of job application results that belong to the user
    """
    logger.info(f"Searching job applications with query: '{query}', user_email: '{user_email}'")
    
    # If no user email is provided, we can't verify ownership, so return no results
    if not user_email:
        logger.info("No user email provided, skipping job application search")
        return []
        
    try:
        # Build query to find matching job applications
        application_query = (
            Q(job__title__icontains=query) |
            Q(job__job_type__icontains=query) |
            Q(job__location__icontains=query)
        )
        
        # Only return applications for the current user's email
        user_filter = Q(email=user_email)
        
        # Find the matching applications
        applications = JobApplication.objects.filter(
            application_query & user_filter
        ).select_related('job').order_by('-applied_date')
        
        logger.info(f"Found {applications.count()} job applications for user '{user_email}'")
        
        # Format the results
        results = []
        for app in applications:
            results.append({
                'id': app.id,
                'title': f"Your application for: {app.job.title}",
                'description': f"Applied on: {app.applied_date.strftime('%Y-%m-%d')}",
                'score': 90,  # High score for personal results
                'type': 'jobapplication',
                'url': f"/jobs/{app.job.id}/"
            })
            
        return results
        
    except Exception as e:
        logger.error(f"Error searching job applications: {str(e)}")
        return [] 

def correct_spelling(query):
    """
    Attempt to correct spelling errors in the query using fuzzy matching
    
    Args:
        query (str): The search query to correct
        
    Returns:
        str: The corrected query
    """
    try:
        # Get all possible terms from the database
        vocabulary = []
        
        # Add project names and keywords
        projects = Project.objects.all()
        for project in projects:
            if project.name:
                vocabulary.append(project.name.lower())
            if project.keywords:
                keywords = [k.strip().lower() for k in project.keywords.split(',')]
                vocabulary.extend(keywords)
                
        # Add challenge questions and categories
        challenges = CyberChallenge.objects.all()
        for challenge in challenges:
            if challenge.question:
                vocabulary.append(challenge.question.lower())
            if challenge.category:
                vocabulary.append(challenge.category.lower())
                
        # Add course titles and codes
        courses = Course.objects.all()
        for course in courses:
            if course.title:
                vocabulary.append(course.title.lower())
            if course.code:
                vocabulary.append(course.code.lower())
                
        # Add common domain-specific terms
        domain_terms = [
            'security', 'cyber', 'cyberattack', 'cybersecurity', 'attack', 'defense',
            'vulnerability', 'exploit', 'malware', 'virus', 'trojan', 'ransomware',
            'phishing', 'smishing', 'authentication', 'authorization', 'encryption',
            'decryption', 'penetration', 'testing', 'pentest', 'hacking', 'ethical',
            'firewall', 'intrusion', 'detection', 'prevention', 'deakin', 'university',
            'course', 'project', 'challenge', 'ctf', 'capture', 'flag'
        ]
        vocabulary.extend(domain_terms)
        
        # Create a unique vocabulary
        vocabulary = list(set(vocabulary))
        
        # Split the query into words and try to correct each word
        words = query.split()
        corrected_words = []
        
        for word in words:
            # Only try to correct words longer than 3 characters
            if len(word) <= 3:
                corrected_words.append(word)
                continue
                
            # Skip stopwords
            if word.lower() in STOPWORDS:
                corrected_words.append(word)
                continue
                
            # Find closest matches in vocabulary
            cutoff = 0.7  # Match threshold
            matches = difflib.get_close_matches(word.lower(), vocabulary, n=3, cutoff=cutoff)
            
            if matches:
                # Found a close match
                best_match = matches[0]
                if best_match != word.lower():
                    corrected_words.append(best_match)
                else:
                    corrected_words.append(word)
            else:
                corrected_words.append(word)
                
        corrected_query = ' '.join(corrected_words)
        return corrected_query
        
    except Exception as e:
        logger.error(f"Error in spell correction: {str(e)}")
        return query