import React from 'react';
import { Icons } from '../icons';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import {
  CertificateCard,
  ProductGallery,
  ImpactStats,
  UrlAction
} from './components';

export interface Source {
  filename: string;
  chunkNumber: number;
  pageNumber?: number;
  similarity?: number;
  preview?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: any; // Changed from string to any to support objects
  timestamp: Date;
  sources?: Source[];
  agent_type?: string;
}

import { parseAgentResponse } from '../../lib/agent-utils';

interface MessageBubbleProps {
  message: Message;
  onCopy?: () => void;
  onFeedback?: (type: 'positive' | 'negative') => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  onCopy,
  onFeedback,
}) => {
  const [showSources, setShowSources] = React.useState(false);
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    const textToCopy = typeof message.content === 'object'
      ? JSON.stringify(message.content, null, 2)
      : message.content;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    onCopy?.();
  };

  const isUser = message.role === 'user';

  const renderContent = () => {
    const content = parseAgentResponse(message.content);

    if (typeof content === 'object' && content !== null) {
      const type = content.type || content.component;

      switch (type) {
        case 'certificate_card':
          return (
            <CertificateCard
              project={content.project || 'Unknown Project'}
              status={content.status || 'Pending'}
              date={content.date || 'N/A'}
              tonnage={content.tonnage || 0}
            />
          );
        case 'product_gallery':
        case 'product_list':
          return <ProductGallery products={content.products || []} />;
        case 'impact_stats':
          return (
            <ImpactStats
              contribution={content.contribution || 0}
              trees_equivalent={content.trees_equivalent || 0}
              rank={content.rank || 'Novice'}
            />
          );
        case 'url_action':
          return (
            <UrlAction
              label={content.label || 'Learn More'}
              url={content.url || '#'}
              type={content.action_type || 'primary'}
            />
          );
        default:
          // If it's an object but types don't match, stringify it
          return <pre className="text-xs overflow-x-auto">{JSON.stringify(content, null, 2)}</pre>;
      }
    }

    return <p className="text-sm whitespace-pre-wrap">{content}</p>;
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[85%] ${isUser ? 'order-2' : 'order-1'}`}>
        {!isUser && (
          <div className="flex items-center gap-1.5 mb-1.5 ml-1">
            <div className="w-1.5 h-1.5 rounded-full bg-primary" />
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest">
              {message.agent_type?.replace(/_/g, ' ') || 'AI Assistant'}
            </span>
          </div>
        )}
        {/* Message bubble */}
        <div
          className={`rounded-lg px-4 py-3 ${isUser
            ? 'bg-primary text-white shadow-md'
            : 'bg-surface border border-border text-text shadow-sm hover:shadow-md transition-shadow'
            }`}
        >
          {renderContent()}
        </div>

        {/* Timestamp */}
        <div className={`text-[10px] text-text-secondary mt-1 opacity-70 ${isUser ? 'text-right' : 'text-left'}`}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>

        {/* Assistant message actions */}
        {!isUser && (
          <div className="mt-2 flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-8 px-2"
            >
              {copied ? (
                <>
                  <Icons.Check className="h-3 w-3 mr-1" />
                  <span className="text-xs">Copied</span>
                </>
              ) : (
                <>
                  <Icons.FileText className="h-3 w-3 mr-1" />
                  <span className="text-xs">Copy</span>
                </>
              )}
            </Button>

            {onFeedback && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onFeedback('positive')}
                  className="h-8 px-2"
                >
                  <span className="text-xs">👍</span>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onFeedback('negative')}
                  className="h-8 px-2"
                >
                  <span className="text-xs">👎</span>
                </Button>
              </>
            )}

            {message.sources && message.sources.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowSources(!showSources)}
                className="h-8 px-2"
              >
                <Icons.FileText className="h-3 w-3 mr-1" />
                <span className="text-xs">
                  {message.sources.length} Source{message.sources.length > 1 ? 's' : ''}
                </span>
                {showSources ? (
                  <Icons.ChevronUp className="h-3 w-3 ml-1" />
                ) : (
                  <Icons.ChevronDown className="h-3 w-3 ml-1" />
                )}
              </Button>
            )}
          </div>
        )}

        {/* Sources */}
        {!isUser && showSources && message.sources && message.sources.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-xs font-semibold text-text">Sources:</p>
            {message.sources.map((source, index) => (
              <div
                key={index}
                className="bg-background border border-border rounded p-2 text-xs"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center space-x-2">
                    <Icons.FileText className="h-3 w-3 text-text-secondary" />
                    <span className="font-medium text-text">{source.filename}</span>
                  </div>
                  {source.similarity && (
                    <Badge variant="outline" className="text-xs">
                      {Math.round(source.similarity * 100)}% match
                    </Badge>
                  )}
                </div>
                <div className="text-text-secondary">
                  Chunk {source.chunkNumber}
                  {source.pageNumber && ` • Page ${source.pageNumber}`}
                </div>
                {source.preview && (
                  <div className="mt-2 text-text-secondary italic border-l-2 border-border pl-2">
                    "{source.preview.substring(0, 150)}..."
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
