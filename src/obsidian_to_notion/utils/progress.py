"""Progress reporting utilities."""

from typing import Any, Optional

from tqdm import tqdm  # type: ignore[import-untyped]


class ProgressTracker:
    """Context manager-enabled progress tracker for migration operations.

    This class provides progress tracking capabilities with support for
    nested progress bars and context manager usage.
    """

    def __init__(self) -> None:
        """Initialize progress tracker."""
        self.main_progress: Optional[tqdm] = None
        self.sub_progress: Optional[tqdm] = None

    def __enter__(self) -> "ProgressTracker":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and clean up progress bars."""
        self.close()

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
