// Configuration centralization and validation
export const CONFIG = {
    API_BASE_URL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001',
    
    // Add a method to validate configuration
    validateConfig() {
      console.group('🔍 Application Configuration');
      console.log('API Base URL:', this.API_BASE_URL);
      
      // Basic sanity checks
      if (!this.API_BASE_URL.startsWith('http')) {
        console.warn('⚠️ API URL might be invalid. It should start with http:// or https://');
      }
      
      console.groupEnd();
    }
  };
  
  // Validate on import
  CONFIG.validateConfig();