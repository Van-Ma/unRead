export default function ContextManager({ folders, activeTab }) {

  const className =
    activeTab === "chat" ? "chat-grid" : "folder-grid";

  return (
    <div className={className}>
      {folders.map((folder) => (
        <div key={folder.id} className="folder-wrapper">
          <div className="folder">
            <img src="/workspace/folder.png" alt="folder" />
            <span className="folder-name">{folder.name}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
