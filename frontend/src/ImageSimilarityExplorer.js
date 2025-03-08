import React, { useState, useEffect, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './components/ui/sheet';
import { Slider } from './components/ui/slider';
import { Button } from './components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './components/ui/dialog';
import { Menu, ZoomIn, ZoomOut, Download, Info } from 'lucide-react';
import GraphControls from './components/GraphControls';
import _ from 'lodash';

const ImageSimilarityExplorer = () => {
  // State management
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [centerImage, setCenterImage] = useState('allianz_stadium_sydney01.jpg');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.63);
  const [neighborLimit, setNeighborLimit] = useState(20);
  const [debugData, setDebugData] = useState(null);
  const [openModal, setOpenModal] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const [isAutoLoadingEnabled, setIsAutoLoadingEnabled] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [maxNodesLimit, setMaxNodesLimit] = useState(200);
  const [extendedMode, setExtendedMode] = useState(true);  // Enable by default
  const [neighborDepth, setNeighborDepth] = useState(2);
  const [limitPerLevel, setLimitPerLevel] = useState(10);
  
  // Refs
  const imagesCache = useRef({});
  const graphRef = useRef(null);
  const loadQueue = useRef([]);
  const processingQueue = useRef(false);
  const viewportBoundsRef = useRef(null);
  
  // Extract filename from path
  const getImageName = useCallback((path) => {
    if (!path) return 'unknown';
    
    // Remove any "images/" prefix
    let filename = path;
    if (filename.startsWith('images/')) {
      filename = filename.substring(7);
    }
    
    // Remove query parameters
    filename = filename.split('?')[0];
    
    // Get just the filename
    return filename.split('/').pop().split('\\').pop();
  }, []);
   
  // Preload an image and store it in cache
  const preloadImage = useCallback((path) => {
    return new Promise((resolve, reject) => {
      if (!path) {
        reject(new Error("Invalid path"));
        return;
      }
      
      const filename = getImageName(path);
      
      // Skip if already in cache
      if (imagesCache.current[path]) {
        resolve(imagesCache.current[path]);
        return;
      }
      
      const img = new Image();
      
      img.onload = () => {
        imagesCache.current[path] = img;
        resolve(img);
      };
      
      img.onerror = (err) => {
        console.error(`Failed to load image: ${path} (${filename})`, err);
        reject(err);
      };
      
      // Use absolute URL with clean filename
      img.src = `http://localhost:5001/static/${filename}`;
      
      // Set a timeout to avoid hanging preloads
      setTimeout(() => {
        if (!imagesCache.current[path]) {
          reject(new Error("Image load timeout"));
        }
      }, 5000);
    });
  }, [getImageName]);

  // Process queue of nodes to load
  const processLoadQueue = useCallback(async () => {
    if (loadQueue.current.length === 0) {
      processingQueue.current = false;
      setLoadingMore(false);
      return;
    }
    
    // If we're at the node limit, stop expanding
    if (graphData.nodes.length >= maxNodesLimit) {
      console.log(`Reached max nodes limit (${maxNodesLimit})`);
      loadQueue.current = [];
      processingQueue.current = false;
      setLoadingMore(false);
      return;
    }
    
    processingQueue.current = true;
    setLoadingMore(true);
    
    // Take first node from the queue
    const nodeId = loadQueue.current.shift();
    
    // Skip if already expanded
    if (expandedNodes.has(nodeId)) {
      setLoadingMore(false);
      setTimeout(() => processLoadQueue(), 50);
      return;
    }
    
    try {
      // Find the path for this node
      const node = graphData.nodes.find(n => n.id === nodeId);
      if (!node) {
        setLoadingMore(false);
        setTimeout(() => processLoadQueue(), 50);
        return;
      }
      
      // Load neighbors for this node
      const filename = getImageName(node.path);
      const response = await fetch(
        `http://localhost:5001/neighbors?image_path=${encodeURIComponent(filename)}&threshold=${similarityThreshold}&limit=${neighborLimit}`
      );
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Merge with existing data
      const newGraphData = mergeGraphData(graphData, data);
      
      // Update graph data
      setGraphData(newGraphData);
      
      // Mark as expanded
      setExpandedNodes(prev => {
        const newSet = new Set(prev);
        newSet.add(nodeId);
        return newSet;
      });
      
      // Preload images for new nodes
      const newNodes = data.nodes.filter(n => 
        !graphData.nodes.some(existingNode => existingNode.id === n.id)
      );
      
      newNodes.forEach(node => {
        preloadImage(node.path).catch(() => {});
      });
    } catch (error) {
      console.error(`Error expanding node ${nodeId}:`, error);
    }
    
    setLoadingMore(false);
    
    // Process next batch with a short delay
    setTimeout(() => processLoadQueue(), 300);
  }, [graphData, expandedNodes, getImageName, maxNodesLimit, neighborLimit, preloadImage, similarityThreshold]);

  // Viewport change handler
  const handleViewportChange = useCallback(() => {
    if (!graphRef.current) return;
    
    // Get current viewport information
    const { x, y, k } = graphRef.current.zoom();
    
    // Use window dimensions
    const width = window.innerWidth;
    const height = window.innerHeight;
    
    // Calculate viewport boundaries with buffer
    const bounds = {
      xMin: (0 - x) / k - 200,
      xMax: (width - x) / k + 200,
      yMin: (0 - y) / k - 200,
      yMax: (height - y) / k + 200
    };
    
    viewportBoundsRef.current = bounds;
    
    // If auto-loading is enabled and not in extended mode, find nodes to expand
    if (isAutoLoadingEnabled && !extendedMode && graphData.nodes.length > 0) {
      // Find visible nodes
      const visibleNodes = graphData.nodes.filter(node => 
        node.x >= bounds.xMin && node.x <= bounds.xMax &&
        node.y >= bounds.yMin && node.y <= bounds.yMax
      );
      
      // Find unexpanded visible nodes
      const unexpandedNodes = visibleNodes.filter(node => 
        !expandedNodes.has(node.id) && 
        !loadQueue.current.includes(node.id)
      );
      
      // Add to load queue (max 3)
      const nodesToQueue = unexpandedNodes.slice(0, 3);
      if (nodesToQueue.length > 0) {
        loadQueue.current.push(...nodesToQueue.map(node => node.id));
        
        // Start processing queue if not already
        if (!processingQueue.current) {
          processLoadQueue();
        }
      }
    }
  }, [expandedNodes, graphData.nodes, isAutoLoadingEnabled, extendedMode, processLoadQueue]);

  // Throttled version of viewport change handler to avoid too many calls
  const throttledViewportChangeHandler = useCallback(
    _.debounce(handleViewportChange, 300),
  [handleViewportChange]
);

// Merge graph data without duplicates
const mergeGraphData = useCallback((currentData, newData) => {
  // Convert newData.edges to expected format
  const newLinks = newData.edges ? newData.edges.map(edge => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    value: edge.weight
  })) : [];
  
  // Get current node and link IDs
  const existingNodeIds = new Set(currentData.nodes.map(n => n.id));
  const existingLinkIds = new Set(currentData.links.map(l => l.id));
  
  // Add new nodes that don't already exist
  const filteredNewNodes = newData.nodes ? 
    newData.nodes.filter(node => !existingNodeIds.has(node.id)) : 
    [];
  
  // Add new links that don't already exist
  const filteredNewLinks = newLinks.filter(link => !existingLinkIds.has(link.id));
  
  // Return merged data
  return {
    nodes: [...currentData.nodes, ...filteredNewNodes],
    links: [...currentData.links, ...filteredNewLinks]
  };
}, []);




