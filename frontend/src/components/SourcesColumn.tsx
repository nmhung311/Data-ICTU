import { Plus, Upload, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRef, useState } from "react";
import SourcesList from "./SourcesList";

interface Source {
  id: string;
  name: string;
  type: string;
  size: number;
  file?: File;
}

interface SourcesColumnProps {
  sources: Source[];
  uploadProgress?: Record<string, number>;
  uploadStatus?: Record<string, 'idle' | 'uploading' | 'success'>;
  onAddSource: (file: File) => void;
  onRename: (id: string, newName: string) => void;
  onDelete: (id: string) => void;
  onSelect: (ids: string[]) => void;
  onExpandPanel?: () => void;
}

const SourcesColumn = ({ 
  sources, 
  uploadProgress = {},
  uploadStatus = {},
  onAddSource, 
  onRename, 
  onDelete,
  onSelect,
  onExpandPanel
}: SourcesColumnProps) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isFileExpanded, setIsFileExpanded] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onAddSource(file);
    }
    // Reset input để có thể chọn cùng file lại
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleAddClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-foreground">Nguồn</h2>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".pdf,.txt,.docx,.doc,.md,.markdown"
        onChange={handleFileChange}
        multiple={false}
      />

      {sources.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-6 py-8">
          <div className="flex flex-col items-center gap-6 max-w-[320px]">
            {/* Icon lớn */}
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center shadow-sm">
              <FileText className="w-10 h-10 text-blue-600" />
            </div>
            
            {/* Text hướng dẫn */}
            <div className="space-y-2">
              <h3 className="text-base font-semibold text-foreground">
                Chưa có nguồn nào
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Thêm file (PDF, TXT, DOCX, MD) để bắt đầu trích xuất và xử lý nội dung. Bạn có thể upload nhiều file để làm việc với nhiều nguồn cùng lúc.
              </p>
            </div>
            
            {/* Nút thêm nguồn lớn */}
            <Button 
              onClick={handleAddClick}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white shadow-sm h-11 font-medium rounded-lg"
              size="lg"
            >
              <Upload className="w-4 h-4 mr-2" />
              Thêm file
            </Button>
            
            {/* Gợi ý */}
            <p className="text-xs text-muted-foreground mt-2">
              Hoặc kéo thả file vào đây
            </p>
          </div>
        </div>
      ) : (
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Nút thêm nguồn ở đầu danh sách - ẩn khi có file đang được xem */}
          {!isFileExpanded && (
            <div className="mb-3">
              <Button 
                variant="outline"
                className="w-full hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 rounded-lg h-10 font-medium"
                onClick={handleAddClick}
              >
                <Plus className="w-4 h-4 mr-2" />
                Thêm nguồn
              </Button>
            </div>
          )}
          
          <SourcesList
            items={sources}
            uploadProgress={uploadProgress}
            uploadStatus={uploadStatus}
            onRename={onRename}
            onDelete={onDelete}
            onSelect={onSelect}
            onExpandPanel={onExpandPanel}
            onExpandChange={setIsFileExpanded}
          />
        </div>
      )}
    </div>
  );
};

export default SourcesColumn;
