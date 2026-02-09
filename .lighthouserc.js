module.exports = {
  ci: {
    collect: {
      url: ['http://localhost:6006'],
      startServerCommand: 'npm run storybook -- --ci',
      startServerReadyPattern: 'storybook.*Started',
      numberOfRuns: 3,
      settings: { chromeFlags: '--no-sandbox --headless' },
    },
    assert: {
      assertions: {
        'categories:performance': ['error', { minScore: 0.9 }],
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['warn'],
        'categories:seo': ['warn'],
      },
    },
    upload: { target: 'temporary-public-storage' },
  },
};
