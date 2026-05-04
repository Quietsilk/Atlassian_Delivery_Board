// Field names match normalizeSnapshot() output in api.js
export const DEMO_HISTORY = [
  { timestamp: "2026-04-05T10:00:00Z", cycleTime: 6.1, cycleTimeP85: 9.8,  timeToMarket: 11.4, timeToMarketP85: 18.2, flowEfficiency: 53.5, reopened: 2, completedCount: 44, wip: 8, backlogAging: 28, wipItems: [] },
  { timestamp: "2026-04-12T10:00:00Z", cycleTime: 5.7, cycleTimeP85: 9.1,  timeToMarket: 10.8, timeToMarketP85: 17.1, flowEfficiency: 52.8, reopened: 1, completedCount: 51, wip: 7, backlogAging: 25, wipItems: [] },
  { timestamp: "2026-04-19T10:00:00Z", cycleTime: 4.9, cycleTimeP85: 8.2,  timeToMarket:  9.3, timeToMarketP85: 15.4, flowEfficiency: 52.7, reopened: 0, completedCount: 58, wip: 6, backlogAging: 22, wipItems: [] },
  { timestamp: "2026-04-26T10:00:00Z", cycleTime: 5.3, cycleTimeP85: 8.7,  timeToMarket:  9.9, timeToMarketP85: 16.2, flowEfficiency: 53.5, reopened: 3, completedCount: 67, wip: 9, backlogAging: 24, wipItems: [] },
  {
    timestamp: "2026-05-03T10:00:00Z", cycleTime: 4.2, cycleTimeP85: 7.1,  timeToMarket:  8.7, timeToMarketP85: 13.9, flowEfficiency: 48.3, reopened: 0, completedCount: 74, wip: 5, backlogAging: 18,
    wipItems: [
      { key: "PROJ-118", title: "Migrate auth service to OAuth 2.0",      assignee: "Alexey M.", daysInProgress: 14, status: "In Progress", blockedReason: "Waiting for security review" },
      { key: "PROJ-97",  title: "Fix race condition in payment processor", assignee: "Daria K.",  daysInProgress: 9,  status: "In Progress", blockedReason: null },
      { key: "PROJ-104", title: "Implement CSV export for analytics",      assignee: "Ivan S.",   daysInProgress: 7,  status: "In Review",   blockedReason: "PR open, no reviewers assigned" },
      { key: "PROJ-112", title: "Update API documentation",                assignee: "Olga V.",   daysInProgress: 5,  status: "In Review",   blockedReason: null },
      { key: "PROJ-89",  title: "Performance profiling — mobile app",      assignee: "Alexey M.", daysInProgress: 3,  status: "In Progress", blockedReason: null },
    ],
  },
];

export const DEMO_ANALYSIS = {
  summary: "Flow is stabilising but QA remains the primary bottleneck — cycle time improved 31% over 5 syncs. WIP is within a healthy range but backlog aging warrants attention.",
  risks: [
    "QA queue depth growing — 6 tickets blocked waiting for review for 3+ days",
    "Sprint overcommitment: planned velocity 28, actual 23 (−18%)",
    "High cycle-time variance across team (range 1.1d – 9.4d) signals uneven workload",
  ],
  actions: [
    "Cap WIP at QA stage to 3 items and assign a dedicated reviewer rotation",
    "Reduce next sprint scope by 15% to align with measured velocity",
    "Run a 30-min cycle-time retro focused on the 3 longest outlier tickets",
  ],
};
