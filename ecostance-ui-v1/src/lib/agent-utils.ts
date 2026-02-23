/**
 * Utilities for processing agent responses, especially tool-based outputs
 * that may contain scratchpads, reasoning markers, or JSON blocks.
 */

export const parseAgentResponse = (content: any): any => {
    if (typeof content !== 'string') return content;

    // 1. Remove markers like "### ANALYZE PREVIOUS TOOL RESULTS:" or "### FINAL ANSWER:"
    // If "### FINAL ANSWER:" exists, we usually only care about what follows it.
    const markers = [
        "### FINAL ANSWER:",
        "### RESPONSE:",
        "### ANSWER:",
        "### ANALYZE PREVIOUS TOOL RESULTS:",
        "### SCRATCHPAD:",
        "FINAL ANSWER:",
        "RESPONSE:",
        "ANSWER:",
        "Thought:",
        "Reasoning:",
        "Observation:",
        "Action:",
        "Action Input:"
    ];

    for (const marker of markers) {
        if (content.includes(marker)) {
            const parts = content.split(marker);
            const lastPart = parts[parts.length - 1].trim();
            if (lastPart) {
                return parseAgentResponse(lastPart); // Recursively parse the extracted part
            }
        }
    }

    // 2. Try to extract JSON from markdown blocks
    const jsonMarkdownRegex = /```json\n([\s\S]*?)\n```/;
    const match = content.match(jsonMarkdownRegex);
    if (match) {
        try {
            const parsed = JSON.parse(match[1].trim());
            return processParsedObject(parsed);
        } catch (e) {
            // If parsing fails, fall back to the raw content
        }
    }

    // 3. Try to parse as raw JSON if it looks like an object or array
    const trimmed = content.trim();
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
        try {
            const parsed = JSON.parse(trimmed);
            return processParsedObject(parsed);
        } catch (e) {
            // If it looks like JSON but failed to parse (e.g. multiple blocks), 
            // try to extract the first/last valid JSON object
            const firstBrace = content.indexOf('{');
            const lastBrace = content.lastIndexOf('}');
            if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
                try {
                    const candidate = content.substring(firstBrace, lastBrace + 1);
                    const parsed = JSON.parse(candidate);
                    return processParsedObject(parsed);
                } catch (e2) { }
            }
        }
    }

    // 4. Handle cases where JSON is embedded in text (e.g. "Here is the data: { ... }")
    if (content.includes('{') && content.includes('}')) {
        try {
            const firstBrace = content.indexOf('{');
            const lastBrace = content.lastIndexOf('}');
            const candidate = content.substring(firstBrace, lastBrace + 1);
            const parsed = JSON.parse(candidate);

            // If the parsed object looks like a meaningful response, use its field
            // but maybe keep the surrounding text if it's brief?
            // Actually, usually we just want the parsed object if it's a rich component
            if (parsed && (parsed.type || parsed.component || parsed.response || parsed.answer)) {
                return processParsedObject(parsed);
            }
        } catch (e) { }
    }

    // 5. Clean up conversational filler/reasoning prefixes
    const reasoningPrefixes = [
        /^Based on the (search results|database|information provided),?\s*/i,
        /^I've analyzed the (query|data|logs),?\s*/i,
        /^I found the following (information|results|details):?\s*/i,
        /^Here is the (information|answer) you requested:?\s*/i,
        /^Sure, I can help with that\.?\s*/i
    ];

    let cleaned = content;
    for (const prefix of reasoningPrefixes) {
        cleaned = cleaned.replace(prefix, '');
    }

    // 6. Return as is if no structured format was identified
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
    if (parsed.type || parsed.component) {
        return parsed;
    }

    // Handle tool-based agent "final answer" format: { tool: "none", args: { response: "..." } }
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
