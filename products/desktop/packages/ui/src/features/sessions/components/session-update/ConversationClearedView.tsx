import { ChatMarker, ChatMarkerContent } from "@flind/quill";

export function ConversationClearedView() {
  return (
    <ChatMarker variant="separator">
      <ChatMarkerContent>Conversation cleared</ChatMarkerContent>
    </ChatMarker>
  );
}
