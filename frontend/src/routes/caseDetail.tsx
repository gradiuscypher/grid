import { useQuery } from '@tanstack/react-query'
import { createRoute, Link } from '@tanstack/react-router'
import { useMemo, useState } from 'react'
import { meQueryOptions } from '../api/auth'
import { caseQueryOptions } from '../api/cases'
import { edgesQueryOptions } from '../api/edges'
import { entityTypesQueryOptions } from '../api/entityTypes'
import { apiErrorMessage } from '../api/errors'
import { nodesQueryOptions } from '../api/nodes'
import { ConnectEdgeDialog, type PendingConnection } from '../canvas/ConnectEdgeDialog'
import { CreateNodePanel } from '../canvas/CreateNodePanel'
import { GraphCanvas } from '../canvas/GraphCanvas'
import { Inspector } from '../canvas/Inspector'
import { useGraphMutations } from '../canvas/useGraphMutations'
import { RouteError } from '../components/RouteError'
import { useCaseEvents } from '../events/useCaseEvents'
import { useCanvasSelectionStore } from '../state/canvasSelectionStore'
import { useRegisterCommands } from '../state/commandRegistryStore'
import { authedLayoutRoute } from './authed'
import styles from './CaseDetailPage.module.css'

const NODE_GRID_COLUMNS = 8
const NODE_GRID_SPACING_X = 200
const NODE_GRID_SPACING_Y = 140
const NODE_GRID_OFFSET = 80

export const caseDetailRoute = createRoute({
  getParentRoute: () => authedLayoutRoute,
  path: '/cases/$caseId',
  loader: ({ context, params }) =>
    context.queryClient.ensureQueryData(caseQueryOptions(params.caseId)),
  component: CaseDetailPage,
  errorComponent: RouteError,
})

function CaseDetailPage() {
  const { caseId } = caseDetailRoute.useParams()
  const caseQuery = useQuery(caseQueryOptions(caseId))
  const meQuery = useQuery(meQueryOptions)
  const nodesQuery = useQuery(nodesQueryOptions(caseId))
  const edgesQuery = useQuery(edgesQueryOptions(caseId))
  const entityTypesQuery = useQuery(entityTypesQueryOptions)

  useCaseEvents(caseId)

  const selectedNodeIds = useCanvasSelectionStore((state) => state.selectedNodeIds)
  const selectedEdgeIds = useCanvasSelectionStore((state) => state.selectedEdgeIds)
  const setSelection = useCanvasSelectionStore((state) => state.setSelection)

  const { createNode, createEdge, updateNode, deleteNode, deleteEdge } = useGraphMutations(caseId)
  const [pendingConnection, setPendingConnection] = useState<PendingConnection | null>(null)

  const nodes = useMemo(() => nodesQuery.data ?? [], [nodesQuery.data])
  const edges = useMemo(() => edgesQuery.data ?? [], [edgesQuery.data])
  const entityTypes = useMemo(() => entityTypesQuery.data ?? [], [entityTypesQuery.data])
  const selectedNodeIdSet = useMemo(() => new Set(selectedNodeIds), [selectedNodeIds])
  const selectedEdgeIdSet = useMemo(() => new Set(selectedEdgeIds), [selectedEdgeIds])

  useRegisterCommands(
    'case-detail',
    useMemo(
      () => [
        {
          id: 'delete-selection',
          label: 'Delete selected node/edge',
          shortcut: 'Backspace',
          run: () => {
            for (const id of selectedNodeIds) deleteNode.mutate(id)
            for (const id of selectedEdgeIds) deleteEdge.mutate(id)
          },
        },
      ],
      [selectedNodeIds, selectedEdgeIds, deleteNode, deleteEdge],
    ),
  )

  function handleCreateNode(entityTypeId: string, value: string) {
    const index = nodes.length
    createNode.mutate({
      entity_type_id: entityTypeId,
      value,
      position_x: NODE_GRID_OFFSET + (index % NODE_GRID_COLUMNS) * NODE_GRID_SPACING_X,
      position_y: NODE_GRID_OFFSET + Math.floor(index / NODE_GRID_COLUMNS) * NODE_GRID_SPACING_Y,
    })
  }

  function handleConnectNodes(sourceId: string, targetId: string) {
    const source = nodes.find((node) => node.id === sourceId)
    const target = nodes.find((node) => node.id === targetId)
    setPendingConnection({
      sourceId,
      targetId,
      sourceLabel: source?.value ?? sourceId,
      targetLabel: target?.value ?? targetId,
    })
  }

  function handleMoveNode(nodeId: string, x: number, y: number) {
    updateNode.mutate({ nodeId, body: { position_x: x, position_y: y } })
  }

  function handleDeleteNodes(ids: string[]) {
    for (const id of ids) deleteNode.mutate(id)
  }

  function handleDeleteEdges(ids: string[]) {
    for (const id of ids) deleteEdge.mutate(id)
  }

  const graphLoading = nodesQuery.isLoading || edgesQuery.isLoading || entityTypesQuery.isLoading

  return (
    <div className={styles.wrap}>
      <Link to="/" className={styles.back}>
        ← Cases
      </Link>
      {caseQuery.isError && (
        <p role="alert">{apiErrorMessage(caseQuery.error, 'Failed to load case')}</p>
      )}
      {caseQuery.data && (
        <>
          <div className={styles.headerRow}>
            <h1 className={styles.title}>{caseQuery.data.name}</h1>
            {caseQuery.data.description && (
              <p className={styles.description}>{caseQuery.data.description}</p>
            )}
          </div>
          <CreateNodePanel
            entityTypes={entityTypes}
            onCreate={handleCreateNode}
            isPending={createNode.isPending}
            error={createNode.isError ? createNode.error : null}
          />
          <div className={styles.body}>
            <div className={styles.canvasArea}>
              {graphLoading ? (
                <p className={styles.loading}>Loading graph…</p>
              ) : (
                <GraphCanvas
                  nodes={nodes}
                  edges={edges}
                  entityTypes={entityTypes}
                  selectedNodeIds={selectedNodeIdSet}
                  selectedEdgeIds={selectedEdgeIdSet}
                  onSelectionChange={setSelection}
                  onConnectNodes={handleConnectNodes}
                  onMoveNode={handleMoveNode}
                  onDeleteNodes={handleDeleteNodes}
                  onDeleteEdges={handleDeleteEdges}
                />
              )}
            </div>
            <div className={styles.inspector}>
              <Inspector
                caseId={caseId}
                nodes={nodes}
                edges={edges}
                entityTypes={entityTypes}
                currentUserId={meQuery.data?.id}
              />
            </div>
          </div>
        </>
      )}
      {pendingConnection && (
        <ConnectEdgeDialog
          pending={pendingConnection}
          isPending={createEdge.isPending}
          error={createEdge.isError ? createEdge.error : null}
          onCancel={() => setPendingConnection(null)}
          onSubmit={(relationship, label) => {
            createEdge.mutate(
              {
                src_node_id: pendingConnection.sourceId,
                dst_node_id: pendingConnection.targetId,
                relationship,
                label,
              },
              { onSuccess: () => setPendingConnection(null) },
            )
          }}
        />
      )}
    </div>
  )
}
