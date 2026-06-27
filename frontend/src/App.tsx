import {
  Add,
  Api,
  CheckCircle,
  Close,
  DataObject,
  HealthAndSafety,
  Hub,
  PlayArrow,
  Search,
  Send,
  Storage,
} from "@mui/icons-material";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Drawer,
  IconButton,
  InputBase,
  LinearProgress,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { health, ingestStatus, queryCodebase, startIngest } from "./api";
import type { ChatMessage, HealthResponse, IngestStatus, QueryOptions, QueryResult, ToolCall } from "./types";

const DEMO_QUERIES = [
  "How does the ingest pipeline work?",
  "Where does sync_file delete chunks from vector store?",
  "Where does the Python parser extract classes and functions?",
  "How does Qdrant search filter chunks?",
  "How does the health endpoint check Qdrant and Neo4j?",
];

function shortId(): string {
  return Math.random().toString(16).slice(2, 10);
}

function compactText(text: string, length = 34): string {
  return text.length <= length ? text : `${text.slice(0, length - 1)}...`;
}

function scoreColor(score: number): "success" | "primary" | "warning" {
  if (score >= 0.7) return "success";
  if (score >= 0.45) return "primary";
  return "warning";
}

function buildSummary(results: QueryResult[]): string {
  if (!results.length) {
    return "No matching context was found. Try lowering the threshold or ingesting the repository first.";
  }
  const top = results[0];
  return `Found ${results.length} relevant code segments. Top match is ${top.metadata.entity_name ?? "unknown"} in ${
    top.metadata.source_file ?? "unknown file"
  }.`;
}

function HealthStatusBadge() {
  const [status, setStatus] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const run = async () => {
      try {
        const response = await health();
        if (mounted) {
          setStatus(response);
          setError(null);
        }
      } catch (exc) {
        if (mounted) setError(exc instanceof Error ? exc.message : "Health check failed");
      }
    };
    run();
    const timer = window.setInterval(run, 30000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  const healthy = status?.status === "ok" && !error;
  return (
    <Chip
      size="small"
      variant="outlined"
      icon={<HealthAndSafety sx={{ color: healthy ? "success.main" : "error.main" }} />}
      label={healthy ? "Healthy" : "Degraded"}
      sx={{ fontWeight: 700 }}
    />
  );
}

function Sidebar({
  sessions,
  activeSession,
  onNewChat,
  onSelectDemo,
  onSelectSession,
}: {
  sessions: ChatMessage[][];
  activeSession: number;
  onNewChat: () => void;
  onSelectDemo: (query: string) => void;
  onSelectSession: (index: number) => void;
}) {
  return (
    <Box sx={{ width: 300, bgcolor: "background.paper", borderRight: 1, borderColor: "divider", display: "flex", flexDirection: "column" }}>
      <Stack direction="row" alignItems="center" spacing={1.5} sx={{ px: 3, height: 72 }}>
        <Avatar variant="rounded" sx={{ bgcolor: "primary.main", width: 40, height: 40 }}>
          <Hub />
        </Avatar>
        <Box>
          <Typography variant="h6" fontSize={18}>
            Knowledge Hub
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Codebase Assistant
          </Typography>
        </Box>
      </Stack>

      <Box sx={{ px: 2.5, pb: 2 }}>
        <Button fullWidth variant="outlined" startIcon={<Add />} onClick={onNewChat} sx={{ justifyContent: "flex-start", py: 1.4 }}>
          New query
        </Button>
      </Box>

      <Box sx={{ flex: 1, overflow: "auto", px: 2 }}>
        <Typography variant="overline" color="text.secondary" fontWeight={800}>
          Session History
        </Typography>
        <List dense disablePadding sx={{ mb: 3 }}>
          {sessions.length === 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ px: 1, py: 1.5 }}>
              No sessions yet
            </Typography>
          )}
          {sessions.map((session, index) => {
            const firstUser = session.find((item) => item.role === "user");
            return (
              <ListItemButton
                key={`${index}-${firstUser?.id ?? "empty"}`}
                selected={index === activeSession}
                onClick={() => onSelectSession(index)}
                sx={{ borderRadius: 1, mb: 0.5, "&.Mui-selected": { bgcolor: "primary.light", color: "primary.dark" } }}
              >
                <ListItemIcon sx={{ minWidth: 34 }}>
                  <Search fontSize="small" />
                </ListItemIcon>
                <ListItemText primary={compactText(firstUser?.content ?? "New query", 25)} />
              </ListItemButton>
            );
          })}
        </List>

        <Typography variant="overline" color="text.secondary" fontWeight={800}>
          Demo Queries
        </Typography>
        <List dense disablePadding>
          {DEMO_QUERIES.map((query) => (
            <ListItemButton key={query} onClick={() => onSelectDemo(query)} sx={{ borderRadius: 1, mb: 0.5 }}>
              <ListItemIcon sx={{ minWidth: 34 }}>
                <DataObject fontSize="small" />
              </ListItemIcon>
              <ListItemText primary={compactText(query, 28)} />
            </ListItemButton>
          ))}
        </List>
      </Box>

      <Box sx={{ p: 2.5, borderTop: 1, borderColor: "divider" }}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Avatar sx={{ bgcolor: "#eef2ff", color: "primary.main", fontWeight: 800 }}>KH</Avatar>
          <Box>
            <Typography variant="body2" fontWeight={800}>
              AI Agent
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Knowledge Hub Demo
            </Typography>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
}

