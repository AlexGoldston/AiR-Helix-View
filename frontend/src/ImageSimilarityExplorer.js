import React, { useState, useEffect, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './components/ui/dialog';
import { Info, ZoomIn, ZoomOut, Download, X } from 'lucide-react';
import { Button } from './components/ui/button';
import { Slider } from './components/ui/slider';
import _ from 'lodash';

const ImageSimilarityExplorer = () => {
  // State management
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [centerImage, setCenterImage] = useState('arrowhead_stadium29.jpg');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.65);
  const [debugData, setDebugData] = useState(null);
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const [openModal, setOpenModal] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const [isAutoLoadingEnabled, setIsAutoLoadingEnabled] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [maxNodesLimit, setMaxNodesLimit] = useState(2000);
  const [extendedMode, setExtendedMode] = useState(false);  // Enable by default
  const [neighborDepth, setNeighborDepth] = useState(3);  // Default to 3 for extended mode
  const [neighborLimit, setNeighborLimit] = useState(1000);
  const [limitPerLevel, setLimitPerLevel] = useState(100);
  const [showControls, setShowControls] = useState(false);
  
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
    return `http://localhost:5001/static/${encodeURIComponent(filename)}`;
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
    
    try {
      // Process multiple nodes at once (batch processing)
      const nodesToProcess = loadQueue.current.splice(0, 3); // Process 3 at a time
      
      // Skip nodes that are already expanded
      const nodesToFetch = nodesToProcess.filter(nodeId => !expandedNodes.has(nodeId));
      
      if (nodesToFetch.length === 0) {
        setLoadingMore(false);
        setTimeout(processLoadQueue, 50);
        return;
      }
      
      // Fetch each node's neighbors in parallel
      const fetchPromises = nodesToFetch.map(async (nodeId) => {
        // Find the node in the current graph data
        const node = graphData.nodes.find(n => n.id === nodeId);
        if (!node || !node.path) return null;
        
        // Get filename and make API request
        const filename = getImageName(node.path);
        const response = await fetch(
          `http://localhost:5001/neighbors?image_path=${encodeURIComponent(filename)}&threshold=${similarityThreshold}&limit=${neighborLimit}`
        );
        
        if (!response.ok) throw new Error(`API error for ${filename}: ${response.status}`);
        
        const data = await response.json();
        return { nodeId, data };
      });
      
      // Wait for all fetches to complete
      const results = await Promise.allSettled(fetchPromises);
      
      // Process successful results
      const newNodes = [];
      const newLinks = [];
      const newExpandedNodes = new Set(expandedNodes);
      
      results.forEach(result => {
        if (result.status === 'fulfilled' && result.value) {
          const { nodeId, data } = result.value;
          
          // Add this node to expanded set
          newExpandedNodes.add(nodeId);
          
          // Add new nodes
          data.nodes.forEach(node => {
            if (!graphData.nodes.some(n => n.id === node.id) && !newNodes.some(n => n.id === node.id)) {
              newNodes.push({
                id: node.id,
                path: node.path,
                label: node.label || getImageName(node.path),
                description: node.description || "",
                isCenter: false,
                level: node.level || 1
              });
            }
          });
          
          // Add new links
          data.edges.forEach(edge => {
            const linkId = edge.id;
            if (!graphData.links.some(l => l.id === linkId) && !newLinks.some(l => l.id === linkId)) {
              newLinks.push({
                id: linkId,
                source: edge.source,
                target: edge.target,
                value: edge.weight || 0.5
              });
            }
          });
        }
      });
      
      // Update graph with all new nodes and links
      if (newNodes.length > 0 || newLinks.length > 0) {
        setGraphData({
          nodes: [...graphData.nodes, ...newNodes],
          links: [...graphData.links, ...newLinks]
        });
        
        // Preload images for new nodes
        newNodes.forEach(node => {
          if (node.path) {
            preloadImage(node.path).catch(() => {});
          }
        });
      }
      
      // Update expanded nodes
      setExpandedNodes(newExpandedNodes);
      
    } catch (error) {
      console.error(`Error in batch node expansion:`, error);
    } finally {
      setLoadingMore(false);
      
      // Continue processing queue with shorter delay
      if (loadQueue.current.length > 0) {
        setTimeout(processLoadQueue, 200);
      } else {
        processingQueue.current = false;
      }
    }
  }, [graphData, expandedNodes, getImageName, maxNodesLimit, neighborLimit, preloadImage, similarityThreshold]);

  // Viewport change handler
  const handleViewportChange = useCallback(() => {
    if (!graphRef.current) return;
    
    try {
      // Get current viewport information
      const zoomState = graphRef.current.zoom();
      if (!zoomState) return;
      
      const { x, y, k } = zoomState;
      
      // Use window dimensions
      const width = window.innerWidth;
      const height = window.innerHeight;
      
      // Calculate viewport boundaries with larger buffer for more expansions
      const bounds = {
        xMin: (0 - x) / k - 300,
        xMax: (width - x) / k + 300,
        yMin: (0 - y) / k - 300,
        yMax: (height - y) / k + 300
      };
      
      viewportBoundsRef.current = bounds;
      
      // If auto-loading is enabled, find nodes to expand
      if (isAutoLoadingEnabled && graphData.nodes.length > 0 && graphData.nodes.length < maxNodesLimit) {
        // Find visible nodes with valid coordinates
        const visibleNodes = graphData.nodes.filter(node => 
          node && 
          typeof node.x === 'number' && typeof node.y === 'number' &&
          node.x >= bounds.xMin && node.x <= bounds.xMax &&
          node.y >= bounds.yMin && node.y <= bounds.yMax
        );
        
        // Find unexpanded visible nodes
        const unexpandedNodes = visibleNodes.filter(node => 
          node.id && 
          !expandedNodes.has(node.id) && 
          !loadQueue.current.includes(node.id)
        );
        
        // Add more nodes to load queue (increased from 2 to 5)
        const nodesToQueue = unexpandedNodes.slice(0, 5);
        if (nodesToQueue.length > 0) {
          console.log(`Adding ${nodesToQueue.length} visible nodes to expansion queue`);
          const nodeIds = nodesToQueue.map(node => node.id).filter(Boolean);
          loadQueue.current.push(...nodeIds);
          
          // Start processing queue if not already
          if (!processingQueue.current) {
            processLoadQueue();
          }
        }
      }
    } catch (error) {
      console.error("Error in viewport change handler:", error);
    }
  }, [expandedNodes, graphData.nodes, isAutoLoadingEnabled, maxNodesLimit, processLoadQueue]);


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

