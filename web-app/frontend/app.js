// Global state
let files = [];
let metadataBlocks = [];
let isLoading = false;
let currentFile = null;
let currentStep = 'upload'; // upload, extract, metadata, structure, complete

// DOM elements - will be initialized when DOM is ready
let fileInput, uploadContent, documentViewer, filesList, metadataMarkdown;
let viewerTitle, viewerSubtitle, viewerLoading, viewerError, viewerErrorMessage, viewerContent;

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    console.log('App initialized');
    
    // Initialize DOM elements
    fileInput = document.getElementById('fileInput');
    uploadContent = document.getElementById('uploadContent');
    documentViewer = document.getElementById('documentViewer');
    filesList = document.getElementById('filesList');
    metadataMarkdown = document.getElementById('metadataMarkdown');
    viewerTitle = document.getElementById('viewerTitle');
    viewerSubtitle = document.getElementById('viewerSubtitle');
    viewerLoading = document.getElementById('viewerLoading');
    viewerError = document.getElementById('viewerError');
    viewerErrorMessage = document.getElementById('viewerErrorMessage');
    viewerContent = document.getElementById('viewerContent');
    
    setupEventListeners();
    loadFiles();
    loadMetadataBlocks();
});

// Setup event listeners
function setupEventListeners() {
    if (fileInput) fileInput.addEventListener('change', handleFileSelect);
    setupDragAndDrop();
}

// Handle file selection
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    console.log('File selected:', file.name, 'Size:', file.size, 'Type:', file.type);
    
    // Client-side validation
    const allowedTypes = ['pdf', 'docx', 'txt', 'md', 'html', 'xml', 'json', 'htm', 'markdown', 'csv', 'bmp', 'jpeg', 'jpg', 'png', 'tiff', 'webp'];
    const fileExt = file.name.split('.').pop().toLowerCase();
    
    if (!allowedTypes.includes(fileExt)) {
        showError(`File type not allowed: .${fileExt}. Allowed types: ${allowedTypes.join(', ')}`);
        return;
    }
    
    if (file.size > 50 * 1024 * 1024) { // 50MB limit
        showError('File too large. Maximum size is 50MB.');
        return;
    }
    
    uploadFile(file);
}

// Upload file
async function uploadFile(file) {
    try {
        console.log('Starting upload for file:', file.name);
        showUploadProgress();

                const formData = new FormData();
        formData.append('file', file);

        const apiUrl = window.API_BASE_URL || 'http://localhost:5000';
        console.log('Sending request to:', `${apiUrl}/api/sources`);
                const response = await fetch(`${apiUrl}/api/sources`, {
                    method: 'POST',
            body: formData
        });
        
        console.log('Upload response status:', response.status);
        console.log('Upload response headers:', response.headers);
        
        const result = await response.json();
        console.log('Upload result:', result);
        
        if (result.success) {
            showUploadResult(result);
            loadFiles(); // Refresh file list
            updateProgressStep('extract'); // Move to extract step
                } else {
            showError('Upload failed: ' + result.error);
        }
    } catch (error) {
        console.error('Upload error:', error);
        showError('Upload failed: ' + error.message);
        } finally {
        hideUploadProgress();
    }
}

// Show upload progress
function showUploadProgress() {
    const uploadProgress = document.getElementById('uploadProgress');
    const uploadResult = document.getElementById('uploadResult');
    if (uploadProgress) uploadProgress.style.display = 'block';
    if (uploadResult) uploadResult.style.display = 'none';
}

// Hide upload progress
function hideUploadProgress() {
    const uploadProgress = document.getElementById('uploadProgress');
    if (uploadProgress) uploadProgress.style.display = 'none';
}

// Show upload result
function showUploadResult(result) {
    const uploadDetails = document.getElementById('uploadDetails');
    const uploadResult = document.getElementById('uploadResult');
    
    if (uploadDetails) {
        uploadDetails.innerHTML = `
            <p><strong>File:</strong> ${result.filename}</p>
            <p><strong>Type:</strong> ${result.file_type}</p>
            <p><strong>Size:</strong> ${formatFileSize(result.file_size)}</p>
        `;
    }
    if (uploadResult) uploadResult.style.display = 'block';
}

