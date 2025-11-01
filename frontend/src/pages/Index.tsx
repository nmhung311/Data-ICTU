import { useEffect, useState, useRef, useCallback } from "react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import SourcesColumn from "@/components/SourcesColumn";
import ConversationColumn from "@/components/ConversationColumn";
import StudioColumn from "@/components/StudioColumn";
import MobileColumnTabs from "@/components/MobileColumnTabs";
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from "@/components/ui/resizable";
import { ImperativePanelHandle } from "react-resizable-panels";

const STORAGE_KEY = "notebook_layout_v1";

const getDefaultLayout = () => {
  const width = window.innerWidth;
  if (width >= 1440) return [24, 48, 28]; // lg+
  if (width >= 1024) return [24, 48, 28]; // md
  if (width >= 640) return [26, 48, 26];  // sm
  return [24, 48, 28]; // fallback
};

const getMinMaxSizes = () => {
  const width = window.innerWidth;
  if (width >= 1920) {
    // xl: ultrawide
    return {
      left: { min: 15, max: 40 },
      center: { min: 30, max: 72 },
      right: { min: 18, max: 40 }
    };
  } else if (width >= 1440) {
    // lg: 24-27"
    return {
      left: { min: 15, max: 40 },
      center: { min: 30, max: 80 },
      right: { min: 18, max: 40 }
    };
  } else if (width >= 1024) {
    // md: 14-15" laptop
    return {
      left: { min: 15, max: 40 },
      center: { min: 30, max: 75 },
      right: { min: 18, max: 40 }
    };
  } else if (width >= 640) {
    // sm: tablet
    return {
      left: { min: 20, max: 35 },
      center: { min: 35, max: 70 },
      right: { min: 20, max: 35 }
    };
  }
  return {
    left: { min: 15, max: 40 },
    center: { min: 30, max: 75 },
    right: { min: 18, max: 40 }
  };
};

interface Source {
  id: string;
  name: string;
  type: string;
  size: number;
  file?: File;
  filepath?: string; // Đường dẫn file trên backend
  documentId?: string; // ID từ database
  markdown?: string; // Nội dung markdown đã trích xuất
}

const API_BASE_URL = 'http://localhost:5000/api';

