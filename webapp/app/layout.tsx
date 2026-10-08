import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ResumeIQ — AI Career Platform & Multi-Agent Engine",
  description: "Event-driven AI Career Advisory platform with Groq 120B MoE, Qdrant Vector & Kafka KRaft.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased selection:bg-indigo-500 selection:text-white min-h-screen bg-[#080c15] text-slate-100 overflow-x-hidden font-sans">
        {children}
      </body>
    </html>
  );
}
