// Examples data extracted from results_of_evaluation
export const genericExamples = [
  {
    title: 'Generic Examples',
    items: [
      {
        name: 'avro',
        git: 'https://github.com/apache/avro',
        from_lasy_days: 360,
        fixed_leaps: 20,
        time: '298 seconds',
        clone_detector: 'nicad',
      },
      {
        name: 'jfreechart',
        git: 'https://github.com/jfree/jfreechart',
        from_lasy_days: 360,
        merge_commits: true,
        time: '98 seconds',
        clone_detector: 'nicad',
      },
      {
        name: 'litiengine',
        git: 'https://github.com/gurkenlabs/litiengine',
        from_specific_commit: "ee67f1f6e0c67e19460358adf29ed02bd6374a65",
        fixed_leaps: 13,
        time: '28 seconds',
        clone_detector: 'nicad',
      },
    ],
  },
];

export const preliminaryExamples = [
  {
    title: 'Preliminary Evaluation',
    items: [
      {
        name: 'booklore',
        git: 'https://github.com/booklore-app/BookLore',
        from_first_commit: true,
        fixed_leaps: 200,
        start_commit: 'first',
        time: '32 seconds',
        clone_detector: 'nicad',
      },
      {
        name: 'pkl',
        git: 'https://github.com/apple/pkl',
        from_first_commit: true,
        fixed_leaps: 200,
        start_commit: 'first',
        time: '37 seconds',
        clone_detector: 'nicad',
      },
      {
        name: 'PeerBanHelper',
        git: 'https://github.com/PBH-BTN/PeerBanHelper',
        from_first_commit: true,
        fixed_leaps: 200,
        start_commit: 'first',
        time: '143 seconds',
        clone_detector: 'nicad',
      },
      {
        name: 'spring-ai-alibaba',
        git: 'https://github.com/alibaba/spring-ai-alibaba',
        from_first_commit: true,
        fixed_leaps: 200,
        start_commit: 'first',
        time: '152 seconds',
        clone_detector: 'nicad',
      },
    ],
  },
];

export default genericExamples;
