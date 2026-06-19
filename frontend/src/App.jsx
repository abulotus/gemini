import { useState } from 'react';
import axios from 'axios';

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreview(URL.createObjectURL(selectedFile));
      setResult(null);
      setError(null);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("Please select an image first.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(
        'https://fastapi-container-production-ece7.up.railway.app/decode-barcode',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      setResult(response.data);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || "An error occurred while decoding the barcode.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '500px', margin: '40px auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Barcode Decoder</h1>
      
      <form onSubmit={handleUpload}>
        <input 
          type="file" 
          accept="image/*" 
          onChange={handleFileChange} 
        />
        
        {preview && (
          <div style={{ margin: '20px 0' }}>
            <img src={preview} alt="Preview" style={{ width: '100%', maxHeight: '200px', objectFit: 'contain' }} />
          </div>
        )}

        <button type="submit" disabled={loading || !file} style={{ width: '100%', padding: '10px', marginTop: '10px' }}>
          {loading ? 'Decoding...' : 'Scan Barcode'}
        </button>
      </form>

      {error && <p style={{ color: 'red', marginTop: '20px' }}>{error}</p>}

      {result && (
        <div style={{ marginTop: '20px', padding: '15px', background: '#f0f0f0', borderRadius: '5px' }}>
          {result.success ? (
            <>
              <h3>🎉 Barcode Detected!</h3>
              <p><strong>Data:</strong> <code>{result.barcode_data}</code></p>
              <p><strong>Format:</strong> {result.barcode_type}</p>
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
