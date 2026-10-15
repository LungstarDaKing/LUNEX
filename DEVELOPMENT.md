# LUNEX Development Guide

This document outlines the development practices, coding standards, and workflows for contributing to the LUNEX project.

## Development Philosophy

LUNEX follows these core development principles:
- **Reliability First**: Never sacrifice reliability for speed or features
- **Security Paramount**: Security considerations come before functionality
- **Architectural Integrity**: Maintain clean separation of concerns
- **Modularity**: Design for extension without modification
- **Transparency**: Code should be understandable and auditable
- **Testability**: All code should be easily testable
- **Documentation**: Self-documenting code with complementary docs

## Getting Started

### Prerequisites
- Git (for version control)
- Node.js >= 20 (for JavaScript/TypeScript development)
- Python >= 3.12 (for backend/utilities)
- Rust >= 1.70 (for performance-critical components)
- Docker (for containerized dependencies, optional)

### Setup
1. Fork and clone the repository
2. Install dependencies:
   ```bash
   # For Node.js components
   npm install
   
   # For Python components
   pip install -r requirements.txt
   
   # For Rust components
   cargo build
   ```
3. Set up environment variables (copy `.env.example` to `.env` and configure)
4. Run initial setup scripts

### Development Workflow
1. Create a feature branch from `main`: `git checkout -b feature/your-feature-name`
2. Make your changes following coding standards
3. Write or update tests for your changes
4. Run local tests to ensure nothing is broken
5. Commit with descriptive messages
6. Push to your fork and open a pull request
7. Address code review feedback
8. Maintainers will merge after approval

## Project Structure

```
lunex/
├── core/                 # Core system functionality
├── ai/                   # AI provider abstractions and integrations
├── agents/               # Specialized agent implementations
├── memory/               # Memory systems and storage
├── tools/                # Tool implementations and engine
├── security/             # Security components and utilities
├── automation/           # Workflow and automation systems
├── integrations/         # External service integrations
├── database/             # Data storage and ORM layers
├── api/                  # API interfaces and endpoints
├── frontend/             # User interface components
├── mobile/               # Mobile applications
├── desktop/              # Desktop applications
├── tests/                # Test suites
├── docs/                 # Documentation
├── scripts/              # Development and deployment scripts
└── config/               # Configuration files
```

## Coding Standards

### Language-Specific Standards

#### TypeScript/JavaScript
- Use TypeScript for all new frontend and Node.js code
- Follow Airbnb JavaScript/TypeScript style guide with project-specific exceptions
- Use ES6+ features consistently
- Prefer functional programming patterns where appropriate
- Use meaningful variable and function names
- Comment complex logic but avoid commenting obvious code
- Maximum line length: 100 characters
- Use 2-space indentation
- Export only what needs to be public
- Handle promises properly with async/await or .then()/catch()

#### Python
- Follow PEP 8 style guide
- Use type hints for all public functions and methods
- Use descriptive names for variables and functions
- Keep functions small and focused (under 50 lines ideal)
- Use docstrings for all public modules, classes, and functions
- Handle exceptions explicitly
- Use virtual environments for dependency management
- Maximum line length: 88 characters (Black default)
- Use 4-space indentation

#### Rust
- Follow Rustfmt default formatting
- Use Clippy for linting
- Write comprehensive documentation comments
- Use meaningful names for variables, functions, and types
- Handle errors properly with Result types
- Avoid unsafe code unless absolutely necessary
- Write unit tests alongside implementation code
- Maximum line length: 100 characters
- Use 4-space indentation

