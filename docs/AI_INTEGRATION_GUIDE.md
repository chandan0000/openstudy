# OpenStudy AI Integration Architecture & API Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                      │
├─────────────────────────────────────────────────────────────────┤
│  API Routes                                                      │
│  ├── /api/v1/resources (REST + WebSocket)                        │
│  │   ├── POST /          - Upload resource (PDF/Link/Note)       │
│  │   ├── GET  /          - List user resources                   │
│  │   ├── GET  /{id}      - Get resource details                 │
│  │   ├── DELETE /{id}    - Delete resource                      │
│  │   ├── POST /{id}/regenerate-summary                         │
│  │   └── WS  /{id}/qa    - Real-time Q&A WebSocket              │
│  │                                                               │
│  ├── /api/v1/quizzes (REST + WebSocket)                          │
│  │   ├── GET  /          - List published quizzes               │
│  │   ├── POST /          - Create new quiz                      │
│  │   ├── GET  /{id}      - Get quiz with questions              │
│  │   ├── PUT  /{id}      - Update quiz                         │
│  │   ├── DELETE /{id}    - Delete quiz                         │
│  │   ├── POST /{id}/publish                                     │
│  │   ├── GET  /{id}/leaderboard                                 │
│  │   └── WS  /{id}/generate-questions - AI Generation WebSocket  │
│  │                                                               │
│  └── /api/v1/auth, /users, /subjects, etc.                       │
├─────────────────────────────────────────────────────────────────┤
│  Services                                                        │
│  ├── ResourceService    - Resource CRUD + summarization          │
│  ├── QAService          - Q&A sessions with streaming AI         │
│  ├── QuizService        - Quiz management + AI generation      │
│  └── QuestionService    - Question CRUD                        │
├─────────────────────────────────────────────────────────────────┤
│  AI Clients                                                      │
│  ├── OpenAIClient       - Async OpenAI wrapper                   │
│  └── get_sync_openai_client() - For Celery tasks               │
├─────────────────────────────────────────────────────────────────┤
│  Background Workers (Celery)                                     │
│  └── process_resource() - PDF processing, summarization        │
├─────────────────────────────────────────────────────────────────┤
│  External Services                                                 │
│  ├── PostgreSQL         - Primary database                     │
│  ├── Redis              - Caching + temp file storage          │
│  └── OpenAI API         - AI summarization, Q&A, quiz gen       │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration

### Required Environment Variables

```bash
# OpenAI (Required for AI features)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini          # Default model
OPENAI_MAX_TOKENS=2000            # Max tokens per request

# AI Feature Toggles
AI_SUMMARIZATION_ENABLED=true
AI_QA_ENABLED=true
AI_QUIZ_GENERATION_ENABLED=true

# AWS S3 (Optional - for PDF storage)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-south-1
AWS_BUCKET_NAME=
AWS_S3_ENABLED=false              # Set to true to use S3

# Local storage (fallback when S3 disabled)
LOCAL_UPLOAD_DIR=/tmp/openstudy_uploads
```

## API Endpoints Usage Guide

### 1. Resource Library

#### Upload a Resource

**PDF Upload:**
```bash
curl -X POST http://localhost:8000/api/v1/resources \
  -H "Authorization: Bearer <token>" \
  -F "title=My Study Notes" \
  -F "type=pdf" \
  -F "subject_id=uuid-here" \
  -F "file=@/path/to/document.pdf"
```

**Link Resource:**
```bash
curl -X POST http://localhost:8000/api/v1/resources \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "title=Wikipedia Article" \
  -d "type=link" \
  -d "url=https://en.wikipedia.org/wiki/Python"
```

**Note Resource:**
```bash
curl -X POST http://localhost:8000/api/v1/resources \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "title=Quick Notes" \
  -d "type=note" \
  -d "content=These are my study notes about..."
```

**Response (201):**
```json
{
  "id": "uuid",
  "title": "My Study Notes",
  "type": "pdf",
  "summary_status": "pending",
  "created_at": "2026-03-18T..."
}
```

**Processing Flow:**
1. Resource created with `summary_status: pending`
2. PDF bytes stored in Redis (1 hour TTL)
3. Celery task dispatched for async processing
4. Task extracts text (PDF/Link/Note)
5. OpenAI generates structured summary
6. Summary saved to DB and cached in Redis
7. Status updated to `done`

#### Get Resource Summary

```bash
curl http://localhost:8000/api/v1/resources/{resource_id} \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "id": "uuid",
  "title": "My Study Notes",
  "summary": "Main Topic: Python Programming...",
  "summary_status": "done",
  "content": "...extracted text...",
  "file_path": "/tmp/openstudy_uploads/uuid.pdf"
}
```

### 2. Q&A WebSocket

Connect to ask questions about a resource and get streaming AI responses.

**Connection:**
```javascript
const ws = new WebSocket(
  `ws://localhost:8000/api/v1/resources/${resourceId}/qa?token=${jwtToken}`
);

ws.onopen = () => {
  console.log('Connected to Q&A');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'token':
      // Append token to response
      console.log('Token:', data.content);
      break;
    case 'done':
      // Response complete
      console.log('Response complete');
      break;
    case 'error':
      // Handle error
      console.error('Error:', data.content);
      break;
  }
};

