"use client";

import React from "react";
import { Plus, SquarePen, Trash2 } from "lucide-react";
import { ChatSessionItem } from "@/lib/types";

interface SidebarProps {
  sessions: ChatSessionItem[];
  currentSessionId: string;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  onRefreshSessions: () => void;
  isOpen: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  isOpen,
}) => {
  if (!isOpen) return null;

  const displaySessions = sessions.length > 0 ? sessions : [
    {
      session_id: "mock_1",
      title: "Senior Backend ATS Audit",
      created_at: new Date().toISOString(),
      last_active_at: new Date().toISOString(),
      message_count: 4,
      preview: "Senior Backend ATS Audit",
    },
    {
      session_id: "mock_2",
      title: "Google L5 Interview Prep",
      created_at: new Date(Date.now() - 86400000).toISOString(),
      last_active_at: new Date(Date.now() - 86400000).toISOString(),
      message_count: 2,
      preview: "Google L5 Interview Prep",
    },
    {
      session_id: "mock_3",
      title: "JD Match: AI Engineer",
      created_at: new Date(Date.now() - 86400000).toISOString(),
      last_active_at: new Date(Date.now() - 86400000).toISOString(),
      message_count: 3,
      preview: "JD Match: AI Engineer",
    }
  ];

  return (
    <aside className="w-[270px] dark-panel rounded-2xl p-4 flex flex-col shrink-0 h-full justify-between select-none">
      {/* Top Segment */}
      <div className="flex flex-col gap-4">
        {/* Brand Header */}
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2.5">
            {/* Outline Ribbon Emblem matching prototype */}
            <div className="h-8 w-8 rounded-xl border-2 border-blue-500/90 bg-blue-600/10 flex items-center justify-center shadow-sm">
              <div className="h-3.5 w-3.5 rounded-sm border-2 border-blue-400 border-b-transparent border-l-transparent rotate-45" />
            </div>
            <h1 className="font-bold text-lg text-white tracking-tight">ResumeIQ</h1>
          </div>
          <button
            onClick={onNewChat}
            title="Compose Chat"
            className="text-slate-400 hover:text-white transition p-1"
          >
            <SquarePen className="w-4 h-4" />
          </button>
        </div>

        {/* + New Chat Pill Button */}
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition shadow-sm active:scale-[0.99]"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>

        {/* Recent Chats Section */}
        <div>
          <p className="text-[11px] text-slate-400 font-normal px-1 mb-2">Recent chats</p>
          <div className="space-y-1.5 overflow-y-auto max-h-[calc(100vh-16rem)] pr-0.5">
            {displaySessions.map((s, index) => {
              const isCurrent = s.session_id === currentSessionId || (index === 0 && !currentSessionId);
              const timeDisplay = index === 0 ? "2h ago" : "Yesterday";

              return (
                <div
                  key={s.session_id}
                  onClick={() => onSelectSession(s.session_id)}
                  className={`group rounded-xl p-3 cursor-pointer transition flex flex-col gap-1 ${
                    isCurrent
                      ? "dark-inset border border-slate-700/60"
                      : "hover:bg-[#131c2e]/50 border border-transparent"
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-100 truncate pr-2">
                      {s.title}
                    </span>
                    <span className="text-[10px] text-slate-400 shrink-0">
                      {timeDisplay}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <div className="flex items-center gap-1.5 truncate">
                      <span className={`h-1.5 w-1.5 rounded-full ${isCurrent ? "bg-indigo-400 shadow-[0_0_6px_#818cf8]" : "bg-slate-500"}`} />
                      <span className="truncate">{s.preview || s.title}</span>
                    </div>

                    {sessions.length > 0 && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteSession(s.session_id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-rose-400 text-slate-500 transition"
                        title="Delete Chat"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Profile Segment */}
      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between px-1">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-full overflow-hidden bg-slate-700 border border-slate-600 flex items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80"
              alt="Alex Chen"
              className="h-full w-full object-cover"
            />
          </div>
        </div>
        <button
          title="Compose / Options"
          className="text-slate-400 hover:text-white transition p-1"
        >
          <SquarePen className="w-4 h-4" />
        </button>
      </div>
    </aside>
  );
};
