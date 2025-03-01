import React, { useState, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import _ from 'lodash';

const ImageSimilarityExplorer = () => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [centerImage, setCenterImage] = useState('images/allianz_stadium_sydney01.jpg');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.7);
  const [neighborLimit, setNeighborLimit] = useState(20);
  
  // Fetch data from the backend API
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Call the backend API
        const response = await fetch(`http://localhost:5001/neighbors?image_path=${encodeURIComponent(centerImage)}&threshold=${similarityThreshold}&limit=${neighborLimit}`);
        
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        
        const apiData = await response.json();
        
        // Transform the API response to match ForceGraph expected format
        const graphData = {
          nodes: [],
          links: []
        };
        
        // Add all nodes from the API response
        apiData.nodes.forEach(node => {
          graphData.nodes.push({
            id: node.id,
            label: node.label,
            path: node.path,
            isCenter: node.isCenter || false
          });
        });
        
        // Add links (edges from the API)
        apiData.edges.forEach(edge => {
          graphData.links.push({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            value: edge.weight
          });
        });
        
        setGraphData(graphData);
      } catch (err) {
        console.error("Error fetching graph data:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [centerImage, similarityThreshold, neighborLimit]);
  
  // Extract filename from path
  const getImageName = (path) => {
    return path.split('/').pop().split('\\').pop();
  };
  
  // Handle node click to change center image
  const handleNodeClick = node => {
    setCenterImage(node.path);
  };
  
  return (
    <div className="flex flex-col p-4 h-screen w-full">
      <h1 className="text-2xl font-bold mb-4">Image Similarity Explorer</h1>
      
      <div className="flex items-center mb-4">
        <div className="mr-8">
          <p className="text-gray-700 mb-1">Current center image: {getImageName(centerImage)}</p>
          <div className="border border-gray-300 p-1 inline-block">
            <img 
              src={`http://localhost:5001/static/${getImageName(centerImage)}`}
              alt={getImageName(centerImage)}
              style={{ width: '200px', height: '120px', objectFit: 'cover' }}
              onError={(e) => {
                e.target.onerror = null; 
                e.target.src = "https://via.placeholder.com/200x120";
              }}
            />
          </div>
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151' }}>Similarity Threshold</label>
            <input 
              type="range" 
              min="0.5" 
              max="0.99" 
              step="0.01" 
              value={similarityThreshold}
              onChange={(e) => setSimilarityThreshold(e.target.value)}
              style={{ width: '200px' }}
            />
            <span style={{ marginLeft: '8px', fontSize: '14px' }}>{similarityThreshold}</span>
          </div>
          
          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#374151' }}>Max Neighbors</label>
            <input 
              type="range" 
              min="5" 
              max="50" 
              step="5" 
              value={neighborLimit}
              onChange={(e) => setNeighborLimit(e.target.value)}
              style={{ width: '200px' }}
            />
            <span style={{ marginLeft: '8px', fontSize: '14px' }}>{neighborLimit}</span>
          </div>
        </div>
      </div>
      
      {loading && <div style={{ textAlign: 'center', padding: '16px 0' }}>Loading image graph data...</div>}
      {error && <div style={{ color: '#EF4444', padding: '16px 0' }}>Error: {error}</div>}
      
      <div style={{ flex: 1, border: '1px solid #D1D5DB', borderRadius: '8px', overflow: 'hidden' }}>
        <ForceGraph2D
          graphData={graphData}
          nodeLabel={node => `${getImageName(node.path)} ${node.isCenter ? '' : `(Similarity: ${getSimilarity(node, graphData)})`}`}
          nodeColor={node => node.isCenter ? '#ff0000' : colorByGroup(2)}
          linkWidth={link => link.value * 5}
          linkColor={() => '#999999'}
          linkOpacity={0.6}
          onNodeClick={handleNodeClick}
          nodeCanvasObject={(node, ctx, globalScale) => {
            // Draw images as nodes
            const size = node.isCenter ? 40 : 24;
            const img = new Image();
            
            // Load actual image from server
            img.src = `http://localhost:5001/static/${getImageName(node.path)}`;
            img.onerror = () => {
              img.src = "https://via.placeholder.com/120x80";
            };
            
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
            ctx.strokeStyle = node.isCenter ? '#ff0000' : colorByGroup(2);
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // Add similarity text if not center node
            if (!node.isCenter) {
              const similarity = getSimilarity(node, graphData);
              if (similarity) {
                ctx.font = '8px Sans-Serif';
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
      </div>
    </div>
  );
};

// Helper function to color nodes by group
const colorByGroup = group => {
  const colors = ['#4285F4', '#34A853', '#FBBC05', '#EA4335', '#8334A2'];
  return colors[(group - 1) % colors.length];
};

// Helper function to get similarity value for a node
const getSimilarity = (node, graphData) => {
  if (node.isCenter) return 1;
  
  const link = graphData.links.find(link => 
    (link.source.id === node.id || link.target.id === node.id) || 
    (link.source === node.id || link.target === node.id)
  );
  
  return link ? link.value : null;
};

export default ImageSimilarityExplorer;