// Reset upload
function resetUpload() {
    const uploadResult = document.getElementById('uploadResult');
    if (uploadResult) uploadResult.style.display = 'none';
    if (fileInput) fileInput.value = '';
}

// Load files from API
async function loadFiles() {
    if (isLoading) return;
    
    try {
        isLoading = true;
        console.log('Loading files from API...');
        
        const apiUrl = window.API_BASE_URL || 'http://localhost:5000';
        const response = await fetch(`${apiUrl}/api/sources?limit=50&offset=0`);
                console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);

            if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const text = await response.text();
        console.log('Response text:', text.substring(0, 200));
        
        const data = JSON.parse(text);
        console.log('Parsed data:', data);
        
        files = data.sources || [];
        renderFiles();
        
    } catch (error) {
        console.error('Error loading files:', error);
        showError('Failed to load files: ' + error.message);
        } finally {
        isLoading = false;
    }
}

// Load metadata blocks from API
async function loadMetadataBlocks() {
    try {
        console.log('Loading metadata blocks from API...');
        
        const apiUrl = window.API_BASE_URL || 'http://localhost:5000';
        const response = await fetch(`${apiUrl}/api/metadata`);

            if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
        console.log('Metadata blocks data:', data);
        
        metadataBlocks = data.blocks || [];
        renderMetadataBlocks();
        
    } catch (error) {
        console.error('Error loading metadata blocks:', error);
        showError('Failed to load metadata blocks: ' + error.message);
    }
}

