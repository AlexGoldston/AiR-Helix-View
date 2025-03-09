// frontend/src/components/SearchPanel.jsx
import React, { useState, useEffect } from 'react';
import { X, Search, Tag, Image, Camera, FileText, Filter } from 'lucide-react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './ui/sheet';

const SearchPanel = ({ onSelectImage }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('text');
  const [availableFeatures, setAvailableFeatures] = useState(null);
  const [selectedFeatures, setSelectedFeatures] = useState({
    tags: [],
    colors: [],
    objects: [],
    camera: '',
    orientation: ''
  });
  const [selectedImage, setSelectedImage] = useState(null);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  // Fetch available features when component mounts
  useEffect(() => {
    const fetchFeatures = async () => {
      try {
        const response = await fetch('http://localhost:5001/features');
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        setAvailableFeatures(data);
      } catch (error) {
        console.error('Error fetching features:', error);
      }
    };

    fetchFeatures();
  }, []);

  const handleSearch = async () => {
    setIsLoading(true);
    setSearchResults([]);

    try {
      let url;
      let params = new URLSearchParams();

      // Different search endpoints depending on search type
      if (activeTab === 'text' && searchQuery.trim()) {
        url = `http://localhost:5001/search?query=${encodeURIComponent(searchQuery)}&limit=20`;
      } else if (activeTab === 'advanced') {
        url = 'http://localhost:5001/search/advanced?';

        // Add tags if selected
        if (selectedFeatures.tags.length > 0) {
          params.append('tags', selectedFeatures.tags.join(','));
          params.append('tags_operator', 'OR'); // Default to OR for better results
        }

        // Add colors if selected
        if (selectedFeatures.colors.length > 0) {
          params.append('colors', selectedFeatures.colors.join(','));
          params.append('colors_operator', 'OR');
        }

        // Add objects if selected
        if (selectedFeatures.objects.length > 0) {
          params.append('objects', selectedFeatures.objects.join(','));
          params.append('objects_operator', 'OR');
          params.append('min_confidence', '0.6');
        }

        // Add camera if selected
        if (selectedFeatures.camera) {
          params.append('camera', selectedFeatures.camera);
        }

        // Add orientation if selected
        if (selectedFeatures.orientation) {
          params.append('orientation', selectedFeatures.orientation);
        }

        url += params.toString();
      } else {
        // Default case - no valid search criteria
        setIsLoading(false);
        return;
      }

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      
      // Format results based on the API response structure
      let formattedResults = [];
      
      if (activeTab === 'text') {
        formattedResults = data.results.map(result => ({
          path: result.path,
          description: result.description,
          id: result.id
        }));
      } else if (activeTab === 'advanced') {
        formattedResults = data.results.map(result => ({
          path: result.path,
          url: result.url
        }));
      }
      
      setSearchResults(formattedResults);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTagSelect = (tag) => {
    setSelectedFeatures(prev => {
      const tags = prev.tags.includes(tag)
        ? prev.tags.filter(t => t !== tag)
        : [...prev.tags, tag];
      return { ...prev, tags };
    });
  };

  const handleColorSelect = (color) => {
    setSelectedFeatures(prev => {
      const colors = prev.colors.includes(color)
        ? prev.colors.filter(c => c !== color)
        : [...prev.colors, color];
      return { ...prev, colors };
    });
  };

  const handleObjectSelect = (object) => {
    setSelectedFeatures(prev => {
      const objects = prev.objects.includes(object)
        ? prev.objects.filter(o => o !== object)
        : [...prev.objects, object];
      return { ...prev, objects };
    });
  };

  const handleCameraSelect = (camera) => {
    setSelectedFeatures(prev => ({
      ...prev,
      camera: prev.camera === camera ? '' : camera
    }));
  };

  const handleOrientationSelect = (orientation) => {
    setSelectedFeatures(prev => ({
      ...prev,
      orientation: prev.orientation === orientation ? '' : orientation
    }));
  };

  const handleClearFilters = () => {
    setSelectedFeatures({
      tags: [],
      colors: [],
      objects: [],
      camera: '',
      orientation: ''
    });
  };

  const handleImageClick = (image) => {
    setSelectedImage(image);
  };

  const handleSetAsCenterImage = () => {
    if (selectedImage && onSelectImage) {
      onSelectImage(selectedImage.path);
      setSelectedImage(null);
      setIsOpen(false);
    }
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="flex items-center"
        onClick={() => setIsOpen(true)}
      >
        <Search className="h-4 w-4 mr-1" /> Search
      </Button>

      {/* Search Dialog */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-4xl bg-gray-900 border-gray-800 max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Image Search</DialogTitle>
          </DialogHeader>

          <div className="flex gap-2 mb-4">
            <Button
              variant={activeTab === 'text' ? "default" : "outline"}
              onClick={() => setActiveTab('text')}
              size="sm"
            >
              <FileText className="h-4 w-4 mr-1" /> Text Search
            </Button>
            <Button
              variant={activeTab === 'advanced' ? "default" : "outline"}
              onClick={() => setActiveTab('advanced')}
              size="sm"
            >
              <Filter className="h-4 w-4 mr-1" /> Feature Search
            </Button>
          </div>

          {/* Text Search */}
          {activeTab === 'text' && (
            <div className="mb-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search images by description..."
                  className="w-full p-2 pl-10 rounded-md bg-gray-800 border border-gray-700 text-white"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                />
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                {searchQuery && (
                  <button 
                    className="absolute right-3 top-2.5 text-gray-400 hover:text-white"
                    onClick={() => setSearchQuery('')}
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
              <Button className="mt-2" onClick={handleSearch} disabled={isLoading}>
                {isLoading ? 'Searching...' : 'Search'}
              </Button>
            </div>
          )}

          {/* Feature Search */}
          {activeTab === 'advanced' && (
            <div className="mb-4 space-y-4 overflow-y-auto max-h-64">
              {/* Display filter sections if features are loaded */}
              {availableFeatures ? (
                <>
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="text-sm font-medium text-gray-300">Popular Tags</h3>
                      <Button variant="link" size="sm" onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}>
                        {showAdvancedFilters ? 'Show Less' : 'Show More'}
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {availableFeatures.tags.slice(0, showAdvancedFilters ? undefined : 10).map(tag => (
                        <Button
                          key={tag.name}
                          size="sm"
                          variant={selectedFeatures.tags.includes(tag.name) ? "default" : "outline"}
                          onClick={() => handleTagSelect(tag.name)}
                        >
                          <Tag className="h-3 w-3 mr-1" /> {tag.name} ({tag.count})
                        </Button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-gray-300 mb-2">Popular Colors</h3>
                    <div className="flex flex-wrap gap-2">
                      {availableFeatures.colors.slice(0, 8).map(color => (
                        <Button
                          key={color.name}
                          size="sm"
                          variant={selectedFeatures.colors.includes(color.name) ? "default" : "outline"}
                          onClick={() => handleColorSelect(color.name)}
                          className="flex items-center"
                        >
                          <div className={`w-3 h-3 rounded-full mr-1 bg-${colorMapping[color.name] || 'gray'}-500`}></div>
                          {color.name} ({color.count})
                        </Button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-gray-300 mb-2">Common Objects</h3>
                    <div className="flex flex-wrap gap-2">
                      {availableFeatures.objects.slice(0, 10).map(object => (
                        <Button
                          key={object.name}
                          size="sm"
                          variant={selectedFeatures.objects.includes(object.name) ? "default" : "outline"}
                          onClick={() => handleObjectSelect(object.name)}
                        >
                          {object.name} ({object.count})
                        </Button>
                      ))}
                    </div>
                  </div>

                  {showAdvancedFilters && (
                    <>
                      <div>
                        <h3 className="text-sm font-medium text-gray-300 mb-2">Orientation</h3>
                        <div className="flex flex-wrap gap-2">
                          {availableFeatures.orientations.map(orientation => (
                            <Button
                              key={orientation.name}
                              size="sm"
                              variant={selectedFeatures.orientation === orientation.name ? "default" : "outline"}
                              onClick={() => handleOrientationSelect(orientation.name)}
                            >
                              {orientation.name} ({orientation.count})
                            </Button>
                          ))}
                        </div>
                      </div>

                      <div>
                        <h3 className="text-sm font-medium text-gray-300 mb-2">Camera Models</h3>
                        <div className="flex flex-wrap gap-2">
                          {availableFeatures.cameras.slice(0, 8).map(camera => (
                            <Button
                              key={camera.model}
                              size="sm"
                              variant={selectedFeatures.camera === camera.model ? "default" : "outline"}
                              onClick={() => handleCameraSelect(camera.model)}
                            >
                              <Camera className="h-3 w-3 mr-1" /> {camera.model} ({camera.count})
                            </Button>
                          ))}
                        </div>
                      </div>
                    </>
                  )}

                  <div className="flex justify-between">
                    <Button variant="outline" size="sm" onClick={handleClearFilters}>
                      Clear All Filters
                    </Button>
                    <Button onClick={handleSearch} disabled={isLoading}>
                      {isLoading ? 'Searching...' : 'Search'}
                    </Button>
                  </div>
                </>
              ) : (
                <div className="text-center py-4">
                  <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
                  <p className="text-sm text-gray-400 mt-2">Loading available filters...</p>
                </div>
              )}
            </div>
          )}

          {/* Search Results */}
          <div className="flex-1 overflow-y-auto mt-4 border-t border-gray-800 pt-4">
            <h3 className="text-sm font-medium text-gray-300 mb-2">
              {searchResults.length > 0 
                ? `Search Results (${searchResults.length})`
                : isLoading 
                  ? 'Searching...'
                  : 'No results yet'}
            </h3>

            {isLoading && (
              <div className="flex justify-center py-8">
                <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
              </div>
            )}

            {!isLoading && searchResults.length === 0 && (
              <div className="text-center py-8 text-gray-400">
                <Image className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No images found. Try a different search.</p>
              </div>
            )}

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {searchResults.map((result, index) => (
                <div 
                  key={index} 
                  className="relative group cursor-pointer"
                  onClick={() => handleImageClick(result)}
                >
                  <img
                    src={`http://localhost:5001/static/${result.path}`}
                    alt={result.path}
                    className="w-full h-24 object-cover rounded-md border border-gray-800 group-hover:border-blue-500 transition-colors"
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = "/api/placeholder/200/120";
                    }}
                  />
                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-opacity rounded-md"></div>
                </div>
              ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Image Preview Dialog */}
      <Dialog open={!!selectedImage} onOpenChange={(open) => !open && setSelectedImage(null)}>
        <DialogContent className="sm:max-w-lg bg-gray-900 border-gray-800">
          <DialogHeader>
            <DialogTitle>Image Details</DialogTitle>
          </DialogHeader>

          {selectedImage && (
            <div className="space-y-4">
              <div className="bg-gray-950 p-2 rounded-lg border border-gray-800">
                <img
                  src={`http://localhost:5001/static/${selectedImage.path}`}
                  alt={selectedImage.path}
                  className="w-full rounded-md object-contain max-h-64"
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = "/api/placeholder/200/120";
                  }}
                />
              </div>

              <div>
                <p className="text-sm text-gray-400">Path: {selectedImage.path}</p>
                {selectedImage.description && (
                  <p className="text-sm mt-2 bg-gray-800 p-2 rounded">
                    {selectedImage.description}
                  </p>
                )}
              </div>

              <div className="flex justify-end mt-4">
                <Button onClick={handleSetAsCenterImage}>
                  Set as Center Image
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

// Color mapping for visualization
const colorMapping = {
  'red': 'red',
  'blue': 'blue',
  'green': 'green',
  'yellow': 'yellow',
  'orange': 'orange',
  'purple': 'purple',
  'pink': 'pink',
  'brown': 'amber',
  'gray': 'gray',
  'black': 'black',
  'white': 'gray',
  'teal': 'teal'
};

export default SearchPanel;