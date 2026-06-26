"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type AnnotateRequest,
  type AnnotateResponse,
  type CleanReport,
  type ClusterDetail,
  type ClusterSummary,
  type DecisionRequest,
  type DecisionResponse,
  type SpeciesScoreReport,
  type SpeciesSuggestion,
  type TaxonSummary,
  getCluster,
  getClusters,
  getTaxa,
  postAnnotate,
  postCleanUpload,
  postDecision,
  scoreTaxon,
  suggestSpecies,
} from "./api";

export function useTaxa() {
  return useQuery<TaxonSummary[]>({ queryKey: ["taxa"], queryFn: getTaxa });
}

export function useClusters(taxon?: string) {
  return useQuery<ClusterSummary[]>({
    queryKey: ["clusters", taxon ?? null],
    queryFn: () => getClusters(taxon),
  });
}

export function useCluster(clusterId: string | null) {
  return useQuery<ClusterDetail>({
    queryKey: ["cluster", clusterId],
    queryFn: () => getCluster(clusterId as string),
    enabled: clusterId !== null,
  });
}

export function useDecision(clusterId: string) {
  const queryClient = useQueryClient();
  return useMutation<DecisionResponse, Error, DecisionRequest>({
    mutationFn: (body: DecisionRequest) => postDecision(clusterId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clusters"] });
      queryClient.invalidateQueries({ queryKey: ["cluster", clusterId] });
    },
  });
}

export function useCleanUpload() {
  return useMutation<CleanReport, Error, File>({
    mutationFn: (file: File) => postCleanUpload(file),
  });
}

export function useSpeciesSuggest(query: string) {
  return useQuery<SpeciesSuggestion[]>({
    queryKey: ["suggest", query],
    queryFn: () => suggestSpecies(query),
    enabled: query.trim().length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}

export function useSpeciesScore(taxon: string | null) {
  return useQuery<SpeciesScoreReport>({
    queryKey: ["score", taxon],
    queryFn: () => scoreTaxon(taxon as string),
    enabled: taxon !== null,
    staleTime: Infinity,
    retry: false,
  });
}

export function useAnnotate() {
  return useMutation<AnnotateResponse, Error, AnnotateRequest>({
    mutationFn: (body: AnnotateRequest) => postAnnotate(body),
  });
}
