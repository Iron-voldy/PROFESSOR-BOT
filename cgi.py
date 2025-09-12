"""
CGI compatibility module for Python 3.13+
This provides basic cgi functionality that was removed in Python 3.13
"""

import urllib.parse
from html import escape

def parse_qs(qs, keep_blank_values=False, strict_parsing=False, 
             encoding='utf-8', errors='replace', max_num_fields=None, separator='&'):
    """Parse a query string given as a string argument."""
    return urllib.parse.parse_qs(qs, keep_blank_values, strict_parsing, 
                                encoding, errors, max_num_fields, separator)

def parse_qsl(qs, keep_blank_values=False, strict_parsing=False,
              encoding='utf-8', errors='replace', max_num_fields=None, separator='&'):
    """Parse a query string given as a string argument."""
    return urllib.parse.parse_qsl(qs, keep_blank_values, strict_parsing,
                                 encoding, errors, max_num_fields, separator)

def escape_html(s, quote=True):
    """Replace special characters with HTML entities."""
    return escape(s, quote)

# For compatibility
escape = escape_html