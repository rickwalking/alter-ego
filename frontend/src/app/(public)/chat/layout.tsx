export default function PublicChatLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.ReactElement {
  return (
    <div
      className="flex h-screen flex-col overflow-hidden"
      style={{ position: "relative", zIndex: 1 }}
    >
      {children}
    </div>
  );
}
