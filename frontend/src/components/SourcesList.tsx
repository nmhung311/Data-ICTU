import { useState, useEffect, useRef } from "react";
import { MoreVertical, FileText, Trash2, Pencil, File, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import PDFViewerContent from "./PDFViewerContent";
import TextPreviewContent from "./TextPreviewContent";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface SourceItem {
  id: string;
  name: string;
  type: string;
  size?: number;
  file?: File;
  filepath?: string;
}

interface SourcesListProps {
  items: SourceItem[];
  uploadProgress?: Record<string, number>;
  uploadStatus?: Record<string, 'idle' | 'uploading' | 'success'>;
  onRename: (id: string, newName: string) => void;
  onDelete: (id: string) => void;
  onSelect: (ids: string[]) => void;
  onExpandPanel?: () => void;
  onExpandChange?: (isExpanded: boolean) => void;
}

const SourcesList = ({ items, uploadProgress = {}, uploadStatus = {}, onRename, onDelete, onSelect, onExpandPanel, onExpandChange }: SourcesListProps) => {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [renameError, setRenameError] = useState("");
  const [expandedFileId, setExpandedFileId] = useState<string | null>(null);
  const menuRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

  // Xử lý select item (radio button - chỉ chọn một)
  const handleItemSelect = (id: string) => {
    // Nếu click vào item đã được chọn thì bỏ chọn, nếu không thì chọn item mới
    setSelectedId(selectedId === id ? null : id);
  };

  // Emit selection changed
  useEffect(() => {
    // Sử dụng ref để tránh gọi lại nếu function reference thay đổi nhưng logic không đổi
    const currentSelection = selectedId ? [selectedId] : [];
    onSelect(currentSelection);
    // Dispatch custom event
    window.dispatchEvent(
      new CustomEvent("sources:selectionChanged", {
        detail: { selectedIds: currentSelection },
      })
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]); // Chỉ depend vào selectedId, không depend vào onSelect để tránh vòng lặp

  // Tự động expand Sources panel khi có file được expand
  useEffect(() => {
    if (expandedFileId && onExpandPanel) {
      onExpandPanel();
    }
    // Thông báo trạng thái expand
    if (onExpandChange) {
      onExpandChange(!!expandedFileId);
    }
  }, [expandedFileId, onExpandPanel, onExpandChange]);

  // Xử lý delete
  const handleDelete = () => {
    if (deleteConfirmId) {
      onDelete(deleteConfirmId);
      setDeleteConfirmId(null);
      // Xóa khỏi selected nếu đang được chọn
      if (selectedId === deleteConfirmId) {
        setSelectedId(null);
      }
    }
  };

  // Xử lý double-click để expand/collapse file
  const handleDoubleClick = (item: SourceItem) => {
    // Kiểm tra loại file để preview
    const nameLower = item.name.toLowerCase();
    const isPDF = nameLower.endsWith('.pdf') || item.type.includes('pdf');
    const isText = nameLower.endsWith('.txt') || item.type.includes('text/plain');
    const isMarkdown = nameLower.endsWith('.md') || nameLower.endsWith('.markdown') || item.type.includes('markdown');
    
    // Cho phép preview PDF, TXT, và MD files
    if (item.file && (isPDF || isText || isMarkdown)) {
      const willExpand = expandedFileId !== item.id;
      setExpandedFileId(willExpand ? item.id : null);
      // useEffect sẽ tự động expand panel khi expandedFileId thay đổi
    }
  };

  // Xử lý rename
  const handleRename = () => {
    if (!renameId || !renameValue.trim()) {
      setRenameError("Tên không được để trống");
      return;
    }

    // Validate ký tự cấm: / \ : * ? " < > |
    const forbiddenChars = /[\/\\:\*\?"<>\|]/;
    if (forbiddenChars.test(renameValue)) {
      setRenameError("Tên không được chứa ký tự: / \\ : * ? \" < > |");
      return;
    }

    onRename(renameId, renameValue.trim());
    setRenameId(null);
    setRenameValue("");
    setRenameError("");
  };

  // Lấy file extension và icon
  const getFileIcon = (filename: string, type: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    
    if (ext === "pdf" || type.includes("pdf")) {
      return (
        <div className="w-6 h-6 rounded bg-red-500 flex items-center justify-center flex-shrink-0">
          <span className="text-white text-xs font-medium">PDF</span>
        </div>
      );
    } else if (ext === "docx" || ext === "doc" || type.includes("word")) {
      return (
        <div className="w-6 h-6 rounded bg-blue-500 flex items-center justify-center flex-shrink-0">
          <File className="w-4 h-4 text-white" />
        </div>
      );
    } else if (ext === "md" || type.includes("markdown")) {
      return (
        <div className="w-6 h-6 rounded bg-gray-500 flex items-center justify-center flex-shrink-0">
          <File className="w-4 h-4 text-white" />
        </div>
      );
    }
    return (
      <div className="w-6 h-6 rounded bg-gray-400 flex items-center justify-center flex-shrink-0">
        <FileText className="w-4 h-4 text-white" />
      </div>
    );
  };

  // Đóng menu khi click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuOpenId) {
        const menuElement = menuRefs.current[menuOpenId];
        if (menuElement && !menuElement.contains(event.target as Node)) {
          setMenuOpenId(null);
        }
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [menuOpenId]);

  // Xử lý keyboard cho menu
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && menuOpenId) {
        setMenuOpenId(null);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [menuOpenId]);

  if (items.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center py-8">
        <p className="text-sm text-muted-foreground">Chưa có nguồn nào</p>
      </div>
    );
  }

  const itemToDelete = items.find((item) => item.id === deleteConfirmId);
  const itemToRename = items.find((item) => item.id === renameId);

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex flex-col h-full">

        {/* Danh sách items */}
        <div className="flex-1 overflow-auto py-2">
          <div className="space-y-2 px-2">
            {items.map((item) => {
              const isSelected = selectedId === item.id;
              const isMenuOpen = menuOpenId === item.id;
              const isExpanded = expandedFileId === item.id;
              const nameLower = item.name.toLowerCase();
              const isPDF = item.file && (nameLower.endsWith('.pdf') || item.type.includes('pdf'));
              const isText = item.file && (nameLower.endsWith('.txt') || item.type.includes('text/plain'));
              const isMarkdown = item.file && (nameLower.endsWith('.md') || nameLower.endsWith('.markdown') || item.type.includes('markdown'));
              const canPreview = isPDF || isText || isMarkdown;
              
              // Nếu có file đang được view, chỉ hiển thị file đó, ẩn các file khác
              if (expandedFileId && expandedFileId !== item.id) {
                return null;
              }

              return (
                <div key={item.id} className="flex flex-col">
                  <div
                    className={`
                      flex items-center gap-3 px-3 py-2 rounded-lg transition-colors
                      ${isSelected ? "bg-white" : "bg-white hover:bg-[#EEF2FF]"}
                      border border-transparent hover:border-border
                      focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2
                      cursor-pointer
                    `}
                    onDoubleClick={() => handleDoubleClick(item)}
                    title={canPreview ? "Double-click để xem file" : ""}
                  >
                  {/* Icon */}
                  {getFileIcon(item.name, item.type)}

                  {/* Tên file với tooltip */}
                  <div className="flex-1 min-w-0">
                    <Tooltip delayDuration={200}>
                      <TooltipTrigger asChild>
                        <span
                          className="text-sm text-foreground block cursor-default"
                          style={{
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {item.name}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent
                        side="bottom"
                        className="z-50 max-w-xs break-words"
                      >
                        <p className="text-xs">
                          {uploadStatus[item.id] === 'uploading' && !item.filepath 
                            ? `${uploadProgress[item.id] || 0}% - Đang tải file lên...`
                            : item.name}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </div>

                  {/* Radio button */}
                  <label className="cursor-pointer flex-shrink-0">
                    <input
                      type="radio"
                      name="source-selection"
                      checked={isSelected}
                      onChange={() => handleItemSelect(item.id)}
                      className="w-4 h-4 cursor-pointer accent-primary"
                      aria-label={`Chọn ${item.name}`}
                      onKeyDown={(e) => {
                        if (e.key === " " || e.key === "Enter") {
                          e.preventDefault();
                          handleItemSelect(item.id);
                        }
                      }}
                    />
                  </label>

                  {/* Menu 3 chấm */}
                  <div className="relative flex-shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0"
                      onClick={() => setMenuOpenId(isMenuOpen ? null : item.id)}
                      aria-label={`Menu cho ${item.name}`}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setMenuOpenId(isMenuOpen ? null : item.id);
                        }
                      }}
                    >
                      <MoreVertical className="w-4 h-4" />
                    </Button>

                    {/* Context Menu */}
                    {isMenuOpen && (
                      <div
                        ref={(el) => (menuRefs.current[item.id] = el)}
                        className="absolute right-0 top-full mt-1 bg-white border border-border rounded-lg shadow-lg z-50 min-w-[180px]"
                        role="menu"
                        aria-label={`Menu hành động cho ${item.name}`}
                      >
                        <button
                          className="w-full flex items-center gap-3 px-4 py-2 text-sm text-foreground hover:bg-accent transition-colors"
                          onClick={() => {
                            setRenameId(item.id);
                            setRenameValue(item.name);
                            setMenuOpenId(null);
                          }}
                          role="menuitem"
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              setRenameId(item.id);
                              setRenameValue(item.name);
                              setMenuOpenId(null);
                            }
                          }}
                        >
                          <Pencil className="w-4 h-4" />
                          <span>Đổi tên nguồn</span>
                        </button>
                        <button
                          className="w-full flex items-center gap-3 px-4 py-2 text-sm text-foreground hover:bg-accent transition-colors"
                          onClick={() => {
                            setDeleteConfirmId(item.id);
                            setMenuOpenId(null);
                          }}
                          role="menuitem"
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              setDeleteConfirmId(item.id);
                              setMenuOpenId(null);
                            }
                          }}
                        >
                          <Trash2 className="w-4 h-4" />
                          <span>Xoá nguồn</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* File Preview Content - hiển thị khi expanded */}
                {isExpanded && item.file && (
                  <>
                    {isPDF && (
                      <PDFViewerContent 
                        file={item.file} 
                        onClose={() => setExpandedFileId(null)}
                      />
                    )}
                    {(isText || isMarkdown) && (
                      <TextPreviewContent 
                        file={item.file}
                        filepath={item.filepath}
                        filename={item.name}
                        onClose={() => setExpandedFileId(null)}
                      />
                    )}
                  </>
                )}
              </div>
              );
            })}
          </div>
        </div>

        {/* Dialog xác nhận xóa */}
        <Dialog open={!!deleteConfirmId} onOpenChange={(open) => !open && setDeleteConfirmId(null)}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-left">Xác nhận xóa</DialogTitle>
            </DialogHeader>
            <div className="py-4 space-y-3">
              <div className="space-y-2">
                <p className="text-sm text-foreground">
                  Bạn có chắc muốn xoá
                </p>
                <p className="text-sm text-foreground font-mono break-all leading-relaxed">
                  {itemToDelete?.name}
                </p>
              </div>
              <p className="text-sm text-muted-foreground">
                Hành động này không thể hoàn tác.
              </p>
            </div>
            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={() => setDeleteConfirmId(null)}
                className="min-w-[80px]"
              >
                Hủy
              </Button>
              <Button 
                variant="destructive" 
                onClick={handleDelete}
                className="min-w-[80px] bg-red-600 hover:bg-red-700"
              >
                Xóa
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Dialog đổi tên */}
        <Dialog open={!!renameId} onOpenChange={(open) => !open && setRenameId(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Đổi tên nguồn</DialogTitle>
              <DialogDescription>
                Nhập tên mới cho nguồn. Đổi tên chỉ thay đổi nhãn hiển thị, không ảnh hưởng đến file gốc.
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <Label htmlFor="rename-input">Tên mới</Label>
              <Input
                id="rename-input"
                value={renameValue}
                onChange={(e) => {
                  setRenameValue(e.target.value);
                  setRenameError("");
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleRename();
                  } else if (e.key === "Escape") {
                    setRenameId(null);
                  }
                }}
                className="mt-2"
                autoFocus
              />
              {renameError && (
                <p className="text-sm text-destructive mt-2">{renameError}</p>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setRenameId(null)}>
                Hủy
              </Button>
              <Button onClick={handleRename}>Lưu</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  );
};

export default SourcesList;

