/**
 * API Configuration
 * Sử dụng environment variable hoặc fallback về localhost cho development
 */
const getApiBaseUrl = (): string => {
  // Vite sẽ tự động thay thế import.meta.env.VITE_API_URL trong build
  const envApiUrl = import.meta.env.VITE_API_URL;
  
  if (envApiUrl) {
    // Nếu là relative URL (bắt đầu bằng /), giữ nguyên
    if (envApiUrl.startsWith('/')) {
      return envApiUrl.replace(/\/$/, '');
    }
    // Nếu là absolute URL, loại bỏ trailing slash
    return envApiUrl.replace(/\/$/, '');
  }
  
  // Fallback cho development local
  return 'http://localhost:5000';
};

// Tạo API_BASE_URL, tránh duplicate /api
const apiBase = getApiBaseUrl();
// Nếu apiBase đã là "/api" hoặc kết thúc bằng "/api", không append thêm
export const API_BASE_URL = apiBase === '/api' || apiBase.endsWith('/api') 
  ? apiBase 
  : `${apiBase}/api`;

// Export base URL riêng để dùng cho các endpoint không có /api prefix
export const API_SERVER_URL = getApiBaseUrl();

