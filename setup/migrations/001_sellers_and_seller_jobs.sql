-- Migration: Create sellers and seller_jobs tables
-- These tables enable seller management and cross-user job syncing.

-- Sellers table
CREATE TABLE IF NOT EXISTS sellers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seller jobs table — jobs assigned to sellers, synced across all users
CREATE TABLE IF NOT EXISTS seller_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id TEXT NOT NULL,
  seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
  company_name TEXT NOT NULL,
  domain TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  requested_by TEXT NOT NULL,
  salesperson_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  result_data JSONB
);

-- Index for fast lookups by seller
CREATE INDEX IF NOT EXISTS idx_seller_jobs_seller_id ON seller_jobs(seller_id);

-- Index for fast lookups by job_id
CREATE INDEX IF NOT EXISTS idx_seller_jobs_job_id ON seller_jobs(job_id);

-- Enable Row Level Security (allow all for now — no auth layer)
ALTER TABLE sellers ENABLE ROW LEVEL SECURITY;
ALTER TABLE seller_jobs ENABLE ROW LEVEL SECURITY;

-- Allow all operations for anon key (public access for now)
CREATE POLICY "Allow all on sellers" ON sellers FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on seller_jobs" ON seller_jobs FOR ALL USING (true) WITH CHECK (true);

-- Enable realtime for both tables
ALTER PUBLICATION supabase_realtime ADD TABLE sellers;
ALTER PUBLICATION supabase_realtime ADD TABLE seller_jobs;
