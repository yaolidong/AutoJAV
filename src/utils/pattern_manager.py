"""Regex pattern manager for code extraction."""

import re
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class CodePattern:
    """Represents a code extraction pattern."""
    
    name: str
    pattern: str
    format: str
    description: str = ""
    enabled: bool = True
    priority: int = 0
    
    def __post_init__(self):
        """Validate the pattern after initialization."""
        try:
            re.compile(self.pattern, re.IGNORECASE)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{self.pattern}': {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodePattern':
        """Create pattern from dictionary."""
        return cls(**data)


class PatternManager:
    """Manages code extraction patterns."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the pattern manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.logger = logging.getLogger(__name__)
        # Try multiple paths for better compatibility
        if config_path:
            self.config_path = Path(config_path)
        elif Path("/app/config/patterns.json").exists():
            self.config_path = Path("/app/config/patterns.json")
        else:
            self.config_path = Path("config/patterns.json")
        self.patterns: List[CodePattern] = []
        self.compiled_patterns: List[re.Pattern] = []
        self.load_patterns()
    
    def load_patterns(self) -> None:
        """Load patterns from configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.patterns = [
                        CodePattern.from_dict(p) 
                        for p in data.get('patterns', [])
                    ]
                    self.logger.info(f"Loaded {len(self.patterns)} patterns from {self.config_path}")
            except Exception as e:
                self.logger.error(f"Error loading patterns: {e}")
                self.load_default_patterns()
        else:
            self.load_default_patterns()
        
        self._compile_patterns()
    
    def load_default_patterns(self) -> None:
        """Load default patterns."""
        self.patterns = [
            CodePattern(
                name="Standard AV Code",
                pattern=r'([A-Z]{2,5})[\s\-]?(\d{3,4})',
                format="{0}-{1}",
                description="Standard patterns like ABC-123, ABCD-123",
                priority=1
            ),
            CodePattern(
                name="Number Prefix Code",
                pattern=r'(\d+[A-Z]+)[\s\-]?(\d+)',
                format="{0}-{1}",
                description="Patterns with numbers in prefix like 1PON-123456",
                priority=2
            ),
            CodePattern(
                name="FC2 Pattern",
                pattern=r'(FC2)[\s\-]?(PPV)?[\s\-]?(\d+)',
                format="FC2-PPV-{2}",
                description="FC2 patterns like FC2-PPV-123456",
                priority=3
            ),
            CodePattern(
                name="Carib Pattern",
                pattern=r'(\d{6})[\s\-](\d{3})',
                format="{0}-{1}",
                description="Carib patterns like 123456-789",
                priority=4
            ),
            CodePattern(
                name="Tokyo Hot Pattern",
                pattern=r'(n)\s?(\d{4})',
                format="n{1}",
                description="Tokyo Hot patterns like n1234",
                priority=5
            ),
            CodePattern(
                name="Heydouga Pattern",
                pattern=r'(\d{4})[\s\-]?(PPV)?(\d+)',
                format="{0}-{2}",
                description="Heydouga patterns like 4017-PPV123",
                priority=6
            ),
        ]
        self.logger.info(f"Loaded {len(self.patterns)} default patterns")
    
    def _compile_patterns(self) -> None:
        """Compile enabled patterns."""
        self.compiled_patterns = []
        for pattern in self.patterns:
            if pattern.enabled:
                try:
                    compiled = re.compile(pattern.pattern, re.IGNORECASE)
                    self.compiled_patterns.append((compiled, pattern))
                except re.error as e:
                    self.logger.error(f"Error compiling pattern '{pattern.name}': {e}")
    
    def save_patterns(self) -> bool:
        """
        Save patterns to configuration file.
        
        Returns:
            True if saved successfully
        """
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'patterns': [p.to_dict() for p in self.patterns]
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(self.patterns)} patterns to {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving patterns: {e}")
            return False
    
    def add_pattern(self, pattern: CodePattern) -> bool:
        """
        Add a new pattern.
        
        Args:
            pattern: The pattern to add
            
        Returns:
            True if added successfully
        """
        try:
            # Check for duplicate names
            if any(p.name == pattern.name for p in self.patterns):
                self.logger.warning(f"Pattern with name '{pattern.name}' already exists")
                return False
            
            self.patterns.append(pattern)
            self._compile_patterns()
            self.save_patterns()
            self.logger.info(f"Added pattern: {pattern.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding pattern: {e}")
            return False
    
    def update_pattern(self, name: str, pattern: CodePattern) -> bool:
        """
        Update an existing pattern.
        
        Args:
            name: Name of the pattern to update
            pattern: Updated pattern data
            
        Returns:
            True if updated successfully
        """
        try:
            for i, p in enumerate(self.patterns):
                if p.name == name:
                    self.patterns[i] = pattern
                    self._compile_patterns()
                    self.save_patterns()
                    self.logger.info(f"Updated pattern: {name}")
                    return True
            
            self.logger.warning(f"Pattern '{name}' not found")
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating pattern: {e}")
            return False
    
    def delete_pattern(self, name: str) -> bool:
        """
        Delete a pattern.
        
        Args:
            name: Name of the pattern to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            self.patterns = [p for p in self.patterns if p.name != name]
            self._compile_patterns()
            self.save_patterns()
            self.logger.info(f"Deleted pattern: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting pattern: {e}")
            return False
    
    def test_pattern(self, pattern_str: str, test_string: str) -> Optional[Dict[str, Any]]:
        """
        Test a regex pattern against a string.
        
        Args:
            pattern_str: The regex pattern to test
            test_string: The string to test against
            
        Returns:
            Match result or None
        """
        try:
            compiled = re.compile(pattern_str, re.IGNORECASE)
            match = compiled.search(test_string)
            
            if match:
                return {
                    'matched': True,
                    'groups': match.groups(),
                    'full_match': match.group(0),
                    'start': match.start(),
                    'end': match.end()
                }
            else:
                return {
                    'matched': False,
                    'groups': [],
                    'full_match': None
                }
                
        except re.error as e:
            return {
                'matched': False,
                'error': str(e),
                'groups': [],
                'full_match': None
            }
    
    def extract_code(self, filename: str) -> Optional[str]:
        """
        Extract code from filename using all enabled patterns.
        
        Args:
            filename: The filename to extract code from
            
        Returns:
            Extracted code or None
        """
        # Clean the filename first
        from pathlib import Path
        name_without_ext = Path(filename).stem
        cleaned = self._clean_filename(name_without_ext)
        
        # Try each compiled pattern
        for compiled_pattern, pattern_obj in self.compiled_patterns:
            match = compiled_pattern.search(cleaned)
            if match:
                try:
                    # Format the code using the pattern's format template
                    groups = match.groups()
                    # Filter out None values from groups
                    groups = [g for g in groups if g is not None]
                    
                    # Apply format template
                    formatted = pattern_obj.format
                    for i, group in enumerate(groups):
                        formatted = formatted.replace(f"{{{i}}}", group)
                    
                    return formatted.upper()
                    
                except Exception as e:
                    self.logger.error(f"Error formatting code with pattern '{pattern_obj.name}': {e}")
                    continue
        
        return None
    
    def _clean_filename(self, filename: str) -> str:
        """
        Clean filename by removing common prefixes, suffixes, and noise.
        
        Args:
            filename: Filename to clean
            
        Returns:
            Cleaned filename
        """
        # Remove common prefixes
        prefixes_to_remove = [
            r'^\[.*?\]',  # Remove [tags] at the beginning
            r'^\(.*?\)',  # Remove (tags) at the beginning
            r'^【.*?】',   # Remove 【tags】 at the beginning
        ]
        
        cleaned = filename
        for prefix_pattern in prefixes_to_remove:
            cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove common suffixes
        suffixes_to_remove = [
            r'\[.*?\]$',  # Remove [tags] at the end
            r'\(.*?\)$',  # Remove (tags) at the end
            r'【.*?】$',   # Remove 【tags】 at the end
            r'_\d+p$',    # Remove quality indicators like _1080p
            r'_HD$',      # Remove HD suffix
            r'_FHD$',     # Remove FHD suffix
            r'_4K$',      # Remove 4K suffix
        ]
        
        for suffix_pattern in suffixes_to_remove:
            cleaned = re.sub(suffix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Replace underscores and dots with spaces, but preserve hyphens
        cleaned = re.sub(r'[_\.]', ' ', cleaned)
        
        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    def get_all_patterns(self) -> List[Dict[str, Any]]:
        """
        Get all patterns as dictionaries.
        
        Returns:
            List of pattern dictionaries
        """
        return [p.to_dict() for p in self.patterns]
    
    def get_pattern(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific pattern by name.
        
        Args:
            name: Name of the pattern
            
        Returns:
            Pattern dictionary or None
        """
        for pattern in self.patterns:
            if pattern.name == name:
                return pattern.to_dict()
        return None