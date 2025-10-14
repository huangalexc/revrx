'use client';

import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function Home() {
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    // Redirect authenticated users to dashboard
    if (isAuthenticated) {
      router.push('/summary');
    }
  }, [isAuthenticated, router]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center" aria-label="Main navigation">
          <div className="flex items-center">
            <span className="text-2xl font-bold text-blue-600">RevRx</span>
            <span className="ml-2 text-sm text-gray-700 hidden sm:inline">Post-Facto Coding Review</span>
          </div>
          <div className="flex gap-4">
            <Link
              href="/login"
              className="px-4 py-2 text-gray-700 hover:text-gray-900 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg"
              aria-label="Log in to your account"
            >
              Log In
            </Link>
            <Link
              href="/register"
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 shadow-sm"
              aria-label="Sign up for a free account"
            >
              Sign Up
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main>
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-32" aria-labelledby="hero-heading">
        <div className="text-center">
          <h1 id="hero-heading" className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-6">
            Maximize Revenue with
            <span className="block text-blue-600 mt-2">AI-Powered Medical Coding</span>
          </h1>
          <p className="text-lg sm:text-xl text-gray-700 mb-8 max-w-3xl mx-auto">
            RevRx uses advanced AI to analyze clinical notes and identify missed billing opportunities,
            ensuring your practice captures every dollar it deserves while maintaining HIPAA compliance.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="px-8 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold text-lg transition-all shadow-lg hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transform hover:scale-105"
              aria-label="Start your 7-day free trial"
            >
              Start Free Trial
            </Link>
            <Link
              href="/login"
              className="px-8 py-4 bg-white text-gray-700 border-2 border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50 font-semibold text-lg transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              aria-label="Request a demo of RevRx"
            >
              Request Demo
            </Link>
          </div>
          <p className="text-sm text-gray-500 mt-6">
            7-day free trial • No credit card required • HIPAA compliant
          </p>
        </div>
      </section>

      {/* Features Section */}
      <section className="bg-white py-20" aria-labelledby="features-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 id="features-heading" className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Everything You Need to Optimize Revenue
            </h2>
            <p className="text-lg sm:text-xl text-gray-700">
              Comprehensive post-facto coding review powered by AI
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <article className="p-8 border border-gray-200 rounded-xl hover:shadow-lg hover:border-blue-200 transition-all focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-2 group">
              <div className="bg-blue-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-200 transition-colors" style={{ width: '48px', height: '48px', minWidth: '48px', minHeight: '48px' }}>
                <svg width="24" height="24" className="text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">AI-Powered Analysis</h3>
              <p className="text-gray-700 leading-relaxed">
                Advanced natural language processing analyzes clinical notes to identify missed CPT codes and billing opportunities automatically.
              </p>
            </article>

            <article className="p-8 border border-gray-200 rounded-xl hover:shadow-lg hover:border-green-200 transition-all focus-within:ring-2 focus-within:ring-green-500 focus-within:ring-offset-2 group">
              <div className="bg-green-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-green-200 transition-colors" style={{ width: '48px', height: '48px', minWidth: '48px', minHeight: '48px' }}>
                <svg width="24" height="24" className="text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">HIPAA Compliant</h3>
              <p className="text-gray-700 leading-relaxed">
                Bank-grade encryption, automatic PHI detection and removal, and full audit trails ensure your patient data stays secure and compliant.
              </p>
            </article>

            <article className="p-8 border border-gray-200 rounded-xl hover:shadow-lg hover:border-purple-200 transition-all focus-within:ring-2 focus-within:ring-purple-500 focus-within:ring-offset-2 group">
              <div className="bg-purple-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-purple-200 transition-colors" style={{ width: '48px', height: '48px', minWidth: '48px', minHeight: '48px' }}>
                <svg width="24" height="24" className="text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Revenue Optimization</h3>
              <p className="text-gray-700 leading-relaxed">
                Track revenue recovery in real-time with detailed analytics showing exactly how much additional revenue you've captured.
              </p>
            </article>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20" aria-labelledby="how-it-works-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 id="how-it-works-heading" className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              How RevRx Works
            </h2>
            <p className="text-lg sm:text-xl text-gray-700">
              Simple workflow, powerful results
            </p>
          </div>

          <ol className="grid md:grid-cols-4 gap-8 list-none">
            <li className="text-center">
              <div className="w-16 h-16 bg-blue-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4" aria-label="Step 1">
                1
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Upload Notes</h3>
              <p className="text-gray-700">
                Upload clinical notes and submitted billing codes in PDF or DOCX format
              </p>
            </li>

            <li className="text-center">
              <div className="w-16 h-16 bg-blue-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4" aria-label="Step 2">
                2
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">AI Analysis</h3>
              <p className="text-gray-700">
                Our AI analyzes notes, removes PHI, and identifies coding opportunities
              </p>
            </li>

            <li className="text-center">
              <div className="w-16 h-16 bg-blue-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4" aria-label="Step 3">
                3
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Review Suggestions</h3>
              <p className="text-gray-700">
                Review AI-suggested codes with confidence scores and justifications
              </p>
            </li>

            <li className="text-center">
              <div className="w-16 h-16 bg-blue-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4" aria-label="Step 4">
                4
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Capture Revenue</h3>
              <p className="text-gray-700">
                Export corrected codes and track revenue recovery over time
              </p>
            </li>
          </ol>
        </div>
      </section>

      {/* Stats Section */}
      <section className="bg-blue-600 py-20" aria-labelledby="stats-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 id="stats-heading" className="sr-only">Platform Statistics</h2>
          <div className="grid md:grid-cols-3 gap-8 text-center text-white">
            <div>
              <div className="text-4xl sm:text-5xl font-bold mb-2" aria-label="15 to 20 percent">15-20%</div>
              <div className="text-blue-50 text-base sm:text-lg font-medium">Average Revenue Increase</div>
            </div>
            <div>
              <div className="text-4xl sm:text-5xl font-bold mb-2" aria-label="99.9 percent">99.9%</div>
              <div className="text-blue-50 text-base sm:text-lg font-medium">Coding Accuracy</div>
            </div>
            <div>
              <div className="text-4xl sm:text-5xl font-bold mb-2" aria-label="2 minutes">2 min</div>
              <div className="text-blue-50 text-base sm:text-lg font-medium">Average Processing Time</div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20" aria-labelledby="cta-heading">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 id="cta-heading" className="text-3xl sm:text-4xl font-bold text-gray-900 mb-6">
            Ready to Optimize Your Revenue?
          </h2>
          <p className="text-lg sm:text-xl text-gray-700 mb-8">
            Join hundreds of healthcare providers who trust RevRx to maximize their billing potential.
          </p>
          <Link
            href="/register"
            className="inline-block px-8 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold text-lg transition-all shadow-lg hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transform hover:scale-105"
            aria-label="Start your 7-day free trial today"
          >
            Start Your Free Trial Today
          </Link>
        </div>
      </section>
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-12" role="contentinfo">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="text-white font-bold text-xl mb-4">RevRx</div>
              <p className="text-sm text-gray-300">
                AI-powered post-facto coding review for healthcare providers.
              </p>
            </div>
            <nav aria-label="Product links">
              <h3 className="text-white font-semibold mb-4">Product</h3>
              <ul className="space-y-2 text-sm">
                <li><Link href="/login" className="hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 rounded">Features</Link></li>
                <li><Link href="/login" className="hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 rounded">Pricing</Link></li>
                <li><Link href="/login" className="hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 rounded">Security</Link></li>
              </ul>
            </nav>
            <nav aria-label="Company links">
              <h3 className="text-white font-semibold mb-4">Company</h3>
              <ul className="space-y-2 text-sm">
                <li><Link href="/login" className="hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 rounded">About</Link></li>
                <li><Link href="/login" className="hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 rounded">Contact</Link></li>
                <li><Link href="/login" className="hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 rounded">Careers</Link></li>
              </ul>
            </nav>
            <nav aria-label="Legal links">
              <h3 className="text-white font-semibold mb-4">Legal</h3>
              <ul className="space-y-2 text-sm">
                <li><Link href="/login" className="hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 rounded">Privacy Policy</Link></li>
                <li><Link href="/login" className="hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 rounded">Terms of Service</Link></li>
                <li><Link href="/login" className="hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 rounded">HIPAA Compliance</Link></li>
              </ul>
            </nav>
          </div>
          <div className="border-t border-gray-800 mt-12 pt-8 text-sm text-center text-gray-300">
            <p>&copy; 2025 RevRx. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
