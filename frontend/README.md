# ShuleLink Web

Vue 3 + Vite + Bootstrap 5 frontend for ShuleLink.

## Run locally

```powershell
cd frontend
npm install
npm run dev
```

The frontend resolves the API from the current hostname by default:

- Platform: `http://admin.localhost:5173` → `http://admin.localhost:8000/api/v1`
- Tenant: `http://<slug>.localhost:5173` → `http://<slug>.localhost:8000/api/v1`

You can override this with `VITE_API_URL` in `.env` when needed.

## Phase 2 test flow

1. Start FastAPI on port `8000`.
2. Start Vue on port `5173`.
3. Open `http://admin.localhost:5173/login`.
4. Sign in with the platform administrator.
5. Open **Schools** and create a shared tenant, for example `demo-primary`.
6. Create a `school_admin` user for the tenant.
7. Open the tenant from the Schools table.
8. Sign in at `http://demo-primary.localhost:5173/login` with the school user.
9. The School Portal should show the resolved tenant context.

The browser stores the short-lived access token and rotating refresh token for the current frontend origin. Platform and tenant subdomains intentionally have separate browser storage, so tenant users sign in on their own school host.
