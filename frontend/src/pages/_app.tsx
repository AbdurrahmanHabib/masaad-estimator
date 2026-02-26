import './globals.css';
import type { AppProps } from 'next/app';
import { useEffect } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import { useAuthStore } from '../store/useAuthStore';

// Pages that do not require authentication
const PUBLIC_PATHS = ['/login'];

function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    const isPublic = PUBLIC_PATHS.includes(router.pathname);

    if (!isAuthenticated && !isPublic) {
      router.replace('/login');
    }
  }, [isAuthenticated, router.pathname]);

  // Render login (and any future public pages) without the main Layout shell
  if (PUBLIC_PATHS.includes(router.pathname)) {
    return <Component {...pageProps} />;
  }

  // While auth state is hydrating from localStorage, show a blank slate to
  // avoid a flash of the protected UI before redirect fires.
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
