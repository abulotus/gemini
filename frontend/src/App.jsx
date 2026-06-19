import { useEffect, useRef, useState } from 'react';
import axios from 'axios';

const API_URL =
  'https://fastapi-container-production-ece7.up.railway.app/decode-barcode';

function App() {
  const videoRef = useRef(null);
  const containerRef = useRef(null);
  const streamRef = useRef(null);

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!cameraOpen) return;

    const attachStream = async () => {
      if (!videoRef.current || !streamRef.current) return;

      try {
        videoRef.current.srcObject = streamRef.current;
        videoRef.current.setAttribute('playsinline', 'true');
        videoRef.current.setAttribute('webkit-playsinline', 'true');
        videoRef.current.muted = true;

        await videoRef.current.play();
      } catch (err) {
        console.error('Video play error:', err);
        setError(`Camera opened but preview failed: ${err.message}`);
      }
    };

    const timer = setTimeout(attachStream, 200);
    return () => clearTimeout(timer);
  }, [cameraOpen]);

  const startCamera = async () => {
    try {
      setError(null);
      setResult(null);
      setPreview(null);
      setFile(null);

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 3840 },
          height: { ideal: 2160 },
        },
        audio: false,
      });

      const track = stream.getVideoTracks()[0];
      

console.log("Camera settings:", track.getSettings());
console.log("Video size:", videoRef.current?.videoWidth, videoRef.current?.videoHeight);
      const capabilities = track.getCapabilities?.();

      if (capabilities?.focusMode?.includes('continuous')) {
        await track.applyConstraints({
          advanced: [{ focusMode: 'continuous' }],
        });
      }

      streamRef.current = stream;
      setCameraOpen(true);
    } catch (err) {
      console.error('Camera error:', err);
      setCameraOpen(false);
      setError(`Could not open camera: ${err.name} - ${err.message}`);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }

    streamRef.current = null;

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraOpen(false);
  };

  const cropBarcodeFromVideo = async () => {
  const video = videoRef.current;
  const container = containerRef.current;

  if (!video || !container) {
    throw new Error('Camera is not ready.');
  }

  if (!video.videoWidth || !video.videoHeight) {
    throw new Error('Video is not ready yet.');
  }

  const videoW = video.videoWidth;
  const videoH = video.videoHeight;

  const displayW = container.clientWidth;
  const displayH = container.clientHeight;

  const videoRatio = videoW / videoH;
  const displayRatio = displayW / displayH;

  let renderedW;
  let renderedH;
  let offsetX = 0;
  let offsetY = 0;

  if (videoRatio > displayRatio) {
    renderedH = displayH;
    renderedW = displayH * videoRatio;
    offsetX = (renderedW - displayW) / 2;
  } else {
    renderedW = displayW;
    renderedH = displayW / videoRatio;
    offsetY = (renderedH - displayH) / 2;
  }

  // Match barcodeFrameStyle:
  // left: 15%, top: 69%, width: 63%, height: 10%
  const boxLeft = displayW * 0.15;
  const boxTop = displayH * 0.60;
  const boxW = displayW * 0.71;
  const boxH = displayH * 0.28;

  const scaleX = videoW / renderedW;
  const scaleY = videoH / renderedH;

  const cropX = (boxLeft + offsetX) * scaleX;
  const cropY = (boxTop + offsetY) * scaleY;
  const cropW = boxW * scaleX;
  const cropH = boxH * scaleY;

  const UPSCALE = 2;

  const cropCanvas = document.createElement('canvas');
  cropCanvas.width = Math.round(cropW * UPSCALE);
  cropCanvas.height = Math.round(cropH * UPSCALE);

  const ctx = cropCanvas.getContext('2d');

  if (!ctx) {
    throw new Error('Could not prepare image crop.');
  }

  ctx.imageSmoothingEnabled = false;

  ctx.drawImage(
    video,
    cropX,
    cropY,
    cropW,
    cropH,
    0,
    0,
    cropCanvas.width,
    cropCanvas.height
  );

  return new Promise((resolve, reject) => {
    cropCanvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error('Could not crop barcode.'));
      } else {
        resolve(blob);
      }
    }, 'image/png');
  });
};

