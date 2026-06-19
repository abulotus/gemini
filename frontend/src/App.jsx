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
      setError('Please select an image first.');
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
        formData
      );

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
        maxWidth: '500px',
        margin: '40px auto',
        padding: '20px',
        fontFamily: 'sans-serif',
      }}
    >
      <h1>Barcode Decoder</h1>

      <form onSubmit={handleUpload}>
        <input type="file" accept="image/*" onChange={handleFileChange} />

        {preview && (
          <div style={{ margin: '20px 0' }}>
            <img
              src={preview}
              alt="Preview"
              style={{
                width: '100%',
                maxHeight: '200px',
                objectFit: 'contain',
              }}
            />
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !file}
          style={{
            width: '100%',
            padding: '10px',
            marginTop: '10px',
          }}
        >
          {loading ? 'Decoding...' : 'Scan Barcode'}
        </button>
      </form>

      {error && (
        <p style={{ color: 'red', marginTop: '20px' }}>
          {error}
        </p>
      )}

      {result && (
        <div
          style={{
            marginTop: '20px',
            padding: '15px',
            background: '#f0f0f0',
            borderRadius: '5px',
          }}
        >
          {result.success ? (
            <>
              <h3>🎉 Barcode Detected!</h3>

              <p>
                <strong>Format:</strong> {result.format}
              </p>

              <p>
                <strong>Decoded Text:</strong>
              </p>

              <textarea
                readOnly
                value={result.decoded_arabic_text || ''}
                rows={6}
                style={{
                  width: '100%',
                  direction: 'rtl',
                }}
              />

              {result.profile && (
                <div style={{ marginTop: '15px' }}>
                  <h4>Extracted Profile</h4>

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