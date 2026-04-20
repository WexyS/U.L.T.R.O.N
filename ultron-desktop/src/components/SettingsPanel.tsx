import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Settings, Bell, Shield, Cpu, Volume2, Globe, 
  Moon, Sun, Save, RefreshCcw, Zap, Search
} from 'lucide-react';

interface SettingsPanelProps {
  onClose?: () => void;
}

export default function SettingsPanel({ onClose }: SettingsPanelProps) {
  const [settings, setSettings] = useState({
    theme: localStorage.getItem('ultron-theme') || 'dark',
    autonomousEvolution: localStorage.getItem('ultron-auto-evolution') === 'true',
    voiceMode: localStorage.getItem('ultron-voice-mode') === 'true',
    searchDepth: parseInt(localStorage.getItem('ultron-search-depth') || '2'),
    model: localStorage.getItem('ultron-model') || 'qwen2.5:32b',
    notifications: true,
  });

  const saveSettings = () => {
    localStorage.setItem('ultron-theme', settings.theme);
    localStorage.setItem('ultron-auto-evolution', String(settings.autonomousEvolution));
    localStorage.setItem('ultron-voice-mode', String(settings.voiceMode));
    localStorage.setItem('ultron-search-depth', String(settings.searchDepth));
    localStorage.setItem('ultron-model', settings.model);
    alert('Settings saved successfully! Some changes may require a restart.');
  };

  const handleChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="h-full flex flex-col bg-white dark:bg-zinc-950">
      <div className="px-8 py-6 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-900/50">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-500">
            <Settings className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-zinc-900 dark:text-white">System Settings</h2>
        </div>
        <button 
          onClick={saveSettings}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-semibold transition-all shadow-lg shadow-indigo-500/20 active:scale-95"
        >
          <Save className="w-4 h-4" />
          Save Changes
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-8 space-y-10 scrollbar-premium">
        {/* General Section */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 text-zinc-400 font-bold text-xs uppercase tracking-widest px-2">
            <Globe className="w-4 h-4" />
            General
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-zinc-700 dark:text-zinc-300">Appearance</span>
                <div className="flex p-1 bg-zinc-200 dark:bg-zinc-800 rounded-lg">
                  <button 
                    onClick={() => handleChange('theme', 'light')}
                    className={`p-1.5 rounded-md transition-all ${settings.theme === 'light' ? 'bg-white shadow-sm text-zinc-900' : 'text-zinc-500'}`}
                  >
                    <Sun className="w-4 h-4" />
                  </button>
                  <button 
                    onClick={() => handleChange('theme', 'dark')}
                    className={`p-1.5 rounded-md transition-all ${settings.theme === 'dark' ? 'bg-zinc-700 shadow-sm text-white' : 'text-zinc-500'}`}
                  >
                    <Moon className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <p className="text-xs text-zinc-500">Toggle between light and dark theme aesthetic.</p>
            </div>

            <div className="p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-zinc-700 dark:text-zinc-300">Voice Mode</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input 
                    type="checkbox" 
                    className="sr-only peer" 
                    checked={settings.voiceMode}
                    onChange={(e) => handleChange('voiceMode', e.target.checked)}
                  />
                  <div className="w-11 h-6 bg-zinc-200 peer-focus:outline-none dark:bg-zinc-800 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
              <p className="text-xs text-zinc-500">Enable or disable the real-time voice assistant.</p>
            </div>
          </div>
        </section>

        {/* Intelligence Section */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 text-zinc-400 font-bold text-xs uppercase tracking-widest px-2">
            <Cpu className="w-4 h-4" />
            Intelligence
          </div>
          <div className="space-y-4">
            <div className="p-6 rounded-2xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h4 className="font-semibold text-zinc-900 dark:text-white">Active LLM Model</h4>
                  <p className="text-sm text-zinc-500">Select the primary brain for Ultron.</p>
                </div>
                <select 
                  className="bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-xl px-4 py-2 text-sm font-medium focus:ring-2 focus:ring-indigo-500 outline-none"
                  value={settings.model}
                  onChange={(e) => handleChange('model', e.target.value)}
                >
                  <option value="qwen2.5:14b">Qwen 2.5 14B (Fast)</option>
                  <option value="qwen2.5:32b">Qwen 2.5 32B (Balanced)</option>
                  <option value="qwen2.5:72b">Qwen 2.5 72B (Powerful)</option>
                  <option value="gemini-2.0-flash">Gemini 2.0 Flash (Remote)</option>
                  <option value="gpt-4o">GPT-4o (Premium)</option>
                </select>
              </div>

              <div className="h-px bg-zinc-100 dark:bg-zinc-800 my-4" />

              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-zinc-900 dark:text-white">Eternal Evolution</h4>
                  <p className="text-sm text-zinc-500">Allow Ultron to autonomously improve its own code.</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input 
                    type="checkbox" 
                    className="sr-only peer" 
                    checked={settings.autonomousEvolution}
                    onChange={(e) => handleChange('autonomousEvolution', e.target.checked)}
                  />
                  <div className="w-11 h-6 bg-zinc-200 peer-focus:outline-none dark:bg-zinc-800 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Search className="w-5 h-5 text-indigo-500" />
                  <h4 className="font-semibold text-zinc-900 dark:text-white">Research Depth</h4>
                </div>
                <span className="text-sm font-bold text-indigo-500 px-3 py-1 bg-indigo-500/10 rounded-lg">{settings.searchDepth} Levels</span>
              </div>
              <input 
                type="range" 
                min="1" 
                max="5" 
                step="1"
                className="w-full h-2 bg-zinc-200 dark:bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                value={settings.searchDepth}
                onChange={(e) => handleChange('searchDepth', parseInt(e.target.value))}
              />
              <div className="flex justify-between text-[10px] font-bold text-zinc-500 mt-2 uppercase tracking-tighter">
                <span>Fast Surface</span>
                <span>Deep Dive Analysis</span>
              </div>
            </div>
          </div>
        </section>

        {/* Danger Zone */}
        <section className="pt-6 border-t border-zinc-200 dark:border-zinc-800">
          <div className="p-4 rounded-2xl bg-red-500/5 border border-red-500/20 flex items-center justify-between">
            <div>
              <h4 className="font-semibold text-red-600 dark:text-red-400">Factory Reset</h4>
              <p className="text-xs text-zinc-500">Clear all memory, profiles and conversation history.</p>
            </div>
            <button 
              onClick={() => confirm('Are you sure you want to reset EVERYTHING?') && alert('Resetting...')}
              className="px-4 py-2 bg-red-600/10 hover:bg-red-600 text-red-600 hover:text-white rounded-xl text-xs font-bold transition-all border border-red-600/20"
            >
              Reset System
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
