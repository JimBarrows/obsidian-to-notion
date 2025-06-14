"""Unit tests for ProgressTracker class."""

import unittest
from unittest.mock import Mock, patch

from obsidian_to_notion.utils.progress import ProgressTracker


class TestProgressTracker(unittest.TestCase):
    """Test ProgressTracker class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.tracker = ProgressTracker()

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_init(self, mock_tqdm: Mock) -> None:
        """Test ProgressTracker initialization."""
        tracker = ProgressTracker()
        self.assertIsNone(tracker.main_progress)
        self.assertIsNone(tracker.sub_progress)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_context_manager(self, mock_tqdm: Mock) -> None:
        """Test ProgressTracker as context manager."""
        mock_progress = Mock()
        mock_tqdm.return_value = mock_progress

        with ProgressTracker() as tracker:
            tracker.start_main(100, "Test")
            self.assertIsNotNone(tracker.main_progress)

        # Should have closed progress bars
        mock_progress.close.assert_called()

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_context_manager_with_exception(self, mock_tqdm: Mock) -> None:
        """Test ProgressTracker context manager with exception."""
        mock_progress = Mock()
        mock_tqdm.return_value = mock_progress

        try:
            with ProgressTracker() as tracker:
                tracker.start_main(100, "Test")
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should still close progress bars on exception
        mock_progress.close.assert_called()

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_start_main(self, mock_tqdm: Mock) -> None:
        """Test starting main progress bar."""
        mock_progress = Mock()
        mock_tqdm.return_value = mock_progress

        self.tracker.start_main(100, "Processing files")

        mock_tqdm.assert_called_once_with(
            total=100, desc="Processing files", position=0
        )
        self.assertEqual(self.tracker.main_progress, mock_progress)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_start_sub(self, mock_tqdm: Mock) -> None:
        """Test starting sub progress bar."""
        mock_progress = Mock()
        mock_tqdm.return_value = mock_progress

        self.tracker.start_sub(50, "Current file")

        mock_tqdm.assert_called_once_with(
            total=50, desc="Current file", position=1, leave=False
        )
        self.assertEqual(self.tracker.sub_progress, mock_progress)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_update_main(self, mock_tqdm: Mock) -> None:
        """Test updating main progress bar."""
        mock_progress = Mock()
        mock_tqdm.return_value = mock_progress

        self.tracker.start_main(100, "Test")
        self.tracker.update_main(5)

        mock_progress.update.assert_called_once_with(5)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_update_main_no_progress(self, mock_tqdm: Mock) -> None:
        """Test updating main progress bar when none exists."""
        # Should not raise error
        self.tracker.update_main(5)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_update_sub(self, mock_tqdm: Mock) -> None:
        """Test updating sub progress bar."""
        mock_progress = Mock()
        mock_tqdm.return_value = mock_progress

        self.tracker.start_sub(50, "Test")
        self.tracker.update_sub(3)

        mock_progress.update.assert_called_once_with(3)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_update_sub_no_progress(self, mock_tqdm: Mock) -> None:
        """Test updating sub progress bar when none exists."""
        # Should not raise error
        self.tracker.update_sub(3)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_set_main_desc(self, mock_tqdm: Mock) -> None:
        """Test setting main progress bar description."""
        mock_progress = Mock()
        mock_tqdm.return_value = mock_progress

        self.tracker.start_main(100, "Test")
        self.tracker.set_main_desc("New description")

        mock_progress.set_description.assert_called_once_with("New description")

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_set_main_desc_no_progress(self, mock_tqdm: Mock) -> None:
        """Test setting main progress bar description when none exists."""
        # Should not raise error
        self.tracker.set_main_desc("New description")

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_set_sub_desc(self, mock_tqdm: Mock) -> None:
        """Test setting sub progress bar description."""
        mock_progress = Mock()
        mock_tqdm.return_value = mock_progress

        self.tracker.start_sub(50, "Test")
        self.tracker.set_sub_desc("New description")

        mock_progress.set_description.assert_called_once_with("New description")

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_set_sub_desc_no_progress(self, mock_tqdm: Mock) -> None:
        """Test setting sub progress bar description when none exists."""
        # Should not raise error
        self.tracker.set_sub_desc("New description")

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_close_sub(self, mock_tqdm: Mock) -> None:
        """Test closing sub progress bar."""
        mock_progress = Mock()
        mock_tqdm.return_value = mock_progress

        self.tracker.start_sub(50, "Test")
        self.tracker.close_sub()

        mock_progress.close.assert_called_once()
        self.assertIsNone(self.tracker.sub_progress)

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_close_sub_no_progress(self, mock_tqdm: Mock) -> None:
        """Test closing sub progress bar when none exists."""
        # Should not raise error
        self.tracker.close_sub()

    @patch("obsidian_to_notion.utils.progress.tqdm")
    def test_close(self, mock_tqdm: Mock) -> None:
        """Test closing all progress bars."""
        mock_main = Mock()
        mock_sub = Mock()
        mock_tqdm.side_effect = [mock_main, mock_sub]

        self.tracker.start_main(100, "Main")
        self.tracker.start_sub(50, "Sub")
        self.tracker.close()

        mock_main.close.assert_called_once()
        mock_sub.close.assert_called_once()
        self.assertIsNone(self.tracker.main_progress)
        self.assertIsNone(self.tracker.sub_progress)


if __name__ == "__main__":
    unittest.main()
