import { useState, useEffect } from 'react';
import { Book, Search, Puzzle, ExternalLink, Download, Zap, Terminal } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from '../config';

interface Skill {
  name: string;
  description: string;
  path: string;
  source: string;
}

export default function SkillsPanel() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [externalAgents, setExternalAgents] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'skills' | 'agents'>('skills');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [skillsRes, agentsRes] = await Promise.all([
          fetch(`${API_URL}/api/v3/skills`),
          fetch(`${API_URL}/api/v3/external-agents`)
        ]);
        
        const [skillsData, agentsData] = await Promise.all([
          skillsRes.json(),
          agentsRes.json()
        ]);

        setSkills(skillsData);
        setExternalAgents(agentsData);
      } catch (err) {
        console.error('Failed to fetch skills:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const filteredItems = (activeTab === 'skills' ? skills : externalAgents).filter(item =>
    item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-full bg-zinc-50 dark:bg-[#121212] overflow-y-auto">
      {/* Header */}
      <div className="px-8 py-6 border-b border-zinc-200 dark:border-zinc-800/50 backdrop-blur-md sticky top-0 z-10 bg-zinc-50/80 dark:bg-[#121212]/80">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Book className="w-6 h-6 text-indigo-500" />
            <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Ultron Skill Nexus</h2>
          </div>
          <div className="flex gap-2 p-1 bg-zinc-100 dark:bg-zinc-800 rounded-xl">
            <button
              onClick={() => setActiveTab('skills')}
              className={`px-4 py-1.5 text-xs font-bold rounded-lg transition-all ${
                activeTab === 'skills' 
                  ? 'bg-white dark:bg-zinc-700 shadow-sm text-zinc-900 dark:text-zinc-50' 
                  : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'
              }`}
            >
              SKILLS ({skills.length})
            </button>
            <button
              onClick={() => setActiveTab('agents')}
              className={`px-4 py-1.5 text-xs font-bold rounded-lg transition-all ${
                activeTab === 'agents' 
                  ? 'bg-white dark:bg-zinc-700 shadow-sm text-zinc-900 dark:text-zinc-50' 
                  : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'
              }`}
            >
              EXTERNAL AGENTS ({externalAgents.length})
            </button>
          </div>
        </div>

        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <input
            type="text"
            placeholder={`Search ${activeTab === 'skills' ? 'skills' : 'external agents'}...`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all text-sm"
          />
        </div>
      </div>

      <div className="p-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
            <p className="text-sm font-medium text-zinc-500 animate-pulse">Scanning ClawHub & local repositories...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="text-center py-20">
            <Puzzle className="w-12 h-12 text-zinc-200 dark:text-zinc-800 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-zinc-400 dark:text-zinc-600">No matches found</h3>
            <p className="text-sm text-zinc-500">Try adjusting your search query or installing new skills.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredItems.map((item) => (
              <motion.div
                key={item.path}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ y: -4 }}
                className="group p-5 bg-white dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800 rounded-2xl hover:border-indigo-500/50 hover:shadow-xl transition-all"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className={`p-3 rounded-xl ${activeTab === 'skills' ? 'bg-indigo-500/10 text-indigo-500' : 'bg-purple-500/10 text-purple-500'}`}>
                    {activeTab === 'skills' ? <Puzzle className="w-5 h-5" /> : <Terminal className="w-5 h-5" />}
                  </div>
                  <div className="flex gap-2">
                    <button className="p-2 bg-zinc-50 dark:bg-zinc-800 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-400 hover:text-zinc-600 transition-colors">
                      <ExternalLink className="w-4 h-4" />
                    </button>
                    <button className="p-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 shadow-lg shadow-indigo-500/20 transition-all">
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <h3 className="font-bold text-zinc-900 dark:text-zinc-100 mb-2 truncate group-hover:text-indigo-500 transition-colors">
                  {item.name}
                </h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-3 leading-relaxed mb-4 h-12">
                  {item.description}
                </p>

                <div className="pt-4 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between text-[10px]">
                  <span className="font-bold text-zinc-400 uppercase tracking-widest">
                    {item.source.includes('clawhub') ? 'CLAW HUB' : 'LOCAL REPO'}
                  </span>
                  <div className="flex items-center gap-1 text-emerald-500">
                    <Zap className="w-3 h-3 fill-current" />
                    <span className="font-bold">READY</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Info Card */}
        <div className="mt-12 p-8 bg-gradient-to-br from-indigo-600 to-purple-700 rounded-3xl text-white shadow-2xl shadow-indigo-500/20 relative overflow-hidden group">
          <div className="relative z-10">
            <h3 className="text-xl font-black mb-2 flex items-center gap-2">
              <Zap className="w-6 h-6 fill-amber-400 text-amber-400" />
              Dynamic Skill Injection
            </h3>
            <p className="text-sm text-indigo-100 max-w-xl mb-6">
              Ultron automatically detects new skills and agents in your workspace. 
              Add a folder with a <code className="bg-white/10 px-1.5 py-0.5 rounded text-white">SKILL.md</code> or <code className="bg-white/10 px-1.5 py-0.5 rounded text-white">AGENT.md</code> file to any indexed directory to instantly expand your AGI's capabilities.
            </p>
            <button className="px-6 py-2.5 bg-white text-indigo-600 font-bold rounded-xl hover:bg-zinc-100 transition-all text-sm shadow-xl">
              OPEN SKILLS DIRECTORY
            </button>
          </div>
          <div className="absolute right-[-50px] top-[-50px] w-64 h-64 bg-white/10 rounded-full blur-3xl group-hover:bg-white/20 transition-all duration-700"></div>
        </div>
      </div>
    </div>
  );
}
