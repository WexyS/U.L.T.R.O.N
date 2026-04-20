import { useState, useEffect } from 'react';
import { Bot, Code, Search, Monitor, Mail, Activity, Clipboard, FileText, Mic, Calendar, ListTodo, CheckCircle, AlertCircle, Cpu, Shield, Globe, Database, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from '../config';

interface AgentData {
  name: string;
  id: string;
  status: string;
  description: string;
  capabilities?: string[];
}

const getAgentIcon = (name: string) => {
  const n = name.toLowerCase();
  if (n.includes('coder') || n.includes('debugger')) return <Code className="w-5 h-5" />;
  if (n.includes('researcher') || n.includes('academic')) return <Search className="w-5 h-5" />;
  if (n.includes('rpa') || n.includes('hardware')) return <Monitor className="w-5 h-5" />;
  if (n.includes('email') || n.includes('message')) return <Mail className="w-5 h-5" />;
  if (n.includes('sysmon') || n.includes('admin')) return <Activity className="w-5 h-5" />;
  if (n.includes('clipboard')) return <Clipboard className="w-5 h-5" />;
  if (n.includes('meeting') || n.includes('voice')) return <Mic className="w-5 h-5" />;
  if (n.includes('file') || n.includes('doc')) return <FileText className="w-5 h-5" />;
  if (n.includes('calendar')) return <Calendar className="w-5 h-5" />;
  if (n.includes('task') || n.includes('plan')) return <ListTodo className="w-5 h-5" />;
  if (n.includes('security') || n.includes('audit')) return <Shield className="w-5 h-5" />;
  if (n.includes('knowledge') || n.includes('graph')) return <Database className="w-5 h-5" />;
  if (n.includes('meta') || n.includes('self')) return <Zap className="w-5 h-5" />;
  if (n.includes('orchestrator')) return <Cpu className="w-5 h-5" />;
  return <Bot className="w-5 h-5" />;
};

const getAgentColor = (name: string) => {
  const n = name.toLowerCase();
  if (n.includes('cognitive') || n.includes('orchestrator')) return 'bg-indigo-500';
  if (n.includes('knowledge')) return 'bg-blue-500';
  if (n.includes('creation')) return 'bg-purple-500';
  if (n.includes('data') || n.includes('finance')) return 'bg-emerald-500';
  if (n.includes('technical') || n.includes('security')) return 'bg-rose-500';
  if (n.includes('iot') || n.includes('control')) return 'bg-orange-500';
  if (n.includes('meta')) return 'bg-amber-500';
  return 'bg-slate-500';
};

export default function AgentsPanel() {
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v3/agents`);
        const data = await response.json();
        setAgents(data);
      } catch (err) {
        console.error('Failed to fetch agents:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchAgents();
    const interval = setInterval(fetchAgents, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  if (loading && agents.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="h-full bg-zinc-50 dark:bg-[#121212] overflow-y-auto">
      {/* Header */}
      <div className="px-8 py-6 border-b border-zinc-200 dark:border-zinc-800/50 backdrop-blur-md sticky top-0 z-10 bg-zinc-50/80 dark:bg-[#121212]/80">
        <div className="flex items-center gap-3 mb-2">
          <Bot className="w-6 h-6 text-purple-500" />
          <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Ultron v3.0 Agent Ecosystem</h2>
        </div>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          {agents.length} autonomous agents active in the decentralized registry
        </p>
      </div>

      <div className="p-8">
        {/* Agents Grid */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {agents.map((agent) => (
            <motion.div
              key={agent.id}
              layout
              onClick={() => setSelectedAgent(selectedAgent === agent.id ? null : agent.id)}
              className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                selectedAgent === agent.id
                  ? 'border-purple-500 bg-purple-500/5 shadow-lg shadow-purple-500/10'
                  : 'border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/50 hover:border-purple-500/50 hover:shadow-md'
              }`}
            >
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-xl ${getAgentColor(agent.name)} text-white flex-shrink-0 shadow-lg`}>
                  {getAgentIcon(agent.name)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-bold text-zinc-900 dark:text-zinc-100 truncate pr-2">{agent.name}</h3>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className={`w-2 h-2 rounded-full ${agent.status === 'idle' ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'}`}></span>
                      <span className="text-[10px] font-bold uppercase tracking-tighter text-zinc-500 dark:text-zinc-400">
                        {agent.status}
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2 leading-relaxed">
                    {agent.description}
                  </p>
                </div>
              </div>

              <AnimatePresence>
                {selectedAgent === agent.id && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-800"
                  >
                    <div className="space-y-4">
                      <div className="flex flex-wrap gap-2">
                        {['Autonomous', 'v3.0 Core', 'Secure', 'Proactive'].map(tag => (
                          <span key={tag} className="px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-[10px] font-medium text-zinc-600 dark:text-zinc-400 rounded-md">
                            {tag}
                          </span>
                        ))}
                      </div>
                      <div>
                        <p className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest mb-2">Agent ID</p>
                        <code className="text-[10px] bg-zinc-100 dark:bg-zinc-800 p-1 rounded text-purple-600 dark:text-purple-400 font-mono block truncate">
                          {agent.id}
                        </code>
                      </div>
                      <button className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold rounded-xl transition-all shadow-lg shadow-purple-600/20">
                        CONFIGURE INSTANCE
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>

        {/* System Health Overlay */}
        <div className="mt-8 p-6 bg-white dark:bg-zinc-900/80 rounded-2xl border border-zinc-200 dark:border-zinc-800 shadow-xl">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-500" />
              Intelligence Network Status
            </h3>
            <span className="px-2 py-1 bg-emerald-500/10 text-emerald-500 text-[10px] font-bold rounded-full">ALL SYSTEMS NOMINAL</span>
          </div>
          
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            <div className="space-y-1">
              <p className="text-3xl font-black text-zinc-900 dark:text-zinc-100">{agents.length}</p>
              <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Total Units</p>
            </div>
            <div className="space-y-1">
              <p className="text-3xl font-black text-emerald-500">{agents.filter(a => a.status === 'idle').length}</p>
              <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Available</p>
            </div>
            <div className="space-y-1">
              <p className="text-3xl font-black text-amber-500">{agents.filter(a => a.status !== 'idle').length}</p>
              <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Busy</p>
            </div>
            <div className="space-y-1">
              <p className="text-3xl font-black text-purple-500">v3.0</p>
              <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Protocol</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
