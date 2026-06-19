import { useRef, useState } from 'react';
import axios from 'axios';

const API_URL =
  'https://fastapi-container-production-ece7.up.railway.app/decode-barcode';

function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const startCamera = async () => {
    try {
      setError(null);
      setResult(null);

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      setCameraOpen(true);
    } catch (err) {
      console.error(err);
      setError('Could not open camera. Please allow camera permission.');
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }

    streamRef.current = null;
    setCameraOpen(false);
  };

  const captureImage = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setError('Could not capture image.');
          return;
        }

        const capturedFile = new File([blob], 'syrian-id-barcode.jpg', {
          type: 'image/jpeg',
        });

        setFile(capturedFile);
        setPreview(URL.createObjectURL(blob));
        setResult(null);
        setError(null);
        stopCamera();
      },
      'image/jpeg',
      0.95
    );
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

      console.log(response.data);
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

      {!cameraOpen && (
        <button
          type="button"
          onClick={startCamera}
          style={{
            width: '100%',
            padding: 14,
            fontSize: 16,
            fontWeight: 600,
            background: '#16a34a',
            color: 'white',
            border: 'none',
            borderRadius: 8,
          }}
        >
          Open Camera
        </button>
      )}

      {cameraOpen && (
        <div style={{ marginTop: 20 }}>
          <div
            style={{
              position: 'relative',
              background: '#000',
              borderRadius: 14,
              overflow: 'hidden',
            }}
          >
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{
                width: '100%',
                display: 'block',
              }}
            />

            <div
              style={{
                position: 'absolute',
                inset: 0,
                background: 'rgba(0,0,0,0.22)',
                pointerEvents: 'none',
              }}
            />

            {/* Outer card guide */}
            <div
              style={{
                position: 'absolute',
                left: '5%',
                top: '12%',
                width: '90%',
                height: '65%',
                border: '3px solid #22c55e',
                borderRadius: 16,
                boxSizing: 'border-box',
                pointerEvents: 'none',
              }}
            />

            {/* Barcode guide */}
            <div
              style={{
                position: 'absolute',
                left: '10%',
                bottom: '12%',
                width: '80%',
                height: '22%',
                border: '4px dashed #22c55e',
                borderRadius: 10,
                boxSizing: 'border-box',
                pointerEvents: 'none',
              }}
            />

            <div
              style={{
                position: 'absolute',
                left: '8%',
                right: '8%',
                bottom: '4%',
                textAlign: 'center',
                color: 'white',
                fontSize: 14,
                fontWeight: 700,
                textShadow: '0 2px 4px black',
                pointerEvents: 'none',
              }}
            >
              Place the PDF417 barcode inside the dashed green box
            </div>
          </div>

          <button
            type="button"
            onClick={captureImage}
            style={{
              width: '100%',
              padding: 14,
              marginTop: 12,
              fontSize: 16,
              fontWeight: 600,
              background: '#16a34a',
              color: 'white',
              border: 'none',
              borderRadius: 8,
            }}
          >
            Capture Image
          </button>

          <button
            type="button"
            onClick={stopCamera}
            style={{
              width: '100%',
              padding: 12,
              marginTop: 8,
              fontSize: 15,
              background: '#e5e7eb',
              color: '#111827',
              border: 'none',
              borderRadius: 8,
            }}
          >
            Close Camera
          </button>
        </div>
      )}

      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {preview && (
        <div style={{ margin: '20px 0' }}>
          <h3>Captured Image</h3>
          <img
            src={preview}
            alt="Captured ID barcode"
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
            width: '100%',
            padding: 14,
            marginTop: 10,
            fontSize: 16,
            fontWeight: 600,
            background: loading || !file ? '#9ca3af' : '#111827',
            color: 'white',
            border: 'none',
            borderRadius: 8,
          }}
        >
          {loading ? 'Decoding...' : 'Scan Barcode'}
        </button>
      </form>

      {error && (
        <p
          style={{
            color: '#b91c1c',
            marginTop: 20,
            background: '#fee2e2',
            padding: 12,
            borderRadius: 8,
          }}
        >
          {error}
        </p>
      )}

      {result && (
        <div
          style={{
            marginTop: 20,
            padding: 15,
            background: '#f3f4f6',
            borderRadius: 8,
          }}
        >
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
                style={{
                  width: '100%',
                  direction: 'rtl',
                  textAlign: 'right',
                  fontFamily: 'Tahoma, Arial, sans-serif',
                }}
              />

              {result.profile && (
                <div style={{ marginTop: 15 }}>
                  <p>
                    <strong>First Name:</strong>{' '}
                    {result.profile.first_name || ''}
                  </p>
                  <p>
                    <strong>Last Name:</strong>{' '}
                    {result.profile.last_name || ''}
                  </p>
                  <p>
                    <strong>Father Name:</strong>{' '}
                    {result.profile.father_name || ''}
                  </p>
                  <p>
                    <strong>Mother Name:</strong>{' '}
                    {result.profile.mother_name || ''}
                  </p>
                  <p>
                    <strong>Birth Place:</strong>{' '}
                    {result.profile.birth_place || ''}
                  </p>
                  <p>
                    <strong>Birth Date:</strong>{' '}
                    {result.profile.birth_date || ''}
                  </p>
                  <p>
                    <strong>National Number:</strong>{' '}
                    {result.profile.national_number || ''}
                  </p>
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

export default App;