const handleFileCapture = (e) => {
  const selectedFile = e.target.files?.[0];

  if (!selectedFile) return;

  setFile(selectedFile);
  setPreview(URL.createObjectURL(selectedFile));

  console.log(
    "Photo size:",
    selectedFile.size / 1024 / 1024,
    "MB"
  );

  setResult(null);
  setError(null);
};

  const captureImage = async () => {
    try {
      const blob = await cropBarcodeFromVideo();

    const capturedFile = new File([blob], 'syrian-id-barcode-crop.png', {
  type: 'image/png',
});

      setFile(capturedFile);
      setPreview(URL.createObjectURL(blob));
      setResult(null);
      setError(null);
      stopCamera();
    } catch (err) {
      setError(err.message || 'Could not capture barcode.');
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();

    if (!file) {
      setError('Please capture an image first.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(API_URL, formData);
      setResult(response.data);
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          'An error occurred while decoding the barcode.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: 520,
        margin: '20px auto',
        padding: 20,
        fontFamily: 'Arial, sans-serif',
      }}
    >
      <h1>Syrian ID Barcode Decoder</h1>


  <label
  style={{
    display: 'block',
    marginTop: 10,
    padding: 14,
    background: '#2563eb',
    color: 'white',
    textAlign: 'center',
    borderRadius: 8,
    cursor: 'pointer',
  }}
>
  Take High Quality Photo

  <input
    type="file"
    accept="image/*"
    capture="environment"
    onChange={handleFileCapture}
    style={{ display: 'none' }}
  />
</label>


      {!cameraOpen && (
        <button type="button" onClick={startCamera} style={primaryButton}>
          Open Camera
        </button>
      )}

      {cameraOpen && (
        <div style={{ marginTop: 20 }}>
          <div ref={containerRef} style={cameraBox}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              controls={false}
              style={videoStyle}
            />

            <div style={idFrameStyle} />
            <div style={barcodeFrameStyle} />

            <div style={instructionStyle}>
              ضع الباركود ضمن المربع المنقط
            </div>
          </div>

          <button type="button" onClick={captureImage} style={primaryButton}>
            Capture Barcode
          </button>

          <button type="button" onClick={stopCamera} style={secondaryButton}>
            Close Camera
          </button>
        </div>
      )}

      {preview && (
        <div style={{ margin: '20px 0' }}>
          <h3>Captured Barcode Crop</h3>
          <img
            src={preview}
            alt="Captured barcode crop"
            style={{
              width: '100%',
              maxHeight: 260,
              objectFit: 'contain',
              borderRadius: 8,
              border: '1px solid #ddd',
            }}
          />
        </div>
      )}

      <form onSubmit={handleUpload}>
        <button
          type="submit"
          disabled={loading || !file}
          style={{
            ...primaryButton,
            background: loading || !file ? '#9ca3af' : '#111827',
          }}
        >
          {loading ? 'Decoding...' : 'Scan Barcode'}
        </button>
      </form>

      {error && <p style={errorStyle}>{error}</p>}

      {result && (
        <div style={resultBox}>
          {result.success ? (
            <>
              <h3>Barcode Detected</h3>

              <p>
                <strong>Format:</strong> {result.format}
              </p>

              <textarea
                readOnly
                value={result.decoded_arabic_text || ''}
                rows={6}
                style={textareaStyle}
              />

              {result.profile && (
                <div style={{ marginTop: 15 }}>
                  <p><strong>First Name:</strong> {result.profile.first_name || ''}</p>
                  <p><strong>Last Name:</strong> {result.profile.last_name || ''}</p>
                  <p><strong>Father Name:</strong> {result.profile.father_name || ''}</p>
                  <p><strong>Mother Name:</strong> {result.profile.mother_name || ''}</p>
                  <p><strong>Birth Place:</strong> {result.profile.birth_place || ''}</p>
                  <p><strong>Birth Date:</strong> {result.profile.birth_date || ''}</p>
                  <p><strong>National Number:</strong> {result.profile.national_number || ''}</p>
                </div>
              )}
            </>
          ) : (
            <p>⚠️ {result.message}</p>
          )}
        </div>
      )}
    </div>
  );
}

const cameraBox = {
  position: 'relative',
  background: '#000',
  borderRadius: 14,
  overflow: 'hidden',
  height: 260,
};

const videoStyle = {
  width: '100%',
  height: '100%',
  background: '#000',
  display: 'block',
  objectFit: 'cover',
};

const idFrameStyle = {
  position: 'absolute',
  left: '0%',
  top: '0%',
  width: '100%',
  height: '90%',
  border: '3px solid #22c55e',
  borderRadius: 16,
  boxSizing: 'border-box',
  pointerEvents: 'none',
};

const barcodeFrameStyle = {
  position: 'absolute',
  left: '15%',
  top: '60%',
  width: '71%',
  height: '28%',
  border: '4px dashed #22c55e',
  borderRadius: 8,
  boxSizing: 'border-box',
  pointerEvents: 'none',
};

const instructionStyle = {
  position: 'absolute',
  left: '8%',
  top: '92%',
  right: '8%',
  bottom: '10%',
  textAlign: 'center',
  color: 'white',
  fontSize: 14,
  fontWeight: 700,
  textShadow: '0 2px 4px black',
  pointerEvents: 'none',
};

const primaryButton = {
  width: '100%',
  padding: 14,
  marginTop: 12,
  fontSize: 16,
  fontWeight: 600,
  background: '#16a34a',
  color: 'white',
  border: 'none',
  borderRadius: 8,
};

const secondaryButton = {
  width: '100%',
  padding: 12,
  marginTop: 8,
  fontSize: 15,
  background: '#e5e7eb',
  color: '#111827',
  border: 'none',
  borderRadius: 8,
};

const errorStyle = {
  color: '#b91c1c',
  marginTop: 20,
  background: '#fee2e2',
  padding: 12,
  borderRadius: 8,
};

const resultBox = {
  marginTop: 20,
  padding: 15,
  background: '#f3f4f6',
  borderRadius: 8,
};

const textareaStyle = {
  width: '100%',
  direction: 'rtl',
  textAlign: 'right',
  fontFamily: 'Tahoma, Arial, sans-serif',
};

export default App;