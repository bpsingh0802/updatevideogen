// import { useState, useEffect } from 'react';
// import { Sparkles, Loader2, Video, CheckCircle, Download } from 'lucide-react';
// import './App.css';

// const App = () => {
//   const [topicsText, setTopicsText] = useState('');
//   const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
//   const [videoDownloadUrl, setVideoDownloadUrl] = useState('');
//   const [error, setError] = useState('');
//   const [taskId, setTaskId] = useState(null);

//   const serverUrl = 'http://localhost:8000'; // Replace with your VPS IP and port

//   const handleGenerateVideo = async () => {
//     const topics = topicsText.split('\n').map(t => t.trim()).filter(t => t.length > 0);
//     if (topics.length === 0) {
//       setError('Please paste at least one topic.');
//       return;
//     }

//     setIsGeneratingVideo(true);
//     setError('');
//     setVideoDownloadUrl('');
//     setTaskId(null);

//     try {
//       const response = await fetch(`${serverUrl}/generate-bulk-videos`, {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ topics }),
//       });

//       if (!response.ok) {
//         const errResult = await response.json();
//         throw new Error(errResult.error || 'Failed to initiate video generation.');
//       }

//       const { task_id } = await response.json();
//       setTaskId(task_id);
//     } catch (err) {
//       console.error(err);
//       setError(`Failed to start video generation: ${err.message}`);
//       setIsGeneratingVideo(false);
//     }
//   };

//   useEffect(() => {
//     if (!taskId) return;

//     const pollStatus = async () => {
//       try {
//         const response = await fetch(`${serverUrl}/check-status/${taskId}`);
//         if (!response.ok) {
//           const errResult = await response.json();
//           throw new Error(errResult.error || 'Failed to check status.');
//         }

//         const task = await response.json();
//         if (task.status === 'completed') {
//           const downloadResponse = await fetch(`${serverUrl}/download/${taskId}`);
//           if (!downloadResponse.ok) {
//             const errResult = await downloadResponse.json();
//             throw new Error(errResult.error || 'Failed to fetch zip file.');
//           }
//           const blob = await downloadResponse.blob();
//           const url = URL.createObjectURL(blob);
//           setVideoDownloadUrl(url);
//           setIsGeneratingVideo(false);
//         } else if (task.status === 'failed') {
//           throw new Error(task.error || 'Video generation failed.');
//         } else {
//           setTimeout(pollStatus, 2000); // Poll every 2 seconds
//         }
//       } catch (err) {
//         console.error(err);
//         setError(`Error during video generation: ${err.message}`);
//         setIsGeneratingVideo(false);
//       }
//     };

//     pollStatus();
//   }, [taskId]);

//   const handleDownload = async () => {
//     try {
//       await fetch(`${serverUrl}/cleanup/${taskId}`, { method: 'POST' });
//       setTimeout(() => {
//         URL.revokeObjectURL(videoDownloadUrl);
//         setVideoDownloadUrl('');
//         setTaskId(null);
//       }, 1000);
//     } catch (err) {
//       console.error('Cleanup failed:', err);
//     }
//   };

//   return (
//     <div className="min-h-screen bg-gray-900 text-gray-100 p-8 flex flex-col items-center">
//       <div className="w-full max-w-4xl bg-gray-800 rounded-3xl shadow-xl p-8 md:p-12 space-y-8">
//         <header className="flex flex-col items-center text-center space-y-4">
//           <Sparkles className="w-16 h-16 text-sky-400 animate-pulse" />
//           <h1 className="text-4xl md:text-5xl font-extrabold text-white">Bulk Video Generator</h1>
//           <p className="text-lg text-gray-400 max-w-2xl">
//             Paste a list of topics (one per line) to generate a video for each.
//           </p>
//         </header>

//         <main className="space-y-6">
//           <div className="flex flex-col items-center justify-center space-y-4">
//             <textarea
//               value={topicsText}
//               onChange={(e) => setTopicsText(e.target.value)}
//               placeholder="e.g.\nHow to brew coffee at home\nThe history of AI\nTips for running a marathon"
//               rows={6}
//               className="w-full p-4 bg-gray-700 text-white rounded-xl border border-gray-600 focus:border-sky-400 focus:ring-1 focus:ring-sky-400 transition duration-200 resize-none"
//               disabled={isGeneratingVideo}
//             />
//           </div>