function ToolCallCard({ toolCall }: { toolCall: ToolCall }) {
  const [tab, setTab] = useState(1);
  const payload = tab === 0 ? toolCall.input : toolCall.output;

  return (
    <Paper variant="outlined" sx={{ borderRadius: 2, overflow: "hidden", mb: 2, maxWidth: 960 }}>
      <Stack direction="row" alignItems="center" spacing={1.25} sx={{ px: 2, py: 1.4, borderBottom: 1, borderColor: "divider" }}>
        <Api fontSize="small" color="action" />
        <Typography variant="body2" fontWeight={800}>
          {toolCall.name}
        </Typography>
        <Chip
          size="small"
          icon={<CheckCircle />}
          label={toolCall.status}
          color={toolCall.status === "SUCCESS" ? "success" : "error"}
          variant="outlined"
          sx={{ ml: "auto", fontWeight: 800 }}
        />
      </Stack>
      <Tabs value={tab} onChange={(_, next) => setTab(next)} sx={{ px: 2, minHeight: 42 }}>
        <Tab label="Input" sx={{ minHeight: 42, fontWeight: 800 }} />
        <Tab label="Output" sx={{ minHeight: 42, fontWeight: 800 }} />
      </Tabs>
      <Box sx={{ bgcolor: "#101827", color: "#e5e7eb", p: 2, maxHeight: 300, overflow: "auto", fontFamily: "JetBrains Mono, Consolas, monospace", fontSize: 13 }}>
        <pre>{JSON.stringify(payload, null, 2)}</pre>
      </Box>
    </Paper>
  );
}

