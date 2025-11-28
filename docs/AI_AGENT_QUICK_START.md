# AI Agent Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Verify Configuration

Check that your `.env` file has these variables:

```env
GOOGLE_API_KEY=your_gemini_api_key
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_api_key
QUICKSHIP_DB_PATH=tenant_system.db
AGENT_MODEL=gemini-2.0-flash-exp
```

✅ Already configured in your `.env` file!

### Step 2: Start the Server

```bash
python run_app.py
```

The server will start on `http://localhost:8000`

### Step 3: Test the Agent

Open your browser and go to:
```
http://localhost:8000/docs
```

Look for **"13. AI Agent (Beta)"** section.

### Step 4: Try Your First Chat

Click on `POST /api/v1/beta/agent/chat` and try it out:

```json
{
  "message": "Hello, who are you?"
}
```

Click **Execute** and see the response!

## 📝 Example Queries

Try these queries to see the agent in action:

### 1. Simple Greeting
```json
{
  "message": "Hello, how can you help me?"
}
```

### 2. Track a Shipment (if you have test data)
```json
{
  "message": "Track QS250001"
}
```

### 3. Search by Phone
```json
{
  "message": "My phone is 9224217802"
}
```

### 4. Knowledge Base Query
```json
{
  "message": "What are your shipping rates?"
}
```

### 5. Multi-turn Conversation
First message:
```json
{
  "session_id": "my-session-123",
  "message": "Where is my order?"
}
```

Second message (same session):
```json
{
  "session_id": "my-session-123",
  "message": "My email is customer@example.com"
}
```

## 🧪 Run the Test Script

```bash
# Make sure server is running first
python test_agent_integration.py
```

This will test all the agent endpoints automatically.

## 🎯 What the Agent Can Do

### Database Queries
- ✅ Track shipments by ID (QS250XXX)
- ✅ Search by phone number
- ✅ Search by email
- ✅ Track by tracking number (TRKXXXXXXXXX)
- ✅ Check delivery estimates
- ✅ Check payment status
- ✅ Check complaints

### Knowledge Base Queries
- ✅ Search company documents
- ✅ Answer policy questions
- ✅ Provide shipping information
- ✅ Answer FAQs

### Conversation Features
- ✅ Multi-turn conversations
- ✅ Context awareness
- ✅ Session management
- ✅ Natural language understanding

## 🔧 Quick Customization

### Change the Agent's Personality

Edit `quickship_agent/agent_service.py`:

```python
SYSTEM_PROMPT = """You are [YOUR COMPANY]'s AI assistant.

Your role:
- [Your specific role]
- [Your specific tasks]

Guidelines:
- [Your guidelines]
"""
```

### Change the Model

Edit `.env`:

```env
AGENT_MODEL=gemini-1.5-pro  # Use a different model
AGENT_TEMPERATURE=0.5       # Adjust creativity (0.0-1.0)
```

## 📱 Use in Your Application

### Python
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/beta/agent/chat",
    json={"message": "Hello"}
)

print(response.json()["response"])
```

### JavaScript/React
```javascript
const response = await fetch('http://localhost:8000/api/v1/beta/agent/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: 'Hello' })
});

const data = await response.json();
console.log(data.response);
```

### cURL
```bash
curl -X POST "http://localhost:8000/api/v1/beta/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

## 🎨 Frontend Integration

### Simple Chat Interface (HTML + JavaScript)

```html
<!DOCTYPE html>
<html>
<head>
    <title>AI Agent Chat</title>
</head>
<body>
    <div id="chat"></div>
    <input id="message" type="text" placeholder="Type a message...">
    <button onclick="sendMessage()">Send</button>

    <script>
        let sessionId = null;

        async function sendMessage() {
            const message = document.getElementById('message').value;
            const response = await fetch('http://localhost:8000/api/v1/beta/agent/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    session_id: sessionId,
                    message: message 
                })
            });

            const data = await response.json();
            sessionId = data.session_id;
            
            document.getElementById('chat').innerHTML += 
                `<p><strong>You:</strong> ${message}</p>
                 <p><strong>Agent:</strong> ${data.response}</p>`;
            
            document.getElementById('message').value = '';
        }
    </script>
</body>
</html>
```

## 🐛 Troubleshooting

### Server won't start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill the process if needed
taskkill /PID <process_id> /F
```

### Agent not responding
1. Check `.env` file has all required variables
2. Verify Google API key is valid
3. Check server logs for errors

### Database errors
1. Verify `QUICKSHIP_DB_PATH` points to correct database
2. Check database file exists: `dir tenant_system.db`

## 📚 Learn More

- **Full Documentation**: `docs/AI_AGENT_INTEGRATION.md`
- **Package README**: `quickship_agent/README.md`
- **Architecture**: `quickship_agent/ARCHITECTURE.md`
- **Examples**: `quickship_agent/examples/`

## 🎉 You're Ready!

The AI Agent is now integrated and ready to use. Start chatting at:

```
http://localhost:8000/docs
```

Look for **"13. AI Agent (Beta)"** section and start experimenting!
