const { useState, useRef, useEffect } = React;

function App() {
    const [file, setFile] = useState(null);
    const [sources, setSources] = useState([]);
    const [metadataBlocks, setMetadataBlocks] = useState([]);
    const [loading, setLoading] = useState(false);
    const [activeMenuId, setActiveMenuId] = useState(null);
    const [showDeletePopup, setShowDeletePopup] = useState(false);
    const [sourceToDelete, setSourceToDelete] = useState(null);
    const [showRenamePopup, setShowRenamePopup] = useState(false);
    const [sourceToRename, setSourceToRename] = useState(null);
    const [newFileName, setNewFileName] = useState('');
    const [activeDocument, setActiveDocument] = useState(null);
    const [activeDocumentContent, setActiveDocumentContent] = useState('');
    const [sidebarWidth, setSidebarWidth] = useState(350);
    const [isResizing, setIsResizing] = useState(false);
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 });
    const fileInputRef = useRef(null);
    const deleteMetadataBlock = async (blockId) => {
        try {
            const response = await fetch(`http://localhost:5000/api/metadata/${blockId}`, {
                method: 'DELETE',
                mode: 'cors',
                headers: {
                    'Accept': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data.success) {
                // Reload metadata blocks
                await loadMetadataBlocks();
                console.log('Metadata block deleted successfully');
            } else {
                console.error('Failed to delete metadata block:', data.error);
                alert('Lỗi khi xóa metadata block: ' + data.error);
            }
        } catch (err) {
            console.error('Error deleting metadata block:', err);
            alert('Lỗi kết nối khi xóa metadata block: ' + err.message);
        }
    };

    const processFileMetadata = async (sourceId) => {
        try {
            console.log('Processing metadata for source:', sourceId);
            const response = await fetch(`http://localhost:5000/api/sources/${sourceId}/process-metadata`, {
                method: 'POST',
                mode: 'cors',
                headers: {
                    'Accept': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Metadata processing result:', data);

            if (data.success) {
                // Reload metadata blocks to show new ones
                await loadMetadataBlocks();
                console.log('Metadata processed successfully');
            } else {
                console.error('Metadata processing failed:', data.error);
            }
        } catch (err) {
            console.error('Error processing metadata:', err);
        }
    };

    const loadMetadataBlocks = async () => {
        try {
            const response = await fetch('http://localhost:5000/api/metadata', {
                method: 'GET',
                mode: 'cors',
                headers: {
                    'Accept': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Loaded metadata blocks:', data);

            if (data.blocks) {
                setMetadataBlocks(data.blocks);
            }
        } catch (err) {
            console.error('Error loading metadata blocks:', err);
        }
    };

    const loadSources = async () => {
        try {
            const response = await fetch('http://localhost:5000/api/sources', {
                method: 'GET',
                mode: 'cors',
                headers: {
                    'Accept': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Loaded sources:', data);

            if (data.sources) {
                const sourcesList = data.sources.map(source => ({
                    id: source.id,
                    name: source.filename,
                    type: source.file_type,
                    selected: true
                }));
                setSources(sourcesList);
            }
        } catch (err) {
            console.error('Error loading sources:', err);
            // Don't show alert for initial load failure
        }
    };

    // Load sources and metadata blocks when component mounts
    useEffect(() => {
        loadSources();
        loadMetadataBlocks();
    }, []);

    const getFileIcon = (fileName) => {
        const extension = fileName.split('.').pop().toLowerCase();
        switch (extension) {
            case 'pdf':
                return (
                    <svg viewBox="0 0 24 24">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" fill="#dc3545"/>
                        <text x="12" y="16" textAnchor="middle" fontSize="8" fontWeight="bold" fill="white">PDF</text>
                    </svg>
                );
            case 'doc':
            case 'docx':
                return (
                    <svg viewBox="0 0 24 24">
                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" fill="#2196f3"/>
                    </svg>
                );
            case 'txt':
                return (
                    <svg viewBox="0 0 24 24">
                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" fill="#6c757d"/>
                    </svg>
                );
            case 'html':
            case 'htm':
                return (
                    <svg viewBox="0 0 24 24">
                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" fill="#ff9800"/>
                    </svg>
                );
            case 'csv':
                return (
                    <svg viewBox="0 0 24 24">
                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" fill="#4caf50"/>
                    </svg>
                );
            case 'xml':
                return (
                    <svg viewBox="0 0 24 24">
                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" fill="#ff5722"/>
                    </svg>
                );
            case 'json':
                return (
                    <svg viewBox="0 0 24 24">
                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" fill="#ffc107"/>
                    </svg>
                );
            case 'jpg':
            case 'jpeg':
            case 'png':
            case 'gif':
            case 'bmp':
            case 'webp':
            case 'tiff':
                return (
                    <svg viewBox="0 0 24 24">
                        <path d="M8.5,13.5L11,16.5L14.5,12L19,18H5M21,19V5C21,3.89 20.1,3 19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19Z" fill="#9c27b0"/>
                    </svg>
                );
            case 'md':
            case 'markdown':
                return (
                    <svg viewBox="0 0 24 24">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" fill="#795548"/>
                        <text x="12" y="16" textAnchor="middle" fontSize="8" fontWeight="bold" fill="white">MD</text>
                    </svg>
                );
            default:
                return (
                    <svg viewBox="0 0 24 24">
                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" fill="#6c757d"/>
                    </svg>
                );
        }
    };

    const handleFileSelect = async (selectedFile) => {
        console.log('File selected:', selectedFile);
        setFile(selectedFile);
        setIsUploading(true);
        setUploadProgress({ current: 1, total: 1 });
        
        if (selectedFile) {
            try {
                const formData = new FormData();
                formData.append('file', selectedFile);

                console.log('Uploading file to:', 'http://localhost:5000/api/sources');

                const response = await fetch('http://localhost:5000/api/sources', {
                    method: 'POST',
                    body: formData,
                    mode: 'cors',
                    headers: {
                        'Accept': 'application/json',
                    }
                });

                console.log('Response status:', response.status);
                console.log('Response ok:', response.ok);

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                console.log('Response data:', data);
                console.log('Current sources before update:', sources);

                if (data.success) {
                    const newSource = {
                        id: data.source_id || Date.now(),
                        name: data.filename || selectedFile.name,
                        type: data.file_type || selectedFile.name.split('.').pop().toLowerCase(),
                        selected: true
                    };
                    console.log('Adding new source:', newSource);
                    setSources(prev => {
                        console.log('Previous sources:', prev);
                        const updated = [...prev, newSource];
                        console.log('Updated sources:', updated);
                        return updated;
                    });
                    
                    // Process metadata for the uploaded file
                    if (data.source_id) {
                        await processFileMetadata(data.source_id);
                    }
                } else {
                    alert('Lỗi khi upload file: ' + (data.error || 'Không thể upload tài liệu'));
                }
            } catch (err) {
                console.error('Error uploading file:', err);
                alert('Lỗi kết nối khi upload file: ' + err.message);
            } finally {
                setIsUploading(false);
                setUploadProgress({ current: 0, total: 0 });
            }
        }
    };

    const handleMultipleFileSelect = async (files) => {
        if (!files || files.length === 0) return;
        
        console.log('=== MULTIPLE FILE UPLOAD START ===');
        console.log('Files selected:', files.length);
        console.log('File names:', Array.from(files).map(f => f.name));
        console.log('File sizes:', Array.from(files).map(f => f.size));
        
        setIsUploading(true);
        setUploadProgress({ current: 0, total: files.length });
        
        let successCount = 0;
        let errorCount = 0;
        const errors = [];
        
        // Upload từng file một cách tuần tự
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            console.log(`\n--- Uploading file ${i + 1}/${files.length} ---`);
            console.log('File name:', file.name);
            console.log('File size:', file.size);
            console.log('File type:', file.type);
            
            setUploadProgress({ current: i + 1, total: files.length });
            
            try {
                const formData = new FormData();
                formData.append('file', file);

                console.log('Sending request to:', 'http://localhost:5000/api/sources');
                
                const response = await fetch('http://localhost:5000/api/sources', {
                    method: 'POST',
                    body: formData,
                    mode: 'cors',
                    headers: {
                        'Accept': 'application/json',
                    }
                });

                console.log('Response status:', response.status);
                console.log('Response ok:', response.ok);

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('Response error:', errorText);
                    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
                }

                const data = await response.json();
                console.log('Response data:', data);

                if (data.success) {
                    const newSource = {
                        id: data.source_id || Date.now() + i,
                        name: data.filename || file.name,
                        type: data.file_type || file.name.split('.').pop().toLowerCase(),
                        selected: true
                    };
                    
                    console.log('Adding new source:', newSource);
                    setSources(prev => {
                        const updated = [...prev, newSource];
                        console.log('Updated sources count:', updated.length);
                        return updated;
                    });
                    successCount++;
                    console.log('✅ File uploaded successfully');
                } else {
                    const errorMsg = `Error uploading ${file.name}: ${data.error || 'Unknown error'}`;
                    console.error(errorMsg);
                    errors.push(errorMsg);
                    errorCount++;
                }
            } catch (err) {
                const errorMsg = `Error uploading ${file.name}: ${err.message}`;
                console.error(errorMsg);
                errors.push(errorMsg);
                errorCount++;
            }
        }
        
        console.log('\n=== UPLOAD SUMMARY ===');
        console.log('Total files:', files.length);
        console.log('Success:', successCount);
        console.log('Errors:', errorCount);
        console.log('Error details:', errors);
        
        setIsUploading(false);
        setUploadProgress({ current: 0, total: 0 });
        
        // Hiển thị thông báo kết quả
        if (files.length > 1) {
            if (errorCount === 0) {
                alert(`✅ Đã upload thành công ${successCount} file!`);
            } else if (successCount === 0) {
                alert(`❌ Không thể upload file nào. Vui lòng kiểm tra console để xem chi tiết lỗi.`);
            } else {
                alert(`⚠️ Upload thành công ${successCount} file, ${errorCount} file lỗi.`);
            }
        }
        
        console.log('=== MULTIPLE FILE UPLOAD END ===\n');
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.currentTarget.classList.add('dragover');
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        e.currentTarget.classList.remove('dragover');
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.currentTarget.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            if (files.length === 1) {
                handleFileSelect(files[0]);
            } else {
                handleMultipleFileSelect(files);
            }
        }
    };

    const handleSendMessage = async () => {
        if (!inputMessage.trim()) return;

        const newMessage = {
            id: Date.now(),
            type: 'user',
            content: inputMessage
        };

        setMessages(prev => [...prev, newMessage]);
        setInputMessage('');
        setLoading(true);

        try {
            const formData = new FormData();
            if (file) {
                formData.append('file', file);
            }
            formData.append('message', inputMessage);

            const response = await fetch('http://localhost:5000/api/chat', {
                method: 'POST',
                body: formData,
                mode: 'cors',
                headers: {
                    'Accept': 'application/json',
                }
            });

            const data = await response.json();

            if (data.success) {
                const aiResponse = {
                    id: Date.now() + 1,
                    type: 'ai',
                    content: data.response
                };
                setMessages(prev => [...prev, aiResponse]);
            } else {
                const errorResponse = {
                    id: Date.now() + 1,
                    type: 'ai',
                    content: 'Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi của bạn.'
                };
                setMessages(prev => [...prev, errorResponse]);
            }
        } catch (err) {
            const errorResponse = {
                id: Date.now() + 1,
                type: 'ai',
                content: 'Lỗi kết nối: ' + err.message
            };
            setMessages(prev => [...prev, errorResponse]);
        } finally {
            setLoading(false);
        }
    };

    const handlePromptClick = (prompt) => {
        setInputMessage(prompt);
    };

    const toggleSourceSelection = (sourceId) => {
        setSources(prev => prev.map(source => 
            source.id === sourceId 
                ? { ...source, selected: !source.selected }
                : source
        ));
    };

    const selectAllSources = () => {
        const allSelected = sources.every(source => source.selected);
        setSources(prev => prev.map(source => ({ ...source, selected: !allSelected })));
    };

    const deleteSource = async (sourceId) => {
        try {
            const sourceToDelete = sources.find(s => s.id === sourceId);
            if (!sourceToDelete) return;

            const response = await fetch(`http://localhost:5000/api/sources/${sourceId}`, {
                method: 'DELETE',
                mode: 'cors',
                headers: {
                    'Accept': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                // Remove from local state
                setSources(prev => prev.filter(source => source.id !== sourceId));
                
                // If the deleted source was the current file, clear it
                if (file && sourceToDelete.name === file.name) {
                    setFile(null);
                }
            } else {
                alert('Lỗi khi xóa nguồn: ' + (data.error || 'Không thể xóa tài liệu'));
            }
        } catch (err) {
            console.error('Error deleting source:', err);
            alert('Lỗi kết nối khi xóa nguồn: ' + err.message);
        }
    };

    const renameSource = async (sourceId, newName) => {
        try {
            const response = await fetch(`http://localhost:5000/api/sources/${sourceId}`, {
                method: 'PUT',
                mode: 'cors',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: JSON.stringify({ name: newName })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                setSources(prev => prev.map(source => 
                    source.id === sourceId 
                        ? { ...source, name: newName }
                        : source
                ));
            } else {
                alert('Lỗi khi đổi tên: ' + (data.error || 'Không thể đổi tên tài liệu'));
            }
        } catch (err) {
            console.error('Error renaming source:', err);
            alert('Lỗi kết nối khi đổi tên: ' + err.message);
        }
    };

    const showRenameConfirmation = (source) => {
        setSourceToRename(source);
        setNewFileName(source.name);
        setShowRenamePopup(true);
        setActiveMenuId(null);
    };

    const confirmRename = async () => {
        if (sourceToRename && newFileName.trim() && newFileName !== sourceToRename.name) {
            await renameSource(sourceToRename.id, newFileName.trim());
            setSourceToRename(null);
            setNewFileName('');
            setShowRenamePopup(false);
        }
    };

    const cancelRename = () => {
        setSourceToRename(null);
        setNewFileName('');
        setShowRenamePopup(false);
    };

    const loadFileContent = async (source) => {
        try {
            const response = await fetch(`http://localhost:5000/api/sources/${source.id}/info`, {
                method: 'GET',
                mode: 'cors',
                headers: {
                    'Accept': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                setActiveDocument(source);
                // Tự động tăng độ rộng sidebar khi mở tài liệu
                setSidebarWidth(600);
                if (data.content_type === 'pdf') {
                    setActiveDocumentContent(`http://localhost:5000/api/sources/${source.id}/content#toolbar=0&navpanes=0&scrollbar=0`);
                } else {
                    setActiveDocumentContent(data.content || '');
                }
            } else {
                alert('Lỗi khi tải nội dung file: ' + (data.error || 'Không thể tải file'));
            }
        } catch (err) {
            console.error('Error loading file content:', err);
            alert('Lỗi kết nối khi tải file: ' + err.message);
        }
    };


    const toggleMenu = (sourceId) => {
        setActiveMenuId(activeMenuId === sourceId ? null : sourceId);
    };

    const closeMenu = () => {
        setActiveMenuId(null);
    };

    const showDeleteConfirmation = (source) => {
        setSourceToDelete(source);
        setShowDeletePopup(true);
        setActiveMenuId(null);
    };

    const confirmDelete = async () => {
        if (sourceToDelete) {
            await deleteSource(sourceToDelete.id);
            setSourceToDelete(null);
            setShowDeletePopup(false);
        }
    };

    const cancelDelete = () => {
        setSourceToDelete(null);
        setShowDeletePopup(false);
    };

    const handleMouseDown = React.useCallback((e) => {
        // Không cho phép resize khi sidebar bị thu gọn
        if (isSidebarCollapsed) return;
        console.log('Resize started, activeDocument:', !!activeDocument);
        setIsResizing(true);
        e.preventDefault();
        e.stopPropagation();
        // Thêm class để hiển thị visual feedback
        e.target.classList.add('resizing');
        // Thêm class body để cải thiện trải nghiệm
        document.body.classList.add('resizing');
    }, [isSidebarCollapsed, activeDocument]);

    const handleMouseMove = React.useCallback((e) => {
        if (!isResizing) return;
        
        const newWidth = e.clientX;
        // Điều chỉnh phạm vi resize dựa trên trạng thái xem tài liệu
        const minWidth = activeDocument ? 500 : 250;
        const maxWidth = activeDocument ? 1200 : 800;
        
        // Đảm bảo width trong phạm vi cho phép
        const clampedWidth = Math.max(minWidth, Math.min(newWidth, maxWidth));
        console.log('Resize move:', { newWidth, clampedWidth, minWidth, maxWidth, activeDocument: !!activeDocument });
        setSidebarWidth(clampedWidth);
    }, [isResizing, activeDocument]);

    const handleMouseUp = React.useCallback(() => {
        console.log('Resize ended');
        setIsResizing(false);
        // Xóa class visual feedback
        const resizeHandle = document.querySelector('.resize-handle');
        if (resizeHandle) {
            resizeHandle.classList.remove('resizing');
        }
        // Xóa class body
        document.body.classList.remove('resizing');
    }, []);

    const toggleSidebar = () => {
        if (activeDocument) {
            // Nếu đang xem tài liệu, đóng tài liệu và khôi phục sidebar
            setActiveDocument(null);
            setActiveDocumentContent('');
            setSidebarWidth(350);
        } else {
            // Nếu không xem tài liệu, toggle thu gọn sidebar
            setIsSidebarCollapsed(!isSidebarCollapsed);
            // Nếu đang thu gọn và có tài liệu đang mở, đóng tài liệu
            if (!isSidebarCollapsed && activeDocument) {
                setActiveDocument(null);
                setActiveDocumentContent('');
            }
            // Khôi phục độ rộng mặc định khi mở lại sidebar
            if (isSidebarCollapsed) {
                setSidebarWidth(350);
            }
        }
    };

    // Add event listeners for resize
    React.useEffect(() => {
        if (isResizing) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            
            return () => {
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
            };
        }
    }, [isResizing, handleMouseMove, handleMouseUp]);

    // Cleanup khi component unmount
    React.useEffect(() => {
        return () => {
            // Đảm bảo cleanup khi component unmount
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.classList.remove('resizing');
        };
    }, [handleMouseMove, handleMouseUp]);

    return (
        <div className="container">
            <div className="header">
                <div className="header-left">
                    <div className="logo">
                        <svg viewBox="0 0 24 24">
                            <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
                        </svg>
                    </div>
                    <div className="header-title">Raw2MD Agent - Document Processing</div>
                </div>
                <div className="header-right">
                    <span className="header-icon">
                        <svg viewBox="0 0 24 24">
                            <path d="M18,16.08C17.24,16.08 16.56,16.38 16.04,16.85L8.91,12.7C8.96,12.47 9,12.24 9,12C9,11.76 8.96,11.53 8.91,11.3L15.96,7.19C16.5,7.69 17.21,8 18,8A3,3 0 0,0 21,5A3,3 0 0,0 18,2A3,3 0 0,0 15,5C15,5.24 15.04,5.47 15.09,5.7L8.04,9.81C7.5,9.31 6.79,9 6,9A3,3 0 0,0 3,12A3,3 0 0,0 6,15C6.79,15 7.5,14.69 8.04,14.19L15.16,18.34C15.11,18.55 15.08,18.77 15.08,19C15.08,20.61 16.39,21.91 18,21.91C19.61,21.91 20.92,20.61 20.92,19A2.92,2.92 0 0,0 18,16.08Z" />
                        </svg>
                    </span>
                    <span className="header-icon">
                        <svg viewBox="0 0 24 24">
                            <path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.68 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z" />
                        </svg>
                    </span>
                    <span className="header-icon">
                        <svg viewBox="0 0 24 24">
                            <path d="M16,12A2,2 0 0,1 18,10A2,2 0 0,1 20,12A2,2 0 0,1 18,14A2,2 0 0,1 16,12M10,12A2,2 0 0,1 12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12M4,12A2,2 0 0,1 6,10A2,2 0 0,1 8,12A2,2 0 0,1 6,14A2,2 0 0,1 4,12Z" />
                        </svg>
                    </span>
                    <div className="user-avatar">
                        <svg viewBox="0 0 24 24">
                            <path d="M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z" />
                        </svg>
                    </div>
                </div>
            </div>
            
            <div className="main-content">
                {/* Sources Sidebar */}
                <div className={`sidebar ${activeDocument ? 'document-viewing' : ''} ${isSidebarCollapsed ? 'collapsed' : ''}`} style={{ width: isSidebarCollapsed ? '60px' : `${sidebarWidth}px` }}>
                    <div className="sidebar-header">
                        <span className="sidebar-icon">
                            <svg viewBox="0 0 24 24">
                                <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
                            </svg>
                        </span>
                        <span className="sidebar-title">
                            {activeDocument ? activeDocument.name : 'Nguồn'}
                        </span>
                    </div>
                    <div className="sidebar-content" 
                         onDragOver={handleDragOver}
                         onDragLeave={handleDragLeave}
                         onDrop={handleDrop}>
                        
                        {!activeDocument ? (
                            <>
                                <button 
                                    className="add-source-btn" 
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={isUploading}
                                >
                                    <span>
                                        <svg viewBox="0 0 24 24" width="16" height="16">
                                            <path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z" />
                                        </svg>
                                    </span>
                                    <span>{isUploading ? 'Đang upload...' : 'Thêm nguồn'}</span>
                                </button>
                                
                                {/* Icon + khi sidebar thu gọn */}
                                {isSidebarCollapsed && (
                                    <div className="add-source-icon" onClick={() => fileInputRef.current?.click()}>
                                        <svg viewBox="0 0 24 24">
                                            <path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z" />
                                        </svg>
                                    </div>
                                )}
                                
                                {/* Loading indicator khi đang upload */}
                                {isUploading && (
                                    <div className="upload-loading">
                                        <div className="upload-spinner"></div>
                                        <div className="upload-text">
                                            Đang upload... ({uploadProgress.current}/{uploadProgress.total})
                                        </div>
                                        <div className="upload-progress">
                                            <div 
                                                className="upload-progress-bar" 
                                                style={{ 
                                                    width: `${uploadProgress.total > 0 ? (uploadProgress.current / uploadProgress.total) * 100 : 0}%` 
                                                }}
                                            ></div>
                                        </div>
                                    </div>
                                )}

                                {/* Chỉ hiển thị "Chọn tất cả nguồn" khi có file */}
                                {sources.length > 0 && !isUploading && (
                                    <div className="select-all">
                                        <span className="select-all-text" onClick={selectAllSources}>Chọn tất cả nguồn</span>
                                        <input 
                                            type="checkbox" 
                                            id="select-all-checkbox"
                                            name="select-all-checkbox"
                                            className="select-all-checkbox"
                                            checked={sources.every(source => source.selected)}
                                            onChange={selectAllSources}
                                        />
                                    </div>
                                )}
                                
                                {sources.map(source => (
                                    <div key={source.id} className="source-item">
                                        <span className="source-icon" onClick={() => toggleMenu(source.id)}>
                                            <div className="file-icon">
                                                {getFileIcon(source.name)}
                                            </div>
                                            <div className="menu-icon">
                                                <svg viewBox="0 0 24 24">
                                                    <path d="M16,12A2,2 0 0,1 18,10A2,2 0 0,1 20,12A2,2 0 0,1 18,14A2,2 0 0,1 16,12M10,12A2,2 0 0,1 12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12M4,12A2,2 0 0,1 6,10A2,2 0 0,1 8,12A2,2 0 0,1 6,14A2,2 0 0,1 4,12Z" />
                                                </svg>
                                            </div>
                                        </span>
                                        <span className="source-name" onClick={() => loadFileContent(source)} style={{cursor: 'pointer'}}>{source.name}</span>
                                        <input 
                                            type="checkbox" 
                                            id={`source-checkbox-${source.id}`}
                                            name={`source-checkbox-${source.id}`}
                                            className="source-checkbox"
                                            checked={source.selected}
                                            onChange={() => toggleSourceSelection(source.id)}
                                        />
                                        
                                        <div className={`source-menu ${activeMenuId === source.id ? 'show' : ''}`}>
                                            <div 
                                                className="source-menu-item"
                                                onClick={() => showRenameConfirmation(source)}
                                            >
                                                <svg viewBox="0 0 24 24">
                                                    <path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z" />
                                                </svg>
                                                <span>Đổi tên nguồn</span>
                                            </div>
                                            <div 
                                                className="source-menu-item"
                                                onClick={() => showDeleteConfirmation(source)}
                                            >
                                                <svg viewBox="0 0 24 24">
                                                    <path d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z" />
                                                </svg>
                                                <span>Xóa nguồn</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </>
                        ) : (
                            /* Document Viewer in Sources */
                            <div className="sources-document-viewer">
                                <div className="document-viewer-content">
                                    {activeDocument.type === 'pdf' ? (
                                        <iframe src={activeDocumentContent} title={activeDocument.name} width="100%" height="100%" style={{ border: 'none' }}></iframe>
                                    ) : (
                                        <div dangerouslySetInnerHTML={{ __html: activeDocumentContent }}></div>
                                    )}
                                </div>
                            </div>
                        )}
                        
                        <input 
                            type="file" 
                            id="file-upload"
                            name="file-upload"
                            ref={fileInputRef}
                            style={{ display: 'none' }}
                            accept=".pdf,.docx,.html,.htm,.txt,.csv,.xml,.json,.jpg,.jpeg,.png,.tiff,.bmp,.webp,.md,.markdown"
                            multiple
                            onChange={(e) => {
                                const files = e.target.files;
                                console.log('=== FILE SELECTION EVENT ===');
                                console.log('Files selected:', files.length);
                                console.log('File names:', Array.from(files).map(f => f.name));
                                console.log('File sizes:', Array.from(files).map(f => f.size));
                                
                                // Reset input để có thể chọn lại cùng file
                                e.target.value = '';
                                
                                if (files.length === 1) {
                                    console.log('Using single file handler');
                                    handleFileSelect(files[0]);
                                } else if (files.length > 1) {
                                    console.log('Using multiple file handler');
                                    handleMultipleFileSelect(files);
                                } else {
                                    console.log('No files selected');
                                }
                            }}
                        />
                    </div>
                    <div className="resize-handle" onMouseDown={handleMouseDown}></div>
                    <button className={`sidebar-toggle ${activeDocument ? 'document-viewing' : ''}`} onClick={toggleSidebar}>
                        <svg viewBox="0 0 24 24" width="30" height="30">
                            {activeDocument ? (
                                // Icon X để đóng tài liệu
                                <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z" fill="currentColor"/>
                            ) : (
                                // Icon panel để thu gọn sidebar
                                <g>
                                    <rect x="2" y="2" width="20" height="20" rx="2" ry="2" fill="none" stroke="currentColor" stroke-width="2"/>
                                    <line x1="9" y1="4" x2="9" y2="20" stroke="currentColor" stroke-width="2"/>
                                </g>
                            )}
                        </svg>
                    </button>
                </div>

                {/* Metadata Area */}
                <div className="metadata-area">
                    <div className="metadata-header">
                        <span className="metadata-title">Metadata Blocks</span>
                        <div className="metadata-actions">
                            <button className="metadata-action-btn" onClick={loadMetadataBlocks}>
                                <span>
                                    <svg viewBox="0 0 24 24" width="16" height="16">
                                        <path d="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z" />
                                    </svg>
                                </span>
                                <span>Làm mới</span>
                            </button>
                            <button className="chat-action-btn">
                                <span>
                                    <svg viewBox="0 0 24 24" width="16" height="16">
                                        <path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.22,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.22,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.68 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z" />
                                    </svg>
                                </span>
                            </button>
                        </div>
                    </div>
                    
                    <div className="chat-content">
                        {messages.map(message => (
                            <div key={message.id}>
                                {message.type === 'user' ? (
                                    <div className="user-message">{message.content}</div>
                                ) : (
                                    <div className="ai-response">
                                        <div className="ai-response-text">{message.content}</div>
                                        <div className="response-actions">
                                            <span className="response-action" title="Lưu vào ghi chú">
                                                <svg viewBox="0 0 24 24" width="16" height="16">
                                                    <path d="M17,3H7A2,2 0 0,0 5,5V21L12,18L19,21V5C19,3.89 18.1,3 17,3Z" />
                                                </svg>
                                            </span>
                                            <span className="response-action" title="Copy">
                                                <svg viewBox="0 0 24 24" width="16" height="16">
                                                    <path d="M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z" />
                                                </svg>
                                            </span>
                                            <span className="response-action" title="Thích">
                                                <svg viewBox="0 0 24 24" width="16" height="16">
                                                    <path d="M23,10C23,8.89 22.1,8 21,8H14.68L15.64,3.43C15.66,3.33 15.67,3.22 15.67,3.11C15.67,2.7 15.5,2.32 15.23,2.05L14.17,1L7.59,7.58C7.22,7.95 7,8.45 7,9V19A2,2 0 0,0 9,21H18C18.83,21 19.54,20.5 19.84,19.78L22.86,12.73C22.95,12.5 23,12.26 23,12V10.08L23,10M1,21H5V9H1V21Z" />
                                                </svg>
                                            </span>
                                            <span className="response-action" title="Không thích">
                                                <svg viewBox="0 0 24 24" width="16" height="16">
                                                    <path d="M19,15H23V17H19M15,3H21V5H15M1,21H5V9H1M9,21H18C18.83,21 19.54,20.5 19.84,19.78L22.86,12.73C22.95,12.5 23,12.26 23,12V10.08L23,10C23,8.89 22.1,8 21,8H14.68L15.64,3.43C15.66,3.33 15.67,3.22 15.67,3.11C15.67,2.7 15.5,2.32 15.23,2.05L14.17,1L7.59,7.58C7.22,7.95 7,8.45 7,9V19A2,2 0 0,0 9,21Z" />
                                                </svg>
                                            </span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                        {loading && (
                            <div className="ai-response">
                                <div className="ai-response-text">Đang xử lý...</div>
                            </div>
                        )}
                    </div>
                    
                    <div className="chat-input-area">
                        <div className="chat-input">
                            <input 
                                type="text" 
                                id="chat-input"
                                name="chat-input"
                                placeholder="Bắt đầu nhập..."
                                value={inputMessage}
                                onChange={(e) => setInputMessage(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                            />
                            <span className="chat-send-btn" onClick={handleSendMessage}>
                                <svg viewBox="0 0 24 24" width="16" height="16">
                                    <path d="M2,21L23,12L2,3V10L17,12L2,14V21Z" />
                                </svg>
                            </span>
                        </div>
                        <div className="suggested-prompts">
                            <button className="prompt-btn" onClick={() => handlePromptClick("Văn bản quy định những gì?")}>
                                Văn bản quy định những gì?
                            </button>
                            <button className="prompt-btn" onClick={() => handlePromptClick("Quy định áp dụng cho những ai?")}>
                                Quy định áp dụng cho những ai?
                            </button>
                            <button className="prompt-btn" onClick={() => handlePromptClick("Tài liệu giảng dạy bắt buộc gồm gì?")}>
                                Tài liệu giảng dạy bắt buộc gồm gì?
                            </button>
                        </div>
                    </div>
                    
                    <div className="chat-footer">
                        Raw2MD Agent có thể đưa ra thông tin không chính xác; hãy kiểm tra kỹ câu trả lời mà bạn nhận được.
                    </div>
                </div>

                {/* Studio Sidebar */}
                <div className="studio-sidebar">
                    <div className="sidebar-header">
                        <span className="sidebar-icon">
                            <svg viewBox="0 0 24 24">
                                <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
                            </svg>
                        </span>
                        <span className="sidebar-title">Studio</span>
                    </div>
                    <div className="sidebar-content">
                        <div className="studio-cards">
                            <div className="studio-card audio">
                                <div className="studio-card-icon">
                                    <svg viewBox="0 0 24 24">
                                        <path d="M12,3V13.55C11.41,13.21 10.73,13 10,13A4,4 0 0,0 6,17A4,4 0 0,0 10,21A4,4 0 0,0 14,17V7H18V3H12Z" />
                                    </svg>
                                </div>
                                <div className="studio-card-title">Tổng quan bằng âm thanh</div>
                                <div className="studio-card-edit">
                                    <svg viewBox="0 0 24 24" width="12" height="12">
                                        <path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z" />
                                    </svg>
                                </div>
                            </div>
                            <div className="studio-card video">
                                <div className="studio-card-icon">
                                    <svg viewBox="0 0 24 24">
                                        <path d="M17,10.5V7A1,1 0 0,0 16,6H4A1,1 0 0,0 3,7V17A1,1 0 0,0 4,18H16A1,1 0 0,0 17,17V13.5L21,17.5V6.5L17,10.5Z" />
                                    </svg>
                                </div>
                                <div className="studio-card-title">Tổng quan bằng video</div>
                                <div className="studio-card-edit">
                                    <svg viewBox="0 0 24 24" width="12" height="12">
                                        <path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z" />
                                    </svg>
                                </div>
                            </div>
                            <div className="studio-card mindmap">
                                <div className="studio-card-icon">
                                    <svg viewBox="0 0 24 24">
                                        <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z" />
                                    </svg>
                                </div>
                                <div className="studio-card-title">Bản đồ tư duy</div>
                                <div className="studio-card-edit">
                                    <svg viewBox="0 0 24 24" width="12" height="12">
                                        <path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z" />
                                    </svg>
                                </div>
                            </div>
                            <div className="studio-card report">
                                <div className="studio-card-icon">
                                    <svg viewBox="0 0 24 24">
                                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
                                    </svg>
                                </div>
                                <div className="studio-card-title">Báo cáo</div>
                                <div className="studio-card-edit">
                                    <svg viewBox="0 0 24 24" width="12" height="12">
                                        <path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z" />
                                    </svg>
                                </div>
                            </div>
                            <div className="studio-card flashcards">
                                <div className="studio-card-icon">
                                    <svg viewBox="0 0 24 24">
                                        <path d="M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3M19,5V19H5V5H19Z" />
                                    </svg>
                                </div>
                                <div className="studio-card-title">Thẻ ghi nhớ</div>
                                <div className="studio-card-edit">
                                    <svg viewBox="0 0 24 24" width="12" height="12">
                                        <path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z" />
                                    </svg>
                                </div>
                            </div>
                            <div className="studio-card quiz">
                                <div className="studio-card-icon">
                                    <svg viewBox="0 0 24 24">
                                        <path d="M11,18H13V16H11V18M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,6A4,4 0 0,0 8,10H10A2,2 0 0,1 12,8A2,2 0 0,1 14,10C14,12 11,11.75 11,15H13C13,12.75 16,12.5 16,10A4,4 0 0,0 12,6Z" />
                                    </svg>
                                </div>
                                <div className="studio-card-title">Bài kiểm tra</div>
                                <div className="studio-card-edit">
                                    <svg viewBox="0 0 24 24" width="12" height="12">
                                        <path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z" />
                                    </svg>
                                </div>
                            </div>
                        </div>
                        
                        <div className="studio-magic">
                            <span className="studio-magic-icon">
                                <svg viewBox="0 0 24 24">
                                    <path d="M7.5,5.6L5,7L6.4,4.5L5,2L7.5,3.4L10,2L8.6,4.5L10,7L7.5,5.6M19.5,15.4L22,14L20.6,16.5L22,19L19.5,17.6L17,19L18.4,16.5L17,14L19.5,15.4M22,2L20.6,4.5L22,7L19.5,5.6L17,7L18.4,4.5L17,2L19.5,3.4L22,2M13.34,12.78L15.78,10.34L13.66,8.22L11.22,10.66L13.34,12.78M14.37,7.29L16.71,9.63C17.1,10 17.1,10.65 16.71,11.04L5.04,22.71C4.65,23.1 4,23.1 3.61,22.71L1.29,20.39C0.9,20 0.9,19.35 1.29,18.96L12.96,7.29C13.35,6.9 14,6.9 14.37,7.29Z" />
                                </svg>
                            </span>
                            <span>Đầu ra của Studio sẽ được lưu ở đây.</span>
                        </div>
                        
                        <div className="studio-description">
                            Sau khi thêm nguồn, hãy nhấp để thêm Tổng quan bằng âm thanh, Hướng dẫn học tập, Bản đồ tư duy và nhiều thông tin khác!
                        </div>
                        
                        <button className="add-note-btn">
                            <span>
                                <svg viewBox="0 0 24 24" width="16" height="16">
                                    <path d="M17,3H7A2,2 0 0,0 5,5V21L12,18L19,21V5C19,3.89 18.1,3 17,3Z" />
                                </svg>
                            </span>
                            <span>Thêm ghi chú</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* Delete Confirmation Popup */}
            {showDeletePopup && (
                <div className={`popup-overlay ${showDeletePopup ? 'show' : ''}`}>
                    <div className="popup-container">
                        <div className="popup-title">
                            Xoá {sourceToDelete?.name}?
                        </div>
                        <div className="popup-actions">
                            <button className="popup-btn popup-btn-cancel" onClick={cancelDelete}>
                                Hủy
                            </button>
                            <button className="popup-btn popup-btn-delete" onClick={confirmDelete}>
                                Xoá
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Rename Confirmation Popup */}
            {showRenamePopup && (
                <div className={`popup-overlay ${showRenamePopup ? 'show' : ''}`}>
                    <div className="popup-container">
                        <div className="popup-title">
                            Đổi tên {sourceToRename?.name}?
                        </div>
                        <input 
                            type="text" 
                            id="rename-input"
                            name="rename-input"
                            className="popup-input"
                            value={newFileName}
                            onChange={(e) => setNewFileName(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && confirmRename()}
                            autoFocus
                        />
                        <div className="popup-actions">
                            <button className="popup-btn popup-btn-cancel" onClick={cancelRename}>
                                Hủy
                            </button>
                            <button className="popup-btn popup-btn-delete" onClick={confirmRename}>
                                Đổi tên
                            </button>
                        </div>
                    </div>
                </div>
            )}

        </div>
    );
}

// Use React 18 createRoot API
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
