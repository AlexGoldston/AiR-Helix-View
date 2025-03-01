import React from 'react';
import ImageSimilarityExplorer from './ImageSimilarityExplorer';

function App() {
  return (
    <div className="App">
      <header className="App-header" style={{ 
        padding: '20px', 
        backgroundColor: '#1e1e1e', 
        borderBottom: '1px solid #333',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        marginBottom: '20px'
      }}>
        <h1 style={{
          margin: 0,
          textAlign: 'center',
          fontSize: '2rem',
          background: 'linear-gradient(45deg, #4285f4, #34a853)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          display: 'inline-block'
        }}>
          AiR-Helix-View
        </h1>
      </header>
      <main>
        <ImageSimilarityExplorer />
      </main>
    </div>
  );
}

export default App;