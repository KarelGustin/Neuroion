# Neuroion API Documentation

Complete API reference for the Neuroion Homebase.

## Base URL

```
http://localhost:8000
```

## Authentication

Most endpoints require authentication via Bearer token in the Authorization header:

```
Authorization: Bearer <token>
```

Tokens are obtained through the pairing process (see `/pair/start` and `/pair/confirm`).

## Endpoints

### Health

#### GET /health

Check service status.

**Response:**
```json
{
  "status": "ok",
  "service": "neuroion-core",
  "timestamp": "2024-01-01T00:00:00"
}
```

### Pairing

#### POST /pair/start

Start pairing process. Generates a short-lived pairing code.

**Request:**
```json
{
  "household_id": 1,
  "device_id": "ios_device_123",
  "device_type": "ios",
  "name": "John's iPhone"
}
```

**Response:**
```json
{
  "pairing_code": "123456",
  "expires_in_minutes": 10
}
```

#### POST /pair/confirm

Confirm pairing with code. Returns long-lived auth token.

**Request:**
```json
{
  "pairing_code": "123456",
  "device_id": "ios_device_123"
}
```

**Response:**
```json
{
  "token": "eyJ...",
  "household_id": 1,
  "user_id": 1,
  "expires_in_hours": 8760
}
```

### Chat

#### POST /chat

Send a message to the agent.

**Headers:**
```
Authorization: Bearer <token>
```

**Request:**
```json
{
  "message": "What should I cook for dinner?",
  "conversation_history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"}
  ]
}
```

**Response:**
```json
{
  "message": "Based on your preferences, I suggest...",
  "reasoning": "You mentioned you like Italian food",
  "actions": [
    {
      "id": 123,
      "name": "generate_week_menu",
      "description": "Generate a weekly meal menu",
      "parameters": {},
      "reasoning": "This will help plan your meals"
    }
  ]
}
```

#### POST /chat/stream

Send a message and receive **Server-Sent Events (SSE)** with real-time progress. Use this for long-running requests (e.g. market research) so the connection stays alive and the client can show status.

**Headers:** same as POST /chat (Bearer token).

**Request:** same body as POST /chat (`message`, optional `conversation_history`).

**Response:** `Content-Type: text/event-stream`. Each event is a JSON object:

- `{"type": "status", "text": "Ik zoek op het web…"}` – status update
- `{"type": "tool_start", "tool": "web.search"}` – tool started
- `{"type": "tool_done", "tool": "web.search"}` – tool finished
- `{"type": "done", "message": "...", "actions": [...]}` – final response (same shape as POST /chat)

#### POST /chat/actions/execute

Execute a confirmed action.

**Headers:**
```
Authorization: Bearer <token>
```

**Request:**
```json
{
  "action_id": 123
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "menu": {
      "Monday": {
        "breakfast": "...",
        "lunch": "...",
        "dinner": "..."
      }
    }
  },
  "error": null
}
```

### Events

#### POST /events

Submit location or health summary events.

**Headers:**
```
Authorization: Bearer <token>
```

**Request (Location):**
```json
{
  "event_type": "location",
  "location": {
    "event_type": "arriving_home",
    "timestamp": "2024-01-01T12:00:00",
    "metadata": {
      "latitude": 37.7749,
      "longitude": -122.4194
    }
  },
  "health_summary": null
}
```

**Request (Health Summary):**
```json
{
  "event_type": "health_summary",
  "location": null,
  "health_summary": {
    "sleep_score": 85.0,
    "recovery_level": "high",
    "activity_level": "medium",
    "summary": "Good sleep quality, high recovery",
    "timestamp": "2024-01-01T08:00:00",
    "metadata": null
  }
}
```

**Response:**
```json
{
  "success": true,
  "snapshot_id": 456,
  "message": "Location event recorded: arriving_home"
}
```

### Admin

#### GET /admin/status

Get system status (requires owner/admin role).

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "households": 1,
  "users": 3,
  "recent_audit_logs": 50,
  "recent_context_snapshots": 100
}
```

#### GET /admin/audit

Get audit logs (requires owner/admin role).

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `limit`: Number of logs to return (default: 100)
- `action_type`: Filter by action type (optional)

**Response:**
```json
[
  {
    "id": 123,
    "action_type": "suggestion",
    "action_name": "generate_week_menu",
    "reasoning": "User asked about dinner",
    "status": "executed",
    "created_at": "2024-01-01T12:00:00",
    "confirmed_at": "2024-01-01T12:01:00",
    "executed_at": "2024-01-01T12:02:00"
  }
]
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

Common status codes:
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error
