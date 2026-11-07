# Frontend

React, TypeScript, and Vite shell. Requires Node.js 20.19+ or 22.12+ (Node 24 tested) and npm 11.

```bash
cd frontend
npm ci
npm run gen:types  # refresh src/types/contracts.ts from ../contracts/openapi.json
npm run dev        # local Vite server
npm run build      # type check and production bundle
npm run lint       # ESLint
npm test           # Vitest
npm run format     # Prettier source formatting
```

The current shell renders the contract fixture and navigation for the planned screens. API calls and outcome submission are not yet connected. Generated types are committed for contract drift checks; do not edit them by hand.
