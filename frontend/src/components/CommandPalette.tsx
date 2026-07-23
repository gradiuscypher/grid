import { useNavigate } from '@tanstack/react-router'
import { Command } from 'cmdk'
import { useEffect, useMemo, useState } from 'react'
import { useCommandRegistryStore } from '../state/commandRegistryStore'
import { useThemeStore } from '../state/themeStore'
import styles from './CommandPalette.module.css'

/** Foundation for the keyboard-first spine (ARCHITECTURE §8): opens on
 * Cmd/Ctrl+K, lists global navigation/theme actions plus whatever the
 * current route has registered via useRegisterCommands. Mounted once in
 * AuthedLayout. */
export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const toggleTheme = useThemeStore((state) => state.toggleTheme)
  const registrations = useCommandRegistryStore((state) => state.registrations)

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        setOpen((current) => !current)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [])

  const globalCommands = useMemo(
    () => [
      { id: 'go-cases', label: 'Go to cases', run: () => navigate({ to: '/' }) },
      { id: 'toggle-theme', label: 'Toggle theme', run: () => toggleTheme() },
    ],
    [navigate, toggleTheme],
  )

  const contextCommands = useMemo(() => Object.values(registrations).flat(), [registrations])

  function run(action: () => void) {
    setOpen(false)
    action()
  }

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Command palette"
      overlayClassName={styles.overlay}
      contentClassName={styles.content}
      shouldFilter
    >
      <Command.Input className={styles.input} placeholder="Type a command…" />
      <Command.List className={styles.list}>
        <Command.Empty className={styles.empty}>No matching commands.</Command.Empty>
        {contextCommands.length > 0 && (
          <Command.Group heading="This case" className={styles.group}>
            {contextCommands.map((command) => (
              <Command.Item
                key={command.id}
                className={styles.item}
                onSelect={() => run(command.run)}
              >
                {command.label}
                {command.shortcut && <span className={styles.shortcut}>{command.shortcut}</span>}
              </Command.Item>
            ))}
          </Command.Group>
        )}
        <Command.Group heading="Navigation" className={styles.group}>
          {globalCommands.map((command) => (
            <Command.Item
              key={command.id}
              className={styles.item}
              onSelect={() => run(command.run)}
            >
              {command.label}
            </Command.Item>
          ))}
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  )
}
