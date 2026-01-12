import React, { useState, useEffect, useRef } from "react";
import '../styles/contextmanager.scss';
import FileManager from './FileManager'; 

export default function ContextManager({ folders, setFolders }) {
  const [activeFolderId, setActiveFolderId] = useState(null);
  const [editingFolder, setEditingFolder] = useState(null);
  const wrapperRef = useRef(null);

  const handleFolderClick = (folderId) => {
    setActiveFolderId(prev => (prev === folderId ? null : folderId));
  };

  const handleEdit = (folder) => {
    setEditingFolder(folder);
  };

  const handleDelete = (folderId) => {
    setFolders(prev => prev.filter(f => f.id !== folderId));
    if (activeFolderId === folderId) setActiveFolderId(null);
    if (editingFolder?.id === folderId) setEditingFolder(null);
  };

  const handleSendToChat = (folder) => console.log("Send to chat:", folder);

  const handleSaveEdit = (updatedFolder) => {
    setFolders(prev => prev.map(f => f.id === updatedFolder.id ? updatedFolder : f));
    setEditingFolder(null);
    setActiveFolderId(null);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setActiveFolderId(null);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="context-manager" ref={wrapperRef}>
      {folders.length === 0 ? (
        <p className="empty-context">No folders yet</p>
      ) : (
        <div className="folders-container">
          {folders.map(folder => (
            <div key={folder.id} className="folder-wrapper">
              <div
                className="folder"
                onClick={() => handleFolderClick(folder.id)}
              >
                <div className="folder-icon">
                  <img src="/workspace/folder.png" alt="folder" />
                </div>
                <div className="folder-info">
                  <span className="folder-name">{folder.name}</span>
                </div>
              </div>

              <div className={`folder-actions ${activeFolderId === folder.id ? "active" : ""}`}>
                <button onClick={(e) => { e.stopPropagation(); handleEdit(folder); }}>
                  <img src="/workspace/edit.png" alt="Edit" />
                </button>
                <button onClick={(e) => { e.stopPropagation(); handleDelete(folder.id); }}>
                  <img src="/workspace/trash.png" alt="Delete" />
                </button>
                <button onClick={(e) => { e.stopPropagation(); handleSendToChat(folder); }}>
                  <img src="/workspace/upload.png" alt="Send" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Edit Modal */}
      {editingFolder && (
        <div className="edit-modal">
          <FileManager
            folders={folders}
            setFolders={setFolders}
            isEditMode={true}
            folderToEdit={editingFolder}
            onSaveEdit={handleSaveEdit}
          />
        </div>
      )}
    </div>
  );
}
