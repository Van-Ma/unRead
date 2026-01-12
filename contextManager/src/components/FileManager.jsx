import { useState } from "react";
import '../styles/filemanager.scss';

export default function FileManager({ folders, setFolders }) {
  const [files, setFiles] = useState([]);
  const [activeFile, setActiveFile] = useState(null);
  const [activeTool, setActiveTool] = useState(null);
  const [contextName, setContextName] = useState("");
  const [selectedContexts, setSelectedContexts] = useState([]);

  // add file
  const handleAddFile = async () => {
    setActiveTool(null);
    const selectedFiles = await window.electronAPI.openFile();
    if (selectedFiles && selectedFiles.length > 0) {
      setFiles((prev) => {
        const newFiles = selectedFiles.filter(
          (f) => !prev.some((file) => file.path === f.path)
        );
        if (!activeFile && newFiles.length > 0) {
          setActiveFile(newFiles[0].path);
        }
        return [...prev, ...newFiles];
      });
    }
  };

  // text selection
  const handleTextSelection = () => {
    if (activeTool !== "highlight") return;

    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;

    const text = selection.toString().trim();
    if (!text) return;

    setSelectedContexts((prev) => [...prev, text]);
    selection.removeAllRanges();
  };

  // highlight text in editor
  const highlightText = (text) => {
    const allSnippets = [...folders.flatMap(f => f.snippets), ...selectedContexts];
    if (allSnippets.length === 0) return text;

    let parts = [text];
    allSnippets.forEach((snippet) => {
      const newParts = [];
      parts.forEach((part) => {
        if (typeof part === "string") {
          const split = part.split(snippet);
          split.forEach((s, i) => {
            newParts.push(s);
            if (i < split.length - 1) {
              newParts.push(
                <mark key={Math.random()} style={{ backgroundColor: "#FDA912" }}>
                  {snippet}
                </mark>
              );
            }
          });
        } else {
          newParts.push(part);
        }
      });
      parts = newParts;
    });

    return parts;
  };

  // remove selected snippet
  const removeContextSnippet = (indexToRemove) => {
    setSelectedContexts((prev) =>
      prev.filter((_, idx) => idx !== indexToRemove)
    );
  };

  // submit context 
  const createFolder = () => {
    if (!contextName.trim() || selectedContexts.length === 0) return;

    const newFolder = {
      id: Date.now(),
      name: contextName.trim(),
      snippets: selectedContexts,
      color: "#FDA912",
    };

    // Use setFolders from App
    setFolders((prev) => [...prev, newFolder]);
    setContextName("");
    setSelectedContexts([]);
  };

  const handleContextSubmit = (e) => {
    if (e.key === "Enter") createFolder();
  };




  // close file tab
  const handleCloseFile = (pathToRemove) => {
    setFiles((prev) => {
      const filtered = prev.filter((file) => file.path !== pathToRemove);
      if (activeFile === pathToRemove) {
        setActiveFile(filtered.length > 0 ? filtered[0].path : null);
      }
      return filtered;
    });
  };

  // toggle active tool
  const toggleTool = (toolName) => {
    setActiveTool((prev) => (prev === toolName ? null : toolName));
  };

  const activeFileContent = files.find((f) => f.path === activeFile);

  return (
    <div className="file-page">
      <div className="file-manager">
        {/* Toolbar */}
        <div className="file-toolbar">
          <button onClick={handleAddFile}>
            <img src="/workspace/addfile2.png" alt="Add File" />
          </button>
          <button
            className={activeTool === "highlight" ? "active-tool" : ""}
            onClick={() => toggleTool("highlight")}
          >
            <img src="/workspace/highlighter.png" alt="Highlight" />
          </button>
          <button
            className={activeTool === "edit" ? "active-tool" : ""}
            onClick={() => toggleTool("edit")}
          >
            <img src="/workspace/read.png" alt="context" />
          </button>
        </div>

        {/* Tabs */}
        <div className="file-tabs">
          {files.map((file) => {
            const fileName = file.path.split(/[/\\]/).pop();
            return (
              <div
                key={file.path}
                className={`file-tab ${activeFile === file.path ? "active" : ""}`}
              >
                <span className="tab-text" onClick={() => setActiveFile(file.path)}>
                  {fileName}
                </span>
                <button className="close-tab" onClick={() => handleCloseFile(file.path)}>×</button>
              </div>
            );
          })}
        </div>

        {/* Editor */}
        <div className="file-editor" onMouseUp={handleTextSelection}>
          {activeFileContent ? (
            <p>{highlightText(activeFileContent.content)}</p>
          ) : (
            <p className="empty-editor">No file selected.</p>
          )}
        </div>
      </div>

      {/* Context Creation */}
      <div className="context-creation">
        <div className="context-directory">
          <input
            type="text"
            placeholder="Name this context…"
            value={contextName}
            onChange={(e) => setContextName(e.target.value)}
            onKeyDown={handleContextSubmit}
          />
          <button onClick={createFolder}>
            <img src="/workspace/folder.png" alt="context" />
          </button>
        </div>

        <div className="selected-text">
          {selectedContexts.length === 0 ? (
            <p className="empty-context">No context selected.</p>
          ) : (
            selectedContexts.map((text, idx) => (
              <div key={idx} className="context-snippet">
                <span>{text}</span>
                <button
                  className="close-snippet"
                  onClick={() => removeContextSnippet(idx)}
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
