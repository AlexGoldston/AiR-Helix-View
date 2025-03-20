import React, { useState, useEffect, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './components/ui/sheet';
import { Slider } from './components/ui/slider';
import { Button } from './components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './components/ui/dialog';
import { Menu, ZoomIn, ZoomOut, Download, Info } from 'lucide-react';
import GraphControls from './components/GraphControls';
import NavBar from './components/NavBar';
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
  const [maxNodesLimit, setMaxNodesLimit] = useState(500);
  const [extendedMode, setExtendedMode] = useState(true);  // Enable by default
  const [neighborDepth, setNeighborDepth] = useState(2);
  const [limitPerLevel, setLimitPerLevel] = useState(10);
  
  // Refs
  const imagesCache = useRef({});
  const graphRef = useRef(null);
  const loadQueue = useRef([]);
  const processingQueue = useRef(false);
  const viewportBoundsRef = useRef(null);
  const clickNodeRef = useRef(null);
  const clickCountRef = useRef(0);
  const clickTimerRef = useRef(null);
  
  // image path handling
  const getImageName = useCallback((path) => {
    if (!path) return 'unknown';
    
    // Create a function to clean the path consistently
    const cleanPath = (inputPath) => {
      // Remove any "images/" prefix
      let filename = inputPath;
      if (filename.startsWith('images/')) {
        filename = filename.substring(7);
      }
      
      // Remove query parameters
      filename = filename.split('?')[0];
      
      // Get just the filename
      return filename.split('/').pop().split('\\').pop();
    };
    
    return cleanPath(path);
  }, []);
  
  // Add this helper function for constructing image URLs consistently
  const getImageUrl = useCallback((path) => {
    if (!path) return null;
    
    const filename = getImageName(path);
    return `${process.env.REACT_APP_API_BASE_URL}/static/${encodeURIComponent(filename)}`;
  }, [getImageName]);
  
  // Then use getImageUrl() throughout your component instead of constructing URLs manually
  // For example, in your preloadImage function:
  
  const preloadImage = useCallback((path) => {
    return new Promise((resolve, reject) => {
      if (!path) {
        reject(new Error("Invalid path"));
        return;
      }
      
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
        console.error(`Failed to load image: ${path}`, err);
        reject(err);
      };
      
      // Use the consistent URL helper
      img.src = getImageUrl(path);
      
      // Set a timeout to avoid hanging preloads
      setTimeout(() => {
        if (!imagesCache.current[path]) {
          reject(new Error("Image load timeout"));
        }
      }, 5000);
    });
  }, [getImageUrl]);

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



  // updated loading queue function
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
      // Find the node in the current graph data
      const node = graphData.nodes.find(n => n.id === nodeId);
      if (!node) {
        console.warn(`Node ${nodeId} not found in graph data`);
        setLoadingMore(false);
        setTimeout(() => processLoadQueue(), 50);
        return;
      }
  
      console.log(`Expanding node: ${node.path} (ID: ${nodeId})`);
      
      // Load neighbors for this node
      const filename = getImageName(node.path);
      const response = await fetch(
        `${process.env.REACT_APP_API_BASE_URL}/neighbors?image_path=${encodeURIComponent(filename)}&threshold=${similarityThreshold}&limit=${neighborLimit}`
      );
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      console.log(`Received ${data.nodes.length} nodes and ${data.edges.length} edges`);
      
      // Create a deep copy of the current graph data
      const newGraphData = {
        nodes: [...graphData.nodes],
        links: [...graphData.links]
      };
  
      // Track added nodes to avoid duplicates
      const addedNodeIds = new Set();
  
      // Add new nodes that don't already exist
      data.nodes.forEach(node => {
        if (!newGraphData.nodes.some(n => n.id === node.id)) {
          addedNodeIds.add(node.id);
          newGraphData.nodes.push({
            id: node.id,
            path: node.path,
            label: node.label || getImageName(node.path),
            description: node.description,
            isCenter: false,
            level: node.level !== undefined ? node.level : 1
          });
        }
      });
  
      // Add new edges that don't already exist
      data.edges.forEach(edge => {
        const linkId = edge.id;
        if (!newGraphData.links.some(l => l.id === linkId)) {
          newGraphData.links.push({
            id: linkId,
            source: edge.source,
            target: edge.target,
            value: edge.weight
          });
        }
      });
      
      // Update graph data
      setGraphData(newGraphData);
      
      // Mark node as expanded
      setExpandedNodes(prev => {
        const newSet = new Set(prev);
        newSet.add(nodeId);
        return newSet;
      });
      
      // Preload images for new nodes
      Array.from(addedNodeIds).forEach(id => {
        const node = newGraphData.nodes.find(n => n.id === id);
        if (node) {
          preloadImage(node.path).catch(() => {});
        }
      });
  
      console.log(`Added ${addedNodeIds.size} new nodes`);
  
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

