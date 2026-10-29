-- Flind Wave252: READ-ONLY PostgreSQL structural catalog snapshot.
-- Run ONLY on independently verified owner-only synthetic Unix-socket
-- PostgreSQL 17 database. Do not connect to customer, shared, or production DB.
-- Output CSV using COPY TO STDOUT, never writes to a database.
-- Numeric physical attnums are deliberately emitted for normalization by
-- qualify_pg_restore_catalog_wave252.py. Constraint expressions, function
-- bodies and index predicate semantics are NOT proven by this snapshot.
COPY (
SELECT kind, name, description FROM (
  SELECT 'relation' AS kind, n.nspname||'.'||c.relname AS name,
    (c.relkind::text||'|'||c.relpersistence::text||'|'||c.relispartition::text) AS description
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'
  UNION ALL
  SELECT 'column', n.nspname||'.'||c.relname||'.'||a.attname,
    (a.attnum::text||'|'||format_type(a.atttypid,a.atttypmod)||'|'||a.attnotnull::text||'|'||
     a.attidentity::text||'|'||a.attgenerated::text)
  FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
  JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND a.attnum>0 AND NOT a.attisdropped
  UNION ALL
  SELECT 'index', ni.nspname||'.'||ci.relname,
    (nt.nspname||'.'||t.relname||'|'||i.indisunique::text||'|'||
     i.indisprimary::text||'|'||i.indisvalid::text||'|'||
     i.indkey::text||'|'||i.indnkeyatts::text)
  FROM pg_index i JOIN pg_class ci ON ci.oid=i.indexrelid
  JOIN pg_namespace ni ON ni.oid=ci.relnamespace
  JOIN pg_class t ON t.oid=i.indrelid
  JOIN pg_namespace nt ON nt.oid=t.relnamespace
  WHERE ni.nspname='public' AND nt.nspname='public'
  UNION ALL
  SELECT 'constraint', coalesce(n.nspname||'.'||c.relname,'public')||'.'||co.conname,
    (co.contype::text||'|'||co.condeferrable::text||'|'||co.condeferred::text||'|'||
     co.convalidated::text||'|'||co.conkey::text||'|'||co.confkey::text||'|'||
     coalesce(ref.relname,''))
  FROM pg_constraint co JOIN pg_namespace n ON n.oid=co.connamespace
  LEFT JOIN pg_class c ON c.oid=co.conrelid
  LEFT JOIN pg_class ref ON ref.oid=co.confrelid
  WHERE n.nspname='public'
  UNION ALL
  SELECT 'function', n.nspname||'.'||p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',
    (p.prokind::text||'|'||p.provolatile::text||'|'||p.prorettype::regtype::text)
  FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'
  UNION ALL
  SELECT 'trigger', n.nspname||'.'||c.relname||'.'||tr.tgname,
    (tr.tgtype::text||'|'||tr.tgenabled::text)
  FROM pg_trigger tr JOIN pg_class c ON c.oid=tr.tgrelid
  JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND NOT tr.tgisinternal
) AS catalog ORDER BY kind,name,description
) TO STDOUT WITH CSV;
