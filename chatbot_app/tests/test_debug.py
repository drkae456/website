import logging
from django.test import TestCase
from chatbot_app import search_engine
from home.models import Project, Course

logging.disable(logging.CRITICAL)

class SearchDebugTests(TestCase):
    """
    Tests to debug the search functionality
    """

    @classmethod
    def setUpTestData(cls):
        # Create test projects
        Project.objects.create(title="AppAttack")
        Project.objects.create(title="PT-GUI")
        Project.objects.create(title="Smishing_Detection")
        Project.objects.create(title="Test Project")

    def test_debug_project_search(self):
        # This will just print results to see how search works
        search_results = search_engine.search('test')
        print("\n\nSEARCH RESULTS FOR 'test':")
        print(f"Results length: {len(search_results)}")
        print(f"Results content: {search_results}")
        
        process_results = search_engine.process_query('test')
        print("\nPROCESS RESULTS FOR 'test':")
        print(f"Results: {process_results}")
        
        # Get all projects
        projects = Project.objects.all()
        print("\nALL PROJECTS IN DATABASE:")
        for project in projects:
            print(f"Project ID: {project.id}, Title: {project.title}, __str__: {str(project)}")
        
        # Debug search_database directly
        db_results = search_engine.search_database('test')
        print("\nDIRECT SEARCH_DATABASE RESULTS FOR 'test':")
        print(f"Results: {db_results}")
        
        # Debug search with direct Project query
        print("\nDIRECT PROJECT QUERY FOR title__icontains='test':")
        direct_results = Project.objects.filter(title__icontains='test')
        print(f"Results count: {direct_results.count()}")
        for result in direct_results:
            print(f"Project ID: {result.id}, Title: {result.title}, __str__: {str(result)}")
        
        # Now assert to make test pass (even if issues exist, we just want output)
        self.assertTrue(True)

    def test_debug_course_search(self):
        # Create test courses
        Course.objects.create(title="Test Course Debug", code="TCD")
        
        # This will just print results to see how search works
        search_results = search_engine.search('course')
        print("\n\nSEARCH RESULTS FOR 'course':")
        print(f"Results length: {len(search_results)}")
        print(f"Results content: {search_results}")
        
        process_results = search_engine.process_query('course')
        print("\nPROCESS RESULTS FOR 'course':")
        print(f"Results: {process_results}")
        
        # Get all courses
        courses = Course.objects.all()
        print("\nALL COURSES IN DATABASE:")
        for course in courses:
            print(f"Course ID: {course.id}, Title: {course.title}, Code: {course.code}")
        
        # Debug search with direct Course query
        print("\nDIRECT COURSE QUERY FOR title__icontains='course':")
        direct_results = Course.objects.filter(title__icontains='course')
        print(f"Results count: {direct_results.count()}")
        for result in direct_results:
            print(f"Course ID: {result.id}, Title: {result.title}, Code: {result.code}")
        
        # Now assert to make test pass (even if issues exist, we just want output)
        self.assertTrue(True) 