function ResultTable({ results, onOpen }: { results: QueryResult[]; onOpen: (result: QueryResult) => void }) {
  if (!results.length) return null;
  return (
    <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2, maxWidth: 960 }}>
      <Table size="small">
        <TableHead sx={{ bgcolor: "#f9fafb" }}>
          <TableRow>
            <TableCell>#</TableCell>
            <TableCell>File / Entity</TableCell>
            <TableCell>Type</TableCell>
            <TableCell>Score</TableCell>
            <TableCell>Lines</TableCell>
            <TableCell>Graph Context</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {results.map((result, index) => (
            <TableRow key={result.chunk_id} hover onClick={() => onOpen(result)} sx={{ cursor: "pointer" }}>
              <TableCell>{index + 1}</TableCell>
              <TableCell>
                <Typography variant="caption" color="text.secondary">
                  {result.metadata.source_file}
                </Typography>
                <Typography variant="body2" fontWeight={800}>
                  {result.metadata.entity_name}
                </Typography>
              </TableCell>
              <TableCell>
                <Chip size="small" variant="outlined" label={result.metadata.chunk_type ?? "chunk"} />
              </TableCell>
              <TableCell>
                <Chip size="small" color={scoreColor(result.relevance_score)} label={result.relevance_score.toFixed(3)} sx={{ fontWeight: 800 }} />
              </TableCell>
              <TableCell sx={{ fontFamily: "Consolas, monospace", fontSize: 12 }}>
                {result.metadata.line_start ?? "-"}-{result.metadata.line_end ?? "-"}
              </TableCell>
              <TableCell>
                <Stack direction="row" gap={0.5} flexWrap="wrap">
                  {result.graph_context.length === 0 && (
                    <Typography variant="caption" color="text.secondary">
                      -
                    </Typography>
                  )}
                  {result.graph_context.slice(0, 3).map((context, contextIndex) => (
                    <Chip
                      key={`${result.chunk_id}-${context.entity}-${contextIndex}`}
                      size="small"
                      label={`${context.entity ?? "node"} ${context.relationship ?? ""}`}
                      variant="outlined"
                    />
                  ))}
                </Stack>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function ResultDetailDrawer({ result, onClose }: { result: QueryResult | null; onClose: () => void }) {
  return (
    <Drawer anchor="right" open={Boolean(result)} onClose={onClose}>
      <Box sx={{ width: { xs: "100vw", sm: 680 }, height: "100%", display: "flex", flexDirection: "column" }}>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ p: 2, borderBottom: 1, borderColor: "divider" }}>
          <Storage color="primary" />
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography fontWeight={900} noWrap>
              {result?.metadata.entity_name}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap>
              {result?.metadata.source_file}:{result?.metadata.line_start}-{result?.metadata.line_end}
            </Typography>
          </Box>
          <IconButton onClick={onClose}>
            <Close />
          </IconButton>
        </Stack>
        <Box sx={{ p: 2, bgcolor: "#101827", color: "#e5e7eb", flex: 1, overflow: "auto", fontFamily: "JetBrains Mono, Consolas, monospace", fontSize: 13 }}>
          <pre>{result?.content}</pre>
        </Box>
        <Stack direction="row" spacing={1} sx={{ p: 2, borderTop: 1, borderColor: "divider" }}>
          <Chip label={`score ${result?.relevance_score.toFixed(3) ?? "-"}`} />
          <Chip label={`vector ${result?.score_breakdown.vector_score.toFixed(3) ?? "-"}`} />
          <Chip label={`graph ${result?.score_breakdown.graph_score.toFixed(3) ?? "-"}`} />
        </Stack>
      </Box>
    </Drawer>
  );
}

function IngestDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [path, setPath] = useState("app");
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setLoading(true);
    setError(null);
    setStatus(null);
    try {
      const job = await startIngest(path);
      let done = false;
      while (!done) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        const next = await ingestStatus(job.job_id);
        setStatus(next);
        done = next.status === "completed" || next.status === "failed";
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Ingest failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onClose={loading ? undefined : onClose} fullWidth maxWidth="sm">
      <DialogTitle>Ingest source</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField label="Source path" value={path} onChange={(event) => setPath(event.target.value)} fullWidth />
          {loading && <LinearProgress />}
          {status && (
            <Alert severity={status.status === "failed" ? "error" : status.status === "completed" ? "success" : "info"}>
              {status.status}: files={status.files_processed}, chunks={status.chunks_created}, nodes={status.nodes_created}
            </Alert>
          )}
          {error && <Alert severity="error">{error}</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Close
        </Button>
        <Button variant="contained" onClick={submit} disabled={loading || !path.trim()}>
          {loading ? "Ingesting..." : "Start ingest"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function MessageList({ messages, onOpenResult }: { messages: ChatMessage[]; onOpenResult: (result: QueryResult) => void }) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (!messages.length) {
    return (
      <Stack alignItems="center" justifyContent="center" sx={{ height: "100%", textAlign: "center", color: "text.secondary" }} spacing={2}>
        <Avatar sx={{ width: 64, height: 64, bgcolor: "primary.light", color: "primary.main" }}>
          <Hub fontSize="large" />
        </Avatar>
        <Box>
          <Typography variant="h6" color="text.primary">
            Knowledge Hub Assistant
          </Typography>
          <Typography>Ask about your codebase and inspect the retrieved context.</Typography>
        </Box>
      </Stack>
    );
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 1100, mx: "auto", width: "100%" }}>
      {messages.map((message) =>
        message.role === "user" ? (
          <Box key={message.id} sx={{ display: "flex", justifyContent: "flex-end" }}>
            <Paper sx={{ bgcolor: "primary.main", color: "white", px: 2, py: 1.5, borderRadius: 3, maxWidth: "70%" }}>
              <Typography>{message.content}</Typography>
            </Paper>
          </Box>
        ) : (
          <Stack key={message.id} direction="row" spacing={1.5} alignItems="flex-start">
            <Avatar sx={{ bgcolor: "primary.light", color: "primary.main", width: 36, height: 36 }}>
              <Hub fontSize="small" />
            </Avatar>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="body2" fontWeight={900} sx={{ mb: 1 }}>
                Knowledge Hub
              </Typography>
              {message.loading ? (
                <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, maxWidth: 640 }}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <CircularProgress size={18} />
                    <Typography color="text.secondary">Running hybrid retrieval...</Typography>
                  </Stack>
                </Paper>
              ) : (
                <>
                  {message.toolCall && <ToolCallCard toolCall={message.toolCall} />}
                  <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, mb: 2, maxWidth: 960 }}>
                    <Typography>{message.content}</Typography>
                  </Paper>
                  {message.results && <ResultTable results={message.results} onOpen={onOpenResult} />}
                </>
              )}
            </Box>
          </Stack>
        ),
      )}
      <div ref={bottomRef} />
    </Stack>
  );
}

