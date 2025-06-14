# Pre-commit Setup Guide

This guide explains how to set up and use pre-commit hooks in the Obsidian to Notion migration project.

## Overview

Pre-commit hooks automatically validate and format code before each commit, ensuring consistent code quality across the project. The hooks run various linters and formatters to catch issues early in the development process.

## Installation

### Prerequisites

- Python 3.8 or higher
- Git

### Setup Steps

1. **Install the project with dev dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```
   This installs pre-commit along with all other development tools.

2. **Install the pre-commit hooks:**
   ```bash
   pre-commit install
   ```
   This sets up Git hooks that will run automatically before each commit.

## Configured Hooks

The project uses the following pre-commit hooks:

### Code Formatting
- **Black**: Formats Python code to ensure consistent style
- **isort**: Sorts and organizes import statements

### Code Quality
- **Flake8**: Checks for Python style guide violations and common errors
- **Ruff**: Fast Python linter that includes rules from multiple tools
- **Mypy**: Performs static type checking
- **Bandit**: Scans for common security issues

### Other Checks
- **Trailing whitespace**: Removes unnecessary whitespace at line ends
- **End of file fixer**: Ensures files end with a newline
- **YAML check**: Validates YAML file syntax
- **Large file check**: Prevents accidentally committing large files

## Usage

### Automatic Validation

Once installed, pre-commit hooks run automatically when you commit:

```bash
git add .
git commit -m "Your commit message"
```

If any hooks fail, the commit will be blocked and you'll see error messages indicating what needs to be fixed.

### Manual Runs

You can manually run pre-commit on all files:

```bash
pre-commit run --all-files
```

Or run specific hooks:

```bash
pre-commit run black --all-files
pre-commit run mypy --all-files
```

### Updating Hooks

To update pre-commit hooks to their latest versions:

```bash
pre-commit autoupdate
```

This updates the hook versions in `.pre-commit-config.yaml`.

## Handling Hook Failures

When a hook fails:

1. **Formatting issues (Black, isort)**: These hooks often fix issues automatically. Review the changes and add them to your commit.

2. **Linting errors (Flake8, Ruff)**: Fix the reported issues in your code.

3. **Type errors (Mypy)**: Add or correct type annotations as needed.

4. **Security issues (Bandit)**: Review and address any security concerns.

### Bypassing Hooks (Emergency Only)

If you absolutely need to commit without running hooks:

```bash
git commit -m "Your message" --no-verify
```

**Warning**: Only use this in emergencies. It's better to fix the issues or temporarily disable specific hooks in `.pre-commit-config.yaml`.

## Configuration

The pre-commit configuration is stored in `.pre-commit-config.yaml`. Each hook can be customized with:

- `args`: Command-line arguments for the tool
- `exclude`: Regex patterns for files to skip
- `types`: File types to check (e.g., `python`)
- `stages`: Git stages when the hook should run

## Troubleshooting

### Common Issues

1. **Import order conflicts between isort and ruff**:
   - Solution: Use ruff's import sorting (it's the final check)
   - The project is configured to handle this automatically

2. **Mypy missing type stubs**:
   - Install type stubs: `pip install types-<package-name>`
   - Already included stubs: `types-PyYAML`, `types-requests`

3. **Black and flake8 line length conflicts**:
   - Both are configured to use 88-character line length
   - Black's formatting takes precedence

### Getting Help

If you encounter issues:

1. Check the error message for specific guidance
2. Run the failing hook manually for more details
3. Consult the tool's documentation (linked in `.pre-commit-config.yaml`)
4. Ask for help in project discussions

## Best Practices

1. **Run before pushing**: Always ensure your commits pass pre-commit checks before pushing
2. **Keep hooks updated**: Regularly run `pre-commit autoupdate`
3. **Don't ignore failures**: Fix issues rather than bypassing hooks
4. **Test locally**: Run `pre-commit run --all-files` before creating PRs

## Integration with CI/CD

Pre-commit hooks are also run in the CI pipeline to ensure all merged code meets quality standards. The same checks run locally will run in CI, so fixing issues locally saves time.
