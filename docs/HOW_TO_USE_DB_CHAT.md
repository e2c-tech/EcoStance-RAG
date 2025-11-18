# How to Use Chat with Database Feature

## Quick Start Guide

### Step 1: Start the Backend

```bash
python run_app.py
```

The backend will start on `http://127.0.0.1:8000`

### Step 2: Start the UI

```bash
streamlit run ui/app.py
```

The UI will open in your browser (usually `http://localhost:8501`)

### Step 3: Connect to Your Database

1. Go to the **"Chat with Database"** tab
2. Select your database type:

   - SQLite (easiest for testing)
   - PostgreSQL
   - MySQL

3. Enter connection details:

   **For SQLite:**

   - Database File Path: `path/to/your/database.db`

   **For PostgreSQL:**

   - Host: `localhost` (or your server)
   - Port: `5432`
   - Username: your username
   - Password: your password
   - Database Name: your database name

   **For MySQL:**

   - Host: `localhost` (or your server)
   - Port: `3306`
   - Username: your username
   - Password: your password
   - Database Name: your database name

4. Click **"Connect"**

### Step 4: Ask Questions

Once connected, you can ask questions in natural language:

**Examples:**

- "Show me all customers"
- "What are the top 5 products by sales?"
- "How many orders were placed last month?"
- "List all employees in the sales department"
- "What is the total revenue this year?"

### Step 5: Review and Execute

1. The system will generate a SQL query
2. You'll see:

   - The generated SQL query
   - An explanation of what it does
   - A safety check result (SAFE/UNSAFE)

3. If the query is marked as **SAFE**, click **"Execute Query"**
4. Results will be displayed in a table

## Safety Features

- Only **SELECT** queries are marked as SAFE
- INSERT, UPDATE, DELETE, DROP queries are blocked
- You can review the SQL before executing
- All queries are validated before execution

## Troubleshooting

### "Database not connected" error

- Make sure you clicked "Connect" and saw a success message
- Check your connection details are correct
- Verify the database server is running

### "Failed to generate query" error

- Check that `GOOGLE_API_KEY` is set in `.env` file
- Verify your question is clear and specific
- Try rephrasing your question

### "Query execution failed" error

- Review the generated SQL query
- Check if the tables/columns mentioned exist in your database
- Verify you have read permissions on the database

## Tips for Best Results

1. **Be specific**: "Show customers from New York" is better than "Show customers"
2. **Use table names**: If you know them, mention them: "From the orders table, show..."
3. **Ask one thing at a time**: Break complex questions into simpler ones
4. **Review the SQL**: Always check the generated query makes sense

## Example Session

```
You: "How many users are in the database?"
AI: Generates: SELECT COUNT(*) FROM users;
You: [Click Execute]
Result: 1,234 users

You: "Show me the 5 most recent orders"
AI: Generates: SELECT * FROM orders ORDER BY created_at DESC LIMIT 5;
You: [Click Execute]
Result: [Table with 5 orders]
```

## Need Help?

- Check the error log: `errorlog.txt`
- Review the fix summary: `DB_CHAT_FIX_SUMMARY.md`
- Run the test script: `python test_db_connection.py`
