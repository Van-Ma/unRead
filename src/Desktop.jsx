import React, { useRef, useState, useEffect } from "react";

export default function Desktop({ files, setFiles }) {
  const desktopRef = useRef(null);

  const [draggingId, setDraggingId] = useState(null);
  const dragOffset = useRef({ x: 0, y: 0 });

  function onMouseDown(e, id) {
    e.preventDefault();
    setDraggingId(id);
    const file = files.find(f => f.id === id);
    if (!file) return;
    dragOffset.current = { x: e.clientX - file.x, y: e.clientY - file.y };
  }

  function onMouseMove(e) {
    if (draggingId === null || !desktopRef.current) return;
    const desktopRect = desktopRef.current.getBoundingClientRect();
    let newX = e.clientX - dragOffset.current.x;
    let newY = e.clientY - dragOffset.current.y;
    const iconSize = 50;
    newX = Math.min(Math.max(0, newX), desktopRect.width - iconSize);
    newY = Math.min(Math.max(0, newY), desktopRect.height - iconSize);
    setFiles(prev =>
      prev.map(f => (f.id === draggingId ? { ...f, x: newX, y: newY } : f))
    );
  }

  function onMouseUp() {
    setDraggingId(null);
  }

  useEffect(() => {
    if (draggingId !== null) {
      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
    } else {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    }
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [draggingId]);

  useEffect(() => {
  function handleResize() {
    if (!desktopRef.current) return;

    const desktopRect = desktopRef.current.getBoundingClientRect();
    const iconSize = 50;
    const maxX = desktopRect.width - iconSize;
    const maxY = desktopRect.height - iconSize;

    setFiles(prevFiles => 
      prevFiles.map(file => {
        let newX = file.x;
        let newY = file.y;

        // Clamp positions to stay within new container bounds
        if (newX > maxX) newX = maxX;
        if (newY > maxY) newY = maxY;

        if (newX < 0) newX = 0;
        if (newY < 0) newY = 0;

        return { ...file, x: newX, y: newY };
      })
    );
  }

  window.addEventListener('resize', handleResize);

  // Run once on mount to ensure no overflow initially
  handleResize();

  return () => window.removeEventListener('resize', handleResize);
}, [setFiles]);

  
  return (
   <div
  ref={desktopRef}
  className="dashboard-desktop-inner"
  style={{
    position: "relative",    
    width: "100%",            
    height: "100%",  
    overflow: "hidden",     
  }}
>
  {files.map(file => (
    <img
      key={file.id}
      src={file.image}
      alt="file icon"
      className="desktop-images"
      style={{
        position: "absolute",
        left: file.x,
        top: file.y,
        cursor: "grab",
        userSelect: "none",
      }}
      onMouseDown={e => onMouseDown(e, file.id)}
      draggable={false}
    />
  ))}
</div>
  );
}
 