//           <button
//             onClick={handleGenerateVideo}
//             className={`w-full py-4 px-6 rounded-xl font-bold text-white transition duration-300 ease-in-out transform
//               ${isGeneratingVideo ? 'bg-indigo-600 cursor-not-allowed' : 'bg-indigo-500 hover:bg-indigo-600 hover:scale-105 active:scale-95'}
//               ${!topicsText ? 'opacity-50 cursor-not-allowed' : ''}`}
//             disabled={!topicsText || isGeneratingVideo}
//           >
//             {isGeneratingVideo ? (
//               <span className="flex items-center justify-center">
//                 <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Generating Videos...
//               </span>
//             ) : (
//               <span className="flex items-center justify-center">
//                 <Video className="mr-2 h-5 w-5" /> Generate Videos
//               </span>
//             )}
//           </button>

//           {error && (
//             <div className="bg-red-500 bg-opacity-20 text-red-300 p-4 rounded-xl border border-red-500 text-sm">
//               <p>{error}</p>
//             </div>
//           )}
//         </main>

//         {videoDownloadUrl && !isGeneratingVideo && (
//           <div className="mt-6">
//             <div className="bg-emerald-500 bg-opacity-20 text-emerald-300 p-4 rounded-xl border border-emerald-500 text-sm flex items-center space-x-2">
//               <CheckCircle size={20} />
//               <p>All videos are ready and compressed into a single zip file.</p>
//             </div>
//             <a
//               href={videoDownloadUrl}
//               download="generated_videos.zip"
//               className="mt-4 w-full py-4 px-6 rounded-xl font-bold text-white transition duration-300 ease-in-out transform flex items-center justify-center bg-emerald-500 hover:bg-emerald-600 hover:scale-105 active:scale-95"
//               onClick={handleDownload}
//             >
//               <Download className="mr-2 h-5 w-5" /> Download Zip File
//             </a>
//           </div>
//         )}
//       </div>
//     </div>
//   );
// };

// export default App;


// import { useState, useEffect } from 'react';
// import { Sparkles, Loader2, Video, CheckCircle, Download, FileImage, LayoutPanelLeft, PictureInPicture } from 'lucide-react';
// import './App.css';

// const App = () => {
//   const [topicsText, setTopicsText] = useState('');
//   // NEW: Two separate states for image files
//   const [sideImageFiles, setSideImageFiles] = useState([]);
//   const [bgImageFiles, setBgImageFiles] = useState([]); 
  
//   const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
//   const [videoDownloadUrl, setVideoDownloadUrl] = useState('');
//   const [error, setError] = useState('');
//   const [taskId, setTaskId] = useState(null);

//   const serverUrl = 'http://localhost:8000'; // Your backend server URL

//   // NEW: Handlers for each file input
//   const handleSideImageChange = (e) => {
//     setSideImageFiles(e.target.files);
//   };
//   const handleBgImageChange = (e) => {
//     setBgImageFiles(e.target.files);
//   };

//   const handleGenerateVideo = async () => {
//     const topics = topicsText.split('\n').map(t => t.trim()).filter(t => t.length > 0);
//     if (topics.length === 0) {
//       setError('Please paste at least one topic.');
//       return;
//     }

//     setIsGeneratingVideo(true);
//     setError('');
//     setVideoDownloadUrl('');
//     setTaskId(null);

//     const formData = new FormData();
//     formData.append('topics', JSON.stringify(topics));

//     // NEW: Append both image lists separately
//     Array.from(sideImageFiles).forEach(file => {
//       formData.append('images_side', file); // Note the name 'images_side'
//     });
//     Array.from(bgImageFiles).forEach(file => {
//       formData.append('images_bg', file); // Note the name 'images_bg'
//     });

//     try {
//       const response = await fetch(`${serverUrl}/generate-bulk-videos`, {
//         method: 'POST',
//         body: formData,
//       });

