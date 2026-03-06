# Supabase — Backend-as-a-Service Patterns

## Purpose
Context for using Supabase as a managed PostgreSQL backend. Use when project needs auth, realtime, storage, or a cloud DB without managing infrastructure.

## Connection (Python)
```python
from supabase import create_client, Client

SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-or-service-key"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
```

## CRUD Patterns
```python
# Insert
data = supabase.table("users").insert({"email": "nacho@example.com"}).execute()

# Select with filter
result = supabase.table("users").select("*").eq("email", email).single().execute()

# Update
supabase.table("users").update({"tier": "pro"}).eq("id", user_id).execute()

# Delete
supabase.table("users").delete().eq("id", user_id).execute()

# Upsert
supabase.table("licenses").upsert({"key": key, "active": True}).execute()
```

## Row Level Security (RLS)
```sql
-- Enable RLS on a table
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Users can only read their own data
CREATE POLICY "Own profile only" ON profiles
  FOR SELECT USING (auth.uid() = user_id);
```

## Edge Functions (Deno)
```typescript
// supabase/functions/validate-license/index.ts
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

serve(async (req) => {
  const { key } = await req.json()
  const supabase = createClient(Deno.env.get("URL")!, Deno.env.get("KEY")!)
  
  const { data } = await supabase
    .table("licenses")
    .select("*")
    .eq("key", key)
    .eq("active", true)
    .single()
  
  return new Response(JSON.stringify({ valid: !!data, expires_at: data?.expires_at }))
})
```

## Auth Patterns
```python
# Sign up
supabase.auth.sign_up({"email": email, "password": password})

# Sign in
session = supabase.auth.sign_in_with_password({"email": email, "password": password})
user = session.user

# Get current user
user = supabase.auth.get_user()
```

## Realtime
```python
def handle_change(payload):
    print("Change:", payload)

supabase.realtime.channel("table-changes") \
    .on("postgres_changes", {"event": "*", "schema": "public", "table": "licenses"}, handle_change) \
    .subscribe()
```

## Cost-Saving Rules
- Use `service_role` key only server-side (never expose to client)
- Set RLS policies before going to production
- Use Supabase Storage for files > 1MB (not DB columns)
- Free tier: 500MB DB, 1GB storage, 50MB file uploads
