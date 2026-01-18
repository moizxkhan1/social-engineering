"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell, Section } from "@/components";
import {
  AnalysisForm,
  JobStatus,
  SummaryCards,
  SubredditTable,
  EntityList,
  EntityDetail,
  RelationshipList,
  GraphView,
  CompetitiveDashboard,
} from "@/features";
import { useAnalysisJob, useEntityDetail } from "@/hooks";
import {
  getSubreddits,
  getEntities,
  getRelationships,
  getGraph,
  getCompetitiveOverview,
} from "@/services";
import type { Subreddit, Entity, Relationship, GraphData, CompetitiveOverview } from "@/types";

type Tab = "subreddits" | "entities" | "relationships" | "graph" | "competitive";

export default function Home() {
  const job = useAnalysisJob();
  const entityDetail = useEntityDetail();

  const [activeTab, setActiveTab] = useState<Tab>("subreddits");
  const [subreddits, setSubreddits] = useState<Subreddit[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [competitiveOverview, setCompetitiveOverview] = useState<CompetitiveOverview | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);

  const fetchAllData = useCallback(async () => {
    setIsLoadingData(true);
    try {
      const [subs, ents, rels, graph, competitive] = await Promise.all([
        getSubreddits(),
        getEntities(),
        getRelationships(),
        getGraph(),
        getCompetitiveOverview(),
      ]);
      setSubreddits(subs);
      setEntities(ents);
      setRelationships(rels);
      setGraphData(graph);
      setCompetitiveOverview(competitive);
    } catch (err) {
      console.error("Failed to fetch data:", err);
    } finally {
      setIsLoadingData(false);
    }
  }, []);

  // Fetch data when job completes
  useEffect(() => {
    if (job.status === "complete") {
      fetchAllData();
    }
  }, [job.status, fetchAllData]);

  const handleAnalyze = (domain: string, competitors: string[]) => {
    setSubreddits([]);
    setEntities([]);
    setRelationships([]);
    setGraphData(null);
    setCompetitiveOverview(null);
    job.start(domain, competitors);
  };

  const handleEntitySelect = (entity: Entity) => {
    entityDetail.fetch(entity.id);
  };

  const hasResults = job.result !== null;

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: "subreddits", label: "Subreddits", count: subreddits.length },
    { id: "entities", label: "Entities", count: entities.length },
    { id: "relationships", label: "Relationships", count: relationships.length },
    { id: "graph", label: "Graph" },
    { id: "competitive", label: "Competitive" },
  ];

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Analysis Form */}
        <AnalysisForm
          onSubmit={handleAnalyze}
          isLoading={job.isLoading}
          disabled={job.isLoading}
        />

        {/* Job Status */}
        {(job.status === "running" || job.status === "queued" || job.error) && (
          <div className="animate-fade-in">
            <JobStatus
              status={job.status}
              progress={job.progress}
              error={job.error}
              onRetry={job.reset}
            />
          </div>
        )}

        {/* Summary Cards */}
        {hasResults && (
          <div className="animate-fade-in">
            <SummaryCards result={job.result} />
          </div>
        )}

        {/* Results Tabs */}
        {hasResults && (
          <div className="animate-fade-in">
            {/* Tab Navigation */}
            <div className="border-b border-slate-200 dark:border-slate-700 mb-6">
              <nav className="flex gap-8" aria-label="Tabs">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`
                      pb-3 text-sm font-medium border-b-2 -mb-px transition-colors
                      ${
                        activeTab === tab.id
                          ? "border-blue-500 text-blue-600 dark:text-blue-400"
                          : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
                      }
                    `}
                  >
                    {tab.label}
                    {tab.count !== undefined && (
                      <span
                        className={`
                          ml-2 px-2 py-0.5 text-xs rounded-full
                          ${
                            activeTab === tab.id
                              ? "bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-300"
                              : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                          }
                        `}
                      >
                        {tab.count}
                      </span>
                    )}
                  </button>
                ))}
              </nav>
            </div>

            {/* Tab Content */}
            <div className="animate-slide-in">
              {activeTab === "subreddits" && (
                <Section
                  title="Discovered Subreddits"
                  description="Ranked by relevance score based on mentions, engagement, and topic alignment"
                >
                  <SubredditTable subreddits={subreddits} isLoading={isLoadingData} />
                </Section>
              )}

              {activeTab === "entities" && (
                <Section
                  title="Extracted Entities"
                  description="Companies and people mentioned in the discussions"
                >
                  <EntityList
                    entities={entities}
                    isLoading={isLoadingData}
                    onSelect={handleEntitySelect}
                  />
                </Section>
              )}

              {activeTab === "relationships" && (
                <Section
                  title="Discovered Relationships"
                  description="Connections between entities found in discussions"
                >
                  <RelationshipList relationships={relationships} isLoading={isLoadingData} />
                </Section>
              )}

              {activeTab === "graph" && (
                <Section
                  title="Knowledge Graph"
                  description="Visual representation of entities and their relationships"
                >
                  <GraphView data={graphData} isLoading={isLoadingData} />
                </Section>
              )}

              {activeTab === "competitive" && (
                <Section
                  title="Competitive Exposure"
                  description="Share of voice, sentiment, co-mentions, and anomalies"
                >
                  <CompetitiveDashboard data={competitiveOverview} isLoading={isLoadingData} />
                </Section>
              )}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!hasResults && !job.isLoading && !job.error && (
          <div className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-4 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center">
              <svg
                className="w-8 h-8 text-slate-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">
              No analysis yet
            </h3>
            <p className="text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
              Enter a company domain above to discover insights from Reddit discussions
            </p>
          </div>
        )}

        {/* Entity Detail Modal */}
        <EntityDetail
          entity={entityDetail.entity}
          isLoading={entityDetail.isLoading}
          error={entityDetail.error}
          onClose={entityDetail.clear}
        />
      </div>
    </AppShell>
  );
}
