import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, StopCircle, Download, RefreshCw, Cpu, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import { API_URL } from '../config';

interface TrainingJob {
  id: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  config: {
    base_model: string;
    method: string;
    num_epochs: number;
    learning_rate: number;
  };
  logs: string[];
  error: string | null;
}

interface TrainingStatus {
  total_jobs: number;
  active_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  is_training: boolean;
  supported_models: string[];
  methods: Record<string, { vram: string; quality: string; speed: string }>;
}

export default function TrainingPanel() {
  const [status, setStatus] = useState<TrainingStatus | null>(null);
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [baseModel, setBaseModel] = useState('meta-llama/Llama-3.1-8B');
  const [method, setMethod] = useState('qlora');
  const [epochs, setEpochs] = useState(3);
  const [learningRate, setLearningRate] = useState(0.0002);
  const [batchSize, setBatchSize] = useState(4);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v2/training/status`);
      if (!res.ok) throw new Error('Failed to fetch training status');
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v2/training/jobs`);
      if (!res.ok) throw new Error('Failed to fetch jobs');
      const data = await res.json();
      setJobs(data.jobs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchJobs();
    const interval = setInterval(() => {
      fetchStatus();
      fetchJobs();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStartTraining = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v2/training/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_model: baseModel,
          dataset: 'data/ultron_training.json',
          method,
          output_dir: `output/ultron_${method}_${Date.now()}`,
          num_epochs: epochs,
          learning_rate: learningRate,
          batch_size: batchSize,
          use_deepspeed: false,
          template: 'llama3',
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to start training');
      }

      await fetchJobs();
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleStopTraining = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v2/training/stop`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to stop training');
      await fetchJobs();
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6" style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text)' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>Ultron Neural Lab</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>Ultron-Native Neural Core Fine-Tuning Engine</p>
        </div>
        <button
          onClick={() => { fetchStatus(); fetchJobs(); }}
          className="p-2 rounded-lg hover:opacity-80 transition-colors"
          style={{ backgroundColor: 'var(--color-bg-tertiary)' }}
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Stats */}
      {status && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)' }}>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Total Jobs</p>
            <p className="text-2xl font-bold mt-1" style={{ color: 'var(--color-text)' }}>{status.total_jobs}</p>
          </div>
          <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)' }}>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Active</p>
            <p className="text-2xl font-bold mt-1" style={{ color: 'var(--color-accent)' }}>{status.active_jobs}</p>
          </div>
          <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)' }}>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Completed</p>
            <p className="text-2xl font-bold mt-1" style={{ color: 'var(--color-success)' }}>{status.completed_jobs}</p>
          </div>
          <div className="p-4 rounded-lg border" style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)' }}>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Failed</p>
            <p className="text-2xl font-bold mt-1" style={{ color: 'var(--color-danger)' }}>{status.failed_jobs}</p>
          </div>
        </div>
      )}

      {/* Training Form */}
      <div className="p-6 rounded-xl border mb-6" style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
        <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--color-text)' }}>Start New Training</h2>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>Base Model</label>
            <select
              value={baseModel}
              onChange={(e) => setBaseModel(e.target.value)}
              className="w-full rounded-lg border px-3 py-2"
              style={{ backgroundColor: 'var(--color-bg)', borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
            >
              <option value="meta-llama/Llama-3.1-8B">Llama 3.1 8B</option>
              <option value="meta-llama/Llama-3.1-70B">Llama 3.1 70B</option>
              <option value="Qwen/Qwen2.5-7B">Qwen 2.5 7B</option>
              <option value="Qwen/Qwen2.5-72B">Qwen 2.5 72B</option>
              <option value="mistralai/Mistral-7B-v0.3">Mistral 7B</option>
              <option value="google/gemma-2-9b">Gemma 2 9B</option>
            </select>
          </div>

          <div>
            <label className="block text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>Method</label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="w-full rounded-lg border px-3 py-2"
              style={{ backgroundColor: 'var(--color-bg)', borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
            >
              <option value="qlora">QLoRA (6GB VRAM, Fast)</option>
              <option value="lora">LoRA (8GB VRAM, Fast)</option>
              <option value="full">Full (80GB+ VRAM, Slow)</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>Epochs</label>
            <input
              type="number"
              value={epochs}
              onChange={(e) => setEpochs(Number(e.target.value))}
              className="w-full rounded-lg border px-3 py-2"
              style={{ backgroundColor: 'var(--color-bg)', borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
              min={1}
              max={10}
            />
          </div>

          <div>
            <label className="block text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>Learning Rate</label>
            <input
              type="number"
              value={learningRate}
              onChange={(e) => setLearningRate(Number(e.target.value))}
              className="w-full rounded-lg border px-3 py-2"
              style={{ backgroundColor: 'var(--color-bg)', borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
              step={0.00001}
              min={0.00001}
              max={0.001}
            />
          </div>

          <div>
            <label className="block text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>Batch Size</label>
            <input
              type="number"
              value={batchSize}
              onChange={(e) => setBatchSize(Number(e.target.value))}
              className="w-full rounded-lg border px-3 py-2"
              style={{ backgroundColor: 'var(--color-bg)', borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
              min={1}
              max={16}
            />
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleStartTraining}
            disabled={loading || status?.is_training}
            className="flex items-center gap-2 px-6 py-2.5 font-medium rounded-lg transition-all disabled:cursor-not-allowed text-white"
            style={{
              backgroundColor: loading || status?.is_training ? 'var(--color-border)' : 'var(--color-accent)',
            }}
          >
            {loading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
            {loading ? 'Starting...' : status?.is_training ? 'Training in Progress' : 'Start Training'}
          </button>

          {status?.is_training && (
            <button
              onClick={handleStopTraining}
              className="flex items-center gap-2 px-6 py-2.5 font-medium rounded-lg transition-all text-white"
              style={{ backgroundColor: 'var(--color-danger)' }}
            >
              <StopCircle className="w-5 h-5" />
              Stop Training
            </button>
          )}
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg border" style={{ backgroundColor: 'rgba(var(--color-danger), 0.1)', borderColor: 'rgb(var(--color-danger))' }}>
            <p className="text-sm" style={{ color: 'var(--color-danger)' }}>{error}</p>
          </div>
        )}
      </div>

      {/* Jobs List */}
      <div>
        <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--color-text)' }}>Training Jobs</h2>

        {jobs.length === 0 ? (
          <div className="p-8 rounded-xl border text-center" style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
            <Cpu className="w-12 h-12 mx-auto mb-3" style={{ color: 'var(--color-text-tertiary)' }} />
            <p style={{ color: 'var(--color-text-secondary)' }}>No training jobs yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => (
              <motion.div
                key={job.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 rounded-lg border"
                style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)' }}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    {job.status === 'completed' ? (
                      <CheckCircle className="w-5 h-5" style={{ color: 'var(--color-success)' }} />
                    ) : job.status === 'failed' ? (
                      <AlertCircle className="w-5 h-5" style={{ color: 'var(--color-danger)' }} />
                    ) : (
                      <Clock className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
                    )}
                    <div>
                      <p className="font-medium" style={{ color: 'var(--color-text)' }}>{job.config.base_model}</p>
                      <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{job.id}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span
                      className="px-2 py-1 rounded text-xs font-medium"
                      style={{
                        backgroundColor:
                          job.status === 'completed' ? 'rgba(var(--color-success), 0.2)' :
                          job.status === 'failed' ? 'rgba(var(--color-danger), 0.2)' :
                          'rgba(var(--color-accent), 0.2)',
                        color:
                          job.status === 'completed' ? 'var(--color-success)' :
                          job.status === 'failed' ? 'var(--color-danger)' :
                          'var(--color-accent)',
                      }}
                    >
                      {job.status}
                    </span>

                    <button
                      className="p-1.5 rounded hover:opacity-80 transition-colors"
                      style={{ backgroundColor: 'var(--color-bg-tertiary)' }}
                      title="Export model"
                    >
                      <Download className="w-4 h-4" style={{ color: 'var(--color-text-secondary)' }} />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p style={{ color: 'var(--color-text-muted)' }}>Method</p>
                    <p style={{ color: 'var(--color-text)' }}>{job.config.method}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--color-text-muted)' }}>Epochs</p>
                    <p style={{ color: 'var(--color-text)' }}>{job.config.num_epochs}</p>
                  </div>
                  <div>
                    <p style={{ color: 'var(--color-text-muted)' }}>Started</p>
                    <p style={{ color: 'var(--color-text)' }}>{new Date(job.created_at).toLocaleString()}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
