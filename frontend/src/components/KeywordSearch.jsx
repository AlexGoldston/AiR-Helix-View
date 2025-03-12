// frontend/src/components/KeywordSearch.jsx
import React, { useState } from 'react';
import { Search, X, Loader } from 'lucide-react';
import { Button } from './ui/button';

const KeywordSearch = ({ onSearch, onClear, isSearchActive }) => {
  const [keyword, setKeyword] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async () => {
    if (!keyword.trim()) return;
    
    setIsSearching(true);
    await onSearch(keyword.trim());
    setIsSearching(false);
  };

  const handleClear = () => {
    setKeyword('');
    onClear();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="relative flex items-center">
      <div className="relative flex-1">
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search filename, tags, description..."
          className="w-full bg-gray-900 border border-gray-700 rounded-l-md py-1 pl-8 pr-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
        <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        {keyword && (
          <button
            onClick={handleClear}
            className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
      <Button
        variant={isSearchActive ? "default" : "secondary"}
        size="sm"
        disabled={isSearching || !keyword.trim()}
        onClick={handleSearch}
        className="rounded-l-none"
      >
        {isSearching ? (
          <Loader className="h-4 w-4 animate-spin" />
        ) : (
          "Search"
        )}
      </Button>
    </div>
  );
};

export default KeywordSearch;