// ensure depth is set to 3 in extended mode by default
useEffect(() => {
  if (extendedMode) {
    setNeighborDepth(3);
  }
}, [extendedMode]);

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
        url = `${process.env.REACT_APP_API_BASE_URL}/extended-neighbors?image_path=${encodeURIComponent(filename)}&threshold=${similarityThreshold}&depth=${neighborDepth}&limit_per_level=${limitPerLevel}&max_nodes=${maxNodesLimit}`;
        console.log(`Fetching extended data for ${centerImage} with depth ${neighborDepth}`);
      } else {
        url = `${process.env.REACT_APP_API_BASE_URL}/neighbors?image_path=${encodeURIComponent(filename)}&threshold=${similarityThreshold}&limit=${neighborLimit}`;
        console.log(`Fetching direct neighbors for ${centerImage}`);
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const apiData = await response.json();
      console.log("API response:", apiData);
      setDebugData(apiData);
      
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
      apiData.nodes.forEach(node => {
        graphData.nodes.push({
          id: node.id,
          path: node.path,
          label: node.label || getImageName(node.path),
          isCenter: node.isCenter || false,
          level: node.level || 0,
          description: node.description || '',
          // Pin center node in place to stop it from moving during simulation
          ...(node.isCenter ? { fx: 0, fy: 0 } : {})
        });
      });
      
      // Process all edges from the API response
      apiData.edges.forEach(edge => {
        graphData.links.push({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          value: edge.weight
        });
      });

      console.log("Processed graph data:", graphData);
      
      // Preload images for better rendering
      const preloadPromises = graphData.nodes.map(node => 
        preloadImage(node.path).catch(() => console.warn(`Failed to preload image: ${node.path}`))
      );
      
      await Promise.allSettled(preloadPromises);
      
      // Set the graph data
      setGraphData(graphData);
      
      // Adjust graph physics after setting data with better timing
      setTimeout(() => {
        if (graphRef.current) {
          // Reset forces with better configurations
          if (graphRef.current.d3Force('charge')) {
            // Adjust charge force based on node count
            const nodeCount = graphData.nodes.length;
            const baseStrength = extendedMode ? -500 : -300;
            // Reduce strength for larger graphs to prevent excessive spread
            const strength = baseStrength * (1 - Math.min(0.5, nodeCount / 200));
            graphRef.current.d3Force('charge').strength(strength);
          }
          
          if (graphRef.current.d3Force('link')) {
            // More dynamic link distances based on similarity
            graphRef.current.d3Force('link').distance(link => {
              // Stronger similarities should result in shorter distances
              const similarityFactor = link.value || 0.5;
              // Base distance differs by mode
              const baseDistance = extendedMode ? 150 : 100;
              // More similar nodes are closer together
              return baseDistance * (1 - similarityFactor) + 30;
            });
          }
          
          // Add collision force for stability
          if (graphRef.current.d3Force('collision')) {
            graphRef.current.d3Force('collision').radius(20);
          }
          
          // Strengthen center force temporarily to help layout
          if (graphRef.current.d3Force('center')) {
            graphRef.current.d3Force('center').strength(0.2);
          }
          
          // Reheat simulation with more iterations for better initial layout
          graphRef.current.d3ReheatSimulation();
          
          // Zoom to fit with padding around the graph
          graphRef.current.zoomToFit(800, 50);
          
          // Reduce center force after initial layout
          setTimeout(() => {
            if (graphRef.current && graphRef.current.d3Force('center')) {
              graphRef.current.d3Force('center').strength(0.05);
            }
          }, 1000);
        }
      }, 100); // Shorter initial delay
    } catch (err) {
      console.error("Error fetching graph data:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  fetchData();
}, [centerImage, similarityThreshold, neighborLimit, extendedMode, neighborDepth, limitPerLevel, maxNodesLimit, getImageName, preloadImage]);

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

//click tracking cleanup
useEffect(() => {
  return () => {
    if (clickTimerRef.current) {
      clearTimeout(clickTimerRef.current);
    }
  };
}, []);

const handleNodeClick = useCallback(node => {
  // Clear any existing timeout
  if (clickTimerRef.current) {
    clearTimeout(clickTimerRef.current);
  }
  
  // If we clicked the same node within a short time, count it as a double click
  if (clickNodeRef.current === node.id) {
    clickCountRef.current += 1;
    
    // Double click detected
    if (clickCountRef.current === 2) {
      console.log("Double click detected on node:", node);
      
      // Only process if not already expanded
      if (!expandedNodes.has(node.id)) {
        // Add node to load queue with high priority
        loadQueue.current = [node.id, ...loadQueue.current];
        
        // Start processing queue if not already
        if (!processingQueue.current) {
          processLoadQueue();
        }
      } else {
        console.log(`Node ${node.id} already expanded`);
      }
      
      // Reset after handling double click
      clickNodeRef.current = null;
      clickCountRef.current = 0;
      return;
    }
  } else {
    // Different node, reset counter
    clickNodeRef.current = node.id;
    clickCountRef.current = 1;
  }
  
  // Set timer for single click action
  clickTimerRef.current = setTimeout(() => {
    // Only proceed with single-click action if we haven't detected a double-click
    if (clickCountRef.current === 1) {
      console.log("Single click action for node:", node);
      if (node && node.path) {
        setSelectedNode(node);
        setOpenModal(true);
      }
    }
    
    // Reset state
    clickNodeRef.current = null;
    clickCountRef.current = 0;
  }, 300); // Shorter timer for better responsiveness
}, [processLoadQueue, expandedNodes]);

