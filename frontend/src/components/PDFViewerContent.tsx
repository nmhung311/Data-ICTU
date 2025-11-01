import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PDFViewerContentProps {
  file: File;
  onClose?: () => void;
}

const PDFViewerContent = ({ file, onClose }: PDFViewerContentProps) => {
  const [pages, setPages] = useState<HTMLImageElement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadPDF = async () => {
      try {
        setLoading(true);
        setError(null);

        // Load PDF.js từ CDN
        // @ts-ignore
        if (!window.pdfjsLib) {
          const script = document.createElement("script");
          script.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
          script.async = true;
          
          await new Promise((resolve, reject) => {
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
          });
          
          // @ts-ignore
          window.pdfjsLib.GlobalWorkerOptions.workerSrc = 
            "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
        }

        // @ts-ignore
        const pdfjsLib = window.pdfjsLib;
        const arrayBuffer = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        const numPages = pdf.numPages;

        const pageImages: HTMLImageElement[] = [];

        for (let pageNum = 1; pageNum <= numPages; pageNum++) {
          if (!isMounted) break;
          
          const page = await pdf.getPage(pageNum);
          const viewport = page.getViewport({ scale: 1.5 });
          
          const canvas = document.createElement("canvas");
          const context = canvas.getContext("2d");
          
          if (!context) {
            throw new Error("Không thể tạo canvas context");
          }

          canvas.height = viewport.height;
          canvas.width = viewport.width;

          await page.render({
            canvasContext: context,
            viewport: viewport,
          }).promise;

          // Convert canvas to image
          const img = new Image();
          img.src = canvas.toDataURL();
          pageImages.push(img);
        }

        if (isMounted) {
          setPages(pageImages);
          setLoading(false);
        }
      } catch (err) {
        console.error("Lỗi khi load PDF:", err);
        if (isMounted) {
          setError("Không thể đọc file PDF");
          setLoading(false);
        }
      }
    };

    loadPDF();

    return () => {
      isMounted = false;
    };
  }, [file]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 px-4 bg-gray-50">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
          <p className="text-xs text-muted-foreground">Đang tải PDF...</p>
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
      
      {/* Nội dung PDF */}
      <div className="max-w-full flex flex-col items-center gap-3">
        {pages.map((img, index) => (
          <div
            key={index}
            className="bg-white shadow-sm rounded-sm overflow-hidden max-w-full"
            style={{
              maxWidth: `${img.width}px`,
            }}
          >
            <img
              src={img.src}
              alt={`Trang ${index + 1}`}
              className="w-full h-auto block"
              style={{ display: "block" }}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default PDFViewerContent;

