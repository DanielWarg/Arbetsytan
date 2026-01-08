import { apiUrl } from './api'

export async function pollJob(jobId, { auth, intervalMs = 1000, timeoutMs = 180000 } = {}) {
  const deadline = Date.now() + timeoutMs

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const res = await fetch(apiUrl(`/jobs/${jobId}`), {
      headers: auth ? { 'Authorization': `Basic ${auth}` } : undefined
    })
    if (!res.ok) {
      throw new Error(`Failed to fetch job: ${res.status}`)
    }
    const job = await res.json()
    const status = String(job.status || '')

    if (status === 'succeeded' || status === 'failed') {
      return job
    }

    if (Date.now() > deadline) {
      throw new Error('Job timeout')
    }

    await new Promise((r) => setTimeout(r, intervalMs))
  }
}

