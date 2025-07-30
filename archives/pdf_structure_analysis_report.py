#!/usr/bin/env python3
"""
PDF Structure Analysis Report for 'Traité de Caractérologie'
Analysis of sub-chapter patterns for optimal document chunking
"""

from langchain_community.document_loaders import PyPDFLoader
import re

def generate_chunking_recommendations():
    """Generate final recommendations for PDF chunking based on structure analysis"""
    
    print("="*80)
    print("PDF STRUCTURE ANALYSIS REPORT")
    print("Document: Traité de Caractérologie by René Le Senne")
    print("="*80)
    
    loader = PyPDFLoader("documents/traite_caracterologie.pdf")
    pages = loader.load()
    
    print(f"Total pages: {len(pages)}")
    
    # Test different chunking patterns with examples
    patterns = {
        'primary_numbered_sections': {
            'regex': r'^\s*(\d+)\.\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{10,100})',
            'description': 'Main numbered sections (1. Section Title)',
            'examples': [],
            'count': 0
        },
        'roman_numeral_sections': {
            'regex': r'^\s*([IVX]+)\.\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{10,100})',
            'description': 'Roman numeral sections (I. Section Title)',
            'examples': [],
            'count': 0
        },
        'major_headings': {
            'regex': r'^\s*(CHAPITRE|PARTIE|SECTION|INTRODUCTION|PRÉFACE|DOCUMENTATION)\s*[:\.\-]?\s*([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{0,100})',
            'description': 'Major structural headings',
            'examples': [],
            'count': 0
        }
    }
    
    # Analyze patterns across the document
    for i, page in enumerate(pages):
        content = page.page_content
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if len(line) < 5:
                continue
                
            for pattern_name, pattern_info in patterns.items():
                matches = re.findall(pattern_info['regex'], line, re.IGNORECASE)
                if matches:
                    patterns[pattern_name]['count'] += 1
                    if len(patterns[pattern_name]['examples']) < 10:
                        patterns[pattern_name]['examples'].append({
                            'page': i + 1,
                            'text': line[:100] + ('...' if len(line) > 100 else ''),
                            'match': matches[0] if matches else None
                        })
    
    # Report findings
    print("\nPATTERN ANALYSIS RESULTS:")
    print("-" * 50)
    
    for pattern_name, pattern_info in patterns.items():
        print(f"\n{pattern_name.upper().replace('_', ' ')}:")
        print(f"  Count: {pattern_info['count']}")
        print(f"  Regex: {pattern_info['regex']}")
        print(f"  Description: {pattern_info['description']}")
        
        if pattern_info['examples']:
            print("  Examples:")
            for example in pattern_info['examples'][:5]:
                print(f"    Page {example['page']:3d}: {example['text']}")
    
    # Provide specific recommendations
    print("\n" + "="*80)
    print("CHUNKING RECOMMENDATIONS")
    print("="*80)
    
    recommendations = [
        {
            'priority': 1,
            'name': 'Primary Numbered Sections',
            'pattern': r'^\s*(\d+)\.\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\n]{10,100})',
            'rationale': f'Found {patterns["primary_numbered_sections"]["count"]} numbered sections. This is the most consistent pattern.',
            'chunk_size': 'Variable (1-5 pages per section)',
            'pros': ['Very consistent', 'Clear semantic boundaries', 'Matches document structure'],
            'cons': ['May create uneven chunk sizes', 'Some very short sections']
        },
        {
            'priority': 2,
            'name': 'Major Structural Headings',
            'pattern': r'^\s*(CHAPITRE|PARTIE|SECTION|INTRODUCTION|PRÉFACE|DOCUMENTATION)',
            'rationale': 'Creates larger, more balanced chunks for major document sections.',
            'chunk_size': 'Large (10-50 pages per section)',
            'pros': ['Creates balanced chunks', 'Major semantic boundaries'],
            'cons': ['Fewer splits', 'May be too large for some use cases']
        },
        {
            'priority': 3,
            'name': 'Hybrid Approach',
            'pattern': 'Combined patterns with size limits',
            'rationale': 'Use numbered sections but combine small sections and split large ones.',
            'chunk_size': 'Optimized (2-8 pages per chunk)',
            'pros': ['Best of both worlds', 'Consistent chunk sizes', 'Semantic boundaries'],
            'cons': ['More complex implementation']
        }
    ]
    
    for rec in recommendations:
        print(f"\n{rec['priority']}. {rec['name'].upper()}")
        print(f"   Pattern: {rec['pattern']}")
        print(f"   Rationale: {rec['rationale']}")
        print(f"   Chunk Size: {rec['chunk_size']}")
        print(f"   Pros: {', '.join(rec['pros'])}")
        print(f"   Cons: {', '.join(rec['cons'])}")
    
    # Implementation code examples
    print("\n" + "="*80)
    print("IMPLEMENTATION EXAMPLES")
    print("="*80)
    
    print("\n1. LANGCHAIN TEXT SPLITTER WITH NUMBERED SECTIONS:")
    print("-" * 50)
    print("""
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re

class NumberedSectionSplitter:
    def __init__(self):
        self.section_pattern = r'^\\s*(\\d+)\\.\\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\\n]{10,100})'
    
    def split_text(self, text):
        # Find all section boundaries
        lines = text.split('\\n')
        sections = []
        current_section = []
        
        for line in lines:
            if re.match(self.section_pattern, line.strip()):
                if current_section:
                    sections.append('\\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        
        if current_section:
            sections.append('\\n'.join(current_section))
        
        return sections
""")
    
    print("\n2. REGEX FOR FINDING SPLIT POINTS:")
    print("-" * 50)
    print("""
# Primary pattern (most reliable)
numbered_section_pattern = r'^\\s*(\\d+)\\.\\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\\n]{10,100})'

# Alternative patterns
roman_numeral_pattern = r'^\\s*([IVX]+)\\.\\s+([A-ZÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ][^\\n]{10,100})'
major_heading_pattern = r'^\\s*(CHAPITRE|PARTIE|SECTION|INTRODUCTION|PRÉFACE)'

# Combined pattern for flexibility
combined_pattern = f'({numbered_section_pattern})|({roman_numeral_pattern})|({major_heading_pattern})'
""")
    
    print("\n3. CHUNK SIZE OPTIMIZATION:")
    print("-" * 50)
    print("""
def optimize_chunks(sections, min_size=1000, max_size=8000):
    optimized = []
    current_chunk = ""
    
    for section in sections:
        if len(current_chunk) + len(section) <= max_size:
            current_chunk += "\\n\\n" + section if current_chunk else section
        else:
            if len(current_chunk) >= min_size:
                optimized.append(current_chunk)
                current_chunk = section
            else:
                current_chunk += "\\n\\n" + section
    
    if current_chunk:
        optimized.append(current_chunk)
    
    return optimized
""")
    
    return patterns

if __name__ == "__main__":
    generate_chunking_recommendations()