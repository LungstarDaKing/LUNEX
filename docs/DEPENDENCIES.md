# Dependency Justifications

## Core Dependencies

- **fastapi>=0.104.0**: Modern, fast web framework for building APIs with automatic OpenAPI documentation
- **uvicorn[standard]>=0.27.0**: ASGI server for running FastAPI applications
- **pydantic>=2.0.0**: Data validation and settings management using Python type annotations
- **pydantic-settings>=2.0.0**: Extended pydantic for managing environment variables and configuration
- **sqlalchemy>=2.0.0**: SQL toolkit and ORM for database operations
- **alembic>=1.13.0**: Database migration tool for SQLAlchemy
- **httpx>=0.25.0**: Modern HTTP client for Python 3.x, used for Ollama provider
- **anyio>=4.0.0**: Compatibility layer for asyncio and trio, used for structured concurrency
- **openai>=1.0.0**: Official OpenAI API client
- **anthropic>=0.3.0**: Official Anthropic API client

## Development Dependencies

- **pytest>=7.0.0**: Testing framework
- **pytest-asyncio>=0.23.0**: Support for async/await tests
- **ruff>=0.4.0**: Fast Python linter and formatter
- **mypy>=1.8.0**: Static type checker for Python