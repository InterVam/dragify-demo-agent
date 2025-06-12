'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import { format } from 'date-fns';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/solid';

interface Log {
  id: number;
  event_type: string;
  event_data: any;
  status: string;
  error_message: string | null;
  created_at: string;
}

export default function Home() {
  const [logs, setLogs] = useState<Log[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/logs');
      setLogs(response.data.logs);
      setLoading(false);
    } catch (err) {
      setError('Failed to fetch logs');
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    if (status === 'success') {
      return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
    }
    if (status === 'error') {
      return <XCircleIcon className="h-5 w-5 text-red-500" />;
    }
    return null;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold mb-4">Loading logs...</h1>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold mb-4 text-red-500">{error}</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">Event Logs</h1>
        
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          <ul className="divide-y divide-gray-200">
            {logs.map((log) => (
              <li key={log.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    {getStatusIcon(log.status)}
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-900">
                        {log.event_type}
                      </p>
                      <p className="text-sm text-gray-500">
                        {format(new Date(log.created_at), 'PPpp')}
                      </p>
                    </div>
                  </div>
                  <div className="ml-4">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      log.status === 'success' ? 'bg-green-100 text-green-800' :
                      log.status === 'error' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {log.status}
                    </span>
                  </div>
                </div>
                
                {log.error_message && (
                  <div className="mt-2">
                    <p className="text-sm text-red-600">{log.error_message}</p>
                  </div>
                )}
                
                <div className="mt-2">
                  <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                    {JSON.stringify(log.event_data, null, 2)}
                  </pre>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
} 