function QueryInput({
  onSubmit,
  loading,
  graphEnabled,
  setGraphEnabled,
  topK,
  setTopK,
  initialQuery,
}: {
  onSubmit: (query: string) => void;
  loading: boolean;
  graphEnabled: boolean;
  setGraphEnabled: (enabled: boolean) => void;
  topK: number;
  setTopK: (value: number) => void;
  initialQuery: string;
}) {
  const [query, setQuery] = useState(initialQuery);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!query.trim() || loading) return;
    onSubmit(query.trim());
    setQuery("");
  }

  return (
    <Paper component="form" onSubmit={submit} sx={{ display: "flex", alignItems: "center", gap: 1, borderRadius: 999, px: 2, py: 1, boxShadow: 3 }}>
      <InputBase
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Ask about your codebase..."
        fullWidth
        disabled={loading}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) submit(event);
        }}
      />
      <Tooltip title="Toggle graph expansion">
        <Chip
          size="small"
          label={graphEnabled ? "Graph ON" : "Graph OFF"}
          color={graphEnabled ? "success" : "default"}
          variant="outlined"
          onClick={() => setGraphEnabled(!graphEnabled)}
          sx={{ fontWeight: 800 }}
        />
      </Tooltip>
      <Select value={topK} onChange={(event) => setTopK(Number(event.target.value))} size="small" variant="standard" disableUnderline sx={{ minWidth: 72 }}>
        <MenuItem value={3}>Top 3</MenuItem>
        <MenuItem value={5}>Top 5</MenuItem>
        <MenuItem value={10}>Top 10</MenuItem>
      </Select>
      <IconButton type="submit" disabled={loading || !query.trim()} sx={{ bgcolor: "primary.main", color: "white", "&:hover": { bgcolor: "primary.dark" }, "&.Mui-disabled": { bgcolor: "grey.300" } }}>
        {loading ? <CircularProgress size={18} color="inherit" /> : <Send />}
      </IconButton>
    </Paper>
  );
}

