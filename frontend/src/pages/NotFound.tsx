/**
 * NotFound: 404 error page
 */

import { Link } from 'react-router-dom'

export function NotFound() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-900 mb-2">404</h1>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Page Not Found</h2>
        <p className="text-gray-600 mb-8 max-w-md mx-auto">
          The page you're looking for doesn't exist. It might have been moved or deleted.
        </p>
        <Link
          to="/dashboard"
          className="inline-block px-6 py-2 bg-blue-500 text-white font-medium rounded-lg hover:bg-blue-600 transition"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  )
}
