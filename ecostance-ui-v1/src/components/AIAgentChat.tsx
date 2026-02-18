import React, { useState, useRef, useEffect } from 'react';
import { useAIAgent } from '../hooks/useAIAgent';
import { parseAgentResponse } from '../lib/agent-utils';


export const AIAgentChat: React.FC = () => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { chat, reset, loading, error, messages, sessionId } = useAIAgent();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const message = input.trim();
    setInput('');
    await chat(message);
  };

  const handleReset = async () => {
    if (window.confirm('Are you sure you want to reset the conversation?')) {
      await reset();
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface rounded-lg shadow-lg border border-border">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div>
          <h2 className="text-xl font-semibold text-text">AI Agent</h2>
          {sessionId && (
            <p className="text-xs text-text-secondary">Session: {sessionId.slice(0, 8)}...</p>
          )}
        </div>
        <button
          onClick={handleReset}
          disabled={loading || messages.length === 0}
          className="px-3 py-1 text-sm text-error hover:bg-error/10 rounded disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Reset
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-text-secondary mt-8">
            <p className="text-lg mb-2">👋 Hello! I'm your AI Agent</p>
            <p className="text-sm">Ask me about:</p>
            <ul className="text-sm mt-2 space-y-1">
              <li>• Shipment tracking</li>
              <li>• Customer information</li>
              <li>• Delivery estimates</li>
              <li>• Knowledge base queries</li>
            </ul>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[70%] rounded-lg px-4 py-2 ${msg.role === 'user'
                  ? 'bg-primary text-white'
                  : 'bg-background text-text border border-border'
                }`}
            >
              <div className="whitespace-pre-wrap">
                {(() => {
                  const content = parseAgentResponse(msg.content);
                  if (typeof content === 'object' && content !== null) {
                    return <pre className="text-xs bg-black/5 p-2 rounded max-w-full overflow-x-auto">{JSON.stringify(content, null, 2)}</pre>;
                  }
                  return content;
                })()}
              </div>
              <p className="text-xs mt-1 opacity-70">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-background border border-border rounded-lg px-4 py-2">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-error/10 border border-error/20 rounded-lg p-3 text-error text-sm">
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-border">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={loading}
            className="flex-1 px-4 py-2 border border-border bg-background rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-text placeholder:text-text-secondary disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
};
