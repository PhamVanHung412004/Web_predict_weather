FE_nextjs - Next.js frontend for Web_predict_weather

This small Next.js app provides a beautiful UI to upload CSV files, view analysis plots produced by the Flask backend, and call the prediction endpoint.

Quick start (Windows PowerShell):

1. Install Node.js (>=16)
2. From this folder run:

```powershell
cd FE_nextjs
npm install
npm run dev
```

3. Open http://localhost:3000 in your browser. Make sure the backend Flask server is running at http://127.0.0.1:5000 (or set NEXT_PUBLIC_BACKEND_URL).

Endpoints used:
- POST /api/analyze_csv (upload CSV)
- POST /api/predict (JSON body of features)
- GET /results/{filename} (images)

Notes:
- The app is intentionally minimal and easy to extend. Add styling libraries or charts (Chart.js, Recharts) as needed.

Tailwind CSS
-- The project includes Tailwind configuration. If you cloned the repo, run `npm install` to install Tailwind and PostCSS dev dependencies. The dev server will compile Tailwind utilities automatically.
