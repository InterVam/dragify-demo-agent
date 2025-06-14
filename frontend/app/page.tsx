"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { format } from "date-fns";

interface Log {
  id: number;
  event_type: string;
  event_data: any;
  status: string;
  error_message: string | null;
  created_at: string;
  updated_at?: string;
  team_id?: string;
}

interface LeadData {
  first_name?: string;
  last_name?: string;
  phone?: string;
  location?: string;
  property_type?: string;
  bedrooms?: string | number;
  budget?: number;
  team_id?: string;
  matched_projects?: string[];
}

interface OAuthStatus {
  slack: boolean;
  zoho: boolean;
  gmail: boolean;
}

export default function Home() {
  const [logs, setLogs] = useState<Log[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<string>("Disconnected");
  const [oauthStatus, setOauthStatus] = useState<OAuthStatus>({
    slack: false,
    zoho: false,
    gmail: false,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  // Properly handle WebSocket URL for both HTTP and HTTPS (ngrok)
  // Remove trailing slash to avoid double slashes
  const cleanApiUrl = API_URL.replace(/\/$/, '');
  const WS_URL = cleanApiUrl.replace("https://", "wss://").replace("http://", "ws://");

  useEffect(() => {
    fetchLogs();
    checkOAuthStatus();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      setConnectionStatus("Connecting...");
      console.log(`Attempting WebSocket connection to: ${WS_URL}/ws/logs`);
      const ws = new WebSocket(`${WS_URL}/ws/logs`);
      
      ws.onopen = () => {
        console.log("WebSocket connected successfully");
        setIsConnected(true);
        setConnectionStatus("Connected");
        wsRef.current = ws;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === "initial_events") {
            setLogs(data.events);
          } else if (data.type === "event_update") {
            setLogs(prevLogs => {
              const existingIndex = prevLogs.findIndex(log => log.id === data.event.id);
              if (existingIndex >= 0) {
                // Update existing event
                const newLogs = [...prevLogs];
                newLogs[existingIndex] = data.event;
                return newLogs;
              } else {
                // Add new event to the beginning
                return [data.event, ...prevLogs];
              }
            });
          }
        } catch (err) {
          console.error("Error parsing WebSocket message:", err);
        }
      };

      ws.onclose = (event) => {
        console.log("WebSocket disconnected", event.code, event.reason);
        setIsConnected(false);
        setConnectionStatus("Disconnected");
        wsRef.current = null;
        
        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket();
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setConnectionStatus("Error");
      };

    } catch (err) {
      console.error("Failed to connect WebSocket:", err);
      setConnectionStatus("Failed");
    }
  };

  const fetchLogs = async () => {
    setRefreshing(true);
    try {
      const response = await axios.get(`${API_URL}/api/logs`);
      setLogs(response.data.logs || []);
      setLoading(false);
    } catch (err) {
      setError("Failed to fetch logs");
      setLoading(false);
    } finally {
      setRefreshing(false);
    }
  };

  const checkOAuthStatus = async () => {
    try {
      const [slackRes, zohoRes, gmailRes] = await Promise.allSettled([
        axios.get(`${API_URL}/slack/status`),
        axios.get(`${API_URL}/zoho/status`),
        axios.get(`${API_URL}/gmail/status`),
      ]);
      setOauthStatus({
        slack: slackRes.status === "fulfilled" && slackRes.value.data.connected,
        zoho: zohoRes.status === "fulfilled" && zohoRes.value.data.connected,
        gmail: gmailRes.status === "fulfilled" && gmailRes.value.data.connected,
      });
    } catch (err) {}
  };

  const handleOAuth = async (service: string) => {
    try {
      const response = await axios.get(`${API_URL}/${service}/oauth/authorize`);
      const authUrl = response.data.auth_url || response.data.authorization_url;
      if (authUrl) {
        window.open(authUrl, "_blank", "width=600,height=600");
      }
    } catch (error) {}
  };

  const createTestEvent = async () => {
    try {
      await axios.post(`${API_URL}/api/test-event`);
    } catch (error) {
      console.error("Failed to create test event:", error);
    }
  };

  const formatBudget = (budget: number) => {
    if (budget >= 1000000) {
      return `$${(budget / 1000000).toFixed(1)}M`;
    } else if (budget >= 1000) {
      return `$${(budget / 1000).toFixed(0)}K`;
    }
    return `$${budget.toLocaleString()}`;
  };

  const extractLeadData = (eventData: any): LeadData | null => {
    if (eventData?.lead_info) return eventData.lead_info;
    if (eventData?.first_name) return eventData;
    return null;
  };

  const getConnectedCount = () => {
    return Object.values(oauthStatus).filter(Boolean).length;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-400 border-t-transparent mx-auto mb-6"></div>
            <div className="absolute inset-0 rounded-full h-12 w-12 border-4 border-purple-400 border-t-transparent animate-ping opacity-20 mx-auto"></div>
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Loading Dashboard</h2>
          <p className="text-blue-200">Fetching latest data...</p>
        </div>
      </div>
    );
  }

    return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900">
      {/* Header */}
      <div className="bg-white/10 backdrop-blur-md border-b border-white/20 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
                Dragify AI Agent
              </h1>
              <p className="text-blue-200 mt-1">Real Estate Lead Processing Dashboard</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className={`flex items-center space-x-2 border rounded-full px-4 py-2 backdrop-blur-sm ${
                isConnected 
                  ? "bg-green-500/20 border-green-400/30" 
                  : "bg-red-500/20 border-red-400/30"
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  isConnected ? "bg-green-400 animate-pulse shadow-lg shadow-green-400/50" : "bg-red-400"
                }`}></div>
                <span className={`text-sm font-medium ${
                  isConnected ? "text-green-200" : "text-red-200"
                }`}>
                  {connectionStatus}
                </span>
              </div>
              <button
                onClick={createTestEvent}
                className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-4 py-2 rounded-lg font-medium transition-all duration-200 transform hover:scale-105 shadow-lg"
              >
                Test Event
              </button>
              <button
                onClick={() => {
                  fetchLogs();
                  checkOAuthStatus();
                }}
                disabled={refreshing}
                className="flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-4 py-2 rounded-lg font-medium transition-all duration-200 transform hover:scale-105 shadow-lg disabled:opacity-50 disabled:transform-none"
              >
                <span>{refreshing ? "Refreshing..." : "Refresh"}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-gradient-to-br from-blue-500/20 to-blue-600/20 backdrop-blur-md rounded-xl border border-blue-400/30 p-6 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-blue-200 uppercase tracking-wider mb-2">Total Events</span>
              <span className="text-3xl font-bold text-white">{logs.length}</span>
              <div className="mt-2 h-1 bg-blue-400/30 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-blue-400 to-blue-500 rounded-full animate-pulse"></div>
              </div>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-emerald-500/20 to-green-600/20 backdrop-blur-md rounded-xl border border-emerald-400/30 p-6 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-emerald-200 uppercase tracking-wider mb-2">Successful</span>
              <span className="text-3xl font-bold text-white">{logs.filter(log => log.status === "success").length}</span>
              <div className="mt-2 h-1 bg-emerald-400/30 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-emerald-400 to-green-500 rounded-full animate-pulse"></div>
              </div>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-purple-500/20 to-violet-600/20 backdrop-blur-md rounded-xl border border-purple-400/30 p-6 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-purple-200 uppercase tracking-wider mb-2">Connected</span>
              <span className="text-3xl font-bold text-white">{getConnectedCount()}/3</span>
              <div className="mt-2 h-1 bg-purple-400/30 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-purple-400 to-violet-500 rounded-full animate-pulse"></div>
              </div>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-amber-500/20 to-orange-600/20 backdrop-blur-md rounded-xl border border-amber-400/30 p-6 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-amber-200 uppercase tracking-wider mb-2">Processing</span>
              <span className="text-3xl font-bold text-white">{logs.filter(log => log.status === "processing").length}</span>
              <div className="mt-2 h-1 bg-amber-400/30 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-amber-400 to-orange-500 rounded-full animate-pulse"></div>
              </div>
            </div>
          </div>
        </div>

        {/* OAuth Integration Cards */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-6">Integration Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { name: "Slack", key: "slack", description: "Receive lead messages", gradient: "from-purple-500 to-indigo-600", emoji: "💬" },
              { name: "Zoho CRM", key: "zoho", description: "Store lead data", gradient: "from-blue-500 to-cyan-600", emoji: "🏢" },
              { name: "Gmail", key: "gmail", description: "Send notifications", gradient: "from-red-500 to-pink-600", emoji: "📧" },
            ].map((service) => (
              <div key={service.key} className="bg-white/10 backdrop-blur-md rounded-xl border border-white/20 p-6 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center">
                    <span className="text-2xl mr-3">{service.emoji}</span>
                    <div>
                      <h3 className="text-lg font-semibold text-white">{service.name}</h3>
                      <p className="text-sm text-blue-200">{service.description}</p>
                    </div>
                  </div>
                  <div className={`w-3 h-3 rounded-full ${oauthStatus[service.key as keyof OAuthStatus] ? "bg-green-400 shadow-lg shadow-green-400/50" : "bg-slate-400"} animate-pulse`}></div>
                </div>
                
                <div className="mb-4">
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${oauthStatus[service.key as keyof OAuthStatus] ? "bg-green-500/20 text-green-300 border border-green-400/30" : "bg-slate-500/20 text-slate-300 border border-slate-400/30"}`}>
                    {oauthStatus[service.key as keyof OAuthStatus] ? "✓ Connected" : "○ Not Connected"}
                    </span>
                </div>
                
                <button
                  onClick={() => handleOAuth(service.key)}
                  disabled={oauthStatus[service.key as keyof OAuthStatus]}
                  className={`w-full px-4 py-3 rounded-lg font-semibold transition-all duration-200 transform hover:scale-105 ${
                    oauthStatus[service.key as keyof OAuthStatus]
                      ? "bg-slate-600/50 text-slate-400 cursor-not-allowed"
                      : `bg-gradient-to-r ${service.gradient} hover:shadow-lg text-white shadow-md`
                  }`}
                >
                  {oauthStatus[service.key as keyof OAuthStatus] ? "Connected" : `Connect ${service.name}`}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-500/20 border border-red-400/30 rounded-xl p-4 mb-8 backdrop-blur-md">
            <div className="flex">
              <div className="ml-1">
                <h3 className="text-sm font-semibold text-red-300">Error</h3>
                <p className="text-sm text-red-200 mt-1">{error}</p>
              </div>
            </div>
                  </div>
                )}
                
        {/* Activity Feed */}
        <div className="bg-white/10 backdrop-blur-md rounded-xl border border-white/20 shadow-xl">
          <div className="px-6 py-4 border-b border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">Live Activity Feed</h2>
                <p className="text-blue-200 mt-1">Real-time event processing logs</p>
              </div>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-400 animate-pulse" : "bg-red-400"}`}></div>
                <span className="text-sm text-blue-200">
                  {isConnected ? "Live Updates" : "Offline"}
                </span>
              </div>
            </div>
          </div>
          
          <div className="divide-y divide-white/10 max-h-96 overflow-y-auto">
            {logs.length === 0 ? (
              <div className="px-6 py-16 text-center">
                <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4 border border-blue-400/30">
                  <span className="text-2xl">📊</span>
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">No events yet</h3>
                <p className="text-blue-200 max-w-sm mx-auto">Events will appear here in real-time as they occur. Try the "Test Event" button to see it in action!</p>
              </div>
            ) : (
              logs.map((log) => {
                const leadData = extractLeadData(log.event_data);
                return (
                  <div key={log.id} className="px-6 py-6 hover:bg-white/5 transition-colors">
                    {/* Event Header */}
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-white capitalize">{log.event_type.replace("_", " ")}</h3>
                        <p className="text-sm text-blue-200">{format(new Date(log.created_at), "MMM d, yyyy • h:mm:ss a")}</p>
                      </div>
                      <span className={`px-3 py-1 text-sm font-semibold rounded-full ${
                        log.status === "success" ? "bg-green-500/20 text-green-300 border border-green-400/30" :
                        log.status === "error" ? "bg-red-500/20 text-red-300 border border-red-400/30" :
                        log.status === "processing" ? "bg-amber-500/20 text-amber-300 border border-amber-400/30 animate-pulse" :
                        "bg-slate-500/20 text-slate-300 border border-slate-400/30"
                      }`}>{log.status}</span>
                    </div>
                    
                    {/* Lead Data Display */}
                    {leadData && (
                      <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-xl p-4 mb-4 border border-blue-400/20 backdrop-blur-sm">
                        <h4 className="text-sm font-semibold text-blue-200 mb-3">Lead Information</h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                          {leadData.first_name && (
                            <div className="bg-white/10 rounded-lg p-3 border border-white/20">
                              <p className="text-xs text-blue-200 mb-1">Name</p>
                              <p className="text-sm font-semibold text-white">{leadData.first_name} {leadData.last_name}</p>
                            </div>
                          )}
                          {leadData.phone && (
                            <div className="bg-white/10 rounded-lg p-3 border border-white/20">
                              <p className="text-xs text-blue-200 mb-1">Phone</p>
                              <p className="text-sm font-semibold text-white">{leadData.phone}</p>
                            </div>
                          )}
                          {leadData.location && (
                            <div className="bg-white/10 rounded-lg p-3 border border-white/20">
                              <p className="text-xs text-blue-200 mb-1">Location</p>
                              <p className="text-sm font-semibold text-white">{leadData.location}</p>
                            </div>
                          )}
                          {leadData.property_type && (
                            <div className="bg-white/10 rounded-lg p-3 border border-white/20">
                              <p className="text-xs text-blue-200 mb-1">Property Type</p>
                              <p className="text-sm font-semibold text-white capitalize">{leadData.property_type}</p>
                            </div>
                          )}
                          {leadData.bedrooms && (
                            <div className="bg-white/10 rounded-lg p-3 border border-white/20">
                              <p className="text-xs text-blue-200 mb-1">Bedrooms</p>
                              <p className="text-sm font-semibold text-white">{leadData.bedrooms} bedrooms</p>
                            </div>
                          )}
                          {leadData.budget && (
                            <div className="bg-white/10 rounded-lg p-3 border border-white/20">
                              <p className="text-xs text-blue-200 mb-1">Budget</p>
                              <p className="text-sm font-semibold text-white">{formatBudget(leadData.budget)}</p>
                            </div>
                          )}
                        </div>
                        
                        {/* Matched Projects */}
                        {leadData.matched_projects && leadData.matched_projects.length > 0 && (
                          <div className="mt-4">
                            <h5 className="text-sm font-semibold text-blue-200 mb-2">Matched Projects</h5>
                            <div className="flex flex-wrap gap-2">
                              {leadData.matched_projects.map((project, index) => (
                                <span key={index} className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-gradient-to-r from-blue-500/20 to-purple-500/20 text-blue-200 border border-blue-400/30">
                                  {project}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Error Message */}
                    {log.error_message && (
                      <div className="bg-red-500/20 border border-red-400/30 rounded-lg p-3 mb-4">
                        <p className="text-sm text-red-200 font-medium">{log.error_message}</p>
                      </div>
                    )}
                    
                    {/* Raw Event Data (Collapsible) */}
                    <details className="group">
                      <summary className="cursor-pointer text-sm text-blue-300 hover:text-white select-none transition-colors">
                        <span>View technical details</span>
                      </summary>
                      <div className="mt-3 bg-slate-900/50 rounded-lg p-4 overflow-x-auto border border-slate-700/50">
                        <pre className="text-xs text-slate-200 font-mono">{JSON.stringify(log.event_data, null, 2)}</pre>
                      </div>
                    </details>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
} 