// Fetch graph data from API
useEffect(() => {
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    setExpandedNodes(new Set());
    loadQueue.current = [];
    
    try {
      // Get filename
      const filename = getImageName(centerImage);
      
      // Choose endpoint and parameters based on mode
      let url;
      if (extendedMode) {
        url = `http://localhost:5001/extended-neighbors?image_path=${encodeURIComponent(filename)}&threshold=${similarityThreshold}&depth=${neighborDepth}&limit_per_level=${limitPerLevel}&max_nodes=${maxNodesLimit}`;
        console.log(`Fetching extended data for ${centerImage} with depth ${neighborDepth}`);
      } else {
        url = `http://localhost:5001/neighbors?image_path=${encodeURIComponent(filename)}&threshold=${similarityThreshold}&limit=${neighborLimit}`;
        console.log(`Fetching direct neighbors for ${centerImage}`);
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const apiData = await response.json();
      console.log("API response:", apiData);
      setDebugData(apiData);
      
      // Rest of your data processing...
      
      // Transform the API response to match ForceGraph expected format
      const graphData = {
        nodes: [],
        links: []
      };

      // Find center node and mark as expanded
      const centerNode = apiData.nodes.find(node => node.isCenter);
      if (centerNode) {
        // Add to expanded nodes set since center is already expanded
        setExpandedNodes(new Set([centerNode.id]));
      }
      
      // Process all nodes from the API response
      for (const node of apiData.nodes) {
        graphData.nodes.push({
          id: node.id,
          path: node.path,
          label: node.label || getImageName(node.path),
          isCenter: node.isCenter || false,
          level: node.level || 0  // Use level if available for coloring
        });
      }
      
      // Process all edges from the API response
      for (const edge of apiData.edges) {
        graphData.links.push({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          value: edge.weight
        });
      }

      console.log("Processed graph data:", graphData);
      
      // Preload images for better rendering
      const preloadPromises = graphData.nodes.map(node => 
        preloadImage(node.path).catch(() => console.warn(`Failed to preload image: ${node.path}`))
      );
      
      await Promise.allSettled(preloadPromises);
      setGraphData(graphData);
      
      // Adjust graph physics after setting data
      if (graphRef.current) {
        setTimeout(() => {
          if (graphRef.current.d3Force('charge')) {
            // Stronger charge force for more spread out display when in extended mode
            graphRef.current.d3Force('charge').strength(extendedMode ? -700 : -500);
          }
          if (graphRef.current.d3Force('link')) {
            // Extended mode may need longer links for better visibility
            graphRef.current.d3Force('link').distance(extendedMode ? 200 : 150);
          }
          graphRef.current.zoomToFit(1000);
        }, 1000);
      }
    } catch (err) {
      console.error("Error fetching graph data:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  fetchData();
}, [centerImage, similarityThreshold, neighborLimit, extendedMode, neighborDepth, limitPerLevel, maxNodesLimit, getImageName, preloadImage, mergeGraphData]);

// Effect to calculate initial viewport
useEffect(() => {
  if (graphRef.current) {
    // Initial viewport calculation
    setTimeout(throttledViewportChangeHandler, 500);
  }
}, [graphData, throttledViewportChangeHandler]);

// Effect to process queue when auto-loading changes
useEffect(() => {
  if (isAutoLoadingEnabled && loadQueue.current.length > 0 && !processingQueue.current) {
    processLoadQueue();
  }
}, [isAutoLoadingEnabled, processLoadQueue]);

const clickTimeoutRef = useRef(null);

const handleNodeClick = useCallback(node => {
  // Clear any existing timeout
  if (clickTimeoutRef.current) {
    clearTimeout(clickTimeoutRef.current);
    clickTimeoutRef.current = null;
  }
  
  // Set a new timeout
  clickTimeoutRef.current = setTimeout(() => {
    console.log("Node clicked:", node);
    if (node && node.path) {
      setSelectedNode(node);
      setOpenModal(true);
    }
    clickTimeoutRef.current = null;
  }, 750); // 250ms delay - adjust as needed
}, []);

const handleNodeDoubleClick = useCallback(node => {
  // Clear the single-click timeout to prevent modal from opening
  if (clickTimeoutRef.current) {
    clearTimeout(clickTimeoutRef.current);
    clickTimeoutRef.current = null;
  }
  
  // Add node to load queue with high priority
  loadQueue.current = [node.id, ...loadQueue.current];
  
  // Start processing queue if not already
  if (!processingQueue.current) {
    processLoadQueue();
  }
}, [processLoadQueue]);

// Change center image 
const handleSetAsCenterImage = useCallback(() => {
  if (selectedNode && !selectedNode.isCenter) {
    setCenterImage(selectedNode.path);
    setOpenModal(false);
  }
}, [selectedNode]);

// Helper function to get similarity value for a node
const getSimilarity = useCallback((node, data) => {
  if (node.isCenter) return 1;
  
  const link = data.links.find(link => {
    if (typeof link.source === 'object' && typeof link.target === 'object') {
      return (link.source.id === node.id || link.target.id === node.id);
    }
    return (link.source === node.id || link.target === node.id);
  });
  
  return link ? link.value : null;
}, []);

// Reset zoom function
const handleResetZoom = useCallback(() => {
  if (graphRef.current) {
    graphRef.current.zoomToFit(500);
  }
}, []);

// Zoom in function
const handleZoomIn = useCallback(() => {
  if (graphRef.current) {
    const currentZoom = graphRef.current.zoom();
    graphRef.current.zoom(currentZoom * 1.2, 400);
  }
}, []);

// Zoom out function
const handleZoomOut = useCallback(() => {
  if (graphRef.current) {
    const currentZoom = graphRef.current.zoom();
    graphRef.current.zoom(currentZoom / 1.2, 400);
  }
}, []);

// Reset expanded nodes
const clearGraph = useCallback(() => {
  setExpandedNodes(new Set());
  loadQueue.current = [];
  // Reset to only the center node
  const centerNode = graphData.nodes.find(n => n.isCenter);
  if (centerNode) {
    setGraphData({
      nodes: [centerNode],
      links: []
    });
  }
}, [graphData.nodes]);

// Reset view to center
const resetView = useCallback(() => {
  if (graphRef.current) {
    graphRef.current.zoomToFit(400);
  }
}, []);

// Toggle automatic loading
const toggleAutomaticLoading = useCallback(() => {
  setIsAutoLoadingEnabled(prev => !prev);
}, []);

return (
  <div className="relative flex flex-col h-screen w-full overflow-hidden">
    {/* Animated Background */}
    <div 
      className="absolute inset-0 w-full h-full bg-gray-950 overflow-hidden z-0 pointer-events-none"
      style={{
        background: `
          radial-gradient(circle at 0% 0%, rgba(45, 55, 72, 0.1) 0%, transparent 50%),
          radial-gradient(circle at 100% 0%, rgba(49, 130, 206, 0.05) 0%, transparent 50%),
          radial-gradient(circle at 100% 100%, rgba(76, 81, 191, 0.1) 0%, transparent 50%),
          radial-gradient(circle at 0% 100%, rgba(66, 153, 225, 0.05) 0%, transparent 50%),
          #0f1117
        `
      }}
    >
      {/* SVG Animated Gradient */}
      <svg width="100%" height="100%" className="opacity-20">
        <defs>
          <filter id="gooey" height="300%" width="100%" x="-50%" y="-100%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur" />
            <feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 30 -11" result="gooey" />
          </filter>
          <linearGradient id="gradient1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#4285F4" stopOpacity="0.2">
              <animate attributeName="stop-color" values="#4285F4;#34A853;#FBBC05;#EA4335;#4285F4" dur="20s" repeatCount="indefinite" />
            </stop>
            <stop offset="100%" stopColor="#34A853" stopOpacity="0.2">
              <animate attributeName="stop-color" values="#34A853;#FBBC05;#EA4335;#4285F4;#34A853" dur="20s" repeatCount="indefinite" />
            </stop>
          </linearGradient>
        </defs>
        <g filter="url(#gooey)">
          <circle cx="25%" cy="25%" r="25%" fill="url(#gradient1)">
            <animate attributeName="cx" values="25%;75%;25%" dur="30s" repeatCount="indefinite" />
            <animate attributeName="cy" values="25%;75%;25%" dur="30s" repeatCount="indefinite" />
          </circle>
          <circle cx="75%" cy="75%" r="25%" fill="url(#gradient1)">
            <animate attributeName="cx" values="75%;25%;75%" dur="30s" repeatCount="indefinite" />
            <animate attributeName="cy" values="75%;25%;75%" dur="30s" repeatCount="indefinite" />
          </circle>
        </g>
      </svg>
    </div>
    
    {/* Top Navigation */}
    <div className="z-10 flex items-center justify-between p-4 bg-gray-950/80 backdrop-blur-sm border-b border-gray-800">
      <div className="flex items-center">
        <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="mr-2">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-80 bg-gray-950 border-r border-gray-800">
            <SheetHeader>
              <SheetTitle className="text-2xl font-bold bg-gradient-to-r from-blue-500 to-teal-400 bg-clip-text text-transparent">Controls</SheetTitle>
            </SheetHeader>
            
            <div className="py-6 space-y-6">
              <div>
                <h3 className="mb-4 text-lg font-medium">Current Image</h3>
                <div className="bg-gray-900 rounded-lg p-2 mb-4">
                  <img 
                    src={`http://localhost:5001/static/${getImageName(centerImage)}`}
                    alt={getImageName(centerImage)}
                    className="w-full h-48 object-contain rounded-md border border-gray-800"
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = "/api/placeholder/200/120";
                    }}
                  />
                  <p className="mt-2 text-sm text-gray-400 text-center truncate">{getImageName(centerImage)}</p>
                </div>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-400 mb-2 block">
                    Similarity Threshold: {similarityThreshold.toFixed(2)}
                  </label>
                  <Slider 
                    defaultValue={[similarityThreshold]} 
                    min={0.5} 
                    max={0.99} 
                    step={0.01}
                    onValueChange={(values) => setSimilarityThreshold(values[0])}
                    className="w-full"
                  />
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-400 mb-2 block">
                    Max Neighbors: {neighborLimit}
                  </label>
                  <Slider 
                    defaultValue={[neighborLimit]} 
                    min={5} 
                    max={50} 
                    step={5}
                    onValueChange={(values) => setNeighborLimit(values[0])}
                    className="w-full"
                  />
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="extendedMode"
                    checked={extendedMode}
                    onChange={() => setExtendedMode(!extendedMode)}
                    className="mr-2 h-4 w-4"
                  />
                  <label htmlFor="extendedMode" className="text-sm font-medium text-gray-400">
                    Extended Graph View
                  </label>
                </div>
                
                {extendedMode && (
                  <>
                    <div>
                      <label className="text-sm font-medium text-gray-400 mb-2 block">
                        Network Depth: {neighborDepth}
                      </label>
                      <Slider 
                        defaultValue={[neighborDepth]} 
                        min={1} 
                        max={3} 
                        step={1}
                        onValueChange={(values) => setNeighborDepth(values[0])}
                        className="w-full"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Higher depth shows more connections
                      </p>
                    </div>
                    
                    <div>
                      <label className="text-sm font-medium text-gray-400 mb-2 block">
                        Nodes Per Level: {limitPerLevel}
                      </label>
                      <Slider 
                        defaultValue={[limitPerLevel]} 
                        min={5} 
                        max={20} 
                        step={5}
                        onValueChange={(values) => setLimitPerLevel(values[0])}
                        className="w-full"
                      />
                    </div>
                  </>
                )}
              </div>
              <div className="pt-4">
                <Button 
                  variant="outline"
                  className="w-full"
                  onClick={() => setDebugData(debugData || { nodes: [], edges: [] })}
                >
                  Toggle Debug Panel
                </Button>
              </div>
              
              <div className="pt-4 border-t border-gray-800">
                <Button 
                  variant="outline"
                  size="sm"
                  onClick={handleResetZoom}
                  className="w-full mb-2"
                >
                  Reset Zoom
                </Button>
                
                <div className="flex gap-2">
                  <Button 
                    variant="outline"
                    size="sm"
                    onClick={handleZoomIn}
                    className="flex-1"
                  >
                    <ZoomIn className="h-4 w-4 mr-1" /> Zoom In
                  </Button>
                  
                  <Button 
                    variant="outline"
                    size="sm"
                    onClick={handleZoomOut}
                    className="flex-1"
                  >
                    <ZoomOut className="h-4 w-4 mr-1" /> Zoom Out
                  </Button>
                </div>
              </div>
            </div>
          </SheetContent>
        </Sheet>
        
        <h1 className="text-xl font-bold bg-gradient-to-r from-blue-500 to-teal-400 bg-clip-text text-transparent">
          AiR-Helix-View
        </h1>
      </div>
      
      <div className="flex items-center space-x-2">
        <Button variant="ghost" size="sm" onClick={() => setSidebarOpen(true)}>
          <Info className="h-4 w-4 mr-1" /> Controls
        </Button>
      </div>
    </div>

    {/* Main Content */}
    <div className="flex-1 relative z-10">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50 backdrop-blur-sm z-20">
            <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
              <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
              <p className="mt-2 text-gray-300">Loading graph data...</p>
            </div>
          </div>
        )}
        
        {error && (
          <div className="absolute top-4 left-0 right-0 mx-auto w-max bg-red-900/80 text-white px-4 py-2 rounded-md shadow-lg z-50">
            Error: {error}
          </div>
        )}
        
        {/* ForceGraph */}
        {graphData.nodes.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 shadow-lg">
              <Info className="h-8 w-8 text-gray-400 mx-auto mb-2" />
              <p className="text-gray-300">No data available for this image</p>
            </div>
          </div>
        ) : (
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            nodeLabel={node => `${getImageName(node.path)} ${node.isCenter ? '' : `(Similarity: ${(getSimilarity(node, graphData) * 100).toFixed(0)}%)`}`}
            nodeColor={node => node.isCenter ? '#ff6b6b' : '#4285F4'}
            linkWidth={link => (link.value || 0.1) * 5}
            linkColor={() => 'rgba(120, 120, 120, 0.15)'}
            linkOpacity={0.2}
            onNodeClick={handleNodeClick}
            onNodeDoubleClick={handleNodeDoubleClick}
            onZoomEnd={throttledViewportChangeHandler}
            onNodeDragEnd={throttledViewportChangeHandler}
            nodeCanvasObject={(node, ctx, globalScale) => {
              const label = node.label || getImageName(node.path);
              const fontSize = 12/globalScale;
              const nodeR = node.isCenter ? 14 : 10;
              
              // Color based on level (for extended mode)
              let nodeColor;
              if (node.isCenter) {
                nodeColor = '#ff6b6b';  // Red for center
              } else if (extendedMode) {
                // Create a gradient of colors based on level
                const levelColors = ['#4285F4', '#34A853', '#FBBC05', '#EA4335'];
                nodeColor = levelColors[node.level % levelColors.length] || '#4285F4';
              } else {
                nodeColor = '#4285F4';  // Default blue
              }
              
              // Draw circle for the node
              ctx.beginPath();
              ctx.fillStyle = nodeColor;
              ctx.arc(node.x, node.y, nodeR, 0, 2 * Math.PI);
              ctx.fill();
              
              // Draw the image if available
              if (node.path && imagesCache.current[node.path]) {
                try {
                  const img = imagesCache.current[node.path];
                  const size = nodeR * 2;
                  ctx.save();
                  // Create circular clipping path
                  ctx.beginPath();
                  ctx.arc(node.x, node.y, nodeR, 0, 2 * Math.PI);
                  ctx.clip();
                  // Draw the image
                  ctx.drawImage(img, node.x - nodeR, node.y - nodeR, size, size);
                  ctx.restore();
                } catch (err) {
                  console.error(`Error rendering image for node ${node.id}:`, err);
                }
              } else {
                // Fallback - render a node with the first letter of filename
                const letter = getImageName(node.path).charAt(0).toUpperCase();
                ctx.font = `${nodeR}px Sans-Serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = 'white';
                ctx.fillText(letter, node.x, node.y);
              }
              
              // Add border to center node
              if (node.isCenter) {
                ctx.beginPath();
                ctx.strokeStyle = '#ff0000';
                ctx.lineWidth = 2 / globalScale;
                ctx.arc(node.x, node.y, nodeR + 1, 0, 2 * Math.PI);
                ctx.stroke();
              }
              
              // // Draw node label when zoomed in
              // if (globalScale >= 0.8) {
              //   ctx.font = `${fontSize}px Sans-Serif`;
              //   ctx.textAlign = 'center';
              //   ctx.textBaseline = 'bottom';
              //   ctx.fillStyle = 'white';
              //   ctx.fillText(label, node.x, node.y - nodeR - 2);
              // }
            }}
            cooldownTicks={100}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
            backgroundColor="rgba(0,0,0,0)"
            d3Force={(force) => {
              if (force('center')) {
                // ForceGraph creates a center force by default, we just modify it
                force('center')
                  .x(0)
                  .y(0)
                  .strength(5.0);
              }

              // Adjust link force - stronger similarity = closer nodes
              force('link')
                .distance(link => extendedMode ? 
                  // Extended mode: longer distances to spread out the network
                  10 * (1 - (link.value || 0.5)) + 90 : 
                  // Regular mode: tighter clustering
                  10 * (1 - (link.value || 0.1))
                )
                .strength(link => 0.5 * (link.value || 0.3));
              
              // Configure charge force for clustering, reduce strength to avoid too much spread
              force('charge')
                .strength(extendedMode ? -300 : -200)
                .distanceMax(extendedMode ? 200 : 150);
              
              // Add collision force for extended mode in a way that doesn't require direct d3 access
              if (extendedMode) {
                // If collision force doesn't exist yet, create it
                if (!force('collision')) {
                  // Use the ForceGraph's built-in way to add forces
                  force('collision', () => {});
                }
                
                // Configure the existing collision force
                force('collision')
                  .radius(15) // Node radius for collision detection
                  .strength(0.7); // Strength of the collision force (0-1)
              } else {
                // Remove collision force when not in extended mode
                if (force('collision')) force.remove('collision');
              }
            }}
          />
        )}
        {extendedMode && (
          <div className="absolute bottom-20 left-4 bg-gray-900/80 backdrop-blur-sm p-2 rounded-lg shadow-lg border border-gray-800 z-20">
            <div className="text-xs text-gray-400 mb-1">Network Levels:</div>
            <div className="flex items-center gap-2">
              <span className="flex items-center">
                <span className="w-3 h-3 bg-[#ff6b6b] rounded-full mr-1"></span>
                Center
              </span>
              <span className="flex items-center">
                <span className="w-3 h-3 bg-[#4285F4] rounded-full mr-1"></span>
                Level 1
              </span>
              <span className="flex items-center">
                <span className="w-3 h-3 bg-[#34A853] rounded-full mr-1"></span>
                Level 2
              </span>
              <span className="flex items-center">
                <span className="w-3 h-3 bg-[#FBBC05] rounded-full mr-1"></span>
                Level 3
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Debug Panel */}
      {debugData && (
        <div className="absolute top-16 right-4 w-80 bg-gray-900/90 backdrop-blur-sm p-4 rounded-lg shadow-lg border border-gray-800 max-h-[80vh] overflow-auto z-20">
          <h3 className="text-lg font-medium text-blue-400 mb-2">API Response</h3>
          <div className="text-sm">
            <div className="mb-1">Nodes: {debugData.nodes?.length || 0}</div>
            <div className="mb-1">Edges: {debugData.edges?.length || 0}</div>
            
            {debugData.nodes?.length > 0 && (
              <div className="mt-4">
                <h4 className="text-green-400 mb-1">Sample Node:</h4>
                <pre className="bg-gray-800 p-2 rounded text-xs overflow-x-auto">
                  {JSON.stringify(debugData.nodes[0], null, 2)}
                </pre>
              </div>
            )}
            
            {debugData.edges?.length > 0 && (
              <div className="mt-4">
                <h4 className="text-green-400 mb-1">Sample Edge:</h4>
                <pre className="bg-gray-800 p-2 rounded text-xs overflow-x-auto">
                  {JSON.stringify(debugData.edges[0], null, 2)}
                </pre>
              </div>
            )}
          </div>
          
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setDebugData(null)}
            className="mt-4 w-full"
          >
            Close Debug Panel
          </Button>
        </div>
      )}
      
      {/* Modal for node details */}
      <Dialog open={openModal} onOpenChange={setOpenModal}>
        <DialogContent className="sm:max-w-3xl bg-gray-900 border-gray-800">
          {selectedNode && (
            <>
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold">
                  {selectedNode.isCenter ? 'Center Image' : 'Similar Image'}
                </DialogTitle>
                <DialogDescription>
                  {getImageName(selectedNode.path)}
                  {!selectedNode.isCenter && (
                    <span className="ml-2 text-blue-400">
                      Similarity: {(getSimilarity(selectedNode, graphData) * 100).toFixed(0)}%
                    </span>
                  )}
                </DialogDescription>
              </DialogHeader>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
                <div className="bg-gray-950 p-2 rounded-lg border border-gray-800">
                  <img
                    src={`http://localhost:5001/static/${getImageName(selectedNode.path)}`}
                    alt={getImageName(selectedNode.path)}
                    className="w-full rounded-md object-contain max-h-64 md:max-h-80"
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = "/api/placeholder/400/300";
                    }}
                  />
                </div>
                
                <div className="flex flex-col justify-between">
                  <div>
                    <h3 className="text-lg font-medium mb-2">Image Details</h3>
                    <div className="space-y-2 text-sm">
                      <p><span className="text-gray-400">Path:</span> {selectedNode.path}</p>
                      <p><span className="text-gray-400">Node ID:</span> {selectedNode.id}</p>
                      <p><span className="text-gray-400">Type:</span> {selectedNode.isCenter ? 'Center Image' : 'Similar Image'}</p>
                      
                      {!selectedNode.isCenter && (
                        <p>
                          <span className="text-gray-400">Similarity to Center:</span>
                          <span className="ml-2 text-blue-400 font-semibold">
                            {(getSimilarity(selectedNode, graphData) * 100).toFixed(1)}%
                          </span>
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="mt-4 flex flex-col space-y-2">
                    {!selectedNode.isCenter && (
                      <Button 
                        variant="default"
                        onClick={handleSetAsCenterImage}
                      >
                        Set as Center Image
                      </Button>
                    )}
                    
                    <a
                      href={`http://localhost:5001/static/${getImageName(selectedNode.path)}`}
                      download={getImageName(selectedNode.path)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <Button variant="outline" className="w-full">
                        <Download className="h-4 w-4 mr-2" />
                        Download Image
                      </Button>
                    </a>
                  </div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
      <GraphControls 
        loading={loading} 
        loadingMore={loadingMore}
        nodeCount={graphData.nodes.length} 
        expandedNodes={expandedNodes.size}
        toggleAutomaticLoading={toggleAutomaticLoading}
        isAutoLoadingEnabled={isAutoLoadingEnabled}
        clearGraph={clearGraph}
        resetView={resetView}
        maxNodesSliderValue={maxNodesLimit}
        setMaxNodesSliderValue={setMaxNodesLimit}
        />
    </div>
  );
};

export default ImageSimilarityExplorer;