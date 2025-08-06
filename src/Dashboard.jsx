import './dashboard.scss';
import { useRef, useState } from "react";
import Desktop from './Desktop';
import Chat from './Chat';
import { createFileObject } from './ContentFiles';
function cleanFileContent(rawContent) {
    const isBinary = /[\x00-\x08\x0E-\x1F\x7F-\x9F]/g.test(rawContent);

    if (isBinary) {
        return "(Unsupported or binary file format)";
    }

    return rawContent
        .replace(/\x00/g, '') // remove null characters
        .replace(/\r\n/g, '\n') // normalize line endings
        .trim();
}
const isTextFile = (fileName) => {
    const textExtensions = ['.txt', '.md', '.csv', '.json', '.js', '.html', '.css', '.xml', '.log'];
    const ext = fileName.slice(fileName.lastIndexOf('.')).toLowerCase();
    return textExtensions.includes(ext);
};

function Dashboard({ section, onBack }) {
    const [files, setFiles] = useState([]);
    const trashRef = useRef(null);
    const fileInputRef = useRef(null);
    const [selectedFile, setSelectedFile] = useState(null); //

    const handleFileSelect = (file) => {
        setSelectedFile(file);
    };

    const handleDropAreaClick = () => {
        if (fileInputRef.current) {
            fileInputRef.current.value = null;
            fileInputRef.current.click();
        }
    };

    const handleFileChange = (e) => {
        const selectedFiles = e.target.files;
        if (!selectedFiles || selectedFiles.length === 0) return;

        const desktop = document.querySelector(".dashboard-desktop-inner");
        if (!desktop) return;

        const desktopRect = desktop.getBoundingClientRect();
        const iconSize = 50;
        const maxX = desktopRect.width - iconSize;
        const maxY = desktopRect.height - iconSize;

        const fileImages = [
            "file1.png",
            "file2.png",
            "file3.png",
            "file4.png",
            "file5.png",
        ];

        Array.from(selectedFiles).forEach((file) => {
            const reader = new FileReader();

            reader.onload = (event) => {
                let content = event.target.result;
                let isBinary = false;

                // For PDF and other binary files, mark isBinary = true and don't show raw content
                if (
                    file.type === "application/pdf" ||
                    file.type === "application/msword" ||
                    file.type ===
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ) {
                    isBinary = true;
                    content = null; // or keep ArrayBuffer if needed elsewhere
                }

                const randomX = Math.floor(Math.random() * maxX);
                const randomY = Math.floor(Math.random() * maxY);

                const projectId = "project-uuid-123";

                const newFile = createFileObject(projectId, file.name, content, fileImages);
                newFile.x = randomX;
                newFile.y = randomY;
                newFile.isBinary = isBinary; // add flag

                setFiles((prev) => [...prev, newFile]);
            };

            // Read file accordingly
            if (
                file.type.startsWith("text") ||
                file.name.endsWith(".json") ||
                file.name.endsWith(".md") ||
                file.name.endsWith(".txt") ||
                file.name.endsWith(".csv") ||
                file.name.endsWith(".html")
            ) {
                reader.readAsText(file);
            } else {
                reader.readAsArrayBuffer(file); // binary file
            }
        });
    };




    // ✅ This is the organize-to-grid logic
    const organizeFilesInGrid = () => {
        const desktop = document.querySelector(".dashboard-desktop-inner");
        if (!desktop) return;

        const iconSize = 50;
        const padding = 20;
        const gap = 50;
        const toolbarHeight = 100; // Add this!

        const desktopRect = desktop.getBoundingClientRect();
        const maxColumns = Math.floor((desktopRect.width - padding * 2) / (iconSize + gap));

        let x = padding;
        let y = padding + toolbarHeight; // Add toolbarHeight here to push icons down
        let col = 0;

        const updated = files.map(file => {
            const updatedFile = { ...file, x, y };

            col++;
            if (col >= maxColumns) {
                col = 0;
                x = padding;
                y += iconSize + gap;
            } else {
                x += iconSize + gap;
            }

            return updatedFile;
        });

        setFiles(updated);
    };



    return (
        <div className="dashboard-page">
            <nav className="dashboard-nav-container">
                <div className="dashboard-nav-btns">
                    <button onClick={onBack} id="back-btn"><img src="leftarrow.png"></img></button>
                    <button id="forward-btn" ><img src="rightarrow.png"></img></button>

                </div>
            </nav>

            {/* file layout */}
            {section === 'new' && (

                <div className="dashboard-layout">
                    {/* Dashboard Desktop - will be full width below on 701-1000px */}
                    <div className="dashboard-container">
                        <div className="dashboard-droparea">
                            <img id="brain-logo" src="brain2.png" alt="brain logo" />
                        </div>
                        {/* Desktop area with toggleable visibility */}
                        <div className="dashboard-desktop">
                            <input
                                type="file"
                                style={{ display: "none" }}
                                ref={fileInputRef}
                                onChange={handleFileChange}
                                multiple
                                accept=".txt,.pdf,.doc,.docx,.json,.md,.xml,.csv,.html,.js"
                            />
                            <Desktop
                                files={files}
                                setFiles={setFiles}
                                handleDropAreaClick={() => fileInputRef.current?.click()}
                                organizeFilesInGrid={organizeFilesInGrid}
                                trashRef={trashRef}
                                onFileSelect={handleFileSelect}  // pass handler down
                            />
                        </div>
                    </div>


                    {/* Container holding left and right panels side by side */}
                    <div className="dashboard-content-layout">
                        {/* Left panel */}
                        <div className="dashboard-left">
                            <div className="dashboard-fileoutput">
                                <div className="file-output-header">
                                    <p>{selectedFile ? selectedFile.fileName : "No file selected"}</p>
                                    <button id="file-exit-btn" onClick={() => setSelectedFile(null)}>
                                        {/* Close icon */}
                                    </button>
                                </div>
                                <pre
                                    style={{
                                        whiteSpace: "pre-wrap",
                                        wordWrap: "break-word",
                                        padding: "20px",
                                        paddingTop: "50px",
                                        color: "black",
                                        fontFamily: "monospace",
                                        maxHeight: "70vh",
                                        overflowY: "auto",
                                        lineHeight: "1.5",
                                    }}
                                >
                                    {selectedFile
                                        ? isTextFile(selectedFile.fileName)
                                            ? selectedFile.content || "(Empty file)"
                                            : "(Preview not available for this file type)"
                                        : "Select a file to view content"}
                                </pre>
                            </div>
                        </div>

                        {/* Right panel */}
                        <div className="dashboard-right">
                            <Chat />
                        </div>

                    </div>
                </div>
            )}

            {/*{section === 'open' && (
               
            )}*/}
        </div>
    );
}

export default Dashboard;