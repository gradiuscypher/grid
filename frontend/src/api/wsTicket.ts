import { createWsTicket } from './generated'

export async function createWsTicketRequest(): Promise<string> {
  const { data, error } = await createWsTicket()
  if (error) throw error
  return data.ticket
}
