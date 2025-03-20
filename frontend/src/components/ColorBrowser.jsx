// frontend/src/components/ColorBrowser.jsx
import React, { useState, useEffect } from 'react';
import { Palette, X } from 'lucide-react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';

const ColorBrowser = ({ onSelectImage }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [colorData, setColorData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedColor, setSelectedColor] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);

  // Fetch color data when component mounts
  useEffect(() => {
    if (isOpen) {
      fetchColorData();
    }
  }, [isOpen]);

  const fetchColorData = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('${process.env.REACT_APP_API_BASE_URL}/features');
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      
      // Sort colors by count
      const sortedColors = [...data.colors].sort((a, b) => b.count - a.count);
      setColorData(sortedColors);
      
    } catch (error) {
      console.error('Error fetching color data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleColorSelect = (color) => {
    setSelectedColor(color);
    searchByColor(color);
  };

  const searchByColor = async (color) => {
    if (!color) return;
    
    setSearchLoading(true);
    setSearchResults([]);
    
    try {
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/search/color?color=${encodeURIComponent(color.name)}&limit=30`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      const data = await response.json();
      setSearchResults(data.results);
      
    } catch (error) {
      console.error('Error searching by color:', error);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleImageClick = (image) => {
    if (onSelectImage) {
      onSelectImage(image.path);
      setIsOpen(false);
      setSelectedColor(null);
      setSearchResults([]);
    }
  };

  const clearSelection = () => {
    setSelectedColor(null);
    setSearchResults([]);
  };

  // Map color names to CSS classes
  const getColorClass = (colorName) => {
    const colorMap = {
      'red': 'bg-red-500',
      'blue': 'bg-blue-500',
      'green': 'bg-green-500',
      'yellow': 'bg-yellow-500',
      'orange': 'bg-orange-500',
      'purple': 'bg-purple-500',
      'pink': 'bg-pink-500',
      'teal': 'bg-teal-500',
      'black': 'bg-gray-900',
      'white': 'bg-gray-100',
      'gray': 'bg-gray-500',
      'brown': 'bg-amber-700'
    };
    
    return colorMap[colorName.toLowerCase()] || 'bg-gray-500';
  };

  // Get text color for contrast
  const getTextColorClass = (colorName) => {
    const darkColors = ['black', 'blue', 'purple', 'teal', 'green', 'brown'];
    return darkColors.includes(colorName.toLowerCase()) ? 'text-white' : 'text-gray-900';
  };

  return (
    <>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm" className="flex items-center">
            <Palette className="h-4 w-4 mr-1" /> Colors
          </Button>
        </DialogTrigger>
        
        <DialogContent className="sm:max-w-lg bg-gray-900 border-gray-800">
          <DialogHeader>
            <DialogTitle>Browse by Color</DialogTitle>
          </DialogHeader>
          
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
              <span className="ml-2 text-sm text-gray-400">Loading colors...</span>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Selected color */}
              {selectedColor && (
                <div className="p-4 border border-gray-700 rounded-md">
                  <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center">
                      <div 
                        className={`w-6 h-6 rounded-full mr-2 ${getColorClass(selectedColor.name)}`}
                      ></div>
                      <h3 className="font-medium">
                        {selectedColor.name} ({selectedColor.count} images)
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
              
              {/* Color palette */}
              {!selectedColor && (
                <div>
                  <h3 className="text-sm font-medium text-gray-300 mb-2">
                    Select a color to browse images
                  </h3>
                  <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                    {colorData.map(color => (
                      <button
                        key={color.name}
                        onClick={() => handleColorSelect(color)}
                        className={`p-3 rounded-md border border-gray-700 hover:border-blue-500 transition-colors ${getColorClass(color.name)} ${getTextColorClass(color.name)} h-20 flex flex-col justify-between`}
                      >
                        <span className="font-medium">{color.name}</span>
                        <span className="text-xs opacity-80">{color.count} images</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Search results */}
              {searchResults.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-300 mb-2">
                    Results ({searchResults.length})
                  </h3>
                  <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-96 overflow-y-auto">
                    {searchResults.map((result, index) => (
                      <div 
                        key={index}
                        className="cursor-pointer group"
                        onClick={() => handleImageClick(result)}
                      >
                        <img
                          src={`${process.env.REACT_APP_API_BASE_URL}/static/${result.path}`}
                          alt={result.path}
                          className="w-full h-24 object-cover rounded-md border border-gray-800 group-hover:border-blue-500 transition-colors"
                          onError={(e) => {
                            e.target.onerror = null;
                            e.target.src = "/api/placeholder/100/100";
                          }}
                        />
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

export default ColorBrowser;