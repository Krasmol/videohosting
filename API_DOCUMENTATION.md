# Video Hosting Platform API Documentation

## Overview

This document provides comprehensive documentation for all API endpoints in the Video Hosting Platform MVP. The API follows REST principles and uses JSON for request/response bodies.

**Base URL:** `http://localhost:5000/api`

**Authentication:** Most endpoints require Bearer token authentication via the `Authorization` header.

## Table of Contents

1. [Authentication](#authentication)
2. [Channels](#channels)
3. [Videos](#videos)
4. [Subscriptions](#subscriptions)
5. [Error Responses](#error-responses)

---

## Authentication

### Register User

Create a new user account.

**Endpoint:** `POST /auth/register`

**Request Body:**
```json
{
  "username": "string (required, unique)",
  "email": "string (required, unique)",
  "password": "string (required)"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "is_author": false,
  "created_at": "2024-01-15T10:30:00"
}
```

**Errors:**
- `400` - Missing required fields
- `409` - Username or email already exists
- `422` - Invalid data

**Example:**
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "securepass123"
  }'
```

---

### Login

Authenticate and receive a session token.

**Endpoint:** `POST /auth/login`

**Request Body:**
```json
{
  "username": "string (required)",
  "password": "string (required)"
}
```

**Response (200 OK):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "is_author": false,
    "created_at": "2024-01-15T10:30:00"
  }
}
```

**Errors:**
- `400` - Missing required fields
- `401` - Invalid credentials

**Example:**
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "password": "securepass123"
  }'
```

---

### Logout

Terminate the current session.

**Endpoint:** `POST /auth/logout`

**Headers:**
- `Authorization: Bearer <token>` (required)

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

**Errors:**
- `401` - Not authenticated or invalid token

**Example:**
```bash
curl -X POST http://localhost:5000/api/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

### Get Current User

Retrieve information about the authenticated user.

**Endpoint:** `GET /auth/me`

**Headers:**
- `Authorization: Bearer <token>` (required)

**Response (200 OK):**
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "is_author": true,
  "created_at": "2024-01-15T10:30:00"
}
```

**Errors:**
- `401` - Not authenticated or invalid token

**Example:**
```bash
curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Channels

### Create Channel

Create a new channel for the authenticated user.

**Endpoint:** `POST /channels`

**Headers:**
- `Authorization: Bearer <token>` (required)

**Request Body:**
```json
{
  "name": "string (required)",
  "description": "string (optional)"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "author_id": 1,
  "name": "My Awesome Channel",
  "description": "A channel about awesome content",
  "subscriber_count": 0,
  "created_at": "2024-01-15T10:30:00"
}
```

**Errors:**
- `400` - Missing required fields
- `401` - Not authenticated
- `409` - User already has a channel
- `422` - Invalid data

**Example:**
```bash
curl -X POST http://localhost:5000/api/channels \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Awesome Channel",
    "description": "A channel about awesome content"
  }'
```

---

### Get Channel

Retrieve channel details by ID.

**Endpoint:** `GET /channels/:id`

**Response (200 OK):**
```json
{
  "id": 1,
  "author_id": 1,
  "name": "My Awesome Channel",
  "description": "A channel about awesome content",
  "subscriber_count": 42,
  "created_at": "2024-01-15T10:30:00"
}
```

**Errors:**
- `404` - Channel not found

**Example:**
```bash
curl -X GET http://localhost:5000/api/channels/1
```

---

### Update Channel

Update channel metadata (owner only).

**Endpoint:** `PUT /channels/:id`

**Headers:**
- `Authorization: Bearer <token>` (required)

**Request Body:**
```json
{
  "name": "string (optional)",
  "description": "string (optional)"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "author_id": 1,
  "name": "Updated Channel Name",
  "description": "Updated description",
  "subscriber_count": 42,
  "created_at": "2024-01-15T10:30:00"
}
```

**Errors:**
- `400` - Missing request body
- `401` - Not authenticated
- `403` - Not the channel owner
- `404` - Channel not found
- `422` - Invalid data

**Example:**
```bash
curl -X PUT http://localhost:5000/api/channels/1 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Channel Name",
    "description": "Updated description"
  }'
```

---

### Get Channel Videos

Retrieve all videos for a channel.

**Endpoint:** `GET /channels/:id/videos`

**Query Parameters:**
- `status` (optional): Filter by video status (`processing`, `ready`, `failed`)

**Response (200 OK):**
```json
{
  "channel_id": 1,
  "videos": [
    {
      "id": 1,
      "title": "My First Video",
      "description": "An awesome video",
      "duration": 300,
      "access_level": "public",
      "status": "ready",
      "created_at": "2024-01-15T11:00:00"
    },
    {
      "id": 2,
      "title": "Another Video",
      "description": "More awesome content",
      "duration": 450,
      "access_level": "subscriber",
      "status": "ready",
      "created_at": "2024-01-15T12:00:00"
    }
  ]
}
```

**Errors:**
- `404` - Channel not found

**Example:**
```bash
# Get all videos
curl -X GET http://localhost:5000/api/channels/1/videos

# Get only ready videos
curl -X GET "http://localhost:5000/api/channels/1/videos?status=ready"
```

---

## Videos

### Upload Video

Upload a new video to your channel.

**Endpoint:** `POST /videos`

**Headers:**
- `Authorization: Bearer <token>` (required)
- `Content-Type: multipart/form-data`

**Form Data:**
- `file` (required): Video file (mp4, avi, mov, mkv, webm)
- `title` (required): Video title
- `description` (optional): Video description
- `duration` (required): Video duration in seconds
- `access_level` (optional): `public`, `subscriber`, or `sponsor` (default: `public`)
- `has_ads` (optional): Boolean (default: `true`)

**Response (201 Created):**
```json
{
  "id": 1,
  "channel_id": 1,
  "title": "My First Video",
  "description": "An awesome video",
  "duration": 300,
  "access_level": "public",
  "has_ads": true,
  "status": "ready",
  "created_at": "2024-01-15T11:00:00"
}
```

**Errors:**
- `400` - Missing required fields or file
- `401` - Not authenticated
- `403` - User is not an author (no channel)
- `422` - Invalid data or file type

**Example:**
```bash
curl -X POST http://localhost:5000/api/videos \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -F "file=@/path/to/video.mp4" \
  -F "title=My First Video" \
  -F "description=An awesome video" \
  -F "duration=300" \
  -F "access_level=public" \
  -F "has_ads=true"
```

---

### Get Video

Retrieve video details by ID.

**Endpoint:** `GET /videos/:id`

**Response (200 OK):**
```json
{
  "id": 1,
  "channel_id": 1,
  "title": "My First Video",
  "description": "An awesome video",
  "duration": 300,
  "access_level": "public",
  "has_ads": true,
  "status": "ready",
  "created_at": "2024-01-15T11:00:00"
}
```

**Errors:**
- `404` - Video not found

**Example:**
```bash
curl -X GET http://localhost:5000/api/videos/1
```

---

### Delete Video

Delete a video (owner only).

**Endpoint:** `DELETE /videos/:id`

**Headers:**
- `Authorization: Bearer <token>` (required)

**Response (200 OK):**
```json
{
  "message": "Video deleted successfully"
}
```

**Errors:**
- `401` - Not authenticated
- `403` - Not the video owner
- `404` - Video not found

**Example:**
```bash
curl -X DELETE http://localhost:5000/api/videos/1 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

### Get Streaming URL

Get the streaming URL for a video (with access control).

**Endpoint:** `GET /videos/:id/stream`

**Headers:**
- `Authorization: Bearer <token>` (optional, required for non-public videos)

**Response (200 OK):**
```json
{
  "video_id": 1,
  "stream_url": "/uploads/videos/abc123.mp4",
  "has_ads": true
}
```

**Notes:**
- Public videos are accessible without authentication
- Subscriber/sponsor videos require appropriate subscription level
- Sponsors don't see ads (`has_ads` will be `false`)

**Errors:**
- `401` - Authentication required for non-public video
- `403` - Insufficient access level
- `404` - Video not found
- `422` - Video not ready for streaming

**Example:**
```bash
# Public video (no auth needed)
curl -X GET http://localhost:5000/api/videos/1/stream

# Subscriber/sponsor video (auth required)
curl -X GET http://localhost:5000/api/videos/2/stream \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Subscriptions

### Subscribe to Channel

Subscribe to a channel.

**Endpoint:** `POST /channels/:id/subscribe`

**Headers:**
- `Authorization: Bearer <token>` (required)

**Request Body (optional):**
```json
{
  "is_sponsor": false
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "user_id": 2,
  "channel_id": 1,
  "is_sponsor": false,
  "created_at": "2024-01-15T13:00:00",
  "channel": {
    "id": 1,
    "name": "My Awesome Channel",
    "description": "A channel about awesome content",
    "author_id": 1
  }
}
```

**Errors:**
- `401` - Not authenticated
- `404` - Channel not found
- `409` - Already subscribed
- `422` - Cannot subscribe to own channel

**Example:**
```bash
curl -X POST http://localhost:5000/api/channels/1/subscribe \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

### Unsubscribe from Channel

Unsubscribe from a channel.

**Endpoint:** `DELETE /channels/:id/subscribe`

**Headers:**
- `Authorization: Bearer <token>` (required)

**Response (200 OK):**
```json
{
  "message": "Unsubscribed successfully"
}
```

**Errors:**
- `401` - Not authenticated
- `404` - Channel or subscription not found

**Example:**
```bash
curl -X DELETE http://localhost:5000/api/channels/1/subscribe \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

### Upgrade to Sponsor

Upgrade a subscription to sponsor level.

**Endpoint:** `POST /channels/:id/sponsor`

**Headers:**
- `Authorization: Bearer <token>` (required)

**Response (200 OK):**
```json
{
  "id": 1,
  "user_id": 2,
  "channel_id": 1,
  "is_sponsor": true,
  "created_at": "2024-01-15T13:00:00",
  "channel": {
    "id": 1,
    "name": "My Awesome Channel",
    "description": "A channel about awesome content",
    "author_id": 1
  }
}
```

**Errors:**
- `401` - Not authenticated
- `404` - Channel or subscription not found
- `409` - Already a sponsor
- `422` - Must be subscribed first

**Example:**
```bash
curl -X POST http://localhost:5000/api/channels/1/sponsor \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

### Downgrade from Sponsor

Downgrade from sponsor to regular subscription.

**Endpoint:** `DELETE /channels/:id/sponsor`

**Headers:**
- `Authorization: Bearer <token>` (required)

**Response (200 OK):**
```json
{
  "id": 1,
  "user_id": 2,
  "channel_id": 1,
  "is_sponsor": false,
  "created_at": "2024-01-15T13:00:00",
  "channel": {
    "id": 1,
    "name": "My Awesome Channel",
    "description": "A channel about awesome content",
    "author_id": 1
  }
}
```

**Errors:**
- `401` - Not authenticated
- `404` - Channel or subscription not found
- `422` - Not a sponsor

**Example:**
```bash
curl -X DELETE http://localhost:5000/api/channels/1/sponsor \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

### Get My Subscriptions

Retrieve all subscriptions for the authenticated user.

**Endpoint:** `GET /users/me/subscriptions`

**Headers:**
- `Authorization: Bearer <token>` (required)

**Query Parameters:**
- `sponsors_only` (optional): If `true`, only return sponsor subscriptions

**Response (200 OK):**
```json
{
  "subscriptions": [
    {
      "id": 1,
      "user_id": 2,
      "channel_id": 1,
      "is_sponsor": true,
      "created_at": "2024-01-15T13:00:00",
      "channel": {
        "id": 1,
        "name": "My Awesome Channel",
        "description": "A channel about awesome content",
        "author_id": 1
      }
    },
    {
      "id": 2,
      "user_id": 2,
      "channel_id": 3,
      "is_sponsor": false,
      "created_at": "2024-01-15T14:00:00",
      "channel": {
        "id": 3,
        "name": "Another Channel",
        "description": "More content",
        "author_id": 5
      }
    }
  ]
}
```

**Errors:**
- `401` - Not authenticated

**Example:**
```bash
# Get all subscriptions
curl -X GET http://localhost:5000/api/users/me/subscriptions \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Get only sponsor subscriptions
curl -X GET "http://localhost:5000/api/users/me/subscriptions?sponsors_only=true" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Error Responses

All error responses follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

### Common Error Codes

| Status Code | Error Code | Description |
|-------------|------------|-------------|
| 400 | BAD_REQUEST | Missing required fields or malformed request |
| 401 | UNAUTHORIZED | Authentication required or invalid token |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | NOT_FOUND | Resource not found |
| 409 | CONFLICT | Resource conflict (e.g., duplicate) |
| 422 | UNPROCESSABLE_ENTITY | Invalid data or business logic violation |
| 429 | RATE_LIMIT_EXCEEDED | Too many requests |
| 500 | INTERNAL_SERVER_ERROR | Server error |
| 503 | SERVICE_UNAVAILABLE | Service temporarily unavailable |

---

## Complete Workflow Examples

### Example 1: New User Registration and Channel Creation

```bash
# 1. Register a new user
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "creator",
    "email": "creator@example.com",
    "password": "securepass123"
  }'

# 2. Login to get token
TOKEN=$(curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "creator",
    "password": "securepass123"
  }' | jq -r '.token')

# 3. Create a channel
curl -X POST http://localhost:5000/api/channels \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Channel",
    "description": "My awesome channel"
  }'