// Render files list
function renderFiles() {
    const filesCount = document.getElementById('filesCount');
    filesCount.textContent = `${files.length} file${files.length !== 1 ? 's' : ''}`;
    
    if (files.length === 0) {
        filesList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">
                    <svg viewBox="0 0 24 24" width="48" height="48">
                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" fill="currentColor"/>
                    </svg>
                </div>
                <h3>No documents yet</h3>
                <p>Upload your first document to get started</p>
            </div>
        `;
            return;
        }

    const filesHTML = files.map(file => `
        <div class="file-item" onclick="viewFile('${file.id}')">
            <div class="file-icon ${getFileIconClass(file.filename)}">
                ${getFileIconText(file.filename)}
            </div>
            <div class="file-info">
                <div class="file-name">${file.filename}</div>
                <div class="file-meta">
                    <span class="file-size">${formatFileSize(file.file_size)}</span>
                    <span class="file-date">${formatDate(file.upload_time)}</span>
                </div>
            </div>
            <div class="file-actions">
                <button class="view-btn" onclick="viewFile('${file.id}')">View</button>
            </div>
        </div>
    `).join('');
    
    filesList.innerHTML = filesHTML;
}

// Get file icon class
function getFileIconClass(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    switch (ext) {
        case 'pdf': return 'pdf';
            case 'md':
        case 'markdown': return 'md';
        default: return 'default';
    }
}

// Get file icon text
function getFileIconText(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    switch (ext) {
        case 'pdf': return 'PDF';
            case 'md':
        case 'markdown': return 'MD';
        default: return 'FILE';
    }
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Show success message
function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success';
    successDiv.textContent = message;
    
    // Insert after header
    const container = document.querySelector('.container');
    const header = document.querySelector('.header');
    container.insertBefore(successDiv, header.nextSibling);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (successDiv.parentNode) {
            successDiv.parentNode.removeChild(successDiv);
        }
    }, 3000);
}

// Show error message
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    
    // Insert after header
    const container = document.querySelector('.container');
    const header = document.querySelector('.header');
    if (container && header) {
        // Insert after header, or append to container if no next sibling
        const nextSibling = header.nextSibling;
        if (nextSibling) {
            container.insertBefore(errorDiv, nextSibling);
        } else {
            container.appendChild(errorDiv);
        }
    }
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.parentNode.removeChild(errorDiv);
        }
    }, 5000);
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return 'Today';
    if (diffDays === 2) return 'Yesterday';
    if (diffDays <= 7) return `${diffDays - 1} days ago`;
    
    return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
}

// View file function
function viewFile(fileId) {
    currentFile = files.find(f => f.id === fileId);
    if (!currentFile) return;
    
    // Show integrated viewer
    showViewer();
    
    // Set title
    viewerTitle.textContent = currentFile.filename;
    viewerSubtitle.textContent = `${formatFileSize(currentFile.file_size)} • ${currentFile.file_type.toUpperCase()}`;
    
    // Show loading
    viewerLoading.style.display = 'flex';
    viewerError.style.display = 'none';
    viewerContent.innerHTML = '';
    
    // Load document
    loadDocument(fileId);
}

// Show integrated viewer
function showViewer() {
    uploadContent.style.display = 'none';
    documentViewer.style.display = 'flex';
    
    // Add class to container for side-by-side layout
    const mainContainer = document.getElementById('mainContainer');
    mainContainer.classList.add('viewer-open');
    
    // Hide documents section header
    const documentsHeader = document.getElementById('documentsSectionHeader');
    documentsHeader.style.display = 'none';
    
    // Disable upload area click
    const uploadArea = document.getElementById('uploadArea');
    uploadArea.style.pointerEvents = 'none';
    uploadArea.style.cursor = 'default';
}

// Hide integrated viewer
function closeViewer() {
    documentViewer.style.display = 'none';
    uploadContent.style.display = 'flex';
    currentFile = null;
    hideViewerStates();
    
    // Remove class from container to return to normal layout
    const mainContainer = document.getElementById('mainContainer');
    mainContainer.classList.remove('viewer-open');
    
    // Show documents section header
    const documentsHeader = document.getElementById('documentsSectionHeader');
    documentsHeader.style.display = 'flex';
    
    // Re-enable upload area click
    const uploadArea = document.getElementById('uploadArea');
    uploadArea.style.pointerEvents = 'auto';
    uploadArea.style.cursor = 'pointer';
}

// Hide all viewer states
function hideViewerStates() {
    viewerLoading.style.display = 'none';
    viewerError.style.display = 'none';
    viewerContent.innerHTML = '';
}

// Load document in integrated viewer
async function loadDocument(fileId) {
    try {
        // For text files, get raw content to preserve UTF-8 encoding
        const apiUrl = window.API_BASE_URL || 'http://localhost:5000';
        const url = currentFile.file_type === 'txt' || currentFile.file_type === 'md' 
            ? `${apiUrl}/api/sources/${fileId}/content?render=raw`
            : `${apiUrl}/api/sources/${fileId}/content?render=html`;
            
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        // Get content type to determine how to handle the response
        const contentType = response.headers.get('content-type') || '';
        console.log('Content type:', contentType);
        
        let html;
        
        if (currentFile.file_type === 'txt' || currentFile.file_type === 'md') {
            // For text files, get raw content and wrap in HTML
            const text = await response.text();
            html = createTextHtml(text, currentFile.filename);
        } else {
            // For HTML files, use as-is
            html = await response.text();
        }
        
        // Display content directly in viewer
        viewerContent.innerHTML = html;
        viewerLoading.style.display = 'none';
        
    } catch (error) {
        console.error('Error loading document:', error);
        showViewerError('Failed to load document: ' + error.message);
    }
}

// Create HTML wrapper for text files
function createTextHtml(text, filename) {
    return `<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${filename}</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 24px;
            background: #ffffff;
            color: #202124;
            font-size: 14px;
        }
        .text-content {
            max-width: 800px;
            margin: 0 auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .file-header {
            border-bottom: 1px solid #dadce0;
            padding-bottom: 16px;
            margin-bottom: 24px;
        }
        .file-title {
            font-size: 18px;
            font-weight: 500;
            color: #202124;
            margin-bottom: 4px;
        }
        .file-meta {
            font-size: 12px;
            color: #5f6368;
        }
    </style>
</head>
<body>
    <div class="file-header">
        <div class="file-title">${filename}</div>
        <div class="file-meta">Text Document</div>
    </div>
    <div class="text-content">${escapeHtml(text)}</div>
</body>
</html>`;
}

// Escape HTML special characters
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show viewer error
function showViewerError(message) {
    viewerErrorMessage.textContent = message;
    viewerLoading.style.display = 'none';
    viewerError.style.display = 'flex';
    viewerContent.innerHTML = '';
}

// Retry load
function retryLoad() {
    if (!currentFile) return;
    loadDocument(currentFile.id);
}

// Delete current file
async function deleteDocument() {
    if (!currentFile) return;
    
    // Confirm deletion
    const confirmed = confirm(`Are you sure you want to delete "${currentFile.filename}"?\n\nThis action cannot be undone.`);
    if (!confirmed) return;
    
    try {
        console.log('Deleting file:', currentFile.id);
        
        const apiUrl = window.API_BASE_URL || 'http://localhost:5000';
        const response = await fetch(`${apiUrl}/api/sources/${currentFile.id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        console.log('Delete result:', result);
        
        if (result.success) {
            // Close viewer
            closeViewer();
            
            // Refresh file list
            loadFiles();
            
            // Show success message
            showSuccess(`File "${currentFile.filename}" deleted successfully`);
                } else {
            showError('Failed to delete file: ' + result.error);
        }
        
    } catch (error) {
        console.error('Error deleting file:', error);
        showError('Failed to delete file: ' + error.message);
    }
}

// Drag and drop functionality
function setupDragAndDrop() {
    const uploadArea = document.getElementById('uploadArea');
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect({ target: { files: files } });
        }
    });
    
    uploadArea.addEventListener('click', (e) => {
        // Only trigger file input if viewer is not open
        if (documentViewer.style.display === 'none' || documentViewer.style.display === '') {
            document.getElementById('fileInput').click();
        } else {
            // Prevent event bubbling when viewer is open
            e.stopPropagation();
            e.preventDefault();
        }
    });
}

