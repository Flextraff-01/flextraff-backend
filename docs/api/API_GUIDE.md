# FlexTraff API Guide

## 📚 API Overview

The FlexTraff Backend provides a comprehensive REST API for adaptive traffic control system operations. This guide covers all available endpoints, their parameters, responses, and usage examples.

**Base URL**: `http://127.0.0.1:8001`  
**API Documentation**: `http://127.0.0.1:8001/docs`

## 🏥 Health & Status Endpoints

### GET `/`
**Purpose**: Get basic API information and version  
**Authentication**: Not required

**Response**:
```json
{
  "service": "FlexTraff ATCS API",
  "version": "1.0.0",
  "description": "Adaptive Traffic Control System Backend",
  "status": "operational"
}
```

**Example**:
```bash
curl http://127.0.0.1:8001/
```

### GET `/health`
**Purpose**: Health check with database connection status  
**Authentication**: Not required

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-15T08:30:00Z",
  "database_connected": true,
  "version": "1.0.0"
}
```

**Example**:
```bash
curl http://127.0.0.1:8001/health
```

## 🚦 Junction Management

### GET `/junctions`
**Purpose**: Retrieve all traffic junctions  
**Authentication**: Not required

**Query Parameters**:
- `limit` (optional): Maximum number of results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response**:
```json
{
  "junctions": [
    {
      "id": 1,
      "name": "Main St & Oak Ave",
      "location": "Downtown",
      "lanes": 4,
      "created_at": "2025-09-15T08:00:00Z",
      "is_active": true
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**Example**:
```bash
curl "http://127.0.0.1:8001/junctions?limit=10&offset=0"
```

### POST `/junctions`
**Purpose**: Create a new traffic junction  
**Authentication**: Required (JWT)

**Request Body**:
```json
{
  "name": "Broadway & 5th St",
  "location": "City Center",
  "lanes": 4,
  "description": "Major intersection with heavy traffic"
}
```

**Response**:
```json
{
  "id": 2,
  "name": "Broadway & 5th St",
  "location": "City Center",
  "lanes": 4,
  "description": "Major intersection with heavy traffic",
  "created_at": "2025-09-15T08:30:00Z",
  "is_active": true
}
```

**Example**:
```bash
curl -X POST http://127.0.0.1:8001/junctions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_jwt_token" \
  -d '{
    "name": "Broadway & 5th St",
    "location": "City Center",
    "lanes": 4
  }'
```

## 🧮 Traffic Calculation

### POST `/calculate-timing`
**Purpose**: Calculate optimal traffic light timing based on lane counts  
**Authentication**: Not required

**Request Body**:
```json
{
  "lane_counts": [25, 30, 20, 15],
  "junction_id": 1,
  "time_window": 300,
  "priority_mode": "balanced"
}
```

**Parameters**:
- `lane_counts` (required): Array of 4 integers representing vehicle counts for each lane
- `junction_id` (required): ID of the junction
- `time_window` (optional): Time window in seconds for calculation (default: 300)
- `priority_mode` (optional): "balanced", "efficiency", or "fairness" (default: "balanced")

**Response**:
```json
{
  "calculation_id": 123,
  "junction_id": 1,
  "green_times": [38, 45, 32, 25],
  "cycle_time": 140,
  "lane_counts": [25, 30, 20, 15],
  "timestamp": "2025-09-15T08:30:00Z",
  "efficiency_score": 0.87,
  "algorithm_version": "v2.1",
  "priority_mode": "balanced"
}
```

**Example**:
```bash
curl -X POST http://127.0.0.1:8001/calculate-timing \
  -H "Content-Type: application/json" \
  -d '{
    "lane_counts": [25, 30, 20, 15],
    "junction_id": 1
  }'
```

## 🚗 Vehicle Detection

### POST `/vehicle-detection`
**Purpose**: Record vehicle detection events  
**Authentication**: Not required

**Request Body**:
```json
{
  "junction_id": 1,
  "lane_number": 2,
  "vehicle_count": 1,
  "timestamp": "2025-09-15T08:30:00Z",
  "detection_confidence": 0.95
}
```

**Parameters**:
- `junction_id` (required): ID of the junction
- `lane_number` (required): Lane number (1-4)
- `vehicle_count` (optional): Number of vehicles detected (default: 1)
- `timestamp` (optional): Detection timestamp (default: current time)
- `detection_confidence` (optional): AI confidence score (0.0-1.0)

**Response**:
```json
{
  "detection_id": 456,
  "junction_id": 1,
  "lane_number": 2,
  "vehicle_count": 1,
  "timestamp": "2025-09-15T08:30:00Z",
  "detection_confidence": 0.95,
  "status": "recorded"
}
```

**Example**:
```bash
curl -X POST http://127.0.0.1:8001/vehicle-detection \
  -H "Content-Type: application/json" \
  -d '{
    "junction_id": 1,
    "lane_number": 2,
    "vehicle_count": 3
  }'
```

## 📊 Junction Status & Information

### GET `/junction/{junction_id}/status`
**Purpose**: Get current status and recent activity for a junction  
**Authentication**: Not required

**Path Parameters**:
- `junction_id`: ID of the junction

**Response**:
```json
{
  "junction_id": 1,
  "current_status": "active",
  "last_calculation": {
    "timestamp": "2025-09-15T08:25:00Z",
    "green_times": [38, 45, 32, 25],
    "cycle_time": 140
  },
  "recent_detections": [
    {
      "lane_number": 1,
      "vehicle_count": 2,
      "timestamp": "2025-09-15T08:29:00Z"
    }
  ],
  "total_vehicles_today": 1250,
  "average_cycle_time": 135
}
```

**Example**:
```bash
curl http://127.0.0.1:8001/junction/1/status
```

## 📈 Historical Data

### GET `/junction/{junction_id}/history`
**Purpose**: Get historical traffic calculations for a junction  
**Authentication**: Not required

**Path Parameters**:
- `junction_id`: ID of the junction

**Query Parameters**:
- `start_date` (optional): Start date (YYYY-MM-DD format)
- `end_date` (optional): End date (YYYY-MM-DD format)  
- `limit` (optional): Maximum results (default: 100)

**Response**:
```json
{
  "junction_id": 1,
  "calculations": [
    {
      "calculation_id": 123,
      "timestamp": "2025-09-15T08:30:00Z",
      "green_times": [38, 45, 32, 25],
      "cycle_time": 140,
      "lane_counts": [25, 30, 20, 15],
      "efficiency_score": 0.87
    }
  ],
  "total_records": 1,
  "date_range": {
    "start": "2025-09-15",
    "end": "2025-09-15"
  }
}
```

**Example**:
```bash
curl "http://127.0.0.1:8001/junction/1/history?start_date=2025-09-01&end_date=2025-09-15&limit=50"
```

### GET `/junction/{junction_id}/daily-summary`
**Purpose**: Get daily traffic summary for a specific date  
**Authentication**: Not required

**Path Parameters**:
- `junction_id`: ID of the junction

**Query Parameters**:
- `date` (required): Date in YYYY-MM-DD format

**Response**:
```json
{
  "junction_id": 1,
  "date": "2025-09-15",
  "summary": {
    "total_calculations": 145,
    "total_vehicles": 2350,
    "average_cycle_time": 138.5,
    "peak_hour": "17:00",
    "peak_vehicle_count": 89,
    "efficiency_metrics": {
      "average_efficiency": 0.84,
      "best_efficiency": 0.95,
      "worst_efficiency": 0.72
    }
  },
  "hourly_breakdown": [
    {
      "hour": "08:00",
      "calculations": 12,
      "vehicles": 185,
      "avg_cycle_time": 142.3
    }
  ]
}
```

**Example**:
```bash
curl "http://127.0.0.1:8001/junction/1/daily-summary?date=2025-09-15"
```

## 🔴 Live Data & Real-time

### GET `/live-timing`
**Purpose**: Get current traffic timing for all active junctions  
**Authentication**: Not required

**Query Parameters**:
- `junction_ids` (optional): Comma-separated list of junction IDs
- `time_window` (optional): Time window in seconds for recent data (default: 300)

**Response**:
```json
{
  "timestamp": "2025-09-15T08:30:00Z",
  "junctions": [
    {
      "junction_id": 1,
      "current_timing": {
        "green_times": [38, 45, 32, 25],
        "cycle_time": 140,
        "last_updated": "2025-09-15T08:29:30Z"
      },
      "live_vehicle_counts": [12, 18, 8, 5],
      "status": "active"
    }
  ],
  "system_status": "operational"
}
```

**Example**:
```bash
curl "http://127.0.0.1:8001/live-timing?junction_ids=1,2,3&time_window=600"
```

## ⚠️ Error Responses

All endpoints return consistent error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid lane_counts: must contain exactly 4 positive integers",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2025-09-15T08:30:00Z"
}
```

### 404 Not Found
```json
{
  "detail": "Junction with ID 999 not found",
  "error_code": "RESOURCE_NOT_FOUND",
  "timestamp": "2025-09-15T08:30:00Z"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Database connection failed",
  "error_code": "INTERNAL_ERROR",
  "timestamp": "2025-09-15T08:30:00Z"
}
```

## 🔐 Authentication

Some endpoints require JWT authentication. Include the token in the Authorization header:

```bash
curl -H "Authorization: Bearer your_jwt_token_here" \
  http://127.0.0.1:8001/protected-endpoint
```

### Getting a Token
Authentication tokens can be obtained through the authentication service (if enabled):

```bash
curl -X POST http://127.0.0.1:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

## 📝 Data Models

### Junction Model
```json
{
  "id": "integer",
  "name": "string",
  "location": "string", 
  "lanes": "integer (1-8)",
  "description": "string (optional)",
  "created_at": "ISO 8601 datetime",
  "is_active": "boolean"
}
```

### Traffic Calculation Model
```json
{
  "calculation_id": "integer",
  "junction_id": "integer",
  "green_times": "array of 4 integers (15-75 seconds)",
  "cycle_time": "integer (60-300 seconds)",
  "lane_counts": "array of 4 integers (0-999)",
  "timestamp": "ISO 8601 datetime",
  "efficiency_score": "float (0.0-1.0)",
  "algorithm_version": "string",
  "priority_mode": "string"
}
```

### Vehicle Detection Model
```json
{
  "detection_id": "integer",
  "junction_id": "integer",
  "lane_number": "integer (1-4)",
  "vehicle_count": "integer (1-999)",
  "timestamp": "ISO 8601 datetime",
  "detection_confidence": "float (0.0-1.0)"
}
```

## 🔍 Usage Examples

### Complete Traffic Management Workflow

1. **Check System Health**:
```bash
curl http://127.0.0.1:8001/health
```

2. **Get Available Junctions**:
```bash
curl http://127.0.0.1:8001/junctions
```

3. **Record Vehicle Detection**:
```bash
curl -X POST http://127.0.0.1:8001/vehicle-detection \
  -H "Content-Type: application/json" \
  -d '{"junction_id": 1, "lane_number": 1, "vehicle_count": 5}'
```

4. **Calculate Optimal Timing**:
```bash
curl -X POST http://127.0.0.1:8001/calculate-timing \
  -H "Content-Type: application/json" \
  -d '{"lane_counts": [25, 30, 20, 15], "junction_id": 1}'
```

5. **Monitor Live Status**:
```bash
curl http://127.0.0.1:8001/junction/1/status
```

6. **Analyze Historical Data**:
```bash
curl "http://127.0.0.1:8001/junction/1/daily-summary?date=2025-09-15"
```

## 🚀 Rate Limiting & Performance

- **Rate Limits**: 1000 requests per minute per IP
- **Response Times**: < 100ms for calculation endpoints
- **Concurrent Requests**: Supports up to 100 concurrent connections
- **Data Retention**: Historical data retained for 1 year

## 📞 Support & Documentation

- **Interactive API Docs**: http://127.0.0.1:8001/docs
- **OpenAPI Specification**: http://127.0.0.1:8001/openapi.json
- **Project Setup**: [PROJECT_SETUP.md](./PROJECT_SETUP.md)
- **Testing Guide**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)