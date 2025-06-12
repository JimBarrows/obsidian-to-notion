"""Parser for Obsidian markdown files."""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import frontmatter


class ObsidianParser:
    """Parse Obsidian markdown files and extract content, metadata, and links."""
    
    # Regex patterns for Obsidian syntax
    WIKILINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')
    EMBED_PATTERN = re.compile(r'!\[\[([^\]]+)\]\]')
    TAG_PATTERN = re.compile(r'#([\w-]+)')
    
    def __init__(self, vault_path: Path):
        """Initialize the parser with the vault path.
        
        Args:
            vault_path: Path to the Obsidian vault directory
        """
        self.vault_path = vault_path
    
    def parse_file(self, file_path: Path) -> Dict:
        """Parse an Obsidian markdown file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            Dictionary containing parsed content and metadata
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        
        content = post.content
        metadata = post.metadata
        
        # Extract links and embeds
        wikilinks = self.extract_wikilinks(content)
        embeds = self.extract_embeds(content)
        tags = self.extract_tags(content)
        
        # Get file info
        relative_path = file_path.relative_to(self.vault_path)
        
        return {
            'path': file_path,
            'relative_path': relative_path,
            'title': file_path.stem,
            'content': content,
            'metadata': metadata,
            'wikilinks': wikilinks,
            'embeds': embeds,
            'tags': tags,
        }
    
    def extract_wikilinks(self, content: str) -> List[Tuple[str, str]]:
        """Extract wikilinks from content.
        
        Args:
            content: Markdown content
            
        Returns:
            List of tuples (full_match, link_text)
        """
        matches = []
        for match in self.WIKILINK_PATTERN.finditer(content):
            full_match = match.group(0)
            link_text = match.group(1)
            matches.append((full_match, link_text))
        return matches
    
    def extract_embeds(self, content: str) -> List[Tuple[str, str]]:
        """Extract embedded files from content.
        
        Args:
            content: Markdown content
            
        Returns:
            List of tuples (full_match, embed_path)
        """
        matches = []
        for match in self.EMBED_PATTERN.finditer(content):
            full_match = match.group(0)
            embed_path = match.group(1)
            matches.append((full_match, embed_path))
        return matches
    
    def extract_tags(self, content: str) -> List[str]:
        """Extract tags from content.
        
        Args:
            content: Markdown content
            
        Returns:
            List of tag names
        """
        return list(set(match.group(1) for match in self.TAG_PATTERN.finditer(content)))
    
    def resolve_link(self, link_text: str, from_file: Path) -> Optional[Path]:
        """Resolve a wikilink to an actual file path.
        
        Args:
            link_text: The text inside the wikilink
            from_file: The file containing the link
            
        Returns:
            Resolved file path or None if not found
        """
        # Handle aliases (e.g., [[file|alias]])
        if '|' in link_text:
            link_path, _ = link_text.split('|', 1)
        else:
            link_path = link_text
        
        # Handle section links (e.g., [[file#section]])
        if '#' in link_path:
            link_path = link_path.split('#')[0]
        
        # If empty after removing section, it's a same-file link
        if not link_path:
            return from_file
        
        # Try different resolution strategies
        strategies = [
            # Absolute path from vault root
            self.vault_path / f"{link_path}.md",
            self.vault_path / link_path,
            # Relative to current file
            from_file.parent / f"{link_path}.md",
            from_file.parent / link_path,
        ]
        
        for path in strategies:
            if path.exists() and path.is_file():
                return path
        
        return None