// handle center image
const handleSetAsCenterImage = useCallback(() => {
  if (selectedNode && !selectedNode.isCenter) {
    // Use the filename directly
    const imagePath = selectedNode.path;
    setCenterImage(imagePath);
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
    
    <NavBar 
      centerImage={centerImage}
      getImageName={getImageName}
      similarityThreshold={similarityThreshold}
      setSimilarityThreshold={setSimilarityThreshold}
      neighborLimit={neighborLimit}
      setNeighborLimit={setNeighborLimit}
      extendedMode={extendedMode}
      setExtendedMode={setExtendedMode}
      neighborDepth={neighborDepth}
      setNeighborDepth={setNeighborDepth}
      limitPerLevel={limitPerLevel}
      setLimitPerLevel={setLimitPerLevel}
      onSelectImage={setCenterImage}
      setDebugData={setDebugData}
      debugData={debugData}
      handleResetZoom={handleResetZoom}
      handleZoomIn={handleZoomIn}
      handleZoomOut={handleZoomOut}
    />

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
            nodeLabel={node => {
              // Create a shortened description preview (max 50 chars) if available
              const descriptionPreview = node.description 
                ? `${node.description.substring(0, 50)}${node.description.length > 50 ? '...' : ''}`
                : 'No description';
                
              return `${getImageName(node.path)} ${node.isCenter ? '' : `(Similarity: ${(getSimilarity(node, graphData) * 100).toFixed(0)}%)`}
            ${descriptionPreview}`;
            }}
            nodeColor={node => node.isCenter ? '#ff6b6b' : '#4285F4'}
            linkWidth={link => (link.value || 0.1) * 5}
            linkColor={() => 'rgba(120, 120, 120, 0.15)'}
            linkOpacity={0.2}
            onNodeClick={handleNodeClick}
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
              // Center force for graph stability
              if (force('center')) {
                force('center')
                  .x(0)
                  .y(0)
                  .strength(extendedMode ? 0.03 : 0.05); // Lower strength in extended mode
              }
            
              // Link force - adjust to make similar nodes closer
              if (force('link')) {
                force('link')
                  .distance(link => {
                    const similarity = link.value || 0.5;
                    // Base distance depends on mode - larger for extended
                    const baseDistance = extendedMode ? 150 : 80;
                    // More similar nodes are closer together
                    return baseDistance * (1 - similarity * 0.7);
                  })
                  .strength(link => {
                    // Link strength proportional to similarity
                    return 0.3 * (link.value || 0.5);
                  });
              }
              
              // Charge force for node repulsion
              if (force('charge')) {
                // Weaker repulsion for extended mode to keep things more compact
                force('charge')
                  .strength(extendedMode ? -200 : -300)
                  .distanceMax(extendedMode ? 250 : 150);
              }
              
              // Add collision force for better node spacing
              if (!force('collision')) {
                // Create if not exists
                force('collision', () => {});
              }
              
              if (force('collision')) {
                force('collision')
                  .radius(node => node.isCenter ? 20 : 12) // Center node has larger collision radius
                  .strength(0.8); // Strong collision prevention
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
                {debugData.nodes[0].description && (
                  <div className="mt-2">
                    <h4 className="text-green-400 mb-1">Node Description:</h4>
                    <div className="bg-gray-800 p-2 rounded text-xs">
                      {debugData.nodes[0].description}
                    </div>
                  </div>
                )}
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
                    src={`${process.env.REACT_APP_API_BASE_URL}/static/${getImageName(selectedNode.path)}`}
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
                      
                      {/* Add description display here */}
                      {selectedNode.description && (
                        <div>
                          <p className="text-gray-400 mb-1">Description:</p>
                          <p className="bg-gray-800 p-2 rounded text-sm">{selectedNode.description}</p>
                        </div>
                      )}
                      
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
                      href={`${process.env.REACT_APP_API_BASE_URL}/static/${getImageName(selectedNode.path)}`}
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
        centerNodeDescription={graphData.nodes.find(n => n.isCenter)?.description}
      />
    </div>
  );
};

export default ImageSimilarityExplorer;