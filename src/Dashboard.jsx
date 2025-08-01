import './dashboard.scss';
import { useRef, useState } from "react";
import Desktop from "./Desktop";

function Dashboard({ section, onBack }) {
    const textareaRef = useRef(null);
    const [leftActive, setLeftActive] = useState(false);
    const [addFilesTrigger, setAddFilesTrigger] = useState(0);
    const [files, setFiles] = useState([]);
    const desktopRef = useRef(null); 



    const toggleLeftPanel = () => {
        setLeftActive(prev => !prev);
    };


    const handleInput = () => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = "auto";
            textarea.style.height = Math.min(textarea.scrollHeight, 300) + "px";
        }
    };

      // Called when drop area clicked -> add a file
  const handleDropAreaClick = () => {
    addFile();
  };

  // Add a file with random position & cycling image
  const addFile = () => {
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
      "file5.png"
    ];

    const img = fileImages[files.length % fileImages.length];
    const randomX = Math.floor(Math.random() * maxX);
    const randomY = Math.floor(Math.random() * maxY);

    setFiles(prev => [
      ...prev,
      {
        id: Date.now() + Math.random(),
        image: img,
        x: randomX,
        y: randomY
      }
    ]);
  };

    // ✅ This is the organize-to-grid logic
    const organizeFilesInGrid = () => {
        const desktop = document.querySelector(".dashboard-desktop-inner");
        if (!desktop) return;

        const iconSize = 50;
        const padding = 10;
        const gap = 20;

        const desktopRect = desktop.getBoundingClientRect();
        const maxColumns = Math.floor((desktopRect.width - padding * 2) / (iconSize + gap));

        let x = padding;
        let y = padding;
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
                    <button id="back-btn" onClick={onBack}><svg xmlns="http://www.w3.org/2000/svg" width="25" height="25" fill="currentColor" class="bi bi-arrow-left-short" viewBox="0 0 16 16">
                        <path fill-rule="evenodd" d="M12 8a.5.5 0 0 1-.5.5H5.707l2.147 2.146a.5.5 0 0 1-.708.708l-3-3a.5.5 0 0 1 0-.708l3-3a.5.5 0 1 1 .708.708L5.707 7.5H11.5a.5.5 0 0 1 .5.5" />
                    </svg></button>
                    <button id="forward-btn"><svg xmlns="http://www.w3.org/2000/svg" width="25" height="25" fill="currentColor" class="bi bi-arrow-right-short" viewBox="0 0 16 16">
                        <path fill-rule="evenodd" d="M4 8a.5.5 0 0 1 .5-.5h5.793L8.146 5.354a.5.5 0 1 1 .708-.708l3 3a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708-.708L10.293 8.5H4.5A.5.5 0 0 1 4 8" />
                    </svg></button>
                </div>
            </nav>

            {/* file layout */}
            {section === 'new' && (

                <div className="dashboard-layout">
                    {/* Dashboard Desktop - will be full width below on 701-1000px */}
                    <div className="dashboard-container">
                        <div className="desktop-tools">
                            <button id="organize-btn" onClick={organizeFilesInGrid}>
                                <img src="organizetool.png" alt="Organize Files" />
                            </button>
                             <button id="trash-btn">
                                <img src="trash.png" alt="Remove Files" />
                            </button>
                        </div>
                        <div className="dashboard-desktop">
                       <Desktop files={files} setFiles={setFiles} />
                    </div>
                    </div>
              

                    {/* Container holding left and right panels side by side */}
                    <div className="dashboard-content-layout">
                        {/* Left panel */}
                        <div
                            className={`dashboard-left ${leftActive ? 'active' : ''}`}
                            onClick={toggleLeftPanel}
                        >
                            <div className="dashboard-droparea" onClick={handleDropAreaClick}>
                                <p>drag and drop or click to upload files.</p>
                                <img id="brain-logo" src="brain2.png" alt="brain logo" />
                            </div>
                            <div className="dashboard-fileoutput">
                                <div className="file-output-header">
                                    <p>filename</p>
                                    <button id="file-exit-btn">
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            width="25"
                                            height="25"
                                            fill="currentColor"
                                            className="bi bi-x"
                                            viewBox="0 0 16 16"
                                        >
                                            <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708" />
                                        </svg>
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Right panel */}
                        <div className="dashboard-right">
                            <div className="dashboard-chatoutput"></div>
                            <div className="dashboard-controls">
                                <textarea
                                    ref={textareaRef}
                                    id="chat-inputbox"
                                    placeholder="Ask AI anything..."
                                    rows={1}
                                    onInput={handleInput}
                                ></textarea>
                                <button id="chat-send-btn">Send</button>
                            </div>
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