"""Parser for Obsidian markdown files."""

import re
from pathlib import Path
from typing import Dict, List, Optional

import frontmatter  # type: ignore[import-untyped]


class ObsidianVaultProcessor:
    """Process Obsidian vault and extract all content."""

    def __init__(self, vault_path: str):
        """Initialize the processor with the vault path.

        Args:
            vault_path: Path to the Obsidian vault directory
        """
        self.vault_path = Path(vault_path)
        self.markdown_files: List[Dict] = []
        self.attachments: List[Path] = []
        self.wikilink_map: Dict[str, Path] = {}

    def process_vault(self) -> Dict:
        """Process entire Obsidian vault and extract all content."""
        print(f"Processing vault at: {self.vault_path}")

        if not self.vault_path.exists():
            raise FileNotFoundError(f"Vault path does not exist: {self.vault_path}")

        for file_path in self.vault_path.rglob("*"):
            if file_path.suffix == ".md":
                file_info = self.process_markdown_file(file_path)
                if file_info:
                    self.markdown_files.append(file_info)
            elif file_path.suffix.lower() in [
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".pdf",
                ".docx",
                ".xlsx",
            ]:
                self.attachments.append(file_path)

        print(
            f"Found {len(self.markdown_files)} markdown files and "
            f"{len(self.attachments)} attachments"
        )

        return {
            "markdown_files": self.markdown_files,
            "attachments": self.attachments,
            "wikilink_map": self.wikilink_map,
        }

    def process_markdown_file(self, file_path: Path) -> Optional[Dict]:
        """Process a single markdown file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                post = frontmatter.load(f)

            # Extract title from filename if not in frontmatter
            title = post.metadata.get("title", file_path.stem)

            # Find wikilinks in content
            wikilinks = self.extract_wikilinks(post.content)

            # Find attachments referenced in content
            embedded_attachments = self.extract_embedded_attachments(post.content)

            file_info = {
                "path": file_path,
                "title": title,
                "metadata": post.metadata,
                "content": post.content,
                "wikilinks": wikilinks,
                "embedded_attachments": embedded_attachments,
                "relative_path": file_path.relative_to(self.vault_path),
            }

            # Build wikilink map for later resolution
            self.wikilink_map[title.lower()] = file_path

            return file_info

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None

    def extract_wikilinks(self, content: str) -> List[Dict]:
        """Extract all wikilink variations from content."""
        # Comprehensive regex for all wikilink types
        wikilink_pattern = (
            r"(!)?\[\[(?:([^|\]#]+?)(?:#([^|\]]+?))?(?:\|([^\]]+?))?)?\]\]"
        )

        wikilinks = []
        for match in re.finditer(wikilink_pattern, content):
            is_embed, note_name, heading, display_text = match.groups()

            wikilinks.append(
                {
                    "original": match.group(0),
                    "is_embed": bool(is_embed),
                    "note_name": note_name or display_text,
                    "heading": heading,
                    "display_text": display_text or note_name,
                    "start": match.start(),
                    "end": match.end(),
                }
            )

        return wikilinks

    def extract_embedded_attachments(self, content: str) -> List[str]:
        """Extract embedded attachment references."""
        # Pattern for embedded images and files
        attachment_pattern = r"!\[\[([^\]]+\.(png|jpg|jpeg|gif|pdf|docx|xlsx))\]\]"

        attachments = []
        for match in re.finditer(attachment_pattern, content, re.IGNORECASE):
            attachments.append(match.group(1))

        return attachments

    def sanitize_for_notion(self, text: str) -> str:
        """Clean text for Notion compatibility."""
        replacements = {
            "\u00a0": " ",  # Non-breaking space
            "*": "",  # Asterisk in filenames
            "/": "-",  # Forward slash
            "\\": "-",  # Backslash
            "<": "",
            ">": "",
            "|": "-",
            "?": "",
            ":": "-",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text.strip()
