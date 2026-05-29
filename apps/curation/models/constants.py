"""
Cross-cutting constants used across multiple modules.
Feature-specific constants should stay in their respective modules.
"""

# Privacy levels for user preferences
PRIVACY_CHOICES = [
    ('public', 'Public'),
    ('internal', 'Internal Only'),
    ('private', 'Private'),
]
