import { useEffect, useState } from "react";
import ContextManager from "./ContextManager";

export default function FileManager({
  folders,
  setFolders,
  activeFolderId,
  setActiveFolderId
}) {
  const [files, setFiles] = useState([]);
  const [activeFile, setActiveFile] = useState(null);
  const [activeTool, setActiveTool] = useState(null);
  const [contextName, setContextName] = useState("");
  const [selectedContexts, setSelectedContexts] = useState([]);

  // sync active folder
  useEffect(() => {
    if (activeFolderId !== null) {
      const folder = folders.find(f => f.id === activeFolderId);
      if (folder) {
        setSelectedContexts(folder.snippets || []);
        setContextName(folder.name || "");
        if (folder.filePath) setActiveFile(folder.filePath);
      }
    } else {
      setSelectedContexts([]);
      setContextName("");
    }
  }, [activeFolderId, folders]);

  // file handling
  const handleAddFile = async () => {
    setActiveTool(null);
    const selectedFiles = await window.electronAPI.openFile();
    if (!selectedFiles || selectedFiles.length === 0) return;

    setFiles(prev => {
      const newFiles = selectedFiles.filter(f => !prev.some(file => file.path === f.path));
      if (!activeFile && newFiles.length > 0) setActiveFile(newFiles[0].path);
      return [...prev, ...newFiles];
    });
  };

  const handleCloseFile = (pathToRemove) => {
    setFiles(prev => {
      const filtered = prev.filter(f => f.path !== pathToRemove);
      if (activeFile === pathToRemove) setActiveFile(filtered.length > 0 ? filtered[0].path : null);
      return filtered;
    });
  };

  // highlighted context
  const handleTextSelection = () => {
    if (activeTool !== "highlight") return;

    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;

    const text = selection.toString().trim();
    if (!text) return;

    setSelectedContexts(prev => {
      const newContexts = [...prev, text];

      // update when text added
      if (activeFolderId !== null) {
        setFolders(foldersPrev =>
          foldersPrev.map(f =>
            f.id === activeFolderId ? { ...f, snippets: newContexts } : f
          )
        );
      }

      return newContexts;
    });

    selection.removeAllRanges();
  };

  const highlightText = (text) => {
    if (selectedContexts.length === 0) return text;

    let parts = [text];
    selectedContexts.forEach(snippet => {
      const newParts = [];
      parts.forEach(part => {
        if (typeof part === "string") {
          const split = part.split(snippet);
          split.forEach((s, i) => {
            newParts.push(s);
            if (i < split.length - 1) {
              newParts.push(
                <mark key={Math.random()} style={{ backgroundColor: "#FFBE48" }}>
                  {snippet}
                </mark>
              );
            }
          });
        } else newParts.push(part);
      });
      parts = newParts;
    });

    return parts;
  };

  const removeContextSnippet = (indexToRemove) => {
    setSelectedContexts(prev => {
      const newContexts = prev.filter((_, idx) => idx !== indexToRemove);

      // update when removed
      if (activeFolderId !== null) {
        setFolders(foldersPrev =>
          foldersPrev.map(f =>
            f.id === activeFolderId ? { ...f, snippets: newContexts } : f
          )
        );
      }

      return newContexts;
    });
  };

  const handleAddContext = () => {
    const newFolder = {
      id: Date.now(),
      name: "New",
      snippets: [],
      filePath: activeFile || null,
      isPlaceholder: true
    };

    setFolders(prev => [...prev, newFolder]);
    setActiveFolderId(newFolder.id);
    setSelectedContexts([]);
    setContextName("");
    setActiveTool(null);
  };

const createFolder = () => {
  if (activeFolderId) {
    setFolders(prev =>
      prev.map(f =>
        f.id === activeFolderId
          ? {
              ...f,
              name: contextName.trim() || "New",
              snippets: selectedContexts,
              filePath: activeFile || null,
              isPlaceholder: false
            }
          : f
      )
    );
  } else {
    const newFolder = {
      id: Date.now(),
      name: contextName.trim() || "New",
      snippets: selectedContexts,
      filePath: activeFile || null,
      isPlaceholder: false
    };
    setFolders(prev => [...prev, newFolder]);
    setActiveFolderId(newFolder.id);
  }

  setContextName("");
  setSelectedContexts([]);
};




  const handleContextSubmit = (e) => {
    if (e.key === "Enter") createFolder();
  };

  const handleFolderClick = (snippets, folderId, filePath) => {
    if (folderId === null) {
      setActiveFolderId(null);
      setSelectedContexts([]);
      setContextName("");
      return;
    }

    setActiveFolderId(folderId);

    if (filePath) {
      const existingFile = files.find(f => f.path === filePath);
      if (existingFile) {
        setActiveFile(filePath);
        setSelectedContexts(snippets || []);
      } else {
        window.electronAPI.readFile(filePath)
          .then(content => {
            setFiles(prev => [...prev, { path: filePath, content }]);
            setActiveFile(filePath);
            setSelectedContexts(snippets || []);
          });
      }
    } else {
      setSelectedContexts(snippets || []);
    }
  };

  const handleDeleteFolder = (folderId) => {
    setFolders(prev => prev.filter(f => f.id !== folderId));
    if (activeFolderId === folderId) {
      setActiveFolderId(null);
      setSelectedContexts([]);
      setContextName("");
    }
  };

  // tool selection
  const toggleTool = (toolName) => {
    setActiveTool(prev => prev === toolName ? null : toolName);
  };

  const activeFileContent = files.find(f => f.path === activeFile);

  return (
    <div className="file-page">
      <div className="file-manager">
        {/* toolbar */}
        <div className="file-toolbar">
          <div className="tooltip">
            <button onClick={handleAddFile}>
              <img src="/workspace/upload2.png" alt="Add File" />
            </button>
            <span className="tooltip-text">Upload a file</span>
          </div>

          <div className="tooltip">
            <button
              className={activeTool === "highlight" ? "active-tool" : ""}
              onClick={() => toggleTool("highlight")}
            >
              <img src="/workspace/highlighter.png" alt="Highlight" />
            </button>
            <span className="tooltip-text">Highlight selected text</span>
          </div>

          <div className="tooltip">
            <button
              className={activeTool === "edit" ? "active-tool" : ""}
              onClick={() => toggleTool("edit")}
            >
              <img src="/workspace/read.png" alt="Context" />
            </button>
            <span className="tooltip-text">Edit context</span>
          </div>


        </div>

        {/* tabs */}
        <div className="file-tabs">
          {files.map(file => {
            const fileName = file.path.split(/[/\\]/).pop();
            return (
              <div
                key={file.path}
                className={`file-tab ${activeFile === file.path ? "active" : ""}`}
              >
                <span className="tab-text" onClick={() => setActiveFile(file.path)}>
                  {fileName}
                </span>
                <button className="close-tab" onClick={() => handleCloseFile(file.path)}>
                  ×
                </button>
              </div>
            );
          })}
        </div>

        {/* editor */}
        <div className="file-editor" onMouseUp={handleTextSelection}>
          {activeFileContent ? (
            <p>{highlightText(activeFileContent.content)}</p>
          ) : (
            <p className="empty-editor">Upload a file.</p>
          )}
        </div>
      </div>

      {/* context manager */}
      <div className="context-creation">
        <div className="context-manager">
          <ContextManager
            folders={folders}
            activeTab="files"
            activeFolderId={activeFolderId}
            onFolderClick={handleFolderClick}
            onDeleteFolder={handleDeleteFolder}
            onAddContext={handleAddContext}
          />

          {/* context */}
          <div className="context-content">
            <div className="context-directory">
              <input
                type="text"
                placeholder="Name this context…"
                value={contextName}
                onChange={e => setContextName(e.target.value)}
                onBlur={() => {
                  // Update folder name live while typing
                  if (activeFolderId !== null) {
                    setFolders(prev =>
                      prev.map(f =>
                        f.id === activeFolderId ? { ...f, name: contextName } : f
                      )
                    );
                  }
                }}
                onKeyDown={handleContextSubmit} // handles Enter key
              />
              <button
                onClick={() => {
                  if (activeFolderId !== null) {
                    // finalize the placeholder folder
                    createFolder();
                  }
                }}
              >
                <img src="/workspace/folder.png" alt="context" />
              </button>
            </div>


            <div className="selected-text">
              {selectedContexts.length === 0 ? (
                <p className="empty-context">Use the highlighter tool to select text for context.</p>
              ) : (
                selectedContexts.map((text, idx) => (
                  <div key={idx} className="context-snippet">
                    <span>{text}</span>
                    <button className="close-snippet" onClick={() => removeContextSnippet(idx)}>×</button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
