// frontend/src/components/ObjectBrowser.jsx
import React, { useState, useEffect } from 'react';
import { Box, Search, X, Sliders } from 'lucide-react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Slider } from './ui/slider';

const ObjectBrowser = ({ onSelectImage }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [objectData, setObjectData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedObject, setSelectedObject] = useState(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.6);
  const [searchLoading, setSearchLoading] = useState(false);

  // Fetch object data when component mounts
  useEffect(() => {
    if (isOpen) {
      fetchObjectData();
    }
  }, [isOpen]);

  const fetchObjectData = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:5001/features');
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      
      // Sort objects by count
      const sortedObjects = [...data.objects].sort((a, b) => b.count - a.count);
      setObjectData(sortedObjects);
      
    } catch (error) {
      console.error('Error fetching object data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleObjectSelect = (object) => {
    setSelectedObject(object);
    searchByObject(object);
  };

  const searchByObject = async (object) => {
    if (!object) return;
    
    setSearchLoading(true);
    setSearchResults([]);
    
    try {
      const response = await fetch(
        `http://localhost:5001/search/object?object=${encodeURIComponent(object.name)}&min_confidence=${confidenceThreshold}&limit=30`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      const data = await response.json();
      setSearchResults(data.results);
      
    } catch (error) {
      console.error('Error searching by object:', error);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleImageClick = (image) => {
    if (onSelectImage) {
      onSelectImage(image.path);
      setIsOpen(false);
      setSelectedObject(null);
      setSearchResults([]);
    }
  };

  const clearSelection = () => {
    setSelectedObject(null);
    setSearchResults([]);
  };

  const handleConfidenceChange = (values) => {
    setConfidenceThreshold(values[0]);
    if (selectedObject) {
      searchByObject(selectedObject);
    }
  };

  // Map some common objects to emojis for visual cues
  const getObjectEmoji = (objectName) => {
    const emojiMap = {
      'person': '👤',
      'people': '👥',
      'car': '🚗',
      'dog': '🐕',
      'cat': '🐈',
      'bird': '🐦',
      'building': '🏢',
      'tree': '🌳',
      'flower': '🌸',
      'mountain': '⛰️',
      'beach': '🏖️',
      'laptop': '💻',
      'phone': '📱',
      'book': '📚',
      'chair': '🪑',
      'table': '🪑',
      'cup': '☕',
      'bottle': '🍾',
      'food': '🍲'
    };
    
    return emojiMap[objectName.toLowerCase()] || '📦';
  };

  return (
    <>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm" className="flex items-center">
            <Box className="h-4 w-4 mr-1" /> Objects
          </Button>
        </DialogTrigger>
        
        <DialogContent className="sm:max-w-lg bg-gray-900 border-gray-800">
          <DialogHeader>
            <DialogTitle>Browse by Detected Objects</DialogTitle>
          </DialogHeader>
          
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
              <span className="ml-2 text-sm text-gray-400">Loading objects...</span>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Confidence slider */}
              <div className="p-3 border border-gray-700 rounded-md">
                <div className="flex items-center mb-2">
                  <Sliders className="h-4 w-4 mr-2 text-gray-400" />
                  <h3 className="text-sm font-medium text-gray-300">Confidence threshold: {confidenceThreshold.toFixed(1)}</h3>
                </div>
                <Slider
                  defaultValue={[confidenceThreshold]}
                  min={0.3}
                  max={0.9}
                  step={0.1}
                  onValueChange={handleConfidenceChange}
                />
                <p className="text-xs text-gray-400 mt-1">Higher values show more accurate matches</p>
              </div>
              
              {/* Selected object */}
              {selectedObject && (
                <div className="p-4 border border-gray-700 rounded-md">
                  <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center">
                      <span className="text-xl mr-2" role="img" aria-label={selectedObject.name}>
                        {getObjectEmoji(selectedObject.name)}
                      </span>
                      <h3 className="font-medium">
                        {selectedObject.name} ({selectedObject.count} images)
                      </h3>
                    </div>
                    <Button variant="ghost" size="sm" onClick={clearSelection}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  
                  {searchLoading && (
                    <div className="flex justify-center py-4">
                      <div className="animate-spin w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                    </div>
                  )}
                </div>
              )}
              
              {/* Object list */}
              {!selectedObject && objectData.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-300 mb-2">
                    Select an object to find images
                  </h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {objectData.map(object => (
                      <button
                        key={object.name}
                        onClick={() => handleObjectSelect(object)}
                        className="p-3 flex justify-between items-center rounded-md border border-gray-700 hover:border-blue-500 transition-colors bg-gray-800 hover:bg-gray-750"
                      >
                        <div className="flex items-center">
                          <span className="text-xl mr-2" role="img" aria-label={object.name}>
                            {getObjectEmoji(object.name)}
                          </span>
                          <span>{object.name}</span>
                        </div>
                        <span className="text-xs text-gray-400">{object.count}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Empty state */}
              {!selectedObject && objectData.length === 0 && !isLoading && (
                <div className="text-center py-10">
                  <Box className="h-16 w-16 mx-auto mb-3 text-gray-600" />
                  <p className="text-gray-400">No object data available</p>
                </div>
              )}
              
              {/* Search results */}
              {searchResults.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-300 mb-2">
                    Results ({searchResults.length})
                  </h3>
                  <div className="grid grid-cols-3 gap-2 max-h-96 overflow-y-auto">
                    {searchResults.map((result, index) => (
                      <div 
                        key={index}
                        className="cursor-pointer group relative"
                        onClick={() => handleImageClick(result)}
                      >
                        <img
                          src={`http://localhost:5001/static/${result.path}`}
                          alt={result.path}
                          className="w-full h-24 object-cover rounded-md border border-gray-800 group-hover:border-blue-500 transition-colors"
                          onError={(e) => {
                            e.target.onerror = null;
                            e.target.src = "/api/placeholder/100/100";
                          }}
                        />
                        <div className="absolute top-0 right-0 bg-black bg-opacity-70 rounded-bl-md px-1">
                          <span className="text-xs">{Math.round(result.confidence * 100)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ObjectBrowser;