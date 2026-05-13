# RBAC Plan (Admin / Staff / Customer)

## 1) Scope & current state
This project provides a Natural-Language-to-SQL backend using:
- **FastAPI routes**: `POST /chat`, `GET /schema`
- **DB introspection**: schema discovery from `information_schema`
- **LLM-generated SQL execution**: `backend/db/query_executor.py::execute_readonly_select()`

### Current security limitation (important)
There is **no authentication/authorization** and **no per-user query/data restriction** in the current code:
- Any caller can invoke `/chat`
- Gemini can generate SQL over the whole `public` schema
- The guardrails in `execute_readonly_select()` only check:
  - query begins with `select`
  - forbidden keywords (basic string checks)

Because of this, all users (Admin/Staff/Customer) are effectively treated the same today.

This RBAC plan defines how access should work going forward.

---

## 2) Data domains in this project (from `backend/scripts/seed_db.py`)
Tables in `public`:
- `public.locations`  
  - `id`, `state_names`
- `public.customers`  
  - `id`, `gender`, `age`, `marital_status`, `segment`, `employees_status`, `payment_method`, `referral`
- `public.transactions`  
  - `id`, `transaction_id`, `transaction_date`, `customer_id`, `location_id`, `amount_spent`

---

## 3) Roles
### A) Admin
**Goal:** Full access for analytics and troubleshooting.

**Permissions (API-level intent)**
- `GET /schema`: allowed
- `POST /chat`: allowed to query any analytics data required for the app

**Allowed DB access**
- Base tables and/or all analytics views:
  - `public.locations`
  - `public.customers`
  - `public.transactions`

---

### B) Staff
**Goal:** Read-only analytics, but restricted to **approved/curated** data shapes.

**Permissions (API-level intent)**
- `GET /schema`: allowed but should be limited to *sanitized* schema (details depend on implementation)
- `POST /chat`: allowed only for **aggregated** and **non-sensitive** queries

**Allowed DB access**
To prevent data leakage, Staff should be restricted to:
- **Analytics views** (recommended) instead of base tables.
- Example categories (implementation-specific view names):
  - spending summaries by:
    - `gender`, `age`, `segment`, `employees_status`, `payment_method`, `state_names`
- Deny direct access to raw rows and sensitive columns via base tables.

---

### C) Customer (end user)
**Goal:** Only the data required for the product experience, strictly aggregated.

**Permissions (API-level intent)**
- `GET /schema`: typically *not shown* fully. If shown, it should be a minimal/sanitized schema.
- `POST /chat`: allowed only to ask questions that map to **safe aggregated analytics**.

**Allowed DB access**
- Only a small set of **customer-safe analytics views** (curated).
- No access to base tables and no access that can reveal individual-level records:
  - no direct `transactions` row retrieval
  - no direct `customers` row retrieval
  - no joins that reconstruct identities unless mediated by approved views

---

## 4) Recommended enforcement strategy (defense-in-depth)
Because the backend executes LLM-generated SQL, RBAC must be enforced **at the database/query level**, not only at the API layer.

### Step 1 — Add authentication & role identity
- Require auth on:
  - `POST /chat`
  - `GET /schema`
- Derive role:
  - `admin`
  - `staff`
  - `customer`

### Step 2 — Enforce allowed query targets (SQL allowlisting)
Replace “string guardrails” with **strong allowlisting**, e.g.:
- Use SQL parsing (AST) and ensure the query reads from only:
  - Staff allowed views (not base tables)
  - Customer allowed views (not base tables)
- Alternatively/also:
  - enforce the SQL contains only `SELECT` from allowlisted view names.

**Outcome:** even if the LLM outputs a valid `SELECT`, it cannot target unauthorized tables/views.

### Step 3 — Use PostgreSQL privileges (GRANT) + optional Row Level Security (RLS)
Recommended:
- Create separate DB roles/users (or map app role to DB role).
- Grant SELECT only on allowed views per role.
- Optionally add RLS to support future per-tenant/per-user scoping (if your dataset becomes tenant-scoped later).

**Outcome:** unauthorized SQL attempts fail at DB permission checks even if bypassed at the API layer.

### Step 4 — Keep existing read-only + timeout guardrails
Continue to keep:
- `READ ONLY` transaction
- `statement_timeout`
- (But do not rely solely on these checks for RBAC.)

---

## 5) Exact DB table/column accessibility by role

> Dataset tables come from `backend/scripts/seed_db.py` and exist in `public` schema:
> - `public.locations(id, state_names)`
> - `public.customers(id, gender, age, marital_status, segment, employees_status, payment_method, referral)`
> - `public.transactions(id, transaction_id, transaction_date, customer_id, location_id, amount_spent)`
>
> **Important:** This backend currently executes LLM-generated SQL without per-role filtering. The table below defines the intended permissions that must be enforced via **SQL allowlisting + DB GRANT/RLS**.

### Admin
- `public.locations`
  - `id` ✅
  - `state_names` ✅
- `public.customers`
  - `id` ✅
  - `gender` ✅
  - `age` ✅
  - `marital_status` ✅
  - `segment` ✅
  - `employees_status` ✅
  - `payment_method` ✅
  - `referral` ✅
- `public.transactions`
  - `id` ✅
  - `transaction_id` ✅
  - `transaction_date` ✅
  - `customer_id` ✅
  - `location_id` ✅
  - `amount_spent` ✅

### Staff
- `public.locations`
  - `id` ❌
  - `state_names` ✅ *(dimension for aggregates only)*
- `public.customers`
  - `id` ❌
  - `gender` ✅
  - `age` ✅
  - `marital_status` ❌
  - `segment` ✅
  - `employees_status` ✅
  - `payment_method` ✅
  - `referral` ❌
- `public.transactions`
  - `id` ❌
  - `transaction_id` ❌
  - `transaction_date` ✅ *(aggregated/time-bucket only)*
  - `customer_id` ❌
  - `location_id` ❌
  - `amount_spent` ✅

### Customer (end user)
- `public.locations`
  - `id` ❌
  - `state_names` ✅ *(aggregate dimension only)*
- `public.customers`
  - `id` ❌
  - `gender` ✅ *(aggregate only)*
  - `age` ✅ *(bucketed/aggregate only)*
  - `marital_status` ❌
  - `segment` ❌
  - `employees_status` ❌
  - `payment_method` ✅ *(aggregate only)*
  - `referral` ❌
- `public.transactions`
  - `id` ❌
  - `transaction_id` ❌
  - `transaction_date` ❌
  - `customer_id` ❌
  - `location_id` ❌
  - `amount_spent` ✅ *(aggregate only)*

---

---

## 6) Notes / future-proofing
- If you later introduce **per-tenant** or **per-customer** data separation, prefer:
  - RLS policies keyed by a tenant/user id
  - Session variables (e.g., `SET app.current_user_id = ...`) passed via connection
- The LLM prompt should be constrained to the role’s allowed schema/views to reduce the chance of generating disallowed queries.

---

## 7) Implementation checklist (high level)
1. Add authentication middleware to FastAPI.
2. Add role mapping to permissions.
3. Create and maintain:
   - staff analytics views
   - customer-safe analytics views
4. Update query execution:
   - parse SQL
   - verify referenced relations are allowlisted for the role
5. Apply DB `GRANT`:
   - revoke base-table access as needed
   - grant only required view SELECT privileges
6. Update `/schema` response to be role-aware and sanitized.
