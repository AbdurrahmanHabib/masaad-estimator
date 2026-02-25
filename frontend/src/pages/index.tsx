import React from 'react';
import Link from 'next/link';

export default function Dashboard() {
  return (
    <div style={{ backgroundColor: '#020617', minHeight: '100vh', color: '#f8fafc', display: 'flex' }}>
      
      {/* SIDEBAR */}
      <div style={{ width: '256px', backgroundColor: '#0f172a', borderRight: '1px solid #1e293b', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div>
          <div style={{ padding: '24px', borderBottom: '1px solid #1e293b', textAlign: 'center' }}>
            <img src="/logo.png" alt="Madinat Al Saada" style={{ height: '64px', margin: '0 auto 16px auto', objectFit: 'contain' }} />
            <h1 style={{ fontSize: '14px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#ffffff' }}>Madinat Al Saada</h1>
            <p style={{ fontSize: '10px', color: '#10b981', fontFamily: 'monospace', marginTop: '8px' }}>ESTIMATOR_PRO_V2.1_CACHE_BUSTER</p>
          </div>
          <nav style={{ padding: '16px' }}>
            <Link href="/" style={{ display: 'block', padding: '12px 16px', backgroundColor: 'rgba(16, 185, 129, 0.1)', color: '#34d399', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.2)', fontSize: '12px', fontWeight: 'bold', textTransform: 'uppercase', textDecoration: 'none' }}>
              Dashboard
            </Link>
          </nav>
        </div>
        <div style={{ padding: '24px', borderTop: '1px solid #1e293b' }}>
          <p style={{ fontSize: '9px', color: '#475569', textAlign: 'center', textTransform: 'uppercase' }}>
            System Architecture by <br/><span style={{ color: '#94a3b8', fontWeight: 'bold' }}>Masaad</span>
          </p>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <header style={{ height: '64px', backgroundColor: 'rgba(15, 23, 42, 0.8)', borderBottom: '1px solid #1e293b', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 40px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 300, fontStyle: 'italic' }}>Industrial_Mission_Control</h2>
          <div style={{ fontSize: '10px', color: '#64748b' }}>
            BUILD_SYNC_TIME: {new Date().toLocaleTimeString()}
          </div>
        </header>

        <main style={{ flex: 1, padding: '40px' }}>
           <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', padding: '32px', borderRadius: '8px', textAlign: 'center' }}>
              <h1 style={{ fontSize: '48px', fontWeight: 900, color: '#dc2626', textTransform: 'uppercase' }}>Update_Verified</h1>
              <p style={{ color: '#94a3b8', fontSize: '12px', marginTop: '16px' }}>If you see this dark screen, we have successfully bypassed the cache.</p>
           </div>
        </main>
      </div>
    </div>
  );
}