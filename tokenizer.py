import re
import sys
from collections import Counter

# An updated set of stopwords (feel free to adjust)
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "almost", "also",
    "am", "an", "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can", "cannot",
    "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd",
    "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its",
    "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll",
    "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
    "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these",
    "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll",
    "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with",
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your",
    "yours", "yourself", "yourselves"
}

class Tokenizer:
    def __init__(self):
        # 1. Decimal numbers with optional sign (e.g., -0.25, +3.14)
        # 2. Integers with optional sign (e.g., -42, +7)
        # 3. Word tokens: sequences of alphanumeric characters and underscore.
        # The re.UNICODE flag ensures proper handling of non-English characters.
        self.pattern = re.compile(
            r'[-+]?\d*\.\d+|[-+]?\d+|\b\w+\b', re.UNICODE)

    def tokenize(self, text_file_path):
        """
        Reads the file line by line and extracts tokens using a regular expression.
        Tokens are converted to lowercase and filtered to remove single-letter tokens.
        :param text_file_path: Path to the text file.
        :return: List of tokens.
        """
        tokens = []
        try:
            with open(text_file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    # Find all tokens in the line.
                    line_tokens = self.pattern.findall(line.lower())
                    # Filter out tokens that are a single character.
                    filtered = [token for token in line_tokens if len(token) > 1]
                    tokens.extend(filtered)
        except FileNotFoundError:
            print(f"ERROR: File not found: {text_file_path}")
            sys.exit(1)
        return tokens

    def compute_word_frequencies(self, tokens):
        return dict(Counter(tokens))

    def print_frequencies(self, frequencies):
        sorted_frequencies = sorted(frequencies.items(), key=lambda x: (-x[1], x[0]))
        for token, freq in sorted_frequencies:
            print(f"{token} -> {freq}")

    def find_intersection(self, tokens1, tokens2):
        return len(set(tokens1) & set(tokens2))
