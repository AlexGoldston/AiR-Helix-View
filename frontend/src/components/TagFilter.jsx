// frontend/src/components/TagFilter.jsx
import React, { useState, useEffect } from 'react';
import { Tag, Filter, X, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from './ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './ui/sheet';

const TagFilter = ({ onApplyFilters, onClearFilters }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [tagData, setTagData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTags, setSelectedTags] = useState([]);
  const [activeCategory, setActiveCategory] = useState(null);
  const [expandedCategories, setExpandedCategories] = useState({});
  const [filterActive, setFilterActive] = useState(false);

  // Fetch tag data when the component mounts
  useEffect(() => {
    fetchTagData();
  }, []);

  const fetchTagData = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('${process.env.REACT_APP_API_BASE_URL}/features');
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
      } else if (Object.keys(categories).length > 0) {
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

  const handleApplyFilters = () => {
    if (selectedTags.length > 0) {
      onApplyFilters(selectedTags);
      setFilterActive(true);
      setIsOpen(false);
    }
  };

  const handleClearFilters = () => {
    setSelectedTags([]);
    onClearFilters();
    setFilterActive(false);
  };

  const toggleCategory = (category) => {
    setExpandedCategories(prev => ({
      ...prev,
      [category]: !prev[category]
    }));
  };

  return (
    <>
      <Sheet open={isOpen} onOpenChange={setIsOpen}>
        <SheetTrigger asChild>
          <Button 
            variant={filterActive ? "default" : "outline"} 
            size="sm" 
            className="flex items-center"
          >
            <Filter className={`h-4 w-4 mr-1 ${filterActive ? "text-white" : ""}`} /> 
            {filterActive ? `Filtering (${selectedTags.length})` : "Filter"}
          </Button>
        </SheetTrigger>
        
        <SheetContent side="right" className="w-80 bg-gray-950 border-l border-gray-800">
          <SheetHeader>
            <SheetTitle className="flex items-center justify-between">
              <span>Filter Graph by Tags</span>
              <Button variant="ghost" size="sm" onClick={fetchTagData} title="Refresh tags">
                <Tag className="h-4 w-4" />
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
                {/* Selected tags */}
                {selectedTags.length > 0 && (
                  <div className="mb-4 border-b border-gray-800 pb-4">
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="text-sm font-medium text-gray-300">Selected Tags</h3>
                      <Button variant="ghost" size="sm" onClick={handleClearFilters}>
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
                          className="bg-blue-600 hover:bg-blue-700 flex items-center"
                        >
                          {tag} <X className="h-3 w-3 ml-1" />
                        </Button>
                      ))}
                    </div>
                    <Button 
                      className="w-full mt-2" 
                      onClick={handleApplyFilters}
                      disabled={selectedTags.length === 0}
                    >
                      Apply Filters
                    </Button>
                  </div>
                )}
                
                {/* Tag browser by categories */}
                {tagData && tagData.categories && (
                  <div className="flex-1 overflow-y-auto">
                    {Object.keys(tagData.categories).map(category => (
                      <div key={category} className="mb-4">
                        <div 
                          className="flex justify-between items-center mb-2 cursor-pointer hover:bg-gray-800 p-2 rounded"
                          onClick={() => toggleCategory(category)}
                        >
                          <h3 className="text-sm font-medium text-gray-300 capitalize">
                            {category} Tags ({tagData.categories[category].length})
                          </h3>
                          {expandedCategories[category] ? 
                            <ChevronUp className="h-4 w-4" /> : 
                            <ChevronDown className="h-4 w-4" />
                          }
                        </div>
                        
                        {expandedCategories[category] && (
                          <div className="grid grid-cols-2 gap-2 pl-2">
                            {tagData.categories[category].map(tag => (
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
                        )}
                      </div>
                    ))}
                    
                    {selectedTags.length > 0 && (
                      <Button 
                        className="w-full mt-4" 
                        onClick={handleApplyFilters}
                      >
                        Apply Filters
                      </Button>
                    )}
                  </div>
                )}
                
                {(!tagData || Object.keys(tagData.categories || {}).length === 0) && !isLoading && (
                  <div className="text-center py-8 text-gray-400">
                    <Tag className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>No tags found in database.</p>
                    <Button className="mt-4" onClick={fetchTagData}>
                      Refresh Tags
                    </Button>
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

export default TagFilter;