export default function App() {
  const [sessions, setSessions] = useState<ChatMessage[][]>(() => {
    const saved = window.localStorage.getItem("knowledge-hub-sessions");
    return saved ? (JSON.parse(saved) as ChatMessage[][]) : [];
  });
  const [activeSession, setActiveSession] = useState(0);
  const [messages, setMessages] = useState<ChatMessage[]>(() => sessions[0] ?? []);
  const [loading, setLoading] = useState(false);
  const [graphEnabled, setGraphEnabled] = useState(true);
  const [topK, setTopK] = useState(5);
  const [threshold] = useState(0.35);
  const [selectedResult, setSelectedResult] = useState<QueryResult | null>(null);
  const [ingestOpen, setIngestOpen] = useState(false);
  const [draftQuery, setDraftQuery] = useState("");

  useEffect(() => {
    window.localStorage.setItem("knowledge-hub-sessions", JSON.stringify(sessions));
  }, [sessions]);

  function persistSession(nextMessages: ChatMessage[]) {
    setMessages(nextMessages);
    setSessions((current) => {
      const next = [...current];
      next[activeSession] = nextMessages;
      return next;
    });
  }

  async function submitQuery(queryText: string) {
    const userMessage: ChatMessage = { id: shortId(), role: "user", content: queryText };
    const loadingMessage: ChatMessage = { id: shortId(), role: "assistant", content: "", loading: true };
    const nextMessages = [...messages, userMessage, loadingMessage];
    persistSession(nextMessages);
    setLoading(true);

    const options: QueryOptions = {
      enable_graph_expansion: graphEnabled,
      max_hops: 2,
      similarity_threshold: threshold,
      filters: {},
    };

    try {
      const response = await queryCodebase(queryText, topK, options);
      const toolCall: ToolCall = {
        name: "hybrid_retrieval",
        status: "SUCCESS",
        input: { query: queryText, top_k: topK, ...options },
        output: { total_results: response.total_results, retrieval_method: response.retrieval_method, results: response.results },
      };
      const assistantMessage: ChatMessage = {
        id: loadingMessage.id,
        role: "assistant",
        content: buildSummary(response.results),
        toolCall,
        results: response.results,
      };
      persistSession([...nextMessages.slice(0, -1), assistantMessage]);
    } catch (exc) {
      const assistantMessage: ChatMessage = {
        id: loadingMessage.id,
        role: "assistant",
        content: exc instanceof Error ? exc.message : "Query failed",
        toolCall: {
          name: "hybrid_retrieval",
          status: "ERROR",
          input: { query: queryText, top_k: topK, ...options },
          output: { error: exc instanceof Error ? exc.message : "Query failed" },
        },
        results: [],
      };
      persistSession([...nextMessages.slice(0, -1), assistantMessage]);
    } finally {
      setLoading(false);
    }
  }

  function newChat() {
    const index = sessions.length;
    setSessions((current) => [...current, []]);
    setActiveSession(index);
    setMessages([]);
  }

  const sessionToken = useMemo(() => `session-${shortId()}`, []);

  return (
    <Box sx={{ height: "100vh", display: "flex", bgcolor: "background.default" }}>
      <Sidebar
        sessions={sessions}
        activeSession={activeSession}
        onNewChat={newChat}
        onSelectDemo={(query) => setDraftQuery(query)}
        onSelectSession={(index) => {
          setActiveSession(index);
          setMessages(sessions[index] ?? []);
        }}
      />
      <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <Stack direction="row" alignItems="center" spacing={1.5} sx={{ height: 64, px: 3, bgcolor: "background.paper", borderBottom: 1, borderColor: "divider" }}>
          <Typography variant="h6" sx={{ flex: 1 }}>
            Knowledge Hub Assistant
          </Typography>
          <HealthStatusBadge />
          <Chip size="small" label={graphEnabled ? "Graph ON" : "Graph OFF"} color={graphEnabled ? "success" : "default"} variant="outlined" sx={{ fontWeight: 800 }} />
          <Chip size="small" label={sessionToken} variant="outlined" />
          <Button variant="contained" startIcon={<PlayArrow />} onClick={() => setIngestOpen(true)}>
            Ingest
          </Button>
        </Stack>

        <Box sx={{ flex: 1, overflow: "auto", p: 3 }}>
          <MessageList messages={messages} onOpenResult={setSelectedResult} />
        </Box>

        <Box sx={{ px: { xs: 2, md: 6 }, pb: 2, pt: 1, bgcolor: "background.default" }}>
          <QueryInput
            onSubmit={submitQuery}
            loading={loading}
            graphEnabled={graphEnabled}
            setGraphEnabled={setGraphEnabled}
            topK={topK}
            setTopK={setTopK}
            initialQuery={draftQuery}
          />
          <Divider sx={{ my: 1.5 }} />
          <Typography variant="caption" color="text.secondary" align="center" display="block">
            Knowledge Hub can surface stale or partial context. Verify critical code paths before acting.
          </Typography>
        </Box>
      </Box>
      <ResultDetailDrawer result={selectedResult} onClose={() => setSelectedResult(null)} />
      <IngestDialog open={ingestOpen} onClose={() => setIngestOpen(false)} />
    </Box>
  );
}
