-- Creates per-agent databases on the shared hermes-db instance.
-- Add a new CREATE DATABASE line here for each new agent.
CREATE DATABASE finance;
GRANT ALL PRIVILEGES ON DATABASE finance TO hermes;
