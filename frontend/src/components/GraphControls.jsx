import React from 'react';
import { useState } from 'react';
import { MoreHorizontal, Loader, ZapOff, Zap, Eye, EyeOff } from 'lucide-react';
import { Button } from './ui/button';

const GraphControls = ({ 
  loading, 
  nodeCount, 
  expandedNodes,
  toggleAutomaticLoading,
  isAutoLoadingEnabled,
  loadingMore,
  clearGraph,
  resetView,
  maxNodesSliderValue,
  setMaxNodesSliderValue,
  centerNodeDescription
}) => {
  const [showControls, setShowControls] = useState(false);
  
  // Add a function to truncate descriptions
  const truncateDescription = (desc, maxLength = 60) => {
    if (!desc) return 'No description available';
    return desc.length > maxLength 
      ? `${desc.substring(0, maxLength)}...` 
      : desc;
  };
  
  return (
    <div className="absolute bottom-4 right-4 z-10">
      {/* Floating control panel */}
      {showControls && (
        <div className="bg-gray-900/90 backdrop-blur-sm p-4 rounded-lg shadow-lg border border-gray-800 mb-2 w-64">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-medium">Graph Controls</h3>
            <button 
              onClick={() => setShowControls(false)}
              className="text-gray-400 hover:text-white"
            >
              <EyeOff size={16} />
            </button>
          </div>
          
          <div className="space-y-4">
            {/* Add description display here */}
            {centerNodeDescription && (
              <div className="text-xs text-gray-300 p-2 bg-gray-800/60 rounded-lg">
                <span className="text-gray-400 block mb-1">Center Image Description:</span>
                {truncateDescription(centerNodeDescription)}
              </div>
            )}
            
            <div className="flex justify-between items-center text-sm">
              <span>Nodes Loaded:</span>
              <span className="font-mono bg-gray-800 px-2 py-1 rounded">{nodeCount}</span>
            </div>
            
            <div className="flex justify-between items-center text-sm">
              <span>Expanded Nodes:</span>
              <span className="font-mono bg-gray-800 px-2 py-1 rounded">{expandedNodes}</span>
            </div>
            
            <div className="pt-2">
              <label className="text-xs text-gray-400 mb-1 block">Max Nodes: {maxNodesSliderValue}</label>
              <input 
                type="range" 
                min="50" 
                max="500" 
                step="50" 
                value={maxNodesSliderValue} 
                onChange={(e) => setMaxNodesSliderValue(parseInt(e.target.value))}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={toggleAutomaticLoading}
                className={`flex items-center justify-center gap-1 px-3 py-1 rounded text-xs ${
                  isAutoLoadingEnabled 
                    ? 'bg-blue-700 hover:bg-blue-600' 
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {isAutoLoadingEnabled ? <Zap size={12} /> : <ZapOff size={12} />}
                {isAutoLoadingEnabled ? 'Auto' : 'Manual'}
              </button>
              
              <button
                onClick={clearGraph}
                className="flex items-center justify-center gap-1 px-3 py-1 rounded bg-gray-700 hover:bg-gray-600 text-xs"
              >
                Clear
              </button>
              
              <button
                onClick={resetView}
                className="flex items-center justify-center gap-1 px-3 py-1 rounded bg-gray-700 hover:bg-gray-600 text-xs"
              >
                Center
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Toggle button */}
      <button 
        onClick={() => setShowControls(!showControls)}
        className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-800/80 backdrop-blur-sm shadow-lg border border-gray-700 hover:bg-gray-700"
      >
        {showControls ? <Eye size={18} /> : <MoreHorizontal size={18} />}
      </button>
      
      {/* Loading indicator */}
      {(loading || loadingMore) && (
        <div className="absolute -top-12 right-0 bg-gray-900/80 backdrop-blur-sm rounded-full p-2 shadow-lg border border-gray-800">
          <div className="flex items-center gap-2 px-2">
            <Loader size={14} className="animate-spin" />
            <span className="text-xs">{loading ? 'Loading' : 'Expanding'}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default GraphControls;