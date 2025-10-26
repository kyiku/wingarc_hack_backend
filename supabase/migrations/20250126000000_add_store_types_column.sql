-- Add types column to stores table to store Google Places types (categories)
ALTER TABLE stores ADD COLUMN IF NOT EXISTS types jsonb DEFAULT '[]'::jsonb;

-- Add comment to explain the column
COMMENT ON COLUMN stores.types IS 'Google Places types/categories (e.g., restaurant, cafe, bar)';
