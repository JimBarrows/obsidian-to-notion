"""Parser for Obsidian markdown files."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import frontmatter  # type: ignore[import-untyped]
import yaml


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
        self.logger = logging.getLogger(__name__)

    def process_vault(self, error_recovery: bool = True) -> Dict:
        """Process entire Obsidian vault and extract all content.

        Args:
            error_recovery: Whether to enable error recovery for invalid YAML

        Returns:
            Dictionary containing processed files, attachments, and wikilink map
        """
        print(f"Processing vault at: {self.vault_path}")

        if not self.vault_path.exists():
            raise FileNotFoundError(f"Vault path does not exist: {self.vault_path}")

        for file_path in self.vault_path.rglob("*"):
            if file_path.suffix == ".md":
                file_info = self.process_markdown_file(file_path, error_recovery)
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

    def _fix_yaml_common_errors(self, yaml_text: str) -> str:
        """Fix common YAML syntax errors.

        Args:
            yaml_text: Raw YAML text

        Returns:
            Fixed YAML text
        """
        # Replace tabs with spaces
        yaml_text = yaml_text.replace("\t", "  ")

        # Fix missing space after colon (but not in URLs)
        lines = yaml_text.split("\n")
        fixed_lines = []
        for line in lines:
            # Skip lines that look like URLs or markdown links
            if "http://" in line or "https://" in line or "](" in line:
                fixed_lines.append(line)
                continue

            # Fix missing space after colon in key:value pairs
            # Match word characters followed by colon and non-space
            match = re.match(r"^(\s*)([^:\s]+):(\S.*)$", line)
            if match:
                indent, key, value = match.groups()
                fixed_lines.append(f"{indent}{key}: {value}")
            else:
                fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def _extract_yaml_content_split(self, content: str) -> Tuple[str, str]:
        """Extract YAML frontmatter and content separately.

        Args:
            content: Full file content

        Returns:
            Tuple of (yaml_text, markdown_content)
        """
        # Check if file starts with frontmatter delimiter
        if not content.strip().startswith("---"):
            return "", content

        # Split by the delimiter
        parts = content.split("---", 2)

        if len(parts) >= 3:
            # Standard format: ---\nyaml\n---\ncontent
            yaml_text = parts[1]
            markdown_content = "---".join(parts[2:])
        elif len(parts) == 2:
            # Missing closing delimiter
            yaml_text = parts[1]
            # Check if yaml_text contains markdown content
            if "\n\n" in yaml_text:
                yaml_part, markdown_part = yaml_text.split("\n\n", 1)
                yaml_text = yaml_part
                markdown_content = markdown_part
            else:
                markdown_content = ""
        else:
            return "", content

        return yaml_text.strip(), markdown_content.strip()

    def _parse_yaml_with_recovery(self, yaml_text: str) -> Dict:
        """Parse YAML with error recovery.

        Args:
            yaml_text: YAML text to parse

        Returns:
            Parsed metadata dictionary (empty dict on complete failure)
        """
        if not yaml_text:
            return {}

        # First attempt: Parse as-is
        try:
            return yaml.safe_load(yaml_text) or {}
        except yaml.YAMLError:
            pass

        # Second attempt: Fix common errors
        try:
            fixed_yaml = self._fix_yaml_common_errors(yaml_text)
            return yaml.safe_load(fixed_yaml) or {}
        except yaml.YAMLError:
            pass

        # Third attempt: Remove template placeholders
        try:
            # Replace {{placeholder}} with empty string
            cleaned_yaml = re.sub(r"\{\{[^}]+\}\}", '""', yaml_text)
            cleaned_yaml = self._fix_yaml_common_errors(cleaned_yaml)
            return yaml.safe_load(cleaned_yaml) or {}
        except yaml.YAMLError:
            pass

        # Fourth attempt: Extract simple key-value pairs
        metadata = {}
        for line in yaml_text.split("\n"):
            # Match simple key: value pattern
            match = re.match(r"^([^:]+):\s*(.+)$", line.strip())
            if match:
                key, value = match.groups()
                # Skip lines with template syntax or other issues
                if "{{" not in value and "[[" not in key:
                    metadata[key.strip()] = value.strip()

        return metadata

    def process_markdown_file(
        self, file_path: Path, error_recovery: bool = True
    ) -> Optional[Dict]:
        """Process a single markdown file with optional error recovery.

        Args:
            file_path: Path to the markdown file
            error_recovery: Whether to attempt error recovery for invalid YAML

        Returns:
            Dictionary with file information or None if completely unreadable
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            metadata = {}
            markdown_content = content

            # Try standard frontmatter parsing first
            try:
                post = frontmatter.loads(content)
                metadata = post.metadata
                markdown_content = post.content
            except Exception as e:
                if error_recovery:
                    # Attempt manual parsing with error recovery
                    self.logger.warning(
                        f"Standard frontmatter parsing failed for {file_path}: {e}. "
                        "Attempting error recovery..."
                    )
                    yaml_text, markdown_content = self._extract_yaml_content_split(
                        content
                    )
                    if yaml_text:
                        metadata = self._parse_yaml_with_recovery(yaml_text)
                        if not metadata:
                            self.logger.warning(
                                f"Could not parse YAML frontmatter in {file_path}. "
                                "Proceeding with empty metadata."
                            )
                else:
                    # Re-raise if error recovery is disabled
                    raise

            # Extract title from metadata or filename
            title = metadata.get("title", file_path.stem)

            # If title is empty or contains template syntax, use filename
            if not title or "{{" in str(title):
                title = file_path.stem

            # Find wikilinks in content
            wikilinks = self.extract_wikilinks(markdown_content)

            # Find attachments referenced in content
            embedded_attachments = self.extract_embedded_attachments(markdown_content)

            file_info = {
                "path": file_path,
                "title": title,
                "metadata": metadata,
                "content": markdown_content,
                "wikilinks": wikilinks,
                "embedded_attachments": embedded_attachments,
                "relative_path": file_path.relative_to(self.vault_path),
            }

            # Build wikilink map for later resolution
            self.wikilink_map[title.lower()] = file_path

            return file_info

        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")

            # If error recovery is enabled, try to at least get the content
            if error_recovery:
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    # Extract any content after potential frontmatter
                    _, markdown_content = self._extract_yaml_content_split(content)
                    if not markdown_content:
                        markdown_content = content

                    return {
                        "path": file_path,
                        "title": file_path.stem,
                        "metadata": {},
                        "content": markdown_content,
                        "wikilinks": self.extract_wikilinks(markdown_content),
                        "embedded_attachments": self.extract_embedded_attachments(
                            markdown_content
                        ),
                        "relative_path": file_path.relative_to(self.vault_path),
                    }
                except Exception as recovery_error:
                    self.logger.error(
                        f"Error recovery also failed for {file_path}: {recovery_error}"
                    )

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
