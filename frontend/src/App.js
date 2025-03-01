import React, { useState, useEffect, useRef } from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import NodeProgramImage from './customImageRenderer';

function MyGraphComponent() {
    const [loading, setLoading] = useState(true);
    const [graph] = useState(new Graph());
    const [centerImage, setCenterImage] = useState('/images/allianz_stadium_sydney01.jpg');
    const [threshold] = useState(0.7);
    const containerRef = useRef(null);
    const sigmaRef = useRef(null);

    useEffect(() => {
        fetchNeighbors(centerImage, threshold);
    }, [centerImage, threshold]);

    // Initialize sigma when the graph data is ready
    useEffect(() => {
        // Clean up previous sigma instance if it exists
        if (sigmaRef.current) {
            sigmaRef.current.kill();
            sigmaRef.current = null;
        }

        if (!loading && containerRef.current && graph.order > 0) {
            try {
                console.log("Initializing Sigma with graph", graph);
                
                // Create new sigma instance with simple settings
                sigmaRef.current = new Sigma(graph, containerRef.current, {
                    renderEdgeLabels: true,
                    defaultNodeType: 'circle',
                    defaultEdgeType: 'line',
                });
                
                // Add event listener for node clicks
                sigmaRef.current.on('clickNode', ({ node }) => {
                    console.log("Clicked node", node);
                    const nodeAttrs = graph.getNodeAttributes(node);
                    
                    // Update the center image path - ensure it has the correct prefix
                    let newImagePath = nodeAttrs.image;
                    if (!newImagePath.startsWith('/images/') && !newImagePath.startsWith('http')) {
                        // If the path doesn't already have /images/ prefix or isn't a full URL, add the prefix
                        if (newImagePath.startsWith('images/')) {
                            newImagePath = '/' + newImagePath;
                        } else {
                            newImagePath = '/images/' + newImagePath.split('/').pop();
                        }
                    }
                    
                    setCenterImage(newImagePath);
                    console.log("Setting new center image:", newImagePath);
                });
                
            } catch (error) {
                console.error("Error initializing Sigma:", error);
            }
        }

        // Cleanup function
        return () => {
            if (sigmaRef.current) {
                sigmaRef.current.kill();
                sigmaRef.current = null;
            }
        };
    }, [loading, graph]);

    const fetchNeighbors = async (imagePath, threshold) => {
        setLoading(true);
        try {
            // Convert the public path to match what's expected by the backend
            let apiImagePath = imagePath;
            
            // If the path starts with /images/, remove the leading slash for the API
            if (apiImagePath.startsWith('/images/')) {
                apiImagePath = 'images/' + apiImagePath.split('/images/')[1];
            }
            
            console.log(`Fetching neighbors for ${apiImagePath} with threshold ${threshold}`);
            
            const response = await fetch(
                `http://localhost:5001/neighbors?image_path=${encodeURIComponent(
                    apiImagePath
                )}&threshold=${threshold}`,
            );
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log("API response data:", data);

            // Clear existing graph
            graph.clear();

            // Add source node (the center image)
            const sourceId = 'source';
            graph.addNode(sourceId, {
                label: imagePath.split('/').pop(), // Just display the filename
                x: 0.5,
                y: 0.5,
                size: 15,
                image: imagePath, // Use the public path with /images/
                color: 'rgb(255, 0, 0)'
            });

            // Add neighbor nodes with randomized positions around the center
            if (data.nodes && data.nodes.length > 0) {
                data.nodes.forEach((node) => {
                    if (!graph.hasNode(node.id)) {
                        const angle = Math.random() * 2 * Math.PI;
                        const distance = 0.1 + Math.random() * 0.2;
                        
                        // Format the image path for frontend
                        let nodePath = node.path;
                        if (!nodePath.startsWith('/images/') && !nodePath.startsWith('http')) {
                            // If the path doesn't have /images/ prefix
                            if (nodePath.startsWith('images/')) {
                                nodePath = '/' + nodePath;
                            } else {
                                nodePath = '/images/' + nodePath.split('/').pop();
                            }
                        }
                        
                        graph.addNode(node.id, {
                            label: nodePath.split('/').pop() || "Unknown", // Just display the filename
                            x: 0.5 + Math.cos(angle) * distance,
                            y: 0.5 + Math.sin(angle) * distance,
                            size: 10,
                            image: nodePath, // Use the public path with /images/
                            color: 'rgb(0, 0, 255)'
                        });
                        
                        // Connect each node to the source
                        graph.addEdge(sourceId, node.id, {
                            weight: 1,
                            size: 1,
                            color: 'rgba(128, 128, 128, 0.5)'
                        });
                    }
                });
            } else {
                console.warn("No nodes returned from API");
            }
            
            console.log(`Graph now has ${graph.order} nodes and ${graph.size} edges`);
        } catch (error) {
            console.error('Error fetching neighbors:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <h1>Image Similarity Explorer</h1>
            <div className="current-image">
                <p>Current center image: {centerImage}</p>
                {/* Display the current center image */}
                <img 
                    src={centerImage} 
                    alt="Center Node" 
                    style={{ maxWidth: '200px', maxHeight: '200px', border: '2px solid red' }} 
                />
            </div>
            {loading ? (
                <div className="loading">Loading graph data...</div>
            ) : (
                <div 
                    ref={containerRef} 
                    style={{ height: '600px', width: '100%', border: '1px solid #ccc', marginTop: '20px' }}
                />
            )}
        </div>
    );
}

export default MyGraphComponent;