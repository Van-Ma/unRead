import React, { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';

/**
 * Creates a new file object tied to a project
 * @param {string} projectId - The UUID of the current project
 * @param {string} fileName - Name of the file
 * @param {string} fileContent - Optional content of the file
 * @param {string[]} imageArray - Array of file icon image paths
 * @returns {object} file object
 */
export function createFileObject(projectId, fileName, fileContent = '', imageArray = []) {
  const randomImage = imageArray[Math.floor(Math.random() * imageArray.length)];

  return {
    projectId,
    id: uuidv4(),               // file ID
    fileName: fileName || 'Untitled.txt',
    content: fileContent,
    image: randomImage,
    x: 100 + Math.floor(Math.random() * 150),  // default/randomized position
    y: 100 + Math.floor(Math.random() * 150),
  };
}

export function DesktopFile({ file, onMouseDown, onRename, onDelete }) {
  const [showMenu, setShowMenu] = useState(false);
  const [menuPos, setMenuPos] = useState({ x: 0, y: 0 });
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState(file.fileName);

  const handleContextMenu = (e) => {
    e.preventDefault();
    setShowMenu(true);
    setMenuPos({ x: e.clientX, y: e.clientY });
  };

  const handleRename = () => {
    setShowMenu(false);
    setIsEditing(true);
  };

  const handleDelete = () => {
    setShowMenu(false);
    onDelete(file.id);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onRename(file.id, editedName.trim() || "Untitled.txt");
    setIsEditing(false);
  };

  return (
    <>
      <div
        style={{
          position: "absolute",
          left: file.x,
          top: file.y,
          width: 80,
          textAlign: "center",
          zIndex: 20,
          cursor: "pointer",
        }}
        onMouseDown={(e) => onMouseDown(e, file.id)}
        onContextMenu={handleContextMenu}
      >
        <img
          src={file.image}
          alt="file"
          draggable={false}
          style={{ width: 50, height: 50, pointerEvents: "none"}}
        />
        {isEditing ? (
          <form onSubmit={handleSubmit}>
            <input
              value={editedName}
              autoFocus
              onBlur={() => setIsEditing(false)}
              onChange={(e) => setEditedName(e.target.value)}
              style={{
                width: 70,
                fontSize: 12,
                marginTop: 2,
                textAlign: "center",
              }}
            />
          </form>
        ) : (
          <div style={{ fontSize: 12, marginTop: 4, color: "white", fontFamily:"monospace" }}>{file.fileName}</div>
        )}
      </div>

      {showMenu && (
        <div
          style={{
            position: "fixed",
            top: menuPos.y,
            left: menuPos.x,
            background: "white",
            border: "1px solid #ccc",
            zIndex: 1000,
            boxShadow: "0 2px 5px rgba(0,0,0,0.2)",
          }}
          onMouseLeave={() => setShowMenu(false)}
        >
          <div style={menuItemStyle} onClick={handleRename}>Rename</div>
          <div style={menuItemStyle} onClick={handleDelete}>Delete</div>
        </div>
      )}
    </>
  );
}

const menuItemStyle = {
  padding: "6px 12px",
  cursor: "pointer",
  fontSize: "14px",
  borderBottom: "1px solid #eee",
};
