import unittest
from chatbot_app.textblob_analyzer import (
    analyze_sentiment,
    extract_noun_phrases,
    correct_spelling,
    get_pos_tags,
    tokenize_text,
    analyze_text
)

class TestTextBlobAnalyzer(unittest.TestCase):
    
    def test_sentiment_analysis(self):
        """Test sentiment analysis with positive, negative, and neutral text."""
        positive_text = "I love this product! It's amazing and works perfectly."
        negative_text = "This is terrible. I'm very disappointed with the poor quality."
        neutral_text = "The product arrived yesterday. It is blue and medium-sized."
        
        positive_result = analyze_sentiment(positive_text)
        negative_result = analyze_sentiment(negative_text)
        neutral_result = analyze_sentiment(neutral_text)
        
        self.assertGreater(positive_result['polarity'], 0.5)
        self.assertLess(negative_result['polarity'], -0.3)
        self.assertAlmostEqual(neutral_result['polarity'], 0.0, delta=0.3)
    
    def test_noun_phrase_extraction(self):
        """Test extracting noun phrases from text."""
        text = "The quick brown fox jumped over the lazy dog. Machine learning models can analyze text effectively."
        
        phrases = extract_noun_phrases(text)
        
        self.assertIn("quick brown fox", phrases)
        self.assertIn("lazy dog", phrases)
        
        # TextBlob might parse "machine learning models" differently
        self.assertTrue(
            "machine learning models" in phrases or 
            ("machine" in phrases and "learning models" in phrases)
        )
    
    def test_spelling_correction(self):
        """Test spelling correction functionality."""
        misspelled_text = "I cant beleive it! The packge arived yesterday."
        corrected = correct_spelling(misspelled_text)
        
        # TextBlob's spelling correction might vary
        self.assertTrue("can" in corrected or "can't" in corrected)
        self.assertIn("believe", corrected)
        self.assertIn("package", corrected)
        self.assertIn("arrived", corrected)
    
    def test_pos_tagging(self):
        """Test part-of-speech tagging."""
        text = "The cat sat on the mat."
        tags = get_pos_tags(text)
        
        # Check that we have the right number of tags
        self.assertEqual(len(tags), 6)
        
        # Check that "cat" is tagged as a noun
        cat_tag = next((tag for tag in tags if tag[0].lower() == "cat"), None)
        self.assertIsNotNone(cat_tag)
        self.assertEqual(cat_tag[1], "NN")
        
        # Check that "sat" is tagged as a verb
        sat_tag = next((tag for tag in tags if tag[0].lower() == "sat"), None)
        self.assertIsNotNone(sat_tag)
        self.assertEqual(sat_tag[1][:2], "VB")
    
    def test_tokenization(self):
        """Test tokenization of text."""
        text = "Hello, world! How are you doing today?"
        tokens = tokenize_text(text)
        
        expected_tokens = ["Hello", "world", "How", "are", "you", "doing", "today"]
        for token in expected_tokens:
            self.assertIn(token, tokens)
        
        self.assertEqual(len(tokens), 7)
    
    def test_comprehensive_analysis(self):
        """Test the comprehensive text analysis function."""
        text = "I really love the new chatbot! It understands my questions perfectly and provides helpful answers."
        
        analysis = analyze_text(text)
        
        # Check that all expected keys are present
        self.assertIn('sentiment', analysis)
        self.assertIn('noun_phrases', analysis)
        self.assertIn('pos_tags', analysis)
        self.assertIn('tokens', analysis)
        self.assertIn('word_counts', analysis)
        
        # Check sentiment is positive
        self.assertGreater(analysis['sentiment']['polarity'], 0.5)
        
        # Check tokens 
        self.assertIn('really', analysis['tokens'])
        self.assertIn('love', analysis['tokens'])
        self.assertIn('chatbot', analysis['tokens'])
        
        # Check word counts
        self.assertEqual(analysis['word_counts'].get('love', 0), 1)


if __name__ == '__main__':
    unittest.main() 