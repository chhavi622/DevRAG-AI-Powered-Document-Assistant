import { useRef, useState } from "react";
import {
  Bot,
  Upload,
  Send,
  FileText,
  MessageSquare,
  Plus,
  Settings,
  Search,
  Sparkles,
  CheckCircle,
  Loader2,
  X
} from "lucide-react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);

  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);

  const [error, setError] = useState("");

  // =====================================================
  // SELECT FILE
  // =====================================================

  const handleFileSelect = (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    setError("");

    if (file.type !== "application/pdf") {
      setError("Please select a PDF file.");
      return;
    }

    setSelectedFile(file);
  };

  // =====================================================
  // UPLOAD PDF
  // =====================================================

  const uploadPDF = async () => {
    if (!selectedFile) {
      setError("Please select a PDF first.");
      return;
    }

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();

      formData.append("file", selectedFile);

      const response = await fetch(
        `${API_URL}/upload-pdf`,
        {
          method: "POST",
          body: formData
        }
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data.message || "PDF upload failed."
        );
      }

      setUploadedFile({
        name: data.filename,
        pages: data.pages,
        chunks: data.chunks
      });

      setSelectedFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      setMessages([
        {
          role: "assistant",
          text: `Your PDF "${data.filename}" has been uploaded successfully. You can now ask questions about it.`
        }
      ]);

    } catch (err) {
      setError(
        err.message ||
        "Unable to upload PDF."
      );
    } finally {
      setUploading(false);
    }
  };

  // =====================================================
  // ASK QUESTION
  // =====================================================

  const askQuestion = async () => {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) return;

    setError("");

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        text: trimmedQuestion
      }
    ]);

    setQuestion("");
    setAsking(true);

    try {
      const response = await fetch(
        `${API_URL}/ask?q=${encodeURIComponent(
          trimmedQuestion
        )}`
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data.message ||
          "Unable to get answer."
        );
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: data.answer,
          sources: data.sources || []
        }
      ]);

    } catch (err) {
      setError(err.message);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Sorry, I couldn't answer that.\n\n${err.message}`
        }
      ]);
    } finally {
      setAsking(false);
    }
  };

  // =====================================================
  // ENTER KEY
  // =====================================================

  const handleKeyDown = (event) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      askQuestion();
    }
  };

  // =====================================================
  // NEW CHAT
  // =====================================================

  const newChat = () => {
    setMessages([]);
    setQuestion("");
    setError("");
  };

  // =====================================================
  // UI
  // =====================================================

  return (
    <div className="app">

      {/* =================================================
          SIDEBAR
      ================================================= */}

      <aside className="sidebar">

        <div className="brand">
          <div className="brand-icon">
            <Bot size={22} />
          </div>

          <div>
            <h2>DevRAG</h2>
            <span>AI Knowledge Assistant</span>
          </div>
        </div>


        <button
          className="new-chat-btn"
          onClick={newChat}
        >
          <Plus size={18} />
          New Chat
        </button>


        <div className="sidebar-section">

          <div className="section-title">
            <MessageSquare size={15} />
            Workspace
          </div>

          <div className="sidebar-item active">
            <Sparkles size={17} />
            AI Assistant
          </div>

          <div className="sidebar-item">
            <FileText size={17} />
            Documents
          </div>

          <div className="sidebar-item">
            <Search size={17} />
            Search
          </div>

        </div>


        <div className="sidebar-section">

          <div className="section-title">
            Recent Chats
          </div>

          <div className="recent-chat">
            About my CV
          </div>

          <div className="recent-chat">
            Project information
          </div>

          <div className="recent-chat">
            Technical skills
          </div>

        </div>


        <div className="sidebar-bottom">

          <div className="sidebar-item">
            <Settings size={17} />
            Settings
          </div>

          <div className="profile">

            <div className="avatar">
              C
            </div>

            <div>
              <strong>Chhavi</strong>
              <span>Student</span>
            </div>

          </div>

        </div>

      </aside>


      {/* =================================================
          MAIN
      ================================================= */}

      <main className="main">

        {/* HEADER */}

        <header className="topbar">

          <div>

            <h1>AI Document Assistant</h1>

            <p>
              Ask questions from your uploaded documents
            </p>

          </div>


          <div className="status">

            <span className="status-dot"></span>

            Backend Connected

          </div>

        </header>


        {/* CONTENT */}

        <div className="content">

          {/* UPLOAD CARD */}

          <section className="upload-card">

            <div className="upload-header">

              <div className="upload-icon">
                <Upload size={22} />
              </div>

              <div>
                <h3>Upload your document</h3>

                <p>
                  Upload a PDF to start asking questions
                </p>
              </div>

            </div>


            <div className="upload-area">

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileSelect}
                hidden
                id="pdf-upload"
              />

              {!selectedFile ? (

                <label
                  htmlFor="pdf-upload"
                  className="upload-label"
                >

                  <Upload size={30} />

                  <strong>
                    Click to choose a PDF
                  </strong>

                  <span>
                    PDF files only
                  </span>

                </label>

              ) : (

                <div className="selected-file">

                  <FileText size={30} />

                  <div className="file-info">

                    <strong>
                      {selectedFile.name}
                    </strong>

                    <span>
                      {(
                        selectedFile.size /
                        1024 /
                        1024
                      ).toFixed(2)} MB
                    </span>

                  </div>


                  <button
                    className="remove-file"
                    onClick={() => {
                      setSelectedFile(null);

                      if (fileInputRef.current) {
                        fileInputRef.current.value = "";
                      }
                    }}
                  >
                    <X size={17} />
                  </button>

                </div>

              )}

            </div>


            {selectedFile && (

              <button
                className="upload-btn"
                onClick={uploadPDF}
                disabled={uploading}
              >

                {uploading ? (
                  <>
                    <Loader2
                      size={18}
                      className="spin"
                    />
                    Processing PDF...
                  </>
                ) : (
                  <>
                    <Upload size={18} />
                    Upload & Process
                  </>
                )}

              </button>

            )}


            {uploadedFile && (

              <div className="uploaded-success">

                <CheckCircle size={18} />

                <div>

                  <strong>
                    {uploadedFile.name}
                  </strong>

                  <span>
                    {uploadedFile.pages} pages •{" "}
                    {uploadedFile.chunks} chunks processed
                  </span>

                </div>

              </div>

            )}

          </section>


          {/* ERROR */}

          {error && (

            <div className="error-box">

              <X size={18} />

              <span>{error}</span>

            </div>

          )}


          {/* CHAT */}

          <section className="chat-card">

            <div className="chat-header">

              <div className="chat-title">

                <div className="ai-icon">
                  <Bot size={20} />
                </div>

                <div>

                  <h3>DevRAG Assistant</h3>

                  <span>
                    Ask anything about your document
                  </span>

                </div>

              </div>


              {uploadedFile && (

                <div className="document-badge">

                  <FileText size={15} />

                  {uploadedFile.name}

                </div>

              )}

            </div>


            {/* MESSAGES */}

            <div className="messages">

              {messages.length === 0 ? (

                <div className="empty-chat">

                  <div className="empty-icon">
                    <Sparkles size={28} />
                  </div>

                  <h2>
                    How can I help you?
                  </h2>

                  <p>
                    Upload a PDF and ask questions
                    about its content.
                  </p>


                  <div className="suggestions">

                    <button
                      onClick={() =>
                        setQuestion(
                          "Give me a summary of this document"
                        )
                      }
                    >
                      Summarize this document
                    </button>

                    <button
                      onClick={() =>
                        setQuestion(
                          "What are the main skills mentioned in my CV?"
                        )
                      }
                    >
                      Find my skills
                    </button>

                    <button
                      onClick={() =>
                        setQuestion(
                          "Tell me about the projects mentioned in my CV"
                        )
                      }
                    >
                      Find my projects
                    </button>

                  </div>

                </div>

              ) : (

                messages.map(
                  (message, index) => (

                    <div
                      key={index}
                      className={`message ${
                        message.role
                      }`}
                    >

                      <div className="message-avatar">

                        {message.role === "assistant" ? (
                          <Bot size={17} />
                        ) : (
                          "C"
                        )}

                      </div>


                      <div className="message-content">

                        <span className="message-name">

                          {message.role === "assistant"
                            ? "DevRAG"
                            : "You"}

                        </span>

                        <p>
                          {message.text}
                        </p>


                        {message.sources &&
                          message.sources.length > 0 && (

                            <div className="sources">

                              <small>
                                Sources
                              </small>

                              {message.sources.map(
                                (source, sourceIndex) => (

                                  <span
                                    key={sourceIndex}
                                    className="source-tag"
                                  >
                                    <FileText
                                      size={13}
                                    />
                                    {source}
                                  </span>

                                )
                              )}

                            </div>

                          )}

                      </div>

                    </div>

                  )
                )

              )}


              {asking && (

                <div className="message assistant">

                  <div className="message-avatar">
                    <Bot size={17} />
                  </div>

                  <div className="message-content">

                    <span className="message-name">
                      DevRAG
                    </span>

                    <div className="typing">

                      <span></span>
                      <span></span>
                      <span></span>

                    </div>

                  </div>

                </div>

              )}

            </div>


            {/* INPUT */}

            <div className="chat-input-area">

              <textarea
                value={question}
                onChange={(e) =>
                  setQuestion(e.target.value)
                }
                onKeyDown={handleKeyDown}
                placeholder={
                  uploadedFile
                    ? "Ask something about your document..."
                    : "Upload a PDF first..."
                }
                disabled={
                  asking || !uploadedFile
                }
                rows={1}
              />

              <button
                className="send-btn"
                onClick={askQuestion}
                disabled={
                  asking ||
                  !question.trim() ||
                  !uploadedFile
                }
              >

                {asking ? (
                  <Loader2
                    size={19}
                    className="spin"
                  />
                ) : (
                  <Send size={19} />
                )}

              </button>

            </div>


            <div className="input-footer">

              <span>
                DevRAG uses your uploaded documents
                to generate answers.
              </span>

              <span>
                Press Enter to send
              </span>

            </div>

          </section>

        </div>

      </main>

    </div>
  );
}

export default App;