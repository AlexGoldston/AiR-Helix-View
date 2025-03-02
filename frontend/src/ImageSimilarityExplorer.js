import React, { useState, useEffect, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { Slider } from '@/components/ui/slider';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Menu, ZoomIn, ZoomOut, Download, Info } from 'lucide-react';

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
  
  // Refs
  const imagesCache = useRef({});
  const graphRef = useRef(null);
  
  // Extract filename from path
  const getImageName = (path) => {
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
  };
  
  // Preload an image and store it in cache
  const preloadImage = (path) => {
    return new Promise((resolve, reject) => {
      if (!path) {
        reject(new Error("Invalid path"));
        return;
      }
      
      const filename = getImageName(path);
      const img = new Image();
      img.onload = () => {
        imagesCache.current[path] = img;
        resolve(img);
      };
      img.onerror = (err) => {
        console.error(`Failed to load image: ${path} (${filename})`, err);
        reject(err);
      };
      
      // Use clean filename without query parameters
      img.src = `http://localhost:5001/static/${filename}`;
    });
  };
  
  // Fetch graph data from API
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        console.log(`Fetching data for ${centerImage} with threshold ${similarityThreshold} and limit ${neighborLimit}`);
        
        // Call the backend API with just the filename
        const filename = getImageName(centerImage);
        const response = await fetch(`http://localhost:5001/neighbors?image_path=${encodeURIComponent(filename)}&threshold=${similarityThreshold}&limit=${neighborLimit}`);
        
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        
        const apiData = await response.json();
        console.log("API response:", apiData);
        setDebugData(apiData);
        
        // Check if we received valid data
        if (!apiData.nodes || !apiData.edges) {
          console.error("Invalid data structure from API", apiData);
          throw new Error("Invalid data structure from API");
        }

        // Transform the API response to match ForceGraph expected format
        const graphData = {
          nodes: [],
          links: []
        };
        
        // Process all nodes from the API response
        for (const node of apiData.nodes) {
          graphData.nodes.push({
            id: node.id,
            path: node.path,
            label: node.label || getImageName(node.path),
            isCenter: node.isCenter || false
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
              graphRef.current.d3Force('charge').strength(-300);
            }
            if (graphRef.current.d3Force('link')) {
              graphRef.current.d3Force('link').distance(100);
            }
            graphRef.current.zoomToFit(500);
          }, 500);
        }
      } catch (err) {
        console.error("Error fetching graph data:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [centerImage, similarityThreshold, neighborLimit]);
  
  // Handle node click to show modal with details
  const handleNodeClick = useCallback(node => {
    console.log("Node clicked:", node);
    if (node && node.path) {
      setSelectedNode(node);
      setOpenModal(true);
    }
  }, []);
  
  // Change center image 
  const handleSetAsCenterImage = useCallback(() => {
    if (selectedNode && !selectedNode.isCenter) {
      setCenterImage(selectedNode.path);
      setOpenModal(false);
    }
  }, [selectedNode]);
  
  // Helper function to get similarity value for a node
  const getSimilarity = (node, data) => {
    if (node.isCenter) return 1;
    
    const link = data.links.find(link => {
      if (typeof link.source === 'object' && typeof link.target === 'object') {
        return (link.source.id === node.id || link.target.id === node.id);
      }
      return (link.source === node.id || link.target === node.id);
    });
    
    return link ? link.value : null;
  };
  
  // Reset zoom function
  const handleResetZoom = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(500);
    }
  };
  
  // Zoom in function
  const handleZoomIn = () => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom();
      graphRef.current.zoom(currentZoom * 1.2, 400);
    }
  };
  
  // Zoom out function
  const handleZoomOut = () => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom();
      graphRef.current.zoom(currentZoom / 1.2, 400);
    }
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
            linkWidth={link => (link.value || 0.5) * 5}
            linkColor={() => 'rgba(120, 120, 120, 0.6)'}
            linkOpacity={0.6}
            onNodeClick={handleNodeClick}
            nodeCanvasObject={(node, ctx, globalScale) => {
              // Draw images as nodes
              const size = node.isCenter ? 40 : 24;
              
              // Try to get the image from cache
              const img = imagesCache.current[node.path];
              
              if (img) {
                // Draw circle background
                ctx.beginPath();
                ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
                ctx.fillStyle = node.isCenter ? 'rgba(255, 107, 107, 0.2)' : 'rgba(66, 133, 244, 0.2)';
                ctx.fill();
                
                // Draw image clipped in circle
                ctx.save();
                ctx.beginPath();
                ctx.arc(node.x, node.y, size - 2, 0, 2 * Math.PI);
                ctx.clip();
                ctx.drawImage(img, node.x - size + 2, node.y - size + 2, (size - 2) * 2, (size - 2) * 2);
                ctx.restore();
                
                // Add border
                ctx.beginPath();
                ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
                ctx.strokeStyle = node.isCenter ? '#ff6b6b' : '#4285F4';
                ctx.lineWidth = 2;
                ctx.stroke();
              } else {
                // Fallback for images that failed to load
                ctx.beginPath();
                ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
                ctx.fillStyle = node.isCenter ? '#ff6b6b' : '#6699cc';
                ctx.fill();
                
                ctx.beginPath();
                ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
                ctx.strokeStyle = node.isCenter ? '#cc0000' : '#336699';
                ctx.lineWidth = 2;
                ctx.stroke();
                
                // Add label inside node
                ctx.font = '8px Sans-Serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = 'white';
                const shortName = getImageName(node.path).substring(0, 6) + '...';
                ctx.fillText(shortName, node.x, node.y);
                
                // Try to load the image again
                preloadImage(node.path).catch(() => {});
              }
              
              // Add similarity text if not center node
              if (!node.isCenter) {
                const similarity = getSimilarity(node, graphData);
                if (similarity) {
                  ctx.font = '10px Sans-Serif';
                  ctx.textAlign = 'center';
                  ctx.textBaseline = 'bottom';
                  ctx.fillStyle = 'white';
                  ctx.fillText(`${(similarity * 100).toFixed(0)}%`, node.x, node.y + size + 10);
                }
              }
            }}
            cooldownTicks={100}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
            backgroundColor="rgba(0,0,0,0)"
          />
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
    </div>
  );
};

export default ImageSimilarityExplorer;