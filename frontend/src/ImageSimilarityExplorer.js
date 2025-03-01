import React, { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

const ImageSimilarityExplorer = () => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [centerImage, setCenterImage] = useState('allianz_stadium_sydney01.jpg');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.63);
  const [neighborLimit, setNeighborLimit] = useState(20);
  const [debugData, setDebugData] = useState(null);
  
  // Ref to store preloaded images
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
      img.src = `http://localhost:5001/static/${filename}?v=${Date.now()}`;
    });
  };
  
  // Fetch data from the backend API
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
  
  // Handle node click to change center image
  const handleNodeClick = node => {
    console.log("Node clicked:", node);
    if (node && node.path && !node.isCenter) {
      setCenterImage(node.path);
    }
  };
  
  // Debug panel
  const renderDebugPanel = () => {
    if (!debugData) return null;
    
    return (
      <div style={{ position: 'absolute', top: '10px', right: '10px', background: 'rgba(255,255,255,0.9)', 
                   padding: '10px', border: '1px solid #ccc', maxWidth: '400px', maxHeight: '80vh', 
                   overflow: 'auto', fontSize: '12px', zIndex: 1000 }}>
        <h3>API Response</h3>
        <div>Nodes: {debugData.nodes?.length || 0}</div>
        <div>Edges: {debugData.edges?.length || 0}</div>
        {debugData.nodes?.length > 0 && (
          <div>
            <h4>Sample Node:</h4>
            <pre>{JSON.stringify(debugData.nodes[0], null, 2)}</pre>
          </div>
        )}
        {debugData.edges?.length > 0 && (
          <div>
            <h4>Sample Edge:</h4>
            <pre>{JSON.stringify(debugData.edges[0], null, 2)}</pre>
          </div>
        )}
        <button onClick={() => setDebugData(null)} style={{ marginTop: '10px', padding: '5px' }}>
          Close Debug Panel
        </button>
      </div>
    );
  };
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', padding: '1rem', height: '100vh', width: '100%' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>Image Similarity Explorer</h1>
      
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem' }}>
        <div style={{ marginRight: '2rem' }}>
          <p style={{ color: '#4B5563', marginBottom: '0.25rem' }}>Current center image: {getImageName(centerImage)}</p>
          <div style={{ border: '1px solid #D1D5DB', padding: '0.25rem', display: 'inline-block' }}>
            <img 
              src={`http://localhost:5001/static/${getImageName(centerImage)}?v=${Date.now()}`}
              alt={getImageName(centerImage)}
              style={{ width: '200px', height: '120px', objectFit: 'cover' }}
              onError={(e) => {
                e.target.onerror = null; 
                const canvas = document.createElement('canvas');
                canvas.width = 200;
                canvas.height = 120;
                const ctx = canvas.getContext('2d');
                ctx.fillStyle = '#ff9999';
                ctx.fillRect(0, 0, 200, 120);
                e.target.src = canvas.toDataURL();
              }}
            />
          </div>
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>Similarity Threshold</label>
            <input 
              type="range" 
              min="0.5" 
              max="0.99" 
              step="0.01" 
              value={similarityThreshold}
              onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
              style={{ width: '200px' }}
            />
            <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem' }}>{similarityThreshold}</span>
          </div>
          
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>Max Neighbors</label>
            <input 
              type="range" 
              min="5" 
              max="50" 
              step="5" 
              value={neighborLimit}
              onChange={(e) => setNeighborLimit(parseInt(e.target.value))}
              style={{ width: '200px' }}
            />
            <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem' }}>{neighborLimit}</span>
          </div>
          
          <button 
            onClick={() => setDebugData(debugData || { nodes: [], edges: [] })} 
            style={{ 
              marginTop: '0.5rem', 
              padding: '4px 8px',
              backgroundColor: '#4B5563',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Toggle Debug Panel
          </button>
        </div>
      </div>
      
      {loading && <div style={{ textAlign: 'center', padding: '1rem 0' }}>Loading image graph data...</div>}
      {error && <div style={{ color: '#EF4444', padding: '1rem 0' }}>Error: {error}</div>}
      
      {/* Debug panel for troubleshooting */}
      {debugData && renderDebugPanel()}
      
      <div style={{ 
        flex: 1, 
        border: '1px solid #D1D5DB', 
        borderRadius: '0.5rem', 
        overflow: 'hidden',
        position: 'relative',
        backgroundColor: '#f9fafb'
      }}>
        {graphData.nodes.length === 0 ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            No data available for this image
          </div>
        ) : (
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            nodeLabel={node => `${getImageName(node.path)} ${node.isCenter ? '' : `(Similarity: ${getSimilarity(node, graphData) || 'unknown'})`}`}
            nodeColor={node => node.isCenter ? '#ff0000' : '#4285F4'}
            linkWidth={link => (link.value || 0.5) * 5}
            linkColor={() => '#999999'}
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
                ctx.fillStyle = node.isCenter ? 'rgba(255, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.2)';
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
                ctx.strokeStyle = node.isCenter ? '#ff0000' : '#4285F4';
                ctx.lineWidth = 2;
                ctx.stroke();
              } else {
                // Fallback for images that failed to load
                ctx.beginPath();
                ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
                ctx.fillStyle = node.isCenter ? '#ff6666' : '#6699cc';
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
                  ctx.fillStyle = 'black';
                  ctx.fillText(`${(similarity * 100).toFixed(0)}%`, node.x, node.y + size + 10);
                }
              }
            }}
            cooldownTicks={100}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
          />
        )}
      </div>
    </div>
  );
};

// Helper function to get similarity value for a node
const getSimilarity = (node, graphData) => {
  if (node.isCenter) return 1;
  
  const link = graphData.links.find(link => {
    if (typeof link.source === 'object' && typeof link.target === 'object') {
      return (link.source.id === node.id || link.target.id === node.id);
    }
    return (link.source === node.id || link.target === node.id);
  });
  
  return link ? link.value : null;
};

export default ImageSimilarityExplorer;