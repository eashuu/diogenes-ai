# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-02-01

### Added
- Initial public release
- Multi-agent research orchestration
- Three research modes (Quick, Balanced, Deep)
- Six research profiles (General, Academic, Technical, News, Medical, Legal)
- Real-time streaming with Server-Sent Events (SSE)
- Web search via SearXNG (privacy-focused)
- Web crawling with Playwright
- Claim verification and reliability scoring
- Inline citation system
- Session history with local storage
- Beautiful React frontend with three themes
- FastAPI backend with comprehensive API documentation
- Comprehensive configuration system
- Docker support
- Full-featured CLI

### Backend
- FastAPI REST API with SSE streaming
- LangGraph-based multi-agent orchestration
- Ollama integration for local LLMs
- SearXNG integration for web search
- Playwright-based web crawling
- SQLite caching and session storage
- Comprehensive error handling and logging
- Configurable via YAML and environment variables

### Frontend
- React 19 with TypeScript
- Vite for fast development and building
- Tailwind CSS for styling
- Framer Motion for animations
- React Markdown for answer rendering
- Real-time streaming updates
- Session management
- Multiple themes (Light, Dark, Diogenes)
- Responsive mobile design

### Documentation
- Comprehensive README
- Installation guide
- API specification
- System design documentation
- Contributing guidelines
- Code of conduct
- Security policy
- Deployment guide

### CI/CD
- GitHub Actions for automated testing
- Security scanning workflows
- Code quality checks

---

## [Unreleased]

### Planned for v2.1
- [ ] Export research to PDF/Markdown
- [ ] User authentication and accounts
- [ ] Backend session persistence
- [ ] Advanced analytics dashboard
- [ ] API rate limiting
- [ ] Webhook support

### Planned for v2.2
- [ ] Real-time collaboration
- [ ] Custom research profiles
- [ ] Plugin system for extensions
- [ ] Multi-language support
- [ ] Browser extensions

### Planned for v3.0
- [ ] Knowledge graph integration
- [ ] Long-term memory and learning
- [ ] Advanced visualization tools
- [ ] Mobile apps (iOS/Android)
- [ ] Desktop applications

---

## Guidelines for Future Releases

### Version Numbers
- **MAJOR** version when you make incompatible API changes
- **MINOR** version when you add functionality in a backwards-compatible manner
- **PATCH** version when you make backwards-compatible bug fixes

### Release Process
1. Update version in all files (package.json, __init__.py, etc.)
2. Update CHANGELOG.md with release notes
3. Create git tag with version
4. Push changes and tag to GitHub
5. Create GitHub Release with changelog
6. Publish packages (if applicable)

---

[2.0.0]: https://github.com/yourusername/diogenes/releases/tag/v2.0.0
