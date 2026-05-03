// Field names match what buildKpis() reads from server snapshots:
// cycleTime, cycleTimeP85, timeToMarket, timeToMarketP85,
// flowEfficiency (%), reopenRate (%), wip, backlogAging (days)

export const DEMO_HISTORY = [
  { cycleTime: 6.1, cycleTimeP85: 9.8,  timeToMarket: 11.4, timeToMarketP85: 18.2, flowEfficiency: 53.5, reopenRate: 12, wip: 8,  backlogAging: 28 },
  { cycleTime: 5.7, cycleTimeP85: 9.1,  timeToMarket: 10.8, timeToMarketP85: 17.1, flowEfficiency: 52.8, reopenRate:  8, wip: 7,  backlogAging: 25 },
  { cycleTime: 4.9, cycleTimeP85: 8.2,  timeToMarket:  9.3, timeToMarketP85: 15.4, flowEfficiency: 52.7, reopenRate:  4, wip: 6,  backlogAging: 22 },
  { cycleTime: 5.3, cycleTimeP85: 8.7,  timeToMarket:  9.9, timeToMarketP85: 16.2, flowEfficiency: 53.5, reopenRate: 14, wip: 9,  backlogAging: 24 },
  { cycleTime: 4.2, cycleTimeP85: 7.1,  timeToMarket:  8.7, timeToMarketP85: 13.9, flowEfficiency: 48.3, reopenRate:  5, wip: 5,  backlogAging: 18 },
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
