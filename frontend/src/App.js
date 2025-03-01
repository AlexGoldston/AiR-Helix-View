import React, { useState } from 'react';
import { Sigma } from 'react-sigma';
import Graph from 'graphology';
import NodeProgramImage from './yourCustomImageRenderer';
import ImageSimilarityExplorer from './ImageSimilarityExplorer';

function App() {
  const [useNewImplementation, setUseNewImplementation] = useState(true);
  
  return (
    <div className="App">
      <header className="App-header" style={{ padding: '20px' }}>
        <h1>AiR-Helix-View</h1>
        <div style={{ marginTop: '10px', marginBottom: '20px' }}>
          <label style={{ marginRight: '10px' }}>
            <input
              type="checkbox"
              checked={useNewImplementation}
              onChange={() => setUseNewImplementation(!useNewImplementation)}
              style={{ marginRight: '5px' }}
            />
            Use new image-based visualization
          </label>
        </div>
      </header>
      <main>
        {useNewImplementation ? (
          <ImageSimilarityExplorer />
        ) : (
          <MyGraphComponent />
        )}
      </main>
    </div>
  );
}

// Original graph component
function MyGraphComponent() {
    const [loading, setLoading] = useState(true);
    const [graph] = useState(new Graph({ allowSelfLoops: false })); // Initialize graph *once*
    const [centerImage, setCenterImage] = useState('images/allianz_stadium_sydney01.jpg'); // Replace with your image
    const [threshold] = useState(0.7);

    useEffect(() => {
        fetchNeighbors(centerImage, threshold);
    }, [centerImage, threshold, graph]); // Add 'graph' to dependencies

    const fetchNeighbors = async (imagePath, threshold) => {
        setLoading(true);
        try {
            const response = await fetch(
                `http://localhost:5001/neighbors?image_path=${encodeURIComponent(
                    imagePath,
                )}&threshold=${threshold}`,
            );
            const data = await response.json();
            console.log("fetchNeighbors data:", data);

            // *** MUTATE the existing graph ***
            graph.clear(); // Clear *before* adding new nodes/edges

            data.nodes.forEach((node) => {
                graph.addNode(node.id, {  // No hasNode check needed after clear
                    label: node.label,
                    x: Math.random(),
                    y: Math.random(),
                    size: 10,
                    image: node.path,
                    type: 'image',
                });
            });
            data.edges.forEach((edge) => {
                graph.addEdge(edge.source, edge.target, { // No hasEdge check
                    id: edge.id,
                    weight: edge.weight,
                    type: 'line',
                });
            });

        } catch (error) {
            console.error('Error fetching neighbors:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <div>Loading...</div>;
    }

    console.log("Rendering Sigma");

    return (
        <Sigma
            graph={graph} // Pass the *same* graph instance
            style={{ height: '900px', width: '1900px' }}
            settings={{
                defaultNodeType: 'image',
                nodeProgramClasses: { image: NodeProgramImage },
            }}
            onClickNode={(event) => {
                console.log("clicked node", event.node);
                const clickedNode = graph.getNodeAttributes(event.node);
                setCenterImage(clickedNode.image);
            }}
        >
        </Sigma>
    );
}

export default App;