/**
 * Utilities for processing agent responses, especially tool-based outputs
 * that may contain scratchpads, reasoning markers, or JSON blocks.
 */

export const parseAgentResponse = (content: any): any => {
    if (typeof content !== 'string') return content;

    let text = content.trim();

    // 1. Handle markers case-insensitively
    // We require markers to either be at the start of the string or follow a newline
    // to avoid matching things like "Recommended Action:" inside a final response.
    const markers = [
        "### FINAL ANSWER:", "### RESPONSE:", "### ANSWER:",
        "FINAL ANSWER:", "RESPONSE:", "ANSWER:",
        "Thought:", "Reasoning:", "Action:", "Observation:"
    ];

    for (const marker of markers) {
        const markerLower = marker.toLowerCase();
        const textLower = text.toLowerCase();

        const index = textLower.lastIndexOf(markerLower);
        if (index !== -1) {
            // Check if it's at the start or follows a newline
            const isAtStart = index === 0;
            const isFollowsNewline = index > 0 && text[index - 1] === '\n';

            // Special case: don't treat "Action:" as a strip marker if it's preceded by "Recommended"
            const isRecommendedAction = markerLower === 'action:' &&
                index >= 12 &&
                textLower.substring(index - 12, index).includes('recommended');

            if ((isAtStart || isFollowsNewline) && !isRecommendedAction) {
                const sub = text.substring(index + marker.length).trim();
                const cleaned = sub.replace(/^[:\*\s\-]+/, '').trim();
                if (cleaned) {
                    return parseAgentResponse(cleaned);
                }
            }
        }
    }

    // 2. Extract and check for JSON blocks
    // This regex finds content between curly braces, handling nested objects 
    // to a shallow degree (enough for most agent responses).
    // We search for all potential JSON blocks and try to parse them.
    const potentialJsonBlocks: string[] = [];
    let braceCount = 0;
    let startPos = -1;

    for (let i = 0; i < text.length; i++) {
        if (text[i] === '{') {
            if (braceCount === 0) startPos = i;
            braceCount++;
        } else if (text[i] === '}') {
            braceCount--;
            if (braceCount === 0 && startPos !== -1) {
                potentialJsonBlocks.push(text.substring(startPos, i + 1));
            }
        }
    }

    // Iterate backwards to find the last valid JSON block (usually the final answer)
    let hasIntermediateToolCall = false;

    for (let i = potentialJsonBlocks.length - 1; i >= 0; i--) {
        const block = potentialJsonBlocks[i];
        let parsed: any = null;

        // Try strict JSON.parse first
        try {
            parsed = JSON.parse(block);
        } catch (e) {
            // JSON.parse failed — likely because the LLM put literal newlines inside
            // string values (e.g. a numbered list). Use regex to extract "response" directly.

            // Check if block looks like a tool response: contains "tool" and "none" and "response"
            if (block.includes('"tool"') && block.includes('"none"') && block.includes('"response"')) {
                const responseMatch = block.match(/"response"\s*:\s*"([\s\S]*?)"\s*[,\n}]/);
                if (responseMatch) {
                    return responseMatch[1].replace(/\\n/g, '\n').trim();
                }
            }

            // Also try: sanitize the JSON by escaping newlines inside strings, then re-parse
            try {
                const sanitized = block.replace(/\n/g, '\\n').replace(/\r/g, '\\r');
                parsed = JSON.parse(sanitized);
            } catch (e2) {
                // Check if it's an intermediate tool call we should skip
                if (block.includes('"tool"') && !block.includes('"none"')) {
                    hasIntermediateToolCall = true;
                }
                continue;
            }
        }

        if (parsed && typeof parsed === 'object') {
            // FINAL ANSWER: tool is "none" — extract the response
            if (parsed.tool === 'none' || parsed.response || parsed.answer) {
                return processParsedObject(parsed);
            }

            // INTERMEDIATE TOOL CALL: tool is "query_database", "search_knowledge_base", etc.
            // This is internal thinking — mark it and skip
            if (parsed.tool && parsed.tool !== 'none') {
                hasIntermediateToolCall = true;
                continue;
            }

            // Generic object with content/type
            if (parsed.content || parsed.type) {
                return processParsedObject(parsed);
            }
        }
    }

    // 3. If we found intermediate tool calls but no final answer,
    // the backend leaked its thinking process. Strip all JSON blocks and scratchpad artifacts.
    if (hasIntermediateToolCall) {
        // Remove all JSON blocks from the text
        let strippedText = text;
        for (const block of potentialJsonBlocks) {
            strippedText = strippedText.replace(block, '');
        }

        // Remove common scratchpad artifacts
        strippedText = strippedText
            .replace(/\*\*Database Schema:\*\*[\s\S]*?(?=\n\n|\*\*|$)/gi, '')
            .replace(/\*\*Database Tables:\*\*[\s\S]*?(?=\n\n|\*\*|$)/gi, '')
            .replace(/\*\*Database Columns:\*\*[\s\S]*?(?=\n\n|\*\*|$)/gi, '')
            .replace(/\*\*Database Query Results:\*\*[\s\S]*?(?=\n\n|\*\*|$)/gi, '')
            .replace(/\*\*Database Results:\*\*[\s\S]*?(?=\n\n|\*\*|$)/gi, '')
            .replace(/TOOL_RESULT\s*\([^)]*\):\s*/gi, '')
            .replace(/list_database_tables/gi, '')
            .replace(/Final Answer:\*?\s*/gi, '')
            .trim();

        // If there's meaningful text left after stripping, return it
        if (strippedText.length > 20) {
            return strippedText;
        }

        // Otherwise return a user-friendly fallback
        return "I'm analyzing your request using the connected database. Please try again in a moment.";
    }

    // 4. Fallback: Check if there's any JSON markdown
    const jsonMarkdownRegex = /```json\n?([\s\S]*?)\n?```/i;
    const match = text.match(jsonMarkdownRegex);
    if (match) {
        try {
            const parsed = JSON.parse(match[1].trim());
            return processParsedObject(parsed);
        } catch (e) { }
    }

    // 5. Conversational filler cleaning
    const reasoningPrefixes = [
        /^Based on the (search results|database|information provided|data analysis),?\s*/i,
        /^I've analyzed the (query|data|logs),?\s*/i,
        /^I found the following (information|results|details):?\s*/i,
        /^Here is the (information|answer) you requested:?\s*/i,
        /^Sure, I can help with that\.?\s*/i,
        /^According to the (database|KB|logs),?\s*/i
    ];

    let cleaned = text;
    for (const prefix of reasoningPrefixes) {
        cleaned = cleaned.replace(prefix, '');
    }

    return cleaned.trim();
};

