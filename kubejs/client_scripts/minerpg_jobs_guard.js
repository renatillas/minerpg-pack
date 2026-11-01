// minerpg: guard against a Jobs+ client crash (2026-11-01).
// Jobs+ 9.0.2 can end up with a job in the local player's list whose definition the client doesn't know
// (getJobInstance() == null). Hovering any job-gated item then crashes the game in Jobs+'s own tooltip
// (LocalPlayer.jobsplus$getJob -> NullPointerException). The server never keeps such jobs, so dropping
// them from the client's copy loses nothing; the server's next job update rebuilds the list anyway.

ClientEvents.tick(event => {
  const player = Client.player
  if (player == null) return
  try {
    // Every tick: the list is at most two jobs, and a tooltip can be drawn in the same frame as an update.
    const it = player.jobsplus$getJobs().iterator()
    while (it.hasNext()) {
      var job = it.next()
      if (job.getJobInstance() == null) {
        console.warn(`[minerpg] dropped a job with no definition from the local job list (level ${job.getLevel()})`)
        it.remove()
      }
    }
  } catch (e) {
    console.error(`[minerpg] jobs guard failed: ${e}`)
  }
})
