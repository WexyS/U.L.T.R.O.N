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
        // SECURITY FIX: Run JavaScript in a sandboxed iframe instead of eval()
        // This prevents access to localStorage, cookies, and parent DOM
        const sandbox = document.createElement('iframe');
        sandbox.sandbox.add('allow-scripts');
        sandbox.style.display = 'none';
        document.body.appendChild(sandbox);

        // Capture console output from the sandbox
        const consoleCapture: string[] = [];
        const wrapperCode = `
          <script>
            (function() {
              const originalLog = console.log;
              const originalError = console.error;
              const originalWarn = console.warn;
              console.log = function(...args) {
                originalLog.apply(console, args);
                window.parent.postMessage({ type: 'console', method: 'log', args: args.map(String) }, '*');
              };
              console.error = function(...args) {
                originalError.apply(console, args);
                window.parent.postMessage({ type: 'console', method: 'error', args: args.map(String) }, '*');
              };
              console.warn = function(...args) {
                originalWarn.apply(console, args);
                window.parent.postMessage({ type: 'console', method: 'warn', args: args.map(String) }, '*');
              };
              window.onerror = function(msg, url, line, col, error) {
                window.parent.postMessage({ type: 'error', message: msg, line: line }, '*');
                return false;
              };
              try {
                ${code}
              } catch(e) {
                window.parent.postMessage({ type: 'error', message: e.message }, '*');
              }
            })();
          <\/script>
        `;
        sandbox.srcdoc = `<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>${wrapperCode}</body></html>`;

        // Listen for console messages from sandbox
        const messageHandler = (event: MessageEvent) => {
          if (event.data?.type === 'console') {
            consoleCapture.push(`[${event.data.method}] ${event.data.args.join(' ')}`);
          } else if (event.data?.type === 'error') {
            consoleCapture.push(`[error] ${event.data.message}${event.data.line ? ` (line ${event.data.line})` : ''}`);
          }
        };
        window.addEventListener('message', messageHandler);

        // Wait a bit for execution, then clean up
        await new Promise(resolve => setTimeout(resolve, 1500));
        window.removeEventListener('message', messageHandler);
        document.body.removeChild(sandbox);

        if (consoleCapture.length > 0) {
          setOutput(`✅ Output:\n${consoleCapture.join('\n')}`);
        } else {
          setOutput('✅ Executed successfully (no console output)');
        }
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
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      setOutput(`❌ Error: ${message}`);
    } finally {
      setIsRunning(false);
    }
  }, [code, language]);

  const languageLabel = language || 'text';

  return (
    <div className="my-4 rounded-lg overflow-hidden border" style={{ borderColor: 'rgb(var(--color-border))' }}>
      {/* Code Header */}
      <div className="flex items-center justify-between px-4 py-2 text-xs" style={{ 
        backgroundColor: 'rgb(var(--color-panel))',
        color: 'rgb(var(--color-text-muted))'
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
            backgroundColor: 'rgb(var(--color-bg))',
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
              backgroundColor: 'rgb(var(--color-panel))',
              borderColor: 'rgb(var(--color-border))',
              color: output.startsWith('❌') ? '#ef4444' : output.startsWith('✅') ? '#10b981' : 'rgb(var(--color-text))'
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
    code: ({ className, children, ...props }: React.HTMLAttributes<HTMLElement>) => {
      const match = /language-(\w+)/.exec(className || '');
      const isInline = !match;
      const language = match ? match[1] : '';
      const code = String(children).replace(/\n$/, '');

      if (!isInline) {
        return <CodeBlock language={language} code={code} />;
      }

      return (
        <code className="px-1.5 py-0.5 rounded-md bg-zinc-100 dark:bg-zinc-800 text-indigo-600 dark:text-indigo-400 font-mono text-sm" {...props}>
          {children}
        </code>
      );
    },
    pre: ({ children }: React.HTMLAttributes<HTMLPreElement>) => <>{children}</>,
    h1: ({ children }: React.HTMLAttributes<HTMLHeadingElement>) => (
      <h1 className="text-2xl font-bold mt-8 mb-4 text-zinc-900 dark:text-zinc-50 tracking-tight">{children}</h1>
    ),
    h2: ({ children }: React.HTMLAttributes<HTMLHeadingElement>) => (
      <h2 className="text-xl font-bold mt-6 mb-3 text-zinc-900 dark:text-zinc-50 tracking-tight">{children}</h2>
    ),
    h3: ({ children }: React.HTMLAttributes<HTMLHeadingElement>) => (
      <h3 className="text-lg font-bold mt-5 mb-2 text-zinc-900 dark:text-zinc-50 tracking-tight">{children}</h3>
    ),
    p: ({ children }: React.HTMLAttributes<HTMLParagraphElement>) => (
      <p className="mb-4 leading-relaxed text-zinc-700 dark:text-zinc-300">{children}</p>
    ),
    ul: ({ children }: React.HTMLAttributes<HTMLUListElement>) => (
      <ul className="list-disc pl-6 mb-4 space-y-2 text-zinc-700 dark:text-zinc-300">{children}</ul>
    ),
    ol: ({ children }: React.HTMLAttributes<HTMLOListElement>) => (
      <ol className="list-decimal pl-6 mb-4 space-y-2 text-zinc-700 dark:text-zinc-300">{children}</ol>
    ),
    li: ({ children }: React.HTMLAttributes<HTMLLIElement>) => (
      <li className="mb-1 leading-relaxed">{children}</li>
    ),
    blockquote: ({ children }: React.HTMLAttributes<HTMLQuoteElement>) => (
      <blockquote className="border-l-4 border-indigo-500 pl-4 py-1 my-4 italic text-zinc-600 dark:text-zinc-400 bg-zinc-50/50 dark:bg-zinc-900/50 rounded-r-lg">
        {children}
      </blockquote>
    ),
    table: ({ children }: React.HTMLAttributes<HTMLTableElement>) => (
      <div className="overflow-x-auto my-6 rounded-xl border border-zinc-200 dark:border-zinc-800">
        <table className="min-w-full border-collapse">
          {children}
        </table>
      </div>
    ),
    th: ({ children }: React.HTMLAttributes<HTMLTableCellElement>) => (
      <th className="px-4 py-2 bg-zinc-50 dark:bg-zinc-800/50 border-b border-zinc-200 dark:border-zinc-800 text-left font-semibold text-zinc-900 dark:text-zinc-100">
        {children}
      </th>
    ),
    td: ({ children }: React.HTMLAttributes<HTMLTableCellElement>) => (
      <td className="px-4 py-2 border-b border-zinc-100 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300">
        {children}
      </td>
    ),
    a: ({ href, children }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
      <a href={href} className="text-indigo-600 dark:text-indigo-400 font-medium underline underline-offset-4 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors" target="_blank" rel="noopener noreferrer">
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
          style={{ backgroundColor: 'rgb(var(--color-accent))' }}
        />
      )}
    </div>
  );
}