//       if (!response.ok) {
//         const errResult = await response.json();
//         throw new Error(errResult.error || 'Failed to initiate video generation.');
//       }

//       const { task_id } = await response.json();
//       setTaskId(task_id);
//     } catch (err) {
//       console.error(err);
//       setError(`Failed to start video generation: ${err.message}`);
//       setIsGeneratingVideo(false);
//     }
//   };

//   // ... (useEffect for polling is unchanged) ...
//   useEffect(() => {
//     if (!taskId) return;
//     const pollStatus = async () => {
//       try {
//         const response = await fetch(`${serverUrl}/check-status/${taskId}`);
//         if (!response.ok) throw new Error('Failed to check status.');
//         const task = await response.json();
//         if (task.status === 'completed') {
//           const downloadResponse = await fetch(`${serverUrl}/download/${taskId}`);
//           if (!downloadResponse.ok) throw new Error('Failed to fetch zip file.');
//           const blob = await downloadResponse.blob();
//           const url = URL.createObjectURL(blob);
//           setVideoDownloadUrl(url);
//           setIsGeneratingVideo(false);
//         } else if (task.status === 'failed') {
//           throw new Error(task.error || 'Video generation failed.');
//         } else {
//           setTimeout(pollStatus, 2000);
//         }
//       } catch (err) {
//         console.error(err);
//         setError(`Error during video generation: ${err.message}`);
//         setIsGeneratingVideo(false);
//       }
//     };
//     pollStatus();
//   }, [taskId]);

//   // ... (handleDownload is unchanged) ...
//   const handleDownload = async () => {
//     try {
//       await fetch(`${serverUrl}/cleanup/${taskId}`, { method: 'POST' });
//       setTimeout(() => {
//         URL.revokeObjectURL(videoDownloadUrl);
//         setVideoDownloadUrl('');
//         setTaskId(null);
//       }, 1000);
//     } catch (err) {
//       console.error('Cleanup failed:', err);
//     }
//   };

//   return (
//     <div className="min-h-screen bg-gray-900 text-gray-100 p-8 flex flex-col items-center">
//       <div className="w-full max-w-4xl bg-gray-800 rounded-3xl shadow-xl p-8 md:p-12 space-y-8">
//         <header className="flex flex-col items-center text-center space-y-4">
//           <Sparkles className="w-16 h-16 text-sky-400 animate-pulse" />
//           <h1 className="text-4xl md:text-5xl font-extrabold text-white">Bulk Video Generator</h1>
//           <p className="text-lg text-gray-400 max-w-2xl">
//             Upload images for the slides and for the background/breaks.
//           </p>
//         </header>

//         <main className="space-y-6">
//           <div className="space-y-4">
//             {/* --- 1. Topics Textarea --- */}
//             <label htmlFor="topics-input" className="block text-sm font-medium text-gray-300">
//               1. Paste Your Topics
//             </label>
//             <textarea
//               id="topics-input"
//               value={topicsText}
//               onChange={(e) => setTopicsText(e.target.value)}
//               placeholder="e.g.&#10;How to brew coffee at home&#10;The history of AI"
//               rows={6}
//               className="w-full p-4 bg-gray-700 text-white rounded-xl border border-gray-600 focus:border-sky-400 focus:ring-1 focus:ring-sky-400"
//               disabled={isGeneratingVideo}
//             />

//             {/* --- 2. NEW: Side-by-Side Image Upload --- */}
//             <label className="block text-sm font-medium text-gray-300">
//               2. Upload Side-by-Side Images (Optional)
//             </label>
//             <label
//               htmlFor="side-image-upload"
//               className={`relative flex w-full justify-center p-4 bg-gray-700 text-white rounded-xl border-2 border-dashed border-gray-600 cursor-pointer
//                 ${isGeneratingVideo ? 'opacity-50 cursor-not-allowed' : 'hover:border-sky-400'}
//               `}
//             >
//               <input
//                 id="side-image-upload"
//                 type="file"
//                 multiple
//                 accept="image/*"
//                 onChange={handleSideImageChange}
//                 className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
//                 disabled={isGeneratingVideo}
//               />
//               <div className="flex flex-col items-center space-y-2 text-gray-400">
//                 <LayoutPanelLeft className="w-8 h-8" />
//                 {sideImageFiles.length > 0 ? (
//                   <span className="font-semibold text-sky-300">{sideImageFiles.length} images selected</span>
//                 ) : (
//                   <span>Upload images for the slides</span>
//                 )}
//               </div>
//             </label>

