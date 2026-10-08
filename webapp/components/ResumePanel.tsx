"use client";

import React, { useRef } from "react";
import { Plus, Loader2, CheckCircle2 } from "lucide-react";
import { ResumeItem } from "@/lib/types";

interface ResumePanelProps {
  resumes: ResumeItem[];
  selectedResumeId: string | null;
  onSelectResume: (id: string, name: string) => void;
  onUploadFile: (file: File) => void;
  isUploading: boolean;
  uploadStatusText: string;
  onRefreshResumes: () => void;
  targetJd: string;
  onChangeTargetJd: (val: string) => void;
}

export const ResumePanel: React.FC<ResumePanelProps> = ({
  resumes,
  selectedResumeId,
  onSelectResume,
  onUploadFile,
  isUploading,
  uploadStatusText,
  targetJd,
  onChangeTargetJd,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onUploadFile(e.target.files[0]);
    }
  };

  const displayResumes = resumes.length > 0 ? resumes : [
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

  // Active resume ID defaults to first item if not set
  const activeId = selectedResumeId || displayResumes[0]?.id;

  return (
    <div className="w-[390px] flex flex-col gap-4 shrink-0">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf,.docx"
        className="hidden"
      />

      {/* 1. Resumes Card */}
      <div className="dark-panel rounded-2xl p-5 flex flex-col gap-3.5 relative overflow-hidden">
        {/* Card Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="font-semibold text-[15px] text-white tracking-tight">
              Resumes ({displayResumes.length})
            </h2>
            <span className="text-[10px] text-slate-400 font-normal">
              Click to switch
            </span>
          </div>

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#162035] hover:bg-[#1c2842] text-slate-200 border border-slate-700/60 text-xs font-medium transition active:scale-95 disabled:opacity-50 shadow-sm"
          >
            <Plus className="w-3.5 h-3.5 text-slate-300" />
            <span>Upload CV</span>
          </button>
        </div>

        {/* Upload status indicator */}
        {isUploading && (
          <div className="px-3 py-2 rounded-xl bg-indigo-950/60 border border-indigo-700/40 text-indigo-300 text-xs flex items-center justify-between animate-pulse">
            <span className="font-medium truncate">{uploadStatusText}</span>
            <Loader2 className="w-4 h-4 animate-spin text-indigo-400 shrink-0" />
          </div>
        )}

        {/* Resumes List */}
        <div className="space-y-3">
          {displayResumes.map((r) => {
            const isSelected = r.id === activeId;
            const score = (r.parsed_data as any)?.ats_score || (r.id === "mock_res_1" ? 92 : 84);

            return (
              <div
                key={r.id}
                onClick={() => onSelectResume(r.id, r.file_name)}
                className={`group rounded-xl p-3.5 cursor-pointer transition-all duration-200 flex items-center justify-between border ${
                  isSelected
                    ? "border-indigo-500/90 bg-[#162238] ring-2 ring-indigo-500/40 shadow-lg shadow-indigo-950/40"
                    : "border-slate-800/80 bg-[#0f172a]/60 hover:border-slate-700 hover:bg-[#131c2e] opacity-75 hover:opacity-100"
                }`}
              >
                <div className="flex items-center gap-3 overflow-hidden flex-1 min-w-0 pr-2">
                  {/* Adobe Acrobat Style White Sheet with Red Curve */}
                  <div className={`h-8 w-6 rounded-[4px] bg-white flex items-center justify-center shrink-0 shadow-sm p-1 transition-transform ${isSelected ? "scale-105" : ""}`}>
                    <svg viewBox="0 0 24 24" className="w-4 h-4 text-[#e11d48]" fill="currentColor">
                      <path d="M19.38 6.54c-.37-.53-.94-.87-1.63-.98-.69-.11-1.46-.02-2.22.25-.97.35-1.92.93-2.73 1.66-.45-.48-.96-1.07-1.48-1.74-.78-1-1.39-2.07-1.78-3.08-.2-.51-.34-1.02-.39-1.48-.05-.46.03-.89.28-1.21.31-.41.8-.62 1.34-.58.55.04 1.05.34 1.38.83.18.27.31.59.38.93.07.35.07.72.01 1.09-.08.49-.29 1.06-.61 1.68-.06.12-.13.24-.2.37.52.92 1.13 1.83 1.83 2.7.2.25.4.49.61.73.91-.49 1.86-.88 2.81-1.14.74-.2 1.48-.3 2.18-.28.71.02 1.35.21 1.84.58.49.38.79.94.84 1.6.05.65-.15 1.33-.6 1.95-.56.76-1.4 1.33-2.39 1.66-1.23.42-2.6.48-3.95.21-.49-.1-.97-.24-1.43-.43-.72.63-1.48 1.33-2.26 2.08-.43.41-.86.83-1.28 1.25.1.48.24.96.41 1.44.44 1.25 1.07 2.45 1.84 3.51.52.71 1.1 1.34 1.72 1.84.62.5 1.27.84 1.93.97.66.13 1.31.02 1.88-.34.57-.36.98-.95 1.16-1.7.18-.75.12-1.62-.21-2.52-.39-1.07-1.12-2.19-2.11-3.19-.24-.24-.49-.47-.75-.69.21-.08.43-.15.65-.21.84-.23 1.72-.34 2.58-.33.86.01 1.69.15 2.43.44.75.29 1.38.73 1.83 1.32.45.58.68 1.31.64 2.13-.04.81-.35 1.67-.93 2.48-.71.99-1.78 1.76-3.07 2.22-1.29.47-2.76.57-4.22.34-1.46-.23-2.88-.81-4.08-1.71-1.2-1-2.15-2.28-2.75-3.79-.39-.99-.62-2.06-.68-3.16-.06-1.1.06-2.22.39-3.32.43-1.44 1.19-2.78 2.18-3.91.99-1.13 2.19-2.02 3.48-2.61.98-.45 2.01-.73 3.03-.83 1.02-.1 2.01-.01 2.92.27 1.14.35 2.08.99 2.7 1.86.62.87.89 1.95.74 3.1-.15 1.15-.72 2.3-1.64 3.32-.92 1.02-2.14 1.86-3.53 2.41z"/>
                    </svg>
                  </div>

                  <div className="overflow-hidden truncate flex flex-col">
                    <span className={`font-medium text-xs truncate ${isSelected ? "text-white font-semibold" : "text-slate-300"}`}>
                      {r.file_name}
                    </span>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {isSelected ? (
                        <span className="flex items-center gap-1 text-[10px] font-semibold text-indigo-400">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Selected</span>
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-500 group-hover:text-slate-400 transition">
                          Click to select
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <span
                  className={`text-xs font-semibold px-2.5 py-1 rounded-lg border shrink-0 transition-colors ${
                    isSelected
                      ? "bg-[#064e3b] text-[#22c55e] border-emerald-500/50 shadow-sm"
                      : "bg-slate-800/80 text-slate-400 border-slate-700/50"
                  }`}
                >
                  {score}% ATS
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Target Job Description Card */}
      <div className="dark-panel rounded-2xl p-5 flex flex-col gap-3.5">
        {/* Card Header */}
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-[15px] text-white tracking-tight">
            Target Job Description
          </h2>
          <span className={`text-xs font-medium px-2.5 py-1 rounded-lg border ${
            targetJd.trim()
              ? "bg-[#064e3b]/80 text-[#22c55e] border-emerald-800/40"
              : "bg-slate-800/80 text-slate-400 border-slate-700/60"
          }`}>
            {targetJd.trim() ? "JD Attached" : "Optional"}
          </span>
        </div>

        {/* Content Box */}
        <div className="dark-inset rounded-xl p-3.5 border border-slate-700/50 min-h-[90px] flex items-center">
          <textarea
            rows={3}
            value={targetJd}
            onChange={(e) => onChangeTargetJd(e.target.value)}
            placeholder="Paste target Job Description (JD) or enter target role requirements here to evaluate semantic match..."
            className="w-full bg-transparent text-xs text-slate-200 placeholder-slate-400 focus:outline-none resize-none leading-relaxed font-normal"
          />
        </div>
      </div>
    </div>
  );
};
