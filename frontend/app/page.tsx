'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageSquare, FileText } from 'lucide-react';
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

  const formatResponseText = (text: string) => {
    // Clean up references and extra formatting
    let cleanedText = text
      .replace(/\([^)]*\.pdf[^)]*\)/gi, '')
      .replace(/\([^)]*\.pptx[^)]*\)/gi, '')
      .replace(/,?\s*p\.\s*\d+[;,.]?/gi, '')
      .replace(/ACC_Provincial_Priorities_June_2024\.pdf/gi, '')
      .replace(/Alberta_Economic_Test_Presentation\.pptx/gi, '')
      .replace(/\s*;\s*/g, '. ')
      .replace(/\s+/g, ' ')
      .trim();

    // Split into sections based on markdown headers
    const sections: Array<{type: 'header' | 'content', text: string}> = [];
    
    // Split by potential headers (text surrounded by ** or starting with *)
    const parts = cleanedText.split(/(?=\*\*[^*]+\*\*)|(?=\*\s*\*\*[^*]+\*\*)/);
    
    parts.forEach(part => {
      const trimmed = part.trim();
      if (!trimmed) return;
      
      // Check if this is a header (starts with ** or * **)
      const headerMatch = trimmed.match(/^\*?\s*\*\*([^*]+)\*\*\s*\*?\s*([\s\S]*)/);
      if (headerMatch) {
        const headerText = headerMatch[1].trim().replace(/[:.]*$/, '');
        const contentText = headerMatch[2].trim();
        
        sections.push({ type: 'header', text: headerText });
        if (contentText) {
          sections.push({ type: 'content', text: contentText });
        }
      } else {
        // Regular content - clean up any remaining asterisks
        const cleanContent = trimmed
          .replace(/^\*\s*/, '') // Remove leading asterisks
          .replace(/\*\s*$/, '') // Remove trailing asterisks
          .replace(/\*\s+/g, '') // Remove asterisks with spaces
          .trim();
        
        if (cleanContent) {
          sections.push({ type: 'content', text: cleanContent });
        }
      }
    });

    return sections.map((section, index) => {
      if (section.type === 'header') {
        return (
          <h3 key={index} className="font-semibold text-gray-900 mb-3 mt-5 text-base first:mt-0">
            {section.text}
          </h3>
        );
      } else {
        // Break content into bullet points (1-2 sentences each)
        const sentences = section.text.split(/(?<=[.!?])\s+/);
        const bulletPoints: string[] = [];
        
        for (let i = 0; i < sentences.length; i += 2) {
          const chunk = sentences.slice(i, i + 2).join(' ').trim();
          if (chunk) {
            bulletPoints.push(chunk);
          }
        }
        
        return (
          <div key={index} className="mb-4">
            {bulletPoints.map((point, pointIndex) => (
              <div key={pointIndex} className="flex items-start gap-3 mb-3">
                <span className="text-blue-500 mt-1.5 text-xs flex-shrink-0">•</span>
                <span className="text-sm leading-relaxed text-gray-700">{point}</span>
              </div>
            ))}
          </div>
        );
      }
    });
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* iOS-style Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-4 safe-area-top">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
              <MessageSquare className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Alberta Assistant</h1>
              <p className="text-xs text-gray-500">Economic Research AI</p>
            </div>
          </div>
          <Link href="/upload" className="text-blue-500 text-sm font-medium hover:text-blue-600">
            Upload
          </Link>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto">
          <div className="max-w-4xl mx-auto px-4 py-4">
            
            {/* Welcome State */}
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center min-h-full py-12">
                <div className="w-20 h-20 bg-blue-500 rounded-full flex items-center justify-center mb-6 shadow-lg">
                  <MessageSquare className="w-10 h-10 text-white" />
                </div>
                <h2 className="text-2xl font-semibold text-gray-900 mb-3 text-center">
                  Hello! Ask me about Alberta's economy
                </h2>
                <p className="text-gray-500 text-center text-base mb-10 max-w-md leading-relaxed">
                  I can help you research Alberta's economic policies, business climate, and government initiatives.
                </p>
                
                {/* Example Questions */}
                <div className="w-full max-w-md space-y-3">
                  {exampleQueries.map((query, index) => (
                    <button
                      key={index}
                      onClick={() => handleExampleClick(query)}
                      className="w-full bg-white rounded-2xl p-4 text-left border border-gray-200 shadow-sm hover:shadow-md hover:border-blue-300 transition-all duration-200 text-sm text-gray-700 leading-relaxed btn-press"
                    >
                      {query}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Message Thread */}
            {messages.length > 0 && (
              <div className="space-y-6 pt-2">
                {messages.map((message) => (
                  <div key={message.id} className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-lg lg:max-w-3xl ${message.isUser ? 'user-message' : 'assistant-message'}`}>
                      {message.isUser ? (
                        // User Message Bubble
                        <div className="bg-blue-500 text-white rounded-2xl rounded-br-lg px-4 py-3 shadow-md">
                          <p className="text-sm leading-relaxed">{message.text}</p>
                        </div>
                      ) : (
                        // Assistant Message Bubble
                        <div className="bg-white rounded-2xl rounded-bl-lg px-6 py-5 shadow-md border border-gray-100">
                          <div className="text-gray-900">
                            {formatResponseText(message.text)}
                          </div>
                          
                          {/* Sources */}
                          {message.sources && message.sources.length > 0 && (
                            <div className="mt-5 pt-4 border-t border-gray-100">
                              <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
                                <FileText className="w-3 h-3" />
                                <span>Sources</span>
                              </div>
                              {message.sources.slice(0, 2).map((source, idx) => (
                                <div key={idx} className="text-xs text-gray-400 mb-1">
                                  {source.document_name} ({Math.round(source.similarity_score * 100)}%)
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* Timestamp */}
                      <div className={`mt-1 text-xs text-gray-400 ${message.isUser ? 'text-right' : 'text-left'}`}>
                        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        {!message.isUser && message.confidence && (
                          <span className="ml-2">• {Math.round(message.confidence * 100)}% confident</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Typing Indicator */}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="max-w-lg lg:max-w-3xl assistant-message">
                      <div className="bg-white rounded-2xl rounded-bl-lg px-4 py-3 shadow-md border border-gray-100">
                        <div className="flex items-center gap-2">
                          <div className="flex gap-1">
                            <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
                            <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
                            <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
                          </div>
                          <span className="text-xs text-gray-500">Thinking...</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* iOS Messages-style Input */}
      <div className="bg-white border-t border-gray-200 px-4 py-3 safe-area-bottom">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="flex items-end gap-3">
            <div className="flex-1 min-h-10 bg-gray-100 rounded-full px-4 py-2 flex items-center">
              <textarea
                ref={inputRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Ask about Alberta..."
                className="flex-1 bg-transparent text-sm resize-none outline-none placeholder-gray-500 max-h-20 leading-relaxed"
                rows={1}
                disabled={isLoading}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
                style={{
                  height: 'auto',
                  minHeight: '20px'
                }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = Math.min(target.scrollHeight, 80) + 'px';
                }}
              />
            </div>
            <button
              type="submit"
              disabled={!inputText.trim() || isLoading}
              className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 btn-press ${
                inputText.trim() && !isLoading
                  ? 'bg-blue-500 text-white shadow-md hover:bg-blue-600'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
