/**
 * Loading spinner component with status message.
 */

'use client';

interface LoadingSpinnerProps {
  message?: string;
  progress?: number;
}

export default function LoadingSpinner({
  message = 'Processing...',
  progress,
}: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12">
      {/* Spinner */}
      <div className="relative w-20 h-20">
        <div className="absolute inset-0 border-4 border-gray-200 rounded-full"></div>
        <div className="absolute inset-0 border-4 border-primary-600 rounded-full border-t-transparent animate-spin"></div>
      </div>

      {/* Message */}
      <p className="mt-6 text-lg font-medium text-gray-700">{message}</p>

      {/* Progress Bar */}
      {progress !== undefined && (
        <div className="mt-4 w-64">
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-600 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <p className="mt-2 text-sm text-center text-gray-600">
            {progress}% complete
          </p>
        </div>
      )}

      {/* Processing Steps */}
      <div className="mt-8 text-sm text-gray-500 space-y-2 text-center max-w-md">
        <p>Gathering intelligence from multiple sources...</p>
        <p>Validating data with LLM agents...</p>
        <p>Generating professional slideshow...</p>
      </div>
    </div>
  );
}
