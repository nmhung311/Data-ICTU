import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TextPreviewContentProps {
  file?: File;
  filepath?: string;
  filename?: string;
  onClose?: () => void;
}

const TextPreviewContent = ({ file, filepath, filename, onClose }: TextPreviewContentProps) => {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMarkdown, setIsMarkdown] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const loadText = async () => {
      try {
        setLoading(true);
        setError(null);

        let text = "";

        // Ưu tiên load từ File object nếu có
        if (file) {
          text = await file.text();
        } else if (filepath) {
          // Thử fetch trực tiếp file từ backend uploads folder
          // filepath có thể là "uploads/filename" hoặc chỉ "filename"
          const path = filepath.startsWith('uploads/') ? filepath : `uploads/${filepath}`;
          const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';
          const fileResponse = await fetch(`${apiUrl}/${path}`);
          if (fileResponse.ok) {
            text = await fileResponse.text();
          } else {
            throw new Error("Không thể tải file từ server");
          }
        } else {
          throw new Error("Không có file hoặc filepath để load");
        }

        // Kiểm tra xem có phải markdown không
        const fileName = filename || file?.name || "";
        const isMd = fileName.toLowerCase().endsWith('.md') || fileName.toLowerCase().endsWith('.markdown');
        setIsMarkdown(isMd);

        if (isMounted) {
          setContent(text);
          setLoading(false);
        }
      } catch (err) {
        console.error("Lỗi khi load text:", err);
        if (isMounted) {
          setError("Không thể đọc file");
          setLoading(false);
        }
      }
    };

    if (file || filepath) {
      loadText();
    }

    return () => {
      isMounted = false;
    };
  }, [file, filepath, filename]);

  // Render markdown đơn giản
  const renderMarkdown = (md: string): string => {
    let html = md
      .replace(/^######\s?(.*)$/gm, '<h6>$1</h6>')
      .replace(/^#####\s?(.*)$/gm, '<h5>$1</h5>')
      .replace(/^####\s?(.*)$/gm, '<h4>$1</h4>')
      .replace(/^###\s?(.*)$/gm, '<h3>$1</h3>')
      .replace(/^##\s?(.*)$/gm, '<h2>$1</h2>')
      .replace(/^#\s?(.*)$/gm, '<h1>$1</h1>')
      .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')
      .replace(/^\s*[-*]\s+(.*)$/gm, '<li>$1</li>');
    
    // Wrap list items with <ul>
    html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
    // Line breaks
    html = html.replace(/\n/g, '<br/>');
    return html;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 px-4 bg-gray-50">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
          <p className="text-xs text-muted-foreground">Đang tải file...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8 px-4 bg-gray-50">
        <p className="text-xs text-red-500">{error}</p>
      </div>
    );
  }

  return (
    <div className="relative bg-gray-50 py-4 px-2 overflow-x-hidden">
      {/* Nút đóng */}
      {onClose && (
        <div className="sticky top-0 z-10 flex justify-end mb-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 bg-white shadow-sm hover:bg-gray-100"
            onClick={onClose}
            aria-label="Đóng xem file"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}
      
      {/* Nội dung Text/Markdown */}
      <div className="bg-white rounded-lg shadow-sm p-4 max-w-full overflow-auto">
        {isMarkdown ? (
          <div 
            className="prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
          />
        ) : (
          <pre className="whitespace-pre-wrap font-mono text-sm text-foreground break-words">
            {content}
          </pre>
        )}
      </div>
    </div>
  );
};

export default TextPreviewContent;

