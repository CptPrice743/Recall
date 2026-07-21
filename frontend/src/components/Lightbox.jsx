import React from 'react';

export default function Lightbox({ isOpen, img, onClose }) {
  if (!isOpen || !img) return null;

  return (
    <div
      data-screen-label="Image viewer"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 60,
        background: 'var(--scrim)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '14px',
        padding: '20px',
        cursor: 'zoom-out'
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="animate-fade-up"
        style={{
          width: 'min(720px, 92vw)',
          height: 'min(72vh, 600px)',
          borderRadius: '12px',
          border: '1.5px solid var(--bord)',
          boxShadow: '5px 5px 0 var(--hard)',
          backgroundColor: 'var(--panel2)',
          backgroundImage: img.src 
            ? 'none' 
            : 'repeating-linear-gradient(45deg, var(--line) 0px, var(--line) 1px, transparent 1px, transparent 10px)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          position: 'relative'
        }}
      >
        {img.src ? (
          <img
            src={img.src}
            alt={img.caption || 'Screenshot'}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              display: 'block'
            }}
          />
        ) : (
          <span
            style={{
              fontSize: '11px',
              fontWeight: 600,
              letterSpacing: '.08em',
              color: 'var(--ink2)',
              background: 'var(--panel)',
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid var(--line)'
            }}
          >
            {img.label}
          </span>
        )}
      </div>
      <div
        style={{
          fontSize: '10.5px',
          fontWeight: 600,
          letterSpacing: '.1em',
          color: '#fff',
          textAlign: 'center',
          textShadow: '0 1px 2px rgba(0,0,0,0.5)'
        }}
      >
        {img.caption} — CLICK ANYWHERE TO CLOSE
      </div>
    </div>
  );
}
