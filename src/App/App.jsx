import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import { Rnd } from "react-rnd";
import "./App.scss";
import FileManager from '../Features/FileManager';

function App() {
  const [zOrder, setZOrder] = useState(["fm", "fe", "chat"]);
  const baseZIndex = 10;
  const [showFileManager, setShowFileManager] = useState(false);

  const bringToFront = (id) => {
    setZOrder((prev) => [...prev.filter((w) => w !== id), id]);
  };

  const getZIndex = (id) => baseZIndex + zOrder.indexOf(id);

  const resizeHandleStyles = {
    top: { cursor: "ns-resize" },
    bottom: { cursor: "ns-resize" },
    left: { cursor: "ew-resize" },
    right: { cursor: "ew-resize" },
    topLeft: { cursor: "nwse-resize" },
    topRight: { cursor: "nesw-resize" },
    bottomLeft: { cursor: "nesw-resize" },
    bottomRight: { cursor: "nwse-resize" },
  };

  const commonProps = {
    bounds: "parent",
    dragHandleClassName: "window-header",
    minWidth: 200,
    minHeight: 150,
    resizeHandleStyles,
    enableResizing: {
      top: true,
      right: true,
      bottom: true,
      left: true,
      topRight: true,
      bottomRight: true,
      bottomLeft: true,
      topLeft: true,
    },
  };

  return (
    <div className="app-page">
      <header className="app-header">
        <img id="brain-logo" src="brain2.png"></img>
      </header>
      <nav className="app-toolbar">
        <button
          id="file-manager-btn"
          onClick={() => setShowFileManager(!showFileManager)}
        >
          <img src="wrench.png" alt="File Manager" />
        </button>
      </nav>
      <div className={`file-manager-container ${showFileManager ? "open" : ""}`}>
        <FileManager />
      </div>
      {/* File Editor */}
      <Rnd
        default={{
          x: 350,
          y: 100,
          width: 400,
          height: 300,
        }}
        {...commonProps}
        style={{ zIndex: getZIndex("fe"), position: "absolute" }}
        onMouseDown={() => bringToFront("fe")}
      >
        <div className="window">
          <div className="window-header">File Editor</div>
          <div className="window-content">Your file editor content...</div>
        </div>
      </Rnd>

      {/* Chat */}
      <Rnd
        default={{
          x: 800,
          y: 50,
          width: 300,
          height: 250,
        }}
        {...commonProps}
        style={{ zIndex: getZIndex("chat"), position: "absolute" }}
        onMouseDown={() => bringToFront("chat")}
      >
        <div className="window">
          <div className="window-header">Chat Manager</div>
          <div className="window-content">Your chat content...</div>
        </div>
      </Rnd>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
