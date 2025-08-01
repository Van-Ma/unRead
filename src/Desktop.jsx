 import React, { useRef, useState, useEffect } from "react"; 
 import { DesktopFile } from './ContentFiles';

export default function Desktop({ files, setFiles, trashRef, organizeFilesInGrid, handleDropAreaClick}) {
  const desktopRef = useRef(null);
  const originalPosition = useRef({x: 0, y: 0});

  const [draggingId, setDraggingId] = useState(null);
  const dragOffset = useRef({ x: 0, y: 0 });

function onMouseDown(e, id) {
  e.preventDefault();
  setDraggingId(id);
  const file = files.find(f => f.id === id);
  if (!file) return;
  dragOffset.current = { x: e.clientX - file.x, y: e.clientY - file.y };
  originalPosition.current = { x: file.x, y: file.y }; // Save original
}
function onMouseMove(e) {
  if (draggingId === null || !desktopRef.current) return;
  const desktopRect = desktopRef.current.getBoundingClientRect();
  const iconSize = 50;

  let newX = e.clientX - dragOffset.current.x;
  let newY = e.clientY - dragOffset.current.y;

  // Allow movement above the top, but restrict left/right/bottom
  newX = Math.min(Math.max(0, newX), desktopRect.width - iconSize);
  newY = Math.min(newY, desktopRect.height - iconSize); // can go above 0

  setFiles(prev =>
    prev.map(f => (f.id === draggingId ? { ...f, x: newX, y: newY } : f))
  );
}
function onMouseUp(e) {
  if (draggingId !== null) {
    const file = files.find(f => f.id === draggingId);
    if (!file) return;

    let isOverTrash = false;
    let isOverToolbar = false;

    if (trashRef?.current) {
      const trashRect = trashRef.current.getBoundingClientRect();
      const mouseX = e.clientX;
      const mouseY = e.clientY;

      isOverTrash =
        mouseX >= trashRect.left &&
        mouseX <= trashRect.right &&
        mouseY >= trashRect.top &&
        mouseY <= trashRect.bottom;
    }

    // Get toolbar area rect
    const desktop = desktopRef.current;
    if (desktop) {
      const toolbar = desktop.querySelector(".desktop-tools");
      if (toolbar) {
        const toolbarRect = toolbar.getBoundingClientRect();
        const mouseX = e.clientX;
        const mouseY = e.clientY;
        // Check if mouse is within toolbar area, but NOT over trash
        if (
          mouseX >= toolbarRect.left &&
          mouseX <= toolbarRect.right &&
          mouseY >= toolbarRect.top &&
          mouseY <= toolbarRect.bottom &&
          !isOverTrash
        ) {
          isOverToolbar = true;
        }
      }
    }

    if (isOverTrash) {
      // Delete file
      setFiles(prev => prev.filter(f => f.id !== draggingId));
    } else if (isOverToolbar) {
      // Revert to original position, don't allow dropping files on toolbar except trash
      setFiles(prev =>
        prev.map(f =>
          f.id === draggingId ? { ...f, x: originalPosition.current.x, y: originalPosition.current.y } : f
        )
      );
    } else {
      // drop anywhere else on desktop allowed - do nothing
    }

    setDraggingId(null);
  }
}
useEffect(() => {
  function handleMouseMove(e) {
    onMouseMove(e);
  }

  function handleMouseUp(e) {
    onMouseUp(e);
  }

  if (draggingId !== null) {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  }

  return () => {
    window.removeEventListener("mousemove", handleMouseMove);
    window.removeEventListener("mouseup", handleMouseUp);
  };
}, [draggingId]);


  
 return (
<div
  ref={desktopRef}
  className="dashboard-desktop-inner"
  style={{
    position: "relative",
    width: "100%",
    height: "100%",
    overflowX: "auto",
    overflowY:"auto",
    zIndex: 1,
  }}
>
  {/* Desktop toolbar (without trash) */}
  <div className="desktop-tools" style={{ position: "relative", zIndex: 10 }}>
           <button id="add-btn" onClick={handleDropAreaClick}>
      <img src="addfile2.png" alt="Add File" />
    </button>
    <button id="organize-btn" onClick={organizeFilesInGrid}>
      <img src="organizetool.png" alt="Organize Files" />
    </button>
  </div>

  {/* Trash button placed absolutely on top */}
  <button
    id="trash-btn"
    ref={trashRef}
    style={{
      position: "absolute",
      top: 9,       // adjust as needed
      right: '30px',     // adjust as needed
      zIndex: 1000,

    }}
  >
    <img src="trash2.png" alt="Remove Files"/>
  </button>

  {/* Desktop icons */}
 {files.map(file => (
  <DesktopFile
    key={file.id}
    file={file}
    onMouseDown={onMouseDown}
    onRename={(id, newName) =>
      setFiles(prev => prev.map(f => f.id === id ? { ...f, fileName: newName } : f))
    }
    onDelete={(id) =>
      setFiles(prev => prev.filter(f => f.id !== id))
    }
  />
))}
</div>
);
}