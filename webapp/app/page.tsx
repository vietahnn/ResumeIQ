"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Zap } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { ResumePanel } from "@/components/ResumePanel";
import { ChatCanvas } from "@/components/ChatCanvas";
import { ResumeItem, ChatSessionItem, ChatMessageItem } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const BOT_HTTP_BASE = process.env.NEXT_PUBLIC_BOT_HTTP_BASE || "http://localhost:8001";
const BOT_WS_BASE = process.env.NEXT_PUBLIC_BOT_WS_BASE || "ws://localhost:8001";

const DEFAULT_RESUMES: ResumeItem[] = [
  {
    id: "mock_res_1",
    file_name: "Alex_Chen_Staff_Backend.pdf",
    status: "COMPLETED",
    parsed_data: { ats_score: 92 },
    created_at: new Date().toISOString(),
  },
  {
    id: "mock_res_2",
    file_name: "Alex_Chen_ML_Lead.pdf",
    status: "COMPLETED",
    parsed_data: { ats_score: 84 },
    created_at: new Date().toISOString(),
  },
];

export default function HomePage() {
  const [resumes, setResumes] = useState<ResumeItem[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>("mock_res_1");
  const [targetJd, setTargetJd] = useState<string>("");

  const [sessions, setSessions] = useState<ChatSessionItem[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);

  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadStatusText, setUploadStatusText] = useState<string>("");

  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [currentAiTokenStream, setCurrentAiTokenStream] = useState<string>("");
  const [agentStatusText, setAgentStatusText] = useState<string | null>(null);
  const [isWsConnected, setIsWsConnected] = useState<boolean>(false);

  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const initSessionId = "session_" + Math.random().toString(36).substring(2, 9);
    setCurrentSessionId(initSessionId);
    fetchResumes();
    fetchSessions();
  }, []);

  const fetchResumes = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/resumes/?limit=20`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setResumes(data);
          setSelectedResumeId(data[0].id);
        }
      }
    } catch (err) {
      console.error("Failed fetching resumes:", err);
    }
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${BOT_HTTP_BASE}/api/v1/chat/sessions`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          setSessions(data);
        }
      }
    } catch (err) {
      console.error("Failed fetching sessions:", err);
    }
  };

  const connectWebSocket = useCallback((sId: string) => {
    if (socketRef.current) {
      socketRef.current.onclose = null;
      socketRef.current.close();
    }

    const ws = new WebSocket(`${BOT_WS_BASE}/ws/chat/${sId}`);
    socketRef.current = ws;

    ws.onopen = () => {
      setIsWsConnected(true);
    };

    ws.onclose = () => {
      setIsWsConnected(false);
      setTimeout(() => {
        if (socketRef.current && socketRef.current.readyState === WebSocket.CLOSED) {
          connectWebSocket(sId);
        }
      }, 2500);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleSocketEvent(data);
      } catch (e) {
        console.error("Invalid JSON over WS:", e);
      }
    };
  }, []);

  useEffect(() => {
    if (currentSessionId) {
      connectWebSocket(currentSessionId);
    }
    return () => {
      if (socketRef.current) {
        socketRef.current.onclose = null;
        socketRef.current.close();
      }
    };
  }, [currentSessionId, connectWebSocket]);

  const handleSocketEvent = (data: any) => {
    const isSuccess = data.status === "SUCCESS";
    const isFailed = data.status === "FAILED";
    const isStatus = data.type === "status" || data.status === "PROGRESS" || data.status === "DISPATCHED";

    if (isSuccess) {
      setAgentStatusText(null);
      setIsStreaming(false);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.content,
          extra_metadata: data.metadata || { source: data.metadata?.source },
        },
      ]);
      fetchSessions();
    } else if (isFailed) {
      setAgentStatusText(null);
      setIsStreaming(false);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `**Error during analysis:** ${data.content || "Task failed"}`,
        },
      ]);
    } else if (isStatus) {
      const taskLabel = data.task_type || "WORKER";
      setIsStreaming(true);
      setAgentStatusText(`[${taskLabel}] ${data.message || data.content || "Processing..."}`);
    } else if (data.type === "stream_start") {
      setIsStreaming(true);
      setCurrentAiTokenStream("");
      setAgentStatusText(null);
    } else if (data.type === "chunk") {
      setCurrentAiTokenStream((prev) => prev + data.content);
    } else if (data.type === "stream_end" || data.type === "done") {
      setIsStreaming(false);
      setCurrentAiTokenStream((finalTokens) => {
        if (finalTokens) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: finalTokens },
          ]);
        }
        return "";
      });
      fetchSessions();
    } else if (data.type === "error") {
      setIsStreaming(false);
      setAgentStatusText(null);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `**Error:** ${data.message || data.content || "Service unavailable"}`,
        },
      ]);
    }
  };

  const effectiveResumes = resumes.length > 0 ? resumes : DEFAULT_RESUMES;
  const currentResumeId = selectedResumeId || effectiveResumes[0]?.id;
  const activeResume = effectiveResumes.find((r) => r.id === currentResumeId);

  const handleSendMessage = (query: string, taskType?: string) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: query },
    ]);

    setIsStreaming(true);
    setCurrentAiTokenStream("");
    setAgentStatusText(
      taskType
        ? `[${taskType}] Dispatching to Worker pool via Kafka...`
        : "Analyzing with Groq 120B..."
    );

    socketRef.current.send(
      JSON.stringify({
        query,
        resume_id: currentResumeId,
        target_jd: targetJd.trim() || null,
        task_type: taskType || null,
      })
    );

    setTimeout(fetchSessions, 600);
  };

  const handleSendQuickPrompt = (promptText: string, taskType?: string) => {
    handleSendMessage(promptText, taskType);
  };

  const handleUploadFile = async (file: File) => {
    setIsUploading(true);
    setUploadStatusText(`Uploading '${file.name}'...`);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/v1/resumes/upload`, {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setUploadStatusText("Upload complete!");
        setTimeout(async () => {
          setIsUploading(false);
          await fetchResumes();
          setSelectedResumeId(data.id);
        }, 1200);
      } else {
        const errorData = await res.json();
        setUploadStatusText(`Upload failed: ${errorData.detail || "Error"}`);
        setTimeout(() => setIsUploading(false), 2000);
      }
    } catch (err: any) {
      setUploadStatusText(`Error: ${err.message}`);
      setTimeout(() => setIsUploading(false), 2000);
    }
  };

  const handleSelectSession = async (targetSessionId: string) => {
    if (targetSessionId === currentSessionId) return;

    setCurrentSessionId(targetSessionId);
    setMessages([]);
    setCurrentAiTokenStream("");

    // Demo session inspection
    if (targetSessionId === "mock_1") {
      setMessages([
        {
          role: "user",
          content: "Review my CV for ATS compatibility and STAR bullet points",
        },
        {
          role: "assistant",
          content: `### STAR analysis\n- **STAR analysis** anewhy etrbantling connection, nocution, and hyper-cusfor to har andi bullet points.\n- **STAR analysis** of connected crn pantitc uoing on nour-bread and decidons to out other solutions.\n\n### Skill Gaps\n- Identified skillsrevetment management.\n- Identified amonnt internal navigation.\n- Identified skill gap: management.`,
          extra_metadata: {
            source: "cache",
            ats_score: 92,
            breakdown: {
              "ATS Compatibility": 92,
              "STAR analysis": 93,
              "Content score": 91,
            },
          },
        },
      ]);
      return;
    }

    try {
      const res = await fetch(`${BOT_HTTP_BASE}/api/v1/chat/history/${targetSessionId}`);
      if (res.ok) {
        const historyData = await res.json();
        if (Array.isArray(historyData)) {
          setMessages(historyData);
          for (const msg of historyData) {
            if (msg.extra_metadata?.resume_id) {
              setSelectedResumeId(msg.extra_metadata.resume_id);
              break;
            }
          }
        }
      }
    } catch (err) {
      console.error("Failed loading chat history:", err);
    }
  };

  const handleNewChat = () => {
    const newId = "session_" + Math.random().toString(36).substring(2, 9);
    setCurrentSessionId(newId);
    setMessages([]);
    setCurrentAiTokenStream("");
    setAgentStatusText(null);
  };

  const handleDeleteSession = async (sId: string) => {
    if (!confirm("Delete this chat session?")) return;

    try {
      const res = await fetch(`${BOT_HTTP_BASE}/api/v1/chat/sessions/${sId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        if (currentSessionId === sId) {
          handleNewChat();
        }
        await fetchSessions();
      }
    } catch (err) {
      console.error("Error deleting session:", err);
    }
  };

  return (
    <div className="flex h-screen w-full bg-[#080c15] p-4 gap-4 overflow-hidden">
      {/* 1. Left Sidebar */}
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        onRefreshSessions={fetchSessions}
        isOpen={true}
      />

      {/* 2. Main Right Area */}
      <div className="flex-1 flex flex-col gap-4 overflow-hidden h-full">
        {/* Top Header Bar */}
        <header className="dark-panel rounded-2xl px-5 py-3 flex items-center justify-between shrink-0 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-normal">
            <span className="text-slate-400">Home</span>
            <span className="text-slate-600 font-mono">&gt;</span>
            <span className="text-slate-400">ResumeIQ</span>
            <span className="text-slate-600 font-mono">&gt;</span>
            <span className="text-slate-300">
              AI Career Advisory & Multi-Agent Platform
            </span>
          </div>

          <div className="dark-inset px-3.5 py-1.5 rounded-xl border border-slate-700/60 text-xs text-slate-300 flex items-center gap-1.5 shadow-sm">
            <Zap className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
            <span>Groq 120B MoE • 0.2ms Working Memory</span>
          </div>
        </header>

        {/* 2-Column Split: Middle Panel (Resumes) + Right Panel (Chat Canvas) */}
        <div className="flex-1 flex gap-4 overflow-hidden min-h-0">
          <ResumePanel
            resumes={effectiveResumes}
            selectedResumeId={currentResumeId}
            onSelectResume={(id) => setSelectedResumeId(id)}
            onUploadFile={handleUploadFile}
            isUploading={isUploading}
            uploadStatusText={uploadStatusText}
            onRefreshResumes={fetchResumes}
            targetJd={targetJd}
            onChangeTargetJd={setTargetJd}
          />

          <ChatCanvas
            messages={messages}
            currentAiTokenStream={currentAiTokenStream}
            isStreaming={isStreaming}
            activeResumeName={activeResume ? activeResume.file_name : null}
            agentStatusText={agentStatusText}
            isWsConnected={isWsConnected}
            onSendMessage={handleSendMessage}
            onSendQuickPrompt={handleSendQuickPrompt}
          />
        </div>
      </div>
    </div>
  );
}
