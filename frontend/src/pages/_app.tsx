import './globals.css';
import type { AppProps } from 'next/app';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import { useAuthStore } from '../store/useAuthStore';

// Pages that do not require authentication
const PUBLIC_PATHS = ['/login'];

function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  // mounted guard: prevents any auth-dependent rendering until client hydration
  // is complete, eliminating React hydration mismatches with persisted Zustand state.
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const isPublic = PUBLIC_PATHS.includes(router.pathname);
    if (!isAuthenticated && !isPublic) {
      router.replace('/login');
    }
  }, [mounted, isAuthenticated, router.pathname]);

  // Render login (and any future public pages) without the main Layout shell.
  // Safe to render before mount because login has no auth-dependent content.
  if (PUBLIC_PATHS.includes(router.pathname)) {
    return <Component {...pageProps} />;
  }

  // Before hydration is complete, show a minimal blank slate so React's
  // server/client HTML match perfectly (avoids hydration warnings).
  if (!mounted) {
    return <div className="min-h-screen bg-[#f8fafc]" />;
  }

  // After hydration: if not authenticated redirect is in-flight — show dark
  // overlay so there is no flash of the protected layout.
  if (!isAuthenticated) {
    return <div className="min-h-screen bg-[#1e293b]" />;
  }

  return (
    <Layout>
      <Component {...pageProps} />
    </Layout>
  );
}

export default MyApp;
