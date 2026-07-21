import React, { useEffect, useRef, useState } from 'react';

const TYPE_META = {
  note: { label: 'NOTE', color: 'var(--c-note)', fg: 'var(--ct-note)', bg: 'var(--cb-note)' },
  shot: { label: 'SCREENSHOT', color: 'var(--c-shot)', fg: 'var(--ct-shot)', bg: 'var(--cb-shot)' },
  post: { label: 'POST', color: 'var(--c-post)', fg: 'var(--ct-post)', bg: 'var(--cb-post)' },
  file: { label: 'FILE', color: 'var(--c-file)', fg: 'var(--ct-file)', bg: 'var(--cb-file)' }
};

export default function ChatScreen({
  messages,
  pending,
  queryValue,
  onQueryChange,
  onSubmitQuery,
  onNewQuestion,
  onOpenHistory,
  onToggleTheme,
  onOpenSettings,
  historyCount,
  modelShort,
  onOpenLightbox,
  onRetryQuery,
  onFixToken
}) {
  const [barVisible, setBarVisible] = useState(() => {
    try {
      return sessionStorage.getItem('pkq_bar') !== 'hidden';
    } catch (e) {
      return true;
    }
  });

  const [openSources, setOpenSources] = useState({});
  const [activeSources, setActiveSources] = useState({});

  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  // Auto scroll to bottom when messages list size changes
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, pending]);

  // Focus input on load
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const handleDismissBar = () => {
    try {
      sessionStorage.setItem('pkq_bar', 'hidden');
    } catch (e) {}
    setBarVisible(false);
  };

  const handleToggleSources = (msgId) => {
    setOpenSources(prev => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  const handleSelectSource = (msgId, index) => {
    setActiveSources(prev => ({
      ...prev,
      [msgId]: index
    }));
  };

  const renderAnswerContent = (text) => {
    const parts = [];
    const re = /\[(\d+)\]/g;
    let lastIndex = 0;
    let match;
    while ((match = re.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(<span key={lastIndex}>{text.slice(lastIndex, match.index)}</span>);
      }
      const num = match[1];
      parts.push(
        <span
          key={match.index}
          style={{
            display: 'inline-flex',
            transform: 'translateY(-6px)',
            marginLeft: '2px',
            marginRight: '2px',
            width: '15px',
            height: '15px',
            borderRadius: '4px',
            background: 'var(--accent)',
            color: 'var(--on-accent)',
            fontSize: '9.5px',
            fontWeight: 700,
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'default'
          }}
          title={`Source [${num}]`}
        >
          {num}
        </span>
      );
      lastIndex = re.lastIndex;
    }
    if (lastIndex < text.length) {
      parts.push(<span key={lastIndex}>{text.slice(lastIndex)}</span>);
    }
    return parts;
  };

  const chips = [
    'What was that shirt with stripes I saw somewhere?',
    'What’s the wifi password for the cabin airbnb?',
    'Did I save anything about tax deadlines?'
  ];

  return (
    <div data-screen-label="Chat" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      {/* Top Header Bar */}
      <div
        style={{
          flex: 'none',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '8px',
          padding: '11px 16px',
          borderBottom: '1.5px solid var(--bord)',
          background: 'var(--panel)'
        }}
      >
        <div style={{ fontWeight: 700, fontSize: '19px', letterSpacing: '-.02em' }}>Recall</div>
        <span
          style={{
            fontSize: '10px',
            fontWeight: 600,
            letterSpacing: '.08em',
            color: 'var(--accent)',
            background: 'var(--accent-soft)',
            padding: '3px 9px',
            borderRadius: '999px'
          }}
        >
          {modelShort}
        </span>
        <div style={{ flex: 1 }} />
        <button
          onClick={onNewQuestion}
          title="Archive this conversation to History and start a fresh one"
          className="btn-secondary"
        >
          ＋ New question
        </button>
        <button
          onClick={onOpenHistory}
          title="Past sessions from this tab"
          className="btn-secondary"
        >
          History {historyCount ? `· ${historyCount}` : ''}
        </button>
        <button
          onClick={onToggleTheme}
          title="Switch light / dark"
          className="btn-square"
        >
          ◐
        </button>
        <button
          onClick={onOpenSettings}
          title="Settings"
          className="btn-square"
        >
          ⚙
        </button>
      </div>

      {/* Info Notice Banner */}
      {barVisible && (
        <div
          style={{
            flex: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            padding: '6px 38px 6px 14px',
            borderBottom: '1px solid var(--line)',
            background: 'var(--panel2)',
            fontSize: '10px',
            fontWeight: 600,
            letterSpacing: '.1em',
            color: 'var(--ink3)',
            textAlign: 'center',
            position: 'relative'
          }}
        >
          <span>◦ SESSION LIVES IN THIS TAB ONLY — CLOSING THE TAB CLEARS IT</span>
          <button
            onClick={handleDismissBar}
            title="Dismiss"
            style={{
              position: 'absolute',
              right: '8px',
              top: '50%',
              transform: 'translateY(-50%)',
              width: '22px',
              height: '22px',
              border: 'none',
              borderRadius: '50%',
              background: 'transparent',
              color: 'var(--ink3)',
              fontSize: '11px',
              cursor: 'pointer',
              padding: 0
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Scrollable Chat Area */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', minHeight: 0, overscrollBehavior: 'contain' }}>
        <div style={{ maxWidth: '680px', margin: '0 auto', padding: '6px 20px 44px', boxSizing: 'border-box' }}>
          
          {/* Empty Workspace Screen */}
          {messages.length === 0 && (
            <div style={{ paddingTop: '10vh', position: 'relative' }} className="animate-fade-up">
              <div
                aria-hidden="true"
                style={{
                  position: 'absolute',
                  inset: '-20px 0 0',
                  pointerEvents: 'none',
                  backgroundImage: 'radial-gradient(var(--line) 1.5px, transparent 1.5px)',
                  backgroundSize: '26px 26px',
                  maskImage: 'radial-gradient(ellipse 90% 80% at 50% 35%, black 20%, transparent 75%)',
                  WebkitMaskImage: 'radial-gradient(ellipse 90% 80% at 50% 35%, black 20%, transparent 75%)'
                }}
              />
              <div
                aria-hidden="true"
                style={{
                  position: 'absolute',
                  top: 0,
                  right: 0,
                  transform: 'rotate(4deg)',
                  width: '132px',
                  pointerEvents: 'none',
                  background: 'var(--panel)',
                  border: '1.5px solid var(--bord)',
                  borderRadius: '8px',
                  boxShadow: '3px 3px 0 var(--hard)',
                  padding: '8px',
                  opacity: 0.6
                }}
              >
                <div
                  style={{
                    height: '52px',
                    borderRadius: '4px',
                    backgroundColor: 'var(--panel2)',
                    backgroundImage: 'repeating-linear-gradient(45deg, var(--line) 0px, var(--line) 1px, transparent 1px, transparent 8px)'
                  }}
                />
                <div style={{ fontSize: '8px', fontWeight: 700, letterSpacing: '.1em', color: 'var(--ct-shot)', marginTop: '6px' }}>
                  SCREENSHOT
                </div>
              </div>
              <div
                aria-hidden="true"
                style={{
                  position: 'absolute',
                  top: '96px',
                  right: '34px',
                  transform: 'rotate(-5deg)',
                  width: '118px',
                  pointerEvents: 'none',
                  background: 'var(--cb-note)',
                  border: '1.5px solid var(--bord)',
                  borderRadius: '8px',
                  boxShadow: '3px 3px 0 var(--hard)',
                  padding: '9px 11px',
                  opacity: 0.6
                }}
              >
                <div style={{ fontSize: '8px', fontWeight: 700, letterSpacing: '.1em', color: 'var(--ct-note)' }}>NOTE</div>
                <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ height: '3px', width: '85%', borderRadius: '2px', background: 'var(--ct-note)', opacity: 0.4 }} />
                  <span style={{ height: '3px', width: '65%', borderRadius: '2px', background: 'var(--ct-note)', opacity: 0.4 }} />
                  <span style={{ height: '3px', width: '75%', borderRadius: '2px', background: 'var(--ct-note)', opacity: 0.4 }} />
                </div>
              </div>
              
              <div style={{ position: 'relative' }}>
                <div style={{ fontSize: 'clamp(30px, 5.5vw, 42px)', fontWeight: 700, lineHeight: 1.08, letterSpacing: '-.03em' }}>
                  Ask your archive.
                </div>
                <div style={{ fontSize: '11px', fontWeight: 600, letterSpacing: '.12em', color: 'var(--ink2)', margin: '14px 0 28px' }}>
                  NOTES · SCREENSHOTS · SAVED POSTS · FILES
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'flex-start' }}>
                  {chips.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => onSubmitQuery(q)}
                      style={{
                        fontSize: '14px',
                        fontWeight: 500,
                        textAlign: 'left',
                        padding: '10px 18px',
                        border: '1.5px solid var(--bord)',
                        borderRadius: '999px',
                        background: 'var(--panel)',
                        color: 'var(--ink2)',
                        cursor: 'pointer',
                        boxShadow: '2px 2px 0 var(--hard)',
                        transition: 'transform 0.1s ease, box-shadow 0.1s ease, color 0.1s ease'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translate(1px, 1px)';
                        e.currentTarget.style.boxShadow = '1px 1px 0 var(--hard)';
                        e.currentTarget.style.color = 'var(--ink)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'none';
                        e.currentTarget.style.boxShadow = '2px 2px 0 var(--hard)';
                        e.currentTarget.style.color = 'var(--ink2)';
                      }}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Render Messages */}
          {messages.map((m) => {
            const isSourcesOpen = !!openSources[m.id];
            const activeIdx = activeSources[m.id] ?? 0;

            return (
              <div key={m.id} className="animate-fade-up">
                
                {/* User Message */}
                {m.kind === 'user' && (
                  <div style={{ marginTop: '36px' }}>
                    <div style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '.12em', color: 'var(--ink3)' }}>
                      YOU · {m.time}
                    </div>
                    <div
                      style={{
                        fontSize: 'clamp(19px, 2.8vw, 23px)',
                        fontWeight: 600,
                        lineHeight: 1.28,
                        marginTop: '6px',
                        letterSpacing: '-.01em',
                        textWrap: 'pretty'
                      }}
                    >
                      {m.text}
                    </div>
                  </div>
                )}

                {/* Loading / Searching stage */}
                {m.kind === 'loading' && m.stage === 'search' && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      marginTop: '18px',
                      fontSize: '10.5px',
                      fontWeight: 600,
                      letterSpacing: '.14em',
                      color: 'var(--ink2)'
                    }}
                  >
                    <span>SEARCHING YOUR ARCHIVE</span>
                    <span style={{ display: 'flex', gap: '5px' }}>
                      <span className="pulse-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)' }} />
                      <span className="pulse-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)', animationDelay: '0.18s' }} />
                      <span className="pulse-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)', animationDelay: '0.36s' }} />
                    </span>
                  </div>
                )}

                {/* Loading / Cold Start stage */}
                {m.kind === 'loading' && m.stage === 'cold' && (
                  <div
                    style={{
                      marginTop: '18px',
                      maxWidth: '520px',
                      border: '1.5px solid var(--bord)',
                      background: 'var(--panel)',
                      borderRadius: '12px',
                      boxShadow: '3px 3px 0 var(--hard)',
                      padding: '16px 18px',
                      display: 'flex',
                      gap: '14px',
                      alignItems: 'flex-start',
                      boxSizing: 'border-box'
                    }}
                  >
                    <span
                      className="breathe-dot"
                      style={{
                        width: '11px',
                        height: '11px',
                        borderRadius: '50%',
                        background: 'var(--accent)',
                        marginTop: '3px',
                        flex: 'none'
                      }}
                    />
                    <div>
                      <div style={{ fontSize: '10.5px', fontWeight: 700, letterSpacing: '.12em', color: 'var(--accent)' }}>
                        COLD START · WAKING THE BACKEND · {m.elapsed || '0S'} ELAPSED
                      </div>
                      <div style={{ fontSize: '13.5px', lineHeight: 1.6, color: 'var(--ink2)', marginTop: '7px', textWrap: 'pretty' }}>
                        It spins down when idle, so the first question can take 30–60 seconds. Yours is queued and will run automatically — no need to resend.
                      </div>
                    </div>
                  </div>
                )}

                {/* Assistant Answer Message */}
                {m.kind === 'answer' && (
                  <div style={{ marginTop: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '10px', fontWeight: 600, letterSpacing: '.12em', color: 'var(--ink3)' }}>
                      <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--accent)' }} />
                      <span>RECALL · {m.model.toUpperCase()}</span>
                    </div>
                    <div
                      style={{
                        fontSize: '15px',
                        lineHeight: 1.75,
                        marginTop: '9px',
                        whiteSpace: 'pre-wrap',
                        textWrap: 'pretty',
                        color: 'var(--ink)'
                      }}
                    >
                      {renderAnswerContent(m.answer)}
                    </div>

                    {/* Citations / Sources Panel */}
                    {m.sources && m.sources.length > 0 && (
                      <div style={{ marginTop: '16px' }}>
                        {!isSourcesOpen ? (
                          <button
                            onClick={() => handleToggleSources(m.id)}
                            style={{
                              width: '100%',
                              display: 'flex',
                              gap: '10px',
                              alignItems: 'center',
                              background: 'var(--panel)',
                              border: '1.5px solid var(--bord)',
                              borderRadius: '10px',
                              boxShadow: '3px 3px 0 var(--hard)',
                              padding: '11px 15px',
                              cursor: 'pointer',
                              textAlign: 'left',
                              transition: 'transform 0.1s ease, box-shadow 0.1s ease'
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.transform = 'translate(1px, 1px)';
                              e.currentTarget.style.boxShadow = '2px 2px 0 var(--hard)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.transform = 'none';
                              e.currentTarget.style.boxShadow = '3px 3px 0 var(--hard)';
                            }}
                          >
                            <span style={{ fontSize: '10.5px', fontWeight: 700, letterSpacing: '.12em', color: 'var(--accent)' }}>
                              SOURCES · {m.sources.length}
                            </span>
                            <span style={{ display: 'flex', gap: '4px' }}>
                              {m.sources.map((s, sIdx) => (
                                <span
                                  key={sIdx}
                                  style={{
                                    width: '8px',
                                    height: '8px',
                                    borderRadius: '50%',
                                    background: TYPE_META[s.type]?.color || 'var(--ink3)'
                                  }}
                                />
                              ))}
                            </span>
                            <span style={{ flex: 1 }} />
                            <span style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '.1em', color: 'var(--ink3)' }}>
                              SHOW ▾
                            </span>
                          </button>
                        ) : (
                          <div>
                            {/* Source Tabs Header */}
                            <div style={{ display: 'flex', gap: '6px', alignItems: 'flex-end', paddingLeft: '14px', flexWrap: 'wrap' }}>
                              {m.sources.map((s, sIdx) => {
                                const meta = TYPE_META[s.type];
                                const isTabActive = sIdx === activeIdx;
                                const label = `${sIdx + 1} · ${s.platform ? `${meta.label} · ${s.platform}` : meta.label}${isTabActive ? ' ▾' : ''}`;
                                
                                return (
                                  <button
                                    key={sIdx}
                                    onClick={() => handleSelectSource(m.id, sIdx)}
                                    style={{
                                      fontSize: '10px',
                                      fontWeight: 700,
                                      letterSpacing: '.08em',
                                      padding: '7px 12px 5px',
                                      background: meta.bg,
                                      color: meta.fg,
                                      border: '1.5px solid var(--bord)',
                                      borderBottom: 'none',
                                      borderRadius: '8px 8px 0 0',
                                      cursor: 'pointer',
                                      opacity: isTabActive ? 1 : 0.62,
                                      position: 'relative',
                                      zIndex: isTabActive ? 2 : 1
                                    }}
                                  >
                                    {label}
                                  </button>
                                );
                              })}
                              <span style={{ flex: 1 }} />
                              <button
                                onClick={() => handleToggleSources(m.id)}
                                style={{
                                  fontSize: '10px',
                                  fontWeight: 600,
                                  letterSpacing: '.1em',
                                  color: 'var(--ink3)',
                                  border: 'none',
                                  background: 'transparent',
                                  cursor: 'pointer',
                                  padding: '4px 2px 6px'
                                }}
                                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--ink)'; }}
                                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--ink3)'; }}
                              >
                                HIDE ▴
                              </button>
                            </div>

                            {/* Active Source Details Box */}
                            {m.sources[activeIdx] && (
                              <div
                                style={{
                                  background: 'var(--panel)',
                                  border: '1.5px solid var(--bord)',
                                  borderRadius: '10px',
                                  boxShadow: '3px 3px 0 var(--hard)',
                                  padding: '15px 16px',
                                  marginTop: '-1px',
                                  position: 'relative'
                                }}
                              >
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', alignItems: 'flex-start' }}>
                                  {m.sources[activeIdx].img && (
                                    <button
                                      onClick={() => onOpenLightbox(m.sources[activeIdx].img)}
                                      style={{
                                        flex: 'none',
                                        width: '190px',
                                        maxWidth: '100%',
                                        padding: 0,
                                        border: '1.5px solid var(--bord)',
                                        borderRadius: '6px',
                                        overflow: 'hidden',
                                        cursor: 'zoom-in',
                                        background: 'transparent'
                                      }}
                                    >
                                      <div
                                        style={{
                                          height: '124px',
                                          display: 'flex',
                                          alignItems: 'center',
                                          justifyContent: 'center',
                                          backgroundColor: 'var(--panel2)',
                                          backgroundImage: 'repeating-linear-gradient(45deg, var(--line) 0px, var(--line) 1px, transparent 1px, transparent 9px)'
                                        }}
                                      >
                                        <span
                                          style={{
                                            fontSize: '9px',
                                            fontWeight: 600,
                                            letterSpacing: '.08em',
                                            color: 'var(--ink2)',
                                            background: 'var(--panel)',
                                            padding: '3px 8px',
                                            borderRadius: '4px',
                                            border: '1px solid var(--line)'
                                          }}
                                        >
                                          TAP TO VIEW
                                        </span>
                                      </div>
                                    </button>
                                  )}
                                  <div style={{ flex: 1, minWidth: '220px' }}>
                                    <div style={{ display: 'flex', gap: '8px', alignItems: 'baseline' }}>
                                      <span
                                        style={{
                                          fontSize: '13px',
                                          fontWeight: 600,
                                          color: 'var(--ink)',
                                          flex: 1,
                                          minWidth: 0,
                                          overflow: 'hidden',
                                          textOverflow: 'ellipsis',
                                          whiteSpace: 'nowrap'
                                        }}
                                      >
                                        {m.sources[activeIdx].title}
                                      </span>
                                    </div>
                                    <div style={{ fontSize: '12.5px', lineHeight: 1.65, color: 'var(--ink2)', marginTop: '7px', whiteSpace: 'pre-wrap' }}>
                                      {m.sources[activeIdx].full}
                                    </div>
                                    <div
                                      style={{
                                        display: 'flex',
                                        flexWrap: 'wrap',
                                        gap: '6px 14px',
                                        marginTop: '11px',
                                        fontSize: '9.5px',
                                        fontWeight: 600,
                                        letterSpacing: '.1em'
                                      }}
                                    >
                                      <span style={{ color: 'var(--ink3)' }}>{m.sources[activeIdx].fullMeta}</span>
                                      <span style={{ color: 'var(--accent)', cursor: 'pointer' }}>OPEN ORIGINAL ↗</span>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* No Matches Screen */}
                {m.kind === 'noresults' && (
                  <div
                    style={{
                      marginTop: '14px',
                      maxWidth: '560px',
                      border: '1.5px dashed var(--bord)',
                      borderRadius: '12px',
                      padding: '16px 18px',
                      boxSizing: 'border-box',
                      background: 'var(--panel)'
                    }}
                  >
                    <div style={{ fontSize: '10.5px', fontWeight: 700, letterSpacing: '.12em', color: 'var(--ink3)' }}>
                      NO MATCHES IN YOUR ARCHIVE
                    </div>
                    <div style={{ fontSize: '14px', lineHeight: 1.6, color: 'var(--ink2)', marginTop: '8px', textWrap: 'pretty' }}>
                      {m.body}
                    </div>
                    <div style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '.1em', color: 'var(--ink3)', marginTop: '11px' }}>
                      TRY DIFFERENT WORDS — RECALL SEARCHES YOUR CONTENT, NOT THE WEB
                    </div>
                  </div>
                )}

                {/* Error Box Screen */}
                {m.kind === 'error' && (
                  <div
                    style={{
                      marginTop: '14px',
                      maxWidth: '560px',
                      border: '1.5px solid var(--err)',
                      borderRadius: '12px',
                      padding: '16px 18px',
                      boxSizing: 'border-box',
                      background: 'var(--panel)',
                      boxShadow: '3px 3px 0 var(--err)'
                    }}
                  >
                    <div style={{ fontSize: '10.5px', fontWeight: 700, letterSpacing: '.12em', color: 'var(--err)' }}>
                      {m.errTitle}
                    </div>
                    <div style={{ fontSize: '14px', lineHeight: 1.6, color: 'var(--ink2)', marginTop: '8px', textWrap: 'pretty' }}>
                      {m.errBody}
                    </div>
                    <div style={{ display: 'flex', gap: '10px', marginTop: '14px' }}>
                      {m.errKind === 'auth' ? (
                        <button
                          onClick={onFixToken}
                          className="btn-primary"
                          style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            padding: '8px 15px',
                            borderRadius: '999px',
                            boxShadow: '2px 2px 0 var(--hard)'
                          }}
                        >
                          Update token
                        </button>
                      ) : (
                        <button
                          onClick={() => onRetryQuery(m.id, m.query)}
                          className="btn-secondary"
                          style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            padding: '8px 15px',
                            borderRadius: '999px'
                          }}
                        >
                          Retry ↻
                        </button>
                      )}
                    </div>
                  </div>
                )}

              </div>
            );
          })}

        </div>
      </div>

      {/* Bottom Query Input Box */}
      <div style={{ flex: 'none', borderTop: '1.5px solid var(--bord)', background: 'var(--bg)', padding: '12px 16px calc(14px + env(safe-area-inset-bottom))' }}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const q = queryValue.trim();
            if (q && !pending) {
              onSubmitQuery(q);
            }
          }}
          style={{
            maxWidth: '680px',
            margin: '0 auto',
            display: 'flex',
            gap: '10px',
            alignItems: 'center',
            background: 'var(--panel)',
            border: '1.5px solid var(--bord)',
            borderRadius: '999px',
            padding: '5px 5px 5px 18px',
            boxShadow: '3px 3px 0 var(--hard)'
          }}
        >
          <input
            ref={inputRef}
            value={queryValue}
            onChange={onQueryChange}
            placeholder="Ask anything you’ve saved…"
            autoComplete="off"
            style={{
              flex: 1,
              minWidth: 0,
              fontSize: '15px',
              padding: '9px 0',
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--ink)'
            }}
          />
          <button
            type="submit"
            disabled={pending}
            title="Ask"
            style={{
              width: '40px',
              height: '40px',
              flex: 'none',
              borderRadius: '50%',
              border: '1.5px solid var(--bord)',
              background: 'var(--accent)',
              color: 'var(--on-accent)',
              fontSize: '17px',
              cursor: pending ? 'not-allowed' : 'pointer',
              opacity: pending ? 0.5 : 1,
              transition: 'filter 0.1s ease',
              outline: 'none',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            onMouseEnter={(e) => { if (!pending) e.currentTarget.style.filter = 'brightness(1.06)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.filter = 'none'; }}
          >
            ↑
          </button>
        </form>
      </div>
    </div>
  );
}
