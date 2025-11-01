import { Loader2 } from "lucide-react";
import { useRef, useState, useEffect } from "react";

interface ConversationColumnProps {
  onAddSource: (file: File) => void;
  sourcesCount: number;
  sources: Array<{
    id: string;
    name: string;
    filepath?: string;
    markdown?: string;
    file?: File;
  }>;
  selectedSourceIds?: string[];
  documentContent?: string | null; // Deprecated: không sử dụng nữa, chỉ giữ để tương thích
  metadataContent?: string | null; // Nội dung metadata đã tạo (bản đã chia nhỏ) - chỉ hiển thị bản này
  isGeneratingMetadata?: boolean; // Trạng thái đang tạo metadata
  onSendQuestion: (question: string, filepath: string) => Promise<string>;
  onTriggerEdit?: (trigger: () => void) => void; // Callback để nhận function trigger edit
}

interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
}

const ConversationColumn = ({ onAddSource, sourcesCount, sources, selectedSourceIds = [], documentContent, metadataContent, isGeneratingMetadata = false, onSendQuestion, onTriggerEdit }: ConversationColumnProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  // Inline edit refs/state
  const messageRefs = useRef<{ [id: string]: HTMLDivElement | null }>({});
  // Lưu bản nháp trong khi đang gõ để tránh setState gây render lại làm nhảy caret
  const draftContentsRef = useRef<{ [id: string]: string }>({});
  const [activelyEditingId, setActivelyEditingId] = useState<string | null>(null);

  // Very-light markdown to HTML (headings, bold/italic, code block, inline code, list, line breaks)
  const renderMarkdown = (md: string): string => {
    let html = md
      .replace(/^######\s?(.*)$/gm, '<h6>$1</h6>')
      .replace(/^#####\s?(.*)$/gm, '<h5>$1</h5>')
      .replace(/^####\s?(.*)$/gm, '<h4>$1</h4>')
      .replace(/^###\s?(.*)$/gm, '<h3>$1</h3>')
      // Xử lý đặc biệt cho ## Metadata - căn giữa và mờ
      .replace(/^##\s+Metadata\s*$/gm, '<h2 style="text-align: center; opacity: 0.6;">Metadata</h2>')
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

  const saveEditedMessage = async (msgId: string, newPlainText: string) => {
    setMessages((prev) => prev.map((m) => (m.id === msgId ? { ...m, content: newPlainText } : m)));
    // Try to PATCH backend if available; ignore errors
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';
      await fetch(`${apiUrl}/api/messages/${encodeURIComponent(msgId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: newPlainText })
      }).catch(() => {});
    } catch {}
  };

  // Không debounce setState khi đang gõ để tránh nhảy caret; chỉ lưu khi blur

  // Auto scroll xuống tin nhắn mới nhất
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Expose function để trigger edit inline từ bên ngoài (từ nút Sửa trong Studio)
  const triggerEditLastMessage = useRef<() => void>(() => {});
  
  useEffect(() => {
    triggerEditLastMessage.current = () => {
      // Tìm câu trả lời assistant cuối cùng (không phải "Đang xử lý...")
      const lastAssistantMessage = [...messages]
        .reverse()
        .find(msg => msg.role === "assistant" && msg.content !== "Đang xử lý...");
      
      if (lastAssistantMessage) {
        const id = lastAssistantMessage.id;
        setActivelyEditingId(id);
        setTimeout(() => {
          const el = messageRefs.current[id];
          if (el) {
            el.focus();
            // Đưa về text thuần để chỉnh sửa
            el.innerText = lastAssistantMessage.content;
            const range = document.createRange();
            range.selectNodeContents(el);
            range.collapse(false);
            const sel = window.getSelection();
            sel?.removeAllRanges();
            sel?.addRange(range);
          }
        }, 50);
      }
    };
    
    if (onTriggerEdit) {
      onTriggerEdit(() => triggerEditLastMessage.current());
    }
  }, [messages, onTriggerEdit]);

  // Inline edit handlers for contentEditable elements
  const onAssistantFocus = (msgId: string, content: string) => {
    setActivelyEditingId(msgId);
    const el = messageRefs.current[msgId];
    if (el) {
      el.innerText = content; // switch to plain text while editing
    }
  };

  const onAssistantInput = (msgId: string, e: React.FormEvent<HTMLDivElement>) => {
    const text = (e.currentTarget as HTMLDivElement).innerText;
    draftContentsRef.current[msgId] = text;
  };

  const onAssistantBlur = (msgId: string, e: React.FocusEvent<HTMLDivElement>) => {
    const text = draftContentsRef.current[msgId] ?? (e.currentTarget as HTMLDivElement).innerText;
    saveEditedMessage(msgId, text);
    setActivelyEditingId((prev) => (prev === msgId ? null : prev));
    const el = messageRefs.current[msgId];
    if (el) el.innerHTML = renderMarkdown(text);
  };

  // Không còn nút Lưu thủ công; hệ thống tự lưu khi blur

  // Chỉ hiển thị metadataContent (bản đã chia nhỏ), không hiển thị documentContent nữa
  useEffect(() => {
    if (selectedSourceIds.length === 0) {
      // Không có file nào được chọn, xóa messages
      setMessages([]);
      return;
    }
    
    const selectedId = selectedSourceIds[0];
    console.log('📋 ConversationColumn - metadataContent:', {
      hasMetadata: !!metadataContent,
      metadataLength: metadataContent?.length,
      selectedId
    });
    
    // Chỉ hiển thị metadataContent
    if (metadataContent) {
      console.log('✅ Hiển thị metadataContent');
      setMessages((prev) => {
        const existingMsg = prev.find((m) => m.id === `metadata-${selectedId}`);
        if (existingMsg && existingMsg.content === metadataContent) {
          return prev; // Đã có, không cần thay đổi
        }
        
        const metadataMessage: Message = {
          id: `metadata-${selectedId}`,
          content: metadataContent,
          role: "assistant",
          timestamp: new Date(),
        };
        return [metadataMessage];
      });
    } else {
      // Không có metadata, xóa messages
      console.log('⚠️ Không có metadataContent để hiển thị');
      setMessages([]);
    }
  }, [metadataContent, selectedSourceIds]);

  return (
    <div className="flex flex-col h-full">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-foreground">Chuẩn hóa dữ liệu cho AI</h2>
        {isGeneratingMetadata && (
          <div className="mt-2 text-xs text-muted-foreground">
            Đang tạo metadata...
          </div>
        )}
      </div>
      
      <div className="flex-1 overflow-hidden flex flex-col">
        {sourcesCount > 0 && (messages.length > 0 || metadataContent) && (
          <div className="flex-1 overflow-auto mb-4">
            <div className="flex flex-col gap-4 p-4">
              {messages.map((msg) => {
                  const isLoadingMsg = msg.content === "Đang xử lý..." && msg.role === "assistant";
                  
                  return (
                    <div
                      key={msg.id}
                      className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} group`}
                    >
                      <div
                        className={`max-w-[80%] rounded-lg px-4 py-2 relative ${
                          msg.role === "user"
                            ? "bg-blue-500 text-white"
                            : "bg-gray-100 text-foreground"
                        }`}
                      >
                        {isLoadingMsg ? (
                          // Loading state
                          <div className="flex items-center gap-2 text-sm">
                            <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
                            <span className="text-muted-foreground">Đang xử lý...</span>
                          </div>
                        ) : (
                          // Inline contentEditable cho assistant; user thì hiển thị bình thường
                          msg.role === "assistant" ? (
                            <div
                              ref={(el) => (messageRefs.current[msg.id] = el)}
                              contentEditable
                              suppressContentEditableWarning
                              className="text-sm whitespace-pre-wrap break-words focus:outline-none"
                              onFocus={() => onAssistantFocus(msg.id, msg.content)}
                              onInput={(e) => onAssistantInput(msg.id, e)}
                              onBlur={(e) => onAssistantBlur(msg.id, e)}
                              dangerouslySetInnerHTML={{
                                __html:
                                  activelyEditingId === msg.id ? msg.content : renderMarkdown(msg.content),
                              }}
                            />
                          ) : (
                            <p className="text-sm whitespace-pre-wrap break-words flex-1">
                              {msg.content}
                            </p>
                          )
                        )}
                      </div>
                    </div>
                  );
                })}
              <div ref={messagesEndRef} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConversationColumn;