// Force neighborDepth to 3 right before fetch when in extended mode
useEffect(() => {
  if (extendedMode && neighborDepth !== 3) {
    console.log("Forcing depth to 3 for extended mode");
    setNeighborDepth(3);
  }
}, [extendedMode, neighborDepth, centerImage]);

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
      
      // Fix: Verify we have nodes and edges before processing
      if (!apiData.nodes || !apiData.edges) {
        throw new Error("API response missing nodes or edges");
      }
      
      console.log(`Received ${apiData.nodes.length} nodes and ${apiData.edges.length} edges from API`);
      
      // Transform the API response to match ForceGraph expected format
      const nodes = [];
      const links = [];
      
      // Find center node and mark as expanded
      const centerNode = apiData.nodes.find(node => node.isCenter);
      if (centerNode) {
        // Add to expanded nodes set since center is already expanded
        setExpandedNodes(new Set([centerNode.id]));
      } else {
        console.warn("No center node found in API response");
      }
      
      // Process all nodes from the API response
      apiData.nodes.forEach(node => {
        nodes.push({
          id: node.id,
          path: node.path,
          label: node.label || getImageName(node.path),
          isCenter: node.isCenter || false,
          level: node.level !== undefined ? node.level : 0,
          description: node.description || '',
          // Pin center node in place to stop it from moving during simulation
          ...(node.isCenter ? { fx: 0, fy: 0 } : {})
        });
      });
      
      // Create a map of node IDs for faster edge creation
      const nodeMap = {};
      nodes.forEach(node => {
        nodeMap[node.id] = node;
      });
      
      // Process all edges from the API response
      apiData.edges.forEach(edge => {
        // Only create links if both source and target nodes exist
        if (nodeMap[edge.source] && nodeMap[edge.target]) {
          links.push({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            value: edge.weight || 0.5
          });
        }
      });

      console.log(`Processed ${nodes.length} nodes and ${links.length} links for graph`);
      
      // Set the graph data with proper nodes and links
      setGraphData({
        nodes: nodes,
        links: links
      });
      
      // Preload images in the background
      const preloadPromises = nodes.map(node => 
        preloadImage(node.path).catch(() => console.warn(`Failed to preload image: ${node.path}`))
      );
      
      Promise.allSettled(preloadPromises).then(() => {
        console.log("All images preloaded (or attempted)");
      });
      
      // Adjust graph physics after setting data with better timing
      setTimeout(() => {
        if (graphRef.current) {
          // Adjust forces
          if (graphRef.current.d3Force('charge')) {
            graphRef.current.d3Force('charge').strength(-300);
          }
          
          if (graphRef.current.d3Force('link')) {
            graphRef.current.d3Force('link').distance(link => 
              Math.min(100, 100 * (1 - (link.value || 0.5)))
            );
          }
          
          // Reheat simulation
          graphRef.current.d3ReheatSimulation();
          
          // Zoom to fit the graph
          graphRef.current.zoomToFit(800, 80);
        }
      }, 100);
      
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