/**
 * Helper to extract the most meaningful field from a parsed JSON object
 */
const processParsedObject = (parsed: any): any => {
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        return parsed;
    }

    // If it's a known rich component type, keep the whole object
    // But exclude 'text' type as that should be extracted
    if ((parsed.type || parsed.component) && parsed.type !== 'text' && parsed.type !== 'message') {
        return parsed;
    }

    // Handle tool-based agent "final answer" format: { tool: "none", response: "..." }
    if (parsed.tool === 'none' && parsed.response) {
        return parsed.response;
    }

    // Handle tool-based agent "final answer" format with args: { tool: "none", args: { response: "..." } }
    if (parsed.tool === 'none' && parsed.args?.response) {
        return parsed.args.response;
    }

    // If it has a response or answer field, prioritize that over reasoning/thoughts
    if (parsed.response && typeof parsed.response === 'string') {
        return parsed.response;
    }
    if (parsed.answer && typeof parsed.answer === 'string') {
        return parsed.answer;
    }

    // If it has a data field but no main response, maybe it's a raw data dump
    // We'll keep it as an object so the UI can decide how to render (e.g. <pre>)

    // If it only has one key, return that key's value if it's a string
    const keys = Object.keys(parsed);
    if (keys.length === 1 && typeof parsed[keys[0]] === 'string') {
        return parsed[keys[0]];
    }

    return parsed;
};
