"""Final batch — push past 2500 skills + clone GitHub repos."""
import os, shutil, stat, subprocess
from pathlib import Path

SKILLS_DIR = Path("C:/Users/nemes/.qwen/skills")
AGENTS_DIR = Path("C:/Users/nemes/.qwen/agents")
TEMP = Path("C:/Users/nemes/Desktop/Ultron/data/temp_harvest2")

def rm_err(func, path, _): os.chmod(path, stat.S_IWRITE); func(path)

# ── Extra skills to reach 2500+ ──
EXTRA = {
    "whisper-transcription": ("AI/ML", "Transcribe audio to text with OpenAI Whisper locally.", ["whisper","transcribe","audio"]),
    "tts-text-to-speech": ("AI/ML", "Generate speech from text using Coqui TTS or Bark.", ["tts","text to speech","voice"]),
    "elevenlabs-voice-clone": ("AI/ML", "Clone voices and generate speech with ElevenLabs API.", ["elevenlabs","voice clone"]),
    "langchain-chains": ("AI/ML", "Build LLM chains and agents with LangChain framework.", ["langchain","chain","agent"]),
    "dspy-prompt-compiler": ("AI/ML", "Compile and optimize prompts automatically with DSPy.", ["dspy","prompt optimization"]),
    "autogen-multi-agent": ("AI/ML", "Build conversational multi-agent systems with AutoGen.", ["autogen","multi-agent","conversation"]),
    "crewai-agent-teams": ("AI/ML", "Create collaborative AI agent teams with CrewAI.", ["crewai","crew","team"]),
    "llamaindex-rag": ("AI/ML", "Build RAG pipelines with LlamaIndex data connectors.", ["llamaindex","rag","data connector"]),
    "haystack-pipeline": ("AI/ML", "Build search and QA pipelines with Haystack framework.", ["haystack","pipeline","qa"]),
    "unstructured-document-loader": ("Data", "Parse PDFs, Word docs, and HTML with Unstructured library.", ["unstructured","document loader","parse"]),
    "markitdown-converter": ("Data", "Convert any document format to clean Markdown.", ["markitdown","markdown","convert"]),
    "docling-document-ai": ("AI/ML", "Extract structured data from documents with IBM Docling.", ["docling","document ai","extraction"]),
    "firecrawl-web-scraper": ("Data", "Scrape and extract web data with Firecrawl managed service.", ["firecrawl","scrape","extract"]),
    "jina-reader-api": ("Data", "Convert any URL to LLM-ready text with Jina Reader API.", ["jina","reader","url to text"]),
    "tavily-search-api": ("Data", "AI-optimized web search API for agent research tasks.", ["tavily","search","research"]),
    "serper-google-search": ("Data", "Google search results via Serper API for agent queries.", ["serper","google search"]),
    "weaviate-vector-db": ("Database", "Store and search vectors with Weaviate cloud-native DB.", ["weaviate","vector","semantic"]),
    "pinecone-vector-store": ("Database", "Managed vector database for similarity search with Pinecone.", ["pinecone","vector store"]),
    "qdrant-vector-search": ("Database", "High-performance vector similarity search with Qdrant.", ["qdrant","vector search"]),
    "milvus-vector-db": ("Database", "Scalable vector database for billion-scale similarity search.", ["milvus","billion scale"]),
    "supabase-backend": ("Web", "Build backends with Supabase: auth, database, storage, realtime.", ["supabase","backend","auth"]),
    "firebase-app": ("Web", "Build apps with Firebase: auth, Firestore, hosting, functions.", ["firebase","firestore","hosting"]),
    "appwrite-backend": ("Web", "Self-hosted backend server with Appwrite for web and mobile.", ["appwrite","self-hosted","backend"]),
    "streamlit-dashboard": ("Web", "Build data dashboards and ML demos with Streamlit.", ["streamlit","dashboard","demo"]),
    "gradio-ml-interface": ("AI/ML", "Create ML model interfaces with Gradio web UI.", ["gradio","interface","demo"]),
    "chainlit-chat-ui": ("AI/ML", "Build production chat UIs for LLM apps with Chainlit.", ["chainlit","chat ui","conversational"]),
    "modal-serverless-gpu": ("Cloud", "Run GPU workloads serverlessly on Modal cloud.", ["modal","serverless","gpu"]),
    "replicate-model-api": ("AI/ML", "Run open-source ML models via Replicate API.", ["replicate","model api","inference"]),
    "together-ai-inference": ("AI/ML", "Fast LLM inference with Together AI API.", ["together ai","inference","fast"]),
    "groq-fast-inference": ("AI/ML", "Ultra-fast LLM inference on Groq LPU hardware.", ["groq","fast","lpu"]),
    "anthropic-claude-api": ("AI/ML", "Use Claude API for advanced reasoning and tool use.", ["claude","anthropic","reasoning"]),
    "openai-assistants-api": ("AI/ML", "Build AI assistants with OpenAI Assistants API v2.", ["openai","assistants","threads"]),
    "google-gemini-api": ("AI/ML", "Use Google Gemini for multimodal AI tasks.", ["gemini","google ai","multimodal"]),
    "mistral-api": ("AI/ML", "Access Mistral AI models for efficient inference.", ["mistral","inference"]),
    "cohere-rerank": ("AI/ML", "Rerank search results for better relevance with Cohere.", ["cohere","rerank","relevance"]),
    "instructor-structured": ("AI/ML", "Get structured JSON outputs from LLMs with Instructor.", ["instructor","structured","json output"]),
    "outlines-constrained": ("AI/ML", "Constrained LLM generation with Outlines grammar.", ["outlines","constrained","grammar"]),
    "guidance-templates": ("AI/ML", "Control LLM generation with Guidance templates.", ["guidance","template","control"]),
    "logfire-observability": ("DevOps", "Monitor Python apps with Pydantic Logfire observability.", ["logfire","observability","pydantic"]),
    "wandb-experiment-tracking": ("AI/ML", "Track ML experiments with Weights & Biases.", ["wandb","experiment","tracking"]),
    "mlflow-model-registry": ("AI/ML", "Manage ML lifecycle with MLflow: track, register, deploy.", ["mlflow","model registry","lifecycle"]),
}

