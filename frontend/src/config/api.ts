/**
 * API Configuration
 * Sử dụng environment variable hoặc fallback về localhost cho development
 */
const getApiBaseUrl = (): string => {
  // Vite sẽ tự động thay thế import.meta.env.VITE_API_URL trong build
  const envApiUrl = import.meta.env.VITE_API_URL;
  
  if (envApiUrl) {
    // Loại bỏ trailing slash nếu có
    return envApiUrl.replace(/\/$/, '');
  }
  
  // Fallback cho development local
  return 'http://localhost:5000';
};

export const API_BASE_URL = `${getApiBaseUrl()}/api`;

// Export base URL riêng để dùng cho các endpoint không có /api prefix
export const API_SERVER_URL = getApiBaseUrl();