const Index = () => {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 640);
  const [layout, setLayout] = useState<number[]>(getDefaultLayout());
  const [sources, setSources] = useState<Source[]>([]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  // Track upload progress và status cho từng file theo source.id
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [uploadStatus, setUploadStatus] = useState<Record<string, 'idle' | 'uploading' | 'success'>>({});
  // Track extract status và progress cho từng file theo source.id
  const [extractStatus, setExtractStatus] = useState<Record<string, 'idle' | 'extracting' | 'success'>>({});
  const [extractProgress, setExtractProgress] = useState<Record<string, number>>({});
  const minMaxSizes = getMinMaxSizes();
  const editLastMessageRef = useRef<(() => void) | null>(null);
  const leftPanelRef = useRef<ImperativePanelHandle>(null);

  const addSource = async (file: File) => {
    // Tạo source tạm
    const tempId = Date.now().toString() + Math.random().toString(36).substr(2, 9);
    const newSource: Source = {
      id: tempId,
      name: file.name,
      type: file.type || "application/octet-stream",
      size: file.size,
      file: file,
    };
    
    // Thêm vào danh sách ngay (optimistic update)
    setSources((prev) => [...prev, newSource]);

    // Upload file lên backend (hỗ trợ PDF, TXT, DOCX, MD, v.v.)
    const allowedExtensions = ['.pdf', '.txt', '.docx', '.doc', '.md', '.markdown'];
    const fileExt = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    if (allowedExtensions.includes(fileExt)) {
      try {
        const formData = new FormData();
        formData.append('file', file);

        // Bắt đầu upload cho file này
        setUploadProgress((prev) => ({ ...prev, [tempId]: 0 }));
        setUploadStatus((prev) => ({ ...prev, [tempId]: 'uploading' }));

        // Sử dụng XMLHttpRequest để track progress
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            setUploadProgress((prev) => ({ ...prev, [tempId]: Math.round(percentComplete) }));
          }
        });

        xhr.addEventListener('load', () => {
          if (xhr.status === 200) {
            const data = JSON.parse(xhr.responseText);
            const documentId = data.document_id;
            
            // Cập nhật source với filepath và documentId
            // Thay đổi id từ tempId sang document_id để đồng nhất với DB
            setSources((prev) =>
              prev.map((source) =>
                source.id === tempId
                  ? { 
                      ...source, 
                      id: documentId, // Đổi id sang document_id để đồng nhất
                      filepath: data.filepath, 
                      documentId: documentId 
                    }
                  : source
              )
            );
            // Cập nhật upload status với document_id mới
            setUploadStatus((prev) => {
              const newStatus = { ...prev };
              delete newStatus[tempId]; // Xóa status cũ
              newStatus[documentId] = 'success'; // Set status mới
              return newStatus;
            });
            setUploadProgress((prev) => {
              const newProgress = { ...prev };
              delete newProgress[tempId]; // Xóa progress cũ
              newProgress[documentId] = 100; // Set progress mới
              return newProgress;
            });
            
            // Tự động hiển thị metadata nếu đã được tạo (cho TẤT CẢ file types)
            if (data.metadata) {
              console.log('📝 Đã tự động tạo metadata, đang hiển thị...');
              // Tự động chọn file này
              setSelectedSourceIds([documentId]);
              // Set metadata để hiển thị
              setMetadataContent(data.metadata);
            } else {
              // Nếu chưa có metadata, vẫn chọn file nhưng không hiển thị gì
              // Có thể do metadata đang được tạo hoặc có lỗi
              console.log('⚠️ Chưa có metadata, có thể đang được tạo...');
              setSelectedSourceIds([documentId]);
              // Thử load lại từ database sau 2 giây (metadata có thể đang được tạo async)
              setTimeout(() => {
                fetch(`${API_BASE_URL}/documents/${documentId}`)
                  .then((res) => res.json())
                  .then((docData) => {
                    if (docData.document?.metadata) {
                      setMetadataContent(docData.document.metadata);
                      console.log('✅ Đã load metadata từ database');
                    }
                  })
                  .catch((err) => console.error('Lỗi khi load metadata:', err));
              }, 2000);
            }
            
            // Giữ nguyên trạng thái success để người dùng biết đã hoàn thành
          } else {
            console.error('Lỗi upload file:', xhr.responseText);
            setUploadStatus((prev) => ({ ...prev, [tempId]: 'idle' }));
            setUploadProgress((prev) => ({ ...prev, [tempId]: 0 }));
          }
        });

        xhr.addEventListener('error', () => {
          console.error('Lỗi khi upload file');
          setUploadStatus((prev) => ({ ...prev, [tempId]: 'idle' }));
          setUploadProgress((prev) => ({ ...prev, [tempId]: 0 }));
        });

        xhr.open('POST', `${API_BASE_URL}/upload-pdf`);
        xhr.send(formData);
      } catch (error) {
        console.error('Lỗi khi upload file:', error);
        setUploadStatus((prev) => ({ ...prev, [tempId]: 'idle' }));
        setUploadProgress((prev) => ({ ...prev, [tempId]: 0 }));
      }
    }
  };

  const handleRename = (id: string, newName: string) => {
    setSources((prev) =>
      prev.map((source) => (source.id === id ? { ...source, name: newName } : source))
    );
  };

  const handleDelete = async (id: string) => {
    // Tìm source cần xóa để lấy documentId
    const sourceToDelete = sources.find(s => s.id === id);
    
    if (!sourceToDelete) {
      console.warn(`Không tìm thấy source với id: ${id}`);
      return;
    }
    
    // Nếu file đang được chọn, xóa khỏi selected và xóa documentContent
    if (selectedSourceIds.includes(id)) {
      setSelectedSourceIds([]);
      setCurrentDocumentContent(null);
    }
    
    // Xóa khỏi database TRƯỚC (để đảm bảo DB được cập nhật)
    let deleteSuccess = false;
    if (sourceToDelete.documentId) {
      try {
        const response = await fetch(`${API_BASE_URL}/documents/${sourceToDelete.documentId}`, {
          method: 'DELETE',
        });
        
        if (response.ok) {
          try {
            const data = await response.json();
            deleteSuccess = data.success === true;
            if (deleteSuccess) {
              console.log(`✅ Đã xóa document ${sourceToDelete.documentId} khỏi database và file OCR`);
            } else {
              console.error('Lỗi khi xóa document khỏi DB:', data.error || data.message);
            }
          } catch (jsonError) {
            // Nếu response không phải JSON, nhưng status code là 200, coi như thành công
            console.warn('Response không phải JSON, nhưng status code là 200:', jsonError);
            deleteSuccess = true;
          }
        } else {
          const errorText = await response.text();
          console.error('Lỗi khi xóa document khỏi DB:', response.status, errorText);
          deleteSuccess = false;
        }
      } catch (error) {
        console.error('Lỗi khi xóa document khỏi DB:', error);
        deleteSuccess = false;
      }
    } else {
      // Nếu không có documentId, vẫn cho phép xóa (file đang upload chưa có documentId)
      deleteSuccess = true;
    }
    
    // Chỉ xóa khỏi state nếu xóa từ DB thành công HOẶC không có documentId
    if (deleteSuccess || !sourceToDelete.documentId) {
      // Xóa source khỏi state - sử dụng functional update để đảm bảo lấy state mới nhất
      setSources((prev) => {
        const filtered = prev.filter((source) => source.id !== id);
        console.log(`🗑️ Đã xóa file ${id} khỏi state. Trước: ${prev.length}, Sau: ${filtered.length}`);
        return filtered;
      });
      
      // Xóa upload/extract status và progress
      setUploadStatus((prev) => {
        const newStatus = { ...prev };
        delete newStatus[id];
        return newStatus;
      });
      setUploadProgress((prev) => {
        const newProgress = { ...prev };
        delete newProgress[id];
        return newProgress;
      });
      setExtractStatus((prev) => {
        const newStatus = { ...prev };
        delete newStatus[id];
        return newStatus;
      });
      setExtractProgress((prev) => {
        const newProgress = { ...prev };
        delete newProgress[id];
        return newProgress;
      });
    } else {
      console.error('❌ Không thể xóa file khỏi UI vì xóa khỏi DB thất bại');
      // Có thể thêm thông báo lỗi cho người dùng ở đây
    }
  };

  const [currentDocumentContent, setCurrentDocumentContent] = useState<string | null>(null);
  const [metadataContent, setMetadataContent] = useState<string | null>(null);
  const [isGeneratingMetadata, setIsGeneratingMetadata] = useState(false);

  const handleGenerateMetadata = async () => {
    // Lấy document được chọn
    if (selectedSourceIds.length === 0) {
      console.warn('Chưa chọn document để tạo metadata');
      return;
    }

    const selectedSource = sources.find(s => s.id === selectedSourceIds[0]);
    // Sử dụng id (document_id) nếu documentId không có
    const docIdToUse = selectedSource?.documentId || selectedSource?.id;
    
    if (!docIdToUse) {
      console.warn('Document không có documentId hoặc id, chưa được lưu vào database');
      return;
    }

    setIsGeneratingMetadata(true);
    try {
      // Lấy OCR text từ database (đã được người dùng chỉnh sửa lỗi encoding)
      const response = await fetch(`${API_BASE_URL}/generate-metadata`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: docIdToUse, // Truyền document_id để lấy OCR text từ DB
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.metadata) {
          setMetadataContent(data.metadata);
          console.log('✅ Đã tạo metadata thành công từ OCR text trong database');
        } else {
          console.error('Lỗi khi tạo metadata:', data.error);
        }
      } else {
        const errorText = await response.text();
        console.error('Lỗi khi tạo metadata:', errorText);
      }
    } catch (error) {
      console.error('Lỗi khi tạo metadata:', error);
    } finally {
      setIsGeneratingMetadata(false);
    }
  };

  const handleSelect = useCallback(async (ids: string[]) => {
    // Kiểm tra xem selection có thay đổi không
    const prevIds = selectedSourceIds;
    const selectionChanged = !(prevIds.length === ids.length && prevIds[0] === ids[0]);
    
    // Chỉ xử lý nếu selection thực sự thay đổi
    setSelectedSourceIds((prevIds) => {
      // So sánh với previous state để tránh re-render không cần thiết
      if (prevIds.length === ids.length && prevIds[0] === ids[0]) {
        // Selection không thay đổi, không cần làm gì
        return prevIds;
      }
      return ids;
    });

    // Chỉ tiếp tục nếu selection thực sự thay đổi
    if (ids.length === 0) {
      setMetadataContent(null); // Xóa metadata khi không có file nào được chọn
      return;
    }
    
    // Chỉ xóa metadata khi chọn file KHÁC (không phải cùng file)
    if (selectionChanged) {
      setMetadataContent(null);
    }

    console.log("Selected sources:", ids);
    
    // Nếu có source được chọn, load metadata từ DB
    const selectedSource = sources.find(s => s.id === ids[0]);
    console.log('🔍 Selected source:', { 
      id: selectedSource?.id, 
      documentId: selectedSource?.documentId,
      name: selectedSource?.name 
    });
    
    // Sử dụng id (document_id) nếu documentId không có
    const docIdToFetch = selectedSource?.documentId || selectedSource?.id;
    
    if (docIdToFetch) {
      console.log(`🔄 Đang load metadata cho document: ${docIdToFetch}`);
      try {
        const response = await fetch(`${API_BASE_URL}/documents/${docIdToFetch}`);
        if (response.ok) {
          const data = await response.json();
          console.log('📄 Document data:', { 
            hasMetadata: !!data.document?.metadata, 
            metadataLength: data.document?.metadata?.length 
          });
          
          // Chỉ load metadata (bản đã chia nhỏ), không load ocr_text nữa
          if (data.document?.metadata) {
            console.log('✅ Đã load metadata thành công');
            setMetadataContent(data.document.metadata);
          } else {
            console.warn('⚠️ Document không có metadata, có thể đang được tạo...');
            setMetadataContent(null);
            // Thử lại sau 3 giây nếu chưa có metadata
            setTimeout(() => {
              fetch(`${API_BASE_URL}/documents/${docIdToFetch}`)
                .then((res) => res.json())
                .then((retryData) => {
                  if (retryData.document?.metadata) {
                    console.log('✅ Đã load metadata sau retry');
                    setMetadataContent(retryData.document.metadata);
                  } else {
                    console.warn('⚠️ Vẫn chưa có metadata sau retry');
                  }
                })
                .catch((err) => console.error('Lỗi khi retry load metadata:', err));
            }, 3000);
          }
          // Không set documentContent nữa
          setCurrentDocumentContent(null);
        } else {
          const errorText = await response.text();
          console.error('❌ Lỗi khi lấy document:', errorText);
          setMetadataContent(null);
          setCurrentDocumentContent(null);
        }
      } catch (error) {
        console.error('❌ Lỗi khi load document:', error);
        setMetadataContent(null);
        setCurrentDocumentContent(null);
      }
    } else {
      console.log('⚠️ Không có documentId hoặc id cho source được chọn:', {
        sourceId: selectedSource?.id,
        documentId: selectedSource?.documentId,
        source: selectedSource
      });
      setMetadataContent(null);
      setCurrentDocumentContent(null);
    }
  }, [sources]);

  const handleSendQuestion = async (question: string, filepath: string): Promise<string> => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          filepath: filepath,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        // Ưu tiên answer vì nó có message prefix và format đầy đủ
        // Nếu answer không có, mới dùng markdown, sau đó fallback
        return data.answer || data.markdown || "Không có nội dung trả về";
      } else {
        const error = await response.json();
        throw new Error(error.error || 'Lỗi khi gửi câu hỏi');
      }
    } catch (error) {
      console.error('Lỗi API:', error);
      throw error;
    }
  };

  // Load lại danh sách sources từ DB khi component mount
  useEffect(() => {
    const loadSourcesFromDB = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/documents`);
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.documents && data.documents.length > 0) {
            // Convert documents từ DB thành Source format
            const loadedSources: Source[] = data.documents.map((doc: any) => ({
              id: doc.document_id, // Sử dụng document_id làm id
              name: doc.filename,
              type: 'application/pdf', // Mặc định là PDF
              size: 0, // Không có size trong DB
              filepath: doc.filepath,
              documentId: doc.document_id,
            }));
            
            // Merge với sources hiện tại (giữ lại các file đang upload chưa có trong DB)
            setSources((prevSources) => {
              // Lấy danh sách IDs từ DB
              const dbIds = new Set(loadedSources.map(s => s.id));
              
              // Giữ lại các source chưa có trong DB (đang upload)
              const sourcesNotInDB = prevSources.filter(s => !s.documentId || !dbIds.has(s.id));
              
              // Merge: sources từ DB + sources đang upload
              const merged = [...loadedSources, ...sourcesNotInDB];
              
              console.log(`📥 Load từ DB: ${loadedSources.length} files. Tổng sau merge: ${merged.length} files`);
              return merged;
            });
            // Set upload status là success cho các file đã có trong DB
            const statusUpdates: Record<string, 'success'> = {};
            const progressUpdates: Record<string, number> = {};
            loadedSources.forEach((source) => {
              statusUpdates[source.id] = 'success';
              progressUpdates[source.id] = 100;
            });
            setUploadStatus(statusUpdates);
            setUploadProgress(progressUpdates);
            console.log(`✅ Đã load ${loadedSources.length} file từ database`);
          } else {
            console.log('📭 Chưa có file nào trong database');
          }
        } else {
          console.error('Lỗi khi load documents:', await response.text());
        }
      } catch (error) {
        console.error('Lỗi khi load documents từ DB:', error);
      }
    };

    loadSourcesFromDB();
  }, []); // Chỉ chạy 1 lần khi component mount

  useEffect(() => {
    const savedLayout = localStorage.getItem(STORAGE_KEY);
    if (savedLayout && !isMobile) {
      try {
        const parsed = JSON.parse(savedLayout);
        setLayout(parsed);
      } catch (e) {
        console.error("Failed to parse saved layout");
      }
    }

    const handleResize = () => {
      const mobile = window.innerWidth < 640;
      setIsMobile(mobile);
      if (!mobile && savedLayout) {
        try {
          const parsed = JSON.parse(savedLayout);
          setLayout(parsed);
        } catch (e) {
          setLayout(getDefaultLayout());
        }
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const handleLayoutChange = (sizes: number[]) => {
    // Chỉ update nếu sizes khác với layout hiện tại (tránh loop)
    if (JSON.stringify(sizes) !== JSON.stringify(layout)) {
      setLayout(sizes);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sizes));
    }
  };

  const handleDoubleClick = () => {
    const defaultLayout = getDefaultLayout();
    setLayout(defaultLayout);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(defaultLayout));
  };

  // Expand Sources panel đến max size
  const expandSourcesPanel = () => {
    const maxLeftSize = minMaxSizes.left.max;
    
    // Resize panel trực tiếp bằng API
    if (leftPanelRef.current) {
      leftPanelRef.current.resize(maxLeftSize);
    } else {
      // Fallback: update layout state nếu ref chưa sẵn sàng
      setLayout((currentLayout) => {
        const newLayout = [...currentLayout];
        newLayout[0] = maxLeftSize;
        
        const remaining = 100 - maxLeftSize;
        const currentCenter = currentLayout[1];
        const currentRight = currentLayout[2];
        const totalOthers = currentCenter + currentRight;
        
        if (totalOthers > 0) {
          newLayout[1] = (currentCenter / totalOthers) * remaining;
          newLayout[2] = (currentRight / totalOthers) * remaining;
        } else {
          newLayout[1] = remaining / 2;
          newLayout[2] = remaining / 2;
        }
        
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newLayout));
        return newLayout;
      });
    }
  };

  return (
    <div className="h-dvh flex flex-col overflow-hidden">
      <Header 
        uploadProgress={uploadProgress} 
        uploadStatus={uploadStatus}
        extractStatus={extractStatus}
        extractProgress={extractProgress}
        sources={sources}
        selectedSourceIds={selectedSourceIds}
      />
      
      <main className="flex-1 overflow-hidden p-3 sm:p-4 md:p-6">
        {isMobile ? (
          <div className="h-full">
            <MobileColumnTabs />
          </div>
        ) : (
          <div className="h-full max-w-[1920px] mx-auto">
            <ResizablePanelGroup
              direction="horizontal"
              onLayout={handleLayoutChange}
              className="h-full rounded-lg"
            >
              <ResizablePanel
                ref={leftPanelRef}
                defaultSize={layout[0]}
                minSize={minMaxSizes.left.min}
                maxSize={minMaxSizes.left.max}
                className="bg-card rounded-l-lg border border-border shadow-sm overflow-hidden flex flex-col"
                aria-label="Cột nguồn"
              >
                <div className="p-4 h-full overflow-auto">
                  <SourcesColumn 
                    sources={sources}
                    uploadProgress={uploadProgress}
                    uploadStatus={uploadStatus}
                    onAddSource={addSource}
                    onRename={handleRename}
                    onDelete={handleDelete}
                    onSelect={handleSelect}
                    onExpandPanel={expandSourcesPanel}
                  />
                </div>
              </ResizablePanel>

              <ResizableHandle
                onDoubleClick={handleDoubleClick}
                withHandle
                className="mx-1 sm:mx-2 hover:bg-[#94A3B8] transition-colors group w-[10px] cursor-col-resize"
                aria-label="Thanh kéo trái - Double-click để reset, dùng phím mũi tên để điều chỉnh"
                tabIndex={0}
              />

              <ResizablePanel
                defaultSize={layout[1]}
                minSize={minMaxSizes.center.min}
                maxSize={minMaxSizes.center.max}
                className="bg-card border-y border-border shadow-sm overflow-hidden flex flex-col"
                aria-label="Cột cuộc trò chuyện"
              >
                <div className="p-4 h-full overflow-auto">
                  <ConversationColumn 
                    onAddSource={addSource} 
                    sourcesCount={sources.length}
                    sources={sources}
                    selectedSourceIds={selectedSourceIds}
                    documentContent={currentDocumentContent}
                    metadataContent={metadataContent}
                    isGeneratingMetadata={isGeneratingMetadata}
                    onSendQuestion={handleSendQuestion}
                    onTriggerEdit={(trigger) => {
                      editLastMessageRef.current = trigger;
                    }}
                  />
                </div>
              </ResizablePanel>

              <ResizableHandle
                onDoubleClick={handleDoubleClick}
                withHandle
                className="mx-1 sm:mx-2 hover:bg-[#94A3B8] transition-colors group w-[10px] cursor-col-resize"
                aria-label="Thanh kéo phải - Double-click để reset, dùng phím mũi tên để điều chỉnh"
                tabIndex={0}
              />

              <ResizablePanel
                defaultSize={layout[2]}
                minSize={minMaxSizes.right.min}
                maxSize={minMaxSizes.right.max}
                className="bg-card rounded-r-lg border border-border shadow-sm overflow-hidden flex flex-col"
                aria-label="Cột studio"
              >
                <div className="p-4 h-full overflow-auto">
                  <StudioColumn 
                    sources={sources}
                    selectedSourceIds={selectedSourceIds}
                    uploadStatus={uploadStatus}
                    extractStatus={extractStatus}
                    extractProgress={extractProgress}
                    onExtractStart={(sourceId) => {
                      setExtractStatus((prev) => ({ ...prev, [sourceId]: 'extracting' }));
                      setExtractProgress((prev) => ({ ...prev, [sourceId]: 0 }));
                    }}
                    onExtractProgress={(sourceId, progress) => {
                      setExtractProgress((prev) => ({ ...prev, [sourceId]: progress }));
                    }}
                    onExtractComplete={(sourceId, markdown) => {
                      setSources((prev) =>
                        prev.map((source) =>
                          source.id === sourceId
                            ? { ...source, markdown: markdown }
                            : source
                        )
                      );
                      setExtractStatus((prev) => ({ ...prev, [sourceId]: 'success' }));
                      setExtractProgress((prev) => ({ ...prev, [sourceId]: 100 }));
                    }}
                    onExtractError={(sourceId) => {
                      setExtractStatus((prev) => ({ ...prev, [sourceId]: 'idle' }));
                      setExtractProgress((prev) => ({ ...prev, [sourceId]: 0 }));
                    }}
                    onEditClick={handleGenerateMetadata}
                  />
                </div>
              </ResizablePanel>
            </ResizablePanelGroup>
          </div>
        )}
      </main>
      
      <Footer />
    </div>
  );
};

export default Index;

