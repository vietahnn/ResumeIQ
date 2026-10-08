"use client";

import React from "react";

export const TechFooter: React.FC = () => {
  const technologies = [
    { name: "Groq 120B MoE", color: "text-amber-700 bg-amber-50 border-amber-200" },
    { name: "Apache Kafka", color: "text-slate-800 bg-slate-100 border-slate-300" },
    { name: "Redis Cache", color: "text-rose-700 bg-rose-50 border-rose-200" },
    { name: "Qdrant Vector", color: "text-purple-700 bg-purple-50 border-purple-200" },
    { name: "PostgreSQL", color: "text-sky-800 bg-sky-50 border-sky-200" },
    { name: "MinIO S3", color: "text-red-700 bg-red-50 border-red-200" },
    { name: "Tavily AI Search", color: "text-teal-700 bg-teal-50 border-teal-200" },
  ];

  return (
    <footer className="mt-4 flex flex-wrap items-center justify-center gap-2 text-center text-[11px] text-slate-500 py-1">
      <span className="font-semibold text-slate-600">Powered by Event-Driven Microservices:</span>
      <div className="flex flex-wrap items-center justify-center gap-1.5">
        {technologies.map((t) => (
          <span
            key={t.name}
            className={`px-2.5 py-0.5 rounded-full font-medium border text-[10px] shadow-sm ${t.color}`}
          >
            {t.name}
          </span>
        ))}
      </div>
    </footer>
  );
};