### General Principles
- DRY (Don't Repeat Yourself) - but prioritize clarity over premature abstraction
- KISS (Keep It Simple, Stupid) - prefer simple solutions
- YAGNI (You Ain't Gonna Need It) - don't implement features until needed
- SOLID principles for object-oriented design
- Composition over inheritance where applicable
- Immutable data structures where beneficial
- Early return patterns to reduce nesting
- Consistent error handling strategies
- Resource acquisition is initialization (RAII) where applicable

## Concurrency & Parallelism

### Asynchronous Patterns
- Use async/await patterns consistently
- Avoid blocking operations in async contexts
- Proper error propagation in asynchronous code
- Use Promise.all() for parallel independent operations
- Limit concurrent operations to prevent resource exhaustion
- Implement proper timeout handling

### Threading (where applicable)
- Use thread pools for CPU-intensive tasks
- Proper synchronization primitives (mutexes, channels, etc.)
- Avoid shared mutable state where possible
- Use message passing for inter-thread communication
- Proper thread lifecycle management
- Thread-safe data structures where needed

## Error Handling

### Principles
- Fail fast and fail safely
- Provide meaningful error messages to users
- Log detailed errors for debugging (without exposing secrets)
- Distinguish between user errors and system errors
- Implement graceful degradation where possible
- Never expose stack traces to end users in production
- Use structured error types/enums where applicable
- Provide error codes for programmatic error handling
- Implement retry logic with exponential backoff where appropriate
- Circuit breaker pattern for external service calls

### Error Reporting
- User-facing errors: Clear, actionable messages
- Developer-facing errors: Detailed context, timestamps, relevant state
- Security-relevant errors: Never leak sensitive information in error messages
- Structured logging with correlation IDs for request tracing

## Testing Strategy

### Unit Tests
- Test individual functions and methods
- Aim for high coverage (>80%) on core logic
- Mock external dependencies appropriately
- Test both positive and negative cases
- Test edge cases and boundary conditions
- Use descriptive test names that explain what is being tested
- Keep tests independent and isolated
- Run unit tests on every commit

### Integration Tests
- Test interactions between components
- Test API endpoints with realistic data
- Test database interactions
- Test external service integrations (with mocks where appropriate)
- Test workflows and multi-step processes
- Test error conditions and recovery scenarios
- Run integration tests on pull requests

### End-to-End Tests
- Test complete user workflows
- Test critical user journeys
- Test across different platforms (where applicable)
- Use headless browsers for UI testing
- Test performance under load
- Test security scenarios
- Run nightly or on release branches

### Performance Tests
- Benchmark critical paths
- Test memory usage and leak detection
- Test concurrent user handling
- Test startup and shutdown times
- Test battery/power consumption (where applicable)
- Establish performance baselines and monitor for regressions

### Security Tests
- Test authentication and authorization boundaries
- Test input validation and sanitization
- Test for common vulnerabilities (OWASP Top 10)
- Test secret handling and data protection
- Test audit logging effectiveness
- Run security scans in CI/CD

## Build System

### Dependency Management
- Use lockfiles for reproducible builds (package-lock.json, Pipfile.lock, Cargo.lock)
- Regular dependency updates with security scanning
- Internal dependency versioning (semantic versioning)
- Private npm/PyPI/Cargo registries for internal packages
- Vendoring only for exceptional cases with proper justification

### Build Process
- Consistent build commands across platforms
- Clear separation between development and production builds
- Environment-specific configuration handling
- Asset optimization and minification
- Code splitting for web applications
- Tree shaking to eliminate unused code
- Source map generation for debugging
- Deterministic builds for reproducibility

### Continuous Integration
- Run tests on every pull request
- Build artifacts for each commit
- Security scanning on every build
- Dependency vulnerability checking
- Code coverage reporting
- Performance benchmark tracking
- Deploy to staging environments for testing
- Automated rollback on failure detection

## Documentation Standards

### Code Documentation
- Public APIs: Comprehensive documentation with examples
- Complex algorithms: Step-by-step explanations
- Non-obvious business logic: Context and rationale
- Public classes and methods: Docstrings/comments
- Modules/files: Purpose and usage overview
- Avoid commenting what the code does; explain why it does it
- Keep documentation updated with code changes

### User Documentation
- Clear, step-by-step instructions
- Visual aids (screenshots, diagrams) where helpful
- Common troubleshooting scenarios
- FAQ sections for frequent questions
- Version-specific documentation
- Accessibility considerations (alt text, etc.)
- Examples and use cases

### API Documentation
- Interactive API documentation (Swagger/OpenAPI)
- Request/response examples
- Authentication requirements
- Error codes and messages
- Rate limiting information
- Versioning and deprecation policies
- SDK examples for different languages

### Contributor Documentation
- Onboarding guide for new contributors
- Development environment setup instructions
- Coding standards and style guides
- Pull request template and guidelines
- Release process documentation
- Licensing and contribution policies

## Release Process

### Versioning
- Follow Semantic Versioning (MAJOR.MINOR.PATCH)
- MAJOR: Incompatible API changes
- MINOR: Backward-compatible functionality additions
- PATCH: Backward-compatible bug fixes
- Pre-release identifiers for alpha/beta (e.g., 1.0.0-alpha.1)
- Build metadata for internal tracking (e.g., 1.0.0+20231015)

### Release Channels
- Development: Latest unstable build
- Stable: Thoroughly tested releases
- LTS: Long-term support versions (every 4th minor version)
- Canary: Experimental features (opt-in)

### Release Preparation
- Complete feature freeze
- Comprehensive testing (unit, integration, e2e, security)
- Performance benchmarking
- Documentation updates
- Changelog entry creation
- Release candidate tagging
- Community testing period
- Final release tagging and deployment

### Post-Release Activities
- Release announcement and notes
- Monitoring for post-release issues
- User feedback collection
- Patch release planning for critical bugs
- Deprecation warnings for upcoming removals
- Version-specific support timelines

## Tooling & Dependencies

### Recommended Editors
- Visual Studio Code with recommended extensions
- JetBrains IDEs (IntelliJ, PyCharm, WebStorm)
- Vim/Neovim with appropriate plugins
- Emacs with appropriate packages

### Essential Tools
- Git version control
- Docker for containerization
- Node.js/npm/yarn/pnpm
- Python/pip/poetry/venv
- Rust/Cargo
- Prettier/code formatters
- ESLint/Static analysis tools
- Jest/Vitest/Testing frameworks
- Postman/API testing
- Redis/MongoDB/PostgreSQL (for development)
- Wireshark/Network analysis (for debugging)
- JProfiler/Performance profiling (where applicable)

### Development Dependencies
- Testing frameworks (Jest, Vitest, PyTest, etc.)
- Linting tools (ESLint, pylint, Clippy, etc.)
- Formatters (Prettier, Black, Rustfmt, etc.)
- Type checkers (TypeScript, MyPy, etc.)
- Mocking libraries
- Code coverage tools
- Security scanning tools
- Performance profiling tools
- Database migration tools
- API documentation generators

## Communication & Collaboration

### Issue Tracking
- Use GitHub Issues for bug reports and feature requests
- Clear, descriptive issue titles
- Steps to reproduce for bug reports
- Expected vs actual behavior
- Environment information (OS, versions, etc.)
- Labeling system for categorization
- Milestone tracking for releases
- Assigning and ownership tracking

### Code Review
- Pull request template with required information
- Checklist for reviewers
- Constructive, actionable feedback
- Focus on correctness, clarity, and maintainability
- Check for adherence to coding standards
- Verify tests are adequate and passing
- Check for security implications
- Verify documentation is updated
- Require at least one approval from maintainer
- Squash merges for clean history

### Continuous Communication
- Regular standup meetings (async or sync)
- Progress updates in issues/pull requests
- Design discussions for major features
- Architecture review for systemic changes
- Knowledge sharing sessions
- Retrospectives for process improvement
- Mentoring for new contributors

## Appendix: Useful Commands

### Git
```bash
# Create feature branch
git checkout -b feature/amazing-feature

# Standard commit message format
git commit -m "feat: add amazing feature"
git commit -m "fix: resolve issue with login"
git commit -m "docs: update API documentation"
git commit -m "refactor: simplify authentication flow"
git commit -m "test: add unit tests for parser"
git commit -m "chore: update dependencies"

# Amend last commit
git commit --amend

# Interactive rebase for cleanup
git rebase -i HEAD~n

# Stash work-in-progress
git stash
git stash pop

# Clean branches
git branch -d feature/old-feature
```

### Testing
```bash
# Run all tests
npm test

# Run unit tests only
npm run test:unit

# Run integration tests
npm run test:integration

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm test -- path/to/test.file.ts

# Run tests in watch mode
npm run test:watch
```

### Linting & Formatting
```bash
# Check linting errors
npm run lint

# Fix linting errors (auto-fixable)
npm run lint:fix

# Format all files
npm run format

# Check formatting
npm run format:check
```

### Database
```bash
# Run migrations
npm run db:migrate

# Rollback migrations
npm run db:rollback

# Reset database
npm run db:reset

# Seed database
npm run db:seed
```