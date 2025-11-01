import { FileSearch, Brain, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useState } from "react";

interface Source {
  id: string;
  name: string;
  filepath?: string;
  markdown?: string;
}

interface StudioColumnProps {
  sources?: Source[];
  selectedSourceIds?: string[];
  uploadStatus?: Record<string, 'idle' | 'uploading' | 'success'>;
  extractStatus?: Record<string, 'idle' | 'extracting' | 'success'>;
  extractProgress?: Record<string, number>;
  onExtractStart?: (sourceId: string) => void;
  onExtractProgress?: (sourceId: string, progress: number) => void;
  onExtractComplete?: (sourceId: string, markdown: string) => void;
  onExtractError?: (sourceId: string) => void;
  onEditClick?: () => void;
  isGeneratingMetadata?: boolean;
}

const tools = [
  { icon: FileSearch, label: "Trích xuất văn bản", id: "extract" },
  { icon: Brain, label: "Tạo Metadata", id: "edit" },
];

const StudioColumn = ({ sources = [], selectedSourceIds = [], uploadStatus = {}, extractStatus = {}, extractProgress = {}, onExtractStart, onExtractProgress, onExtractComplete, onExtractError, onEditClick, isGeneratingMetadata = false }: StudioColumnProps) => {
  const [isExtracting, setIsExtracting] = useState(false);

  const handleExtract = async () => {
    if (!sources || sources.length === 0) {
      return;
    }

    // Lấy các file đã chọn hoặc tất cả file nếu chưa chọn
    const filesToExtract = selectedSourceIds.length > 0
      ? sources.filter(s => selectedSourceIds.includes(s.id) && s.filepath && !s.markdown)
      : sources.filter(s => s.filepath && !s.markdown);

    if (filesToExtract.length === 0) {
      return;
    }

    setIsExtracting(true);

    try {
      const totalFiles = filesToExtract.length;
      let completedFiles = 0;

      // Trích xuất tuần tự từng file (xử lý theo hàng đợi)
      for (let index = 0; index < filesToExtract.length; index++) {
        const source = filesToExtract[index];
        if (!source.filepath) continue;

        // Báo bắt đầu trích xuất cho file này
        if (onExtractStart) {
          onExtractStart(source.id);
        }

        // Tính progress ban đầu dựa trên số file đã xử lý
        const baseProgress = Math.round((completedFiles / totalFiles) * 100);
        if (onExtractProgress) {
          onExtractProgress(source.id, baseProgress);
        }

        try {
          // Cập nhật progress 50% khi đang fetch
          const midProgress = Math.round(((completedFiles + 0.5) / totalFiles) * 100);
          if (onExtractProgress) {
            onExtractProgress(source.id, midProgress);
          }

          const response = await fetch('http://localhost:5000/api/extract-pdf', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              filepath: source.filepath,
            }),
          });

          if (response.ok) {
            const data = await response.json();
            completedFiles++;
            
            // Cập nhật progress khi hoàn thành file này
            const finalProgress = Math.round((completedFiles / totalFiles) * 100);
            if (onExtractProgress) {
              onExtractProgress(source.id, finalProgress);
            }
            
            if (onExtractComplete && data.markdown) {
              onExtractComplete(source.id, data.markdown);
            }
          } else {
            console.error(`Lỗi trích xuất file ${source.name}:`, await response.text());
            if (onExtractError) {
              onExtractError(source.id);
            }
          }
        } catch (error) {
          console.error(`Lỗi khi trích xuất file ${source.name}:`, error);
          if (onExtractError) {
            onExtractError(source.id);
          }
        }
      }
    } catch (error) {
      console.error('Lỗi khi trích xuất:', error);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleToolClick = (toolId: string) => {
    if (toolId === "extract") {
      handleExtract();
    } else if (toolId === "edit" && onEditClick) {
      onEditClick();
    }
    // Các tool khác có thể xử lý sau
  };

  return (
    <div className="flex flex-col h-full">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-foreground">Chức năng</h2>
      </div>

      <div className="flex flex-col gap-3 sm:gap-4 mb-6">
        {tools.map((tool) => {
          const isExtractButton = tool.id === "extract";
          const isMetadataButton = tool.id === "edit";
          // Kiểm tra xem có bất kỳ file nào đang upload không
          const hasUploadingFiles = sources.some(s => uploadStatus[s.id] === 'uploading');
          const hasSelectedFile = selectedSourceIds.length > 0;
          
          let isDisabled = false;
          if (isExtractButton) {
            isDisabled = isExtracting || !sources || sources.length === 0 || hasUploadingFiles;
          } else if (isMetadataButton) {
            isDisabled = isGeneratingMetadata || !hasSelectedFile || hasUploadingFiles;
          }
          
          return (
            <Card 
              key={tool.id}
              className={`cursor-pointer hover:bg-accent transition-colors min-h-[56px] sm:min-h-[64px] ${
                isDisabled ? 'opacity-50 cursor-not-allowed' : ''
              }`}
              onClick={() => !isDisabled && handleToolClick(tool.id)}
            >
              <CardContent className="p-3 sm:p-4 flex flex-col items-center justify-center gap-2 h-full">
                {((isExtractButton && isExtracting) || (isMetadataButton && isGeneratingMetadata)) ? (
                  <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 text-foreground flex-shrink-0 animate-spin" />
                ) : (
                  <tool.icon className="w-4 h-4 sm:w-5 sm:h-5 text-foreground flex-shrink-0" />
                )}
                <span className="text-xs text-center text-foreground leading-tight">
                  {tool.label}
                </span>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
};

export default StudioColumn;
