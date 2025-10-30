-- Add storage metadata to job card attachments
ALTER TABLE job_card_attachments ADD COLUMN file_path VARCHAR(512) NOT NULL DEFAULT '';
ALTER TABLE job_card_attachments ADD COLUMN mime_type VARCHAR(120);
UPDATE job_card_attachments SET file_path = filename WHERE file_path = '';