// Get a short description from the center node
const getCenterNodeDescription = useCallback(() => {
  const centerNode = graphData.nodes.find(node => node.isCenter);
  if (centerNode && centerNode.description) {
    const maxLength = 100;
    return centerNode.description.length > maxLength ? 
      `${centerNode.description.substring(0, maxLength)}...` : 
      centerNode.description;
  }
  return "No description available";
}, [graphData.nodes]);

// Add a function to truncate descriptions
const truncateDescription = (desc, maxLength = 60) => {
  if (!desc) return 'No description available';
  return desc.length > maxLength 
    ? `${desc.substring(0, maxLength)}...` 
    : desc;
};

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

    {/* Simple Title Banner */}
    <div className="z-10 flex items-center justify-between p-4 bg-gray-950/80 backdrop-blur-sm border-b border-gray-800">
      <h1 className="text-xl font-bold bg-gradient-to-r from-blue-500 to-teal-400 bg-clip-text text-transparent">
        AiR-Helix-View
      </h1>
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
              const nodeR = node.isCenter ? 15 : 8;
              
              // Color based on level (for extended mode) with better colors
              let nodeColor;
              if (node.isCenter) {
                nodeColor = '#E63946';  // Brighter red for center
              } else if (extendedMode) {
                // Create a gradient of colors based on level
                const levelColors = ['#4361EE', '#3A86FF', '#00BBF9', '#4CC9F0'];
                nodeColor = levelColors[node.level % levelColors.length] || '#4361EE';
              } else {
                // Better default color
                nodeColor = '#4361EE';
              }
              
              // Add glow effect for better visibility
              const shadowSize = nodeR * 1.5;
              ctx.shadowColor = nodeColor;
              ctx.shadowBlur = 15 * (1/globalScale);
              ctx.shadowOffsetX = 0;
              ctx.shadowOffsetY = 0;
              
              // Draw circle for the node
              ctx.beginPath();
              ctx.fillStyle = nodeColor;
              ctx.arc(node.x, node.y, nodeR, 0, 2 * Math.PI);
              ctx.fill();
              
              // Reset shadow
              ctx.shadowBlur = 0;
              
              // Draw the image if available
              if (node.path && imagesCache.current[node.path]) {
                try {
                  const img = imagesCache.current[node.path];
                  const size = nodeR * 2;
                  ctx.save();
                  // Create circular clipping path
                  ctx.beginPath();
                  ctx.arc(node.x, node.y, nodeR * 0.9, 0, 2 * Math.PI);
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
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 2 / globalScale;
                ctx.arc(node.x, node.y, nodeR + 2, 0, 2 * Math.PI);
                ctx.stroke();
              }
            }}
          />
        )}
        
        {/* Level indicator legend - always shown */}
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

      {/* Consolidated Control Panel */}
      <div className="absolute bottom-4 right-4 z-10">
        <div className={`bg-gray-900/90 backdrop-blur-sm p-4 rounded-lg shadow-lg border border-gray-800 mb-2 transition-all duration-300 ${showControls ? 'w-80' : 'w-auto'}`}>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-medium">Graph Controls</h3>
            <button 
              onClick={() => setShowControls(!showControls)}
              className="text-gray-400 hover:text-white"
            >
              {showControls ? <X size={16} /> : null}
            </button>
          </div>
          
          {showControls && (
            <div className="space-y-4">
              {/* Current Image */}
              <div>
                <h4 className="text-sm font-medium mb-2">Current Center Image</h4>
                <div className="bg-gray-950 p-2 rounded-lg mb-2">
                  <img 
                    src={`http://localhost:5001/static/${getImageName(centerImage)}`}
                    alt={getImageName(centerImage)}
                    className="w-full h-32 object-contain rounded-md border border-gray-800"
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = "/api/placeholder/200/120";
                    }}
                  />
                  <p className="mt-2 text-xs text-gray-400 text-center truncate">{getImageName(centerImage)}</p>
                </div>
                
                {/* Description */}
                <div className="text-xs text-gray-300 p-2 bg-gray-800/60 rounded-lg">
                  <span className="text-gray-400 block mb-1">Description:</span>
                  {truncateDescription(getCenterNodeDescription(), 100)}
                </div>
              </div>
              
              {/* Similarity Threshold */}
              <div>
                <label className="text-xs text-gray-400 mb-1 block">
                  Similarity Threshold: {similarityThreshold.toFixed(2)}
                </label>
                <Slider 
                  defaultValue={[similarityThreshold]} 
                  min={0.5} 
                  max={0.95} 
                  step={0.01}
                  onValueChange={(values) => setSimilarityThreshold(values[0])}
                  className="w-full"
                />
                <p className="text-xs text-gray-500 mt-1">Higher values show more similar images</p>
              </div>
              
              {/* Neighbor Limit */}
              <div>
                <label className="text-xs text-gray-400 mb-1 block">
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
              
              {/* Max Nodes Limit */}
              <div>
                <label className="text-xs text-gray-400 mb-1 block">
                  Max Nodes: {maxNodesLimit}
                </label>
                <Slider 
                  defaultValue={[maxNodesLimit]} 
                  min={50} 
                  max={500} 
                  step={50}
                  onValueChange={(values) => setMaxNodesLimit(values[0])}
                  className="w-full"
                />
              </div>
              
              {/* Extended Mode Toggle */}
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="extendedMode"
                  checked={extendedMode}
                  onChange={() => setExtendedMode(!extendedMode)}
                  className="mr-2 h-4 w-4"
                />
                <label htmlFor="extendedMode" className="text-xs text-gray-400">
                  Extended Graph View
                </label>
              </div>
              
              {/* Extended Mode Options */}
              {extendedMode && (
                <>
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">
                      Network Depth: {neighborDepth}
                    </label>
                    <Slider 
                      value={[neighborDepth]} 
                      min={1} 
                      max={3} 
                      step={1}
                      disabled={true} // Always 3 for extended mode
                      className="w-full opacity-70"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Fixed at 3 for extended mode
                    </p>
                  </div>
                  
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">
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
              
              {/* Auto-loading Toggle */}
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="autoLoading"
                  checked={isAutoLoadingEnabled}
                  onChange={toggleAutomaticLoading}
                  className="mr-2 h-4 w-4"
                />
                <label htmlFor="autoLoading" className="text-xs text-gray-400">
                  Automatic Node Expansion
                </label>
              </div>
              
              {/* Stats */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-gray-800 p-2 rounded-md">
                  <span className="text-gray-400 block">Nodes:</span>
                  <span className="font-medium">{graphData.nodes.length}</span>
                </div>
                <div className="bg-gray-800 p-2 rounded-md">
                  <span className="text-gray-400 block">Expanded:</span>
                  <span className="font-medium">{expandedNodes.size}</span>
                </div>
              </div>
              
              {/* Actions */}
              <div className="grid grid-cols-2 gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={clearGraph}
                  className="text-xs"
                >
                  Clear Graph
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={resetView}
                  className="text-xs"
                >
                  Reset View
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleZoomIn}
                  className="text-xs flex items-center justify-center"
                >
                  <ZoomIn className="h-3 w-3 mr-1" /> Zoom In
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleZoomOut}
                  className="text-xs flex items-center justify-center"
                >
                  <ZoomOut className="h-3 w-3 mr-1" /> Zoom Out
                </Button>
              </div>
              
              {/* Debug Toggle */}
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setShowDebugPanel(!showDebugPanel)}
                className="w-full text-xs"
              >
                {showDebugPanel ? 'Hide Debug Info' : 'Show Debug Info'}
              </Button>
              
              {/* Debug Panel */}
              {showDebugPanel && debugData && (
                <div className="mt-2 border-t border-gray-700 pt-2 text-xs">
                  <h4 className="font-medium text-blue-400 mb-1">API Response</h4>
                  <div>
                    <div className="mb-1">Nodes: {debugData.nodes?.length || 0}</div>
                    <div className="mb-1">Edges: {debugData.edges?.length || 0}</div>
                    
                    {debugData.nodes?.length > 0 && (
                      <div className="mt-2">
                        <div className="text-green-400 mb-1">Sample Node:</div>
                        <pre className="bg-gray-800 p-2 rounded text-xs overflow-x-auto">
                          {JSON.stringify(debugData.nodes[0], null, 2)}
                        </pre>
                      </div>
                    )}
                    
                    {debugData.edges?.length > 0 && (
                      <div className="mt-2">
                        <div className="text-green-400 mb-1">Sample Edge:</div>
                        <pre className="bg-gray-800 p-2 rounded text-xs overflow-x-auto">
                          {JSON.stringify(debugData.edges[0], null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* Toggle Button (Only shown when controls are hidden) */}
        {!showControls && (
          <Button 
            onClick={() => setShowControls(true)}
            className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-800/80 backdrop-blur-sm shadow-lg border border-gray-700 hover:bg-gray-700"
          >
            <Info size={18} />
          </Button>
        )}
        
        {/* Loading indicator */}
        {(loading || loadingMore) && (
          <div className="absolute -top-12 right-0 bg-gray-900/80 backdrop-blur-sm rounded-full p-2 shadow-lg border border-gray-800">
            <div className="flex items-center gap-2 px-2">
              <div className="animate-spin w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full"></div>
              <span className="text-xs">{loading ? 'Loading' : 'Expanding'}</span>
            </div>
          </div>
        )}
      </div>
      
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
    </div>
  );
};

export default ImageSimilarityExplorer;