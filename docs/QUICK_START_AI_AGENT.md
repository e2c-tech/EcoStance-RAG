# 🤖 AI Agent - Quick Start

## ✅ Integration Complete!

The QuickShip AI Agent is now integrated into your application.

## 🚀 Start Using It Now

### Step 1: Start the Server
```bash
python run_app.py
```

### Step 2: Open API Docs
```
http://localhost:8000/docs
```

### Step 3: Find "13. AI Agent (Beta)"
Scroll down to the **"13. AI Agent (Beta)"** section

### Step 4: Try It!
Click on `POST /api/v1/beta/agent/chat` and try:

```json
{
  "message": "Hello, who are you?"
}
```

## 🧪 Run Automated Tests
```bash
python test_agent_integration.py
```

## 📝 Example Queries

Try these in the API docs:

1. **Greeting**
   ```json
   {"message": "Hello, how can you help me?"}
   ```

2. **Track Shipment**
   ```json
   {"message": "Track QS250001"}
   ```

3. **Search by Phone**
   ```json
   {"message": "My phone is 9224217802"}
   ```

4. **Knowledge Base**
   ```json
   {"message": "What are your shipping rates?"}
   ```

## 🎯 What It Can Do

✅ Track shipments by ID, phone, email, or tracking number
✅ Check delivery estimates and payment status
✅ Search knowledge bases with RAG
✅ Multi-turn conversations with context
✅ Natural language understanding

## 📚 Documentation

- **Quick Start**: `docs/AI_AGENT_QUICK_START.md`
- **Full Guide**: `docs/AI_AGENT_INTEGRATION.md`
- **Package Docs**: `quickship_agent/README.md`

## 🔧 Configuration

All set in `.env`:
```env
GOOGLE_API_KEY=✅ Configured
QDRANT_URL=✅ Configured
QDRANT_API_KEY=✅ Configured
QUICKSHIP_DB_PATH=✅ Configured
AGENT_MODEL=✅ Configured
```

## 🎉 You're Ready!

The AI Agent is live at:
```
http://localhost:8000/api/v1/beta/agent/chat
```

Start chatting now! 🚀
