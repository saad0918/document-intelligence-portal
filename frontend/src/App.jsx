import { useEffect, useState } from "react";
import {
  Search,
  FileText,
  Upload,
  LoaderCircle,
  ExternalLink,
  Database,
  Sparkles,
  X,
  BookOpen,
} from "lucide-react";
import "./App.css";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/+$/, "");

// These are the two source PDFs supplied for this portal.
// The viewer renders the original PDF files directly so their layout is preserved.
const SOURCE_DOCUMENTS = [
  {
    name: "Tata Chemicals – Tender for Architectural Design",
    filename: "tata_tender.pdf",
    pages: 29,
    description:
      "Original tender document covering architectural design and staff housing development.",
  },
  {
    name: "RBI – Commercial Banks: Financial Statements",
    filename: "company_document.pdf",
    pages: 120,
    description:
      "Original RBI directions covering financial statement presentation and disclosures.",
  },
];

function cleanResultText(text) {
  const textarea = document.createElement("textarea");
  textarea.innerHTML = text ?? "";

  return textarea.value
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function getHighlightedBlocks(pageData, searchQuery) {
  if (!pageData?.blocks || !searchQuery?.trim()) {
    return [];
  }

  const terms = searchQuery
    .toLowerCase()
    .split(/\s+/)
    .filter((term) => term.length > 2);

  if (terms.length === 0) return [];

  return pageData.blocks.filter((block) => {
    const blockText = block.text.toLowerCase();

    return terms.some((term) => blockText.includes(term));
  });
}

function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [pageData, setPageData] = useState(null);
  const [pageLoading, setPageLoading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");

  const documentUrl = (filename, page = 1) =>
    `${API_BASE_URL}/documents/${encodeURIComponent(filename)}#page=${page}`;
  const openDocument = (
  filename,
  page = 1,
  displayName = filename,
  searchQuery = ""
) => {
  setSelectedDocument({
    name: displayName,
    filename,
    page,
    url: documentUrl(filename, page),
    searchQuery,
  });
};
useEffect(() => {
  if (!selectedDocument) {
    setPageData(null);
    return;
  }

  const fetchPageData = async () => {
    setPageLoading(true);
    setPageData(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/page-data/${encodeURIComponent(
          selectedDocument.filename
        )}/${selectedDocument.page}`
      );

      if (!response.ok) {
        throw new Error("Unable to load page data.");
      }

      const data = await response.json();
      setPageData(data);
    } catch (err) {
      console.error("Page data error:", err);
      setPageData(null);
    } finally {
      setPageLoading(false);
    }
  };

  fetchPageData();
}, [selectedDocument]);

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
    } catch (err) {
      setError(err.message || "Unable to upload the PDF.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
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
          <span className="status-dot" />
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
            Search across both source documents, open the original PDF, and
            navigate directly to the page containing a relevant passage.
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
            {["tender deadline", "architectural design", "financial statements"].map(
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
          <div
            className={
              error ? "notice error-notice" : "notice success-notice"
            }
          >
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

        <section className="documents-section">
          <div className="section-heading">
            <div>
              <span className="section-kicker">SOURCE LIBRARY</span>
              <h2>Original documents</h2>
              <p className="section-description">
                Open either supplied PDF in the portal. The source PDF is
                rendered directly, preserving its original pages and layout.
              </p>
            </div>
            <span className="library-count">2 source PDFs</span>
          </div>

          <div className="documents-grid">
            {SOURCE_DOCUMENTS.map((document) => (
              <article className="document-card" key={document.filename}>
                <div className="document-card-icon">
                  <FileText size={24} />
                </div>
                <div className="document-card-content">
                  <span className="document-type">ORIGINAL PDF</span>
                  <h3>{document.name}</h3>
                  <p>{document.description}</p>
                  <span className="page-count">{document.pages} pages</span>
                </div>
                <div className="document-card-actions">
                  <button
                    type="button"
                    className="primary-document-button"
                    onClick={() =>
                      openDocument(
                        document.filename,
                        1,
                        document.name
                      )
                    }
                  >
                    <BookOpen size={16} />
                    View original PDF
                  </button>
                  <a
                    className="text-link"
                    href={documentUrl(document.filename)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open in new tab <ExternalLink size={14} />
                  </a>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="results-section">
          <div className="section-heading">
            <div>
              <span className="section-kicker">YOUR KNOWLEDGE BASE</span>
              <h2>
                {loading
                  ? "Searching documents..."
                  : searched
                    ? "Search results"
                    : "Search across your documents"}
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
                        openDocument(
                          result.document,
                          result.page,
                          result.document,
                          query
                        )
                      }
                    >
                      View page <ExternalLink size={15} />
                    </button>
                  </div>

                  <p className="result-text">
                    {cleanResultText(result.text)}
                  </p>

                  <div className="result-card-footer">
                    <span>
                      <Sparkles size={14} />
                      Retrieved passage
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        openDocument(
                          result.document,
                          result.page,
                          result.document,
                          query
                        )
                      }
                    >
                      Open original document →
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state search-prompt">
              <Search size={30} />
              <p>Enter a query above to find information in both PDFs.</p>
            </div>
          )}
        </section>
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

            <div className="page-preview-container">
              {pageLoading ? (
                <p>Loading page...</p>
              ) : pageData ? (
                <iframe
                  key={`${selectedDocument.filename}-${selectedDocument.page}`}
                  src={`${API_BASE_URL}/reconstructed/${selectedDocument.filename.replace(
                    /\.pdf$/i,
                    ""
                  )}/html_pages/index.html#page-${selectedDocument.page}`}
                  title={`${selectedDocument.name} - Page ${selectedDocument.page}`}
                  className="html-document-viewer"
                />
              ) : (
                <p>Unable to load reconstructed page.</p>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default App;
