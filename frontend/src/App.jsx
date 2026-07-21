import React, { useState, useEffect } from 'react';
import { queryArchive } from './api';
import AuthScreen from './components/AuthScreen';
import ChatScreen from './components/ChatScreen';
import SettingsModal from './components/SettingsModal';
import HistoryModal from './components/HistoryModal';
import Lightbox from './components/Lightbox';

const DEFAULT_APIS = [
  { id: 'gemini', name: 'Gemini API', key: '', models: ['gemini-3.1-flash-lite', 'gemini-3.5-flash'] },
  { id: 'nim', name: 'Nvidia NIM API', key: '', models: ['deepseek-v4-flash', 'deepseek-v4-pro'] }
];

export default function App() {
  // --- STATE SYSTEM ---
  const [token, setToken] = useState(() => localStorage.getItem('pkq_token') || '');
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('pkq_theme') || 
      (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  });
  const [model, setModel] = useState(() => localStorage.getItem('pkq_model') || 'gemini-3.5-flash');
  
  const [apis, setApis] = useState(() => {
    try {
      const rawApis = localStorage.getItem('pkq_apis');
      return rawApis ? JSON.parse(rawApis) : DEFAULT_APIS;
    } catch (e) {
      return DEFAULT_APIS;
    }
  });

  const [simMode, setSimMode] = useState('normal');
  const [tokenStatus, setTokenStatus] = useState('');
  
  // Modals & Screen States
  const [screen, setScreen] = useState(token ? 'app' : 'auth');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [lightbox, setLightbox] = useState(null);

  // Session & Conversations States
  const [messages, setMessages] = useState(() => {
    try {
      const rawCurrent = sessionStorage.getItem('pkq_current');
      return rawCurrent ? JSON.parse(rawCurrent) : [];
    } catch (e) {
      return [];
    }
  });
  
  const [sessions, setSessions] = useState(() => {
    try {
      const rawHistory = sessionStorage.getItem('pkq_history');
      return rawHistory ? JSON.parse(rawHistory) : [];
    } catch (e) {
      return [];
    }
  });

  const [queryValue, setQueryValue] = useState('');
  const [pending, setPending] = useState(false);

  // Timer reference & counter tracking
  const timersRef = React.useRef([]);
  const tickIntervalRef = React.useRef(null);
  const uidRef = React.useRef(0);

  // --- INITIALIZE TIMER & LIFE CYCLE ---
  useEffect(() => {
    // Sync theme class with body element
    document.body.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    // Write sessions & current messages to sessionStorage
    try {
      sessionStorage.setItem('pkq_current', JSON.stringify(messages.filter(m => m.kind !== 'loading')));
      sessionStorage.setItem('pkq_history', JSON.stringify(sessions));
    } catch (e) {}

    // Track highest UID
    const ids = messages.map(m => m.id).filter(id => typeof id === 'number');
    if (ids.length) {
      uidRef.current = Math.max(...ids);
    }
  }, [messages, sessions]);

  // Clean up timers on unmount
  useEffect(() => {
    return () => {
      timersRef.current.forEach(clearTimeout);
      if (tickIntervalRef.current) clearInterval(tickIntervalRef.current);
    };
  }, []);

  const addTimeout = (fn, ms) => {
    const t = setTimeout(fn, ms);
    timersRef.current.push(t);
  };

  const clearAllTimers = () => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    if (tickIntervalRef.current) {
      clearInterval(tickIntervalRef.current);
      tickIntervalRef.current = null;
    }
  };

  const getNowFormattedTime = () => {
    return new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  };

  // --- BUSINESS LOGIC ---

  // Lockscreen Auth Unlock
  const handleUnlock = (cleanToken) => {
    localStorage.setItem('pkq_token', cleanToken);
    setToken(cleanToken);
    setTokenStatus('');
    setScreen('app');
  };

  // Archive current session
  const archiveCurrentIntoHistory = (currentSessions) => {
    const validMsgs = messages.filter(m => m.kind !== 'loading');
    if (!validMsgs.length) return currentSessions;
    
    const firstUserMsg = validMsgs.find(m => m.kind === 'user');
    const questionCount = validMsgs.filter(m => m.kind === 'user').length;
    
    const newSession = {
      id: 's' + Date.now() + '-' + Math.floor(Math.random() * 1e6),
      title: firstUserMsg ? firstUserMsg.text : 'Untitled session',
      count: questionCount,
      time: getNowFormattedTime(),
      messages: validMsgs
    };

    return [newSession, ...currentSessions];
  };

  // Start fresh conversation
  const handleNewQuestion = () => {
    clearAllTimers();
    setSessions(prev => archiveCurrentIntoHistory(prev));
    setMessages([]);
    setPending(false);
    setQueryValue('');
  };

  // Open past session
  const handleOpenSession = (sessionId) => {
    const targetSession = sessions.find(s => s.id === sessionId);
    if (!targetSession) return;
    
    clearAllTimers();
    const remainingSessions = sessions.filter(s => s.id !== sessionId);
    
    setSessions(archiveCurrentIntoHistory(remainingSessions));
    setMessages(targetSession.messages);
    setHistoryOpen(false);
    setPending(false);
  };

  // Delete past session
  const handleDeleteSession = (sessionId) => {
    setSessions(prev => prev.filter(s => s.id !== sessionId));
  };

  // Run Query
  const handleRunQuery = async (queryText, forceNormal = false) => {
    const mode = forceNormal ? 'normal' : simMode;
    const userMsgId = ++uidRef.current;
    const loadMsgId = ++uidRef.current;
    
    const userMsg = { id: userMsgId, kind: 'user', text: queryText, time: getNowFormattedTime() };
    const loadMsg = { id: loadMsgId, kind: 'loading', stage: 'search', coldStart: 0 };
    
    setMessages(prev => [...prev, userMsg, loadMsg]);
    setQueryValue('');
    setPending(true);
    setSimMode('normal'); // Reset simulator selection after query runs

    const replaceLoadingMessage = (replacementMsg) => {
      clearAllTimers();
      setMessages(prev => prev.map(m => m.id === loadMsgId ? { ...replacementMsg, id: loadMsgId } : m));
      setPending(false);
    };

    const triggerColdStartProgress = () => {
      const startTime = Date.now();
      setMessages(prev => prev.map(m => m.id === loadMsgId ? { ...m, stage: 'cold', coldStart: startTime, elapsed: '0S' } : m));
      
      tickIntervalRef.current = setInterval(() => {
        const elapsedSecs = Math.max(0, Math.floor((Date.now() - startTime) / 1000));
        setMessages(prev => prev.map(m => {
          if (m.id === loadMsgId) {
            return { ...m, elapsed: `${elapsedSecs}S` };
          }
          return m;
        }));
      }, 1000);
    };

    // Run simulated delay and API queries
    try {
      if (mode === 'reject') {
        addTimeout(() => {
          setTokenStatus('rejected');
          replaceLoadingMessage({
            kind: 'error',
            errKind: 'auth',
            query: queryText,
            errTitle: 'TOKEN REJECTED · 401',
            errBody: 'The backend refused your access token. It may have been rotated — paste the current one and ask again.'
          });
        }, 1200);
      } else if (mode === 'rate') {
        addTimeout(() => {
          replaceLoadingMessage({
            kind: 'error',
            errKind: 'rate',
            query: queryText,
            errTitle: 'RATE LIMITED · 429',
            errBody: 'The underlying API quota was hit. Your question is kept — wait a few seconds and retry.'
          });
        }, 1400);
      } else if (mode === 'down') {
        addTimeout(triggerColdStartProgress, 2000);
        addTimeout(() => {
          replaceLoadingMessage({
            kind: 'error',
            errKind: 'down',
            query: queryText,
            errTitle: 'BACKEND UNREACHABLE',
            errBody: 'No response — the backend never woke up. Check that it’s deployed and reachable, then retry. Your question is kept.'
          });
        }, 2000 + 8000); // 8s mock cold start duration
      } else if (mode === 'cold') {
        addTimeout(triggerColdStartProgress, 2000);
        addTimeout(async () => {
          try {
            const answer = await queryArchive(queryText, token, model, 'normal');
            replaceLoadingMessage(answer);
          } catch (e) {
            replaceLoadingMessage({
              kind: 'error',
              errKind: 'general',
              query: queryText,
              errTitle: 'QUERY ERROR',
              errBody: e.message || 'An error occurred while fetching search results.'
            });
          }
        }, 2000 + 8000);
      } else {
        // Normal execution
        addTimeout(async () => {
          try {
            const answer = await queryArchive(queryText, token, model, 'normal');
            replaceLoadingMessage(answer);
          } catch (e) {
            replaceLoadingMessage({
              kind: 'error',
              errKind: 'general',
              query: queryText,
              errTitle: 'QUERY ERROR',
              errBody: e.message || 'An error occurred while fetching search results.'
            });
          }
        }, 1800);
      }
    } catch (err) {
      replaceLoadingMessage({
        kind: 'error',
        errKind: 'general',
        query: queryText,
        errTitle: 'ERROR',
        errBody: err.message || 'Something went wrong.'
      });
    }
  };

  const handleRetryQuery = (errId, queryText) => {
    clearAllTimers();
    setMessages(prev => prev.filter(m => m.id !== errId));
    handleRunQuery(queryText, true);
  };

  // Toggle Theme between Light/Dark
  const handleToggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('pkq_theme', nextTheme);
    setTheme(nextTheme);
  };

  // Save token in Settings
  const handleSaveToken = (cleanToken) => {
    localStorage.setItem('pkq_token', cleanToken);
    setToken(cleanToken);
    setTokenStatus('');
  };

  // Forget Token (Lock Archive)
  const handleForgetToken = () => {
    localStorage.removeItem('pkq_token');
    setToken('');
    setTokenStatus('');
    setScreen('auth');
    setSettingsOpen(false);
    setMessages([]);
  };

  // Manage API list configurations
  const handleUpdateApis = (nextApis) => {
    localStorage.setItem('pkq_apis', JSON.stringify(nextApis));
    setApis(nextApis);

    // Fix active model if deleted
    const allModels = nextApis.flatMap(a => a.models);
    if (!allModels.includes(model)) {
      const nextModel = allModels[0] || '';
      localStorage.setItem('pkq_model', nextModel);
      setModel(nextModel);
    }
  };

  const handleSelectModel = (modelId) => {
    localStorage.setItem('pkq_model', modelId);
    setModel(modelId);
  };

  return (
    <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg)', color: 'var(--ink)' }}>
      {/* Auth Screen Locked View */}
      {screen === 'auth' && (
        <AuthScreen
          onUnlock={handleUnlock}
          authRejected={tokenStatus === 'rejected'}
        />
      )}

      {/* Main App Unlocked View */}
      {screen === 'app' && (
        <ChatScreen
          messages={messages}
          pending={pending}
          queryValue={queryValue}
          onQueryChange={(e) => setQueryValue(e.target.value)}
          onSubmitQuery={handleRunQuery}
          onNewQuestion={handleNewQuestion}
          onOpenHistory={() => setHistoryOpen(true)}
          onToggleTheme={handleToggleTheme}
          onOpenSettings={() => setSettingsOpen(true)}
          historyCount={sessions.length}
          modelShort={model.replace('gemini-', '').replace('deepseek-', '').toUpperCase()}
          onOpenLightbox={setLightbox}
          onRetryQuery={handleRetryQuery}
          onFixToken={() => { setSettingsOpen(true); }}
        />
      )}

      {/* Overlays / Modals */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        token={token}
        onSaveToken={handleSaveToken}
        onForgetToken={handleForgetToken}
        theme={theme}
        onSelectTheme={(t) => { localStorage.setItem('pkq_theme', t); setTheme(t); }}
        simMode={simMode}
        onSelectSimMode={setSimMode}
        apis={apis}
        onUpdateApis={handleUpdateApis}
        activeModel={model}
        onSelectModel={handleSelectModel}
        tokenRejected={tokenStatus === 'rejected'}
      />

      <HistoryModal
        isOpen={historyOpen}
        onClose={() => setHistoryOpen(false)}
        sessions={sessions}
        onOpenSession={handleOpenSession}
        onDeleteSession={handleDeleteSession}
      />

      <Lightbox
        isOpen={!!lightbox}
        img={lightbox}
        onClose={() => setLightbox(null)}
      />
    </div>
  );
}
