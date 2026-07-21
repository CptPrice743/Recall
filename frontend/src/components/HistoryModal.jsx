import React from 'react';

export default function HistoryModal({
  isOpen,
  onClose,
  sessions,
  onOpenSession,
  onDeleteSession
}) {
  if (!isOpen) return null;

  return (
    <div
      data-screen-label="History"
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
          maxWidth: '440px',
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
          <div style={{ fontWeight: 700, fontSize: '21px', letterSpacing: '-.02em', flex: 1 }}>History</div>
          <button
            onClick={onClose}
            className="btn-square"
            style={{ width: '30px', height: '30px', fontSize: '13px' }}
          >
            ✕
          </button>
        </div>

        <div style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '.1em', lineHeight: 1.7, color: 'var(--ink3)', marginTop: '8px' }}>
          PAST SESSIONS FROM THIS TAB — NOTHING IS SAVED ON THE SERVER. CLOSING THE TAB CLEARS ALL OF IT.
        </div>

        {/* Empty State */}
        {sessions.length === 0 && (
          <div
            style={{
              marginTop: '18px',
              border: '1.5px dashed var(--bord)',
              borderRadius: '12px',
              padding: '16px',
              fontSize: '13.5px',
              lineHeight: 1.6,
              color: 'var(--ink2)'
            }}
          >
            No past sessions yet. “＋ New question” archives the current conversation here and starts a fresh one.
          </div>
        )}

        {/* Past Sessions List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '16px' }}>
          {sessions.map((s) => {
            const questionCount = s.messages.filter(m => m.kind === 'user').length;
            const metaText = `${questionCount} ${questionCount === 1 ? 'QUESTION' : 'QUESTIONS'} · ${s.time}`;
            
            return (
              <div key={s.id} style={{ display: 'flex', alignItems: 'stretch', gap: '8px' }}>
                <button
                  onClick={() => onOpenSession(s.id)}
                  style={{
                    flex: 1,
                    minWidth: 0,
                    textAlign: 'left',
                    border: '1.5px solid var(--bord)',
                    borderRadius: '11px',
                    background: 'var(--panel)',
                    padding: '11px 14px',
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
                  <div
                    style={{
                      fontSize: '14px',
                      fontWeight: 600,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      color: 'var(--ink)'
                    }}
                  >
                    {s.title}
                  </div>
                  <div style={{ fontSize: '9.5px', fontWeight: 600, letterSpacing: '.1em', color: 'var(--ink3)', marginTop: '5px' }}>
                    {metaText}
                  </div>
                </button>
                <button
                  onClick={() => onDeleteSession(s.id)}
                  title="Delete session"
                  style={{
                    width: '36px',
                    border: '1.5px solid var(--bord)',
                    borderRadius: '11px',
                    background: 'var(--panel)',
                    color: 'var(--ink3)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    padding: 0,
                    boxShadow: '2px 2px 0 var(--hard)',
                    transition: 'color 0.1s ease, border-color 0.1s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = 'var(--err)';
                    e.currentTarget.style.borderColor = 'var(--err)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = 'var(--ink3)';
                    e.currentTarget.style.borderColor = 'var(--bord)';
                  }}
                >
                  ✕
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
