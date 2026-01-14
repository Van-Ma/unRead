export default function ContextManager({ 
  folders,
  activeTab,
  onFolderClick,
  activeFolderId,
  onDeleteFolder,
  onEditFolder,  
  onAddContext,  
}) {
  const className = activeTab === "chat" ? "chat-grid" : "folder-grid";

  // handle folder click
  const handleFolderClick = (folder, e) => {
    e.stopPropagation(); 
    if (!onFolderClick) return;

    if (folder.id === activeFolderId) {
      onFolderClick(null, null, null);
    } else {
      onFolderClick(folder.snippets, folder.id, folder.filePath);
    }
  };

  // handle click on the grid background
  const handleGridClick = () => {
    if (onFolderClick) onFolderClick(null, null, null);
  };

  return (
    <>
      <div className={className} onClick={handleGridClick}>
        {folders.map((folder) => (
          <div key={folder.id} className="folder-wrapper">
            <div
              className={`folder ${folder.id === activeFolderId ? "active-folder" : ""}`}
              onClick={(e) => handleFolderClick(folder, e)}
            >
              <img src="/workspace/folder.png" alt="folder" />
              <span className="folder-name">{folder.name}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="folder-buttons">
        {activeTab === "files" && onAddContext && (
          <button
            className="folder-controls-btn"
            onClick={onAddContext}
          >
            Add Context
          </button>
        )}

        {activeTab === "chat" && onEditFolder && activeFolderId !== null && (
          <button
            className="folder-controls-btn"
            onClick={() => onEditFolder(activeFolderId)}
          >
            Edit
          </button>
        )}

        {onDeleteFolder && activeFolderId !== null && (
          <button
            className="folder-controls-btn"
            onClick={() => onDeleteFolder(activeFolderId)}
          >
            Delete
          </button>
        )}
      </div>
    </>
  );
}
