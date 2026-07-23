import { Handle, type NodeProps, Position } from '@xyflow/react'
import styles from './EntityNode.module.css'
import { entityTypeIcon } from './entityIcons'
import type { EntityNode as EntityNodeType } from './graphModel'
import { PROVENANCE_ICON, PROVENANCE_LABEL } from './provenanceIcons'

export function EntityNode({ data, selected }: NodeProps<EntityNodeType>) {
  const { node, entityType } = data
  const Icon = entityTypeIcon(entityType?.icon)
  const ProvenanceIcon = PROVENANCE_ICON[node.created_via]
  const accent = entityType?.color ?? 'var(--color-border)'

  return (
    <div
      className={[styles.node, selected ? styles.selected : ''].filter(Boolean).join(' ')}
      style={{ borderLeftColor: accent }}
    >
      <Handle type="target" position={Position.Left} id="target" className={styles.handle} />
      <div className={styles.icon} style={{ color: accent }}>
        <Icon size={16} aria-hidden />
      </div>
      <div className={styles.body}>
        <div className={styles.value} title={node.value}>
          {node.value}
        </div>
        <div className={styles.type}>{entityType?.display_name ?? entityType?.name ?? '—'}</div>
      </div>
      {node.created_via !== 'user' && (
        <div
          className={styles.provenance}
          role="img"
          title={PROVENANCE_LABEL[node.created_via]}
          aria-label={PROVENANCE_LABEL[node.created_via]}
        >
          <ProvenanceIcon size={12} aria-hidden />
        </div>
      )}
      <Handle type="source" position={Position.Right} id="source" className={styles.handle} />
    </div>
  )
}
