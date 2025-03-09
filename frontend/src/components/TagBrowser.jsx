// frontend/src/components/TagBrowser.jsx
import React, { useState, useEffect } from 'react';
import { Tag, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import { Button } from './ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './ui/sheet';

const TagBrowser = ({ onSelectImage }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [tagData, setTagData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTags, setSelectedTags] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [activeCategory, setActiveCategory] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);

  // Fetch tag data when the component mounts
  useEffect(() => {
    fetchTagData();
  }, []);

  const fetchTagData = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:5001/features');
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      
      // Process tag data to group by categories
      const categories = processTagCategories(data.tags);
      setTagData({ tags: data.tags, categories });
      
      // If we have a contains category, set it as active by default
      if (categories.contains) {
        setActiveCategory('contains');
      } else if (categories.color) {
        setActiveCategory('color');
      } else if (categories.length > 0) {
        setActiveCategory(Object.keys(categories)[0]);
      }
      
    } catch (error) {
      console.error('Error fetching tag data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Process tags into categories
  const processTagCategories = (tags) => {
    const categories = {};
    
    tags.forEach(tag => {
      // Check if tag has a category prefix (e.g., "contains:person")
      const parts = tag.name.split(':');
      if (parts.length > 1) {
        const category = parts[0];
        const value = parts[1];
        
        if (!categories[category]) {
          categories[category] = [];
        }
        
        categories[category].push({
          fullTag: tag.name,
          value,
          count: tag.count
        });
      } else {
        // Handle tags without a category
        if (!categories['general']) {
          categories['general'] = [];
        }
        
        categories['general'].push({
          fullTag: tag.name,
          value: tag.name,
          count: tag.count
        });
      }
    });
    
    // Sort each category by count (descending)
    Object.keys(categories).forEach(category => {
      categories[category].sort((a, b) => b.count - a.count);
    });
    
    return categories;
  };

  const handleTagSelect = (tag) => {
    setSelectedTags(prev => {
      if (prev.includes(tag)) {
        return prev.filter(t => t !== tag);
      } else {
        return [...prev, tag];
      }
    });
  };

  const handleSearch = async () => {
    if (selectedTags.length === 0) return;
    
    setSearchLoading(true);
    setSearchResults([]);
    
    try {
      const tagsParam = selectedTags.join(',');
      const response = await fetch(`http://localhost:5001/search/tags?tags=${encodeURIComponent(tagsParam)}&operator=OR&limit=50`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      const data = await response.json();
      setSearchResults(data.results);
      
    } catch (error) {
      console.error('Error searching by tags:', error);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleImageClick = (image) => {
    if (onSelectImage) {
      onSelectImage(image.path);
      setIsOpen(false);
      setSelectedTags([]);
      setSearchResults([]);
    }
  };

  const clearSelection = () => {
    setSelectedTags([]);
    setSearchResults([]);
  };

  return (
    <>
      <Sheet open={isOpen} onOpenChange={setIsOpen}>
        <SheetTrigger asChild>
          <Button variant="outline" size="sm" className="flex items-center">
            <Tag className="h-4 w-4 mr-1" /> Tags
          </Button>
        </SheetTrigger>
        
        <SheetContent side="right" className="w-80 bg-gray-950 border-l border-gray-800">
          <SheetHeader>
            <SheetTitle className="flex items-center justify-between">
              <span>Browse by Tags</span>
              <Button variant="ghost" size="sm" onClick={fetchTagData} title="Refresh tags">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </SheetTitle>
          </SheetHeader>
          
          <div className="mt-4 h-full flex flex-col">
            {isLoading ? (
              <div className="flex items-center justify-center flex-1">
                <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                <span className="ml-2 text-sm text-gray-400">Loading tags...</span>
              </div>
            ) : (
              <>
                {/* Tag categories */}
                {tagData && tagData.categories && (
                  <div className="mb-4 overflow-x-auto flex space-x-2 pb-2">
                    {Object.keys(tagData.categories).map(category => (
                      <Button
                        key={category}
                        size="sm"
                        variant={activeCategory === category ? "default" : "outline"}
                        onClick={() => setActiveCategory(category)}
                      >
                        {category}
                      </Button>
                    ))}
                  </div>
                )}
                
                {/* Selected tags */}
                {selectedTags.length > 0 && (
                  <div className="mb-4 border-b border-gray-800 pb-4">
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="text-sm font-medium text-gray-300">Selected Tags</h3>
                      <Button variant="ghost" size="sm" onClick={clearSelection}>
                        Clear All
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {selectedTags.map(tag => (
                        <Button
                          key={tag}
                          size="sm"
                          variant="default"
                          onClick={() => handleTagSelect(tag)}
                          className="bg-blue-600 hover:bg-blue-700"
                        >
                          {tag}
                        </Button>
                      ))}
                    </div>
                    <Button 
                      className="w-full mt-2" 
                      onClick={handleSearch}
                      disabled={searchLoading}
                    >
                      {searchLoading ? 'Searching...' : 'Search'}
                    </Button>
                  </div>
                )}
                
                {/* Tag browser */}
                {tagData && activeCategory && (
                  <div className="flex-1 overflow-y-auto">
                    <h3 className="text-sm font-medium text-gray-300 mb-2">
                      {activeCategory} Tags
                    </h3>
                    <div className="grid grid-cols-2 gap-2">
                      {tagData.categories[activeCategory]?.map(tag => (
                        <Button
                          key={tag.fullTag}
                          size="sm"
                          variant={selectedTags.includes(tag.fullTag) ? "default" : "outline"}
                          onClick={() => handleTagSelect(tag.fullTag)}
                          className="flex items-center justify-between overflow-hidden"
                          title={`${tag.value} (${tag.count} images)`}
                        >
                          <span className="truncate mr-1">{tag.value}</span>
                          <span className="text-xs opacity-70">{tag.count}</span>
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Search results */}
                {searchResults.length > 0 && (
                  <div className="mt-4 border-t border-gray-800 pt-4">
                    <h3 className="text-sm font-medium text-gray-300 mb-2">
                      Results ({searchResults.length})
                    </h3>
                    <div className="grid grid-cols-2 gap-2 max-h-72 overflow-y-auto">
                      {searchResults.map((result, index) => (
                        <div 
                          key={index}
                          className="cursor-pointer group"
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
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
};

export default TagBrowser;