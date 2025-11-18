# Query Classification System

## Overview

The AI Agent now uses a **deterministic query classifier** to decide whether to search the database or knowledge base, eliminating blank responses and ensuring reliable behavior.

---

## How It Works

### Classification Logic:

```
User Query
    ↓
Classifier analyzes keywords
    ↓
    ├─→ Database Query? → Use database tools (shipment tracking)
    ├─→ KB Query? → Search knowledge base directly
    └─→ Unknown? → Use LLM with tools
```

---

## Query Types

### 1. Database Queries (Shipment Tracking)

**Indicators:**
- `track`, `qs250`, `shipment`, `order`
- `delivery boy`, `cod collected`, `payment status`
- `complaint for`, `where is my`, `phone is`, `email is`
- `trk`, `delivered`, `in transit`, `estimate for`

**Examples:**
- "Track QS250001"
- "Where is my order?"
- "My phone is 9224217802"
- "Check payment for QS250010"

**Action:** Uses database tools to query QuickShip.db

---

### 2. Knowledge Base Queries (Policies & Procedures)

**Indicators:**
- `rate`, `cost`, `price`, `how much`
- `policy`, `procedure`, `how do i`
- `what is your`, `what are your`, `tell me about`
- `how long does`, `do you offer`, `what documents`
- `shipping`, `delivery time`, `pickup`, `international`

**Examples:**
- "What are your shipping rates?"
- "How long does delivery take?"
- "Do you offer pickup service?"
- "What documents needed for international shipping?"

**Action:** Searches knowledge base directly (bypasses LLM tool calling)

---

### 3. Unknown Queries

**When:** No clear indicators found

**Action:** Uses LLM with tools (lets model decide)

---

## Benefits

### ✅ Reliable
- No more blank responses
- Predictable behavior
- Fast response times

### ✅ Efficient
- Direct KB search (no LLM overhead for simple queries)
- Database tools for tracking
- LLM only when needed

### ✅ Accurate
- Right tool for the job
- No confusion between query types
- Clear separation of concerns

---

## Implementation

### Classifier Function:

```python
def _classify_query(self, message: str) -> str:
    """
    Classify query type
    Returns: 'database', 'knowledge_base', or 'unknown'
    """
    message_lower = message.lower()
    
    # Check database indicators
    if any(indicator in message_lower for indicator in db_indicators):
        return 'database'
    
    # Check KB indicators  
    if any(indicator in message_lower for indicator in kb_indicators):
        return 'knowledge_base'
    
    return 'unknown'
```

### Query Handling:

```python
query_type = self._classify_query(message)

if query_type == 'knowledge_base' and has_kb:
    # Direct KB search
    result = search_knowledge_base(kb_name, message)
    return result

elif query_type == 'database':
    # Use LLM with database tools
    result = llm_with_tools.invoke(message)
    return result

else:
    # Unknown - let LLM decide
    result = llm_with_tools.invoke(message)
    return result
```

---

## Examples

### Example 1: KB Query
```
Input: "What are your shipping rates?"
Classifier: 'knowledge_base' (found 'rate')
Action: Direct KB search
Output: "Shipping rates: ₹55-₹120 per kg..."
```

### Example 2: Database Query
```
Input: "Track QS250001"
Classifier: 'database' (found 'track' and 'qs250')
Action: Use database tools
Output: "Shipment QS250001 is Delivered..."
```

### Example 3: Hybrid Query
```
Input: "My order QS250001 is delayed, what can I do?"
Classifier: 'database' (found 'qs250' and 'order')
Action: Use database tools + LLM decides to also search KB
Output: "Your order is in transit... According to our policy..."
```

---

## Troubleshooting

### Issue: Query classified wrong

**Solution:** Add more indicators to the classifier

```python
# Add to db_indicators or kb_indicators
db_indicators.append('new_keyword')
```

### Issue: Still getting blank responses

**Check:**
1. Is KB selected in sidebar?
2. Does KB have content?
3. Check backend logs for errors

### Issue: Query should use both DB and KB

**Solution:** This is handled automatically for 'unknown' queries where LLM can use both tools

---

## Future Improvements

- [ ] Machine learning classifier (more accurate)
- [ ] Intent detection (understand user goals)
- [ ] Multi-intent queries (track + policy in one)
- [ ] Confidence scores (how sure is the classifier)
- [ ] User feedback loop (learn from corrections)

---

**Version:** 1.2.0-beta  
**Last Updated:** November 17, 2025  
**Feature:** Deterministic Query Classification
