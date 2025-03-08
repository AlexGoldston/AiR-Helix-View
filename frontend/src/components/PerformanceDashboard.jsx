// frontend/src/components/PerformanceDashboard.jsx
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const PerformanceDashboard = ({ isVisible }) => {
  const [performanceData, setPerformanceData] = useState(null);
  const [error, setError] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pollInterval, setPollInterval] = useState(null);

  // Function to fetch performance data
  const fetchPerformanceData = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:5001/debug/performance');
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      const data = await response.json();
      setPerformanceData(data.metrics);
      
      // Add to chart data
      setChartData(prevData => {
        const newPoint = {
          time: new Date().toLocaleTimeString(),
          avgTime: data.metrics.avg_time * 1000, // Convert to ms
          totalQueries: data.metrics.total_queries
        };
        
        // Keep last 20 data points
        const updatedData = [...prevData, newPoint];
        if (updatedData.length > 20) {
          return updatedData.slice(updatedData.length - 20);
        }
        return updatedData;
      });
      
      setError(null);
    } catch (err) {
      setError(`Error fetching performance data: ${err.message}`);
      console.error('Performance data fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Set up polling when component becomes visible
  useEffect(() => {
    if (isVisible) {
      // Initial fetch
      fetchPerformanceData();
      
      // Set up polling every 10 seconds
      const interval = setInterval(fetchPerformanceData, 10000);
      setPollInterval(interval);
      
      return () => {
        if (pollInterval) {
          clearInterval(pollInterval);
        }
      };
    } else {
      // Clear polling when not visible
      if (pollInterval) {
        clearInterval(pollInterval);
        setPollInterval(null);
      }
    }
  }, [isVisible]);

  if (!isVisible) {
    return null;
  }

  return (
    <div className="bg-gray-900/90 backdrop-blur-sm p-4 rounded-lg shadow-lg border border-gray-800 my-4">
      <h2 className="text-lg font-medium mb-4">Neo4j Performance Dashboard</h2>
      
      {loading && <div className="text-blue-400 mb-2">Refreshing data...</div>}
      {error && <div className="text-red-400 mb-2">{error}</div>}
      
      {performanceData && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-gray-800 p-3 rounded-md">
              <div className="text-sm text-gray-400">Total Queries</div>
              <div className="text-xl font-bold">{performanceData.total_queries}</div>
            </div>
            
            <div className="bg-gray-800 p-3 rounded-md">
              <div className="text-sm text-gray-400">Average Time</div>
              <div className="text-xl font-bold">{(performanceData.avg_time * 1000).toFixed(2)} ms</div>
            </div>
            
            <div className="bg-gray-800 p-3 rounded-md">
              <div className="text-sm text-gray-400">Min Time</div>
              <div className="text-xl font-bold">{(performanceData.min_time * 1000).toFixed(2)} ms</div>
            </div>
            
            <div className="bg-gray-800 p-3 rounded-md">
              <div className="text-sm text-gray-400">Max Time</div>
              <div className="text-xl font-bold">{(performanceData.max_time * 1000).toFixed(2)} ms</div>
            </div>
          </div>
          
          <div className="bg-gray-800 p-3 rounded-md">
            <h3 className="text-md font-medium mb-2">Driver Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <div>
                <span className="text-gray-400">Neo4j Driver: </span>
                <span>{performanceData.driver_info?.neo4j_driver_version || 'Unknown'}</span>
              </div>
              <div>
                <span className="text-gray-400">Rust Extension: </span>
                <span className={performanceData.driver_info?.rust_extension_available ? 'text-green-400' : 'text-red-400'}>
                  {performanceData.driver_info?.rust_extension_available 
                    ? `Enabled (${performanceData.driver_info.rust_extension_version})` 
                    : 'Disabled'}
                </span>
              </div>
            </div>
          </div>
          
          {/* Query Type Performance */}
          <div className="bg-gray-800 p-3 rounded-md">
            <h3 className="text-md font-medium mb-2">Query Performance by Type</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full bg-gray-900 rounded-md">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="px-4 py-2 text-left">Query Type</th>
                    <th className="px-4 py-2 text-right">Count</th>
                    <th className="px-4 py-2 text-right">Avg Time (ms)</th>
                    <th className="px-4 py-2 text-right">Min Time (ms)</th>
                    <th className="px-4 py-2 text-right">Max Time (ms)</th>
                  </tr>
                </thead>
                <tbody>
                  {performanceData.query_types && Object.entries(performanceData.query_types).map(([type, metrics]) => (
                    <tr key={type} className="border-b border-gray-800">
                      <td className="px-4 py-2">{type}</td>
                      <td className="px-4 py-2 text-right">{metrics.count}</td>
                      <td className="px-4 py-2 text-right">{(metrics.avg_time * 1000).toFixed(2)}</td>
                      <td className="px-4 py-2 text-right">{(metrics.min_time * 1000).toFixed(2)}</td>
                      <td className="px-4 py-2 text-right">{(metrics.max_time * 1000).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          
          {/* Performance Chart */}
          {chartData.length > 1 && (
            <div className="bg-gray-800 p-3 rounded-md">
              <h3 className="text-md font-medium mb-2">Performance Trend</h3>
              <div className="h-60">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                    <XAxis dataKey="time" stroke="#888" tick={{ fill: '#888' }} />
                    <YAxis yAxisId="left" stroke="#888" tick={{ fill: '#888' }} />
                    <YAxis yAxisId="right" orientation="right" stroke="#888" tick={{ fill: '#888' }} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#222', borderColor: '#555' }} 
                      labelStyle={{ color: '#fff' }}
                    />
                    <Legend />
                    <Line 
                      yAxisId="left"
                      type="monotone" 
                      dataKey="avgTime" 
                      name="Avg Query Time (ms)" 
                      stroke="#4285F4" 
                      activeDot={{ r: 8 }} 
                    />
                    <Line 
                      yAxisId="right"
                      type="monotone" 
                      dataKey="totalQueries" 
                      name="Total Queries" 
                      stroke="#34A853" 
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
          
          <div className="flex justify-end">
            <button 
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
              onClick={fetchPerformanceData}
              disabled={loading}
            >
              Refresh Data
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PerformanceDashboard;