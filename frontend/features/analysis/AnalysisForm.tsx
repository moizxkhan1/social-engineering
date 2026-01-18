"use client";

import { useState, FormEvent } from "react";
import { Button, Card } from "@/components";

interface AnalysisFormProps {
  onSubmit: (domain: string, competitors: string[]) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export function AnalysisForm({ onSubmit, isLoading, disabled }: AnalysisFormProps) {
  const [domain, setDomain] = useState("");
  const [competitorsInput, setCompetitorsInput] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = domain.trim();
    const competitors = competitorsInput
      .split(",")
      .map((value) => value.trim())
      .filter((value) => value.length > 0);
    if (trimmed) {
      onSubmit(trimmed, competitors);
    }
  };

  return (
    <Card className="overflow-hidden border-0 shadow-xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header Section */}
      <div className="relative px-8 pt-8 pb-6">
        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl -mr-32 -mt-32" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl -ml-24 -mb-24" />

        <div className="relative">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-white">Company Intelligence</h2>
          </div>
          <p className="text-slate-400 text-base max-w-lg">
            Discover what Reddit is saying about any company. Uncover insights, key people, and relationships from public discussions.
          </p>
        </div>
      </div>

      {/* Form Section */}
      <form onSubmit={handleSubmit} className="relative px-8 pb-8">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Domain Input */}
          <div className="flex-1 relative group">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-xl opacity-0 group-focus-within:opacity-100 blur transition-opacity duration-300" />
            <div className="relative flex items-center bg-slate-800/80 backdrop-blur-sm border border-slate-700/50 rounded-xl overflow-hidden focus-within:border-blue-500/50 transition-all duration-300">
              <div className="pl-4 pr-2">
                <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                </svg>
              </div>
              <input
                type="text"
                name="domain"
                placeholder="Enter a company domain (e.g., openai.com)"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                disabled={isLoading || disabled}
                className="flex-1 py-4 pr-4 bg-transparent text-white placeholder-slate-500 text-base focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          </div>

          <div className="flex-1 relative group">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-xl opacity-0 group-focus-within:opacity-100 blur transition-opacity duration-300" />
            <div className="relative flex items-center bg-slate-800/80 backdrop-blur-sm border border-slate-700/50 rounded-xl overflow-hidden focus-within:border-emerald-500/50 transition-all duration-300">
              <div className="pl-4 pr-2">
                <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7h18M3 12h18M3 17h18" />
                </svg>
              </div>
              <input
                type="text"
                name="competitors"
                placeholder="Competitors (comma-separated)"
                value={competitorsInput}
                onChange={(e) => setCompetitorsInput(e.target.value)}
                disabled={isLoading || disabled}
                className="flex-1 py-4 pr-4 bg-transparent text-white placeholder-slate-500 text-base focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            isLoading={isLoading}
            disabled={!domain.trim() || disabled}
            size="lg"
            className="sm:w-auto w-full px-8 py-4 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          >
            {!isLoading && (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            )}
            {isLoading ? "Analyzing..." : "Analyze"}
          </Button>
        </div>

        {/* Example domains */}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-500">Try:</span>
          {["stripe.com", "anthropic.com", "notion.so"].map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setDomain(example)}
              disabled={isLoading || disabled}
              className="text-xs px-3 py-1.5 rounded-full bg-slate-800/50 text-slate-400 hover:text-blue-400 hover:bg-slate-700/50 border border-slate-700/50 hover:border-blue-500/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {example}
            </button>
          ))}
        </div>
      </form>
    </Card>
  );
}