// Generate metadata blocks for current file
async function generateMetadata() {
    if (!currentFile) {
        showError('Không có file nào được chọn');
        return;
    }

    if (!confirm(`Bạn có chắc chắn muốn tạo metadata blocks cho file "${currentFile.filename}"?\n\nQuá trình này sẽ sử dụng AI để phân tích và chia nhỏ tài liệu thành các blocks có cấu trúc.`)) {
            return;
        }

    // Get button reference and original text
    const generateBtn = document.getElementById('generateMetadataBtn');
    if (!generateBtn) {
        showError('Generate Metadata button not found');
                return;
            }

    const originalText = generateBtn.innerHTML;

    try {
        // Show loading state
        generateBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="16" height="16" class="loading-spinner">
                <path d="M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z" fill="currentColor"/>
            </svg>
            Generating...
        `;
        generateBtn.disabled = true;
        
        const apiUrl = window.API_BASE_URL || 'http://localhost:5000';
        const response = await fetch(`${apiUrl}/api/sources/${currentFile.id}/generate-metadata`, {
            method: 'POST',
                headers: {
                'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`Đã tạo thành công ${result.total} metadata blocks cho file "${currentFile.filename}"!\n\nSử dụng công nghệ AI để phân tích và chia nhỏ tài liệu thành các blocks có cấu trúc.`);
            
            // Refresh metadata blocks
            loadMetadataBlocks();
            
            // Show metadata blocks info
            if (result.blocks && result.blocks.length > 0) {
                const categories = [...new Set(result.blocks.map(block => block.category))];
                
                console.log('Generated metadata blocks:', result.blocks);
                console.log(`Categories found: ${categories.join(', ')}`);
            }
            
            // Move to metadata step, then complete
            updateProgressStep('metadata');
            setTimeout(() => updateProgressStep('complete'), 1000);
            } else {
            showError(result.error || 'Lỗi khi tạo metadata blocks');
        }
        
    } catch (error) {
        console.error('Error generating metadata:', error);
        showError('Lỗi khi tạo metadata blocks: ' + error.message);
    } finally {
        // Restore button state
        generateBtn.innerHTML = originalText;
        generateBtn.disabled = false;
    }
}

// Render metadata blocks as complete markdown
async function renderMetadataBlocks() {
    const metadataCount = document.getElementById('metadataCount');
    const clearMetadataBtn = document.getElementById('clearMetadataBtn');
    const exportMarkdownBtn = document.getElementById('exportMarkdownBtn');
    const metadataMarkdown = document.getElementById('metadataMarkdown');
    
    metadataCount.textContent = `${metadataBlocks.length} block${metadataBlocks.length !== 1 ? 's' : ''}`;
    
    // Show/hide buttons based on metadata count
    if (metadataBlocks.length > 0) {
        clearMetadataBtn.style.display = 'inline-flex';
        exportMarkdownBtn.style.display = 'inline-flex';
    } else {
        clearMetadataBtn.style.display = 'none';
        exportMarkdownBtn.style.display = 'none';
    }
    
    if (metadataBlocks.length === 0) {
        metadataMarkdown.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">
                    <svg viewBox="0 0 24 24" width="48" height="48">
                        <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 8,12A4,4 0 0,1 12,16A4,4 0 0,1 12,8Z" fill="currentColor"/>
                    </svg>
                </div>
                <h3>No metadata blocks yet</h3>
                <p>Generate metadata from your documents to see complete markdown output</p>
            </div>
        `;
        return;
    }

    try {
        // Lấy markdown từ backend (đã được format với build_can_cu_markdown)
        const apiUrl = window.API_BASE_URL || 'http://localhost:5000';
        const url = `${apiUrl}/api/metadata/markdown`;
        console.log('Fetching markdown from:', url);
        console.log('Current origin:', window.location.origin);
        
        // Tạo AbortController cho timeout (tương thích với browser cũ hơn)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 seconds
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        console.log('Response status:', response.status);
        console.log('Response headers:', [...response.headers.entries()]);
        
        if (!response.ok) {
            const errorText = await response.text().catch(() => 'No error message');
            console.error('API error:', response.status, errorText);
            throw new Error(`HTTP ${response.status}: ${errorText.substring(0, 100)}`);
        }
        
        const data = await response.json();
        console.log('Markdown data received, blocks_count:', data.blocks_count);
        
        if (data.success && data.markdown) {
            // Sử dụng markdown từ backend (đã có format đúng với keyword)
            const htmlContent = markdownToHtml(data.markdown);
            metadataMarkdown.innerHTML = `
                <div class="metadata-markdown-content">
                    ${htmlContent}
                </div>
            `;
            return;
        } else {
            console.warn('API returned success=false or no markdown:', data);
            throw new Error(data.error || 'No markdown content received');
        }
    } catch (error) {
        console.error('Error loading markdown from API:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        
        // Fallback: dùng hàm cũ
        console.log('Falling back to local markdown generation');
        const markdownContent = generateMarkdownContent(metadataBlocks);
        const htmlContent = markdownToHtml(markdownContent);
        metadataMarkdown.innerHTML = `
            <div class="metadata-markdown-content">
                ${htmlContent}
            </div>
        `;
    }
}

// Generate markdown content from metadata blocks
function generateMarkdownContent(blocks) {
    let markdown = '';
    
    blocks.forEach((block, index) => {
        // Add separator between blocks (except for first block)
        if (index > 0) {
            markdown += '\n\n---\n\n';
        }
        
        // Metadata section
        markdown += '## Metadata\n';
        markdown += `- **doc_id**: ${block.doc_id || 'N/A'}\n`;
        markdown += `- **department**: ${block.department || 'N/A'}\n`;
        markdown += `- **type_data**: ${block.type_data || 'N/A'}\n`;
        markdown += `- **category**: ${block.category || 'N/A'}\n`;
        markdown += `- **date**: ${block.date || 'N/A'}\n`;
        markdown += `- **source**: ${block.source || 'N/A'}\n\n`;
        
        // Content section
        markdown += '## Nội dung\n\n';
        markdown += block.content || '';
    });
    
    return markdown;
}

// Convert markdown to HTML for display
function markdownToHtml(markdown) {
    return markdown
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^\- \*\*(.*?)\*\*: (.*$)/gim, '<li><strong>$1</strong>: $2</li>')
        .replace(/^\- (.*$)/gim, '<li>$1</li>')
        .replace(/^---$/gim, '<hr>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/^(.*)$/gm, '<p>$1</p>')
        .replace(/<p><h2>/g, '<h2>')
        .replace(/<\/h2><\/p>/g, '</h2>')
        .replace(/<p><li>/g, '<ul><li>')
        .replace(/<\/li><\/p>/g, '</li></ul>')
        .replace(/<p><hr><\/p>/g, '<hr>')
        .replace(/<p><\/p>/g, '')
        .replace(/<ul><li><strong>(.*?)<\/strong>: (.*?)<\/li><\/ul>/g, '<ul><li><strong>$1</strong>: $2</li></ul>');
}

// View metadata block
function viewMetadataBlock(blockId) {
    const block = metadataBlocks.find(b => b.id === blockId);
    if (!block) return;
    
    // Show block content in a modal or alert for now
    const content = `
Category: ${block.category}
Source: ${block.source}
Date: ${block.date}
Doc ID: ${block.doc_id}
Department: ${block.department}
Type Data: ${block.type_data}

Content:
${block.content}
    `;
    
    alert(content);
}

// Clear all metadata blocks
async function clearAllMetadata() {
    if (metadataBlocks.length === 0) {
        showError('Không có metadata blocks nào để xóa');
        return;
    }
    
    // Confirm deletion
    const confirmed = confirm(`Bạn có chắc chắn muốn xóa tất cả ${metadataBlocks.length} metadata blocks?\n\nHành động này không thể hoàn tác.`);
    if (!confirmed) return;
    
    try {
        console.log('Clearing all metadata blocks...');
        
        const apiUrl = window.API_BASE_URL || 'http://localhost:5000';
        const response = await fetch(`${apiUrl}/api/metadata`, {
            method: 'DELETE'
            });

            if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('Clear metadata result:', result);
        
        if (result.success) {
            // Clear local state
            metadataBlocks = [];
            renderMetadataBlocks();
            
            // Show success message
            showSuccess(`Đã xóa thành công ${result.deleted_count} metadata blocks!`);
            } else {
            showError('Lỗi khi xóa metadata blocks: ' + result.error);
        }
        
    } catch (error) {
        console.error('Error clearing metadata:', error);
        showError('Lỗi khi xóa metadata blocks: ' + error.message);
    }
}

// Export metadata blocks to markdown file
async function exportToMarkdown() {
    if (metadataBlocks.length === 0) {
        showError('Không có metadata blocks nào để export');
        return;
    }
    
    try {
        console.log('Exporting metadata blocks to markdown...');
        
        // Show loading state
        const exportBtn = document.getElementById('exportMarkdownBtn');
        const originalText = exportBtn.innerHTML;
        exportBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="16" height="16" class="loading-spinner">
                <path d="M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z" fill="currentColor"/>
                                    </svg>
            Exporting...
        `;
        exportBtn.disabled = true;
        
        // Generate markdown content locally
        const markdownContent = generateMarkdownContent(metadataBlocks);
        
        // Create and download file
        const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `metadata_export_${new Date().toISOString().slice(0, 10)}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showSuccess(`Đã export thành công ${metadataBlocks.length} metadata blocks thành file markdown!`);
        
    } catch (error) {
        console.error('Error exporting metadata:', error);
        showError('Lỗi khi export metadata blocks: ' + error.message);
    } finally {
        // Restore button state
        const exportBtn = document.getElementById('exportMarkdownBtn');
        exportBtn.innerHTML = originalText;
        exportBtn.disabled = false;
    }
}

// Update progress step
function updateProgressStep(step) {
    currentStep = step;
    
    // Remove active class from all steps
    const allSteps = ['step-upload', 'step-extract', 'step-metadata', 'step-structure', 'step-complete'];
    allSteps.forEach(stepId => {
        const stepEl = document.getElementById(stepId);
        if (stepEl) {
            stepEl.classList.remove('active', 'completed');
        }
    });
    
    // Add active to current step and completed to previous steps
    const stepMap = {
        'upload': 'step-upload',
        'extract': 'step-extract',
        'metadata': 'step-metadata',
        'structure': 'step-structure',
        'complete': 'step-complete'
    };
    
    const stepOrder = ['upload', 'extract', 'metadata', 'structure', 'complete'];
    const currentIndex = stepOrder.indexOf(step);
    
    stepOrder.forEach((stepName, index) => {
        const stepEl = document.getElementById(stepMap[stepName]);
        if (stepEl) {
            if (index < currentIndex) {
                stepEl.classList.add('completed');
            } else if (index === currentIndex) {
                stepEl.classList.add('active');
            }
        }
    });
}

// Initialize progress on load
updateProgressStep(currentStep);

// Global functions for HTML onclick
window.resetUpload = resetUpload;
window.loadFiles = loadFiles;
window.viewFile = viewFile;
window.closeViewer = closeViewer;
window.retryLoad = retryLoad;
window.generateMetadata = generateMetadata;
window.viewMetadataBlock = viewMetadataBlock;
window.clearAllMetadata = clearAllMetadata;
window.exportToMarkdown = exportToMarkdown;
window.updateProgressStep = updateProgressStep;