//             {/* --- 3. NEW: Background Image Upload --- */}
//             <label className="block text-sm font-medium text-gray-300">
//               3. Upload Background/Break Images (Optional)
//             </label>
//             <label
//               htmlFor="bg-image-upload"
//               className={`relative flex w-full justify-center p-4 bg-gray-700 text-white rounded-xl border-2 border-dashed border-gray-600 cursor-pointer
//                 ${isGeneratingVideo ? 'opacity-50 cursor-not-allowed' : 'hover:border-sky-400'}
//               `}
//             >
//               <input
//                 id="bg-image-upload"
//                 type="file"
//                 multiple
//                 accept="image/*"
//                 onChange={handleBgImageChange}
//                 className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
//                 disabled={isGeneratingVideo}
//               />
//               <div className="flex flex-col items-center space-y-2 text-gray-400">
//                 <PictureInPicture className="w-8 h-8" />
//                 {bgImageFiles.length > 0 ? (
//                   <span className="font-semibold text-sky-300">{bgImageFiles.length} images selected</span>
//                 ) : (
//                   <span>Upload images for background & breaks</span>
//                 )}
//               </div>
//             </label>
//           </div>

//           {/* --- 4. Generate Button --- */}
//           <button
//             onClick={handleGenerateVideo}
//             className={`w-full py-4 px-6 rounded-xl font-bold text-white transition
//               ${isGeneratingVideo ? 'bg-indigo-600 cursor-not-allowed' : 'bg-indigo-500 hover:bg-indigo-600'}
//               ${!topicsText ? 'opacity-50 cursor-not-allowed' : ''}`}
//             disabled={!topicsText || isGeneratingVideo}
//           >
//             {isGeneratingVideo ? (
//               <span className="flex items-center justify-center">
//                 <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Generating Videos...
//               </span>
//             ) : (
//               <span className="flex items-center justify-center">
//                 <Video className="mr-2 h-5 w-5" /> Generate Videos
//               </span>
//             )}
//           </button>

//           {/* ... (Error and Download sections are unchanged) ... */}
//           {error && (
//             <div className="bg-red-500 bg-opacity-20 text-red-300 p-4 rounded-xl border border-red-500 text-sm">
//               <p>{error}</p>
//             </div>
//           )}
//         </main>

//         {videoDownloadUrl && !isGeneratingVideo && (
//           <div className="mt-6">
//             <div className="bg-emerald-500 bg-opacity-20 text-emerald-300 p-4 rounded-xl border border-emerald-500 text-sm flex items-center space-x-2">
//               <CheckCircle size={20} />
//               <p>All videos are ready and compressed into a single zip file.</p>
//             </div>
//             <a
//               href={videoDownloadUrl}
//               download="generated_videos.zip"
//               className="mt-4 w-full py-4 px-6 rounded-xl font-bold text-white flex items-center justify-center bg-emerald-500 hover:bg-emerald-600"
//               onClick={handleDownload}
//             >
//               <Download className="mr-2 h-5 w-5" /> Download Zip File
//             </a>
//           </div>
//         )}
//       </div>
//     </div>
//   );
// };

// export default App;












import { useState, useEffect } from 'react';
import { Sparkles, Loader2, Video, CheckCircle, Download, FileImage, LayoutPanelLeft, PictureInPicture } from 'lucide-react';
import './App.css';

