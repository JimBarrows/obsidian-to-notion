# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Pre-commit hooks configuration for enforcing code quality standards
- Comprehensive GitHub Actions CI/CD workflows:
  - CI workflow with linting, security scanning, and testing across Python 3.8-3.11
  - Release workflow for automated PyPI publishing
  - Scheduled dependency security checks
- Security scanning tools (Bandit and Safety)
- Code coverage requirements (80% minimum threshold)
- Flake8 configuration file for consistent linting rules
- Additional development tools in pyproject.toml (ruff, isort)
- Configuration for coverage.py, bandit, isort, and ruff in pyproject.toml

### Changed
- All code formatted with Black for consistent style
- Fixed all flake8 linting issues (112 violations resolved)
- Updated pyproject.toml with comprehensive tool configurations
- Removed unused imports across the codebase

### Fixed
- Line length violations in code
- Unused variable assignments
- Import ordering issues

## [0.1.0] - 2024-01-15

### Added
- Initial release with Obsidian vault parsing functionality
- ObsidianVaultProcessor for comprehensive vault parsing
- Dataclass-based configuration system
- CLI with argument parsing
- BDD tests using Behave/Gherkin
- Unit tests with pytest
