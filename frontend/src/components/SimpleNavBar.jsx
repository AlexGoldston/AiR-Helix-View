// frontend/src/components/SimplifiedNavBar.jsx
import React, { useState } from 'react';
import { Menu, Info, ZoomIn, ZoomOut } from 'lucide-react';
import { Button } from './ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './ui/sheet';
import { Slider } from './ui/slider';

// Simplified NavBar component without search functionality
const SimpleNavBar = (props) => {
  const { 
    centerImage,
    getImageName,
    similarityThreshold,
    setSimilarityThreshold,
    neighborLimit,
    setNeighborLimit,
    extendedMode,
    setExtendedMode,
    neighborDepth,
    setNeighborDepth,
    limitPerLevel,
    setLimitPerLevel,
    setDebugData,
    debugData,
    handleResetZoom,
    handleZoomIn,
    handleZoomOut
  } = props;

  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="z-10 flex items-center justify-between p-4 bg-gray-950/80 backdrop-blur-sm border-b border-gray-800">
      <div className="flex items-center">
        <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="mr-2">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-80 bg-gray-950 border-r border-gray-800">
            <SheetHeader>
              <SheetTitle className="text-2xl font-bold bg-gradient-to-r from-blue-500 to-teal-400 bg-clip-text text-transparent">Controls</SheetTitle>
            </SheetHeader>
            
            <div className="py-6 space-y-6">
              <div>
                <h3 className="mb-4 text-lg font-medium">Current Image</h3>
                <div className="bg-gray-900 rounded-lg p-2 mb-4">
                  <img 
                    src={`${process.env.REACT_APP_API_BASE_URL}/static/${getImageName(centerImage)}`}
                    alt={getImageName(centerImage)}
                    className="w-full h-48 object-contain rounded-md border border-gray-800"
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = "/api/placeholder/200/120";
                    }}
                  />
                  <p className="mt-2 text-sm text-gray-400 text-center truncate">{getImageName(centerImage)}</p>
                </div>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-400 mb-2 block">
                    Similarity Threshold: {similarityThreshold.toFixed(2)}
                  </label>
                  <Slider 
                    defaultValue={[similarityThreshold]} 
                    min={0.5} 
                    max={0.99} 
                    step={0.01}
                    onValueChange={(values) => setSimilarityThreshold(values[0])}
                    className="w-full"
                  />
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-400 mb-2 block">
                    Max Neighbors: {neighborLimit}
                  </label>
                  <Slider 
                    defaultValue={[neighborLimit]} 
                    min={5} 
                    max={50} 
                    step={5}
                    onValueChange={(values) => setNeighborLimit(values[0])}
                    className="w-full"
                  />
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="extendedMode"
                    checked={extendedMode}
                    onChange={() => setExtendedMode(!extendedMode)}
                    className="mr-2 h-4 w-4"
                  />
                  <label htmlFor="extendedMode" className="text-sm font-medium text-gray-400">
                    Extended Graph View
                  </label>
                </div>
                
                {extendedMode && (
                  <>
                    <div>
                      <label className="text-sm font-medium text-gray-400 mb-2 block">
                        Network Depth: {neighborDepth}
                      </label>
                      <Slider 
                        defaultValue={[neighborDepth]} 
                        min={1} 
                        max={3} 
                        step={1}
                        onValueChange={(values) => setNeighborDepth(values[0])}
                        className="w-full"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Higher depth shows more connections
                      </p>
                    </div>
                    
                    <div>
                      <label className="text-sm font-medium text-gray-400 mb-2 block">
                        Nodes Per Level: {limitPerLevel}
                      </label>
                      <Slider 
                        defaultValue={[limitPerLevel]} 
                        min={5} 
                        max={20} 
                        step={5}
                        onValueChange={(values) => setLimitPerLevel(values[0])}
                        className="w-full"
                      />
                    </div>
                  </>
                )}
              </div>

              <div className="pt-4">
                <Button 
                  variant="outline"
                  className="w-full"
                  onClick={() => setDebugData(debugData || { nodes: [], edges: [] })}
                >
                  Toggle Debug Panel
                </Button>
              </div>
              
              <div className="pt-4 border-t border-gray-800">
                <Button 
                  variant="outline"
                  size="sm"
                  onClick={handleResetZoom}
                  className="w-full mb-2"
                >
                  Reset Zoom
                </Button>
                
                <div className="flex gap-2">
                  <Button 
                    variant="outline"
                    size="sm"
                    onClick={handleZoomIn}
                    className="flex-1"
                  >
                    <ZoomIn className="h-4 w-4 mr-1" /> Zoom In
                  </Button>
                  
                  <Button 
                    variant="outline"
                    size="sm"
                    onClick={handleZoomOut}
                    className="flex-1"
                  >
                    <ZoomOut className="h-4 w-4 mr-1" /> Zoom Out
                  </Button>
                </div>
              </div>
            </div>
          </SheetContent>
        </Sheet>
        
        <h1 className="text-xl font-bold bg-gradient-to-r from-blue-500 to-teal-400 bg-clip-text text-transparent">
          AiR-Helix-View
        </h1>
      </div>
      
      <div className="flex items-center space-x-2">
        {/* Controls Button - Shows/hides sidebar */}
        <Button variant="ghost" size="sm" onClick={() => setSidebarOpen(true)}>
          <Info className="h-4 w-4 mr-1" /> Controls
        </Button>
      </div>
    </div>
  );
};

export default SimpleNavBar;