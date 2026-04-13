# Ultron v2.1 - Documentation

## 📚 Reports

- [Debugging Report](reports/DEBUGGING_REPORT.md) - All bugs found and fixed
- [Final Project Summary](reports/FINAL_PROJECT_SUMMARY.md) - Complete project overview
- [Phase B Summary](reports/PHASE_B_SUMMARY.md) - Autonomous learning system documentation
- [Test Results](reports/TEST_RESULTS.md) - Backend test results (8/8 passed)

## 📖 Guides

- [UI Enhancements](guides/UI_ENHANCEMENTS.md) - UI feature documentation
- [UI Testing Checklist](guides/UI_TESTING_CHECKLIST.md) - Complete UI testing guide

## 🚀 Quick Start

```bash
# Backend
cd c:\Users\nemes\Desktop\Ultron
.venv\Scripts\activate
python -m uvicorn ultron.api.main:app --host 127.0.0.1 --port 8000

# Frontend
cd ultron-desktop
npm run dev
```

## 📁 Project Structure

```
Ultron/
├── config/              # Configuration files
├── context/             # Session context
├── data/                # Runtime data & memory
├── docs/                # Documentation (this folder)
├── scripts/             # Utility scripts
├── tests/               # Test files
├── ultron/              # Backend source code
├── ultron-desktop/      # Frontend React app
├── workspace/           # Generated workspace items
├── .env.example         # Environment template
├── pyproject.toml       # Python dependencies
├── README.md            # Main documentation
└── start.bat            # Quick start script
```

---

**GitHub:** https://github.com/WexyS/U.L.T.R.O.N
