import re

def removeSpecialCharacters(string):
    """Remove special characters from string for filesystem safety"""
    pattern = re.compile(r'[^a-zA-Z0-9\s]')
    return re.sub(pattern, '', string) 