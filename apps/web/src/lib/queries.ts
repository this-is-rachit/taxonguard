"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type ClusterDetail,
  type ClusterSummary,
  type DecisionRequest,
  type DecisionResponse,
  type TaxonSummary,
  getCluster,
  getClusters,
  getTaxa,
  postDecision,
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
