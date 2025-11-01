import * as React from "react";
import { GripVertical } from "lucide-react";
import * as ResizablePrimitive from "react-resizable-panels";

import { cn } from "@/lib/utils";

const ResizablePanelGroup = ({ className, ...props }: React.ComponentProps<typeof ResizablePrimitive.PanelGroup>) => (
  <ResizablePrimitive.PanelGroup
    className={cn("flex h-full w-full data-[panel-group-direction=vertical]:flex-col", className)}
    {...props}
  />
);

const ResizablePanel = React.forwardRef<
  React.ElementRef<typeof ResizablePrimitive.Panel>,
  React.ComponentPropsWithoutRef<typeof ResizablePrimitive.Panel>
>((props, ref) => (
  <ResizablePrimitive.Panel ref={ref} {...props} />
));
ResizablePanel.displayName = "ResizablePanel";

const ResizableHandle = ({
  withHandle,
  className,
  ...props
}: React.ComponentProps<typeof ResizablePrimitive.PanelResizeHandle> & {
  withHandle?: boolean;
}) => (
  <ResizablePrimitive.PanelResizeHandle
    className={cn(
      "relative flex w-px items-center justify-center bg-border after:absolute after:inset-y-0 after:left-1/2 after:w-1 after:-translate-x-1/2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 cursor-col-resize touch-none min-h-[40px]",
      className,
    )}
    title="Kéo để thay đổi kích thước - Double-click để reset"
    {...props}
  >
    {withHandle && (
      <div className="z-10 flex h-10 w-3 items-center justify-center rounded-sm border bg-border group-hover:bg-[#94A3B8] transition-colors touch-none">
        <GripVertical className="h-3 w-3" />
      </div>
    )}
  </ResizablePrimitive.PanelResizeHandle>
);


export { ResizablePanelGroup, ResizablePanel, ResizableHandle };