// Send a question
ws.send(JSON.stringify({
  message: "What are the key concepts in this document?"
}));
```

**Protocol:**
- Send: `{"message": "your question"}`
- Receive tokens: `{"type": "token", "content": "..."}`
- Receive done: `{"type": "done"}`
- Receive error: `{"type": "error", "content": "..."}`

**Features:**
- AI only answers based on resource content
- Maintains conversation history (last 10 messages)
- Uses cached summary if available
- Saves Q&A session to database

### 3. AI Quiz Generation WebSocket

Generate multiple choice questions using AI.

**Connection:**
```javascript
const ws = new WebSocket(
  `ws://localhost:8000/api/v1/quizzes/${quizId}/generate-questions?token=${jwtToken}`
);

ws.onopen = () => {
  // Send generation parameters
  ws.send(JSON.stringify({
    topic: "Python Basics",
    count: 5,
    difficulty: "easy"  // easy, medium, hard
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'progress':
      console.log('Progress:', data.content);
      break;
    case 'question':
      console.log(`Question ${data.index}/${data.total}:`, data.data);
      break;
    case 'done':
      console.log(`Generated ${data.total} questions`);
      ws.close();
      break;
    case 'error':
      console.error('Error:', data.content);
      break;
  }
};
```

**Question Data Format:**
```json
{
  "type": "question",
  "index": 1,
  "total": 5,
  "data": {
    "id": "uuid",
    "question_text": "What is the output of print(2 + 2)?",
    "options": ["A. 2", "B. 4", "C. 22", "D. Error"],
    "correct_answer": "B",
    "explanation": "2 + 2 equals 4 in Python.",
    "difficulty": "easy",
    "marks": 1,
    "order_index": 0
  }
}
```

### 4. Quiz Management

**Create Quiz:**
```bash
curl -X POST http://localhost:8000/api/v1/quizzes \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Basics Quiz",
    "subject": "Computer Science",
    "description": "Test your Python knowledge",
    "time_limit_minutes": 30
  }'
```

**Get Quiz with Questions:**
```bash
curl http://localhost:8000/api/v1/quizzes/{quiz_id} \
  -H "Authorization: Bearer <token>"
```

**Publish Quiz:**
```bash
curl -X POST http://localhost:8000/api/v1/quizzes/{quiz_id}/publish \
  -H "Authorization: Bearer <token>"
```

## Future Usage Patterns

### 1. Study Session Workflow

```
1. Upload resource (PDF/Link/Note)
   ↓
2. Wait for summarization (poll GET /resources/{id})
   ↓
3. Read AI-generated summary
   ↓
4. Connect to Q&A WebSocket
   ↓
5. Ask questions about confusing topics
   ↓
6. Create quiz from material
   ↓
7. Generate AI questions via WebSocket
   ↓
8. Take quiz / Share with friends
```

### 2. Batch Processing Pattern

For multiple resources:
```python
# Upload multiple resources
resource_ids = []
for file in files:
    response = upload_resource(file)
    resource_ids.append(response['id'])

# Poll all until done
while not all_done:
    for rid in resource_ids:
        status = get_resource(rid)['summary_status']
        if status == 'done':
            mark_done(rid)
```

### 3. Real-time Study Assistant

```javascript
// Real-time Q&A while reading
class StudyAssistant {
  constructor(resourceId, token) {
    this.ws = new WebSocket(
      `ws://.../resources/${resourceId}/qa?token=${token}`
    );
    this.responseBuffer = '';
    
    this.ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'token') {
        this.responseBuffer += data.content;
        this.onUpdate(this.responseBuffer);
      }
    };
  }
  
  ask(question) {
    this.responseBuffer = '';
    this.ws.send(JSON.stringify({ message: question }));
  }
}
```

### 4. AI Content Generation Pipeline

```
1. Create empty quiz
   POST /quizzes → quiz_id
   
2. Connect to generation WebSocket
   WS /quizzes/{quiz_id}/generate-questions
   
3. Send parameters
   { topic: "...", count: 10, difficulty: "medium" }
   
4. Stream results and display as they arrive
   
5. Auto-save to database
   
6. Review, edit, publish
```

## Error Handling

### Common HTTP Status Codes

- `201` - Resource created successfully
- `400` - Validation error (missing fields, invalid type)
- `401` - Authentication required
- `403` - Not authorized (not your resource/quiz)
- `404` - Resource/quiz not found
- `422` - Unprocessable entity (malformed request)

### WebSocket Error Codes

- `4001` - Authentication failed (invalid/missing token)
- Connection closes with JSON: `{"type": "error", "content": "..."}`

### Celery Task Failures

- Task retries 3 times with 60s delay
- `summary_status` set to `failed` on final failure
- Can trigger regeneration via `POST /{id}/regenerate-summary`

## Scaling Considerations

### Horizontal Scaling

- **Stateless API**: Can run multiple FastAPI instances behind load balancer
- **Redis**: Centralized cache shared across instances
- **Celery Workers**: Scale worker count independently
- **PostgreSQL**: Use connection pooling (PgBouncer)

### Performance Tips

1. **Enable AWS S3** for PDF storage in production
2. **Redis caching** for summaries (24 hour TTL)
3. **Rate limiting** on OpenAI calls
4. **Connection pooling** for database

### Monitoring

- Check Celery task queue length
- Monitor OpenAI API usage/costs
- Track Redis memory usage (temporary PDF storage)
- Database connection pool saturation
