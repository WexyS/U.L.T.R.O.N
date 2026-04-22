import { useState, useEffect } from 'react';
import { Bot, Code, Search, Activity, Cpu, Zap, CheckCircle, AlertCircle, BarChart3, List, Settings, Play, Shield, Globe } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from '../config';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

interface AgentActivity {
  timestamp: string;
  agent: string;
  task: string;
  status: 'success' | 'error' | 'running';
  duration?: string;
}

const mockActivity: AgentActivity[] = [
  { timestamp: '14:32:05', agent: 'CoderAgent', task: 'Python fibonacci function write', status: 'success', duration: '2.3s' },
  { timestamp: '14:32:08', agent: 'ResearcherAgent', task: 'Deep research on FLUX models', status: 'success', duration: '4.1s' },
  { timestamp: '14:35:12', agent: 'DebuggerAgent', task: 'Fixing ImportError in main.py', status: 'running' },
];

const mockMetrics = [
  { time: '00:00', load: 12 },
  { time: '04:00', load: 8 },
  { time: '08:00', load: 45 },
  { time: '12:00', load: 78 },
  { time: '16:00', load: 56 },
  { time: '20:00', load: 34 },
  { time: '23:59', load: 15 },
];

export default function AgentControlPanel() {
  const [activeTab, setActiveTab] = useState<'grid' | 'activity' | 'metrics'>('grid');
  const [agents, setAgents] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v3/agents`);
        const data = await response.json();
        setAgents(data);
      } catch (err) {
        console.error('Failed to fetch agents:', err);
      }
    };
    fetchAgents();
  }, []);

  return (
    <div className="h-full bg-zinc-50 dark:bg-[#0a0a0a] flex flex-col overflow-hidden">
      {/* Header & Tabs */}
      <div className="px-8 py-6 border-b border-zinc-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/50 backdrop-blur-xl">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="p-2 bg-purple-500 rounded-lg shadow-lg shadow-purple-500/20">
              <Cpu className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-black text-zinc-900 dark:text-zinc-50 tracking-tight">AGENT CONTROL CENTER</h2>
              <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Ultron Intelligence Network v3.0</p>
            </div>
          </div>
          <div className="flex bg-zinc-100 dark:bg-zinc-800 p-1 rounded-xl border border-zinc-200 dark:border-zinc-700">
            {[
              { id: 'grid', icon: Bot, label: 'Ecosystem' },
              { id: 'activity', icon: List, label: 'Live Feed' },
              { id: 'metrics', icon: BarChart3, label: 'Analytics' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  activeTab === tab.id 
                    ? 'bg-white dark:bg-zinc-700 text-purple-600 dark:text-purple-400 shadow-sm' 
                    : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Quick Stats Bar */}
        <div className="flex gap-8 items-center">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]"></span>
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Nodes Online: {agents.length}</span>
          </div>
          <div className="flex items-center gap-2">
            <Activity className="w-3 h-3 text-purple-500" />
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Avg Latency: 420ms</span>
          </div>
          <div className="flex items-center gap-2">
            <Zap className="w-3 h-3 text-amber-500" />
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Daily Tasks: 1,284</span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-8">
        <AnimatePresence mode="wait">
          {activeTab === 'grid' && (
            <motion.div
              key="grid"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            >
              {agents.map((agent) => (
                <AgentCard 
                  key={agent.id} 
                  agent={agent} 
                  isSelected={selectedAgent === agent.id}
                  onClick={() => setSelectedAgent(selectedAgent === agent.id ? null : agent.id)}
                />
              ))}
            </motion.div>
          )}

          {activeTab === 'activity' && (
            <motion.div
              key="activity"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="max-w-4xl mx-auto space-y-4"
            >
              {mockActivity.map((log, i) => (
                <div key={i} className="flex items-center gap-4 p-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl">
                  <div className={`p-2 rounded-lg ${
                    log.status === 'success' ? 'bg-emerald-500/10 text-emerald-500' : 
                    log.status === 'error' ? 'bg-rose-500/10 text-rose-500' : 'bg-blue-500/10 text-blue-500 animate-pulse'
                  }`}>
                    {log.status === 'success' ? <CheckCircle className="w-4 h-4" /> : 
                     log.status === 'error' ? <AlertCircle className="w-4 h-4" /> : <Activity className="w-4 h-4" />}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-bold text-zinc-400 font-mono">{log.timestamp}</span>
                      <span className="text-xs font-black text-purple-600 dark:text-purple-400 uppercase tracking-tighter">{log.agent}</span>
                    </div>
                    <p className="text-sm text-zinc-700 dark:text-zinc-300 font-medium">{log.task}</p>
                  </div>
                  {log.duration && (
                    <span className="text-[10px] font-bold bg-zinc-100 dark:bg-zinc-800 px-2 py-1 rounded-md text-zinc-500">
                      {log.duration}
                    </span>
                  )}
                </div>
              ))}
            </motion.div>
          )}

          {activeTab === 'metrics' && (
            <motion.div
              key="metrics"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
              className="grid grid-cols-1 lg:grid-cols-2 gap-8"
            >
              <div className="p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl">
                <h3 className="font-bold mb-6 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-purple-500" /> System Load (Tasks/hr)
                </h3>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={mockMetrics}>
                      <defs>
                        <linearGradient id="colorLoad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#333" />
                      <XAxis dataKey="time" stroke="#666" fontSize={10} axisLine={false} tickLine={false} />
                      <YAxis stroke="#666" fontSize={10} axisLine={false} tickLine={false} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#18181b', border: 'none', borderRadius: '12px', fontSize: '10px' }}
                        itemStyle={{ color: '#a78bfa' }}
                      />
                      <Area type="monotone" dataKey="load" stroke="#8b5cf6" strokeWidth={3} fillOpacity={1} fill="url(#colorLoad)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: 'Intelligence Ratio', val: '94.2%', icon: Zap, color: 'text-amber-500' },
                  { label: 'Security Score', val: 'A+', icon: Shield, color: 'text-emerald-500' },
                  { label: 'Global Nodes', val: '12', icon: Globe, color: 'text-blue-500' },
                  { label: 'Success Rate', val: '99.8%', icon: CheckCircle, color: 'text-purple-500' }
                ].map(stat => (
                  <div key={stat.label} className="p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl flex flex-col justify-center items-center text-center">
                    <stat.icon className={`w-8 h-8 mb-4 ${stat.color}`} />
                    <p className="text-3xl font-black mb-1">{stat.val}</p>
                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">{stat.label}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function AgentCard({ agent, isSelected, onClick }: any) {
  return (
    <motion.div
      layout
      onClick={onClick}
      className={`p-6 rounded-3xl border cursor-pointer transition-all ${
        isSelected
          ? 'border-purple-500 bg-purple-500/5 shadow-2xl shadow-purple-500/10'
          : 'border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/50 hover:border-purple-500/50 shadow-sm'
      }`}
    >
      <div className="flex items-start justify-between mb-6">
        <div className={`p-4 rounded-2xl shadow-xl ${
          agent.status === 'idle' ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500' : 'bg-purple-600 text-white'
        }`}>
          <Bot className="w-6 h-6" />
        </div>
        <div className="text-right">
          <div className="flex items-center gap-2 justify-end mb-1">
            <span className={`w-2 h-2 rounded-full ${agent.status === 'idle' ? 'bg-zinc-400' : 'bg-emerald-500 animate-pulse'}`}></span>
            <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">{agent.status}</span>
          </div>
          <p className="text-[10px] font-bold text-zinc-400">v3.0.4-stable</p>
        </div>
      </div>

      <h3 className="text-lg font-black text-zinc-900 dark:text-zinc-50 mb-2 truncate uppercase">{agent.name}</h3>
      <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2 leading-relaxed mb-6 font-medium">
        {agent.description}
      </p>

      <div className="flex items-center justify-between">
        <div className="flex -space-x-2">
          {[1,2,3].map(i => (
            <div key={i} className="w-6 h-6 rounded-full border-2 border-white dark:border-zinc-900 bg-zinc-200 dark:bg-zinc-700"></div>
          ))}
        </div>
        <button className="flex items-center gap-2 text-[10px] font-black text-purple-600 dark:text-purple-400 uppercase tracking-widest hover:underline">
          <Settings className="w-3 h-3" />
          Settings
        </button>
      </div>

      <AnimatePresence>
        {isSelected && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-6 pt-6 border-t border-zinc-200 dark:border-zinc-800 space-y-4"
          >
            <div className="flex gap-2">
              <button className="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2">
                <Play className="w-3 h-3 fill-current" /> Run Test
              </button>
              <button className="p-3 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded-xl transition-all">
                <Settings className="w-4 h-4" />
              </button>
            </div>
            <div className="bg-zinc-100 dark:bg-zinc-800/50 p-4 rounded-2xl">
              <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2">Capabilities</p>
              <div className="flex flex-wrap gap-2">
                {agent.capabilities?.map((cap: string) => (
                  <span key={cap} className="px-2 py-1 bg-white dark:bg-zinc-900 text-[9px] font-bold text-purple-600 dark:text-purple-400 rounded-md border border-purple-500/20">
                    {cap}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
