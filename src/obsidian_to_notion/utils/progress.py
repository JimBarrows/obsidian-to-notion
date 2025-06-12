"""Progress reporting utilities."""

from typing import Optional

from tqdm import tqdm  # type: ignore[import-untyped]


class ProgressReporter:
    """Report progress for long-running operations."""

    def __init__(self) -> None:
        """Initialize progress reporter."""
        self.main_progress: Optional[tqdm] = None
        self.sub_progress: Optional[tqdm] = None

    def start_main(self, total: int, desc: str = "Processing") -> None:
        """Start main progress bar.

        Args:
            total: Total number of items
            desc: Description for progress bar
        """
        self.main_progress = tqdm(total=total, desc=desc, position=0)

    def start_sub(self, total: int, desc: str = "Current file") -> None:
        """Start sub progress bar.

        Args:
            total: Total number of items
            desc: Description for progress bar
        """
        self.sub_progress = tqdm(total=total, desc=desc, position=1, leave=False)

    def update_main(self, n: int = 1) -> None:
        """Update main progress bar.

        Args:
            n: Number of items completed
        """
        if self.main_progress:
            self.main_progress.update(n)

    def update_sub(self, n: int = 1) -> None:
        """Update sub progress bar.

        Args:
            n: Number of items completed
        """
        if self.sub_progress:
            self.sub_progress.update(n)

    def set_main_desc(self, desc: str) -> None:
        """Update main progress bar description.

        Args:
            desc: New description
        """
        if self.main_progress:
            self.main_progress.set_description(desc)

    def set_sub_desc(self, desc: str) -> None:
        """Update sub progress bar description.

        Args:
            desc: New description
        """
        if self.sub_progress:
            self.sub_progress.set_description(desc)

    def close_sub(self) -> None:
        """Close sub progress bar."""
        if self.sub_progress:
            self.sub_progress.close()
            self.sub_progress = None

    def close(self) -> None:
        """Close all progress bars."""
        self.close_sub()
        if self.main_progress:
            self.main_progress.close()
            self.main_progress = None
