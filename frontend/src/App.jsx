import { useState } from "react";
import {
  Search,
  FileText,
  Upload,
  LoaderCircle,
  ExternalLink,
  Database,
  Sparkles,
  X,
} from "lucide-react";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";
function cleanResultText(text) {
  const textarea = document.createElement("textarea");
  textarea.innerHTML = text ?? "";

  return textarea.value
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [uploadMessage, setUploadMessage] = useState("");

  const searchDocuments = async (event) => {
    event.preventDefault();

    if (!query.trim()) {
      setError("Please enter something to search.");
      return;
    }

    setLoading(true);
    setError("");
    setUploadMessage("");
    setSearched(true);
    setSelectedDocument(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/search?q=${encodeURIComponent(query)}&top_k=5`
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Search failed.");
      }

      const data = await response.json();
      setResults(data.results || []);
    } catch (err) {
      setResults([]);
      setError(
        err.message ||
          "Unable to connect to the backend. Please check that FastAPI is running."
      );
    } finally {
      setLoading(false);
    }
  };

  const uploadDocument = async (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select a PDF file.");
      event.target.value = "";
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setUploading(true);
    setError("");
    setUploadMessage("");

    try {
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "PDF upload failed.");
      }

      setUploadMessage(
        `${data.document} processed successfully. ${data.chunks_created} text chunks indexed.`
      );

      setSelectedDocument(null);
    } catch (err) {
      setError(err.message || "Unable to upload the PDF.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const openDocument = (documentName, page) => {
    setSelectedDocument({
      name: documentName,
      page,
      url: `${API_BASE_URL}/documents/${encodeURIComponent(documentName)}#page=${page}`,
    });
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Document Intelligence home">
          <span className="brand-icon">
            <Database size={23} />
          </span>
          <span>
            <strong>DocuMind</strong>
            <small>DOCUMENT INTELLIGENCE</small>
          </span>
        </a>

        <div className="topbar-right">
          <span className="status-dot"></span>
          <span>AI Search Portal</span>

          <label className="upload-button">
            {uploading ? (
              <LoaderCircle size={17} className="spin" />
            ) : (
              <Upload size={17} />
            )}
            {uploading ? "Indexing..." : "Upload PDF"}
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={uploadDocument}
              disabled={uploading}
              hidden
            />
          </label>
        </div>
      </header>

      <main>
        <section className="hero-section">
          <div className="eyebrow">
            <Sparkles size={15} />
            INTELLIGENT DOCUMENT SEARCH
          </div>

          <h1>
            Every document.
            <br />
            <span>One intelligent search.</span>
          </h1>

          <p className="hero-description">
            Search across your documents using natural language. Find relevant
            information and jump directly to the original PDF page.
          </p>

          <form className="search-form" onSubmit={searchDocuments}>
            <Search size={22} className="search-icon" />

            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Try: What is the tender submission deadline?"
              aria-label="Search documents"
            />

            <button type="submit" disabled={loading}>
              {loading ? (
                <LoaderCircle size={18} className="spin" />
              ) : (
                <Search size={18} />
              )}
              Search
            </button>
          </form>

          <div className="search-hint">
            <span>Try searching for:</span>
            {["tender deadline", "eligibility criteria", "payment terms"].map(
              (suggestion) => (
                <button
                  type="button"
                  key={suggestion}
                  onClick={() => setQuery(suggestion)}
                >
                  {suggestion}
                </button>
              )
            )}
          </div>
        </section>

        {(error || uploadMessage) && (
          <div className={error ? "notice error-notice" : "notice success-notice"}>
            <span>{error || uploadMessage}</span>
            <button
              type="button"
              onClick={() => {
                setError("");
                setUploadMessage("");
              }}
              aria-label="Dismiss notification"
            >
              <X size={17} />
            </button>
          </div>
        )}

        <section className="results-section">
          <div className="section-heading">
            <div>
              <span className="section-kicker">YOUR KNOWLEDGE BASE</span>
              <h2>
                {loading
                  ? "Searching documents..."
                  : searched
                    ? "Search results"
                    : "Explore your documents"}
              </h2>
            </div>

            {searched && !loading && (
              <span className="result-count">
                {results.length} {results.length === 1 ? "result" : "results"}
              </span>
            )}
          </div>

          {loading ? (
            <div className="empty-state">
              <LoaderCircle size={32} className="spin" />
              <p>Finding relevant passages in your documents...</p>
            </div>
          ) : searched && results.length === 0 && !error ? (
            <div className="empty-state">
              <Search size={34} />
              <h3>No results found</h3>
              <p>Try different keywords or a more descriptive search.</p>
            </div>
          ) : searched && results.length > 0 ? (
            <div className="results-list">
              {results.map((result, index) => (
                <article
                  className="result-card"
                  key={`${result.document}-${result.page}-${index}`}
                >
                  <div className="result-card-top">
                    <span className="file-icon">
                      <FileText size={20} />
                    </span>

                    <div className="result-document">
                      <strong>{result.document}</strong>
                      <span>Page {result.page}</span>
                    </div>

                    <button
                      className="view-button"
                      type="button"
                      onClick={() =>
                        openDocument(result.document, result.page)
                      }
                    >
                      View PDF <ExternalLink size={15} />
                    </button>
                  </div>

                  <p className="result-text">{cleanResultText(result.text)}</p>

                  <div className="result-card-footer">
                    <span>
                      <Sparkles size={14} />
                      Semantic search match
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        openDocument(result.document, result.page)
                      }
                    >
                      Open original document →
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="welcome-grid">
              <article className="welcome-card">
                <span className="welcome-icon">
                  <Search size={22} />
                </span>
                <h3>Search naturally</h3>
                <p>
                  Ask a question or enter keywords to find relevant passages
                  across indexed PDFs.
                </p>
              </article>

              <article className="welcome-card">
                <span className="welcome-icon">
                  <Database size={22} />
                </span>
                <h3>Vector-powered retrieval</h3>
                <p>
                  Sentence embeddings and ChromaDB help retrieve semantically
                  relevant text, not just exact keyword matches.
                </p>
              </article>

              <article className="welcome-card">
                <span className="welcome-icon">
                  <FileText size={22} />
                </span>
                <h3>Original PDFs preserved</h3>
                <p>
                  Open the source PDF and navigate to the page containing a
                  relevant passage.
                </p>
              </article>
            </div>
          )}
        </section>

        <footer className="footer">
          <span>DocuMind AI · Document Intelligence Portal</span>
          <span>FastAPI · ChromaDB · Sentence Transformers · React</span>
        </footer>
      </main>

      {selectedDocument && (
        <div className="pdf-overlay">
          <section className="pdf-modal">
            <div className="pdf-toolbar">
              <div className="pdf-title">
                <FileText size={19} />
                <div>
                  <strong>{selectedDocument.name}</strong>
                  <span>Page {selectedDocument.page}</span>
                </div>
              </div>

              <div className="pdf-actions">
                <a
                  href={selectedDocument.url}
                  target="_blank"
                  rel="noreferrer"
                  className="open-new-tab"
                >
                  Open in new tab <ExternalLink size={15} />
                </a>

                <button
                  type="button"
                  className="close-pdf"
                  onClick={() => setSelectedDocument(null)}
                  aria-label="Close PDF viewer"
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            <iframe
              title={`PDF viewer: ${selectedDocument.name}`}
              src={selectedDocument.url}
              className="pdf-frame"
            />
          </section>
        </div>
      )}
    </div>
  );
}

export default App;