#!/usr/bin/env python3
"""
Production-level optimized script for analyzing Faroese text statistics.
Calculates most common words, letters, bigraphs, and trigraphs.
"""

import re
from collections import Counter
import sys


def read_file(filename):
    """Read the entire file content."""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def get_words(text):
    """Extract words from text using regex."""
    # Find all sequences of word characters (letters, digits, underscores)
    words = re.findall(r'\b\w+\b', text.lower())
    return words


def get_letters(text):
    """Extract individual letters from text."""
    # Only keep alphabetic characters
    letters = [char for char in text.lower() if char.isalpha()]
    return letters


def get_bigraphs(text):
    """Extract letter bigraphs (pairs of consecutive letters) from text."""
    # Clean text to only include letters
    clean_text = ''.join(char for char in text.lower() if char.isalpha())
    bigraphs = []
    for i in range(len(clean_text) - 1):
        bigraphs.append(clean_text[i:i+2])
    return bigraphs


def get_trigraphs(text):
    """Extract letter trigraphs (triplets of consecutive letters) from text."""
    # Clean text to only include letters
    clean_text = ''.join(char for char in text.lower() if char.isalpha())
    trigraphs = []
    for i in range(len(clean_text) - 2):
        trigraphs.append(clean_text[i:i+3])
    return trigraphs


def write_results(counter, output_filename):
    """Write counter results to a file in descending order."""
    with open(output_filename, 'w', encoding='utf-8') as f:
        for item, count in counter.most_common():
            f.write(f"{item}\t{count}\n")


def main(input_filename):
    print("Reading file...")
    text = read_file(input_filename)
    
    print("Processing words...")
    words = get_words(text)
    word_counts = Counter(words)
    write_results(word_counts, 'MostCommonWords.txt')
    print(f"Processed {len(words)} words")
    
    print("Processing letters...")
    letters = get_letters(text)
    letter_counts = Counter(letters)
    write_results(letter_counts, 'MostCommonLetters.txt')
    print(f"Processed {len(letters)} letters")
    
    print("Processing bigraphs...")
    bigraphs = get_bigraphs(text)
    bigraph_counts = Counter(bigraphs)
    write_results(bigraph_counts, 'MostCommonBigraphs.txt')
    print(f"Processed {len(bigraphs)} bigraphs")
    
    print("Processing trigraphs...")
    trigraphs = get_trigraphs(text)
    trigraph_counts = Counter(trigraphs)
    write_results(trigraph_counts, 'MostCommonTrigraphs.txt')
    print(f"Processed {len(trigraphs)} trigraphs")
    
    print("Analysis complete!")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python analyze_faroese.py <input_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    main(input_file)