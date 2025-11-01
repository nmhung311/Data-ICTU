import { Upload, FileSearch, FileText, Network, Check } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const steps = [
  {
    id: 1,
    label: "Tải file",
    icon: Upload,
    tooltip: "Upload tệp gốc (.pdf, .docx, .md)",
  },
  {
    id: 2,
    label: "Trích xuất",
    icon: FileSearch,
    tooltip: "Phân tích và tách nội dung",
  },
  {
    id: 3,
    label: "Metadata",
    icon: FileText,
    tooltip: "Sinh thông tin hành chính (doc_id, title, signer…)",
  },
  {
    id: 4,
    label: "Cấu trúc",
    icon: Network,
    tooltip: "Đánh dấu các phần Điều – Khoản – Mục",
  },
  {
    id: 5,
    label: "Hoàn tất",
    icon: Check,
    tooltip: "Hiển thị kết quả cuối cùng để xem hoặc tải về",
  },
];

interface WorkflowStepperProps {
  uploadProgress?: number;
  uploadStatus?: 'idle' | 'uploading' | 'success';
  extractStatus?: 'idle' | 'extracting' | 'success';
  extractProgress?: number;
}

const WorkflowStepper = ({ uploadProgress = 0, uploadStatus = 'idle', extractStatus = 'idle', extractProgress = 0 }: WorkflowStepperProps) => {
  const getStepStyle = (stepId: number) => {
    // Step 1 là "Tải file"
    if (stepId === 1) {
      if (uploadStatus === 'uploading') {
        return {
          bg: 'bg-yellow-500',
          iconColor: 'text-white',
          textColor: 'text-yellow-600',
        };
      } else if (uploadStatus === 'success') {
        return {
          bg: 'bg-green-500',
          iconColor: 'text-white',
          textColor: 'text-green-600',
        };
      }
    }
    
    // Step 2 là "Trích xuất"
    if (stepId === 2) {
      if (extractStatus === 'extracting') {
        return {
          bg: 'bg-yellow-500',
          iconColor: 'text-white',
          textColor: 'text-yellow-600',
        };
      } else if (extractStatus === 'success') {
        return {
          bg: 'bg-green-500',
          iconColor: 'text-white',
          textColor: 'text-green-600',
        };
      }
    }
    
    return {
      bg: 'bg-step-inactive',
      iconColor: 'text-step-text',
      textColor: 'text-step-text',
    };
  };

  const getStepTooltip = (step: typeof steps[0]) => {
    if (step.id === 1 && uploadStatus === 'uploading') {
      return `${uploadProgress}% - Đang tải file lên...`;
    } else if (step.id === 1 && uploadStatus === 'success') {
      return `100% - Tải file thành công`;
    } else if (step.id === 2 && extractStatus === 'extracting') {
      return `${extractProgress}% - Đang trích xuất văn bản...`;
    } else if (step.id === 2 && extractStatus === 'success') {
      return `100% - Trích xuất văn bản thành công`;
    }
    return step.tooltip;
  };

  return (
    <TooltipProvider>
      <div className="flex items-center gap-3">
        {steps.map((step, index) => {
          const stepStyle = getStepStyle(step.id);
          const tooltipText = getStepTooltip(step);
          
          return (
            <div key={step.id} className="flex items-center">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex flex-col items-center gap-1.5 cursor-pointer">
                    <div className={`w-9 h-9 rounded-full ${stepStyle.bg} flex items-center justify-center transition-colors`}>
                      <step.icon className={`w-4 h-4 ${stepStyle.iconColor}`} />
                    </div>
                    <span className={`text-xs ${stepStyle.textColor} whitespace-nowrap transition-colors`}>
                      {step.label}
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="text-sm">{tooltipText}</p>
                </TooltipContent>
              </Tooltip>
              
              {index < steps.length - 1 && (
                <div className="w-8 h-[1px] bg-border mx-2 mb-5" />
              )}
            </div>
          );
        })}
      </div>
    </TooltipProvider>
  );
};

export default WorkflowStepper;
