'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageSquare, FileText, Upload, Zap, Search } from 'lucide-react';
import axios from 'axios';
import Link from 'next/link';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  sources?: Array<{
    document_name: string;
    page_number?: number;
    similarity_score: number;
  }>;
  confidence?: number;
  processingTime?: number;
}

interface ChatResponse {
  response: string;
  sources: Array<{
    document_name: string;
    page_number?: number;
    similarity_score: number;
  }>;
  confidence_score: number;
  processing_time: number;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const exampleQueries = [
  "What are Alberta's key economic priorities for 2024?",
  "Tell me about skills training initiatives in Alberta",
  "What are the main challenges facing Alberta businesses?",
  "How is Alberta addressing red tape reduction?"
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      isUser: true,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      console.log('Sending request to:', `${BACKEND_URL}/query/`);
      const response = await axios.post<ChatResponse>(`${BACKEND_URL}/query/`, {
        query: inputText,
        max_results: 5,
        similarity_threshold: 0.7
      }, {
        timeout: 30000,
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.data.response,
        isUser: false,
        timestamp: new Date(),
        sources: response.data.sources,
        confidence: response.data.confidence_score,
        processingTime: response.data.processing_time,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Error sending message:', err);
      let errorMessage = 'Sorry, I encountered an error processing your request.';
      
      if (axios.isAxiosError(err)) {
        if (err.code === 'ECONNREFUSED') {
          errorMessage = 'Cannot connect to the backend server. Please ensure it is running.';
        } else if (err.response?.status === 404) {
          errorMessage = 'API endpoint not found. Please check the backend configuration.';
        } else if (err.response?.data?.detail) {
          errorMessage = err.response.data.detail;
        }
      }
      
      const errorMsgObj: Message = {
        id: (Date.now() + 1).toString(),
        text: errorMessage,
        isUser: false,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsgObj]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExampleClick = (query: string) => {
    setInputText(query);
    inputRef.current?.focus();
  };

  const formatConfidence = (confidence?: number) => {
    if (!confidence) return '';
    return `${Math.round(confidence * 100)}%`;
  };

  const formatProcessingTime = (time?: number) => {
    if (!time) return '';
    return `${time.toFixed(2)}s`;
  };

  // Format response text with better structure
  const formatResponseText = (text: string) => {
    // Split into paragraphs and format
    const paragraphs = text.split('\n\n');
    return paragraphs.map((paragraph, index) => {
      // Check if it's a bullet point list
      if (paragraph.includes('•') || paragraph.includes('-') || paragraph.includes('*')) {
        const lines = paragraph.split('\n');
        return (
          <div key={index} className="mb-4">
            {lines.map((line, lineIndex) => {
              if (line.trim().startsWith('•') || line.trim().startsWith('-') || line.trim().startsWith('*')) {
                return (
                  <div key={lineIndex} className="flex items-start gap-2 mb-2">
                    <span className="text-blue-400 mt-1">•</span>
                    <span>{line.replace(/^[•\-*]\s*/, '').trim()}</span>
                  </div>
                );
              }
              return line.trim() ? <p key={lineIndex} className="mb-2 font-medium">{line}</p> : null;
            })}
          </div>
        );
      }
      // Regular paragraph
      return paragraph.trim() ? <p key={index} className="mb-4 leading-relaxed">{paragraph}</p> : null;
    });
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Clean Header */}
      <header className="glass border-b border-white/10 px-6 py-6">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold gradient-text">Alberta Perspectives RAG</h1>
              <p className="text-sm opacity-70">AI-powered research assistant for Alberta economic insights</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/upload" className="text-sm opacity-70 hover:opacity-100 transition-opacity">
              <Upload className="w-4 h-4 inline mr-1" />
              Upload
            </Link>
            <div className="text-xs opacity-50 flex items-center gap-1">
              <Zap className="w-3 h-3" />
              Gemini 2.0
            </div>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto px-6 py-8">
          <div className="max-w-4xl mx-auto">
            
            {/* Suggestion Cards - Only when no messages */}
            {messages.length === 0 && (
              <div className="py-8">
                <p className="text-center text-sm opacity-70 mb-6">Try one of these questions to get started:</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-3xl mx-auto">
                  {exampleQueries.map((query, index) => (
                    <button
                      key={index}
                      onClick={() => handleExampleClick(query)}
                      className="glass rounded-xl p-4 text-left hover:shadow-lg transition-all duration-200 group border border-white/10"
                    >
                      <div className="flex items-start gap-3">
                        <Search className="w-4 h-4 text-blue-500 group-hover:text-purple-600 transition-colors flex-shrink-0 mt-0.5" />
                        <span className="text-sm leading-relaxed opacity-80 group-hover:opacity-100 transition-opacity">
                          {query}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Messages with More Spacing */}
            <div className="space-y-8">
              {messages.map((message) => (
                <div key={message.id} className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-3xl ${message.isUser ? 'ml-12' : 'mr-12'}`}>
                    <div className={message.isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'}>
                      {message.isUser ? (
                        <p className="leading-relaxed">{message.text}</p>
                      ) : (
                        <div className="space-y-2">
                          {formatResponseText(message.text)}
                        </div>
                      )}
                      
                      {!message.isUser && message.sources && message.sources.length > 0 && (
                        <div className="mt-6 pt-4 border-t border-white/20">
                          <div className="text-xs opacity-70 mb-3">
                            <FileText className="w-3 h-3 inline mr-1" />
                            Sources ({message.sources.length})
                          </div>
                          {message.sources.slice(0, 2).map((source, idx) => (
                            <div key={idx} className="text-xs opacity-60 mb-2 pl-2 border-l-2 border-blue-400/30">
                              {source.document_name} ({Math.round(source.similarity_score * 100)}% match)
                            </div>
                          ))}
                        </div>
                      )}
                      
                      {!message.isUser && (message.confidence || message.processingTime) && (
                        <div className="mt-3 text-xs opacity-50 flex gap-4">
                          {message.confidence && (
                            <span>Confidence: {formatConfidence(message.confidence)}</span>
                          )}
                          {message.processingTime && (
                            <span>{formatProcessingTime(message.processingTime)}s</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="max-w-3xl mr-12">
                    <div className="chat-bubble-assistant">
                      <div className="typing-indicator">
                        <div className="typing-dot"></div>
                        <div className="typing-dot"></div>
                        <div className="typing-dot"></div>
                        <span className="ml-3 text-sm opacity-70">Thinking...</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>
        </div>

        {/* Large Chat Input */}
        <div className="border-t border-white/10 p-6">
          <div className="max-w-4xl mx-auto">
            <form onSubmit={handleSubmit} className="flex gap-4">
              <div className="flex-1">
                <textarea
                  ref={inputRef}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Ask about Alberta's economy, policies, or business climate..."
                  className="input-modern w-full text-lg resize-none"
                  rows={3}
                  disabled={isLoading}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit(e);
                    }
                  }}
                />
              </div>
              <button
                type="submit"
                disabled={!inputText.trim() || isLoading}
                className="btn-primary self-end h-fit px-6 py-3"
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
