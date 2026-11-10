// minerpg: guard against a Jobs+ client crash (2026-11-01).
// Jobs+ 9.0.2 can end up with a job in the local player's list whose definition the client doesn't know
// (getJobInstance() == null). Hovering any job-gated item then crashes the game in Jobs+'s own tooltip
// (LocalPlayer.jobsplus$getJob -> NullPointerException). The server never keeps such jobs, so dropping
// them from the client's copy loses nothing; the server's next job update rebuilds the list anyway.

ClientEvents.tick(event => {
  var guardPlayer = Client.player
  if (guardPlayer == null) return
  // var, not const: Rhino rejects const/let re-declared on every run inside a try block.
  try {
    // Every tick: the list is at most three jobs, and a tooltip can be drawn in the same frame as an update.
    var guardJobs = guardPlayer.jobsplus$getJobs().iterator()
    while (guardJobs.hasNext()) {
      var guardJob = guardJobs.next()
      if (guardJob.getJobInstance() == null) {
        console.warn(`[minerpg] dropped a job with no definition from the local job list (level ${guardJob.getLevel()})`)
        guardJobs.remove()
      }
    }
  } catch (e) {
    console.error(`[minerpg] jobs guard failed: ${e}`)
  }
})
