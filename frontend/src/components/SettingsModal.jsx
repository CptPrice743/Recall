import React, { useState } from 'react';

const SIM_OPTIONS = [
  { id: 'normal', label: 'Normal' },
  { id: 'cold', label: 'Cold start' },
  { id: 'down', label: 'Backend down' },
  { id: 'rate', label: 'Rate limit' },
  { id: 'reject', label: 'Bad token' }
];

export default function SettingsModal({
  isOpen,
  onClose,
  token,
  onSaveToken,
  onForgetToken,
  theme,
  onSelectTheme,
  simMode,
  onSelectSimMode,
  apis,
  onUpdateApis,
  activeModel,
  onSelectModel,
  tokenRejected
}) {
  const [activeTab, setActiveTab] = useState('general'); // 'general' | 'models'
  
  // Settings token form input state
  const [settingsToken, setSettingsToken] = useState(token);

  // New Provider form inputs
  const [newApiName, setNewApiName] = useState('');
  const [newApiKey, setNewApiKey] = useState('');

  // Draft models for each API provider (keyed by api.id)
  const [modelDrafts, setModelDrafts] = useState({});

  if (!isOpen) return null;

  const handleSaveTokenSubmit = (e) => {
    e.preventDefault();
    const t = settingsToken.trim();
    if (t) {
      onSaveToken(t);
    }
  };

  const handleAddProviderSubmit = (e) => {
    e.preventDefault();
    const name = newApiName.trim();
    if (!name) return;
    
    const newProvider = {
      id: 'api-' + Date.now(),
      name,
      key: newApiKey.trim(),
      models: []
    };

    onUpdateApis([...apis, newProvider]);
    setNewApiName('');
    setNewApiKey('');
  };

  const handleRemoveProvider = (apiId) => {
    const nextApis = apis.filter(a => a.id !== apiId);
    onUpdateApis(nextApis);
  };

  const handleUpdateApiKey = (apiId, val) => {
    const nextApis = apis.map(a => a.id === apiId ? { ...a, key: val } : a);
    onUpdateApis(nextApis);
  };

  const handleAddModel = (e, apiId) => {
    e.preventDefault();
    const draft = (modelDrafts[apiId] || '').trim();
    if (!draft) return;

    const nextApis = apis.map(a => {
      if (a.id === apiId) {
        const models = a.models.includes(draft) ? a.models : [...a.models, draft];
        return { ...a, models };
      }
      return a;
    });

    onUpdateApis(nextApis);
    setModelDrafts(prev => ({ ...prev, [apiId]: '' }));
  };

  const handleRemoveModel = (apiId, modelId) => {
    const nextApis = apis.map(a => {
      if (a.id === apiId) {
        return { ...a, models: a.models.filter(m => m !== modelId) };
      }
      return a;
    });
    onUpdateApis(nextApis);
  };

  return (
    <div
      data-screen-label="Settings"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '18px',
        background: 'var(--scrim)'
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="animate-fade-up"
        style={{
          width: '100%',
          maxWidth: '470px',
          maxHeight: '88vh',
          overflowY: 'auto',
          background: 'var(--panel)',
          color: 'var(--ink)',
          border: '1.5px solid var(--bord)',
          borderRadius: '16px',
          boxShadow: '5px 5px 0 var(--hard)',
          padding: '22px',
          boxSizing: 'border-box'
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ fontWeight: 700, fontSize: '21px', letterSpacing: '-.02em', flex: 1 }}>Settings</div>
          <button
            onClick={onClose}
            className="btn-square"
            style={{ width: '30px', height: '30px', fontSize: '13px' }}
          >
            ✕
          </button>
        </div>

        {/* Tab Buttons */}
        <div style={{ display: 'flex', gap: '8px', marginTop: '16px', borderBottom: '1.5px solid var(--line)', paddingBottom: '14px' }}>
          {[
            { id: 'general', label: 'General' },
            { id: 'models', label: 'API keys & models' }
          ].map(t => {
            const isActive = activeTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  letterSpacing: '.04em',
                  padding: '8px 14px',
                  border: '1.5px solid var(--bord)',
                  borderRadius: '999px',
                  background: isActive ? 'var(--accent)' : 'var(--panel)',
                  color: isActive ? 'var(--on-accent)' : 'var(--ink2)',
                  cursor: 'pointer',
                  boxShadow: '2px 2px 0 var(--hard)',
                  transition: 'transform 0.1s ease, box-shadow 0.1s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translate(1px, 1px)';
                  e.currentTarget.style.boxShadow = '1px 1px 0 var(--hard)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'none';
                  e.currentTarget.style.boxShadow = '2px 2px 0 var(--hard)';
                }}
              >
                {t.label}
              </button>
            );
          })}
        </div>

        {/* General Tab */}
        {activeTab === 'general' && (
          <div>
            {/* Access Token Block */}
            <div style={{ marginTop: '18px' }}>
              <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '.14em', color: 'var(--ink3)' }}>
                ACCESS TOKEN
              </div>
              {tokenRejected && (
                <div
                  style={{
                    marginTop: '8px',
                    border: '1.5px solid var(--err)',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    background: 'var(--err-soft)',
                    fontSize: '10.5px',
                    fontWeight: 600,
                    lineHeight: 1.6,
                    color: 'var(--err)'
                  }}
                >
                  REJECTED BY SERVER (401) — PASTE THE CURRENT TOKEN
                </div>
              )}
              <form onSubmit={handleSaveTokenSubmit} style={{ display: 'flex', gap: '8px', marginTop: '9px' }}>
                <input
                  type="password"
                  value={settingsToken}
                  onChange={(e) => setSettingsToken(e.target.value)}
                  autoComplete="off"
                  className="input-text"
                  style={{
                    padding: '10px 13px',
                    borderRadius: '10px',
                    fontSize: '13px',
                    borderColor: tokenRejected ? 'var(--err)' : 'var(--bord)'
                  }}
                />
                <button
                  type="submit"
                  className="btn-primary"
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '0 16px',
                    borderRadius: '10px',
                    boxShadow: '2px 2px 0 var(--hard)'
                  }}
                >
                  Save
                </button>
              </form>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: '12px',
                  marginTop: '9px',
                  fontSize: '10px',
                  fontWeight: 600,
                  letterSpacing: '.06em'
                }}
              >
                <span style={{ color: 'var(--ink3)' }}>STORED IN THIS BROWSER ONLY</span>
                <span style={{ flex: 1 }} />
                <button
                  onClick={onForgetToken}
                  style={{
                    border: 'none',
                    background: 'transparent',
                    padding: 0,
                    fontSize: '10px',
                    fontWeight: 600,
                    letterSpacing: '.06em',
                    color: 'var(--err)',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.textDecoration = 'underline'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.textDecoration = 'none'; }}
                >
                  FORGET TOKEN + LOCK
                </button>
              </div>
            </div>

            {/* Appearance theme block */}
            <div style={{ marginTop: '22px', borderTop: '1.5px solid var(--line)', paddingTop: '18px' }}>
              <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '.14em', color: 'var(--ink3)' }}>
                APPEARANCE
              </div>
              <div style={{ display: 'flex', gap: '8px', marginTop: '9px' }}>
                {['light', 'dark'].map(t => {
                  const isActive = theme === t;
                  return (
                    <button
                      key={t}
                      onClick={() => onSelectTheme(t)}
                      style={{
                        flex: 1,
                        fontSize: '11px',
                        fontWeight: 600,
                        letterSpacing: '.08em',
                        padding: '9px 0',
                        border: '1.5px solid var(--bord)',
                        borderRadius: '10px',
                        background: isActive ? 'var(--accent)' : 'var(--panel)',
                        color: isActive ? 'var(--on-accent)' : 'var(--ink2)',
                        cursor: 'pointer',
                        boxShadow: '2px 2px 0 var(--hard)',
                        transition: 'transform 0.1s ease, box-shadow 0.1s ease'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translate(1px, 1px)';
                        e.currentTarget.style.boxShadow = '1px 1px 0 var(--hard)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'none';
                        e.currentTarget.style.boxShadow = '2px 2px 0 var(--hard)';
                      }}
                    >
                      {t.toUpperCase()}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Simulator config block */}
            <div style={{ marginTop: '22px', borderTop: '1.5px solid var(--line)', paddingTop: '18px' }}>
              <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '.14em', color: 'var(--ink3)' }}>
                PROTOTYPE · HOW THE NEXT QUESTION BEHAVES
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
                {SIM_OPTIONS.map(o => {
                  const isActive = simMode === o.id;
                  return (
                    <button
                      key={o.id}
                      onClick={() => onSelectSimMode(o.id)}
                      style={{
                        fontSize: '10.5px',
                        fontWeight: 600,
                        letterSpacing: '.04em',
                        padding: '8px 13px',
                        border: '1.5px solid var(--bord)',
                        borderRadius: '999px',
                        background: isActive ? 'var(--accent)' : 'var(--panel)',
                        color: isActive ? 'var(--on-accent)' : 'var(--ink2)',
                        cursor: 'pointer',
                        boxShadow: '2px 2px 0 var(--hard)',
                        transition: 'transform 0.1s ease, box-shadow 0.1s ease'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translate(1px, 1px)';
                        e.currentTarget.style.boxShadow = '1px 1px 0 var(--hard)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'none';
                        e.currentTarget.style.boxShadow = '2px 2px 0 var(--hard)';
                      }}
                    >
                      {o.label}
                    </button>
                  );
                })}
              </div>
              <div style={{ fontSize: '10px', fontWeight: 500, lineHeight: 1.7, letterSpacing: '.04em', color: 'var(--ink3)', marginTop: '10px' }}>
                ONE-SHOT — RESETS TO NORMAL AFTER IT FIRES. THIS SECTION WOULDN’T EXIST IN THE REAL APP.
              </div>
            </div>
          </div>
        )}

        {/* API keys & models Tab */}
        {activeTab === 'models' && (
          <div>
            <div style={{ marginTop: '18px', fontSize: '10px', fontWeight: 600, letterSpacing: '.1em', lineHeight: 1.7, color: 'var(--ink3)' }}>
              PICK THE ACTIVE MODEL — TAKES EFFECT ON YOUR NEXT QUESTION. KEYS AND MODEL IDS ARE STORED IN THIS BROWSER ONLY.
            </div>

            {/* Providers List */}
            {apis.map(a => (
              <div
                key={a.id}
                style={{
                  marginTop: '14px',
                  border: '1.5px solid var(--bord)',
                  borderRadius: '12px',
                  padding: '14px',
                  background: 'var(--bg)',
                  boxShadow: '3px 3px 0 var(--hard)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '.06em' }}>{a.name}</span>
                  <span style={{ flex: 1 }} />
                  <button
                    onClick={() => handleRemoveProvider(a.id)}
                    title="Remove this API key and its models"
                    style={{
                      fontSize: '9.5px',
                      fontWeight: 600,
                      letterSpacing: '.06em',
                      padding: '5px 10px',
                      border: '1.5px solid var(--line)',
                      borderRadius: '999px',
                      background: 'transparent',
                      color: 'var(--ink3)',
                      cursor: 'pointer',
                      transition: 'color 0.1s ease, border-color 0.1s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = 'var(--err)';
                      e.currentTarget.style.borderColor = 'var(--err)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = 'var(--ink3)';
                      e.currentTarget.style.borderColor = 'var(--line)';
                    }}
                  >
                    REMOVE
                  </button>
                </div>

                <input
                  type="password"
                  value={a.key || ''}
                  onChange={(e) => handleUpdateApiKey(a.id, e.target.value)}
                  placeholder="api key"
                  className="input-text"
                  autoComplete="off"
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    marginTop: '10px',
                    fontSize: '12px',
                    padding: '9px 12px',
                    background: 'var(--panel)',
                    borderRadius: '9px'
                  }}
                />

                {/* Models List for this Provider */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '7px', marginTop: '10px' }}>
                  {a.models.map(mId => {
                    const isActive = mId === activeModel;
                    return (
                      <div key={mId} style={{ display: 'flex', alignItems: 'stretch', gap: '7px' }}>
                        <button
                          onClick={() => onSelectModel(mId)}
                          title="Set as active model"
                          style={{
                            flex: 1,
                            minWidth: 0,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '9px',
                            padding: '8px 11px',
                            border: `1.5px solid ${isActive ? 'var(--accent)' : 'var(--line)'}`,
                            borderRadius: '9px',
                            background: isActive ? 'var(--accent-soft)' : 'var(--panel)',
                            cursor: 'pointer',
                            textAlign: 'left'
                          }}
                        >
                          <span
                            style={{
                              width: '9px',
                              height: '9px',
                              borderRadius: '50%',
                              flex: 'none',
                              boxSizing: 'border-box',
                              border: `1.5px solid ${isActive ? 'var(--accent)' : 'var(--ink3)'}`,
                              background: isActive ? 'var(--accent)' : 'transparent'
                            }}
                          />
                          <span
                            style={{
                              fontSize: '12px',
                              fontWeight: 500,
                              color: 'var(--ink)',
                              minWidth: 0,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}
                          >
                            {mId}
                          </span>
                          <span style={{ flex: 1 }} />
                          {isActive && (
                            <span style={{ fontSize: '9px', fontWeight: 700, letterSpacing: '.1em', color: 'var(--accent)', flex: 'none' }}>
                              ACTIVE
                            </span>
                          )}
                        </button>
                        <button
                          onClick={() => handleRemoveModel(a.id, mId)}
                          title="Remove model"
                          style={{
                            width: '30px',
                            border: '1.5px solid var(--line)',
                            borderRadius: '9px',
                            background: 'transparent',
                            color: 'var(--ink3)',
                            cursor: 'pointer',
                            fontSize: '11px',
                            padding: 0,
                            transition: 'color 0.1s ease, border-color 0.1s ease'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.color = 'var(--err)';
                            e.currentTarget.style.borderColor = 'var(--err)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.color = 'var(--ink3)';
                            e.currentTarget.style.borderColor = 'var(--line)';
                          }}
                        >
                          ✕
                        </button>
                      </div>
                    );
                  })}
                </div>

                {/* Form to Add Model */}
                <form
                  onSubmit={(e) => handleAddModel(e, a.id)}
                  style={{ display: 'flex', gap: '7px', marginTop: '9px' }}
                >
                  <input
                    value={modelDrafts[a.id] || ''}
                    onChange={(e) => setModelDrafts({ ...modelDrafts, [a.id]: e.target.value })}
                    placeholder="add model id, e.g. gemini-3.5-flash"
                    autoComplete="off"
                    style={{
                      flex: 1,
                      minWidth: 0,
                      fontSize: '12px',
                      padding: '8px 11px',
                      background: 'var(--panel)',
                      border: '1.5px solid var(--line)',
                      borderRadius: '9px',
                      outline: 'none'
                    }}
                  />
                  <button
                    type="submit"
                    className="btn-primary"
                    style={{
                      fontSize: '10.5px',
                      fontWeight: 600,
                      padding: '0 14px',
                      borderRadius: '9px',
                      boxShadow: '2px 2px 0 var(--hard)'
                    }}
                  >
                    Add
                  </button>
                </form>
              </div>
            ))}

            {/* Form to Add API Key Provider */}
            <div style={{ marginTop: '18px', borderTop: '1.5px dashed var(--line)', paddingTop: '16px' }}>
              <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '.14em', color: 'var(--ink3)' }}>
                ADD API KEY
              </div>
              <form onSubmit={handleAddProviderSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '9px' }}>
                <input
                  value={newApiName}
                  onChange={(e) => setNewApiName(e.target.value)}
                  placeholder="provider name, e.g. OpenRouter"
                  className="input-text"
                  autoComplete="off"
                  style={{
                    fontSize: '12px',
                    padding: '9px 12px',
                    borderRadius: '9px'
                  }}
                />
                <input
                  type="password"
                  value={newApiKey}
                  onChange={(e) => setNewApiKey(e.target.value)}
                  placeholder="api key (can be added later)"
                  className="input-text"
                  autoComplete="off"
                  style={{
                    fontSize: '12px',
                    padding: '9px 12px',
                    borderRadius: '9px'
                  }}
                />
                <button
                  type="submit"
                  className="btn-primary"
                  style={{
                    alignSelf: 'flex-start',
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '9px 16px',
                    borderRadius: '9px',
                    boxShadow: '2px 2px 0 var(--hard)'
                  }}
                >
                  Add provider
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
