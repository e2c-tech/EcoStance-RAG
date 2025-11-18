# Database Chat UI Guide

## How the Connection Form Works

The "Chat with Database" tab has a smart connection form that adapts based on the database type you select.

### For SQLite
When you select **SQLite**, you'll see:
- **Database File Path**: Enter the path to your SQLite database file (e.g., `sqlite.db`, `data/mydb.db`)

### For PostgreSQL
When you select **PostgreSQL**, you'll see two columns with:

**Left Column:**
- **Host**: Database server address (e.g., `localhost`, `192.168.1.100`)
- **Username**: Your PostgreSQL username (e.g., `postgres`, `admin`)
- **Database Name**: Name of the database to connect to

**Right Column:**
- **Port**: PostgreSQL port (default: `5432`)
- **Password**: Your database password (hidden input)

### For MySQL
When you select **MySQL**, you'll see two columns with:

**Left Column:**
- **Host**: Database server address (e.g., `localhost`, `192.168.1.100`)
- **Username**: Your MySQL username (e.g., `root`, `admin`)
- **Database Name**: Name of the database to connect to

**Right Column:**
- **Port**: MySQL port (default: `3306`)
- **Password**: Your database password (hidden input)

## Connection Flow

1. **Select Database Type** from the dropdown
2. **Fill in credentials** (form adapts automatically)
3. **Click "Connect"** button
4. **Wait for connection** (spinner shows progress)
5. **Success!** You'll see a green checkmark and can start chatting

## Chat Interface Features

Once connected, you get a full chat interface:

### User Messages
- Type your question in natural language
- Press Enter or click send
- Your question appears in the chat

### Assistant Responses
Each response shows:
- **Generated SQL**: The SQL query created from your question
- **Explanation**: What the query does (💡 icon)
- **Results**: Data table with results (if SELECT query)
- **Row Count**: Number of rows returned (📊 caption)
- **Errors**: Clear error messages if something goes wrong (❌ icon)

### Safety Features
- Only **SELECT** queries are executed automatically
- INSERT/UPDATE/DELETE queries are blocked
- You can see the SQL before it runs
- Clear error messages for unsafe queries

## Example Conversation

```
You: "Show me all users"
Assistant:
  Generated SQL:
  SELECT * FROM users;
  
  💡 This query retrieves all records from the users table
  
  [Table with user data]
  📊 150 rows returned

You: "How many orders were placed today?"
Assistant:
  Generated SQL:
  SELECT COUNT(*) as order_count 
  FROM orders 
  WHERE DATE(created_at) = CURRENT_DATE;
  
  💡 This query counts orders created today
  
  [Table showing count]
  📊 1 row returned
```

## Disconnect

Click the **"Disconnect"** button in the top right to:
- Close the database connection
- Clear the chat history
- Return to the connection form

## Tips

1. **Test with SQLite first** - It's the easiest to set up
2. **Check your credentials** - Make sure host, port, username, and password are correct
3. **Verify database is running** - Ensure your PostgreSQL/MySQL server is active
4. **Use specific questions** - "Show customers from New York" is better than "Show data"
5. **Review the SQL** - Always check the generated query makes sense

## Troubleshooting

### "Connection failed" error
- Verify database server is running
- Check host and port are correct
- Confirm username and password
- Ensure database name exists

### "Failed to generate query" error
- Check `GOOGLE_API_KEY` is set in `.env`
- Try rephrasing your question
- Be more specific about what you want

### No results showing
- Check if the table/columns exist
- Verify you have read permissions
- Try a simpler query first

## Quick Start Example

**SQLite (Easiest):**
1. Select "SQLite"
2. Enter: `sqlite.db`
3. Click "Connect"
4. Ask: "Show me all tables"

**PostgreSQL:**
1. Select "PostgreSQL"
2. Host: `localhost`
3. Port: `5432`
4. Username: `postgres`
5. Password: `your_password`
6. Database: `mydb`
7. Click "Connect"
8. Ask: "What tables are in this database?"

## Features Summary

✅ Adaptive form based on database type
✅ Secure password input (hidden)
✅ Real-time chat interface
✅ SQL query preview
✅ Automatic query execution (safe queries only)
✅ Beautiful data table display
✅ Clear error messages
✅ Chat history maintained during session
✅ Easy disconnect and reconnect
