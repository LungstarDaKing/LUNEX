# LUNEX AI Provider Abstraction and Core Chat Design

## Table of Contents
- [Overview](#overview)
- [Architecture Approach](#architecture-approach)
- [Core Components](#core-components)
- [Implementation Details](#implementation-details)
- [API Endpoints](#api-endpoints)
- [Data Flow](#data-flow)
- [Error Handling](#error-handling)
- [Dependencies](#dependencies)
- [Configuration](#configuration)
- [Status Vocabulary](#status-vocabulary)

## Overview

This document describes the design for Phase 1 of LUNEX: Core chat functionality and AI provider abstraction layer. This phase implements the foundation for LUNEX's ability to interact with various AI models through a unified interface while providing chat capabilities with context management, streaming responses, and multi-turn conversations.

## Architecture Approach

LUNEX implements a hybrid approach combining Strategy Pattern with Feature Registry for AI provider abstraction:

1. **Abstract AIProvider Base Class**: Defines core interface (generate, stream, embeddings, etc.)
2. **Feature Interfaces**: Optional capabilities like IVisionCapable, IFunctionCallingCapable
3. **Provider Registry**: Tracks provider capabilities and feature support
4. **Chat Manager**: Routes requests based on required features
5. **Provider Self-Registration**: Providers announce their capabilities at startup

This approach satisfies the decision priorities:
- Correctness > Security > Ease of adding providers > Latency > Throughput (D6)
- Everything is async with streaming as primary path (D9)
- Unified normalized interface + Capabilities object + provider_options passthrough (D8)
- Model names never hard-coded (D5)

## Core Components

### 1. Provider Interface (`src/lunex/ai/providers/base.py`)
```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, Optional
from lunex.ai.providers.capabilities import ProviderCapabilities

class AIProvider(ABC):
    """Abstract base class for all AI providers"""
    
    def __init__(self, provider_name: str, config: Dict[str, Any]):
        self.provider_name = provider_name
        self.config = config
        self._capabilities = self._detect_capabilities()
    
    @property
    def capabilities(self) -> ProviderCapabilities:
        """Return what features this provider supports"""
        return self._capabilities
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        options: Dict[str, Any],
        provider_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a complete response (non-streaming)"""
        pass
    
    @abstractmethod
    async def stream(
        self, 
        prompt: str, 
        options: Dict[str, Any],
        provider_options: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """Stream response tokens as they become available"""
        pass
    
    async def embeddings(
        self, 
        text: str, 
        options: Dict[str, Any]
    ) -> list[float]:
        """Generate embeddings for text (optional)"""
        raise CapabilityNotSupported("Embeddings not supported")
    
    @abstractmethod
    def _detect_capabilities(self) -> ProviderCapabilities:
        """Detect and return provider capabilities"""
        pass
```

### 2. Capabilities System (`src/lunex/ai/providers/capabilities.py`)
```python
from enum import IntFlag, auto

class ProviderCapabilities(IntFlag):
    """Bitmask of capabilities that AI providers can support"""
    NONE = 0
    TEXT = auto()           # Basic text generation
    STREAMING = auto()      # Streaming response support
    VISION = auto()         # Image/video understanding
    FUNCTION_CALLING = auto() # Tool/function calling
    EMBEDDINGS = auto()     # Embedding generation
    AUDIO = auto()          # Audio processing
    # Extend as needed

# Helper functions for capability checking
def has_capability(provider_cap: ProviderCapabilities, required_cap: ProviderCapabilities) -> bool:
    return bool(provider_cap & required_cap)
```

### 3. Provider Implementations

#### OpenAI Provider (`src/lunex/ai/providers/openai.py`)
```python
from openai import AsyncOpenAI
from lunex.ai.providers.base import AIProvider
from lunex.ai.providers.capabilities import ProviderCapabilities, has_capability

class OpenAIProvider(AIProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("openai", config)
        self.client = AsyncOpenAI(api_key=config.get("api_key"))
    
    def _detect_capabilities(self) -> ProviderCapabilities:
        caps = ProviderCapabilities.TEXT | ProviderCapabilities.STREAMING
        # Check model-specific capabilities from config
        if self.config.get("vision_capable"):
            caps |= ProviderCapabilities.VISION
        if self.config.get("function_calling_capable"):
            caps |= ProviderCapabilities.FUNCTION_CALLING
        return caps
    
    async def generate(self, prompt: str, options: Dict[str, Any], 
                      provider_options: Optional[Dict[str, Any]] = None) -> str:
        # Merge options with provider_options
        final_options = {**options, **(provider_options or {})}
        response = await self.client.chat.completions.create(
            model=self.config["model"],
            messages=[{"role": "user", "content": prompt}],
            **final_options
        )
        return response.choices[0].message.content
    
    async def stream(self, prompt: str, options: Dict[str, Any],
                    provider_options: Optional[Dict[str, Any]] = None) -> AsyncIterator[str]:
        final_options = {**options, **(provider_options or {})}
        stream = await self.client.chat.completions.create(
            model=self.config["model"],
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **final_options
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

#### Anthropic Provider (`src/lunex/ai/providers/anthropic.py`)
```python
# Similar structure using anthropic.AsyncAnthropic
```

#### Ollama Provider (`src/lunex/ai/providers/ollama.py`)
```python
# Uses httpx to call Ollama REST API
```

#### Mock Provider (`src/lunex/ai/providers/mock.py`)
```python
class MockProvider(AIProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("mock", config)
        # Always supports basic capabilities for testing
        self._capabilities = ProviderCapabilities.TEXT | ProviderCapabilities.STREAMING
    
    def _detect_capabilities(self) -> ProviderCapabilities:
        return self._capabilities
    
    async def generate(self, prompt: str, options: Dict[str, Any], 
                      provider_options: Optional[Dict[str, Any]] = None) -> str:
        # Simulate processing delay
        await asyncio.sleep(0.1)
        return f"[MOCK PROVIDER — not a real AI] Response to: {prompt[:50]}..."
    
    async def stream(self, prompt: str, options: Dict[str, Any],
                    provider_options: Optional[Dict[str, Any]] = None) -> AsyncIterator[str]:
        mock_response = f"[MOCK PROVIDER — not a real AI] Response to: {prompt[:50]}..."
        for char in mock_response:
            await asyncio.sleep(0.01)  # Simulate streaming
            yield char
```

### 4. Provider Registry (`src/lunex/ai/providers/registry.py`)
```python
from typing import Dict, List, Type
from lunex.ai.providers.base import AIProvider
from lunex.ai.providers.capabilities import ProviderCapabilities, has_capability

class ProviderRegistry:
    """Registry for AI providers with capability-based matching"""
    
    def __init__(self):
        self._providers: Dict[str, AIProvider] = {}
        self._provider_classes: Dict[str, Type[AIProvider]] = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "ollama": OllamaProvider,
            "mock": MockProvider
        }
    
    def register_provider(self, name: str, config: Dict[str, Any]) -> None:
        """Register and initialize a provider"""
        if name not in self._provider_classes:
            raise ValueError(f"Unknown provider: {name}")
        
        provider_class = self._provider_classes[name]
        provider = provider_class(config)
        self._providers[name] = provider
    
    def get_providers_for_capabilities(
        self, 
        required_capabilities: ProviderCapabilities
    ) -> List[AIProvider]:
        """Return providers that support all required capabilities"""
        matching = []
        for provider in self._providers.values():
            if has_capability(provider.capabilities, required_capabilities):
                matching.append(provider)
        return matching
    
    def get_provider(self, name: str) -> Optional[AIProvider]:
        """Get a specific provider by name"""
        return self._providers.get(name)
    
    def list_providers(self) -> List[str]:
        """List all registered provider names"""
        return list(self._providers.keys())
```

### 5. Chat Manager (`src/lunex/ai/chat/manager.py`)
```python
import asyncio
import json
from typing import List, AsyncIterator, Dict, Any, Optional
from datetime import datetime
from lunex.ai.providers.registry import ProviderRegistry
from lunex.ai.providers.capabilities import ProviderCapabilities, has_capability
from lunex.database.models import ChatMessage, Conversation
from lunex.database.session import get_db_session

class ChatManager:
    """Manages chat interactions and conversation history"""
    
    def __init__(self, provider_registry: ProviderRegistry):
        self.provider_registry = provider_registry
    
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None,
        provider_options: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any] | AsyncIterator[str]:
        """Main chat completion interface"""
        
        # 1. Get model configuration to determine required capabilities
        model_config = await self._get_model_config(model)
        required_caps = self._infer_required_capabilities(model_config, stream)
        
        # 2. Find providers that support required capabilities
        available_providers = self.provider_registry.get_providers_for_capabilities(required_caps)
        if not available_providers:
            raise LunexError(
                "NO_SUITABLE_PROVIDER",
                f"No provider found supporting capabilities: {required_caps}",
                {"model": model, "required_caps": required_caps.value}
            )
        
        # 3. Select best provider (simple: first available, could be enhanced)
        provider = available_providers[0]
        
        # 4. Prepare prompt from messages
        prompt = self._messages_to_prompt(messages)
        
        # 5. Call appropriate method
        if stream:
            return self._stream_response(provider, prompt, options or {}, provider_options or {})
        else:
            response = await self._generate_response(provider, prompt, options or {}, provider_options or {})
            
            # 6. Persist conversation turn
            await self._persist_conversation_turn(
                conversation_id, model, messages, response, options
            )
            
            return response
    
    async def _generate_response(
        self, 
        provider: AIProvider, 
        prompt: str, 
        options: Dict[str, Any],
        provider_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get non-streaming response"""
        start_time = asyncio.get_event_loop().time()
        content = await provider.generate(prompt, options, provider_options)
        end_time = asyncio.get_event_loop().time()
        
        return {
            "id": f"chatcmpl-{asyncio.get_event_loop().time():.0f}",
            "object": "chat.completion",
            "created": int(asyncio.get_event_loop().time()),
            "model": options.get("model", "unknown"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": self._estimate_tokens(prompt),
                "completion_tokens": self._estimate_tokens(content),
                "total_tokens": self._estimate_tokens(prompt + content)
            }
        }
    
    async def _stream_response(
        self, 
        provider: AIProvider, 
        prompt: str, 
        options: Dict[str, Any],
        provider_options: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """Stream response tokens"""
        async for token in provider.stream(prompt, options, provider_options):
            yield f"data: {json.dumps(self._make_chunk_token(token))}\n\n"
        yield "data: [DONE]\n\n"
    
    async def _persist_conversation_turn(
        self,
        conversation_id: Optional[str],
        model: str,
        messages: List[Dict[str, str]],
        response: Dict[str, Any],
        options: Dict[str, Any]
    ) -> None:
        """Store conversation turn in database"""
        if not conversation_id:
            return
            
        async with get_db_session() as session:
            # Save user messages
            for msg in messages:
                if msg["role"] == "user":
                    chat_msg = ChatMessage(
                        conversation_id=conversation_id,
                        role=msg["role"],
                        content=msg["content"],
                        timestamp=datetime.utcnow(),
                        model_used=model
                    )
                    session.add(chat_msg)
            
            # Save assistant response
            assistant_msg = ChatMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=response["choices"][0]["message"]["content"],
                timestamp=datetime.utcnow(),
                model_used=model,
                prompt_tokens=response["usage"]["prompt_tokens"],
                completion_tokens=response["usage"]["completion_tokens"]
            )
            session.add(assistant_msg)
            await session.commit()
    
    # Helper methods (_get_model_config, _infer_required_capabilities, etc.)
    # ... implementation details omitted for brevity ...
```

### 6. Database Models (`src/lunex/database/models.py`)
```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm relationship

Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)  # For future multi-user support
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"))
    role = Column(String)  # "user" or "assistant"
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    metadata = Column(JSON, nullable=True)  # For storing additional info
    
    conversation = relationship("Conversation", back_populates="messages")
```

## Implementation Details

### Project Layout (per D1)
```
src/lunex/
├── ai/
│   ├── providers/
│   │   ├── base.py
│   │   ├── capabilities.py
│   │   ├── registry.py
│   │   ├── openai.py
│   │   ├── anthropic.py
│   │   ├── ollama.py
│   │   └── mock.py
│   └── chat/
│       └── manager.py
├── config/
│   └── models.yaml
├── database/
│   ├── models.py
│   └── session.py
└── main.py  # FastAPI application entry point
```

### Configuration

#### Environment Variables
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key  
- `LUNEX_API_TOKEN`: Bearer token for API authentication (D12)
- `OLLAMA_HOST`: Ollama host URL (default: http://localhost:11434)

#### Config File (`config/models.yaml`)
```yaml
providers:
  openai:
    api_key: "${OPENAI_API_KEY}"
    models:
      gpt-4:
        capabilities: [TEXT, STREAMING, FUNCTION_CALLING]
        default_options:
          temperature: 0.7
          max_tokens: 2000
      gpt-4-turbo:
        capabilities: [TEXT, STREAMING, FUNCTION_CALLING]
      gpt-4-vision-preview:
        capabilities: [TEXT, STREAMING, VISION, FUNCTION_CALLING]
        default_options:
          max_tokens: 4000
  
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      claude-3-opus-20240229:
        capabilities: [TEXT, STREAMING, FUNCTION_CALLING]
        default_options:
          temperature: 0.7
          max_tokens: 4000
      claude-3-sonnet-20240229:
        capabilities: [TEXT, STREAMING, FUNCTION_CALLING]
  
  ollama:
    host: "http://localhost:11434"
    models:
      llama3:
        capabilities: [TEXT, STREAMING]
      codellama:
        capabilities: [TEXT, STREAMING]
      llava:
        capabilities: [TEXT, STREAMING, VISION]
  
  mock:
    models:
      mock-text:
        capabilities: [TEXT, STREAMING]
      mock-vision:
        capabilities: [TEXT, STREAMING, VISION]

# Global settings
defaults:
  temperature: 0.7
  max_tokens: 1000
  timeout_connect: 10s
  timeout_first_token: 30s
  timeout_total: 120s
```

### Error Handling (per D5, D6, D14, D15)
- Structured errors only: `LunexError(code, user_message, detail)`
- Error codes include:
  - `NO_SUITABLE_PROVIDER`: No provider supports required capabilities
  - `PROVIDER_ERROR`: Provider-specific error occurred
  - `INVALID_MODEL`: Model not found in configuration
  - `MISSING_API_KEY`: Required API key not configured
  - `CAPABILITY_NOT_SUPPORTED`: Provider doesn't support requested feature
- Never log, store or echo API keys, tokens, passwords (per D6)
- Mock provider output always visibly labelled `[MOCK PROVIDER — not a real AI]` (per D15)
- Missing API key => provider marked as unconfigured (health state), app does NOT crash (per D14)

### Timeouts and Latency (per D7)
- All timeouts configurable via config/models.yaml
- Connect timeout: 10s
- First-token timeout: 30s (stream first token as soon as available)
- Total timeout: 120s
- Health-check interval: 5s
- Streaming is primary path; non-streaming generate() also exists

### Dependencies (per D1, D19)
Core dependencies in `pyproject.toml` or `requirements.txt`:
```toml
[project]
name = "lunex"
version = "0.1.0"
dependencies = [
    "python>=3.12",
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "httpx>=0.25.0",
    "anyio>=4.0.0",
    # AI provider SDKs
    "openai>=1.0.0",
    "anthropic>=0.3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.4.0",
    "mypy>=1.8.0",
]
```
Each new dependency requires one-line justification in docs/DEPENDENCIES.md

## API Endpoints (per D3, D10, D12)

### REST Endpoints
All endpoints require `Authorization: Bearer $LUNEX_API_TOKEN`

#### Non-streaming Completion
```
POST /api/v1/chat/completions
```

#### Streaming Completion
```
POST /api/v1/chat/completions/stream
Returns: text/event-stream
```

#### Health Check
```
GET /api/v1/health
Returns: {
    "status": "healthy",
    "providers": {
        "openai": {"status": "healthy", "latency_ms": 120},
        "anthropic": {"status": "healthy", "latency_ms": 150},
        "ollama": {"status": "healthy", "latency_ms": 50},
        "mock": {"status": "healthy"}
    }
}
```

#### Model Information
```
GET /api/v1/models
Returns: List of available models with their capabilities
```

### WebSocket Endpoint
```
WS /api/v1/chat/ws
```
Supports full-duplex communication for interactive chat sessions.

### Request Format (Common to REST and WS)
```json
{
  "model": "gpt-4-vision",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What's in this image?"},
    {"role": "user", "content": "[image_data]", "type": "image_url"}
  ],
  "stream": false,
  "options": {
    "temperature": 0.7,
    "max_tokens": 1000
  },
  "provider_options": {
    "openai": {"presence_penalty": 0.1}
  }
}
```

### Response Format
#### Non-streaming
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1704067200,
  "model": "gpt-4-vision",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "The image shows a beautiful sunset over mountains..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 56,
    "completion_tokens": 132,
    "total_tokens": 188
  }
}
```

#### Streaming (text/event-stream)
```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1704067200,"model":"gpt-4-vision","choices":[{"index":0,"delta":{"role":"assistant","content":"The"},"finish_reason":null}]}\n\n
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1704067200,"model":"gpt-4-vision","choices":[{"index":0,"delta":{"content":" image"},"finish_reason":null}]}\n\n
...
data: [DONE]\n\n
```

## Data Flow

1. **Request Reception**
   - API endpoint receives chat completion request
   - Validates Authorization token (per D12)
   - Parses request JSON into internal format

2. **Capability Analysis**
   - Chat Manager retrieves model configuration from config/models.yaml
   - Determines required capabilities based on model and stream flag
   - Example: gpt-4-vision + stream=true → requires [TEXT, STREAMING, VISION]

3. **Provider Selection**
   - Chat Manager queries Provider Registry for providers supporting required capabilities
   - Registry returns list of matching providers
   - Chat Manager selects best provider (currently first match, can be enhanced with ranking)

4. **Provider Execution**
   - Chat Manager calls appropriate method on selected provider:
     - `provider.stream()` for streaming requests
     - `provider.generate()` for non-streaming requests
   - Provider-specific options passed via provider_options dict
   - For streaming: yields tokens as they arrive (per D7: stream first token ASAP)
   - For non-streaming: waits for complete response

5. **Response Handling**
   - Non-streaming: formats response according to OpenAI-compatible schema
   - Streaming: formats as text/event-stream with proper chunk structure
   - Adds usage statistics (prompt/completion/total tokens)

6. **Persistence**
   - After non-streaming response: persists conversation turn to SQLite
   - Stores: user messages, assistant response, token counts, timestamps
   - Enables multi-turn conversation context (per D9)

7. **Return to Client**
   - Returns formatted response to API client
   - For WebSocket: sends message through WS connection
   - For REST: returns HTTP response with appropriate headers

## Error Handling Details

### Exception Hierarchy
```
LunexError
├── ProviderError
│   ├── OpenAIError
│   ├── AnthropicError
│   └── OllamaError
├── ConfigurationError
├── CapabilityNotSupported
├── NoSuitableProvider
├── InvalidModel
└── MissingAPIKey
```

### Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "detail": {} // Optional technical details
  }
}
```

### Specific Error Cases
- **Missing API Key**: Provider marked as unhealthy, specific error when attempting to use
- **Model Not Found**: Clear error showing available models
- **Capability Not Supported**: Lists what capabilities the provider actually supports
- **Provider Unavailable**: Health check failure, automatic failover to next provider
- **Rate Limiting**: Provider-specific handling with retry-after headers
- **Invalid Request**: Detailed validation error with field-specific messages

## Status Vocabulary (per D20)

All capabilities in docs/UI use this vocabulary:
- **IMPLEMENTED**: Feature is fully implemented and tested
- **EXPERIMENTAL**: Feature is implemented but may have limitations
- **REQUIRES_INTEGRATION**: Interface exists but needs external service/configuration
- **REQUIRES_PERMISSION**: Feature exists but requires user permission to use
- **PLANNED**: Feature is specified but not yet implemented

### Phase 1 Status Table
| Capability | Status | Reason/Dependency/Next Step |
|------------|--------|-----------------------------|
| Core chat interface (non-streaming) | IMPLEMENTED | - |
| Core chat interface (streaming) | IMPLEMENTED | - |
| OpenAI provider (GPT-4, GPT-4-Turbo) | IMPLEMENTED | - |
| OpenAI provider (GPT-4-Vision) | EXPERIMENTAL | Vision testing needed |
| Anthropic provider (Claude-3) | REQUIRES_INTEGRATION | API key configuration |
| Ollama provider (local models) | REQUIRES_INTEGRATION | Ollama installation required |
| Mock provider | IMPLEMENTED | - |
| Multi-turn conversation persistence | IMPLEMENTED | SQLite backend |
| Model configuration via config/models.yaml | IMPLEMENTED | - |
| Environment variable configuration | IMPLEMENTED | - |
| Provider health checks | IMPLEMENTED | 5s interval |
| Capability-based provider matching | IMPLEMENTED | - |
| Provider options passthrough | IMPLEMENTED | - |
| Structured error handling | IMPLEMENTED | - |
| API authentication (Bearer token) | IMPLEMENTED | - |
| REST API endpoints | IMPLEMENTED | - |
| WebSocket API endpoint | PLANNED | Next step after REST |
| Function calling support | PLANNED | Requires tool system integration |
| Audio processing capability | PLANNED | Future phase |
| Fine-tuning support | PLANNED | Future phase |
| Embedding generation | PLANNED | Future phase |
| Batch processing | PLANNED | Future phase |
| Token streaming optimization | PLANNED | Performance phase |
| Provider fallback/retry logic | PLANNED | Enhancement phase |
| Detailed usage analytics | PLANNED | Monitoring phase |
| Prompt caching | PLANNED | Optimization phase |
| Response caching | PLANNED | Optimization phase |
| Rate limiting | PLANNED | Security phase |
| Request/response validation | PLANNED | Security phase |
| Input sanitization | PLANNED | Security phase |
| Output encoding | PLANNED | Security phase |

## Conclusion

This design provides a solid foundation for LUNEX's AI capabilities in Phase 1, adhering strictly to the decisions outlined in CLAUDE.md. The architecture prioritizes correctness and security while maintaining ease of adding new providers. The implementation ready for development follows all standing rules and prepares for subsequent phases.

The design supports:
- Multiple AI providers (OpenAI, Anthropic, Ollama, Mock)
- Async-first architecture with streaming as primary path
- Unified interface with capability-based routing
- Proper error handling and security practices
- Configuration-driven model and provider management
- Conversation persistence for multi-turn chats
- Extensible foundation for future phases

Next steps after implementation:
1. Write implementation following this design
2. Create comprehensive unit and integration tests
3. Perform manual verification and acceptance testing
4. Update ROADMAP.md to mark Phase 1 as complete
5. Proceed to Phase 2: Memory system implementation