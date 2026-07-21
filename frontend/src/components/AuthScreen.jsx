import React, { useState } from 'react';

export default function AuthScreen({ onUnlock, authRejected }) {
  const [tokenDraft, setTokenDraft] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const cleanToken = tokenDraft.trim();
    if (cleanToken) {
      onUnlock(cleanToken);
    }
  };

  const isUnlockDisabled = !tokenDraft.trim();

  return (
    <div
      data-screen-label="Token entry"
      style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        position: 'relative',
        overflow: 'hidden',
        backgroundImage: 'radial-gradient(var(--line) 1.5px, transparent 1.5px)',
        backgroundSize: '26px 26px'
      }}
    >
      {/* Background Floating Badges */}
      <div aria-hidden="true" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
        <span
          style={{
            position: 'absolute',
            top: '12%',
            left: '8%',
            transform: 'rotate(-7deg)',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '.08em',
            padding: '8px 14px',
            background: 'var(--cb-post)',
            color: 'var(--ct-post)',
            border: '1.5px solid var(--bord)',
            borderRadius: '8px',
            boxShadow: '3px 3px 0 var(--hard)',
            opacity: 0.55
          }}
        >
          POST · IG
        </span>
        <span
          style={{
            position: 'absolute',
            top: '22%',
            right: '10%',
            transform: 'rotate(5deg)',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '.08em',
            padding: '8px 14px',
            background: 'var(--cb-shot)',
            color: 'var(--ct-shot)',
            border: '1.5px solid var(--bord)',
            borderRadius: '8px',
            boxShadow: '3px 3px 0 var(--hard)',
            opacity: 0.55
          }}
        >
          SCREENSHOT
        </span>
        <span
          style={{
            position: 'absolute',
            bottom: '24%',
            left: '11%',
            transform: 'rotate(4deg)',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '.08em',
            padding: '8px 14px',
            background: 'var(--cb-note)',
            color: 'var(--ct-note)',
            border: '1.5px solid var(--bord)',
            borderRadius: '8px',
            boxShadow: '3px 3px 0 var(--hard)',
            opacity: 0.55
          }}
        >
          NOTE
        </span>
        <span
          style={{
            position: 'absolute',
            bottom: '14%',
            right: '8%',
            transform: 'rotate(-5deg)',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '.08em',
            padding: '8px 14px',
            background: 'var(--cb-file)',
            color: 'var(--ct-file)',
            border: '1.5px solid var(--bord)',
            borderRadius: '8px',
            boxShadow: '3px 3px 0 var(--hard)',
            opacity: 0.55
          }}
        >
          FILE · PDF
        </span>
        <span
          style={{
            position: 'absolute',
            top: '52%',
            left: '4%',
            transform: 'rotate(-3deg)',
            width: '15px',
            height: '15px',
            borderRadius: '4px',
            background: 'var(--accent)',
            opacity: 0.3
          }}
        />
        <span
          style={{
            position: 'absolute',
            top: '9%',
            right: '32%',
            transform: 'rotate(6deg)',
            width: '15px',
            height: '15px',
            borderRadius: '4px',
            background: 'var(--accent)',
            opacity: 0.3
          }}
        />
        <span
          style={{
            position: 'absolute',
            bottom: '9%',
            left: '38%',
            transform: 'rotate(-8deg)',
            width: '15px',
            height: '15px',
            borderRadius: '4px',
            background: 'var(--accent)',
            opacity: 0.3
          }}
        />
      </div>

      {/* Auth Card */}
      <div
        className="animate-fade-up"
        style={{
          width: '100%',
          maxWidth: '410px',
          position: 'relative',
          background: 'var(--panel)',
          border: '1.5px solid var(--bord)',
          borderRadius: '16px',
          boxShadow: '5px 5px 0 var(--hard)',
          padding: '28px',
          boxSizing: 'border-box'
        }}
      >
        <div style={{ fontWeight: 700, fontSize: '34px', letterSpacing: '-.03em', lineHeight: 1 }}>
          Recall
        </div>
        <div
          style={{
            fontSize: '10px',
            fontWeight: 600,
            letterSpacing: '.14em',
            color: 'var(--ink3)',
            marginTop: '10px'
          }}
        >
          PERSONAL ARCHIVE · SINGLE USER
        </div>
        <p style={{ fontSize: '14.5px', lineHeight: 1.65, color: 'var(--ink2)', margin: '18px 0 0' }}>
          Your notes, screenshots, saved posts and files — queryable in plain language. Enter the access token to open the archive.
        </p>

        {authRejected && (
          <div
            style={{
              marginTop: '16px',
              border: '1.5px solid var(--err)',
              borderRadius: '10px',
              padding: '10px 14px',
              background: 'var(--err-soft)',
              fontSize: '11.5px',
              fontWeight: 600,
              lineHeight: 1.6,
              color: 'var(--err)'
            }}
          >
            TOKEN REJECTED BY THE SERVER (401). It may have been rotated — paste the current one.
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '20px' }}>
          <input
            type="password"
            value={tokenDraft}
            onChange={(e) => setTokenDraft(e.target.value)}
            placeholder="access token"
            className="input-text"
            autoComplete="off"
            style={{
              borderColor: authRejected ? 'var(--err)' : 'var(--bord)'
            }}
          />
          <button
            type="submit"
            disabled={isUnlockDisabled}
            className="btn-primary"
            style={{
              opacity: isUnlockDisabled ? 0.5 : 1,
              cursor: isUnlockDisabled ? 'not-allowed' : 'pointer'
            }}
          >
            Unlock archive
          </button>
        </form>

        <div
          style={{
            fontSize: '10.5px',
            fontWeight: 500,
            lineHeight: 1.7,
            letterSpacing: '.04em',
            color: 'var(--ink3)',
            marginTop: '16px'
          }}
        >
          Stored only in this browser — sent only to your own backend.
        </div>
      </div>
    </div>
  );
}
