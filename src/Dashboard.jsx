import './dashboard.scss';
import { useRef, useState } from "react";
import Desktop from './Desktop';
import Chat from './Chat';

function Dashboard({ section, onBack }) {

    const [leftActive, setLeftActive] = useState(false);
    const [files, setFiles] = useState([]);
    const desktopRef = useRef(null);
    const trashRef = useRef(null);



    const toggleLeftPanel = () => {
        setLeftActive(prev => !prev);
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
                            <Desktop
                                files={files}
                                setFiles={setFiles}
                                handleDropAreaClick={handleDropAreaClick}
                                organizeFilesInGrid={organizeFilesInGrid}
                                trashRef={trashRef}
                            />

                        </div>
                    </div>


                    {/* Container holding left and right panels side by side */}
                    <div className="dashboard-content-layout">
                        {/* Left panel */}
                        <div className="dashboard-left">
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