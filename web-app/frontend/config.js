// Configuration for frontend
// Tự động detect API URL dựa trên host hiện tại
(function() {
    const hostname = window.location.hostname;
    const port = window.location.port || (window.location.protocol === 'https:' ? '443' : '80');
    
    // Kiểm tra URL parameters để override API URL (cho Ngrok hoặc custom backend)
    const urlParams = new URLSearchParams(window.location.search);
    const apiUrlOverride = urlParams.get('api_url') || urlParams.get('backend_url');
    
    let API_BASE_URL;
    
    if (apiUrlOverride) {
        // Manual override từ URL parameter
        API_BASE_URL = apiUrlOverride;
        console.log('API URL overridden from URL parameter:', API_BASE_URL);
    } else if (hostname === 'localhost' || hostname === '127.0.0.1') {
        // Localhost: dùng localhost:5000
        API_BASE_URL = 'http://localhost:5000';
    } else if (hostname.includes('trycloudflare') || hostname.includes('cloudflare') || hostname.includes('loca.lt')) {
        // Nếu frontend đang chạy qua tunnel (ngrok, localtunnel, cloudflare), 
        // cần set backend URL manually hoặc qua URL parameter
        // Ví dụ: ?api_url=https://backend-tunnel-url
        console.warn('Frontend is running through tunnel. Please provide backend URL via ?api_url= parameter');
        API_BASE_URL = `${window.location.protocol}//${hostname}:5000`;
    } else {
        // IP hoặc domain khác: dùng cùng host với port 5000
        API_BASE_URL = `${window.location.protocol}//${hostname}:5000`;
    }
    
    // Export API_BASE_URL để dùng trong app.js
    window.API_BASE_URL = API_BASE_URL;
    console.log('API Base URL:', API_BASE_URL);
    console.log('Frontend URL:', window.location.origin);
    
    // Hiển thị thông báo nếu cần config manual
    if ((hostname.includes('trycloudflare') || hostname.includes('loca.lt')) && !apiUrlOverride) {
        console.warn('⚠️ Frontend is running through tunnel. To connect to backend:');
        console.warn('   Add ?api_url=YOUR_BACKEND_URL to the frontend URL');
        console.warn('   Example: https://frontend-url.trycloudflare.com?api_url=https://backend-url.trycloudflare.com');
    }
})();

