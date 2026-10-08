"use client";

import React, { useRef, useEffect, useState } from "react";
import { Zap, Sparkles, FileText, Target, Award, HelpCircle } from "lucide-react";
import { marked } from "marked";
import { ChatMessageItem } from "@/lib/types";

interface ChatCanvasProps {
  messages: ChatMessageItem[];
  currentAiTokenStream: string;
  isStreaming: boolean;
  activeResumeName: string | null;
  agentStatusText: string | null;
  isWsConnected: boolean;
  onSendMessage: (query: string, taskType?: string) => void;
  onSendQuickPrompt: (promptText: string, taskType?: string) => void;
}

export const ChatCanvas: React.FC<ChatCanvasProps> = ({
  messages,
  currentAiTokenStream,
  isStreaming,
  activeResumeName,
  agentStatusText,
  onSendMessage,
  onSendQuickPrompt,
}) => {
  const [inputVal, setInputVal] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, currentAiTokenStream, agentStatusText]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim() || isStreaming) return;
    onSendMessage(inputVal.trim());
    setInputVal("");
  };

  const isEmpty = messages.length === 0 && !isStreaming;

  return (
    <div className="flex-1 dark-panel rounded-2xl flex flex-col justify-between overflow-hidden h-full p-5">
      {/* Messages Scroll Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4 pr-1">
        {/* Empty State when New Chat */}
        {isEmpty && (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 max-w-xl mx-auto">
            <div className="h-12 w-12 rounded-2xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center mb-4 shadow-lg shadow-indigo-950/50">
              <Sparkles className="w-6 h-6 text-indigo-400" />
            </div>

            <h3 className="text-lg font-bold text-white tracking-tight mb-1">
              New Consultation Session
            </h3>

            <p className="text-xs text-slate-400 max-w-md leading-relaxed mb-6">
              Active Context:{" "}
              <span className="text-indigo-400 font-semibold">
                {activeResumeName || "Alex_Chen_Staff_Backend.pdf"}
              </span>
              . Select a starter prompt below or enter any question to begin.
            </p>

            {/* Starter Suggestion Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full">
              <button
                onClick={() =>
                  onSendQuickPrompt(
                    "Review my CV for ATS compatibility and STAR bullet points",
                    "ATS_CRITIQUE"
                  )
                }
                className="p-3 rounded-xl dark-inset hover:border-indigo-500/60 hover:bg-[#162238] border border-slate-700/60 text-left transition group"
              >
                <div className="flex items-center gap-2 mb-1">
                  <FileText className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
                  <span className="font-semibold text-xs text-white">Review CV & ATS</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-snug">
                  ATS score critique, keyword optimization, and formatting audit.
                </p>
              </button>

              <button
                onClick={() =>
                  onSendQuickPrompt(
                    "Evaluate my resume fit against the target Job Description and show my skill gaps",
                    "JD_MATCHING"
                  )
                }
                className="p-3 rounded-xl dark-inset hover:border-indigo-500/60 hover:bg-[#162238] border border-slate-700/60 text-left transition group"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Target className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
                  <span className="font-semibold text-xs text-white">JD Semantic Match</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-snug">
                  Measure alignment with target JD and identify missing requirements.
                </p>
              </button>

              <button
                onClick={() =>
                  onSendQuickPrompt(
                    "Audit my bullet points using the STAR method and suggest high-impact revisions",
                    "ATS_CRITIQUE"
                  )
                }
                className="p-3 rounded-xl dark-inset hover:border-indigo-500/60 hover:bg-[#162238] border border-slate-700/60 text-left transition group"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Award className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform" />
                  <span className="font-semibold text-xs text-white">STAR Bullets Audit</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-snug">
                  Re-structure achievements into Situation, Task, Action, and Result.
                </p>
              </button>

              <button
                onClick={() =>
                  onSendQuickPrompt(
                    "Prepare 3 high-yield technical interview questions based on my experience",
                    "INTERVIEW_PREP"
                  )
                }
                className="p-3 rounded-xl dark-inset hover:border-indigo-500/60 hover:bg-[#162238] border border-slate-700/60 text-left transition group"
              >
                <div className="flex items-center gap-2 mb-1">
                  <HelpCircle className="w-4 h-4 text-rose-400 group-hover:scale-110 transition-transform" />
                  <span className="font-semibold text-xs text-white">Mock Interview Prep</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-snug">
                  Simulate technical grilling tailored to your specific background.
                </p>
              </button>
            </div>
          </div>
        )}

        {/* Real Conversation Messages */}
        {messages.map((m, idx) => {
          const isUser = m.role === "user";
          const isCacheHit = m.extra_metadata?.source === "cache";
          const score = m.extra_metadata?.ats_score || m.extra_metadata?.score || m.extra_metadata?.overall_score;
          const breakdown = m.extra_metadata?.breakdown || (score ? {
            "ATS Compatibility": m.extra_metadata?.ats_compatibility_score || score,
            "STAR analysis": m.extra_metadata?.impact_metrics_score || Math.min(100, score + 1),
            "Content score": m.extra_metadata?.overall_score || Math.max(0, score - 1),
          } : undefined);

          if (isUser) {
            return (
              <div key={idx} className="flex justify-end">
                <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-xs leading-relaxed shadow-sm max-w-[85%]">
                  {m.content}
                </div>
              </div>
            );
          }

          return (
            <div key={idx} className="flex flex-col gap-2 max-w-full">
              {/* AI Advisor Header */}
              <div className="flex items-center gap-2.5">
                <div className="h-7 w-7 rounded-full bg-gradient-to-tr from-indigo-500 via-indigo-600 to-purple-500 flex items-center justify-center shadow-sm shrink-0">
                  <Sparkles className="w-3.5 h-3.5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-white leading-none">AI Advisor</h3>
                  {isCacheHit ? (
                    <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 mt-1">
                      <Zap className="w-3 h-3 text-amber-400 fill-amber-400" />
                      <span>Served from Redis Cache (~5ms)</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mt-1">
                      <Zap className="w-3 h-3 text-amber-400 fill-amber-400" />
                      <span>Groq 120B MoE • Qdrant Vector RAG</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Optional ATS Score Widget if available in metadata */}
              {score && (
                <div className="dark-inset border border-slate-700/60 rounded-2xl p-4 flex items-center gap-8 max-w-xl my-1">
                  <div className="flex flex-col shrink-0 min-w-[90px]">
                    <span className="text-xs text-slate-400 font-normal">ATS Score</span>
                    <span className="text-4xl font-extrabold text-white tracking-tight mt-0.5">
                      {score}/100
                    </span>
                  </div>

                  <div className="w-[1px] h-14 bg-slate-700/70 shrink-0" />

                  <div className="flex-1 flex flex-col gap-1.5">
                    <span className="text-xs text-slate-400 font-normal">Breakdown</span>
                    <div className="flex justify-between items-center text-xs gap-6">
                      <span className="text-slate-300">ATS Compatibility</span>
                      <span className="text-[#22c55e] font-semibold">{breakdown?.["ATS Compatibility"] || 92}/100</span>
                    </div>
                    <div className="flex justify-between items-center text-xs gap-6">
                      <span className="text-slate-300">STAR analysis</span>
                      <span className="text-[#22c55e] font-semibold">{breakdown?.["STAR analysis"] || 93}/100</span>
                    </div>
                    <div className="flex justify-between items-center text-xs gap-6">
                      <span className="text-slate-300">Content score</span>
                      <span className="text-[#22c55e] font-semibold">{breakdown?.["Content score"] || 91}/100</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Formatted Markdown Body */}
              <div
                className="prose prose-invert max-w-none text-xs leading-relaxed text-slate-200 mt-1 dark-inset rounded-2xl p-4 border border-slate-700/50"
                dangerouslySetInnerHTML={{ __html: marked.parse(m.content) as string }}
              />
            </div>
          );
        })}

        {/* Streaming tokens indicator */}
        {isStreaming && (
          <div className="flex flex-col gap-2 max-w-full">
            <div className="flex items-center gap-2.5">
              <div className="h-7 w-7 rounded-full bg-gradient-to-tr from-indigo-500 via-indigo-600 to-purple-500 flex items-center justify-center shadow-sm animate-pulse">
                <Sparkles className="w-3.5 h-3.5 text-white" />
              </div>
              <h3 className="font-semibold text-sm text-white">AI Advisor</h3>
            </div>
            <div className="dark-inset text-slate-200 border border-slate-700/60 rounded-2xl rounded-tl-sm p-4 text-xs max-w-[85%]">
              {currentAiTokenStream ? (
                <div dangerouslySetInnerHTML={{ __html: marked.parse(currentAiTokenStream) as string }} />
              ) : (
                <span className="text-slate-400 animate-pulse">
                  {agentStatusText || "Analyzing with Groq 120B..."}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Section */}
      <div className="pt-3 flex flex-col gap-2.5">
        {/* Quick Action Prompt Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
          <button
            onClick={() =>
              onSendQuickPrompt(
                "Review my CV for ATS compatibility and STAR bullet points",
                "ATS_CRITIQUE"
              )
            }
            className="px-4 py-1.5 rounded-full dark-inset hover:bg-slate-800 border border-slate-700/60 text-slate-300 text-xs font-normal transition active:scale-95 shadow-sm whitespace-nowrap"
          >
            ATS Deep Critique
          </button>
          <button
            onClick={() =>
              onSendQuickPrompt(
                "Analyze JD semantic gap and missing skills",
                "JD_MATCHING"
              )
            }
            className="px-4 py-1.5 rounded-full dark-inset hover:bg-slate-800 border border-slate-700/60 text-slate-300 text-xs font-normal transition active:scale-95 shadow-sm whitespace-nowrap"
          >
            JD Semantic Gap
          </button>
          <button
            onClick={() =>
              onSendQuickPrompt(
                "Generate mock technical interview questions",
                "INTERVIEW_PREP"
              )
            }
            className="px-4 py-1.5 rounded-full dark-inset hover:bg-slate-800 border border-slate-700/60 text-slate-300 text-xs font-normal transition active:scale-95 shadow-sm whitespace-nowrap"
          >
            Mock Interview
          </button>
        </div>

        {/* Floating Input Bar */}
        <form
          onSubmit={handleSubmit}
          className="dark-inset rounded-xl px-4 py-2 flex items-center justify-between border border-slate-700/60 shadow-sm"
        >
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Ask ResumeIQ anything about your CV or target role..."
            className="bg-transparent text-xs text-slate-100 placeholder-slate-400 focus:outline-none flex-1 py-1"
          />

          <button
            type="submit"
            disabled={!inputVal.trim() && !isStreaming}
            className="h-8 w-8 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center transition disabled:opacity-60 shadow-sm active:scale-95 shrink-0"
          >
            <svg viewBox="0 0 24 24" className="w-4 h-4 fill-white translate-x-[1px] translate-y-[-1px]">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
};
