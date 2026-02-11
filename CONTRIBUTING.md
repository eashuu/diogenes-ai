# Contributing to Diogenes

First off, thank you for considering contributing to Diogenes! It's people like you that make Diogenes such a great tool for the research community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)

## Code of Conduct

This project and everyone participating in it is governed by the [Diogenes Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** (screenshots, code snippets, logs)
- **Describe the behavior you observed** and what you expected
- **Include environment details** (OS, Python version, Node version, etc.)

Use the bug report template when creating an issue.

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful**
- **List any alternatives** you've considered

### Your First Code Contribution

Unsure where to begin? You can start by looking through `good-first-issue` and `help-wanted` issues:

- **Good first issues** - issues which should only require a few lines of code
- **Help wanted issues** - issues which might be more involved

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the style guidelines
6. Issue the pull request!

## Development Setup

### Backend Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/diogenes.git
cd diogenes

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (with dev dependencies)
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If available

# Install pre-commit hooks (recommended)
pre-commit install

# Run tests
pytest tests/ -v
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Run linter
npm run lint

# Run type checker
npm run type-check
```

### Docker Setup (Optional)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make your changes**
   - Write clear, concise commit messages
   - Follow the coding standards below
   - Add tests for new functionality

3. **Test your changes**
   ```bash
   # Backend
   pytest tests/ -v
   
   # Frontend
   npm test
   ```

4. **Update documentation**
   - Update README.md if needed
   - Update API documentation for API changes
   - Add docstrings to new functions/classes

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```
   
   Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
   - `feat:` A new feature
   - `fix:` A bug fix
   - `docs:` Documentation changes
   - `style:` Code style changes (formatting, etc.)
   - `refactor:` Code refactoring
   - `test:` Adding or updating tests
   - `chore:` Maintenance tasks

6. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```

7. **Open a Pull Request**
   - Use the PR template
   - Link related issues
   - Request review from maintainers

## Coding Standards

### Python (Backend)

We follow **PEP 8** with some modifications:

```python
# Good practices:
- Use type hints for function signatures
- Write docstrings for all public functions/classes
- Keep functions small and focused
- Use descriptive variable names
- Maximum line length: 100 characters

# Example:
def extract_citations(
    text: str,
    source_urls: list[str]
) -> list[Citation]:
    """
    Extract citations from text and match to source URLs.
    
    Args:
        text: The text to extract citations from
        source_urls: List of source URLs to match against
        
    Returns:
        List of Citation objects with matched sources
        
    Raises:
        ValueError: If text is empty
    """
    if not text:
        raise ValueError("Text cannot be empty")
    ...
```

**Tools:**
- **Black** for code formatting: `black src/ tests/`
- **isort** for import sorting: `isort src/ tests/`
- **flake8** for linting: `flake8 src/ tests/`
- **mypy** for type checking: `mypy src/`

### TypeScript/JavaScript (Frontend)

We follow standard TypeScript best practices:

```typescript
// Good practices:
- Use TypeScript for all new code
- Define interfaces for all data structures
- Use functional components with hooks
- Keep components small and focused
- Use meaningful variable names

// Example:
interface ResearchRequest {
  query: string;
  mode: 'quick' | 'balanced' | 'deep';
  profile?: string;
}

export async function research(
  request: ResearchRequest
): Promise<ResearchResponse> {
  // Implementation
}
```

**Tools:**
- **Prettier** for formatting: `npm run format`
- **ESLint** for linting: `npm run lint`
- **TypeScript** compiler: `npm run type-check`

### CSS/Styling

- Use **Tailwind CSS** utility classes
- Follow the existing design system
- Ensure responsive design (mobile-first)
- Test on multiple screen sizes
- Maintain accessibility (ARIA labels, keyboard navigation)

## Testing Guidelines

### Backend Tests

```python
# tests/test_feature.py
import pytest
from src.feature import my_function

def test_my_function_with_valid_input():
    """Test that my_function works with valid input."""
    result = my_function("valid input")
    assert result == "expected output"

def test_my_function_with_invalid_input():
    """Test that my_function raises error with invalid input."""
    with pytest.raises(ValueError):
        my_function("invalid input")

@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality."""
    result = await async_function()
    assert result is not None
```

**Testing Requirements:**
- Aim for >80% code coverage
- Test happy paths and edge cases
- Test error handling
- Use descriptive test names
- Use fixtures for common setup

### Frontend Tests

```typescript
// Example test structure (if/when implemented)
import { render, screen } from '@testing-library/react';
import { ResearchComponent } from './ResearchComponent';

describe('ResearchComponent', () => {
  it('renders query input', () => {
    render(<ResearchComponent />);
    expect(screen.getByPlaceholderText(/ask/i)).toBeInTheDocument();
  });

  it('handles query submission', async () => {
    // Test implementation
  });
});
```

### Integration Tests

```bash
# Run integration tests
python scripts/test_integration.py
```

## Documentation

### Code Documentation

- **Python**: Use Google-style docstrings
- **TypeScript**: Use JSDoc comments
- Document all public APIs
- Include examples in complex functions
- Keep docs up-to-date with code changes

### Project Documentation

When contributing to documentation:

- **README.md**: Project overview and quick start
- **[CODEBASE_STRUCTURE.md](CODEBASE_STRUCTURE.md)**: Detailed structure guide
- **[NAVIGATION.md](NAVIGATION.md)**: Quick navigation reference
- **[docs/](docs/)**: Comprehensive documentation
  - **[docs/README.md](docs/README.md)**: Documentation index
  - **docs/architecture/**: System design and architecture
  - **docs/guides/**: User guides and tutorials
  - **docs/backend/**: Backend development documentation
  - **docs/deployment/**: Deployment and setup guides
  - **docs/troubleshooting/**: Problem-solving guides
  - **docs/planning/**: Project planning documents

**When adding new documentation:**

1. Determine the appropriate category
2. Place file in the relevant `docs/` subdirectory
3. Update [docs/README.md](docs/README.md) index
4. Update [NAVIGATION.md](NAVIGATION.md) for commonly referenced docs
5. Link from main README.md if user-facing

See [docs/REORGANIZATION_SUMMARY.md](docs/REORGANIZATION_SUMMARY.md) for documentation organization guidelines.

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Examples:**
```
feat(api): add streaming endpoint for research

Implements Server-Sent Events (SSE) streaming for real-time
research progress updates.

Closes #123
```

```
fix(frontend): resolve citation rendering bug

Citations were not properly linking to sources in deep mode.
Fixed by updating the citation parsing logic.

Fixes #456
```

## Questions?

Feel free to ask questions by:
- Opening a [Discussion](https://github.com/yourusername/diogenes/discussions)
- Reaching out on our Discord (link coming soon)
- Commenting on relevant issues

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project website (coming soon)

Thank you for contributing to Diogenes! 🔍✨