# 4. Upload a video
curl -X POST http://localhost:5000/api/videos \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@video.mp4" \
  -F "title=My First Video" \
  -F "duration=300"
```

### Example 2: Subscribe and Watch Videos

```bash
# 1. Login as viewer
TOKEN=$(curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "viewer",
    "password": "password123"
  }' | jq -r '.token')

# 2. Subscribe to a channel
curl -X POST http://localhost:5000/api/channels/1/subscribe \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'

# 3. Get streaming URL for a video
curl -X GET http://localhost:5000/api/videos/1/stream \
  -H "Authorization: Bearer $TOKEN"

# 4. Upgrade to sponsor
curl -X POST http://localhost:5000/api/channels/1/sponsor \
  -H "Authorization: Bearer $TOKEN"
```

---

## Rate Limiting

The API implements rate limiting to prevent abuse. Default limits:
- **Authentication endpoints**: 5 requests per minute
- **Other endpoints**: 100 requests per minute

When rate limited, you'll receive a `429` status code with a `Retry-After` header indicating when you can retry.

---

## Versioning

This is version 1.0 of the API (MVP). Future versions may introduce breaking changes with appropriate versioning in the URL path (e.g., `/api/v2/`).

---

## Support

For issues or questions, please contact the development team or file an issue in the project repository.
