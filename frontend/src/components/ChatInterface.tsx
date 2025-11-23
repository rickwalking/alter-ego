import { useState, useEffect, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { sendMessage, ApiError } from '@/services/api';
import type { Message } from '@/types';

/**
 * Chat Interface Component
 *
 * Features:
 * - Real-time message display with ScrollArea
 * - User/AI message distinction with Avatar
 * - Auto-scroll to latest message
 * - Loading state during API calls
 * - Error handling for backend unavailability
 * - Liquid glass morphism styling
 */
export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [lastSentTime, setLastSentTime] = useState<number | null>(null);
  const [rateLimitRemaining, setRateLimitRemaining] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Constants for validation
  const MAX_MESSAGE_LENGTH = 5000;
  const RATE_LIMIT_MS = 1000; // 1 second

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    // Double requestAnimationFrame ensures layout is complete
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      });
    });
  }, [messages]);

  // Rate limit countdown timer
  useEffect(() => {
    if (lastSentTime === null) return;

    const updateRateLimit = () => {
      const now = Date.now();
      const elapsed = now - lastSentTime;
      const remaining = Math.max(0, RATE_LIMIT_MS - elapsed);

      setRateLimitRemaining(remaining);

      if (remaining > 0) {
        requestAnimationFrame(updateRateLimit);
      }
    };

    requestAnimationFrame(updateRateLimit);
  }, [lastSentTime, RATE_LIMIT_MS]);

  const handleSendMessage = async () => {
    // Clear validation errors
    setValidationError(null);

    // Validate input
    if (!inputMessage.trim()) {
      return;
    }

    // Validate character count
    if (inputMessage.length > MAX_MESSAGE_LENGTH) {
      setValidationError(`Message too long (${inputMessage.length}/${MAX_MESSAGE_LENGTH} characters)`);
      return;
    }

    // Validate rate limit
    if (lastSentTime !== null) {
      const timeSinceLastSend = Date.now() - lastSentTime;
      if (timeSinceLastSend < RATE_LIMIT_MS) {
        const remainingSeconds = ((RATE_LIMIT_MS - timeSinceLastSend) / 1000).toFixed(1);
        setValidationError(`Please wait ${remainingSeconds}s before sending another message`);
        return;
      }
    }

    // Clear error state
    setError(null);

    // Create user message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      content: inputMessage,
      role: 'user',
      timestamp: new Date().toISOString(),
    };

    // Add user message to chat
    setMessages((prev) => [...prev, userMessage]);

    // Clear input
    setInputMessage('');

    // Update rate limit timestamp
    setLastSentTime(Date.now());

    // Set loading state
    setIsLoading(true);

    try {
      // Send message to backend
      const response = await sendMessage(inputMessage);

      // Create AI response message
      const aiMessage: Message = {
        id: crypto.randomUUID(),
        content: response.response,
        role: 'assistant',
        timestamp: response.timestamp,
      };

      // Add AI response to chat
      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      // Handle error
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setInputMessage('');
      setError(null);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-4">
      <Card className="glass-card h-[600px] flex flex-col">
        <CardContent className="flex-1 flex flex-col p-6 overflow-hidden">
          {/* Chat Messages */}
          <ScrollArea
            className="flex-1 mb-4 overflow-auto"
            role="log"
            aria-live="polite"
            aria-busy={isLoading}
            aria-label="Chat messages"
          >
            <div ref={scrollRef} className="pr-4 h-full">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-text-tertiary text-sm min-h-[400px]">
            Start a conversation by typing a message below
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex items-start gap-3 animate-[message-in_0.3s_ease-out]`}
              >
                {/* Avatar */}
                <Avatar className={`border-2 ${
                  message.role === 'user'
                    ? 'border-primary-600'
                    : 'border-primary-400'
                }`}>
                  <AvatarFallback className={
                    message.role === 'user'
                      ? 'bg-primary-600/20 text-primary-400'
                      : 'bg-primary-600/40 text-primary-200'
                  }>
                    {message.role === 'user' ? 'U' : 'AI'}
                  </AvatarFallback>
                </Avatar>

                {/* Message Content */}
                <div className={`flex-1 p-4 max-w-[75%] ${
                  message.role === 'user'
                    ? 'message-user ml-auto'
                    : 'message-ai'
                }`}>
                  <p className="text-sm text-text-primary whitespace-pre-wrap">
                    {message.content}
                  </p>
                  <p className="text-xs text-text-tertiary mt-1">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-start gap-3 mt-4 animate-[message-in_0.3s_ease-out]">
            <Avatar className="border-2 border-primary-400">
              <AvatarFallback className="bg-primary-600/40 text-primary-200 animate-pulse">
                AI
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 message-ai p-3 max-w-[75%]">
              <div className="flex gap-1">
                <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-2 h-2 rounded-full bg-primary-400 animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </div>
          </div>
        )}
            </div>
      </ScrollArea>

      {/* API Error Message */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-error/20 border border-error/50 text-error text-sm">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Input Area */}
      <div className="flex flex-col gap-2">
        <span id="message-input-description" className="sr-only">
          Type your message and press Enter or click Send to send it to the AI assistant
        </span>
        <span id="validation-error-description" className="sr-only">
          {validationError || ''}
        </span>
        <div className="flex gap-2">
          <Input
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            disabled={isLoading}
            className="glass-input flex-1"
            aria-label="Message input"
            aria-describedby="message-input-description validation-error-description"
            aria-invalid={!!validationError}
          />
          <Button
            onClick={handleSendMessage}
            disabled={isLoading || !inputMessage.trim() || inputMessage.length > MAX_MESSAGE_LENGTH || rateLimitRemaining > 0}
            className="glass-button-primary text-white"
            size="lg"
            aria-label="Send message"
          >
            {isLoading ? 'Sending...' : rateLimitRemaining > 0 ? `Wait ${(rateLimitRemaining / 1000).toFixed(1)}s` : 'Send'}
          </Button>
        </div>

        {/* Character Counter and Validation Error */}
        <div className="flex items-start justify-between gap-4 min-h-[20px]">
          {/* Validation Error (left-aligned) */}
          <div className="flex-1">
            {validationError && (
              <div className="p-2 rounded-lg bg-error/20 border border-error/50 text-error text-xs">
                {validationError}
              </div>
            )}
          </div>

          {/* Character Counter (right-aligned) */}
          <div className={`text-xs whitespace-nowrap ${
            inputMessage.length > MAX_MESSAGE_LENGTH
              ? 'text-error font-semibold'
              : inputMessage.length > MAX_MESSAGE_LENGTH * 0.9
              ? 'text-warning'
              : 'text-text-tertiary'
          }`}>
            {inputMessage.length} / {MAX_MESSAGE_LENGTH} characters
          </div>
        </div>
      </div>
        </CardContent>
      </Card>
    </div>
  );
}
