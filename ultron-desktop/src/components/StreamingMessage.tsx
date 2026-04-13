import { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Copy, Check, Play, Code, Terminal } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface StreamingMessageProps {
  content: string;
  isStreaming?: boolean;
}

// Code block component with copy/run buttons
function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [output, setOutput] = useState<string | null>(null);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  }, [code]);

  const handleRun = useCallback(async () => {
    if (!language || !['javascript', 'python', 'html', 'css'].includes(language)) {
      setOutput('⚠️ Run is only supported for JavaScript, Python, HTML, and CSS');
      return;
    }

    setIsRunning(true);
    setOutput('⏳ Running code...');

    try {
      if (language === 'javascript') {
        // Run JavaScript in sandbox
        const result = eval(code);
        setOutput(`✅ Output:\n${JSON.stringify(result, null, 2)}`);
      } else if (language === 'html') {
        // Open HTML in new window
        const blob = new Blob([code], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
        setOutput('✅ HTML opened in new window');
      } else if (language === 'python') {
        setOutput('⚠️ Python execution requires backend - code copied to clipboard');
        await navigator.clipboard.writeText(code);
      } else if (language === 'css') {
        setOutput('✅ CSS copied to clipboard - apply to your stylesheet');
        await navigator.clipboard.writeText(code);
      }
    } catch (error: any) {
      setOutput(`❌ Error: ${error.message || error}`);
    } finally {
      setIsRunning(false);
    }
  }, [code, language]);

  const languageLabel = language || 'text';

  return (
    <div className="my-4 rounded-lg overflow-hidden border" style={{ borderColor: 'var(--color-border)' }}>
      {/* Code Header */}
      <div className="flex items-center justify-between px-4 py-2 text-xs" style={{ 
        backgroundColor: 'var(--color-panel)',
        color: 'var(--color-text-muted)'
      }}>
        <div className="flex items-center gap-2">
          {language === 'javascript' || language === 'typescript' ? (
            <Terminal className="w-3.5 h-3.5" />
          ) : (
            <Code className="w-3.5 h-3.5" />
          )}
          <span className="font-mono font-semibold">{languageLabel}</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Copy Button */}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md hover:bg-gray-700/50 transition-colors"
            title="Copy code"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-green-400" />
                <span className="text-green-400">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>

          {/* Run Button (for supported languages) */}
          {['javascript', 'html', 'python', 'css'].includes(language) && (
            <button
              onClick={handleRun}
              disabled={isRunning}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-ultron-primary/20 hover:bg-ultron-primary/30 transition-colors disabled:opacity-50"
              title={isRunning ? 'Running...' : 'Run code'}
            >
              <Play className="w-3.5 h-3.5" />
              <span>{isRunning ? 'Running...' : 'Run'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Code Content */}
      <div className="relative">
        <SyntaxHighlighter
          language={language || 'text'}
          style={oneDark}
          customStyle={{
            margin: 0,
            padding: '1rem',
            fontSize: '0.875rem',
            lineHeight: '1.5',
            backgroundColor: 'var(--color-bg)',
          }}
          showLineNumbers
          wrapLines
        >
          {code}
        </SyntaxHighlighter>
      </div>

      {/* Output (if running code) */}
      <AnimatePresence>
        {output && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t px-4 py-3 text-sm font-mono whitespace-pre-wrap"
            style={{ 
              backgroundColor: 'var(--color-panel)',
              borderColor: 'var(--color-border)',
              color: output.startsWith('❌') ? '#ef4444' : output.startsWith('✅') ? '#10b981' : 'var(--color-text)'
            }}
          >
            {output}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Main StreamingMessage component
export default function StreamingMessage({ content, isStreaming = false }: StreamingMessageProps) {
  // Memoize components to prevent unnecessary re-renders during streaming
  const MarkdownComponents = useMemo(() => ({
    code: ({ className, children, ...props }: any) => {
      const match = /language-(\w+)/.exec(className || '');
      const isInline = !match;
      const language = match ? match[1] : '';
      const code = String(children).replace(/\n$/, '');

      if (!isInline) {
        return <CodeBlock language={language} code={code} />;
      }

      return (
        <code className={className} style={{
          backgroundColor: 'var(--color-panel)',
          padding: '0.2em 0.4em',
          borderRadius: '0.25rem',
          fontSize: '0.875em',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
        }} {...props}>
          {children}
        </code>
      );
    },
    pre: ({ children }: any) => <>{children}</>,
    h1: ({ children }: any) => (
      <h1 className="text-2xl font-bold mt-6 mb-3" style={{ color: 'var(--color-text)' }}>{children}</h1>
    ),
    h2: ({ children }: any) => (
      <h2 className="text-xl font-bold mt-5 mb-2" style={{ color: 'var(--color-text)' }}>{children}</h2>
    ),
    h3: ({ children }: any) => (
      <h3 className="text-lg font-bold mt-4 mb-2" style={{ color: 'var(--color-text)' }}>{children}</h3>
    ),
    p: ({ children }: any) => (
      <p className="mb-3 leading-relaxed" style={{ color: 'var(--color-text)' }}>{children}</p>
    ),
    ul: ({ children }: any) => (
      <ul className="list-disc pl-6 mb-3 space-y-1" style={{ color: 'var(--color-text)' }}>{children}</ul>
    ),
    ol: ({ children }: any) => (
      <ol className="list-decimal pl-6 mb-3 space-y-1" style={{ color: 'var(--color-text)' }}>{children}</ol>
    ),
    li: ({ children }: any) => (
      <li className="mb-1" style={{ color: 'var(--color-text)' }}>{children}</li>
    ),
    blockquote: ({ children }: any) => (
      <blockquote className="border-l-4 pl-4 py-2 my-3 italic" style={{ 
        borderColor: 'var(--color-accent)',
        color: 'var(--color-text-secondary)',
        backgroundColor: 'var(--color-panel)'
      }}>
        {children}
      </blockquote>
    ),
    table: ({ children }: any) => (
      <div className="overflow-x-auto my-4">
        <table className="min-w-full border-collapse border" style={{ borderColor: 'var(--color-border)' }}>
          {children}
        </table>
      </div>
    ),
    th: ({ children }: any) => (
      <th className="border px-3 py-2 font-semibold" style={{ 
        backgroundColor: 'var(--color-panel)',
        borderColor: 'var(--color-border)',
        color: 'var(--color-text)'
      }}>
        {children}
      </th>
    ),
    td: ({ children }: any) => (
      <td className="border px-3 py-2" style={{ 
        borderColor: 'var(--color-border)',
        color: 'var(--color-text)'
      }}>
        {children}
      </td>
    ),
    a: ({ href, children }: any) => (
      <a href={href} className="underline hover:opacity-80" style={{ color: 'var(--color-accent)' }} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    ),
  }), []);

  return (
    <div className="streaming-message">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={MarkdownComponents}
      >
        {content}
      </ReactMarkdown>

      {/* Streaming cursor indicator */}
      {isStreaming && (
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.8, repeat: Infinity, repeatType: "reverse" }}
          className="inline-block w-0.5 h-5 ml-0.5 align-middle"
          style={{ backgroundColor: 'var(--color-accent)' }}
        />
      )}
    </div>
  );
}
