# OmniCCG Frontend - Code Clone Genealogy Visualization

A modern web interface for visualizing and analyzing code clone genealogies, built with React, TypeScript, and shadcn/ui components.

## About Code Clone Genealogy

Code clone genealogy tracks the evolution of code clones (duplicated code fragments) across multiple versions of a software system. This tool helps researchers and developers understand:

- How clones evolve over time (Added, Removed, Unchanged)
- Which clones persist across versions (alive vs dead lineages)
- Clone change patterns (consistent, inconsistent, stable)
- Clone density and volatility metrics
- The lifespan and survival rate of clone genealogies

## Features

### 🏠 Home Page
- Configure analysis parameters
- Input repository URL
- Select clone detection tools (NiCad, Simian, or external API)
- Choose temporal scope (all commits, specific commit range, or time-based)
- Advanced options: merge commits, commit leaps

### 📊 Visualize Page
Interactive genealogy visualization with:
- **Multiple lineage tabs**: Each clone genealogy in a separate tab
- **Graph visualization**: Cytoscape-based interactive graph showing clone evolution
- **Node details panel**: Detailed information about each version including:
  - Commit hash and version number
  - Evolution status (Add/Subtraction/Same)
  - Change patterns (Consistent/Inconsistent/Same)
  - Source code locations
  - Code snippet viewer with syntax highlighting
- **Zoom controls**: Zoom in/out and fit-to-screen
- **Metrics button**: Navigate to detailed metrics analysis

### 📈 Metrics Page
Comprehensive metrics dashboard displaying:

#### Clone Statistics
- **Total Clone Lineages**: Number of distinct clone genealogies
- **Evolution Pattern**: Distribution of Add/Same/Subtract changes
- **Change Patterns**: Consistent/Stable/Inconsistent classifications

#### Status & Lifespan
- **Alive vs Dead Lineages**: Current status with percentages
- **Dead Lineage Length**: Min/Avg/Max lifespan statistics

#### Clone Density Analysis
- **Version-by-version density**: Bar chart showing clone density evolution
- **Commit hash integration**: Links density to specific commits
- **Summary statistics**: Average density metrics

#### K-Volatile Analysis
- **Survival curve**: CDF chart showing clone mortality by age
- **Age distribution**: How long clones survive before removal
- **Interpretation guide**: Understanding clone stability patterns

## Technology Stack

- **Framework**: React 18.3.1 with TypeScript 5.8.3
- **Build Tool**: Vite 5.4.19
- **UI Components**: shadcn/ui (modern, accessible components)
- **Styling**: Tailwind CSS
- **Visualization**: Cytoscape.js for graph rendering
- **API Client**: Fetch API with TypeScript types
- **Routing**: React Router DOM
- **State Management**: React hooks (useState, useEffect)

## Getting Started

### Prerequisites

- Node.js 18+ and npm (install via [nvm](https://github.com/nvm-sh/nvm#installing-and-updating))
- OmniCCG Backend API running on `http://127.0.0.1:5000`

### Installation

```sh
# Clone the repository
git clone <YOUR_GIT_URL>
cd clone-roots

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:8080`

### Production Build

```sh
# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/
│   ├── genealogy/          # Genealogy visualization components
│   │   ├── LineageGraph.tsx       # Cytoscape graph renderer
│   │   ├── NodeDetailsPanel.tsx   # Node information sidebar
│   │   └── CodeSnippetModal.tsx   # Code viewer modal
│   └── ui/                 # shadcn/ui components
├── pages/
│   ├── Home.tsx           # Configuration page
│   ├── Visualize.tsx      # Genealogy visualization
│   ├── Metrics.tsx        # Metrics dashboard
│   └── NotFound.tsx       # 404 page
├── services/
│   └── api.ts             # API client
└── types/
    └── index.ts           # TypeScript type definitions
```

## API Integration

The frontend communicates with the OmniCCG backend API:

- `POST /detect_clones` - Start clone detection analysis
- `GET /clone_genealogy/{taskId}` - Retrieve genealogy results
- `GET /get_metrics/{taskId}` - Fetch metrics data
- `POST /get_code_snippets` - Retrieve source code snippets

## Development

### Code Style

- TypeScript strict mode enabled
- ESLint for code linting
- Prettier for code formatting (via shadcn/ui conventions)

### Key Components

**LineageGraph**: Renders interactive genealogy graphs using Cytoscape
- Preserves zoom/pan when clicking nodes
- Color-coded nodes based on evolution/change patterns
- DAG layout (left-to-right flow)

**NodeDetailsPanel**: Displays detailed information
- Version metadata (hash, evolution, change)
- Source code locations
- Integrated code snippet viewer

**Metrics Page**: Comprehensive analytics
- XML-based metrics parsing
- Interactive charts and visualizations
- Clone density trends
- K-volatile survival analysis

## Contributing

When working on this project:

1. Keep the genealogy visualization responsive and performant
2. Ensure all metrics are accurately parsed from XML
3. Maintain accessibility (ARIA labels, keyboard navigation)
4. Test with various repository sizes
5. Handle API errors gracefully with user-friendly messages

## License

This project is part of the OmniCCG (Code Clone Genealogy) research tool.

## Related Projects

- **OmniCCG Backend**: Python-based clone detection and genealogy analysis
- **NiCad**: Clone detection tool integration
- **Simian**: Alternative clone detector

## Support

For issues or questions:
- Check the backend API logs for errors
- Verify the repository URL is accessible
- Ensure the selected clone detector is properly configured
- Review browser console for frontend errors
