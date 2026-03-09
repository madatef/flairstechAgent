# Project Backend Setup Guide


```
cd backend
```

## 1. Create & Activate a Virtual Environment

### Create the virtual environment
```bash
python -m venv .venv
```

### Activate the virtual environment
| Environment | Command |
|------------|---------|
| **Windows PowerShell** | `.venv/Scripts/Activate` |
| **Git Bash (Windows)** | `source .venv/Scripts/Activate` |
| **Linux / macOS** | `source .venv/bin/activate` |

---

## 2. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 3. Supabase Setup

1. Create a **Supabase project**.
2. Copy your **Project URL** and **API Key**.
3. Create a `.env` file and set your variables.  
   You can rename `.env.example` to `.env` and update the values.

---

## 4. Create the SQL RPC Function

In the Supabase dashboard:

1. Open **SQL Editor** (left sidebar).
2. Paste the script below:
```sql
create or replace function exec_sql(sql text) returns void as $$
begin
    execute sql;
end;
$$ language plpgsql security definer;
```
3. Click **Run**.

This creates an RPC function that the app will call on first run to initialize tables and types through the `lifespan` function in `main.py`.

Alternatively, you can run the SQL manually using the scripts located in:
```
db/schema.sql
```

---

## 5. Run the Application
```bash
python main.py
```

---

## Notes

- This is a **demo**, so **no sign-up or login functionality** is included.
- There is **no authentication flow**.
- The `User` table has **no password field**.
- To create users, use the Supabase **Web UI** or **Supabase CLI** directly.


Run the backen with ```npm run dev``` from the backend directory and that's it!
