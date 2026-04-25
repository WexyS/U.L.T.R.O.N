import React, { useState, useEffect } from 'react';
import { Zap, Activity, Shield, Code, Cpu, Timer, CheckCircle2, AlertCircle, RefreshCw, GitBranch, Bot } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from '../config';

interface EvolutionStats {
  enabled: boolean;
  allow_git: boolean;
  interval: string;
  current_state: 'idle' | 'thinking' | 'implementing' | 'success' | 'failed_tests';
  last_vision: any;
  active_agents: string[];
  last_cycle_time: string | null;
}

export default function EvolutionMonitor() {
  const [stats, setStats] = useState<EvolutionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v2/status/evolution`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error("Failed to fetch evolution stats:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const triggerEvolution = async () => {
    setRefreshing(true);
    try {
      await fetch(`${API_URL}/api/v2/workspace/evolve`, { method: 'POST' });
      fetchStats();
    } catch (error) {
      console.error("Failed to trigger evolution:", error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="w-8 h-8 text-purple-500 animate-spin" />
      </div>
    );
  }

  const getStatusColor = (state: string) => {
    switch (state) {
      case 'thinking': return 'text-amber-500 bg-amber-500/10';
      case 'implementing': return 'text-blue-500 bg-blue-500/10';
      case 'success': return 'text-emerald-500 bg-emerald-500/10';
      case 'failed_tests': return 'text-rose-500 bg-rose-500/10';
      default: return 'text-zinc-500 bg-zinc-500/10';
    }
  };

  return (
    <div className="h-full overflow-y-auto p-8 bg-white dark:bg-[#0A0A0A] space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-white">Eternal Evolution</h2>
          </div>
          <p className="text-zinc-500 dark:text-zinc-400 max-w-2xl">
            Ultron's autonomous self-improvement engine. Observe the Catalyst's vision and the system's growth in real-time.
          </p>
        </div>

        <button
          onClick={triggerEvolution}
          disabled={refreshing || stats?.current_state !== 'idle'}
          className="flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-2xl transition-all shadow-lg shadow-purple-500/20"
        >
          <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
          Force Evolution
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Status Card */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="lg:col-span-2 p-8 rounded-[2rem] bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800 relative overflow-hidden"
        >
          <div className="relative z-10 space-y-6">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold uppercase tracking-widest text-zinc-400">Current Phase</span>
              <div className={`px-4 py-1 rounded-full text-xs font-black uppercase tracking-tighter ${getStatusColor(stats?.current_state || 'idle')}`}>
                {stats?.current_state || 'IDLE'}
              </div>
            </div>

            <AnimatePresence mode="wait">
              {stats?.last_vision ? (
                <motion.div 
                  key={stats.last_vision.vision}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="space-y-4"
                >
                  <h3 className="text-2xl font-bold text-zinc-900 dark:text-white">{stats.last_vision.vision}</h3>
                  <p className="text-lg text-zinc-600 dark:text-zinc-400 leading-relaxed">
                    {stats.last_vision.rationale}
                  </p>
                  
                  <div className="flex flex-wrap gap-2 pt-4">
                    {stats.active_agents.map((agent) => (
                      <div key={agent} className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                        <Bot className="w-4 h-4 text-purple-500" />
                        {agent}
                      </div>
                    ))}
                  </div>
                </motion.div>
              ) : (
                <div className="py-12 text-center text-zinc-500">
                  <Activity className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>No active vision. Catalyst is observing...</p>
                </div>
              )}
            </AnimatePresence>
          </div>

          {/* Animated Background Pulse if active */}
          {stats?.current_state !== 'idle' && (
            <motion.div 
              animate={{ 
                scale: [1, 1.2, 1],
                opacity: [0.1, 0.2, 0.1]
              }}
              transition={{ duration: 4, repeat: Infinity }}
              className="absolute -right-20 -top-20 w-80 h-80 bg-purple-600 rounded-full blur-[100px]"
            />
          )}
        </motion.div>

        {/* Info Sidebar */}
        <div className="space-y-6">
          {/* Config Card */}
          <div className="p-6 rounded-[2rem] bg-zinc-900 text-white space-y-6">
            <h4 className="font-bold flex items-center gap-2">
              <Cpu className="w-5 h-5 text-purple-400" />
              Engine Configuration
            </h4>
            
            <div className="space-y-4">
              <div className="flex justify-between items-center text-sm">
                <span className="text-zinc-400 font-medium">Auto-Evolve</span>
                <span className={stats?.enabled ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                  {stats?.enabled ? 'ENABLED' : 'DISABLED'}
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-zinc-400 font-medium">Git Protection</span>
                <span className={stats?.allow_git ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                  {stats?.allow_git ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-zinc-400 font-medium">Scan Interval</span>
                <div className="flex items-center gap-2 font-bold">
                  <Timer className="w-4 h-4" />
                  {stats?.interval}m
                </div>
              </div>
            </div>
          </div>

          {/* Timeline Hint */}
          <div className="p-6 rounded-[2rem] bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800">
            <div className="flex items-center gap-2 mb-4">
              <GitBranch className="w-5 h-5 text-blue-500" />
              <h4 className="font-bold text-zinc-900 dark:text-white">Last Activity</h4>
            </div>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              {stats?.last_cycle_time ? new Date(stats.last_cycle_time).toLocaleString() : 'Waiting for first cycle...'}
            </p>
          </div>
        </div>
      </div>

      {/* Progress Steps (Visual only) */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { icon: Zap, label: 'Brainstorming', active: stats?.current_state === 'thinking' },
          { icon: Shield, label: 'Architect Review', active: stats?.current_state === 'thinking' },
          { icon: Code, label: 'Implementation', active: stats?.current_state === 'implementing' },
          { icon: CheckCircle2, label: 'Verification', active: stats?.current_state === 'success' }
        ].map((step, i) => (
          <div 
            key={i}
            className={`p-4 rounded-2xl flex items-center gap-3 transition-all ${
              step.active 
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20' 
                : 'bg-zinc-100 dark:bg-zinc-900 text-zinc-400'
            }`}
          >
            <step.icon className={`w-5 h-5 ${step.active ? 'animate-pulse' : ''}`} />
            <span className="text-sm font-bold">{step.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
