# Contributing to Waiting The Longest™

Thank you for your interest in contributing! Every contribution helps shelter animals find homes faster.

## 🐾 Our Mission

**Because Every Day Matters** - We help shelter animals who have waited the longest find forever homes.

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+ (optional, for frontend tooling)
- Git

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/ianmerrill10/WaitingTheLongest.git
cd WaitingTheLongest

# Create virtual environment
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the development server
cd ..
python scripts/run.py
```

### Running Tests

```bash
cd backend
pytest -v
```

## 📝 How to Contribute

### Reporting Bugs

1. Check existing issues first
2. Create a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable

### Suggesting Features

1. Open a GitHub Issue with the `enhancement` label
2. Describe the feature and its benefits
3. Include mockups or examples if possible

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest -v`
5. Run linting: `black . && flake8`
6. Commit with clear messages: `git commit -m "Add amazing feature"`
7. Push to your fork: `git push origin feature/amazing-feature`
8. Open a Pull Request

## 🎨 Code Style

### Python
- Use Black for formatting (line length: 100)
- Use isort for import sorting
- Follow PEP 8 guidelines
- Add docstrings to all functions

### JavaScript
- Use consistent indentation (2 spaces)
- Add JSDoc comments for functions
- Prefer const over let

### Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code restructuring
- `test:` Adding tests
- `chore:` Maintenance

## 🧪 Testing Guidelines

- Write tests for all new features
- Maintain >80% code coverage
- Use descriptive test names
- Include edge cases

## 📚 Documentation

- Update README.md for major changes
- Add inline comments for complex logic
- Update API docs for endpoint changes
- Document environment variables

## 🤝 Code Review Process

1. All PRs require at least one review
2. Address all review comments
3. Keep PRs focused and small
4. Squash commits before merge

## 🙏 Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for helping shelter animals find homes!** 🐕🐈