const App = () => {
  const [topicsText, setTopicsText] = useState('');
  // NEW: Two separate states for image files
  const [sideImageFiles, setSideImageFiles] = useState([]);
  const [bgImageFiles, setBgImageFiles] = useState([]); 
  
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [videoDownloadUrl, setVideoDownloadUrl] = useState('');
  const [error, setError] = useState('');
  const [taskId, setTaskId] = useState(null);

  const serverUrl = 'http://localhost:8000'; // Your backend server URL

  // NEW: Handlers for each file input
  const handleSideImageChange = (e) => {
    setSideImageFiles(e.target.files);
  };
  const handleBgImageChange = (e) => {
    setBgImageFiles(e.target.files);
  };

  const handleGenerateVideo = async () => {
    const topics = topicsText.split('\n').map(t => t.trim()).filter(t => t.length > 0);
    if (topics.length === 0) {
      setError('Please paste at least one topic.');
      return;
    }

    setIsGeneratingVideo(true);
    setError('');
    setVideoDownloadUrl('');
    setTaskId(null);

    const formData = new FormData();
    formData.append('topics', JSON.stringify(topics));

    // NEW: Append both image lists separately
    Array.from(sideImageFiles).forEach(file => {
      formData.append('images_side', file); // Note the name 'images_side'
    });
    Array.from(bgImageFiles).forEach(file => {
      formData.append('images_bg', file); // Note the name 'images_bg'
    });

    try {
      const response = await fetch(`${serverUrl}/generate-bulk-videos`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errResult = await response.json();
        throw new Error(errResult.error || 'Failed to initiate video generation.');
      }

      const { task_id } = await response.json();
      setTaskId(task_id);
    } catch (err) {
      console.error(err);
      setError(`Failed to start video generation: ${err.message}`);
      setIsGeneratingVideo(false);
    }
  };

  // ... (useEffect for polling is unchanged) ...
  useEffect(() => {
    if (!taskId) return;
    const pollStatus = async () => {
      try {
        const response = await fetch(`${serverUrl}/check-status/${taskId}`);
        if (!response.ok) throw new Error('Failed to check status.');
        const task = await response.json();
        if (task.status === 'completed') {
          const downloadResponse = await fetch(`${serverUrl}/download/${taskId}`);
          if (!downloadResponse.ok) throw new Error('Failed to fetch zip file.');
          const blob = await downloadResponse.blob();
          const url = URL.createObjectURL(blob);
          setVideoDownloadUrl(url);
          setIsGeneratingVideo(false);
        } else if (task.status === 'failed') {
          throw new Error(task.error || 'Video generation failed.');
        } else {
          setTimeout(pollStatus, 2000);
        }
      } catch (err) {
        console.error(err);
        setError(`Error during video generation: ${err.message}`);
        setIsGeneratingVideo(false);
      }
    };
    pollStatus();
  }, [taskId]);

  // ... (handleDownload is unchanged) ...
  const handleDownload = async () => {
    try {
      await fetch(`${serverUrl}/cleanup/${taskId}`, { method: 'POST' });
      setTimeout(() => {
        URL.revokeObjectURL(videoDownloadUrl);
        setVideoDownloadUrl('');
        setTaskId(null);
      }, 1000);
    } catch (err) {
      console.error('Cleanup failed:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-8 flex flex-col items-center">
      <div className="w-full max-w-4xl bg-gray-800 rounded-3xl shadow-xl p-8 md:p-12 space-y-8">
        <header className="flex flex-col items-center text-center space-y-4">
          <Sparkles className="w-16 h-16 text-sky-400 animate-pulse" />
          <h1 className="text-4xl md:text-5xl font-extrabold text-white">Bulk Video Generator</h1>
          <p className="text-lg text-gray-400 max-w-2xl">
            Upload images for the slides and for the background/breaks.
          </p>
        </header>

        <main className="space-y-6">
          <div className="space-y-4">
            {/* --- 1. Topics Textarea --- */}
            <label htmlFor="topics-input" className="block text-sm font-medium text-gray-300">
              1. Paste Your Topics
            </label>
            <textarea
              id="topics-input"
              value={topicsText}
              onChange={(e) => setTopicsText(e.target.value)}
              placeholder="e.g.&#10;How to brew coffee at home&#10;The history of AI"
              rows={6}
              className="w-full p-4 bg-gray-700 text-white rounded-xl border border-gray-600 focus:border-sky-400 focus:ring-1 focus:ring-sky-400"
              disabled={isGeneratingVideo}
            />

            {/* --- 2. NEW: Side-by-Side Image Upload --- */}
            <label className="block text-sm font-medium text-gray-300">
              2. Upload Side-by-Side Images (Optional)
            </label>
            <label
              htmlFor="side-image-upload"
              className={`relative flex w-full justify-center p-4 bg-gray-700 text-white rounded-xl border-2 border-dashed border-gray-600 cursor-pointer
                ${isGeneratingVideo ? 'opacity-50 cursor-not-allowed' : 'hover:border-sky-400'}
              `}
            >
              <input
                id="side-image-upload"
                type="file"
                multiple
                accept="image/*"
                onChange={handleSideImageChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                disabled={isGeneratingVideo}
              />
              <div className="flex flex-col items-center space-y-2 text-gray-400">
                <LayoutPanelLeft className="w-8 h-8" />
                {sideImageFiles.length > 0 ? (
                  <span className="font-semibold text-sky-300">{sideImageFiles.length} images selected</span>
                ) : (
                  <span>Upload images for the slides</span>
                )}
              </div>
            </label>

            {/* --- 3. NEW: Background Image Upload --- */}
            <label className="block text-sm font-medium text-gray-300">
              3. Upload Background/Break Images (Optional)
            </label>
            <label
              htmlFor="bg-image-upload"
              className={`relative flex w-full justify-center p-4 bg-gray-700 text-white rounded-xl border-2 border-dashed border-gray-600 cursor-pointer
                ${isGeneratingVideo ? 'opacity-50 cursor-not-allowed' : 'hover:border-sky-400'}
              `}
            >
              <input
                id="bg-image-upload"
                type="file"
                multiple
                accept="image/*"
                onChange={handleBgImageChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                disabled={isGeneratingVideo}
              />
              <div className="flex flex-col items-center space-y-2 text-gray-400">
                <PictureInPicture className="w-8 h-8" />
                {bgImageFiles.length > 0 ? (
                  <span className="font-semibold text-sky-300">{bgImageFiles.length} images selected</span>
                ) : (
                  <span>Upload images for background & breaks</span>
                )}
              </div>
            </label>
          </div>

          {/* --- 4. Generate Button --- */}
          <button
            onClick={handleGenerateVideo}
            className={`w-full py-4 px-6 rounded-xl font-bold text-white transition
              ${isGeneratingVideo ? 'bg-indigo-600 cursor-not-allowed' : 'bg-indigo-500 hover:bg-indigo-600'}
              ${!topicsText ? 'opacity-50 cursor-not-allowed' : ''}`}
            disabled={!topicsText || isGeneratingVideo}
          >
            {isGeneratingVideo ? (
              <span className="flex items-center justify-center">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Generating Videos...
              </span>
            ) : (
              <span className="flex items-center justify-center">
                <Video className="mr-2 h-5 w-5" /> Generate Videos
              </span>
            )}
          </button>

          {/* ... (Error and Download sections are unchanged) ... */}
          {error && (
            <div className="bg-red-500 bg-opacity-20 text-red-300 p-4 rounded-xl border border-red-500 text-sm">
              <p>{error}</p>
            </div>
          )}
        </main>

        {videoDownloadUrl && !isGeneratingVideo && (
          <div className="mt-6">
            <div className="bg-emerald-500 bg-opacity-20 text-emerald-300 p-4 rounded-xl border border-emerald-500 text-sm flex items-center space-x-2">
              <CheckCircle size={20} />
              <p>All videos are ready and compressed into a single zip file.</p>
            </div>
            <a
              href={videoDownloadUrl}
              download="generated_videos.zip"
              className="mt-4 w-full py-4 px-6 rounded-xl font-bold text-white flex items-center justify-center bg-emerald-500 hover:bg-emerald-600"
              onClick={handleDownload}
            >
              <Download className="mr-2 h-5 w-5" /> Download Zip File
            </a>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;
