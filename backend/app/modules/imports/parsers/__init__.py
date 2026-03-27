"""Parser cascade for broker note import.

Parser cascade order:
1. correpy_parser.parse_with_correpy  — primary B3 nota de corretagem parser
2. pdfplumber_parser.parse_with_pdfplumber — table-extraction fallback
3. gpt4o_parser.parse_with_gpt4o — vision-based last resort
"""
