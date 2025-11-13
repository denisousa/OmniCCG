# OmniCCG-Web

## Pages
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


## Requirements to Execute

- Node.js 18+ and npm (install via [nvm](https://github.com/nvm-sh/nvm#installing-and-updating))
- **`OmniCCG-API`** running on `http://127.0.0.1:5000`

## Steps to Install
Download the [repository](https://anonymous.4open.science/r/OmniCCG-660A/):

Go to **`OmniCCG-Web`**:
```
cd OmniCCG/OmniCCG-Web
```

Install dependencies with Poetry:
```
npm install
```

## Steps to Execute
Run the application:
```
npm run dev
```

The platform will be available at `http://localhost:8080`

