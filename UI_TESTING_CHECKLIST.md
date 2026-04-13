# Ultron v2.1 - UI Testing Checklist ✅

**Date:** 13 Nisan 2026  
**Purpose:** Verify all UI enhancements work correctly

---

## 🚀 **Quick Start**

### **1. Start Backend (Terminal 1)**
```bash
cd c:\Users\nemes\Desktop\Ultron
.venv\Scripts\activate
python -m uvicorn ultron.api.main:app --host 127.0.0.1 --port 8000 --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### **2. Start Frontend (Terminal 2)**
```bash
cd c:\Users\nemes\Desktop\Ultron\ultron-desktop
npm install  # Only first time
npm run dev
```

**Expected Output:**
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

### **3. Open Browser**
Navigate to: **http://localhost:5173**

---

## ✅ **Testing Checklist**

### **A. Visual Design & Animations**

- [ ] **Welcome Screen Loads**
  - Animated gradient logo (pulsing effect)
  - "Ultron v2.1" title with gradient text
  - 4 capability cards (Chat, Code, Research, Agents)
  - Model info displayed at bottom

- [ ] **Theme Toggle Works**
  - Click sun/moon icon in top-right
  - Smooth transition between light/dark modes
  - Theme persists after page refresh

- [ ] **Animations Are Smooth**
  - Messages fade in when appearing
  - Buttons have hover effects
  - Panels slide open/closed smoothly

---

### **B. Chat Interface**

- [ ] **Send a Message**
  - Type "Hello, how are you?" in input box
  - Press Enter or click Send button
  - See your message appear in chat bubble (green/teal)

- [ ] **Streaming Response**
  - Watch for typing indicator (3 bouncing dots)
  - Response should stream token-by-token
  - Blinking cursor visible during streaming
  - "Ultron is thinking..." text appears

- [ ] **Message Actions (Hover over assistant message)**
  - [ ] **Copy button** - Click it, see checkmark ✓
  - [ ] **Regenerate button** - Visible on hover
  - [ ] **TTS button** - Speaker icon, should read message
  - [ ] **Thumbs up/down** - Click to give feedback, see color change

- [ ] **Timestamps**
  - Each message shows time (e.g., "2:45 PM")

---

### **C. Code Block Features**

**Test this by asking:** "Write a JavaScript function to add two numbers"

- [ ] **Syntax Highlighting**
  - Code should have colors (oneDark theme)
  - Language label visible (e.g., "javascript")
  - Line numbers on left side

- [ ] **Copy Button**
  - Click "Copy" in code header
  - See "Copied!" confirmation with checkmark

- [ ] **Run Button** (for JavaScript)
  - Click "Run" button
  - Should see output below code block
  - Output shows: ✅ Output: followed by result

**Test this by asking:** "Create a simple HTML page with a heading"

- [ ] **HTML Execution**
  - Click "Run" on HTML code
  - Should open in new window
  - See rendered HTML page

---

### **D. Conversation Sidebar**

- [ ] **Open Conversation Sidebar**
  - Click "Conversations" button in left sidebar
  - OR click MessageSquare icon in header
  - Sidebar should slide in from left

- [ ] **Create New Conversation**
  - Click "New Chat" button (gradient blue)
  - Should create new conversation
  - Chat area clears

- [ ] **Conversation List**
  - See conversations grouped by time:
    - Last hour
    - Today
    - Yesterday
    - Last 7 days
    - etc.

- [ ] **Search Conversations**
  - Type in search box at top
  - Conversations filter in real-time
  - "No conversations found" if no match

- [ ] **Select Conversation**
  - Click on a conversation
  - Should switch to that conversation
  - Sidebar closes

- [ ] **Rename Conversation**
  - Hover over conversation
  - Click ⋮ (three dots) menu
  - Click "Rename"
  - Edit title, press Enter to save
  - Should update immediately

- [ ] **Delete Conversation**
  - Hover over conversation
  - Click ⋮ menu
  - Click "Delete"
  - Should remove from list

- [ ] **Conversation Metadata**
  - See message count (e.g., "5 msgs")
  - See time ago (e.g., "2h ago")

- [ ] **LocalStorage Persistence**
  - Create a conversation
  - Refresh browser page (F5)
  - Conversations should still be there

---

### **E. Panels Navigation**

- [ ] **Switch Between Panels**
  - Click "💬 Chat" - see chat interface
  - Click "🗂️ Workspace" - see workspace panel
  - Click "🤖 Agents" - see agents panel
  - Click "🎓 Training" - see training panel

- [ ] **Toggle Inspector Panel**
  - Click panel icon in top-right
  - Should slide open/close from right
  - Shows status, providers, workspace info

---

### **F. Responsive Design**

- [ ] **Resize Browser Window**
  - Make window narrow (mobile size)
  - Sidebar should become overlay
  - Touch targets should be large enough

- [ ] **Conversation Sidebar on Mobile**
  - Should show backdrop overlay
  - Click backdrop to close

---

### **G. Error Handling**

- [ ] **Backend Not Running**
  - Stop backend server
  - Send a message
  - Should see error banner: "Connection failed"

- [ ] **Reconnection**
  - Restart backend
  - Should automatically reconnect
  - Status badge turns green

---

## 🐛 **Known Issues to Watch For**

1. **TypeScript Errors on First Build**
   - Run `npm install` if packages missing
   - Specifically: `remark-gfm`, `react-syntax-highlighter`

2. **CORS Errors**
   - Backend must be running on port 8000
   - Check browser console (F12) for errors

3. **TTS Not Working**
   - Requires backend TTS endpoint
   - Will show error if not available

4. **Code Run Button Limited**
   - Only works for JavaScript, HTML, Python, CSS
   - Other languages show message

---

## 📊 **Expected Results**

### **Performance Metrics:**
- Page load: < 2 seconds
- Message send: < 100ms latency
- Streaming start: < 500ms
- Animation FPS: 60fps (smooth)

### **Visual Quality:**
- No layout shifts
- Smooth transitions (no jank)
- Proper color contrast
- Readable font sizes

---

## ✅ **Success Criteria**

**UI is ready if:**
- ✅ All animations work smoothly
- ✅ Code blocks render with syntax highlighting
- ✅ Can copy/run code
- ✅ Conversation sidebar works
- ✅ Theme toggle persists
- ✅ No console errors (except expected CORS when backend off)

---

## 🎯 **Comparison Test (Optional)**

Open these side-by-side with Ultron:
- **Claude:** claude.ai
- **ChatGPT:** chat.openai.com
- **Gemini:** gemini.google.com

**Compare:**
- Streaming smoothness
- Code block quality
- Message actions
- Overall design polish

---

## 📝 **Testing Report Template**

After testing, fill this out:

```
UI Test Report - [Date]

✅ Working:
- [List features that work perfectly]

⚠️ Needs Improvement:
- [List minor issues]

❌ Broken:
- [List critical issues]

Overall Rating: [1-10]

Comparison to Claude: [Better/Same/Worse]
Comparison to ChatGPT: [Better/Same/Worse]
Comparison to Gemini: [Better/Same/Worse]
```

---

**Ready to test? Let me know if you encounter any issues!**
