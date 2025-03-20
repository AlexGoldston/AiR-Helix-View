import { CONFIG } from '../config';

export const apiGet = async (endpoint) => {
  try {
    const response = await fetch(`${CONFIG.API_BASE_URL}${endpoint}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`API Call Error to ${endpoint}:`, error);
    throw error;
  }
};

export const apiPost = async (endpoint, data) => {
  try {
    const response = await fetch(`${CONFIG.API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`API Post Error to ${endpoint}:`, error);
    throw error;
  }
};