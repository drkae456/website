#!/usr/bin/env python
"""
Test script for the verify_search_connection function.
"""
from django.test import TestCase
from django.core.management import execute_from_command_line

class SearchConnectionTestCase(TestCase):
    """Test case for the verify_search_connection function."""
    
    def test_verify_search_connection(self):
        """Test that the verify_search_connection function returns proper status."""
        from chatbot_app.search_engine import verify_search_connection
        
        print("\n=== Testing verify_search_connection function ===\n")
        
        try:
            # Call the function
            result = verify_search_connection()
            
            # Print the result
            print("Connection status:")
            print(f"  Status: {result.get('status', 'unknown')}")
            print(f"  Message: {result.get('message', 'No message provided')}")
            
            # Print diagnostics if available
            if 'diagnostics' in result:
                print("\nDiagnostics:")
                for key, value in result['diagnostics'].items():
                    if key != 'timestamp':  # Skip timestamp for cleaner output
                        print(f"  {key}: {value}")
            
            # Verify the result structure
            self.assertTrue(isinstance(result, dict), "Result should be a dictionary")
            self.assertTrue('status' in result, "Result should include status")
            self.assertTrue('message' in result, "Result should include message")
            self.assertTrue('diagnostics' in result, "Result should include diagnostics")
            
            # If connected, check that we have models
            if result['status'] == 'success':
                self.assertTrue('models_found' in result['diagnostics'], 
                              "Diagnostics should include models_found")
                self.assertTrue(result['diagnostics']['models_found'] > 0,
                              "Should find at least one model")
            
            print("\nTest completed successfully.")
            
        except Exception as e:
            print(f"Error testing verify_search_connection: {str(e)}")
            raise
        
if __name__ == "__main__":
    # Run the test using Django's test framework
    execute_from_command_line(['manage.py', 'test', 'test_search_connection.SearchConnectionTestCase', '-v', '2']) 