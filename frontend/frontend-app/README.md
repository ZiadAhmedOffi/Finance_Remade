# FinanceRemade - Frontend Application

A modern financial dashboard built with React 19, TypeScript, and Vite.

## 🏗 Component Structure

### Pages
- **Dashboard:** The entry point. Features auto-rotating performance graphs for all accessible funds.
- **FundDashboard:** The main workspace for a specific fund. Uses a tabbed interface to organize financial data.

### Tabs (`components/`)
- **ModelInputsTab:** Configuration of fund parameters.
- **DealPrognosisTab:** Investment tracking and scenario modeling.
- **FundPerformanceTab:** Advanced analytics and waterfall charts.
- **AggregatedExitsTab:** Scenario comparison and exit analysis.
- **AdminFeeTab:** Detailed G&A and operations cost reporting.

## 🎨 Design System

The application uses a custom "Enterprise" design system defined in `FundDashboard.css` and `Dashboard.css`.

- **Primary Theme:** Professional Blue (`#2563eb`).
- **Containers:** All major sections are wrapped in `content-card` (rounded rectangles).
- **Data Display:** Tables use `data-table` with zebra striping and sticky headers.
- **Spacing:** Generous margins (3rem+) are used to prevent visual clutter in data-heavy views.

## 📈 Visualizations

Powered by **Recharts**:
- **Waterfall Charts:** Annual portfolio expansion.
- **Line Charts:** IRR-based performance scenarios.
- **Pie Charts:** Portfolio diversification by company type.
- **Bar Charts:** Holding period analysis.

## 🛠 Commands
- `npm run dev`: Start development server.
- `npm run build`: Build for production.
- `npm run lint`: Run ESLint.
