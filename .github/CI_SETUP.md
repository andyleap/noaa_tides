# CI/CD Setup Documentation

This document explains the continuous integration and development workflow setup for the NOAA Tides integration.

## 🔄 GitHub Actions Workflows

### 1. **Validate Workflow** (`.github/workflows/validate.yaml`)

Runs on every push, pull request, and daily:

#### Hassfest Job
- Validates Home Assistant integration structure
- Checks manifest.json validity
- Ensures all required files are present

#### HACS Job
- Validates HACS compatibility
- Checks repository structure
- Verifies integration category

#### Tests Job
- Runs on Python 3.11 and 3.12
- **Ruff**: Fast Python linter (replaces flake8, isort, etc.)
- **Black**: Code formatter (120 char line length)
- **MyPy**: Static type checking
- **Pytest**: Unit tests with coverage reporting

### 2. **Release Workflow** (`.github/workflows/release.yaml`)

Triggers when a new release is published:
- Validates version tag matches manifest.json
- Creates release notes
- Uploads changelog

## 🛠️ Development Tools

### Pre-commit Hooks (`.pre-commit-config.yaml`)

Automatically runs before each commit:
- **Ruff**: Auto-fix common issues
- **Black**: Format code
- **Trailing whitespace**: Remove
- **End-of-file**: Ensure newline
- **YAML/JSON validation**
- **Codespell**: Catch typos
- **MyPy**: Type checking

**Setup:**
```bash
pip install pre-commit
pre-commit install
```

### Configuration Files

#### `pyproject.toml`
Central configuration for:
- Black (line length: 120)
- Ruff (linting rules)
- MyPy (type checking)
- Pytest (test discovery)
- Coverage (reporting)

#### `requirements_test.txt`
Development dependencies:
- Testing: pytest, pytest-asyncio, pytest-cov
- Linting: ruff, black, mypy
- Home Assistant testing helpers
- Runtime dependencies: scipy, aiohttp

## 📊 Test Structure

```
tests/
├── __init__.py           # Test package
├── conftest.py          # Pytest fixtures
├── test_init.py         # Integration setup tests
└── test_tide_math.py    # Math function tests
```

### Running Tests Locally

```bash
# Install dependencies
pip install -r requirements_test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components/noaa_tides

# Run specific test
pytest tests/test_tide_math.py -v
```

## 🔍 Code Quality Checks

### Manual Validation
```bash
# Format code
black custom_components/noaa_tides/

# Lint
ruff check custom_components/noaa_tides/

# Fix auto-fixable issues
ruff check --fix custom_components/noaa_tides/

# Type check
mypy custom_components/noaa_tides/
```

### Pre-commit (Recommended)
```bash
# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

## 🤖 Dependabot

Auto-updates dependencies weekly:
- GitHub Actions versions
- Python packages in requirements

Review and merge Dependabot PRs to keep dependencies current.

## 📦 Release Process

1. **Update version** in `manifest.json`
2. **Update** `CHANGELOG.md` with changes
3. **Commit and push** to main
4. **Create GitHub release** with tag `vX.Y.Z`
5. **GitHub Actions** automatically validates and publishes

### Version Tag Format
- **Major**: `v1.0.0` - Breaking changes
- **Minor**: `v1.1.0` - New features
- **Patch**: `v1.0.1` - Bug fixes

## 🐛 Issue Templates

Located in `.github/ISSUE_TEMPLATE/`:
- **bug_report.yml**: Structured bug reports
- **feature_request.yml**: Feature suggestions

Users fill out forms with all needed information.

## 🎯 Badge Integration

Add to your README.md:

```markdown
[![Validate](https://github.com/andyleap/noaatides/workflows/Validate/badge.svg)](https://github.com/andyleap/noaatides/actions)
[![HACS](https://img.shields.io/badge/HACS-Default-orange.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/release/andyleap/noaatides.svg)](https://github.com/andyleap/noaatides/releases)
```

## 📝 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- Development setup instructions
- Code style guidelines
- Testing requirements
- Pull request process

## ✅ CI/CD Checklist

Before first release:
- [x] Workflows created
- [x] Pre-commit configured
- [x] Tests written
- [x] pyproject.toml configured
- [ ] Run `pre-commit run --all-files` successfully
- [ ] Push to GitHub and verify workflows run
- [ ] Add badges to README
- [ ] Test release process with tag

## 🔧 Troubleshooting

### Workflow Failures

**Hassfest fails:**
- Check manifest.json syntax
- Ensure all required files exist
- Verify version format

**HACS fails:**
- Check hacs.json structure
- Ensure integration in correct directory
- Verify repository structure

**Tests fail:**
- Run locally: `pytest -v`
- Check imports and dependencies
- Review test logs in GitHub Actions

**Linting fails:**
- Run `black custom_components/noaa_tides/`
- Run `ruff check --fix custom_components/noaa_tides/`
- Commit formatting changes

### Local Setup Issues

**Pre-commit not running:**
```bash
pre-commit install
pre-commit autoupdate
```

**Import errors in tests:**
```bash
pip install -r requirements_test.txt
```

**Python version mismatch:**
Use Python 3.11 or 3.12 (same as HA requirements)

## 📚 Resources

- [Home Assistant Integration Quality Scale](https://developers.home-assistant.io/docs/integration_quality_scale_index/)
- [HACS Documentation](https://hacs.xyz/docs/publish/integration)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pre-commit Documentation](https://pre-commit.com/)

## 🎉 Next Steps

1. **Push to GitHub**: Let workflows run
2. **Fix any failures**: Address CI issues
3. **Add badges**: Make README pretty
4. **Create first release**: Tag v1.0.0
5. **Submit to HACS**: Follow HACS submission process

Your integration now has enterprise-grade CI/CD! 🚀
