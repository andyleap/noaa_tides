# Contributing to NOAA Tides

Thank you for your interest in contributing to the NOAA Tides integration!

## Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/andyleap/noaatides.git
cd noaatides
```

### 2. Set up a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install development dependencies
```bash
pip install -r requirements_test.txt
```

### 4. Install pre-commit hooks
```bash
pre-commit install
```

## Code Quality

### Running tests locally
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components/noaa_tides --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Code formatting and linting
```bash
# Format code
black custom_components/noaa_tides/

# Lint code
ruff check custom_components/noaa_tides/

# Type checking
mypy custom_components/noaa_tides/
```

### Pre-commit checks
Pre-commit will automatically run on every commit. To run manually:
```bash
pre-commit run --all-files
```

## Testing with Home Assistant

### Development environment
1. Copy the integration to your Home Assistant config:
```bash
cp -r custom_components/noaa_tides /path/to/homeassistant/custom_components/
```

2. Restart Home Assistant

3. Add the integration via UI: Settings → Devices & Services → Add Integration

### Remote testing (if you have a remote HA instance)
```bash
# Example using the provided homeassistant.local
scp -r custom_components/noaa_tides root@homeassistant.local:/config/custom_components/
ssh root@homeassistant.local "ha core restart"
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Update CHANGELOG.md
6. Submit a pull request

### PR Checklist
- [ ] Code follows the project's style guidelines
- [ ] Tests added for new functionality
- [ ] All tests pass
- [ ] CHANGELOG.md updated
- [ ] Documentation updated if needed
- [ ] No breaking changes (or clearly documented)

## GitHub Actions

All PRs will automatically run:
- **Hassfest**: Home Assistant integration validation
- **HACS**: HACS compatibility check
- **Tests**: Python tests across multiple versions
- **Linting**: Code quality checks with ruff and black
- **Type checking**: MyPy static type analysis

Make sure all checks pass before requesting review.

## Release Process

Releases are managed by maintainers:

1. Update version in `manifest.json`
2. Update `CHANGELOG.md` with release date
3. Create a new release on GitHub with tag `vX.Y.Z`
4. GitHub Actions will automatically validate and publish

## Code Style

- **Line length**: 120 characters (black and ruff configured)
- **Python version**: 3.11+ (must support HA 2024.1+)
- **Imports**: Organized by isort/ruff
- **Type hints**: Required for all functions
- **Docstrings**: Required for all public functions
- **Logging**: Use module logger, appropriate levels

## Questions?

Open an issue for:
- Bug reports
- Feature requests
- Questions about contributing

Thank you for contributing! 🎉
