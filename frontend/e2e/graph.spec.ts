import { expect, type Page, test } from '@playwright/test'

function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`
}

async function registerAndLogin(page: Page, email: string): Promise<void> {
  await page.goto('/register')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Display name').fill('E2E Tester')
  await page.getByLabel('Password').fill('correct horse battery staple')
  await page.getByRole('button', { name: /create account/i }).click()
  await expect(page.getByRole('heading', { name: 'Cases' })).toBeVisible()
}

async function createCase(page: Page, name: string): Promise<void> {
  await page.getByLabel('Name').fill(name)
  await page.getByRole('button', { name: /create case/i }).click()
  await page.getByRole('link', { name: new RegExp(name) }).click()
  await expect(page.getByRole('heading', { name })).toBeVisible()
}

async function addNode(page: Page, entityTypeLabel: string, value: string): Promise<void> {
  await page.getByLabel('Type').selectOption({ label: entityTypeLabel })
  await page.getByLabel('Value').fill(value)
  await page.getByRole('button', { name: /add node/i }).click()
  await expect(page.getByText(value, { exact: true })).toBeVisible()
}

async function connectNodes(
  page: Page,
  sourceValue: string,
  targetValue: string,
  relationship: string,
): Promise<void> {
  const sourceNode = page.locator('.react-flow__node', { hasText: sourceValue })
  const targetNode = page.locator('.react-flow__node', { hasText: targetValue })
  const sourceHandle = sourceNode.locator('[data-handleid="source"]')
  const targetHandle = targetNode.locator('[data-handleid="target"]')

  const sourceBox = await sourceHandle.boundingBox()
  const targetBox = await targetHandle.boundingBox()
  if (!sourceBox || !targetBox) throw new Error('handle bounding boxes not found')

  await page.mouse.move(sourceBox.x + sourceBox.width / 2, sourceBox.y + sourceBox.height / 2)
  await page.mouse.down()
  await page.mouse.move(targetBox.x + targetBox.width / 2, targetBox.y + targetBox.height / 2, {
    steps: 10,
  })
  await page.mouse.up()

  await expect(page.getByRole('dialog', { name: 'Connect nodes' })).toBeVisible()
  await page.getByLabel('Relationship').fill(relationship)
  await page.getByRole('button', { name: /^connect$/i }).click()
  await expect(page.getByRole('dialog', { name: 'Connect nodes' })).toBeHidden()
}

test('login → create case → build a small graph → reload → intact', async ({ page }) => {
  const email = uniqueEmail()
  const caseName = `E2E Case ${Date.now()}`

  await registerAndLogin(page, email)
  await createCase(page, caseName)

  await addNode(page, 'Domain', 'example.com')
  await addNode(page, 'IPv4 Address', '93.184.216.34')
  await connectNodes(page, 'example.com', '93.184.216.34', 'resolves_to')

  await expect(page.getByText('resolves_to')).toBeVisible()

  await page.reload()
  await expect(page.getByText('example.com', { exact: true })).toBeVisible()
  await expect(page.getByText('93.184.216.34', { exact: true })).toBeVisible()
  await expect(page.getByText('resolves_to')).toBeVisible()
})

test('dragging a node persists its position across reload', async ({ page }) => {
  const email = uniqueEmail()
  const caseName = `E2E Drag Case ${Date.now()}`

  await registerAndLogin(page, email)
  await createCase(page, caseName)
  await addNode(page, 'Domain', 'drag-test.example')

  const node = page.locator('.react-flow__node', { hasText: 'drag-test.example' })
  const box = await node.boundingBox()
  if (!box) throw new Error('node bounding box not found')

  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
  await page.mouse.down()
  await page.mouse.move(box.x + box.width / 2 + 220, box.y + box.height / 2 + 160, { steps: 15 })
  await page.mouse.up()

  // Debounced persistence flushes on drag-stop; give the PATCH a moment to land.
  await page.waitForTimeout(500)

  const caseId = new URL(page.url()).pathname.split('/').pop()
  const nodesAfterDrag: Array<{ value: string; position_x: number; position_y: number }> =
    await page.evaluate(async (id) => {
      const response = await fetch(`/api/v1/cases/${id}/nodes`, {
        headers: { 'X-Grid-Client': 'web' },
      })
      return response.json()
    }, caseId)
  const dragged = nodesAfterDrag.find((n) => n.value === 'drag-test.example')
  expect(dragged).toBeDefined()
  expect(dragged?.position_x).not.toBe(80)

  await page.reload()
  const nodesAfterReload: Array<{ value: string; position_x: number; position_y: number }> =
    await page.evaluate(async (id) => {
      const response = await fetch(`/api/v1/cases/${id}/nodes`, {
        headers: { 'X-Grid-Client': 'web' },
      })
      return response.json()
    }, caseId)
  const draggedAfterReload = nodesAfterReload.find((n) => n.value === 'drag-test.example')
  expect(draggedAfterReload?.position_x).toBeCloseTo(dragged?.position_x ?? 0, 0)
  expect(draggedAfterReload?.position_y).toBeCloseTo(dragged?.position_y ?? 0, 0)
})

test('two open tabs on the same case see a new node live over WS', async ({ context }) => {
  const email = uniqueEmail()
  const caseName = `E2E Live Case ${Date.now()}`

  const pageA = await context.newPage()
  await registerAndLogin(pageA, email)
  await createCase(pageA, caseName)
  const caseUrl = pageA.url()

  const pageB = await context.newPage()
  await pageB.goto(caseUrl)
  await expect(pageB.getByRole('heading', { name: caseName })).toBeVisible()

  await addNode(pageA, 'Domain', 'live-sync.example')

  // No reload on pageB — this only passes if the WS event patched its cache.
  await expect(pageB.getByText('live-sync.example', { exact: true })).toBeVisible({
    timeout: 5000,
  })
})
