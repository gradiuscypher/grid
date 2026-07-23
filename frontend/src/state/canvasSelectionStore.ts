import { create } from 'zustand'

interface CanvasSelectionState {
  selectedNodeIds: string[]
  selectedEdgeIds: string[]
  setSelection: (nodeIds: string[], edgeIds: string[]) => void
  clearSelection: () => void
}

export const useCanvasSelectionStore = create<CanvasSelectionState>((set) => ({
  selectedNodeIds: [],
  selectedEdgeIds: [],
  setSelection: (nodeIds, edgeIds) => set({ selectedNodeIds: nodeIds, selectedEdgeIds: edgeIds }),
  clearSelection: () => set({ selectedNodeIds: [], selectedEdgeIds: [] }),
}))
