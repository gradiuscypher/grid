import { useMemo } from 'react'
import type { EdgeOut, EntityTypeOut, NodeOut } from '../api/generated'
import { Panel } from '../components/Panel'
import { TextField } from '../components/TextField'
import { useCanvasSelectionStore } from '../state/canvasSelectionStore'
import { entityTypeIcon } from './entityIcons'
import { entityTypesById } from './graphModel'
import styles from './Inspector.module.css'
import { NotesPanel } from './NotesPanel'
import { PropertiesEditor } from './PropertiesEditor'
import { PROVENANCE_LABEL } from './provenanceIcons'
import { useGraphMutations } from './useGraphMutations'

interface InspectorProps {
  caseId: string
  nodes: NodeOut[]
  edges: EdgeOut[]
  entityTypes: EntityTypeOut[]
  currentUserId: string | undefined
}

function provenanceText(
  createdVia: NodeOut['created_via'],
  createdByUserId: string | null,
  currentUserId: string | undefined,
) {
  if (createdVia === 'user') {
    if (createdByUserId && currentUserId && createdByUserId === currentUserId)
      return 'Created by you'
    return 'Created by a user'
  }
  return PROVENANCE_LABEL[createdVia]
}

export function Inspector({ caseId, nodes, edges, entityTypes, currentUserId }: InspectorProps) {
  const { selectedNodeIds, selectedEdgeIds } = useCanvasSelectionStore()
  const entityTypesMap = useMemo(() => entityTypesById(entityTypes), [entityTypes])
  const { updateNode, updateEdge } = useGraphMutations(caseId)

  const selectedCount = selectedNodeIds.length + selectedEdgeIds.length

  if (selectedCount === 0) {
    return (
      <Panel className={styles.panel}>
        <p className={styles.placeholder}>Select a node or edge to inspect it.</p>
      </Panel>
    )
  }

  if (selectedCount > 1) {
    return (
      <Panel className={styles.panel}>
        <p className={styles.placeholder}>{selectedCount} items selected.</p>
      </Panel>
    )
  }

  if (selectedNodeIds.length === 1) {
    const node = nodes.find((candidate) => candidate.id === selectedNodeIds[0])
    if (!node) {
      return (
        <Panel className={styles.panel}>
          <p className={styles.placeholder}>Selected node no longer exists.</p>
        </Panel>
      )
    }
    const entityType = entityTypesMap.get(node.entity_type_id)
    const Icon = entityTypeIcon(entityType?.icon)

    return (
      <Panel className={styles.panel} key={node.id}>
        <div className={styles.header}>
          <Icon size={18} aria-hidden />
          <div>
            <div className={styles.value}>{node.value}</div>
            <div className={styles.type}>{entityType?.display_name ?? entityType?.name}</div>
          </div>
        </div>
        <p className={styles.provenance}>
          {provenanceText(node.created_via, node.created_by_user_id, currentUserId)}
        </p>
        <TextField
          label="Confidence"
          type="number"
          min={0}
          max={1}
          step={0.05}
          defaultValue={node.confidence}
          key={`${node.id}-confidence`}
          onBlur={(event) => {
            const parsed = Number(event.target.value)
            if (!Number.isNaN(parsed) && parsed !== node.confidence) {
              updateNode.mutate({ nodeId: node.id, body: { confidence: parsed } })
            }
          }}
        />
        <PropertiesEditor
          key={`${node.id}-properties`}
          initial={node.properties}
          isPending={updateNode.isPending}
          error={updateNode.isError ? updateNode.error : null}
          onSave={(properties) => updateNode.mutate({ nodeId: node.id, body: { properties } })}
        />
        <NotesPanel caseId={caseId} targetType="node" targetId={node.id} />
      </Panel>
    )
  }

  const edge = edges.find((candidate) => candidate.id === selectedEdgeIds[0])
  if (!edge) {
    return (
      <Panel className={styles.panel}>
        <p className={styles.placeholder}>Selected edge no longer exists.</p>
      </Panel>
    )
  }
  const source = nodes.find((candidate) => candidate.id === edge.src_node_id)
  const target = nodes.find((candidate) => candidate.id === edge.dst_node_id)

  return (
    <Panel className={styles.panel} key={edge.id}>
      <div className={styles.header}>
        <div>
          <div className={styles.value}>{edge.relationship}</div>
          <div className={styles.type}>
            {source?.value ?? '?'} → {target?.value ?? '?'}
          </div>
        </div>
      </div>
      <p className={styles.provenance}>
        {provenanceText(edge.created_via, edge.created_by_user_id, currentUserId)}
      </p>
      <TextField
        label="Label"
        key={`${edge.id}-label`}
        defaultValue={edge.label ?? ''}
        onBlur={(event) => {
          const nextLabel = event.target.value.trim() || null
          if (nextLabel !== edge.label) {
            updateEdge.mutate({ edgeId: edge.id, body: { label: nextLabel } })
          }
        }}
      />
      <PropertiesEditor
        key={`${edge.id}-properties`}
        initial={edge.properties}
        isPending={updateEdge.isPending}
        error={updateEdge.isError ? updateEdge.error : null}
        onSave={(properties) => updateEdge.mutate({ edgeId: edge.id, body: { properties } })}
      />
      <NotesPanel caseId={caseId} targetType="edge" targetId={edge.id} />
    </Panel>
  )
}
