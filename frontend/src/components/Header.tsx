import { Waves } from "lucide-react";
import WorkflowStepper from "./WorkflowStepper";

interface Source {
  id: string;
  documentId?: string;
}

interface HeaderProps {
  uploadProgress?: Record<string, number>;
  uploadStatus?: Record<string, 'idle' | 'uploading' | 'success'>;
  extractStatus?: Record<string, 'idle' | 'extracting' | 'success'>;
  extractProgress?: Record<string, number>;
  sources?: Source[];
  selectedSourceIds?: string[];
}

const Header = ({ uploadProgress = {}, uploadStatus = {}, extractStatus = {}, extractProgress = {}, sources = [], selectedSourceIds = [] }: HeaderProps) => {
  // Lấy trạng thái của file đang được chọn
  const getSelectedFileStatus = () => {
    // Nếu có file được chọn, hiển thị trạng thái của file đó
    if (selectedSourceIds.length > 0) {
      const selectedSource = sources.find(s => s.id === selectedSourceIds[0]);
      if (selectedSource) {
        return {
          uploadProgress: uploadProgress[selectedSource.id] || 0,
          uploadStatus: uploadStatus[selectedSource.id] || 'idle',
          extractStatus: extractStatus[selectedSource.id] || 'idle',
          extractProgress: extractProgress[selectedSource.id] || 0
        };
      }
    }
    
    // Nếu không có file nào được chọn, lấy file mới nhất đang upload
    const uploadingFiles = sources.filter(s => uploadStatus[s.id] === 'uploading');
    if (uploadingFiles.length > 0) {
      const latest = uploadingFiles[uploadingFiles.length - 1];
        return {
          uploadProgress: uploadProgress[latest.id] || 0,
          uploadStatus: uploadStatus[latest.id] || 'idle',
          extractStatus: extractStatus[latest.id] || 'idle',
          extractProgress: extractProgress[latest.id] || 0
        };
    }
    
    // Nếu không có file nào đang upload, lấy file mới nhất có status success
    const successFiles = sources.filter(s => uploadStatus[s.id] === 'success');
    if (successFiles.length > 0) {
      const latest = successFiles[successFiles.length - 1];
        return {
          uploadProgress: uploadProgress[latest.id] || 100,
          uploadStatus: uploadStatus[latest.id] || 'success',
          extractStatus: extractStatus[latest.id] || 'idle',
          extractProgress: extractProgress[latest.id] || 0
        };
    }
    
    // Mặc định: idle
    return { uploadProgress: 0, uploadStatus: 'idle' as const, extractStatus: 'idle' as const, extractProgress: 0 };
  };

  const selectedFileStatus = getSelectedFileStatus();
  return (
    <header className="bg-header border-b border-border sticky top-0 z-50 mt-2">
      <div className="h-[60px] px-4 sm:px-6 flex items-center">
        <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
          <h1 className="text-sm sm:text-base font-medium text-foreground truncate">Hệ thống cập nhật tri thức cho AI ICTU</h1>
        </div>
        
        <div className="hidden sm:flex flex-1 justify-center">
          <WorkflowStepper 
            uploadProgress={selectedFileStatus.uploadProgress} 
            uploadStatus={selectedFileStatus.uploadStatus}
            extractStatus={selectedFileStatus.extractStatus}
            extractProgress={selectedFileStatus.extractProgress}
          />
        </div>
        
        <div className="flex-1 hidden sm:block"></div>
      </div>
    </header>
  );
};

export default Header;