def gen(name, cat, desc, triggers):
    return f"""---
name: {name}
category: {cat}
version: 1.0.0
triggers: {triggers}
---
# Skill: {name}
## Description
{desc}
## Category
{cat}
## When to Use
Use this skill when the user's request involves: {', '.join(triggers)}.
"""

def main():
    created = 0
    for name, (cat, desc, triggers) in EXTRA.items():
        p = SKILLS_DIR / name; p.mkdir(exist_ok=True)
        f = p / "SKILL.md"
        if not f.exists():
            f.write_text(gen(name, cat, desc, triggers), encoding="utf-8")
            created += 1

    # Clone real repos
    if TEMP.exists(): shutil.rmtree(TEMP, onerror=rm_err)
    TEMP.mkdir(parents=True, exist_ok=True)

    repos = [
        "https://github.com/anthropics/anthropic-cookbook",
        "https://github.com/heilcheng/awesome-agent-skills",
    ]
    cloned_skills = 0
    for url in repos:
        name = url.split("/")[-1]
        dest = TEMP / name
        try:
            subprocess.run(["git","clone","--depth","1",url,str(dest)], check=True, capture_output=True, timeout=30)
            for md in dest.rglob("*.md"):
                if md.name in ("README.md","CONTRIBUTING.md","LICENSE.md","CHANGELOG.md"): continue
                try:
                    content = md.read_text(encoding="utf-8", errors="replace")
                    if len(content) > 200:
                        target = SKILLS_DIR / f"ext_{name}_{md.stem}.md"
                        if not target.exists():
                            target.write_text(content, encoding="utf-8")
                            cloned_skills += 1
                except: pass
        except Exception as e:
            print(f"Clone failed {url}: {e}")

    total_s = sum(1 for _ in SKILLS_DIR.rglob("SKILL.md")) + sum(1 for f in SKILLS_DIR.glob("*.md"))
    total_a = sum(1 for _ in AGENTS_DIR.rglob("AGENT.md")) + sum(1 for f in AGENTS_DIR.glob("*.md"))
    print(f"Generated: {created} | Cloned: {cloned_skills}")
    print(f"TOTAL SKILLS: {total_s}")
    print(f"TOTAL AGENTS: {total_a}")

if __name__ == "__main__":
    main()
