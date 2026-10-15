# LUNEX API Documentation

## Overview

LUNEX provides a comprehensive API for interacting with its core functionalities. This document describes the available endpoints, authentication methods, request/response formats, and usage examples.

## Base URL

All API endpoints are relative to the base URL:
- Development: `http://localhost:3000/api/v1`
- Production: `https://api.lunex.os/api/v1`

## Authentication

LUNEX uses JWT (JSON Web Tokens) for API authentication. All protected endpoints require a valid token in the Authorization header.

### Getting a Token
```http
POST /auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "secure_password"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the Token
Include the token in the Authorization header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Refreshing Tokens
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "your_refresh_token_here"
}
```

## Rate Limiting

API requests are rate-limited to prevent abuse:
- Authenticated users: 1000 requests/hour
- Anonymous users: 100 requests/hour
- Burst limit: 100 requests/minute

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

## Error Format

All API errors follow a consistent format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {} // Optional additional details
  }
}
```

Common error codes:
- `VALIDATION_ERROR`: Invalid request data
- `AUTHENTICATION_REQUIRED`: Missing or invalid authentication
- `AUTHORIZATION_INSUFFICIENT`: Insufficient permissions
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `RESOURCE_CONFLICT`: Conflict with existing resource
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_SERVER_ERROR`: Unexpected server error

## Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Authenticate user and get access token |
| POST | `/auth/logout` | Invalidate user session |
| POST | `/auth/refresh` | Refresh access token using refresh token |
| POST | `/auth/register` | Register new user account |
| POST | `/auth/password-reset` | Initiate password reset |
| POST | `/auth/password-reset/confirm` | Confirm password reset |

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/me` | Get current user profile |
| PUT | `/users/me` | Update current user profile |
| GET | `/users/{id}` | Get user by ID (admin only) |
| PUT | `/users/{id}` | Update user by ID (admin only) |
| DELETE | `/users/{id}` | Delete user by ID (admin only) |
| GET | `/users` | List users (admin only, paginated) |

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents` | List available agents |
| GET | `/agents/{id}` | Get agent details |
| POST | `/agents/{id}/execute` | Execute agent with task |
| GET | `/agents/{id}/executions` | Get agent execution history |
| GET | `/agents/{id}/executions/{executionId}` | Get specific execution details |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tasks` | List user tasks (paginated) |
| POST | `/tasks` | Create new task |
| GET | `/tasks/{id}` | Get task by ID |
| PUT | `/tasks/{id}` | Update task |
| DELETE | `/tasks/{id}` | Delete task |
| POST | `/tasks/{id}/cancel` | Cancel running task |
| POST | `/tasks/{id}/retry` | Retry failed task |

### Memories
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/memories` | List memories (paginated, filterable) |
| POST | `/memories` | Create new memory |
| GET | `/memories/{id}` | Get memory by ID |
| PUT | `/memories/{id}` | Update memory |
| DELETE | `/memories/{id}` | Delete memory |
| GET | `/memories/search` | Search memories (full-text) |
| POST | `/memories/{id}/share` | Share memory with another user |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects` | List user projects (paginated) |
| POST | `/projects` | Create new project |
| GET | `/projects/{id}` | Get project by ID |
| PUT | `/projects/{id}` | Update project |
| DELETE | `/projects/{id}` | Delete project |
| GET | `/projects/{id}/members` | Get project members |
| POST | `/projects/{id}/members` | Add member to project |
| DELETE | `/projects/{id}/members/{userId}` | Remove member from project |

### Tools
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tools` | List available tools |
| GET | `/tools/{id}` | Get tool details |
| POST | `/tools/{id}/execute` | Execute tool with parameters |
| GET | `/tools/{id}/executions` | Get tool execution history |

### Missions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/missions` | List user missions (paginated) |
| POST | `/missions` | Create new mission |
| GET | `/missions/{id}` | Get mission by ID |
| PUT | `/missions/{id}` | Update mission |
| DELETE | `/missions/{id}` | Delete mission |
| GET | `/missions/{id}/progress` | Get mission progress |
| POST | `/missions/{id}/complete` | Mark mission as complete |

### Automation
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/automations` | List user automations (paginated) |
| POST | `/automations` | Create new automation |
| GET | `/automations/{id}` | Get automation by ID |
| PUT | `/automations/{id}` | Update automation |
| DELETE | `/automations/{id}` | Delete automation |
| POST | `/automations/{id}/execute` | Execute automation manually |
| GET | `/automations/{id}/executions` | Get automation execution history |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/system/status` | Get system status and health |
| GET | `/system/metrics` | Get system performance metrics |
| GET | `/system/version` | Get system version information |
| POST | `/system/maintenance` | Enable/disable maintenance mode |
| GET | `/system/logs` | Get system logs (admin only) |
| GET | `/system/audit` | Get audit log (admin only) |

