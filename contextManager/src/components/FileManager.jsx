import { useState } from "react";
import '../styles/filemanager.scss';

export default function FileManager() {
  const [files, setFiles] = useState([]);
  const [activeFile, setActiveFile] = useState(null);
  const [highlighterActive, setHighlighterActive] = useState(false);

  //add file 
  const handleAddFile = async () => {
    setHighlighterActive(false);
    const selectedFiles = await window.electronAPI.openFile();
    if (selectedFiles && selectedFiles.length > 0) {
      setFiles((prev) => {
        const newFiles = selectedFiles.filter(
          (f) => !prev.some((file) => file.path === f.path)
        );
        const updatedFiles = [...prev, ...newFiles];
        if (!activeFile && newFiles.length > 0) {
          setActiveFile(newFiles[0].path);
        }
        return updatedFiles;
      });
    }
  };

  //close file tab
  const handleCloseFile = (pathToRemove) => {
    setFiles((prev) => {
      const filtered = prev.filter((file) => file.path !== pathToRemove);
      if (activeFile === pathToRemove) {
        setActiveFile(filtered.length > 0 ? filtered[0].path : null);
      }
      return filtered;
    });
  };

  //toggle highlighter
  const toggleHighlighter = () => {
    setHighlighterActive((prev) => !prev);
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
            className={highlighterActive ? "active-tool" : ""}
            onClick={toggleHighlighter}
          >
            <img src="/workspace/highlighter.png" alt="Highlight" />
          </button>
          <button >
            <img src="/workspace/save.png" alt="Save" />
          </button>
          <button >
            <img src="/workspace/trash.png" alt="Delete" />
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
        <div className="file-editor">
          {activeFileContent ? (
            <p>{activeFileContent.content}</p>
          ) : (
            <p className="empty-editor">No file selected.</p>
          )}
        </div>
      </div>

      {/* Context manager */}
      <div className="context-manager">

      </div>
    </div>
  );
}
