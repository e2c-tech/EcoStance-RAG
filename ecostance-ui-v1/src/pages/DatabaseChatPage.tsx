import { useState, useEffect } from "react";
import { databaseAPI } from "../services/api";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import {
  Database,
  Plus,
  Trash2,
  Play,
  Save,
  AlertCircle,
  Edit2,
  Table,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { useDatabase } from "../context/DatabaseContext";

interface QueryResult {
  columns?: string[];
  rows?: Record<string, unknown>[];
  message?: string;
  rows_affected?: number;
}

interface ChatMessage {
  id: string;
  type: "question" | "sql" | "result" | "error";
  content: string;
  data?: QueryResult;
  timestamp: Date;
}

export default function DatabaseChatPage() {
  const {
    connections,
    selectedConnection,
    isConnected,
    schema,
    fetchConnections,
    connect,
    disconnect,
    setIsConnected,
    setSelectedConnection,
    setSchema,
    loadSchema, // Keep loadSchema if used elsewhere, but removing it from destructuring if it's causing warnings
  } = useDatabase();

  const [showConnectionForm, setShowConnectionForm] = useState(false);
  const [showQuickConnect, setShowQuickConnect] = useState(false);
  const [editingConnection, setEditingConnection] = useState<string | null>(
    null
  );
  const [question, setQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [dbConnecting, setDbConnecting] = useState(false);
  const [error, setError] = useState("");
  const [uploadingFile, setUploadingFile] = useState(false);
  const [showSchema, setShowSchema] = useState(false);

  const [connectionForm, setConnectionForm] = useState({
    name: "",
    db_type: "postgresql",
    host: "",
    port: "5432",
    username: "",
    password: "",
    database: "",
  });

  const [quickConnectForm, setQuickConnectForm] = useState({
    db_type: "postgresql",
    host: "",
    port: "5432",
    username: "",
    password: "",
    database: "",
    db_path: "",
  });

  useEffect(() => {
    fetchConnections();
  }, [fetchConnections]);

  const handleConnect = async (connectionName: string) => {
    try {
      setDbConnecting(true);
      setError("");
      await connect(connectionName);
      setChatHistory([]); // Clear chat history on new connection
    } catch (err: any) {
      setError(err.message || "Failed to connect to database");
    } finally {
      setDbConnecting(false);
    }
  };

  const handleSQLiteUpload = async (
    file: File,
    isQuickConnect: boolean = false
  ) => {
    try {
      setUploadingFile(true);
      setError("");

      console.log("Uploading SQLite file:", file.name);
      const result = (await databaseAPI.uploadSQLite(file)) as any;
      console.log("Upload result:", result);

      // Use the returned file_path
      if (isQuickConnect) {
        setQuickConnectForm({
          ...quickConnectForm,
          db_path: result.file_path,
        });
      } else {
        setConnectionForm({
          ...connectionForm,
          database: result.file_path,
        });
      }

      console.log("SQLite file uploaded successfully:", result.filename);
    } catch (err: any) {
      setError(err.message || "Failed to upload SQLite file");
      console.error("Upload error:", err);
    } finally {
      setUploadingFile(false);
    }
  };

  const handleQuickConnect = async () => {
    try {
      setLoading(true);
      setError("");

      const { db_type, host, port, username, password, database, db_path } =
        quickConnectForm;

      const dbUri =
        db_type === "sqlite"
          ? `sqlite:///${db_path}`
          : `${db_type}://${username}:${password}@${host}:${port}/${database}`;

      console.log(
        "Quick connecting to database with URI:",
        dbUri.replace(/:[^:@]+@/, ":****@")
      ); // Log without password
      const response = (await databaseAPI.connect(dbUri)) as any;
      console.log("Quick connect response:", response);

      setIsConnected(true);
      setSelectedConnection("Quick Connect");
      setShowQuickConnect(false);
      setChatHistory([]); // Clear chat history on new connection

      // Try to load schema
      try {
        const schemaData = (await databaseAPI.getSchema()) as any;
        console.log("Schema data:", schemaData);
        setSchema(schemaData);
      } catch (schemaErr) {
        console.warn("Failed to load schema:", schemaErr);
        // Schema is optional, don't fail the connection
      }
    } catch (err: any) {
      setError(err.message || "Failed to connect to database");
      console.error("Quick connect error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleEditConnection = async (name: string) => {
    try {
      setLoading(true);
      setError("");
      const conn = (await databaseAPI.loadConnection(name)) as any;

      if (!conn) {
        throw new Error("Connection details could not be loaded");
      }

      setConnectionForm({
        name: conn.name || "",
        db_type: conn.type || "postgresql",
        host: conn.host || "",
        port: String(conn.port || "5432"),
        username: conn.username || "",
        password: conn.password || "",
        database: conn.database || "",
      });
      setEditingConnection(name);
      setShowConnectionForm(true);
      setShowQuickConnect(false);
    } catch (err: any) {
      console.error("Edit connection error:", err);
      setError(err.message || "Failed to load connection details");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConnection = async () => {
    // Validate connection name
    if (!connectionForm.name.trim()) {
      setError("Connection name is required");
      return;
    }

    try {
      setLoading(true);
      setError("");

      // If editing, delete the old connection first (if name changed)
      if (editingConnection && editingConnection !== connectionForm.name) {
        await databaseAPI.deleteConnection(editingConnection);
      }

      await databaseAPI.saveConnection(connectionForm);
      await fetchConnections(true);
      setShowConnectionForm(false);
      setEditingConnection(null);
      setConnectionForm({
        name: "",
        db_type: "postgresql",
        host: "",
        port: "5432",
        username: "",
        password: "",
        database: "",
      });
    } catch (err: any) {
      setError(err.message || "Failed to save connection");
    } finally {
      setLoading(false);
    }
  };

  const handleCancelEdit = () => {
    setShowConnectionForm(false);
    setEditingConnection(null);
    setConnectionForm({
      name: "",
      db_type: "postgresql",
      host: "",
      port: "5432",
      username: "",
      password: "",
      database: "",
    });
  };

  const handleDeleteConnection = async (name: string) => {
    if (!confirm(`Delete connection "${name}"?`)) return;
    try {
      await databaseAPI.deleteConnection(name);
      await fetchConnections(true);
      if (selectedConnection === name) {
        disconnect();
      }
    } catch (err: any) {
      setError(err.message || "Failed to delete connection");
    }
  };

  const handleGenerateQuery = async () => {
    if (!question.trim()) return;

    const questionText = question;
    setQuestion(""); // Clear input immediately

    // Add question to chat
    const questionMsg: ChatMessage = {
      id: Date.now().toString(),
      type: "question",
      content: questionText,
      timestamp: new Date(),
    };
    setChatHistory((prev) => [...prev, questionMsg]);

    try {
      setLoading(true);
      setError("");
      const result = (await databaseAPI.generateQuery(questionText)) as {
        sql_query: string;
      };

      // Add SQL to chat
      const sqlMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: "sql",
        content: result.sql_query,
        timestamp: new Date(),
      };
      setChatHistory((prev) => [...prev, sqlMsg]);

      // Auto-execute the query
      await executeQuery(result.sql_query);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: "error",
        content: err.message || "Failed to generate query",
        timestamp: new Date(),
      };
      setChatHistory((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const executeQuery = async (sql: string) => {
    try {
      const result = (await databaseAPI.executeQuery(sql)) as any;
      console.log("Query result:", result);

      // Handle different response formats
      let formattedResult: QueryResult;

      if (Array.isArray(result)) {
        formattedResult = {
          rows: result,
          columns: result.length > 0 ? Object.keys(result[0]) : [],
        };
      } else if (result.rows) {
        formattedResult = result;
      } else {
        formattedResult = result;
      }

      // Add result to chat
      const resultMsg: ChatMessage = {
        id: (Date.now() + 2).toString(),
        type: "result",
        content: "",
        data: formattedResult,
        timestamp: new Date(),
      };
      setChatHistory((prev) => [...prev, resultMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 2).toString(),
        type: "error",
        content: err.message || "Failed to execute query",
        timestamp: new Date(),
      };
      setChatHistory((prev) => [...prev, errorMsg]);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text flex items-center gap-2">
          <Database className="w-6 h-6 text-primary" />
          Database Chat
        </h1>
        <p className="text-text-secondary mt-1">
          Connect to databases and query using natural language
        </p>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-error/10 border border-error/20 rounded-lg flex items-start gap-2">
          <AlertCircle className="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
          <p className="text-error">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Connections Sidebar */}
        <div className="lg:col-span-1">
          <Card className="p-4 bg-surface border-border">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-text">Connections</h2>
              <div className="flex gap-2">
                {/* <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setShowQuickConnect(!showQuickConnect);
                    setShowConnectionForm(false);
                  }}
                  title="Quick Connect (temporary)"
                >
                  <Database className="w-4 h-4" />
                </Button> */}
                {/* <div className="relative"> Add database</div> */}
                <Button
                  size="sm"
                  onClick={() => {
                    setShowConnectionForm(!showConnectionForm);
                    setShowQuickConnect(false);
                  }}
                  title="Save Connection"
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {showQuickConnect && (
              <div className="mb-4 p-3 bg-background rounded-lg space-y-2">
                <p className="text-xs text-text-secondary mb-2">
                  Quick Connect (not saved)
                </p>
                <select
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text focus:border-primary focus:outline-none"
                  value={quickConnectForm.db_type}
                  onChange={(e) =>
                    setQuickConnectForm({
                      ...quickConnectForm,
                      db_type: e.target.value,
                    })
                  }
                >
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="sqlite">SQLite</option>
                </select>
                {quickConnectForm.db_type !== "sqlite" ? (
                  <>
                    <input
                      type="text"
                      placeholder="Host (e.g., localhost)"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                      value={quickConnectForm.host}
                      onChange={(e) =>
                        setQuickConnectForm({
                          ...quickConnectForm,
                          host: e.target.value,
                        })
                      }
                    />
                    <input
                      type="text"
                      placeholder="Port"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                      value={quickConnectForm.port}
                      onChange={(e) =>
                        setQuickConnectForm({
                          ...quickConnectForm,
                          port: e.target.value,
                        })
                      }
                    />
                    <input
                      type="text"
                      placeholder="Username"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                      value={quickConnectForm.username}
                      onChange={(e) =>
                        setQuickConnectForm({
                          ...quickConnectForm,
                          username: e.target.value,
                        })
                      }
                    />
                    <input
                      type="password"
                      placeholder="Password"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                      value={quickConnectForm.password}
                      onChange={(e) =>
                        setQuickConnectForm({
                          ...quickConnectForm,
                          password: e.target.value,
                        })
                      }
                    />
                    <input
                      type="text"
                      placeholder="Database Name"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                      value={quickConnectForm.database}
                      onChange={(e) =>
                        setQuickConnectForm({
                          ...quickConnectForm,
                          database: e.target.value,
                        })
                      }
                    />
                  </>
                ) : (
                  <div className="space-y-2">
                    <label className="text-xs text-text-secondary">
                      Upload SQLite Database File
                    </label>
                    <input
                      type="file"
                      accept=".db,.sqlite,.sqlite3"
                      disabled={uploadingFile}
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:bg-primary file:text-white hover:file:bg-primary/90 disabled:opacity-50"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          handleSQLiteUpload(file, true);
                        }
                      }}
                    />
                    {uploadingFile && (
                      <p className="text-xs text-primary">Uploading file...</p>
                    )}
                    <p className="text-xs text-text-secondary">
                      Or enter path:
                    </p>
                    <input
                      type="text"
                      placeholder="/path/to/db.sqlite"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                      value={quickConnectForm.db_path}
                      onChange={(e) =>
                        setQuickConnectForm({
                          ...quickConnectForm,
                          db_path: e.target.value,
                        })
                      }
                    />
                  </div>
                )}
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={handleQuickConnect}
                    disabled={loading}
                  >
                    <Play className="w-4 h-4 mr-1" />
                    Connect
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowQuickConnect(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {showConnectionForm && (
              <div className="mb-4 p-3 bg-background rounded-lg space-y-2">
                <p className="text-xs text-text-secondary mb-2">
                  {editingConnection
                    ? `Edit Connection: ${editingConnection}`
                    : "Save Connection"}
                </p>
                <input
                  type="text"
                  placeholder="Connection Name"
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                  value={connectionForm.name}
                  onChange={(e) =>
                    setConnectionForm({
                      ...connectionForm,
                      name: e.target.value,
                    })
                  }
                />
                <select
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text focus:border-primary focus:outline-none"
                  value={connectionForm.db_type}
                  onChange={(e) =>
                    setConnectionForm({
                      ...connectionForm,
                      db_type: e.target.value,
                    })
                  }
                >
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="sqlite">SQLite</option>
                </select>
                {connectionForm.db_type !== "sqlite" ? (
                  <>
                    <input
                      type="text"
                      placeholder="Host"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                      value={connectionForm.host}
                      onChange={(e) =>
                        setConnectionForm({
                          ...connectionForm,
                          host: e.target.value,
                        })
                      }
                    />
                    <input
                      type="text"
                      placeholder="Port"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                      value={connectionForm.port}
                      onChange={(e) =>
                        setConnectionForm({
                          ...connectionForm,
                          port: e.target.value,
                        })
                      }
                    />
                    <input
                      type="text"
                      placeholder="Username"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                      value={connectionForm.username}
                      onChange={(e) =>
                        setConnectionForm({
                          ...connectionForm,
                          username: e.target.value,
                        })
                      }
                    />
                    <input
                      type="password"
                      placeholder="Password"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                      value={connectionForm.password}
                      onChange={(e) =>
                        setConnectionForm({
                          ...connectionForm,
                          password: e.target.value,
                        })
                      }
                    />
                    <input
                      type="text"
                      placeholder="Database Name"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                      value={connectionForm.database}
                      onChange={(e) =>
                        setConnectionForm({
                          ...connectionForm,
                          database: e.target.value,
                        })
                      }
                    />
                  </>
                ) : (
                  <div className="space-y-2">
                    <label className="text-xs text-text-secondary">
                      Upload SQLite Database File
                    </label>
                    <input
                      type="file"
                      accept=".db,.sqlite,.sqlite3"
                      disabled={uploadingFile}
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:bg-primary file:text-white hover:file:bg-primary/90 disabled:opacity-50"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          handleSQLiteUpload(file, false);
                        }
                      }}
                    />
                    {uploadingFile && (
                      <p className="text-xs text-primary">Uploading file...</p>
                    )}
                    <p className="text-xs text-text-secondary">
                      Or enter path:
                    </p>
                    <input
                      type="text"
                      placeholder="./data/sqlite.db"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                      value={connectionForm.database}
                      onChange={(e) =>
                        setConnectionForm({
                          ...connectionForm,
                          database: e.target.value,
                        })
                      }
                    />
                  </div>
                )}
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={handleSaveConnection}
                    disabled={loading || !connectionForm.name.trim()}
                  >
                    <Save className="w-4 h-4 mr-1" />
                    {editingConnection ? "Update" : "Save"}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleCancelEdit}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            <div className="space-y-2">
              {connections.length === 0 && (
                <div className="text-xs text-text-secondary uppercase">
                  No Database Found add it
                </div>
              )}
              {connections.map((conn) => (
                <div
                  key={conn.name}
                  className={`p-3 rounded-lg border transition-colors ${
                    selectedConnection === conn.name
                      ? "bg-primary/10 border-primary"
                      : "bg-surface border-border hover:bg-surface-hover"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div
                      className="flex-1 min-w-0 cursor-pointer"
                      // onClick={() => handleConnect(conn.name)}
                    >
                      <div className="font-medium text-sm text-text truncate">
                        {conn.name}
                      </div>
                      <div
                        className="text-xs text-text-secondary truncate"
                        title={conn.database}
                      >
                        {conn.type} -{" "}
                        {conn.type === "sqlite"
                          ? conn.database.split("/").pop() || conn.database
                          : conn.database}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditConnection(conn.name);
                        }}
                        className="text-text-secondary hover:text-primary p-1"
                        title="Edit connection"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteConnection(conn.name);
                        }}
                        className="text-text-secondary hover:text-error p-1"
                        title="Delete connection"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <button
                        disabled={loading}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleConnect(conn.name);
                        }}
                        className={`p-1 ${
                          selectedConnection === conn.name && isConnected
                            ? "text-green-500"
                            : "text-text-secondary hover:text-green-500"
                        } disabled:opacity-50`}
                        title={
                          selectedConnection === conn.name && isConnected
                            ? "Connected"
                            : "Connect"
                        }
                      >
                        <Play className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Schema Display */}
          {isConnected && (
            <Card className="p-4 bg-surface border-border mt-4">
              <button
                onClick={() => setShowSchema(!showSchema)}
                className="flex items-center gap-2 text-sm font-medium text-text hover:text-primary w-full mb-3"
              >
                {showSchema ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
                <Table className="w-4 h-4" />
                Schema
                {schema && schema.tables && (
                  <span className="text-xs text-text-secondary ml-auto">
                    {schema.tables.length} tables
                  </span>
                )}
              </button>
              {showSchema && (
                <div>
                  {schema && schema.tables && schema.tables.length > 0 ? (
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {schema.tables.map((table) => (
                        <div
                          key={table.name}
                          className="text-xs border-l-2 border-primary pl-3"
                        >
                          <div className="font-semibold text-text mb-1">
                            {table.name}
                          </div>
                          <div className="space-y-0.5">
                            {table.columns?.map((col) => (
                              <div
                                key={col.name}
                                className="text-text-secondary flex items-center gap-2"
                              >
                                <span className="font-mono">{col.name}</span>
                                <span className="text-primary/60 text-[10px]">
                                  {col.type}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-text-secondary">
                      Schema not available
                    </div>
                  )}
                </div>
              )}
            </Card>
          )}
        </div>

        {/* Main Chat Area */}
        <div className="lg:col-span-2 flex flex-col h-[calc(100vh-12rem)]">
          {connections.length === 0 ? (
            <Card className="p-8 text-center bg-surface border-border">
              <Database className="w-12 h-12 text-text-secondary mx-auto mb-4" />
              <h3 className="text-lg font-medium text-text mb-2">
                No Database Found
              </h3>
              <p className="text-text-secondary">
                Add a database connection to get started
              </p>
            </Card>
          ) : !isConnected ? (
            <Card className="p-8 text-center bg-surface border-border">
              <Database className="w-12 h-12 text-text-secondary mx-auto mb-4" />
              <h3 className="text-lg font-medium text-text mb-2">
                No Database Connected
              </h3>
              <p className="text-text-secondary">
                Select a database connection to get started
              </p>
            </Card>
          ) : (
            <>
              {/* Chat History */}
              <div className="flex-1 overflow-y-auto mb-4 space-y-4">
                {chatHistory.map((msg) => (
                  <div key={msg.id}>
                    {msg.type === "question" && (
                      <div className="flex justify-end">
                        <div className="bg-primary text-white px-4 py-2 rounded-lg max-w-[80%]">
                          {msg.content}
                        </div>
                      </div>
                    )}

                    {msg.type === "sql" && (
                      <Card className="p-3 bg-surface border-border">
                        <div className="text-xs text-text-secondary mb-2">
                          Generated SQL
                        </div>
                        <pre className="bg-background text-text p-3 rounded text-sm overflow-x-auto">
                          {msg.content}
                        </pre>
                      </Card>
                    )}

                    {msg.type === "result" && msg.data && (
                      <Card className="p-3 bg-surface border-border">
                        <div className="text-xs text-text-secondary mb-2">
                          Results
                        </div>
                        {msg.data.rows && msg.data.rows.length > 0 ? (
                          <div className="overflow-x-auto">
                            <div className="mb-2 text-xs text-text-secondary">
                              {msg.data.rows.length} row
                              {msg.data.rows.length !== 1 ? "s" : ""}
                            </div>
                            <table className="w-full text-xs border border-border">
                              <thead className="bg-background">
                                <tr>
                                  {Object.keys(msg.data.rows[0]).map((col) => (
                                    <th
                                      key={col}
                                      className="px-3 py-1 text-left font-medium text-text border-b border-border"
                                    >
                                      {col}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-border">
                                {msg.data.rows.map((row, idx) => (
                                  <tr
                                    key={idx}
                                    className="hover:bg-surface-hover"
                                  >
                                    {Object.values(row).map((val, i) => (
                                      <td
                                        key={i}
                                        className="px-3 py-1 text-text"
                                      >
                                        {val === null ? (
                                          <span className="text-text-secondary italic">
                                            null
                                          </span>
                                        ) : (
                                          String(val)
                                        )}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <p className="text-xs text-text-secondary">
                            {msg.data.message ||
                              `Query executed. ${
                                msg.data.rows_affected || 0
                              } rows affected.`}
                          </p>
                        )}
                      </Card>
                    )}

                    {msg.type === "error" && (
                      <Card className="p-3 bg-error/10 border-error/20">
                        <div className="flex items-start gap-2">
                          <AlertCircle className="w-4 h-4 text-error flex-shrink-0 mt-0.5" />
                          <p className="text-sm text-error">{msg.content}</p>
                        </div>
                      </Card>
                    )}
                  </div>
                ))}

{dbConnecting && (
                  <div className="flex justify-center">
                    <div className="animate-pulse text-text-secondary text-sm">
                      Connecting to database ...
                    </div>
                  </div>
                )}
                {loading && (
                  <div className="flex justify-center">
                    <div className="animate-pulse text-text-secondary text-sm">
                      AI Thinking ...
                    </div>
                  </div>
                )}
              </div>

              {/* Input Area */}
              <Card className="p-4 bg-surface border-border">
                <div className="flex gap-2 items-center">
                  <textarea
                    className="flex-1 px-3 py-2 bg-background border border-border rounded-lg resize-none text-text placeholder:text-text-secondary focus:border-primary focus:outline-none"
                    rows={2}
                    placeholder="Ask a question about your database..."
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleGenerateQuery();
                      }
                    }}
                  />
                  <Button
                    onClick={handleGenerateQuery}
                    disabled={loading || !question.trim()}
                  >
                    <Play className="w-4 h-4" />
                  </Button>
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