## WebSocket API

LUNEX also provides a WebSocket API for real-time updates.

### Connection
```
WebSocket: ws://localhost:3000/ws
Secure WebSocket: wss://api.lunex.os/ws
```

### Authentication
Send authentication token immediately after connection:
```json
{
  "type": "auth",
  "token": "your_jwt_token_here"
}
```

### Message Format
All WebSocket messages follow this format:
```json
{
  "type": "message_type",
  "data": {}
  // Optional: "id": "message_id" for request/response correlation
}
```

### Message Types
| Type | Direction | Description |
|------|-----------|-------------|
| `auth` | Client → Server | Authentication message |
| `auth_success` | Server → Client | Authentication successful |
| `auth_error` | Server → Client | Authentication failed |
| `task_update` | Server → Client | Task status update |
| `agent_status` | Server → Client | Agent status change |
| `memory_update` | Server → Client | Memory added/updated/deleted |
| `notification` | Server → Client | User notification |
| `system_alert` | Server → Client | System-wide alert |
| `ping` | Bidirectional | Connection keep-alive |
| `pong` | Bidirectional | Response to ping |

### Subscriptions
Clients can subscribe to specific event types:
```json
{
  "type": "subscribe",
  "events": ["task_update", "agent_status", "memory_update"]
}
```

## SDKs

LUNEX provides official SDKs for various platforms:

### JavaScript/TypeScript
```bash
npm install @lunex/sdk
```

```javascript
import { LunexClient } from '@lunex/sdk';

const client = new LunexClient({
  baseUrl: 'https://api.lunex.os/api/v1',
  token: 'your_jwt_token'
});

// Example usage
const user = await client.users.getCurrent();
const tasks = await client.tasks.list({ status: 'pending' });
```

### Python
```bash
pip install lunex-sdk
```

```python
from lunex_sdk import LunexClient

client = LunexClient(
    base_url="https://api.lunex.os/api/v1",
    token="your_jwt_token"
)

# Example usage
user = client.users.get_current()
tasks = client.tasks.list(status="pending")
```

### Swift (iOS)
```bash
# Add to Package.swift
.package(url: "https://github.com/lunexos/swift-sdk.git", from: "1.0.0")
```

```swift
import LunexSDK

let client = LunexClient(
    baseURL: URL(string: "https://api.lunex.os/api/v1")!,
    token: "your_jwt_token"
)

// Example usage
let user = try await client.users.getCurrent()
let tasks = try await client.tasks.list(status: .pending)
```

### Kotlin (Android)
```gradle
// Add to build.gradle
implementation 'com.lunexos:android-sdk:1.0.0'
```

```kotlin
import com.lunexos.sdk.LunexClient

val client = LunexClient(
    baseUrl = "https://api.lunex.os/api/v1",
    token = "your_jwt_token"
)

// Example usage (using coroutines)
val user = client.users.getCurrent()
val tasks = client.tasks.list(status = TaskStatus.PENDING)
```

## Versioning

API versions are indicated in the URL path (`/api/v1/`). Versioning follows these rules:
- Backward-compatible changes: Minor version bump (v1.1 → v1.2)
- Backward-incompatible changes: Major version bump (v1.x → v2.0)
- Deprecated endpoints are maintained for at least one minor version
- Deprecation notices are included in API responses
- Migration guides are provided for major version upgrades

## Changelog

### v1.0.0 (Initial Release)
- Core authentication endpoints
- User management
- Agent execution interface
- Task management
- Memory storage and retrieval
- Project collaboration
- Tool execution API
- Mission tracking
- Automation system
- System monitoring
- WebSocket real-time updates

## Support

For API-related questions and support:
- Documentation: https://docs.lunex.os/api
- Community Forum: https://community.lunexos.org
- Issue Tracker: https://github.com/lunexos/lunex/issues
- Email Support: api-support@lunex.os

## Terms of Use

By using the LUNEX API, you agree to:
- Respect rate limits
- Not reverse engineer or decompile API clients
- Not use the API for unlawful purposes
- Protect user data and privacy
- Notify LUNEX of security vulnerabilities
- Comply with all applicable laws and regulations