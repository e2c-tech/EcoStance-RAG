/**
 * Utilities for processing agent responses, especially tool-based outputs
 * that may contain scratchpads, reasoning markers, or JSON blocks.
 */

export const parseAgentResponse = (content: any): any => {
    if (typeof content !== 'string') return content;

    // 1. Remove markers like "### ANALYZE PREVIOUS TOOL RESULTS:" or "### FINAL ANSWER:"
    // If "### FINAL ANSWER:" exists, we usually only care about what follows it.
    const finalMarker = "### FINAL ANSWER:";
    if (content.includes(finalMarker)) {
        const parts = content.split(finalMarker);
        const lastPart = parts[parts.length - 1].trim();
        if (lastPart) {
            return parseAgentResponse(lastPart); // Recursively parse the extracted part
        }
    }

    // 2. Try to extract JSON from markdown blocks
    const jsonMarkdownRegex = /```json\n([\s\S]*?)\n```/;
    const match = content.match(jsonMarkdownRegex);
    if (match) {
        try {
            return JSON.parse(match[1].trim());
        } catch (e) {
            // If parsing fails, fall back to the raw content
        }
    }

    // 3. Try to parse as raw JSON if it looks like an object or array
    const trimmed = content.trim();
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
        try {
            const parsed = JSON.parse(trimmed);

            // Handle tool-based agent "final answer" format: { tool: "none", args: { response: "..." } }
            if (parsed && typeof parsed === 'object') {
                if (parsed.tool === 'none' && parsed.args?.response) {
                    return parsed.args.response;
                }
                // Also handle cases where the response is inside an 'answer' or 'response' field
                if (Object.keys(parsed).length === 1 && (parsed.response || parsed.answer)) {
                    return parsed.response || parsed.answer;
                }
            }

            return parsed;
        } catch (e) {
            // If it looks like JSON but failed to parse (e.g. multiple blocks), 
            // try to extract the first/last valid JSON object
            const firstBrace = content.indexOf('{');
            const lastBrace = content.lastIndexOf('}');
            if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
                try {
                    const candidate = content.substring(firstBrace, lastBrace + 1);
                    const parsed = JSON.parse(candidate);
                    if (parsed.tool === 'none' && parsed.args?.response) {
                        return parsed.args.response;
                    }
                    return parsed;
                } catch (e2) { }
            }
        }
    }

    // 4. Return as is if no structured format was identified
    return content;
};
