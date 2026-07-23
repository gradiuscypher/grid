import {
  AtSign,
  Building,
  FileText,
  Globe,
  HardDrive,
  Hash,
  Link,
  type LucideIcon,
  Mail,
  Network,
  Server,
  Shapes,
  Share2,
  User,
} from 'lucide-react'

// Slugs come from the entity_types.icon column (backend seed migration
// 244e9746d9db) and happen to be literal Lucide icon names. Custom entity
// types can set any string here — unrecognized slugs fall back to a generic
// icon rather than rendering nothing.
const ICONS: Record<string, LucideIcon> = {
  globe: Globe,
  server: Server,
  'hard-drive': HardDrive,
  network: Network,
  'share-2': Share2,
  link: Link,
  mail: Mail,
  'at-sign': AtSign,
  user: User,
  building: Building,
  hash: Hash,
  'file-text': FileText,
}

export function entityTypeIcon(slug: string | null | undefined): LucideIcon {
  if (!slug) return Shapes
  return ICONS[slug] ?? Shapes
}
