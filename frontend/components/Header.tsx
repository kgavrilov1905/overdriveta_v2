import React from 'react';
import Link from 'next/link';
import { Brain, Zap, Upload, MessageSquare } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle: string;
  showUploadLink?: boolean;
  showChatLink?: boolean;
}

export default function Header({ 
  title, 
  subtitle, 
  showUploadLink = true, 
  showChatLink = false 
}: HeaderProps) {
  return (
    <header className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700 px-6 py-4">
      <div className="max-w-4xl mx-auto flex items-center gap-3">
        <div className="flex items-center gap-3">
          <Link href="/" className="p-2 bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
            <Brain className="w-6 h-6 text-white" />
          </Link>
          <div>
            <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
              {title}
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {subtitle}
            </p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-4">
          {showChatLink && (
            <Link
              href="/"
              className="flex items-center gap-2 px-3 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Chat</span>
            </Link>
          )}
          {showUploadLink && (
            <Link
              href="/upload"
              className="flex items-center gap-2 px-3 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <Upload className="w-4 h-4" />
              <span>Upload Documents</span>
            </Link>
          )}
          <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
            <Zap className="w-4 h-4" />
            <span>Powered by Gemini 2.0 Flash</span>
          </div>
        </div>
      </div>
    </header>
  );
} 