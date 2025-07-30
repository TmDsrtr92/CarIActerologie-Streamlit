from langchain_community.document_loaders import PyPDFLoader
import re
from collections import defaultdict

def analyze_document_structure():
    """Analyze PDF document structure to identify sub-chapter patterns"""
    try:
        loader = PyPDFLoader("documents/traite_caracterologie.pdf")
        pages = loader.load()
        
        print(f"Document loaded successfully: {len(pages)} pages")
        
        # Patterns to look for sub-chapters
        patterns = {
            'numbered_sections': r'^\s*(\d+)\.\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{10,100})\s*$',
            'numbered_subsections': r'^\s*(\d+)\.\s*(\d+)\.\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{10,100})\s*$',
            'lettered_sections': r'^\s*([A-Z])\.\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{10,100})\s*$',
            'roman_numerals': r'^\s*([IVX]+)\.\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{10,100})\s*$',
            'chapter_headings': r'^\s*(CHAPITRE|PARTIE|SECTION)\s+([IVX\d]+)\s*[:\.\-]?\s*([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{5,100})\s*$',
            'all_caps_headings': r'^\s*([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ\s]{10,80})\s*$'
        }
        
        found_patterns = defaultdict(list)
        page_analysis = []
        
        # Analyze each page
        for i, page in enumerate(pages):
            content = page.page_content
            lines = content.split('\n')
            
            page_info = {
                'page_num': i + 1,
                'line_count': len(lines),
                'patterns_found': []
            }
            
            # Look for patterns in each line
            for line_num, line in enumerate(lines):
                line = line.strip()
                if len(line) < 5:  # Skip very short lines
                    continue
                    
                for pattern_name, pattern in patterns.items():
                    matches = re.findall(pattern, line, re.MULTILINE | re.IGNORECASE)
                    if matches:
                        match_info = {
                            'pattern': pattern_name,
                            'line': line,
                            'line_num': line_num,
                            'matches': matches
                        }
                        found_patterns[pattern_name].append({
                            'page': i + 1,
                            'line': line,
                            'matches': matches
                        })
                        page_info['patterns_found'].append(match_info)
            
            page_analysis.append(page_info)
        
        # Report findings
        print("\n" + "="*80)
        print("DOCUMENT STRUCTURE ANALYSIS")
        print("="*80)
        
        for pattern_name, matches in found_patterns.items():
            if matches:
                print(f"\n{pattern_name.upper().replace('_', ' ')} ({len(matches)} found):")
                print("-" * 50)
                for match in matches[:10]:  # Show first 10 examples
                    print(f"Page {match['page']:3d}: {match['line'][:80]}...")
                if len(matches) > 10:
                    print(f"... and {len(matches) - 10} more")
        
        # Look for table of contents
        print("\n" + "="*80)
        print("SEARCHING FOR TABLE OF CONTENTS")
        print("="*80)
        
        toc_keywords = ['table', 'sommaire', 'matières', 'contents', 'index']
        for i, page in enumerate(pages[:20]):  # Check first 20 pages
            content = page.page_content.lower()
            if any(keyword in content for keyword in toc_keywords):
                print(f"\nPossible TOC found on page {i + 1}:")
                print("-" * 50)
                lines = page.page_content.split('\n')
                for line in lines[:20]:  # Show first 20 lines
                    if line.strip():
                        print(line.strip())
                break
        
        # Analyze specific pages for detailed structure
        print("\n" + "="*80)
        print("DETAILED PAGE ANALYSIS (Pages 20-30)")
        print("="*80)
        
        for i in range(19, min(30, len(pages))):
            page = pages[i]
            content = page.page_content
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            print(f"\n--- Page {i + 1} ---")
            print(f"Line count: {len(lines)}")
            
            # Show lines that might be headings (short, capitalized, or numbered)
            potential_headings = []
            for line in lines:
                if (len(line) < 100 and 
                    (line.isupper() or 
                     re.match(r'^\s*\d+\.', line) or 
                     re.match(r'^\s*[A-Z]\.', line) or
                     re.match(r'^\s*[IVX]+\.', line))):
                    potential_headings.append(line)
            
            if potential_headings:
                print("Potential headings:")
                for heading in potential_headings:
                    print(f"  • {heading}")
        
        return found_patterns, page_analysis
        
    except Exception as e:
        print(f"Error analyzing document: {e}")
        return None, None

def suggest_chunking_patterns(found_patterns):
    """Suggest regex patterns for chunking based on analysis"""
    print("\n" + "="*80)
    print("SUGGESTED CHUNKING PATTERNS")
    print("="*80)
    
    suggestions = []
    
    if found_patterns.get('numbered_sections'):
        suggestions.append({
            'name': 'Numbered Sections',
            'pattern': r'^\s*(\d+)\.\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{10,100})',
            'description': 'Split on numbered sections (e.g., "1. Introduction")'
        })
    
    if found_patterns.get('numbered_subsections'):
        suggestions.append({
            'name': 'Numbered Subsections',
            'pattern': r'^\s*(\d+)\.\s*(\d+)\.\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{10,100})',
            'description': 'Split on numbered subsections (e.g., "1.1. Overview")'
        })
    
    if found_patterns.get('chapter_headings'):
        suggestions.append({
            'name': 'Chapter Headings',
            'pattern': r'^\s*(CHAPITRE|PARTIE|SECTION)\s+([IVX\d]+)',
            'description': 'Split on major chapter/section headings'
        })
    
    if found_patterns.get('all_caps_headings'):
        suggestions.append({
            'name': 'All Caps Headings',
            'pattern': r'^\s*([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ\s]{10,80})\s*$',
            'description': 'Split on all-caps headings (use with caution)'
        })
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion['name']}")
        print(f"   Pattern: {suggestion['pattern']}")
        print(f"   Description: {suggestion['description']}")
        print()
    
    if not suggestions:
        print("No clear patterns found. Consider:")
        print("1. Manual inspection of more pages")
        print("2. Fixed-size chunking")
        print("3. Semantic-based chunking")

def test_document_structure():
    """Test to verify PDF document structure and loading"""
    try:
        loader = PyPDFLoader("documents/traite_caracterologie.pdf")
        pages = loader.load()
        
        print(f"Document loaded successfully: {len(pages)} pages")
        
        # Display pages 10-15 to verify structure
        start_page = min(10, len(pages))
        end_page = min(15, len(pages))
        
        for i in range(start_page, end_page):
            print(f"\n--- Page {i + 1} ---")
            print(f"Content preview (first 200 chars): {pages[i].page_content[:200]}...")
            print(f"Metadata: {pages[i].metadata}")
            
        return True
    except Exception as e:
        print(f"Error loading document: {e}")
        return False

if __name__ == "__main__":
    print("Running comprehensive document structure analysis...")
    found_patterns, page_analysis = analyze_document_structure()
    if found_patterns:
        suggest_chunking_patterns(found_patterns)