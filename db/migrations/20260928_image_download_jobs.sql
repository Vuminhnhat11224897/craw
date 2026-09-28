-- Apply in public on the article database before starting the image API and worker.
-- Existing article tables are managed by the article writer, not this migration.
CREATE TABLE IF NOT EXISTS image_download_jobs (
    image_id uuid PRIMARY KEY,
    source_url varchar(2000) NOT NULL,
    article_url varchar(2000) NOT NULL,
    object_key varchar(2000) NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'downloaded', 'failed')),
    attempts integer NOT NULL DEFAULT 0,
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    locked_until timestamptz,
    claim_token uuid,
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Also upgrade schemas created before completed jobs were retained.
ALTER TABLE image_download_jobs DROP CONSTRAINT IF EXISTS image_download_jobs_status_check;
ALTER TABLE image_download_jobs ADD CONSTRAINT image_download_jobs_status_check
    CHECK (status IN ('pending', 'processing', 'downloaded', 'failed'));

CREATE INDEX IF NOT EXISTS image_download_jobs_due
    ON image_download_jobs (next_attempt_at, image_id) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS image_download_jobs_expired
    ON image_download_jobs (locked_until, image_id) WHERE status = 'processing';
