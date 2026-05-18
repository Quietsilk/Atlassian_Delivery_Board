// Field names match normalizeSnapshot() output in api.js
export const DEMO_HISTORY = [
  { timestamp: "2026-04-05T10:00:00Z", cycleTime: 6.1, cycleTimeP85: 9.8,  timeToMarket: 11.4, timeToMarketP85: 18.2, flowEfficiency: 53.5, sprintCompletion: 68.2, sprintCommittedCount: 22, sprintCompletedCount: 15, sprintAddedCount: 3, sprintRemovedCount: 1, reopenedCount: 3, reopenedRate: 6.8, completedCount: 44, throughput: 5, wip: 8, backlogAging: 28, wipItems: [] },
  { timestamp: "2026-04-12T10:00:00Z", cycleTime: 5.7, cycleTimeP85: 9.1,  timeToMarket: 10.8, timeToMarketP85: 17.1, flowEfficiency: 52.8, sprintCompletion: 75.0, sprintCommittedCount: 20, sprintCompletedCount: 15, sprintAddedCount: 2, sprintRemovedCount: 0, reopenedCount: 2, reopenedRate: 3.9, completedCount: 51, throughput: 7, wip: 7, backlogAging: 25, wipItems: [] },
  { timestamp: "2026-04-19T10:00:00Z", cycleTime: 4.9, cycleTimeP85: 8.2,  timeToMarket:  9.3, timeToMarketP85: 15.4, flowEfficiency: 52.7, sprintCompletion: 81.0, sprintCommittedCount: 21, sprintCompletedCount: 17, sprintAddedCount: 1, sprintRemovedCount: 1, reopenedCount: 4, reopenedRate: 6.9, completedCount: 58, throughput: 7, wip: 6, backlogAging: 22, wipItems: [] },
  { timestamp: "2026-04-26T10:00:00Z", cycleTime: 5.3, cycleTimeP85: 8.7,  timeToMarket:  9.9, timeToMarketP85: 16.2, flowEfficiency: 53.5, sprintCompletion: 73.9, sprintCommittedCount: 23, sprintCompletedCount: 17, sprintAddedCount: 4, sprintRemovedCount: 2, reopenedCount: 3, reopenedRate: 4.5, completedCount: 67, throughput: 9, wip: 9, backlogAging: 24, wipItems: [] },
  {
    timestamp: "2026-05-03T10:00:00Z", cycleTime: 4.2, cycleTimeP85: 7.1,  timeToMarket:  8.7, timeToMarketP85: 13.9, flowEfficiency: 48.3, sprintCompletion: 90.0, sprintCommittedCount: 20, sprintCompletedCount: 18, sprintAddedCount: 2, sprintRemovedCount: 0, reopenedCount: 2, reopenedRate: 2.7, completedCount: 74, throughput: 7, wip: 5, backlogAging: 18,
    wipItems: [
      { key: "PROJ-118", title: "Migrate auth service to OAuth 2.0",      assignee: "Alexey M.", daysInProgress: 14, status: "In Progress", blockedReason: "Waiting for security review" },
      { key: "PROJ-97",  title: "Fix race condition in payment processor", assignee: "Daria K.",  daysInProgress: 9,  status: "In Progress", blockedReason: null },
      { key: "PROJ-104", title: "Implement CSV export for analytics",      assignee: "Ivan S.",   daysInProgress: 7,  status: "In Review",   blockedReason: "PR open, no reviewers assigned" },
      { key: "PROJ-112", title: "Update API documentation",                assignee: "Olga V.",   daysInProgress: 5,  status: "In Review",   blockedReason: null },
      { key: "PROJ-89",  title: "Performance profiling — mobile app",      assignee: "Alexey M.", daysInProgress: 3,  status: "In Progress", blockedReason: null },
    ],
  },
];
