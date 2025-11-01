import { useState } from "react";
import { FileText, MessageSquare, Sparkles } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import SourcesColumn from "./SourcesColumn";
import ConversationColumn from "./ConversationColumn";
import StudioColumn from "./StudioColumn";

const MobileColumnTabs = () => {
  const [activeTab, setActiveTab] = useState("conversation");

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
      <TabsList className="grid w-full grid-cols-3 mb-2">
        <TabsTrigger value="sources" className="text-xs" aria-label="Nguồn">
          <FileText className="w-4 h-4 mr-1" />
          Nguồn
        </TabsTrigger>
        <TabsTrigger value="conversation" className="text-xs" aria-label="Cuộc trò chuyện">
          <MessageSquare className="w-4 h-4 mr-1" />
          Trò chuyện
        </TabsTrigger>
        <TabsTrigger value="studio" className="text-xs" aria-label="Studio">
          <Sparkles className="w-4 h-4 mr-1" />
          Studio
        </TabsTrigger>
      </TabsList>

      <TabsContent value="sources" className="flex-1 mt-0 overflow-auto bg-card rounded-lg border border-border p-4 shadow-sm">
        <SourcesColumn />
      </TabsContent>

      <TabsContent value="conversation" className="flex-1 mt-0 overflow-auto bg-card rounded-lg border border-border p-4 shadow-sm">
        <ConversationColumn />
      </TabsContent>

      <TabsContent value="studio" className="flex-1 mt-0 overflow-auto bg-card rounded-lg border border-border p-4 shadow-sm">
        <StudioColumn />
      </TabsContent>
    </Tabs>
  );
};

export default MobileColumnTabs;
