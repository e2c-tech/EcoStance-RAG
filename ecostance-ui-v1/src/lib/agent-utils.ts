/**
 * Utilities for processing agent responses, especially tool-based outputs
 * that may contain scratchpads, reasoning markers, or JSON blocks.
 */

export const parseAgentResponse = (content: any): any => {
    if (typeof content !== 'string') return content;

    let text = content.trim();

    // 1. Handle markers case-insensitively
    const markers = [
        "### FINAL ANSWER:", "### RESPONSE:", "### ANSWER:",
        "FINAL ANSWER:", "RESPONSE:", "ANSWER:",
        "Thought:", "Reasoning:", "Action:", "Observation:"
    ];

    for (const marker of markers) {
        const markerLower = marker.toLowerCase();
        const textLower = text.toLowerCase();

        // Find index of marker, maybe preceded by newline or at start
        if (textLower.includes(markerLower)) {
            // Find the last occurrence of this marker to get the final answer
            const index = textLower.lastIndexOf(markerLower);
            const sub = text.substring(index + marker.length).trim();

            // Clean up leading punctuation often added by LLMs like ":", "*", " "
            const cleaned = sub.replace(/^[:\*\s\-]+/, '').trim();
            if (cleaned) {
                // Return recursive call to handle nested JSON in the extracted block
                return parseAgentResponse(cleaned);
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
    for (let i = potentialJsonBlocks.length - 1; i >= 0; i--) {
        try {
            const block = potentialJsonBlocks[i];
            const parsed = JSON.parse(block);

            // If it's a valid object, process it
            if (parsed && typeof parsed === 'object') {
                // If it looks like a meaningful response, return it
                // We check for common tool/response keys
                if (parsed.tool === 'none' || parsed.response || parsed.answer || parsed.content || parsed.type) {
                    return processParsedObject(parsed);
                }

                // If it's the last block and looks like JSON, we'll take it 
                // but keep looking for a specifically 'response' oriented block
                if (i === potentialJsonBlocks.length - 1) {
                    const result = processParsedObject(parsed);
                    if (result !== parsed) return result;
                }
            }
        } catch (e) {
            // Not valid JSON, continue to next block
        }
    }

    // 3. Fallback: Check if there's any JSON markdown
    const jsonMarkdownRegex = /```json\n?([\s\S]*?)\n?```/i;
    const match = text.match(jsonMarkdownRegex);
    if (match) {
        try {
            const parsed = JSON.parse(match[1].trim());
            return processParsedObject(parsed);
        } catch (e) { }
    }

    // 4. Conversational filler cleaning
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
