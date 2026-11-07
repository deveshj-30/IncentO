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

Start the backend on `http://localhost:8000` before using the live flow; Vite proxies `/api` there. The shell initially displays the contract fixture with a clear label. Use **Load and investigate** to load a scenario and create a live run. The incident screen can record an outcome and retry failed retention. Generated types are committed for contract drift checks; do not edit them by hand.
