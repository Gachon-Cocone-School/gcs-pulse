--
-- PostgreSQL database dump
--

\restrict QFafwNu6ErhifFMsbFtj7BZ8bhWG9wiSQ4UWkxbjdGqeNYdWBdvifa6saYxyI9R

-- Dumped from database version 17.6
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: auth; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA auth;


--
-- Name: extensions; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA extensions;


--
-- Name: graphql; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA graphql;


--
-- Name: graphql_public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA graphql_public;


--
-- Name: pgbouncer; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA pgbouncer;


--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


--
-- Name: realtime; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA realtime;


--
-- Name: storage; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA storage;


--
-- Name: vault; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA vault;


--
-- Name: pg_graphql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_graphql WITH SCHEMA graphql;


--
-- Name: EXTENSION pg_graphql; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_graphql IS 'pg_graphql: GraphQL support';


--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA extensions;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: supabase_vault; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;


--
-- Name: EXTENSION supabase_vault; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION supabase_vault IS 'Supabase Vault Extension';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: aal_level; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.aal_level AS ENUM (
    'aal1',
    'aal2',
    'aal3'
);


--
-- Name: code_challenge_method; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.code_challenge_method AS ENUM (
    's256',
    'plain'
);


--
-- Name: factor_status; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.factor_status AS ENUM (
    'unverified',
    'verified'
);


--
-- Name: factor_type; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.factor_type AS ENUM (
    'totp',
    'webauthn',
    'phone'
);


--
-- Name: oauth_authorization_status; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.oauth_authorization_status AS ENUM (
    'pending',
    'approved',
    'denied',
    'expired'
);


--
-- Name: oauth_client_type; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.oauth_client_type AS ENUM (
    'public',
    'confidential'
);


--
-- Name: oauth_registration_type; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.oauth_registration_type AS ENUM (
    'dynamic',
    'manual'
);


--
-- Name: oauth_response_type; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.oauth_response_type AS ENUM (
    'code'
);


--
-- Name: one_time_token_type; Type: TYPE; Schema: auth; Owner: -
--

CREATE TYPE auth.one_time_token_type AS ENUM (
    'confirmation_token',
    'reauthentication_token',
    'recovery_token',
    'email_change_token_new',
    'email_change_token_current',
    'phone_change_token'
);


--
-- Name: action; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.action AS ENUM (
    'INSERT',
    'UPDATE',
    'DELETE',
    'TRUNCATE',
    'ERROR'
);


--
-- Name: equality_op; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.equality_op AS ENUM (
    'eq',
    'neq',
    'lt',
    'lte',
    'gt',
    'gte',
    'in'
);


--
-- Name: user_defined_filter; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.user_defined_filter AS (
	column_name text,
	op realtime.equality_op,
	value text
);


--
-- Name: wal_column; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.wal_column AS (
	name text,
	type_name text,
	type_oid oid,
	value jsonb,
	is_pkey boolean,
	is_selectable boolean
);


--
-- Name: wal_rls; Type: TYPE; Schema: realtime; Owner: -
--

CREATE TYPE realtime.wal_rls AS (
	wal jsonb,
	is_rls_enabled boolean,
	subscription_ids uuid[],
	errors text[]
);


--
-- Name: buckettype; Type: TYPE; Schema: storage; Owner: -
--

CREATE TYPE storage.buckettype AS ENUM (
    'STANDARD',
    'ANALYTICS',
    'VECTOR'
);


--
-- Name: email(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.email() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.email', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'email')
  )::text
$$;


--
-- Name: FUNCTION email(); Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON FUNCTION auth.email() IS 'Deprecated. Use auth.jwt() -> ''email'' instead.';


--
-- Name: jwt(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.jwt() RETURNS jsonb
    LANGUAGE sql STABLE
    AS $$
  select 
    coalesce(
        nullif(current_setting('request.jwt.claim', true), ''),
        nullif(current_setting('request.jwt.claims', true), '')
    )::jsonb
$$;


--
-- Name: role(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.role() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.role', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role')
  )::text
$$;


--
-- Name: FUNCTION role(); Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON FUNCTION auth.role() IS 'Deprecated. Use auth.jwt() -> ''role'' instead.';


--
-- Name: uid(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.uid() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$$;


--
-- Name: FUNCTION uid(); Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON FUNCTION auth.uid() IS 'Deprecated. Use auth.jwt() -> ''sub'' instead.';


--
-- Name: grant_pg_cron_access(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.grant_pg_cron_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS (
    SELECT
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_cron'
  )
  THEN
    grant usage on schema cron to postgres with grant option;

    alter default privileges in schema cron grant all on tables to postgres with grant option;
    alter default privileges in schema cron grant all on functions to postgres with grant option;
    alter default privileges in schema cron grant all on sequences to postgres with grant option;

    alter default privileges for user supabase_admin in schema cron grant all
        on sequences to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on tables to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on functions to postgres with grant option;

    grant all privileges on all tables in schema cron to postgres with grant option;
    revoke all on table cron.job from postgres;
    grant select on table cron.job to postgres with grant option;
  END IF;
END;
$$;


--
-- Name: FUNCTION grant_pg_cron_access(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.grant_pg_cron_access() IS 'Grants access to pg_cron';


--
-- Name: grant_pg_graphql_access(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.grant_pg_graphql_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    func_is_graphql_resolve bool;
BEGIN
    func_is_graphql_resolve = (
        SELECT n.proname = 'resolve'
        FROM pg_event_trigger_ddl_commands() AS ev
        LEFT JOIN pg_catalog.pg_proc AS n
        ON ev.objid = n.oid
    );

    IF func_is_graphql_resolve
    THEN
        -- Update public wrapper to pass all arguments through to the pg_graphql resolve func
        DROP FUNCTION IF EXISTS graphql_public.graphql;
        create or replace function graphql_public.graphql(
            "operationName" text default null,
            query text default null,
            variables jsonb default null,
            extensions jsonb default null
        )
            returns jsonb
            language sql
        as $$
            select graphql.resolve(
                query := query,
                variables := coalesce(variables, '{}'),
                "operationName" := "operationName",
                extensions := extensions
            );
        $$;

        -- This hook executes when `graphql.resolve` is created. That is not necessarily the last
        -- function in the extension so we need to grant permissions on existing entities AND
        -- update default permissions to any others that are created after `graphql.resolve`
        grant usage on schema graphql to postgres, anon, authenticated, service_role;
        grant select on all tables in schema graphql to postgres, anon, authenticated, service_role;
        grant execute on all functions in schema graphql to postgres, anon, authenticated, service_role;
        grant all on all sequences in schema graphql to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on tables to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on functions to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on sequences to postgres, anon, authenticated, service_role;

        -- Allow postgres role to allow granting usage on graphql and graphql_public schemas to custom roles
        grant usage on schema graphql_public to postgres with grant option;
        grant usage on schema graphql to postgres with grant option;
    END IF;

END;
$_$;


--
-- Name: FUNCTION grant_pg_graphql_access(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.grant_pg_graphql_access() IS 'Grants access to pg_graphql';


--
-- Name: grant_pg_net_access(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.grant_pg_net_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_net'
  )
  THEN
    IF NOT EXISTS (
      SELECT 1
      FROM pg_roles
      WHERE rolname = 'supabase_functions_admin'
    )
    THEN
      CREATE USER supabase_functions_admin NOINHERIT CREATEROLE LOGIN NOREPLICATION;
    END IF;

    GRANT USAGE ON SCHEMA net TO supabase_functions_admin, postgres, anon, authenticated, service_role;

    IF EXISTS (
      SELECT FROM pg_extension
      WHERE extname = 'pg_net'
      -- all versions in use on existing projects as of 2025-02-20
      -- version 0.12.0 onwards don't need these applied
      AND extversion IN ('0.2', '0.6', '0.7', '0.7.1', '0.8', '0.10.0', '0.11.0')
    ) THEN
      ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;
      ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;

      ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;
      ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;

      REVOKE ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;
      REVOKE ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;

      GRANT EXECUTE ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
      GRANT EXECUTE ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
    END IF;
  END IF;
END;
$$;


--
-- Name: FUNCTION grant_pg_net_access(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.grant_pg_net_access() IS 'Grants access to pg_net';


--
-- Name: pgrst_ddl_watch(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.pgrst_ddl_watch() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN SELECT * FROM pg_event_trigger_ddl_commands()
  LOOP
    IF cmd.command_tag IN (
      'CREATE SCHEMA', 'ALTER SCHEMA'
    , 'CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO', 'ALTER TABLE'
    , 'CREATE FOREIGN TABLE', 'ALTER FOREIGN TABLE'
    , 'CREATE VIEW', 'ALTER VIEW'
    , 'CREATE MATERIALIZED VIEW', 'ALTER MATERIALIZED VIEW'
    , 'CREATE FUNCTION', 'ALTER FUNCTION'
    , 'CREATE TRIGGER'
    , 'CREATE TYPE', 'ALTER TYPE'
    , 'CREATE RULE'
    , 'COMMENT'
    )
    -- don't notify in case of CREATE TEMP table or other objects created on pg_temp
    AND cmd.schema_name is distinct from 'pg_temp'
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


--
-- Name: pgrst_drop_watch(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.pgrst_drop_watch() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  obj record;
BEGIN
  FOR obj IN SELECT * FROM pg_event_trigger_dropped_objects()
  LOOP
    IF obj.object_type IN (
      'schema'
    , 'table'
    , 'foreign table'
    , 'view'
    , 'materialized view'
    , 'function'
    , 'trigger'
    , 'type'
    , 'rule'
    )
    AND obj.is_temporary IS false -- no pg_temp objects
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


--
-- Name: set_graphql_placeholder(); Type: FUNCTION; Schema: extensions; Owner: -
--

CREATE FUNCTION extensions.set_graphql_placeholder() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $_$
    DECLARE
    graphql_is_dropped bool;
    BEGIN
    graphql_is_dropped = (
        SELECT ev.schema_name = 'graphql_public'
        FROM pg_event_trigger_dropped_objects() AS ev
        WHERE ev.schema_name = 'graphql_public'
    );

    IF graphql_is_dropped
    THEN
        create or replace function graphql_public.graphql(
            "operationName" text default null,
            query text default null,
            variables jsonb default null,
            extensions jsonb default null
        )
            returns jsonb
            language plpgsql
        as $$
            DECLARE
                server_version float;
            BEGIN
                server_version = (SELECT (SPLIT_PART((select version()), ' ', 2))::float);

                IF server_version >= 14 THEN
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql extension is not enabled.'
                            )
                        )
                    );
                ELSE
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql is only available on projects running Postgres 14 onwards.'
                            )
                        )
                    );
                END IF;
            END;
        $$;
    END IF;

    END;
$_$;


--
-- Name: FUNCTION set_graphql_placeholder(); Type: COMMENT; Schema: extensions; Owner: -
--

COMMENT ON FUNCTION extensions.set_graphql_placeholder() IS 'Reintroduces placeholder function for graphql_public.graphql';


--
-- Name: get_auth(text); Type: FUNCTION; Schema: pgbouncer; Owner: -
--

CREATE FUNCTION pgbouncer.get_auth(p_usename text) RETURNS TABLE(username text, password text)
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO ''
    AS $_$
  BEGIN
      RAISE DEBUG 'PgBouncer auth request: %', p_usename;

      RETURN QUERY
      SELECT
          rolname::text,
          CASE WHEN rolvaliduntil < now()
              THEN null
              ELSE rolpassword::text
          END
      FROM pg_authid
      WHERE rolname=$1 and rolcanlogin;
  END;
  $_$;


--
-- Name: apply_rls(jsonb, integer); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer DEFAULT (1024 * 1024)) RETURNS SETOF realtime.wal_rls
    LANGUAGE plpgsql
    AS $$
declare
-- Regclass of the table e.g. public.notes
entity_ regclass = (quote_ident(wal ->> 'schema') || '.' || quote_ident(wal ->> 'table'))::regclass;

-- I, U, D, T: insert, update ...
action realtime.action = (
    case wal ->> 'action'
        when 'I' then 'INSERT'
        when 'U' then 'UPDATE'
        when 'D' then 'DELETE'
        else 'ERROR'
    end
);

-- Is row level security enabled for the table
is_rls_enabled bool = relrowsecurity from pg_class where oid = entity_;

subscriptions realtime.subscription[] = array_agg(subs)
    from
        realtime.subscription subs
    where
        subs.entity = entity_
        -- Filter by action early - only get subscriptions interested in this action
        -- action_filter column can be: '*' (all), 'INSERT', 'UPDATE', or 'DELETE'
        and (subs.action_filter = '*' or subs.action_filter = action::text);

-- Subscription vars
roles regrole[] = array_agg(distinct us.claims_role::text)
    from
        unnest(subscriptions) us;

working_role regrole;
claimed_role regrole;
claims jsonb;

subscription_id uuid;
subscription_has_access bool;
visible_to_subscription_ids uuid[] = '{}';

-- structured info for wal's columns
columns realtime.wal_column[];
-- previous identity values for update/delete
old_columns realtime.wal_column[];

error_record_exceeds_max_size boolean = octet_length(wal::text) > max_record_bytes;

-- Primary jsonb output for record
output jsonb;

begin
perform set_config('role', null, true);

columns =
    array_agg(
        (
            x->>'name',
            x->>'type',
            x->>'typeoid',
            realtime.cast(
                (x->'value') #>> '{}',
                coalesce(
                    (x->>'typeoid')::regtype, -- null when wal2json version <= 2.4
                    (x->>'type')::regtype
                )
            ),
            (pks ->> 'name') is not null,
            true
        )::realtime.wal_column
    )
    from
        jsonb_array_elements(wal -> 'columns') x
        left join jsonb_array_elements(wal -> 'pk') pks
            on (x ->> 'name') = (pks ->> 'name');

old_columns =
    array_agg(
        (
            x->>'name',
            x->>'type',
            x->>'typeoid',
            realtime.cast(
                (x->'value') #>> '{}',
                coalesce(
                    (x->>'typeoid')::regtype, -- null when wal2json version <= 2.4
                    (x->>'type')::regtype
                )
            ),
            (pks ->> 'name') is not null,
            true
        )::realtime.wal_column
    )
    from
        jsonb_array_elements(wal -> 'identity') x
        left join jsonb_array_elements(wal -> 'pk') pks
            on (x ->> 'name') = (pks ->> 'name');

for working_role in select * from unnest(roles) loop

    -- Update `is_selectable` for columns and old_columns
    columns =
        array_agg(
            (
                c.name,
                c.type_name,
                c.type_oid,
                c.value,
                c.is_pkey,
                pg_catalog.has_column_privilege(working_role, entity_, c.name, 'SELECT')
            )::realtime.wal_column
        )
        from
            unnest(columns) c;

    old_columns =
            array_agg(
                (
                    c.name,
                    c.type_name,
                    c.type_oid,
                    c.value,
                    c.is_pkey,
                    pg_catalog.has_column_privilege(working_role, entity_, c.name, 'SELECT')
                )::realtime.wal_column
            )
            from
                unnest(old_columns) c;

    if action <> 'DELETE' and count(1) = 0 from unnest(columns) c where c.is_pkey then
        return next (
            jsonb_build_object(
                'schema', wal ->> 'schema',
                'table', wal ->> 'table',
                'type', action
            ),
            is_rls_enabled,
            -- subscriptions is already filtered by entity
            (select array_agg(s.subscription_id) from unnest(subscriptions) as s where claims_role = working_role),
            array['Error 400: Bad Request, no primary key']
        )::realtime.wal_rls;

    -- The claims role does not have SELECT permission to the primary key of entity
    elsif action <> 'DELETE' and sum(c.is_selectable::int) <> count(1) from unnest(columns) c where c.is_pkey then
        return next (
            jsonb_build_object(
                'schema', wal ->> 'schema',
                'table', wal ->> 'table',
                'type', action
            ),
            is_rls_enabled,
            (select array_agg(s.subscription_id) from unnest(subscriptions) as s where claims_role = working_role),
            array['Error 401: Unauthorized']
        )::realtime.wal_rls;

    else
        output = jsonb_build_object(
            'schema', wal ->> 'schema',
            'table', wal ->> 'table',
            'type', action,
            'commit_timestamp', to_char(
                ((wal ->> 'timestamp')::timestamptz at time zone 'utc'),
                'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'
            ),
            'columns', (
                select
                    jsonb_agg(
                        jsonb_build_object(
                            'name', pa.attname,
                            'type', pt.typname
                        )
                        order by pa.attnum asc
                    )
                from
                    pg_attribute pa
                    join pg_type pt
                        on pa.atttypid = pt.oid
                where
                    attrelid = entity_
                    and attnum > 0
                    and pg_catalog.has_column_privilege(working_role, entity_, pa.attname, 'SELECT')
            )
        )
        -- Add "record" key for insert and update
        || case
            when action in ('INSERT', 'UPDATE') then
                jsonb_build_object(
                    'record',
                    (
                        select
                            jsonb_object_agg(
                                -- if unchanged toast, get column name and value from old record
                                coalesce((c).name, (oc).name),
                                case
                                    when (c).name is null then (oc).value
                                    else (c).value
                                end
                            )
                        from
                            unnest(columns) c
                            full outer join unnest(old_columns) oc
                                on (c).name = (oc).name
                        where
                            coalesce((c).is_selectable, (oc).is_selectable)
                            and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                    )
                )
            else '{}'::jsonb
        end
        -- Add "old_record" key for update and delete
        || case
            when action = 'UPDATE' then
                jsonb_build_object(
                        'old_record',
                        (
                            select jsonb_object_agg((c).name, (c).value)
                            from unnest(old_columns) c
                            where
                                (c).is_selectable
                                and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                        )
                    )
            when action = 'DELETE' then
                jsonb_build_object(
                    'old_record',
                    (
                        select jsonb_object_agg((c).name, (c).value)
                        from unnest(old_columns) c
                        where
                            (c).is_selectable
                            and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                            and ( not is_rls_enabled or (c).is_pkey ) -- if RLS enabled, we can't secure deletes so filter to pkey
                    )
                )
            else '{}'::jsonb
        end;

        -- Create the prepared statement
        if is_rls_enabled and action <> 'DELETE' then
            if (select 1 from pg_prepared_statements where name = 'walrus_rls_stmt' limit 1) > 0 then
                deallocate walrus_rls_stmt;
            end if;
            execute realtime.build_prepared_statement_sql('walrus_rls_stmt', entity_, columns);
        end if;

        visible_to_subscription_ids = '{}';

        for subscription_id, claims in (
                select
                    subs.subscription_id,
                    subs.claims
                from
                    unnest(subscriptions) subs
                where
                    subs.entity = entity_
                    and subs.claims_role = working_role
                    and (
                        realtime.is_visible_through_filters(columns, subs.filters)
                        or (
                          action = 'DELETE'
                          and realtime.is_visible_through_filters(old_columns, subs.filters)
                        )
                    )
        ) loop

            if not is_rls_enabled or action = 'DELETE' then
                visible_to_subscription_ids = visible_to_subscription_ids || subscription_id;
            else
                -- Check if RLS allows the role to see the record
                perform
                    -- Trim leading and trailing quotes from working_role because set_config
                    -- doesn't recognize the role as valid if they are included
                    set_config('role', trim(both '"' from working_role::text), true),
                    set_config('request.jwt.claims', claims::text, true);

                execute 'execute walrus_rls_stmt' into subscription_has_access;

                if subscription_has_access then
                    visible_to_subscription_ids = visible_to_subscription_ids || subscription_id;
                end if;
            end if;
        end loop;

        perform set_config('role', null, true);

        return next (
            output,
            is_rls_enabled,
            visible_to_subscription_ids,
            case
                when error_record_exceeds_max_size then array['Error 413: Payload Too Large']
                else '{}'
            end
        )::realtime.wal_rls;

    end if;
end loop;

perform set_config('role', null, true);
end;
$$;


--
-- Name: broadcast_changes(text, text, text, text, text, record, record, text); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text DEFAULT 'ROW'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    -- Declare a variable to hold the JSONB representation of the row
    row_data jsonb := '{}'::jsonb;
BEGIN
    IF level = 'STATEMENT' THEN
        RAISE EXCEPTION 'function can only be triggered for each row, not for each statement';
    END IF;
    -- Check the operation type and handle accordingly
    IF operation = 'INSERT' OR operation = 'UPDATE' OR operation = 'DELETE' THEN
        row_data := jsonb_build_object('old_record', OLD, 'record', NEW, 'operation', operation, 'table', table_name, 'schema', table_schema);
        PERFORM realtime.send (row_data, event_name, topic_name);
    ELSE
        RAISE EXCEPTION 'Unexpected operation type: %', operation;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Failed to process the row: %', SQLERRM;
END;

$$;


--
-- Name: build_prepared_statement_sql(text, regclass, realtime.wal_column[]); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) RETURNS text
    LANGUAGE sql
    AS $$
      /*
      Builds a sql string that, if executed, creates a prepared statement to
      tests retrive a row from *entity* by its primary key columns.
      Example
          select realtime.build_prepared_statement_sql('public.notes', '{"id"}'::text[], '{"bigint"}'::text[])
      */
          select
      'prepare ' || prepared_statement_name || ' as
          select
              exists(
                  select
                      1
                  from
                      ' || entity || '
                  where
                      ' || string_agg(quote_ident(pkc.name) || '=' || quote_nullable(pkc.value #>> '{}') , ' and ') || '
              )'
          from
              unnest(columns) pkc
          where
              pkc.is_pkey
          group by
              entity
      $$;


--
-- Name: cast(text, regtype); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime."cast"(val text, type_ regtype) RETURNS jsonb
    LANGUAGE plpgsql IMMUTABLE
    AS $$
declare
  res jsonb;
begin
  if type_::text = 'bytea' then
    return to_jsonb(val);
  end if;
  execute format('select to_jsonb(%L::'|| type_::text || ')', val) into res;
  return res;
end
$$;


--
-- Name: check_equality_op(realtime.equality_op, regtype, text, text); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) RETURNS boolean
    LANGUAGE plpgsql IMMUTABLE
    AS $$
      /*
      Casts *val_1* and *val_2* as type *type_* and check the *op* condition for truthiness
      */
      declare
          op_symbol text = (
              case
                  when op = 'eq' then '='
                  when op = 'neq' then '!='
                  when op = 'lt' then '<'
                  when op = 'lte' then '<='
                  when op = 'gt' then '>'
                  when op = 'gte' then '>='
                  when op = 'in' then '= any'
                  else 'UNKNOWN OP'
              end
          );
          res boolean;
      begin
          execute format(
              'select %L::'|| type_::text || ' ' || op_symbol
              || ' ( %L::'
              || (
                  case
                      when op = 'in' then type_::text || '[]'
                      else type_::text end
              )
              || ')', val_1, val_2) into res;
          return res;
      end;
      $$;


--
-- Name: is_visible_through_filters(realtime.wal_column[], realtime.user_defined_filter[]); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
    /*
    Should the record be visible (true) or filtered out (false) after *filters* are applied
    */
        select
            -- Default to allowed when no filters present
            $2 is null -- no filters. this should not happen because subscriptions has a default
            or array_length($2, 1) is null -- array length of an empty array is null
            or bool_and(
                coalesce(
                    realtime.check_equality_op(
                        op:=f.op,
                        type_:=coalesce(
                            col.type_oid::regtype, -- null when wal2json version <= 2.4
                            col.type_name::regtype
                        ),
                        -- cast jsonb to text
                        val_1:=col.value #>> '{}',
                        val_2:=f.value
                    ),
                    false -- if null, filter does not match
                )
            )
        from
            unnest(filters) f
            join unnest(columns) col
                on f.column_name = col.name;
    $_$;


--
-- Name: list_changes(name, name, integer, integer); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) RETURNS SETOF realtime.wal_rls
    LANGUAGE sql
    SET log_min_messages TO 'fatal'
    AS $$
      with pub as (
        select
          concat_ws(
            ',',
            case when bool_or(pubinsert) then 'insert' else null end,
            case when bool_or(pubupdate) then 'update' else null end,
            case when bool_or(pubdelete) then 'delete' else null end
          ) as w2j_actions,
          coalesce(
            string_agg(
              realtime.quote_wal2json(format('%I.%I', schemaname, tablename)::regclass),
              ','
            ) filter (where ppt.tablename is not null and ppt.tablename not like '% %'),
            ''
          ) w2j_add_tables
        from
          pg_publication pp
          left join pg_publication_tables ppt
            on pp.pubname = ppt.pubname
        where
          pp.pubname = publication
        group by
          pp.pubname
        limit 1
      ),
      w2j as (
        select
          x.*, pub.w2j_add_tables
        from
          pub,
          pg_logical_slot_get_changes(
            slot_name, null, max_changes,
            'include-pk', 'true',
            'include-transaction', 'false',
            'include-timestamp', 'true',
            'include-type-oids', 'true',
            'format-version', '2',
            'actions', pub.w2j_actions,
            'add-tables', pub.w2j_add_tables
          ) x
      )
      select
        xyz.wal,
        xyz.is_rls_enabled,
        xyz.subscription_ids,
        xyz.errors
      from
        w2j,
        realtime.apply_rls(
          wal := w2j.data::jsonb,
          max_record_bytes := max_record_bytes
        ) xyz(wal, is_rls_enabled, subscription_ids, errors)
      where
        w2j.w2j_add_tables <> ''
        and xyz.subscription_ids[1] is not null
    $$;


--
-- Name: quote_wal2json(regclass); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.quote_wal2json(entity regclass) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $$
      select
        (
          select string_agg('' || ch,'')
          from unnest(string_to_array(nsp.nspname::text, null)) with ordinality x(ch, idx)
          where
            not (x.idx = 1 and x.ch = '"')
            and not (
              x.idx = array_length(string_to_array(nsp.nspname::text, null), 1)
              and x.ch = '"'
            )
        )
        || '.'
        || (
          select string_agg('' || ch,'')
          from unnest(string_to_array(pc.relname::text, null)) with ordinality x(ch, idx)
          where
            not (x.idx = 1 and x.ch = '"')
            and not (
              x.idx = array_length(string_to_array(nsp.nspname::text, null), 1)
              and x.ch = '"'
            )
          )
      from
        pg_class pc
        join pg_namespace nsp
          on pc.relnamespace = nsp.oid
      where
        pc.oid = entity
    $$;


--
-- Name: send(jsonb, text, text, boolean); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.send(payload jsonb, event text, topic text, private boolean DEFAULT true) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
  generated_id uuid;
  final_payload jsonb;
BEGIN
  BEGIN
    -- Generate a new UUID for the id
    generated_id := gen_random_uuid();

    -- Check if payload has an 'id' key, if not, add the generated UUID
    IF payload ? 'id' THEN
      final_payload := payload;
    ELSE
      final_payload := jsonb_set(payload, '{id}', to_jsonb(generated_id));
    END IF;

    -- Set the topic configuration
    EXECUTE format('SET LOCAL realtime.topic TO %L', topic);

    -- Attempt to insert the message
    INSERT INTO realtime.messages (id, payload, event, topic, private, extension)
    VALUES (generated_id, final_payload, event, topic, private, 'broadcast');
  EXCEPTION
    WHEN OTHERS THEN
      -- Capture and notify the error
      RAISE WARNING 'ErrorSendingBroadcastMessage: %', SQLERRM;
  END;
END;
$$;


--
-- Name: subscription_check_filters(); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.subscription_check_filters() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    /*
    Validates that the user defined filters for a subscription:
    - refer to valid columns that the claimed role may access
    - values are coercable to the correct column type
    */
    declare
        col_names text[] = coalesce(
                array_agg(c.column_name order by c.ordinal_position),
                '{}'::text[]
            )
            from
                information_schema.columns c
            where
                format('%I.%I', c.table_schema, c.table_name)::regclass = new.entity
                and pg_catalog.has_column_privilege(
                    (new.claims ->> 'role'),
                    format('%I.%I', c.table_schema, c.table_name)::regclass,
                    c.column_name,
                    'SELECT'
                );
        filter realtime.user_defined_filter;
        col_type regtype;

        in_val jsonb;
    begin
        for filter in select * from unnest(new.filters) loop
            -- Filtered column is valid
            if not filter.column_name = any(col_names) then
                raise exception 'invalid column for filter %', filter.column_name;
            end if;

            -- Type is sanitized and safe for string interpolation
            col_type = (
                select atttypid::regtype
                from pg_catalog.pg_attribute
                where attrelid = new.entity
                      and attname = filter.column_name
            );
            if col_type is null then
                raise exception 'failed to lookup type for column %', filter.column_name;
            end if;

            -- Set maximum number of entries for in filter
            if filter.op = 'in'::realtime.equality_op then
                in_val = realtime.cast(filter.value, (col_type::text || '[]')::regtype);
                if coalesce(jsonb_array_length(in_val), 0) > 100 then
                    raise exception 'too many values for `in` filter. Maximum 100';
                end if;
            else
                -- raises an exception if value is not coercable to type
                perform realtime.cast(filter.value, col_type);
            end if;

        end loop;

        -- Apply consistent order to filters so the unique constraint on
        -- (subscription_id, entity, filters) can't be tricked by a different filter order
        new.filters = coalesce(
            array_agg(f order by f.column_name, f.op, f.value),
            '{}'
        ) from unnest(new.filters) f;

        return new;
    end;
    $$;


--
-- Name: to_regrole(text); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.to_regrole(role_name text) RETURNS regrole
    LANGUAGE sql IMMUTABLE
    AS $$ select role_name::regrole $$;


--
-- Name: topic(); Type: FUNCTION; Schema: realtime; Owner: -
--

CREATE FUNCTION realtime.topic() RETURNS text
    LANGUAGE sql STABLE
    AS $$
select nullif(current_setting('realtime.topic', true), '')::text;
$$;


--
-- Name: can_insert_object(text, text, uuid, jsonb); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.can_insert_object(bucketid text, name text, owner uuid, metadata jsonb) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
  INSERT INTO "storage"."objects" ("bucket_id", "name", "owner", "metadata") VALUES (bucketid, name, owner, metadata);
  -- hack to rollback the successful insert
  RAISE sqlstate 'PT200' using
  message = 'ROLLBACK',
  detail = 'rollback successful insert';
END
$$;


--
-- Name: enforce_bucket_name_length(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.enforce_bucket_name_length() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
begin
    if length(new.name) > 100 then
        raise exception 'bucket name "%" is too long (% characters). Max is 100.', new.name, length(new.name);
    end if;
    return new;
end;
$$;


--
-- Name: extension(text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.extension(name text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
_filename text;
BEGIN
	select string_to_array(name, '/') into _parts;
	select _parts[array_length(_parts,1)] into _filename;
	-- @todo return the last part instead of 2
	return reverse(split_part(reverse(_filename), '.', 1));
END
$$;


--
-- Name: filename(text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.filename(name text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
BEGIN
	select string_to_array(name, '/') into _parts;
	return _parts[array_length(_parts,1)];
END
$$;


--
-- Name: foldername(text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.foldername(name text) RETURNS text[]
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
BEGIN
	select string_to_array(name, '/') into _parts;
	return _parts[1:array_length(_parts,1)-1];
END
$$;


--
-- Name: get_common_prefix(text, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.get_common_prefix(p_key text, p_prefix text, p_delimiter text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
SELECT CASE
    WHEN position(p_delimiter IN substring(p_key FROM length(p_prefix) + 1)) > 0
    THEN left(p_key, length(p_prefix) + position(p_delimiter IN substring(p_key FROM length(p_prefix) + 1)))
    ELSE NULL
END;
$$;


--
-- Name: get_size_by_bucket(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.get_size_by_bucket() RETURNS TABLE(size bigint, bucket_id text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    return query
        select sum((metadata->>'size')::int) as size, obj.bucket_id
        from "storage".objects as obj
        group by obj.bucket_id;
END
$$;


--
-- Name: list_multipart_uploads_with_delimiter(text, text, text, integer, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.list_multipart_uploads_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer DEFAULT 100, next_key_token text DEFAULT ''::text, next_upload_token text DEFAULT ''::text) RETURNS TABLE(key text, id text, created_at timestamp with time zone)
    LANGUAGE plpgsql
    AS $_$
BEGIN
    RETURN QUERY EXECUTE
        'SELECT DISTINCT ON(key COLLATE "C") * from (
            SELECT
                CASE
                    WHEN position($2 IN substring(key from length($1) + 1)) > 0 THEN
                        substring(key from 1 for length($1) + position($2 IN substring(key from length($1) + 1)))
                    ELSE
                        key
                END AS key, id, created_at
            FROM
                storage.s3_multipart_uploads
            WHERE
                bucket_id = $5 AND
                key ILIKE $1 || ''%'' AND
                CASE
                    WHEN $4 != '''' AND $6 = '''' THEN
                        CASE
                            WHEN position($2 IN substring(key from length($1) + 1)) > 0 THEN
                                substring(key from 1 for length($1) + position($2 IN substring(key from length($1) + 1))) COLLATE "C" > $4
                            ELSE
                                key COLLATE "C" > $4
                            END
                    ELSE
                        true
                END AND
                CASE
                    WHEN $6 != '''' THEN
                        id COLLATE "C" > $6
                    ELSE
                        true
                    END
            ORDER BY
                key COLLATE "C" ASC, created_at ASC) as e order by key COLLATE "C" LIMIT $3'
        USING prefix_param, delimiter_param, max_keys, next_key_token, bucket_id, next_upload_token;
END;
$_$;


--
-- Name: list_objects_with_delimiter(text, text, text, integer, text, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.list_objects_with_delimiter(_bucket_id text, prefix_param text, delimiter_param text, max_keys integer DEFAULT 100, start_after text DEFAULT ''::text, next_token text DEFAULT ''::text, sort_order text DEFAULT 'asc'::text) RETURNS TABLE(name text, id uuid, metadata jsonb, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone)
    LANGUAGE plpgsql STABLE
    AS $_$
DECLARE
    v_peek_name TEXT;
    v_current RECORD;
    v_common_prefix TEXT;

    -- Configuration
    v_is_asc BOOLEAN;
    v_prefix TEXT;
    v_start TEXT;
    v_upper_bound TEXT;
    v_file_batch_size INT;

    -- Seek state
    v_next_seek TEXT;
    v_count INT := 0;

    -- Dynamic SQL for batch query only
    v_batch_query TEXT;

BEGIN
    -- ========================================================================
    -- INITIALIZATION
    -- ========================================================================
    v_is_asc := lower(coalesce(sort_order, 'asc')) = 'asc';
    v_prefix := coalesce(prefix_param, '');
    v_start := CASE WHEN coalesce(next_token, '') <> '' THEN next_token ELSE coalesce(start_after, '') END;
    v_file_batch_size := LEAST(GREATEST(max_keys * 2, 100), 1000);

    -- Calculate upper bound for prefix filtering (bytewise, using COLLATE "C")
    IF v_prefix = '' THEN
        v_upper_bound := NULL;
    ELSIF right(v_prefix, 1) = delimiter_param THEN
        v_upper_bound := left(v_prefix, -1) || chr(ascii(delimiter_param) + 1);
    ELSE
        v_upper_bound := left(v_prefix, -1) || chr(ascii(right(v_prefix, 1)) + 1);
    END IF;

    -- Build batch query (dynamic SQL - called infrequently, amortized over many rows)
    IF v_is_asc THEN
        IF v_upper_bound IS NOT NULL THEN
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND o.name COLLATE "C" >= $2 ' ||
                'AND o.name COLLATE "C" < $3 ORDER BY o.name COLLATE "C" ASC LIMIT $4';
        ELSE
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND o.name COLLATE "C" >= $2 ' ||
                'ORDER BY o.name COLLATE "C" ASC LIMIT $4';
        END IF;
    ELSE
        IF v_upper_bound IS NOT NULL THEN
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND o.name COLLATE "C" < $2 ' ||
                'AND o.name COLLATE "C" >= $3 ORDER BY o.name COLLATE "C" DESC LIMIT $4';
        ELSE
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND o.name COLLATE "C" < $2 ' ||
                'ORDER BY o.name COLLATE "C" DESC LIMIT $4';
        END IF;
    END IF;

    -- ========================================================================
    -- SEEK INITIALIZATION: Determine starting position
    -- ========================================================================
    IF v_start = '' THEN
        IF v_is_asc THEN
            v_next_seek := v_prefix;
        ELSE
            -- DESC without cursor: find the last item in range
            IF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_next_seek FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" >= v_prefix AND o.name COLLATE "C" < v_upper_bound
                ORDER BY o.name COLLATE "C" DESC LIMIT 1;
            ELSIF v_prefix <> '' THEN
                SELECT o.name INTO v_next_seek FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" >= v_prefix
                ORDER BY o.name COLLATE "C" DESC LIMIT 1;
            ELSE
                SELECT o.name INTO v_next_seek FROM storage.objects o
                WHERE o.bucket_id = _bucket_id
                ORDER BY o.name COLLATE "C" DESC LIMIT 1;
            END IF;

            IF v_next_seek IS NOT NULL THEN
                v_next_seek := v_next_seek || delimiter_param;
            ELSE
                RETURN;
            END IF;
        END IF;
    ELSE
        -- Cursor provided: determine if it refers to a folder or leaf
        IF EXISTS (
            SELECT 1 FROM storage.objects o
            WHERE o.bucket_id = _bucket_id
              AND o.name COLLATE "C" LIKE v_start || delimiter_param || '%'
            LIMIT 1
        ) THEN
            -- Cursor refers to a folder
            IF v_is_asc THEN
                v_next_seek := v_start || chr(ascii(delimiter_param) + 1);
            ELSE
                v_next_seek := v_start || delimiter_param;
            END IF;
        ELSE
            -- Cursor refers to a leaf object
            IF v_is_asc THEN
                v_next_seek := v_start || delimiter_param;
            ELSE
                v_next_seek := v_start;
            END IF;
        END IF;
    END IF;

    -- ========================================================================
    -- MAIN LOOP: Hybrid peek-then-batch algorithm
    -- Uses STATIC SQL for peek (hot path) and DYNAMIC SQL for batch
    -- ========================================================================
    LOOP
        EXIT WHEN v_count >= max_keys;

        -- STEP 1: PEEK using STATIC SQL (plan cached, very fast)
        IF v_is_asc THEN
            IF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" >= v_next_seek AND o.name COLLATE "C" < v_upper_bound
                ORDER BY o.name COLLATE "C" ASC LIMIT 1;
            ELSE
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" >= v_next_seek
                ORDER BY o.name COLLATE "C" ASC LIMIT 1;
            END IF;
        ELSE
            IF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" < v_next_seek AND o.name COLLATE "C" >= v_prefix
                ORDER BY o.name COLLATE "C" DESC LIMIT 1;
            ELSIF v_prefix <> '' THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" < v_next_seek AND o.name COLLATE "C" >= v_prefix
                ORDER BY o.name COLLATE "C" DESC LIMIT 1;
            ELSE
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" < v_next_seek
                ORDER BY o.name COLLATE "C" DESC LIMIT 1;
            END IF;
        END IF;

        EXIT WHEN v_peek_name IS NULL;

        -- STEP 2: Check if this is a FOLDER or FILE
        v_common_prefix := storage.get_common_prefix(v_peek_name, v_prefix, delimiter_param);

        IF v_common_prefix IS NOT NULL THEN
            -- FOLDER: Emit and skip to next folder (no heap access needed)
            name := rtrim(v_common_prefix, delimiter_param);
            id := NULL;
            updated_at := NULL;
            created_at := NULL;
            last_accessed_at := NULL;
            metadata := NULL;
            RETURN NEXT;
            v_count := v_count + 1;

            -- Advance seek past the folder range
            IF v_is_asc THEN
                v_next_seek := left(v_common_prefix, -1) || chr(ascii(delimiter_param) + 1);
            ELSE
                v_next_seek := v_common_prefix;
            END IF;
        ELSE
            -- FILE: Batch fetch using DYNAMIC SQL (overhead amortized over many rows)
            -- For ASC: upper_bound is the exclusive upper limit (< condition)
            -- For DESC: prefix is the inclusive lower limit (>= condition)
            FOR v_current IN EXECUTE v_batch_query USING _bucket_id, v_next_seek,
                CASE WHEN v_is_asc THEN COALESCE(v_upper_bound, v_prefix) ELSE v_prefix END, v_file_batch_size
            LOOP
                v_common_prefix := storage.get_common_prefix(v_current.name, v_prefix, delimiter_param);

                IF v_common_prefix IS NOT NULL THEN
                    -- Hit a folder: exit batch, let peek handle it
                    v_next_seek := v_current.name;
                    EXIT;
                END IF;

                -- Emit file
                name := v_current.name;
                id := v_current.id;
                updated_at := v_current.updated_at;
                created_at := v_current.created_at;
                last_accessed_at := v_current.last_accessed_at;
                metadata := v_current.metadata;
                RETURN NEXT;
                v_count := v_count + 1;

                -- Advance seek past this file
                IF v_is_asc THEN
                    v_next_seek := v_current.name || delimiter_param;
                ELSE
                    v_next_seek := v_current.name;
                END IF;

                EXIT WHEN v_count >= max_keys;
            END LOOP;
        END IF;
    END LOOP;
END;
$_$;


--
-- Name: operation(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.operation() RETURNS text
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    RETURN current_setting('storage.operation', true);
END;
$$;


--
-- Name: protect_delete(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.protect_delete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Check if storage.allow_delete_query is set to 'true'
    IF COALESCE(current_setting('storage.allow_delete_query', true), 'false') != 'true' THEN
        RAISE EXCEPTION 'Direct deletion from storage tables is not allowed. Use the Storage API instead.'
            USING HINT = 'This prevents accidental data loss from orphaned objects.',
                  ERRCODE = '42501';
    END IF;
    RETURN NULL;
END;
$$;


--
-- Name: search(text, text, integer, integer, integer, text, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.search(prefix text, bucketname text, limits integer DEFAULT 100, levels integer DEFAULT 1, offsets integer DEFAULT 0, search text DEFAULT ''::text, sortcolumn text DEFAULT 'name'::text, sortorder text DEFAULT 'asc'::text) RETURNS TABLE(name text, id uuid, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone, metadata jsonb)
    LANGUAGE plpgsql STABLE
    AS $_$
DECLARE
    v_peek_name TEXT;
    v_current RECORD;
    v_common_prefix TEXT;
    v_delimiter CONSTANT TEXT := '/';

    -- Configuration
    v_limit INT;
    v_prefix TEXT;
    v_prefix_lower TEXT;
    v_is_asc BOOLEAN;
    v_order_by TEXT;
    v_sort_order TEXT;
    v_upper_bound TEXT;
    v_file_batch_size INT;

    -- Dynamic SQL for batch query only
    v_batch_query TEXT;

    -- Seek state
    v_next_seek TEXT;
    v_count INT := 0;
    v_skipped INT := 0;
BEGIN
    -- ========================================================================
    -- INITIALIZATION
    -- ========================================================================
    v_limit := LEAST(coalesce(limits, 100), 1500);
    v_prefix := coalesce(prefix, '') || coalesce(search, '');
    v_prefix_lower := lower(v_prefix);
    v_is_asc := lower(coalesce(sortorder, 'asc')) = 'asc';
    v_file_batch_size := LEAST(GREATEST(v_limit * 2, 100), 1000);

    -- Validate sort column
    CASE lower(coalesce(sortcolumn, 'name'))
        WHEN 'name' THEN v_order_by := 'name';
        WHEN 'updated_at' THEN v_order_by := 'updated_at';
        WHEN 'created_at' THEN v_order_by := 'created_at';
        WHEN 'last_accessed_at' THEN v_order_by := 'last_accessed_at';
        ELSE v_order_by := 'name';
    END CASE;

    v_sort_order := CASE WHEN v_is_asc THEN 'asc' ELSE 'desc' END;

    -- ========================================================================
    -- NON-NAME SORTING: Use path_tokens approach (unchanged)
    -- ========================================================================
    IF v_order_by != 'name' THEN
        RETURN QUERY EXECUTE format(
            $sql$
            WITH folders AS (
                SELECT path_tokens[$1] AS folder
                FROM storage.objects
                WHERE objects.name ILIKE $2 || '%%'
                  AND bucket_id = $3
                  AND array_length(objects.path_tokens, 1) <> $1
                GROUP BY folder
                ORDER BY folder %s
            )
            (SELECT folder AS "name",
                   NULL::uuid AS id,
                   NULL::timestamptz AS updated_at,
                   NULL::timestamptz AS created_at,
                   NULL::timestamptz AS last_accessed_at,
                   NULL::jsonb AS metadata FROM folders)
            UNION ALL
            (SELECT path_tokens[$1] AS "name",
                   id, updated_at, created_at, last_accessed_at, metadata
             FROM storage.objects
             WHERE objects.name ILIKE $2 || '%%'
               AND bucket_id = $3
               AND array_length(objects.path_tokens, 1) = $1
             ORDER BY %I %s)
            LIMIT $4 OFFSET $5
            $sql$, v_sort_order, v_order_by, v_sort_order
        ) USING levels, v_prefix, bucketname, v_limit, offsets;
        RETURN;
    END IF;

    -- ========================================================================
    -- NAME SORTING: Hybrid skip-scan with batch optimization
    -- ========================================================================

    -- Calculate upper bound for prefix filtering
    IF v_prefix_lower = '' THEN
        v_upper_bound := NULL;
    ELSIF right(v_prefix_lower, 1) = v_delimiter THEN
        v_upper_bound := left(v_prefix_lower, -1) || chr(ascii(v_delimiter) + 1);
    ELSE
        v_upper_bound := left(v_prefix_lower, -1) || chr(ascii(right(v_prefix_lower, 1)) + 1);
    END IF;

    -- Build batch query (dynamic SQL - called infrequently, amortized over many rows)
    IF v_is_asc THEN
        IF v_upper_bound IS NOT NULL THEN
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" >= $2 ' ||
                'AND lower(o.name) COLLATE "C" < $3 ORDER BY lower(o.name) COLLATE "C" ASC LIMIT $4';
        ELSE
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" >= $2 ' ||
                'ORDER BY lower(o.name) COLLATE "C" ASC LIMIT $4';
        END IF;
    ELSE
        IF v_upper_bound IS NOT NULL THEN
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" < $2 ' ||
                'AND lower(o.name) COLLATE "C" >= $3 ORDER BY lower(o.name) COLLATE "C" DESC LIMIT $4';
        ELSE
            v_batch_query := 'SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata ' ||
                'FROM storage.objects o WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" < $2 ' ||
                'ORDER BY lower(o.name) COLLATE "C" DESC LIMIT $4';
        END IF;
    END IF;

    -- Initialize seek position
    IF v_is_asc THEN
        v_next_seek := v_prefix_lower;
    ELSE
        -- DESC: find the last item in range first (static SQL)
        IF v_upper_bound IS NOT NULL THEN
            SELECT o.name INTO v_peek_name FROM storage.objects o
            WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" >= v_prefix_lower AND lower(o.name) COLLATE "C" < v_upper_bound
            ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
        ELSIF v_prefix_lower <> '' THEN
            SELECT o.name INTO v_peek_name FROM storage.objects o
            WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" >= v_prefix_lower
            ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
        ELSE
            SELECT o.name INTO v_peek_name FROM storage.objects o
            WHERE o.bucket_id = bucketname
            ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
        END IF;

        IF v_peek_name IS NOT NULL THEN
            v_next_seek := lower(v_peek_name) || v_delimiter;
        ELSE
            RETURN;
        END IF;
    END IF;

    -- ========================================================================
    -- MAIN LOOP: Hybrid peek-then-batch algorithm
    -- Uses STATIC SQL for peek (hot path) and DYNAMIC SQL for batch
    -- ========================================================================
    LOOP
        EXIT WHEN v_count >= v_limit;

        -- STEP 1: PEEK using STATIC SQL (plan cached, very fast)
        IF v_is_asc THEN
            IF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" >= v_next_seek AND lower(o.name) COLLATE "C" < v_upper_bound
                ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1;
            ELSE
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" >= v_next_seek
                ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1;
            END IF;
        ELSE
            IF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" < v_next_seek AND lower(o.name) COLLATE "C" >= v_prefix_lower
                ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
            ELSIF v_prefix_lower <> '' THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" < v_next_seek AND lower(o.name) COLLATE "C" >= v_prefix_lower
                ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
            ELSE
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" < v_next_seek
                ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
            END IF;
        END IF;

        EXIT WHEN v_peek_name IS NULL;

        -- STEP 2: Check if this is a FOLDER or FILE
        v_common_prefix := storage.get_common_prefix(lower(v_peek_name), v_prefix_lower, v_delimiter);

        IF v_common_prefix IS NOT NULL THEN
            -- FOLDER: Handle offset, emit if needed, skip to next folder
            IF v_skipped < offsets THEN
                v_skipped := v_skipped + 1;
            ELSE
                name := split_part(rtrim(storage.get_common_prefix(v_peek_name, v_prefix, v_delimiter), v_delimiter), v_delimiter, levels);
                id := NULL;
                updated_at := NULL;
                created_at := NULL;
                last_accessed_at := NULL;
                metadata := NULL;
                RETURN NEXT;
                v_count := v_count + 1;
            END IF;

            -- Advance seek past the folder range
            IF v_is_asc THEN
                v_next_seek := lower(left(v_common_prefix, -1)) || chr(ascii(v_delimiter) + 1);
            ELSE
                v_next_seek := lower(v_common_prefix);
            END IF;
        ELSE
            -- FILE: Batch fetch using DYNAMIC SQL (overhead amortized over many rows)
            -- For ASC: upper_bound is the exclusive upper limit (< condition)
            -- For DESC: prefix_lower is the inclusive lower limit (>= condition)
            FOR v_current IN EXECUTE v_batch_query
                USING bucketname, v_next_seek,
                    CASE WHEN v_is_asc THEN COALESCE(v_upper_bound, v_prefix_lower) ELSE v_prefix_lower END, v_file_batch_size
            LOOP
                v_common_prefix := storage.get_common_prefix(lower(v_current.name), v_prefix_lower, v_delimiter);

                IF v_common_prefix IS NOT NULL THEN
                    -- Hit a folder: exit batch, let peek handle it
                    v_next_seek := lower(v_current.name);
                    EXIT;
                END IF;

                -- Handle offset skipping
                IF v_skipped < offsets THEN
                    v_skipped := v_skipped + 1;
                ELSE
                    -- Emit file
                    name := split_part(v_current.name, v_delimiter, levels);
                    id := v_current.id;
                    updated_at := v_current.updated_at;
                    created_at := v_current.created_at;
                    last_accessed_at := v_current.last_accessed_at;
                    metadata := v_current.metadata;
                    RETURN NEXT;
                    v_count := v_count + 1;
                END IF;

                -- Advance seek past this file
                IF v_is_asc THEN
                    v_next_seek := lower(v_current.name) || v_delimiter;
                ELSE
                    v_next_seek := lower(v_current.name);
                END IF;

                EXIT WHEN v_count >= v_limit;
            END LOOP;
        END IF;
    END LOOP;
END;
$_$;


--
-- Name: search_by_timestamp(text, text, integer, integer, text, text, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.search_by_timestamp(p_prefix text, p_bucket_id text, p_limit integer, p_level integer, p_start_after text, p_sort_order text, p_sort_column text, p_sort_column_after text) RETURNS TABLE(key text, name text, id uuid, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone, metadata jsonb)
    LANGUAGE plpgsql STABLE
    AS $_$
DECLARE
    v_cursor_op text;
    v_query text;
    v_prefix text;
BEGIN
    v_prefix := coalesce(p_prefix, '');

    IF p_sort_order = 'asc' THEN
        v_cursor_op := '>';
    ELSE
        v_cursor_op := '<';
    END IF;

    v_query := format($sql$
        WITH raw_objects AS (
            SELECT
                o.name AS obj_name,
                o.id AS obj_id,
                o.updated_at AS obj_updated_at,
                o.created_at AS obj_created_at,
                o.last_accessed_at AS obj_last_accessed_at,
                o.metadata AS obj_metadata,
                storage.get_common_prefix(o.name, $1, '/') AS common_prefix
            FROM storage.objects o
            WHERE o.bucket_id = $2
              AND o.name COLLATE "C" LIKE $1 || '%%'
        ),
        -- Aggregate common prefixes (folders)
        -- Both created_at and updated_at use MIN(obj_created_at) to match the old prefixes table behavior
        aggregated_prefixes AS (
            SELECT
                rtrim(common_prefix, '/') AS name,
                NULL::uuid AS id,
                MIN(obj_created_at) AS updated_at,
                MIN(obj_created_at) AS created_at,
                NULL::timestamptz AS last_accessed_at,
                NULL::jsonb AS metadata,
                TRUE AS is_prefix
            FROM raw_objects
            WHERE common_prefix IS NOT NULL
            GROUP BY common_prefix
        ),
        leaf_objects AS (
            SELECT
                obj_name AS name,
                obj_id AS id,
                obj_updated_at AS updated_at,
                obj_created_at AS created_at,
                obj_last_accessed_at AS last_accessed_at,
                obj_metadata AS metadata,
                FALSE AS is_prefix
            FROM raw_objects
            WHERE common_prefix IS NULL
        ),
        combined AS (
            SELECT * FROM aggregated_prefixes
            UNION ALL
            SELECT * FROM leaf_objects
        ),
        filtered AS (
            SELECT *
            FROM combined
            WHERE (
                $5 = ''
                OR ROW(
                    date_trunc('milliseconds', %I),
                    name COLLATE "C"
                ) %s ROW(
                    COALESCE(NULLIF($6, '')::timestamptz, 'epoch'::timestamptz),
                    $5
                )
            )
        )
        SELECT
            split_part(name, '/', $3) AS key,
            name,
            id,
            updated_at,
            created_at,
            last_accessed_at,
            metadata
        FROM filtered
        ORDER BY
            COALESCE(date_trunc('milliseconds', %I), 'epoch'::timestamptz) %s,
            name COLLATE "C" %s
        LIMIT $4
    $sql$,
        p_sort_column,
        v_cursor_op,
        p_sort_column,
        p_sort_order,
        p_sort_order
    );

    RETURN QUERY EXECUTE v_query
    USING v_prefix, p_bucket_id, p_level, p_limit, p_start_after, p_sort_column_after;
END;
$_$;


--
-- Name: search_v2(text, text, integer, integer, text, text, text, text); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.search_v2(prefix text, bucket_name text, limits integer DEFAULT 100, levels integer DEFAULT 1, start_after text DEFAULT ''::text, sort_order text DEFAULT 'asc'::text, sort_column text DEFAULT 'name'::text, sort_column_after text DEFAULT ''::text) RETURNS TABLE(key text, name text, id uuid, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone, metadata jsonb)
    LANGUAGE plpgsql STABLE
    AS $$
DECLARE
    v_sort_col text;
    v_sort_ord text;
    v_limit int;
BEGIN
    -- Cap limit to maximum of 1500 records
    v_limit := LEAST(coalesce(limits, 100), 1500);

    -- Validate and normalize sort_order
    v_sort_ord := lower(coalesce(sort_order, 'asc'));
    IF v_sort_ord NOT IN ('asc', 'desc') THEN
        v_sort_ord := 'asc';
    END IF;

    -- Validate and normalize sort_column
    v_sort_col := lower(coalesce(sort_column, 'name'));
    IF v_sort_col NOT IN ('name', 'updated_at', 'created_at') THEN
        v_sort_col := 'name';
    END IF;

    -- Route to appropriate implementation
    IF v_sort_col = 'name' THEN
        -- Use list_objects_with_delimiter for name sorting (most efficient: O(k * log n))
        RETURN QUERY
        SELECT
            split_part(l.name, '/', levels) AS key,
            l.name AS name,
            l.id,
            l.updated_at,
            l.created_at,
            l.last_accessed_at,
            l.metadata
        FROM storage.list_objects_with_delimiter(
            bucket_name,
            coalesce(prefix, ''),
            '/',
            v_limit,
            start_after,
            '',
            v_sort_ord
        ) l;
    ELSE
        -- Use aggregation approach for timestamp sorting
        -- Not efficient for large datasets but supports correct pagination
        RETURN QUERY SELECT * FROM storage.search_by_timestamp(
            prefix, bucket_name, v_limit, levels, start_after,
            v_sort_ord, v_sort_col, sort_column_after
        );
    END IF;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: storage; Owner: -
--

CREATE FUNCTION storage.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW; 
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_log_entries; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.audit_log_entries (
    instance_id uuid,
    id uuid NOT NULL,
    payload json,
    created_at timestamp with time zone,
    ip_address character varying(64) DEFAULT ''::character varying NOT NULL
);


--
-- Name: TABLE audit_log_entries; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.audit_log_entries IS 'Auth: Audit trail for user actions.';


--
-- Name: custom_oauth_providers; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.custom_oauth_providers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    provider_type text NOT NULL,
    identifier text NOT NULL,
    name text NOT NULL,
    client_id text NOT NULL,
    client_secret text NOT NULL,
    acceptable_client_ids text[] DEFAULT '{}'::text[] NOT NULL,
    scopes text[] DEFAULT '{}'::text[] NOT NULL,
    pkce_enabled boolean DEFAULT true NOT NULL,
    attribute_mapping jsonb DEFAULT '{}'::jsonb NOT NULL,
    authorization_params jsonb DEFAULT '{}'::jsonb NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    email_optional boolean DEFAULT false NOT NULL,
    issuer text,
    discovery_url text,
    skip_nonce_check boolean DEFAULT false NOT NULL,
    cached_discovery jsonb,
    discovery_cached_at timestamp with time zone,
    authorization_url text,
    token_url text,
    userinfo_url text,
    jwks_uri text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT custom_oauth_providers_authorization_url_https CHECK (((authorization_url IS NULL) OR (authorization_url ~~ 'https://%'::text))),
    CONSTRAINT custom_oauth_providers_authorization_url_length CHECK (((authorization_url IS NULL) OR (char_length(authorization_url) <= 2048))),
    CONSTRAINT custom_oauth_providers_client_id_length CHECK (((char_length(client_id) >= 1) AND (char_length(client_id) <= 512))),
    CONSTRAINT custom_oauth_providers_discovery_url_length CHECK (((discovery_url IS NULL) OR (char_length(discovery_url) <= 2048))),
    CONSTRAINT custom_oauth_providers_identifier_format CHECK ((identifier ~ '^[a-z0-9][a-z0-9:-]{0,48}[a-z0-9]$'::text)),
    CONSTRAINT custom_oauth_providers_issuer_length CHECK (((issuer IS NULL) OR ((char_length(issuer) >= 1) AND (char_length(issuer) <= 2048)))),
    CONSTRAINT custom_oauth_providers_jwks_uri_https CHECK (((jwks_uri IS NULL) OR (jwks_uri ~~ 'https://%'::text))),
    CONSTRAINT custom_oauth_providers_jwks_uri_length CHECK (((jwks_uri IS NULL) OR (char_length(jwks_uri) <= 2048))),
    CONSTRAINT custom_oauth_providers_name_length CHECK (((char_length(name) >= 1) AND (char_length(name) <= 100))),
    CONSTRAINT custom_oauth_providers_oauth2_requires_endpoints CHECK (((provider_type <> 'oauth2'::text) OR ((authorization_url IS NOT NULL) AND (token_url IS NOT NULL) AND (userinfo_url IS NOT NULL)))),
    CONSTRAINT custom_oauth_providers_oidc_discovery_url_https CHECK (((provider_type <> 'oidc'::text) OR (discovery_url IS NULL) OR (discovery_url ~~ 'https://%'::text))),
    CONSTRAINT custom_oauth_providers_oidc_issuer_https CHECK (((provider_type <> 'oidc'::text) OR (issuer IS NULL) OR (issuer ~~ 'https://%'::text))),
    CONSTRAINT custom_oauth_providers_oidc_requires_issuer CHECK (((provider_type <> 'oidc'::text) OR (issuer IS NOT NULL))),
    CONSTRAINT custom_oauth_providers_provider_type_check CHECK ((provider_type = ANY (ARRAY['oauth2'::text, 'oidc'::text]))),
    CONSTRAINT custom_oauth_providers_token_url_https CHECK (((token_url IS NULL) OR (token_url ~~ 'https://%'::text))),
    CONSTRAINT custom_oauth_providers_token_url_length CHECK (((token_url IS NULL) OR (char_length(token_url) <= 2048))),
    CONSTRAINT custom_oauth_providers_userinfo_url_https CHECK (((userinfo_url IS NULL) OR (userinfo_url ~~ 'https://%'::text))),
    CONSTRAINT custom_oauth_providers_userinfo_url_length CHECK (((userinfo_url IS NULL) OR (char_length(userinfo_url) <= 2048)))
);


--
-- Name: flow_state; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.flow_state (
    id uuid NOT NULL,
    user_id uuid,
    auth_code text,
    code_challenge_method auth.code_challenge_method,
    code_challenge text,
    provider_type text NOT NULL,
    provider_access_token text,
    provider_refresh_token text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    authentication_method text NOT NULL,
    auth_code_issued_at timestamp with time zone,
    invite_token text,
    referrer text,
    oauth_client_state_id uuid,
    linking_target_id uuid,
    email_optional boolean DEFAULT false NOT NULL
);


--
-- Name: TABLE flow_state; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.flow_state IS 'Stores metadata for all OAuth/SSO login flows';


--
-- Name: identities; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.identities (
    provider_id text NOT NULL,
    user_id uuid NOT NULL,
    identity_data jsonb NOT NULL,
    provider text NOT NULL,
    last_sign_in_at timestamp with time zone,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    email text GENERATED ALWAYS AS (lower((identity_data ->> 'email'::text))) STORED,
    id uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: TABLE identities; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.identities IS 'Auth: Stores identities associated to a user.';


--
-- Name: COLUMN identities.email; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.identities.email IS 'Auth: Email is a generated column that references the optional email property in the identity_data';


--
-- Name: instances; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.instances (
    id uuid NOT NULL,
    uuid uuid,
    raw_base_config text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: TABLE instances; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.instances IS 'Auth: Manages users across multiple sites.';


--
-- Name: mfa_amr_claims; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.mfa_amr_claims (
    session_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    authentication_method text NOT NULL,
    id uuid NOT NULL
);


--
-- Name: TABLE mfa_amr_claims; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.mfa_amr_claims IS 'auth: stores authenticator method reference claims for multi factor authentication';


--
-- Name: mfa_challenges; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.mfa_challenges (
    id uuid NOT NULL,
    factor_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    verified_at timestamp with time zone,
    ip_address inet NOT NULL,
    otp_code text,
    web_authn_session_data jsonb
);


--
-- Name: TABLE mfa_challenges; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.mfa_challenges IS 'auth: stores metadata about challenge requests made';


--
-- Name: mfa_factors; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.mfa_factors (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    friendly_name text,
    factor_type auth.factor_type NOT NULL,
    status auth.factor_status NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    secret text,
    phone text,
    last_challenged_at timestamp with time zone,
    web_authn_credential jsonb,
    web_authn_aaguid uuid,
    last_webauthn_challenge_data jsonb
);


--
-- Name: TABLE mfa_factors; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.mfa_factors IS 'auth: stores metadata about factors';


--
-- Name: COLUMN mfa_factors.last_webauthn_challenge_data; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.mfa_factors.last_webauthn_challenge_data IS 'Stores the latest WebAuthn challenge data including attestation/assertion for customer verification';


--
-- Name: oauth_authorizations; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.oauth_authorizations (
    id uuid NOT NULL,
    authorization_id text NOT NULL,
    client_id uuid NOT NULL,
    user_id uuid,
    redirect_uri text NOT NULL,
    scope text NOT NULL,
    state text,
    resource text,
    code_challenge text,
    code_challenge_method auth.code_challenge_method,
    response_type auth.oauth_response_type DEFAULT 'code'::auth.oauth_response_type NOT NULL,
    status auth.oauth_authorization_status DEFAULT 'pending'::auth.oauth_authorization_status NOT NULL,
    authorization_code text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone DEFAULT (now() + '00:03:00'::interval) NOT NULL,
    approved_at timestamp with time zone,
    nonce text,
    CONSTRAINT oauth_authorizations_authorization_code_length CHECK ((char_length(authorization_code) <= 255)),
    CONSTRAINT oauth_authorizations_code_challenge_length CHECK ((char_length(code_challenge) <= 128)),
    CONSTRAINT oauth_authorizations_expires_at_future CHECK ((expires_at > created_at)),
    CONSTRAINT oauth_authorizations_nonce_length CHECK ((char_length(nonce) <= 255)),
    CONSTRAINT oauth_authorizations_redirect_uri_length CHECK ((char_length(redirect_uri) <= 2048)),
    CONSTRAINT oauth_authorizations_resource_length CHECK ((char_length(resource) <= 2048)),
    CONSTRAINT oauth_authorizations_scope_length CHECK ((char_length(scope) <= 4096)),
    CONSTRAINT oauth_authorizations_state_length CHECK ((char_length(state) <= 4096))
);


--
-- Name: oauth_client_states; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.oauth_client_states (
    id uuid NOT NULL,
    provider_type text NOT NULL,
    code_verifier text,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: TABLE oauth_client_states; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.oauth_client_states IS 'Stores OAuth states for third-party provider authentication flows where Supabase acts as the OAuth client.';


--
-- Name: oauth_clients; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.oauth_clients (
    id uuid NOT NULL,
    client_secret_hash text,
    registration_type auth.oauth_registration_type NOT NULL,
    redirect_uris text NOT NULL,
    grant_types text NOT NULL,
    client_name text,
    client_uri text,
    logo_uri text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    client_type auth.oauth_client_type DEFAULT 'confidential'::auth.oauth_client_type NOT NULL,
    token_endpoint_auth_method text NOT NULL,
    CONSTRAINT oauth_clients_client_name_length CHECK ((char_length(client_name) <= 1024)),
    CONSTRAINT oauth_clients_client_uri_length CHECK ((char_length(client_uri) <= 2048)),
    CONSTRAINT oauth_clients_logo_uri_length CHECK ((char_length(logo_uri) <= 2048)),
    CONSTRAINT oauth_clients_token_endpoint_auth_method_check CHECK ((token_endpoint_auth_method = ANY (ARRAY['client_secret_basic'::text, 'client_secret_post'::text, 'none'::text])))
);


--
-- Name: oauth_consents; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.oauth_consents (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    client_id uuid NOT NULL,
    scopes text NOT NULL,
    granted_at timestamp with time zone DEFAULT now() NOT NULL,
    revoked_at timestamp with time zone,
    CONSTRAINT oauth_consents_revoked_after_granted CHECK (((revoked_at IS NULL) OR (revoked_at >= granted_at))),
    CONSTRAINT oauth_consents_scopes_length CHECK ((char_length(scopes) <= 2048)),
    CONSTRAINT oauth_consents_scopes_not_empty CHECK ((char_length(TRIM(BOTH FROM scopes)) > 0))
);


--
-- Name: one_time_tokens; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.one_time_tokens (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_type auth.one_time_token_type NOT NULL,
    token_hash text NOT NULL,
    relates_to text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT one_time_tokens_token_hash_check CHECK ((char_length(token_hash) > 0))
);


--
-- Name: refresh_tokens; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.refresh_tokens (
    instance_id uuid,
    id bigint NOT NULL,
    token character varying(255),
    user_id character varying(255),
    revoked boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    parent character varying(255),
    session_id uuid
);


--
-- Name: TABLE refresh_tokens; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.refresh_tokens IS 'Auth: Store of tokens used to refresh JWT tokens once they expire.';


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE; Schema: auth; Owner: -
--

CREATE SEQUENCE auth.refresh_tokens_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: auth; Owner: -
--

ALTER SEQUENCE auth.refresh_tokens_id_seq OWNED BY auth.refresh_tokens.id;


--
-- Name: saml_providers; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.saml_providers (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    entity_id text NOT NULL,
    metadata_xml text NOT NULL,
    metadata_url text,
    attribute_mapping jsonb,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    name_id_format text,
    CONSTRAINT "entity_id not empty" CHECK ((char_length(entity_id) > 0)),
    CONSTRAINT "metadata_url not empty" CHECK (((metadata_url = NULL::text) OR (char_length(metadata_url) > 0))),
    CONSTRAINT "metadata_xml not empty" CHECK ((char_length(metadata_xml) > 0))
);


--
-- Name: TABLE saml_providers; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.saml_providers IS 'Auth: Manages SAML Identity Provider connections.';


--
-- Name: saml_relay_states; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.saml_relay_states (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    request_id text NOT NULL,
    for_email text,
    redirect_to text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    flow_state_id uuid,
    CONSTRAINT "request_id not empty" CHECK ((char_length(request_id) > 0))
);


--
-- Name: TABLE saml_relay_states; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.saml_relay_states IS 'Auth: Contains SAML Relay State information for each Service Provider initiated login.';


--
-- Name: schema_migrations; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.schema_migrations (
    version character varying(255) NOT NULL
);


--
-- Name: TABLE schema_migrations; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.schema_migrations IS 'Auth: Manages updates to the auth system.';


--
-- Name: sessions; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.sessions (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    factor_id uuid,
    aal auth.aal_level,
    not_after timestamp with time zone,
    refreshed_at timestamp without time zone,
    user_agent text,
    ip inet,
    tag text,
    oauth_client_id uuid,
    refresh_token_hmac_key text,
    refresh_token_counter bigint,
    scopes text,
    CONSTRAINT sessions_scopes_length CHECK ((char_length(scopes) <= 4096))
);


--
-- Name: TABLE sessions; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.sessions IS 'Auth: Stores session data associated to a user.';


--
-- Name: COLUMN sessions.not_after; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.sessions.not_after IS 'Auth: Not after is a nullable column that contains a timestamp after which the session should be regarded as expired.';


--
-- Name: COLUMN sessions.refresh_token_hmac_key; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.sessions.refresh_token_hmac_key IS 'Holds a HMAC-SHA256 key used to sign refresh tokens for this session.';


--
-- Name: COLUMN sessions.refresh_token_counter; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.sessions.refresh_token_counter IS 'Holds the ID (counter) of the last issued refresh token.';


--
-- Name: sso_domains; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.sso_domains (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    domain text NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    CONSTRAINT "domain not empty" CHECK ((char_length(domain) > 0))
);


--
-- Name: TABLE sso_domains; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.sso_domains IS 'Auth: Manages SSO email address domain mapping to an SSO Identity Provider.';


--
-- Name: sso_providers; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.sso_providers (
    id uuid NOT NULL,
    resource_id text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    disabled boolean,
    CONSTRAINT "resource_id not empty" CHECK (((resource_id = NULL::text) OR (char_length(resource_id) > 0)))
);


--
-- Name: TABLE sso_providers; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.sso_providers IS 'Auth: Manages SSO identity provider information; see saml_providers for SAML.';


--
-- Name: COLUMN sso_providers.resource_id; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.sso_providers.resource_id IS 'Auth: Uniquely identifies a SSO provider according to a user-chosen resource ID (case insensitive), useful in infrastructure as code.';


--
-- Name: users; Type: TABLE; Schema: auth; Owner: -
--

CREATE TABLE auth.users (
    instance_id uuid,
    id uuid NOT NULL,
    aud character varying(255),
    role character varying(255),
    email character varying(255),
    encrypted_password character varying(255),
    email_confirmed_at timestamp with time zone,
    invited_at timestamp with time zone,
    confirmation_token character varying(255),
    confirmation_sent_at timestamp with time zone,
    recovery_token character varying(255),
    recovery_sent_at timestamp with time zone,
    email_change_token_new character varying(255),
    email_change character varying(255),
    email_change_sent_at timestamp with time zone,
    last_sign_in_at timestamp with time zone,
    raw_app_meta_data jsonb,
    raw_user_meta_data jsonb,
    is_super_admin boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    phone text DEFAULT NULL::character varying,
    phone_confirmed_at timestamp with time zone,
    phone_change text DEFAULT ''::character varying,
    phone_change_token character varying(255) DEFAULT ''::character varying,
    phone_change_sent_at timestamp with time zone,
    confirmed_at timestamp with time zone GENERATED ALWAYS AS (LEAST(email_confirmed_at, phone_confirmed_at)) STORED,
    email_change_token_current character varying(255) DEFAULT ''::character varying,
    email_change_confirm_status smallint DEFAULT 0,
    banned_until timestamp with time zone,
    reauthentication_token character varying(255) DEFAULT ''::character varying,
    reauthentication_sent_at timestamp with time zone,
    is_sso_user boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    is_anonymous boolean DEFAULT false NOT NULL,
    CONSTRAINT users_email_change_confirm_status_check CHECK (((email_change_confirm_status >= 0) AND (email_change_confirm_status <= 2)))
);


--
-- Name: TABLE users; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON TABLE auth.users IS 'Auth: Stores user login data within a secure schema.';


--
-- Name: COLUMN users.is_sso_user; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON COLUMN auth.users.is_sso_user IS 'Auth: Set this column to true when the account comes from SSO. These accounts can have duplicate emails.';


--
-- Name: achievement_definitions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.achievement_definitions (
    id integer NOT NULL,
    code character varying NOT NULL,
    name character varying NOT NULL,
    description text NOT NULL,
    badge_image_url character varying NOT NULL,
    rarity character varying(16) DEFAULT 'common'::character varying NOT NULL,
    is_public_announceable boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: achievement_definitions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.achievement_definitions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: achievement_definitions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.achievement_definitions_id_seq OWNED BY public.achievement_definitions.id;


--
-- Name: achievement_grants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.achievement_grants (
    id integer NOT NULL,
    user_id integer NOT NULL,
    achievement_definition_id integer NOT NULL,
    granted_at timestamp with time zone NOT NULL,
    publish_start_at timestamp with time zone NOT NULL,
    publish_end_at timestamp with time zone,
    external_grant_id character varying,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: achievement_grants_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.achievement_grants_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: achievement_grants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.achievement_grants_id_seq OWNED BY public.achievement_grants.id;


--
-- Name: api_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token_hash character varying NOT NULL,
    description character varying,
    idempotency_key character varying,
    created_at timestamp with time zone DEFAULT now(),
    last_used_at timestamp with time zone
);


--
-- Name: api_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.api_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: api_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.api_tokens_id_seq OWNED BY public.api_tokens.id;


--
-- Name: comments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.comments (
    id integer NOT NULL,
    user_id integer NOT NULL,
    daily_snippet_id integer,
    weekly_snippet_id integer,
    comment_type character varying(16) DEFAULT 'peer'::character varying NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: comments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.comments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.comments_id_seq OWNED BY public.comments.id;


--
-- Name: consents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.consents (
    id integer NOT NULL,
    user_id integer,
    term_id integer,
    agreed_at timestamp with time zone DEFAULT now()
);


--
-- Name: consents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.consents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.consents_id_seq OWNED BY public.consents.id;


--
-- Name: daily_snippets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.daily_snippets (
    id integer NOT NULL,
    user_id integer NOT NULL,
    date date NOT NULL,
    content text NOT NULL,
    playbook text,
    feedback text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: daily_snippets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.daily_snippets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: daily_snippets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.daily_snippets_id_seq OWNED BY public.daily_snippets.id;


--
-- Name: notification_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_settings (
    user_id integer NOT NULL,
    notify_post_author boolean DEFAULT true NOT NULL,
    notify_mentions boolean DEFAULT true NOT NULL,
    notify_participants boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    user_id integer NOT NULL,
    actor_user_id integer NOT NULL,
    type character varying(50) NOT NULL,
    daily_snippet_id integer,
    weekly_snippet_id integer,
    comment_id integer,
    is_read boolean DEFAULT false NOT NULL,
    read_at timestamp with time zone,
    dedupe_key character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: peer_evaluation_session_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.peer_evaluation_session_members (
    id integer NOT NULL,
    session_id integer NOT NULL,
    student_user_id integer NOT NULL,
    team_label character varying(64) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: peer_evaluation_session_members_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.peer_evaluation_session_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: peer_evaluation_session_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.peer_evaluation_session_members_id_seq OWNED BY public.peer_evaluation_session_members.id;


--
-- Name: peer_evaluation_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.peer_evaluation_sessions (
    id integer NOT NULL,
    title character varying NOT NULL,
    professor_user_id integer NOT NULL,
    is_open boolean DEFAULT true NOT NULL,
    access_token character varying(128) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: peer_evaluation_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.peer_evaluation_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: peer_evaluation_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.peer_evaluation_sessions_id_seq OWNED BY public.peer_evaluation_sessions.id;


--
-- Name: peer_evaluation_submissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.peer_evaluation_submissions (
    id integer NOT NULL,
    session_id integer NOT NULL,
    evaluator_user_id integer NOT NULL,
    evaluatee_user_id integer NOT NULL,
    contribution_percent integer NOT NULL,
    fit_yes_no boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_peer_eval_submission_contribution_range CHECK (((contribution_percent >= 0) AND (contribution_percent <= 100)))
);


--
-- Name: peer_evaluation_submissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.peer_evaluation_submissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: peer_evaluation_submissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.peer_evaluation_submissions_id_seq OWNED BY public.peer_evaluation_submissions.id;


--
-- Name: role_assignment_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_assignment_rules (
    id integer NOT NULL,
    rule_type character varying NOT NULL,
    rule_value json NOT NULL,
    assigned_role character varying NOT NULL,
    priority integer,
    is_active boolean,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: role_assignment_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.role_assignment_rules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: role_assignment_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.role_assignment_rules_id_seq OWNED BY public.role_assignment_rules.id;


--
-- Name: route_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.route_permissions (
    id integer NOT NULL,
    path character varying NOT NULL,
    method character varying NOT NULL,
    is_public boolean,
    roles json
);


--
-- Name: route_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.route_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: route_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.route_permissions_id_seq OWNED BY public.route_permissions.id;


--
-- Name: student_risk_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_risk_snapshots (
    id integer NOT NULL,
    user_id integer NOT NULL,
    evaluated_at timestamp with time zone DEFAULT now() NOT NULL,
    l1 double precision NOT NULL,
    l2 double precision NOT NULL,
    l3 double precision NOT NULL,
    risk_score double precision NOT NULL,
    risk_band character varying(16) NOT NULL,
    confidence json NOT NULL,
    reasons_json json NOT NULL,
    tone_policy_json json NOT NULL,
    daily_subscores_json json NOT NULL,
    weekly_subscores_json json NOT NULL,
    trend_subscores_json json NOT NULL,
    needs_professor_review boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: student_risk_snapshots_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_risk_snapshots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_risk_snapshots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_risk_snapshots_id_seq OWNED BY public.student_risk_snapshots.id;


--
-- Name: teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teams (
    id integer NOT NULL,
    name character varying NOT NULL,
    invite_code character varying,
    league_type character varying DEFAULT 'none'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: teams_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teams_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teams_id_seq OWNED BY public.teams.id;


--
-- Name: terms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.terms (
    id integer NOT NULL,
    type character varying NOT NULL,
    version character varying NOT NULL,
    content text NOT NULL,
    is_required boolean,
    is_active boolean,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: terms_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.terms_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: terms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.terms_id_seq OWNED BY public.terms.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying NOT NULL,
    name character varying,
    picture character varying,
    created_at timestamp with time zone DEFAULT now(),
    roles json,
    league_type character varying DEFAULT 'none'::character varying NOT NULL,
    team_id integer
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: weekly_snippets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.weekly_snippets (
    id integer NOT NULL,
    user_id integer NOT NULL,
    week date NOT NULL,
    content text NOT NULL,
    playbook text,
    feedback text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: weekly_snippets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.weekly_snippets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: weekly_snippets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.weekly_snippets_id_seq OWNED BY public.weekly_snippets.id;


--
-- Name: messages; Type: TABLE; Schema: realtime; Owner: -
--

CREATE TABLE realtime.messages (
    topic text NOT NULL,
    extension text NOT NULL,
    payload jsonb,
    event text,
    private boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    inserted_at timestamp without time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL
)
PARTITION BY RANGE (inserted_at);


--
-- Name: schema_migrations; Type: TABLE; Schema: realtime; Owner: -
--

CREATE TABLE realtime.schema_migrations (
    version bigint NOT NULL,
    inserted_at timestamp(0) without time zone
);


--
-- Name: subscription; Type: TABLE; Schema: realtime; Owner: -
--

CREATE TABLE realtime.subscription (
    id bigint NOT NULL,
    subscription_id uuid NOT NULL,
    entity regclass NOT NULL,
    filters realtime.user_defined_filter[] DEFAULT '{}'::realtime.user_defined_filter[] NOT NULL,
    claims jsonb NOT NULL,
    claims_role regrole GENERATED ALWAYS AS (realtime.to_regrole((claims ->> 'role'::text))) STORED NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    action_filter text DEFAULT '*'::text,
    CONSTRAINT subscription_action_filter_check CHECK ((action_filter = ANY (ARRAY['*'::text, 'INSERT'::text, 'UPDATE'::text, 'DELETE'::text])))
);


--
-- Name: subscription_id_seq; Type: SEQUENCE; Schema: realtime; Owner: -
--

ALTER TABLE realtime.subscription ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME realtime.subscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: buckets; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.buckets (
    id text NOT NULL,
    name text NOT NULL,
    owner uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    public boolean DEFAULT false,
    avif_autodetection boolean DEFAULT false,
    file_size_limit bigint,
    allowed_mime_types text[],
    owner_id text,
    type storage.buckettype DEFAULT 'STANDARD'::storage.buckettype NOT NULL
);


--
-- Name: COLUMN buckets.owner; Type: COMMENT; Schema: storage; Owner: -
--

COMMENT ON COLUMN storage.buckets.owner IS 'Field is deprecated, use owner_id instead';


--
-- Name: buckets_analytics; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.buckets_analytics (
    name text NOT NULL,
    type storage.buckettype DEFAULT 'ANALYTICS'::storage.buckettype NOT NULL,
    format text DEFAULT 'ICEBERG'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: buckets_vectors; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.buckets_vectors (
    id text NOT NULL,
    type storage.buckettype DEFAULT 'VECTOR'::storage.buckettype NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: migrations; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.migrations (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    hash character varying(40) NOT NULL,
    executed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: objects; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.objects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    bucket_id text,
    name text,
    owner uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_accessed_at timestamp with time zone DEFAULT now(),
    metadata jsonb,
    path_tokens text[] GENERATED ALWAYS AS (string_to_array(name, '/'::text)) STORED,
    version text,
    owner_id text,
    user_metadata jsonb
);


--
-- Name: COLUMN objects.owner; Type: COMMENT; Schema: storage; Owner: -
--

COMMENT ON COLUMN storage.objects.owner IS 'Field is deprecated, use owner_id instead';


--
-- Name: s3_multipart_uploads; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.s3_multipart_uploads (
    id text NOT NULL,
    in_progress_size bigint DEFAULT 0 NOT NULL,
    upload_signature text NOT NULL,
    bucket_id text NOT NULL,
    key text NOT NULL COLLATE pg_catalog."C",
    version text NOT NULL,
    owner_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    user_metadata jsonb
);


--
-- Name: s3_multipart_uploads_parts; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.s3_multipart_uploads_parts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    upload_id text NOT NULL,
    size bigint DEFAULT 0 NOT NULL,
    part_number integer NOT NULL,
    bucket_id text NOT NULL,
    key text NOT NULL COLLATE pg_catalog."C",
    etag text NOT NULL,
    owner_id text,
    version text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: vector_indexes; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.vector_indexes (
    id text DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL COLLATE pg_catalog."C",
    bucket_id text NOT NULL,
    data_type text NOT NULL,
    dimension integer NOT NULL,
    distance_metric text NOT NULL,
    metadata_configuration jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: refresh_tokens id; Type: DEFAULT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.refresh_tokens ALTER COLUMN id SET DEFAULT nextval('auth.refresh_tokens_id_seq'::regclass);


--
-- Name: achievement_definitions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.achievement_definitions ALTER COLUMN id SET DEFAULT nextval('public.achievement_definitions_id_seq'::regclass);


--
-- Name: achievement_grants id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.achievement_grants ALTER COLUMN id SET DEFAULT nextval('public.achievement_grants_id_seq'::regclass);


--
-- Name: api_tokens id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_tokens ALTER COLUMN id SET DEFAULT nextval('public.api_tokens_id_seq'::regclass);


--
-- Name: comments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments ALTER COLUMN id SET DEFAULT nextval('public.comments_id_seq'::regclass);


--
-- Name: consents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consents ALTER COLUMN id SET DEFAULT nextval('public.consents_id_seq'::regclass);


--
-- Name: daily_snippets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_snippets ALTER COLUMN id SET DEFAULT nextval('public.daily_snippets_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: peer_evaluation_session_members id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_session_members ALTER COLUMN id SET DEFAULT nextval('public.peer_evaluation_session_members_id_seq'::regclass);


--
-- Name: peer_evaluation_sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_sessions ALTER COLUMN id SET DEFAULT nextval('public.peer_evaluation_sessions_id_seq'::regclass);


--
-- Name: peer_evaluation_submissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_submissions ALTER COLUMN id SET DEFAULT nextval('public.peer_evaluation_submissions_id_seq'::regclass);


--
-- Name: role_assignment_rules id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_assignment_rules ALTER COLUMN id SET DEFAULT nextval('public.role_assignment_rules_id_seq'::regclass);


--
-- Name: route_permissions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.route_permissions ALTER COLUMN id SET DEFAULT nextval('public.route_permissions_id_seq'::regclass);


--
-- Name: student_risk_snapshots id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_risk_snapshots ALTER COLUMN id SET DEFAULT nextval('public.student_risk_snapshots_id_seq'::regclass);


--
-- Name: teams id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams ALTER COLUMN id SET DEFAULT nextval('public.teams_id_seq'::regclass);


--
-- Name: terms id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.terms ALTER COLUMN id SET DEFAULT nextval('public.terms_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: weekly_snippets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weekly_snippets ALTER COLUMN id SET DEFAULT nextval('public.weekly_snippets_id_seq'::regclass);


--
-- Data for Name: audit_log_entries; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.audit_log_entries (instance_id, id, payload, created_at, ip_address) FROM stdin;
\.


--
-- Data for Name: custom_oauth_providers; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.custom_oauth_providers (id, provider_type, identifier, name, client_id, client_secret, acceptable_client_ids, scopes, pkce_enabled, attribute_mapping, authorization_params, enabled, email_optional, issuer, discovery_url, skip_nonce_check, cached_discovery, discovery_cached_at, authorization_url, token_url, userinfo_url, jwks_uri, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: flow_state; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.flow_state (id, user_id, auth_code, code_challenge_method, code_challenge, provider_type, provider_access_token, provider_refresh_token, created_at, updated_at, authentication_method, auth_code_issued_at, invite_token, referrer, oauth_client_state_id, linking_target_id, email_optional) FROM stdin;
\.


--
-- Data for Name: identities; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at, id) FROM stdin;
\.


--
-- Data for Name: instances; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.instances (id, uuid, raw_base_config, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: mfa_amr_claims; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.mfa_amr_claims (session_id, created_at, updated_at, authentication_method, id) FROM stdin;
\.


--
-- Data for Name: mfa_challenges; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.mfa_challenges (id, factor_id, created_at, verified_at, ip_address, otp_code, web_authn_session_data) FROM stdin;
\.


--
-- Data for Name: mfa_factors; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.mfa_factors (id, user_id, friendly_name, factor_type, status, created_at, updated_at, secret, phone, last_challenged_at, web_authn_credential, web_authn_aaguid, last_webauthn_challenge_data) FROM stdin;
\.


--
-- Data for Name: oauth_authorizations; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.oauth_authorizations (id, authorization_id, client_id, user_id, redirect_uri, scope, state, resource, code_challenge, code_challenge_method, response_type, status, authorization_code, created_at, expires_at, approved_at, nonce) FROM stdin;
\.


--
-- Data for Name: oauth_client_states; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.oauth_client_states (id, provider_type, code_verifier, created_at) FROM stdin;
\.


--
-- Data for Name: oauth_clients; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.oauth_clients (id, client_secret_hash, registration_type, redirect_uris, grant_types, client_name, client_uri, logo_uri, created_at, updated_at, deleted_at, client_type, token_endpoint_auth_method) FROM stdin;
\.


--
-- Data for Name: oauth_consents; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.oauth_consents (id, user_id, client_id, scopes, granted_at, revoked_at) FROM stdin;
\.


--
-- Data for Name: one_time_tokens; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.one_time_tokens (id, user_id, token_type, token_hash, relates_to, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: refresh_tokens; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.refresh_tokens (instance_id, id, token, user_id, revoked, created_at, updated_at, parent, session_id) FROM stdin;
\.


--
-- Data for Name: saml_providers; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.saml_providers (id, sso_provider_id, entity_id, metadata_xml, metadata_url, attribute_mapping, created_at, updated_at, name_id_format) FROM stdin;
\.


--
-- Data for Name: saml_relay_states; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.saml_relay_states (id, sso_provider_id, request_id, for_email, redirect_to, created_at, updated_at, flow_state_id) FROM stdin;
\.


--
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.schema_migrations (version) FROM stdin;
20171026211738
20171026211808
20171026211834
20180103212743
20180108183307
20180119214651
20180125194653
00
20210710035447
20210722035447
20210730183235
20210909172000
20210927181326
20211122151130
20211124214934
20211202183645
20220114185221
20220114185340
20220224000811
20220323170000
20220429102000
20220531120530
20220614074223
20220811173540
20221003041349
20221003041400
20221011041400
20221020193600
20221021073300
20221021082433
20221027105023
20221114143122
20221114143410
20221125140132
20221208132122
20221215195500
20221215195800
20221215195900
20230116124310
20230116124412
20230131181311
20230322519590
20230402418590
20230411005111
20230508135423
20230523124323
20230818113222
20230914180801
20231027141322
20231114161723
20231117164230
20240115144230
20240214120130
20240306115329
20240314092811
20240427152123
20240612123726
20240729123726
20240802193726
20240806073726
20241009103726
20250717082212
20250731150234
20250804100000
20250901200500
20250903112500
20250904133000
20250925093508
20251007112900
20251104100000
20251111201300
20251201000000
20260115000000
20260121000000
20260219120000
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.sessions (id, user_id, created_at, updated_at, factor_id, aal, not_after, refreshed_at, user_agent, ip, tag, oauth_client_id, refresh_token_hmac_key, refresh_token_counter, scopes) FROM stdin;
\.


--
-- Data for Name: sso_domains; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.sso_domains (id, sso_provider_id, domain, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: sso_providers; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.sso_providers (id, resource_id, created_at, updated_at, disabled) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: auth; Owner: -
--

COPY auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at, invited_at, confirmation_token, confirmation_sent_at, recovery_token, recovery_sent_at, email_change_token_new, email_change, email_change_sent_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, is_super_admin, created_at, updated_at, phone, phone_confirmed_at, phone_change, phone_change_token, phone_change_sent_at, email_change_token_current, email_change_confirm_status, banned_until, reauthentication_token, reauthentication_sent_at, is_sso_user, deleted_at, is_anonymous) FROM stdin;
\.


--
-- Data for Name: achievement_definitions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.achievement_definitions (id, code, name, description, badge_image_url, rarity, is_public_announceable, created_at, updated_at) FROM stdin;
1	daily_submitted	데일리 제출	데일리 스니펫을 제출했습니다.	https://assets.1000.school/achievements/v1/daily_submitted.png	common	t	2026-03-06 06:55:35.832383+00	2026-03-06 06:55:35.832383+00
2	daily_score_90	데일리 점수 90	데일리 피드백 점수 90점 이상을 달성했습니다.	https://assets.1000.school/achievements/v1/daily_score_90.png	rare	t	2026-03-06 06:55:35.832383+00	2026-03-06 06:55:35.832383+00
3	weekly_submitted	위클리 제출	위클리 스니펫을 제출했습니다.	https://assets.1000.school/achievements/v1/weekly_submitted.png	uncommon	t	2026-03-06 06:55:35.832383+00	2026-03-06 06:55:35.832383+00
4	daily_rank_1	데일리 1위	데일리 피드백 점수 1위를 달성했습니다.	https://assets.1000.school/achievements/v1/daily_rank_1.png	uncommon	t	2026-03-06 06:55:35.832383+00	2026-03-06 06:55:35.832383+00
5	weekly_rank_1	위클리 1위	위클리 피드백 점수 1위를 달성했습니다.	https://assets.1000.school/achievements/v1/weekly_rank_1.png	epic	t	2026-03-06 06:55:35.832383+00	2026-03-06 06:55:35.832383+00
6	daily_team_all_submitted	데일리 팀 전원 제출	같은 팀원 전원이 데일리 스니펫을 제출했습니다.	https://assets.1000.school/achievements/v1/daily_team_all_submitted.png	uncommon	t	2026-03-06 06:55:35.832383+00	2026-03-06 06:55:35.832383+00
7	weekly_team_all_submitted	위클리 팀 전원 제출	같은 팀원 전원이 위클리 스니펫을 제출했습니다.	https://assets.1000.school/achievements/v1/weekly_team_all_submitted.png	rare	t	2026-03-06 06:55:35.832383+00	2026-03-06 06:55:35.832383+00
8	daily_streak_7	데일리 7일 연속	7일 연속으로 데일리 스니펫을 제출했습니다.	https://assets.1000.school/achievements/v1/daily_streak_7.png	rare	t	2026-03-06 06:55:35.832383+00	2026-03-06 06:55:35.832383+00
9	daily_streak_28	데일리 28일 연속	28일 연속으로 데일리 스니펫을 제출했습니다.	https://assets.1000.school/achievements/v1/daily_streak_28.png	epic	t	2026-03-06 06:55:35.832383+00	2026-03-06 06:55:35.832383+00
10	daily_streak_100	데일리 100일 연속	100일 연속으로 데일리 스니펫을 제출했습니다.	https://assets.1000.school/achievements/v1/daily_streak_100.png	legend	t	2026-03-06 06:55:35.832383+00	2026-03-06 06:55:35.832383+00
11	team_daily_streak_7	팀 데일리 7일 연속	팀원 전원이 7일 연속으로 데일리 스니펫을 제출했습니다.	https://assets.1000.school/achievements/v1/team_daily_streak_7.png	epic	t	2026-03-06 06:55:35.832383+00	2026-03-06 06:55:35.832383+00
12	team_daily_streak_28	팀 데일리 28일 연속	팀원 전원이 28일 연속으로 데일리 스니펫을 제출했습니다.	https://assets.1000.school/achievements/v1/team_daily_streak_28.png	legend	t	2026-03-06 06:55:35.832383+00	2026-03-06 06:55:35.832383+00
13	e2e_legend_streak	E2E 레전드 연속 달성	E2E legend test seed	https://assets.1000.school/achievements/v1/e2e_legend.png	legend	t	2026-03-09 05:07:03.218887+00	2026-03-09 05:07:03.218887+00
14	e2e_epic_writer	E2E 에픽 작성자	E2E epic test seed	https://assets.1000.school/achievements/v1/e2e_epic.png	epic	t	2026-03-09 05:07:03.218887+00	2026-03-09 05:07:03.218887+00
15	e2e_common_starter	E2E 일반 시작	E2E common test seed	https://assets.1000.school/achievements/v1/e2e_common.png	common	t	2026-03-09 05:07:03.218887+00	2026-03-09 05:07:03.218887+00
\.


--
-- Data for Name: achievement_grants; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.achievement_grants (id, user_id, achievement_definition_id, granted_at, publish_start_at, publish_end_at, external_grant_id, created_at) FROM stdin;
1	1	13	2026-03-09 05:07:03.367004+00	2026-03-09 05:06:03.367004+00	\N	e2e-seed:e2e_legend_streak:1773032823	2026-03-09 05:07:03.218887+00
2	1	14	2026-03-09 05:06:03.367004+00	2026-03-09 05:05:03.367004+00	\N	e2e-seed:e2e_epic_writer:1773032823	2026-03-09 05:07:03.218887+00
3	1	15	2026-03-09 05:05:03.367004+00	2026-03-09 05:04:03.367004+00	\N	e2e-seed:e2e_common_starter:1773032823	2026-03-09 05:07:03.218887+00
\.


--
-- Data for Name: api_tokens; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.api_tokens (id, user_id, token_hash, description, idempotency_key, created_at, last_used_at) FROM stdin;
1	1	615e20209dd1a4673d3ca89ccc2939e4837beb70f875df6e73fb56b5e7b7b8b5	[CHK-DAILY-004] 1772937915948	2434aab6-d8b8-45f3-bc9e-6b76d92d96d5	2026-03-08 02:45:18.472995+00	2026-03-08 02:45:19.150967+00
9	1	21566cf9e36940766b3fe52fb847624f6ada84e30d76c11bfc826699079686c1	[CHK-DAILY-004] 1772979835675	3e2c7d05-3cae-4d65-948b-86b9201181aa	2026-03-08 14:23:59.142619+00	2026-03-08 14:23:59.842084+00
2	1	469986db683b0063385b1d4192f776cba4146c7da67e15ab572b37399ffe7998	[CHK-WEEKLY-004] 1772937986518	5a1c1531-0c36-48f2-9216-4852616b70f3	2026-03-08 02:46:29.030856+00	2026-03-08 02:46:29.612407+00
12	1	e5b7ee881ae3cf9c04c1169764f988b27097a39186974e11cd3c7fdeb49d7a00	[CHK-WEEKLY-004] 1773032471012	e845c13c-746e-442a-964b-3c7e3e652412	2026-03-09 05:01:13.560874+00	2026-03-09 05:01:14.169995+00
3	1	0b616dbf3a9b9257040279708743a9e5c776268579e7b2ce0ed62d3e9767c781	[CHK-DAILY-004] 1772938229917	b994fdd4-c1cf-4d79-a4de-b3034a5e5419	2026-03-08 02:50:32.409636+00	2026-03-08 02:50:33.022586+00
10	1	1e04e72d6f512b34b0024c8f966bac9ac2ce63bdf04f700b2afe901eda5200f0	[CHK-WEEKLY-004] 1772979932420	2049b03a-d2ec-4a08-9716-4331e0b095e0	2026-03-08 14:25:34.989462+00	2026-03-08 14:25:35.664995+00
4	1	997df2c9bb6ebef0967cfd8256399fa2fce9e2edb21f49702ff62909b9d008e9	[CHK-WEEKLY-004] 1772938306204	c4650353-41b7-48df-87bf-6ba049768d56	2026-03-08 02:51:48.705748+00	2026-03-08 02:51:49.417606+00
13	1	1f32a2581253c82519c91a8a8d795002d8cbd2ec2970c134da39e87aeb94bf60	[CHK-DAILY-004] 1773032912357	a52d308c-0bb2-43f5-ad80-516c68e18ef9	2026-03-09 05:08:34.895616+00	2026-03-09 05:08:35.540714+00
5	6	259015a5206ce471a25a65000b7f64c47f2044fc23021a34a7bde2eea4103bf4	[CHK-DAILY-004] 1772974814375	21355944-fe51-4315-8f65-9cfd359e9809	2026-03-08 13:00:16.955246+00	2026-03-08 13:00:17.70455+00
6	6	b3d662cd5e299b75db4a50e1e1fdc787ef265fcacac0dca31dd662065d124488	[CHK-WEEKLY-004] 1772974894052	a8a1c0ad-0445-4ed4-8d49-b54326478553	2026-03-08 13:01:36.660226+00	2026-03-08 13:01:37.351914+00
14	1	97211b6c521b0431707a448b3dc95a9e3b9a3e815e836b872974ab6f6536807b	[CHK-WEEKLY-004] 1773033003674	bd74f6d0-19ba-4ccd-8507-e963102b84e3	2026-03-09 05:10:06.270138+00	2026-03-09 05:10:06.880961+00
7	6	b914ba8f5a0a172a14c62a1855c9627654e4dca6bfc26b61ad9c91b17e3a8f00	[CHK-DAILY-004] 1772975545049	6a70ffd5-8648-4d0e-9d50-53e4a82a4ebb	2026-03-08 13:12:27.545425+00	2026-03-08 13:12:28.263023+00
8	6	a432c4decbdf3db42452a691b70663a7931d40177efe4e3bca09f9a66e714d58	[CHK-WEEKLY-004] 1772975616626	2f0bf27b-99f5-48c5-8029-a1a45cf662a1	2026-03-08 13:13:39.189834+00	2026-03-08 13:13:40.026818+00
11	1	3bcb7e98b5601b5d0ffe6b80f0e1c3ccc60add0899735b25a06f6169d07ccdda	[CHK-DAILY-004] 1773032422169	71ce4042-ea96-4d2f-9002-9fc45b7ffc4c	2026-03-09 05:00:24.738111+00	2026-03-09 05:00:25.494529+00
15	1	150458bbf155e1d2077fd695599bbce6e94cb3a683459258315c9fdcd3ff4376	[CHK-DAILY-004] 1773033164716	a8162e4f-200a-4382-a89e-430e3e804a76	2026-03-09 05:12:47.280044+00	2026-03-09 05:12:47.893872+00
16	1	b0e90f53e9ec38c1db6c66e33d5c01b734016599f329b6bdaac632f38f47b671	[CHK-WEEKLY-004] 1773033232193	280f55d6-2ca7-412b-89ea-51ad83ee2b14	2026-03-09 05:13:54.750764+00	2026-03-09 05:13:55.384041+00
\.


--
-- Data for Name: comments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.comments (id, user_id, daily_snippet_id, weekly_snippet_id, comment_type, content, created_at, updated_at) FROM stdin;
1	2	\N	1	professor	[CHK-PROF-002] professor comment 1772937889880	2026-03-08 02:44:50.839675+00	2026-03-08 02:44:50.839675+00
2	2	\N	1	professor	[CHK-PROF-002] professor comment 1772938201305	2026-03-08 02:50:02.259809+00	2026-03-08 02:50:02.259809+00
3	2	\N	1	professor	[CHK-PROF-002] professor comment 1772974414674	2026-03-08 12:53:35.682909+00	2026-03-08 12:53:35.682909+00
4	2	\N	1	professor	[CHK-PROF-002] professor comment 1772974782966	2026-03-08 12:59:43.957938+00	2026-03-08 12:59:43.957938+00
5	2	\N	1	professor	[CHK-PROF-002] professor comment 1772975513777	2026-03-08 13:11:54.767038+00	2026-03-08 13:11:54.767038+00
6	2	\N	6	professor	[CHK-PROF-002] professor comment 1773032103576	2026-03-09 04:55:04.571365+00	2026-03-09 04:55:04.571365+00
7	2	\N	6	professor	[CHK-PROF-002] professor comment 1773032251223	2026-03-09 04:57:32.206776+00	2026-03-09 04:57:32.206776+00
8	2	\N	6	professor	[CHK-PROF-002] professor comment 1773032371101	2026-03-09 04:59:32.082307+00	2026-03-09 04:59:32.082307+00
9	2	\N	6	professor	[CHK-PROF-002] professor comment 1773041484354	2026-03-09 07:31:25.34339+00	2026-03-09 07:31:25.34339+00
10	2	\N	6	professor	[CHK-PROF-002] professor comment 1773041624804	2026-03-09 07:33:45.789895+00	2026-03-09 07:33:45.789895+00
11	2	\N	7	professor	[CHK-PROF-002] professor comment 1773042080965	2026-03-09 07:41:21.423055+00	2026-03-09 07:41:21.423055+00
\.


--
-- Data for Name: consents; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.consents (id, user_id, term_id, agreed_at) FROM stdin;
1	1	1	2026-03-08 02:37:46.765742+00
2	1	2	2026-03-08 02:37:47.013219+00
3	5	1	2026-03-08 12:48:55.654725+00
4	5	2	2026-03-08 12:48:55.792768+00
5	6	1	2026-03-08 12:53:21.116949+00
6	6	2	2026-03-08 12:53:21.252883+00
7	7	1	2026-03-09 04:54:51.089737+00
8	7	2	2026-03-09 04:54:51.334636+00
9	2	1	2026-03-09 07:13:14.540365+00
10	2	2	2026-03-09 07:13:14.789435+00
11	8	1	2026-03-09 07:33:35.885237+00
12	8	2	2026-03-09 07:33:36.016382+00
14	4	1	2026-03-09 11:42:22.126528+00
20	3	1	2026-03-09 11:42:22.126528+00
22	4	2	2026-03-09 11:42:22.126528+00
28	3	2	2026-03-09 11:42:22.126528+00
\.


--
-- Data for Name: daily_snippets; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.daily_snippets (id, user_id, date, content, playbook, feedback, created_at, updated_at) FROM stdin;
1	3	2026-03-08	[E2E-PROF-STUDENT-DAILY] 2026-03-08	\N	\N	2026-03-08 02:37:51.168135+00	2026-03-08 02:37:51.168135+00
8	1	2026-03-09	#### 오늘 한 일\n\n- 전날 작업(CHK-DAILY-005: organize source 1772956561955) 검토 후 후속 조치: 파일/폴더 구조 정리, 네이밍 규칙 일부 적용, 주석/README 초안 작성.  \n  - 변경사항 커밋/PR 준비 중(커밋/PR 번호: [입력]).  \n- 팀에 공유하거나 리뷰 요청한 내용이 있으면 해당 내역 추가: [예: 슬랙/이슈 링크].\n\n#### 수행 목적\n\n- 소스 가독성 및 유지보수성 향상으로 향후 기능 개발·리뷰 속도 개선.\n- 팀원이 해당 소스에 빠르게 진입할 수 있도록 문서화 기반 마련.\n\n#### 하이라이트\n\n- 주요 파일 구조를 정리해 탐색 용이성 개선(구체적으로 정리한 폴더/파일: [입력]).\n- README 초안으로 변경 목적과 사용 방법을 빠르게 전달할 수 있는 상태로 만듦.\n\n#### 로우라이트\n\n- 관련 컨텍스트(설계 문서/결정 기록)가 부족해 일부 리팩토링 결정을 미룸.\n- 자동화된 테스트/검증은 아직 완료되지 않음(테스트 실패/미작성 항목: [입력]).\n\n#### 내일의 우선순위\n\n- PR 마무리 및 팀 리뷰 요청(검토받을 항목 명시).  \n- 정리한 부분에 대한 테스트 실행 및 결과 확인 → 필요 시 수정.  \n- README/변경로그 보완 및 최종 문서화.  \n- 관련자(팀원 또는 멘토)와 짧은 동기화 미팅으로 결정 보류된 항목 확정.\n\n#### 오늘 내가 팀에 기여한 가치\n\n- 소스 정리와 문서화로 다음 작업자의 진입 장벽을 낮추어 전체 개발 효율에 기여.\n- 리뷰 가능한 상태로 만들어 개발 파이프라인 흐름을 원활하게 함.\n\n#### 오늘의 배움 또는 남길 말\n\n- 정리하면서 느낀 점/개선 아이디어: 예) 파일 네이밍 컨벤션을 명문화할 필요가 있음, 공통 유틸을 모듈화하면 중복 감소. (구체 내용 입력: [입력])  \n- 다음 번엔 처음부터 문서화를 병행하자.\n\n#### 헬스 체크 (10점)\n\n- 제안: 7/10 — [간단한 이유 입력, 예: 약간 피로하지만 집중은 잘됨]	\N	{\n  "total_score": 84,\n  "scores": {\n    "record_completeness": {\n      "score": 13,\n      "max_score": 15\n    },\n    "learning_signal_detection": {\n      "score": 20,\n      "max_score": 25\n    },\n    "cause_effect_connection": {\n      "score": 15,\n      "max_score": 20\n    },\n    "action_translation": {\n      "score": 18,\n      "max_score": 20\n    },\n    "learning_attitude_consistency": {\n      "score": 18,\n      "max_score": 20\n    }\n  },\n  "key_learning": "초기부터 문서화와 명확한 네이밍/폴더 구조 규칙을 병행하면 리팩토링·리뷰 속도와 품질이 개선된다.",\n  "learning_sources": [\n    "highlight",\n    "lowlight",\n    "emotion",\n    "energy",\n    "decision"\n  ],\n  "playbook_relation": {\n    "related_playbook_item": "",\n    "relation_type": "extend",\n    "playbook_insight": "현재 별도의 운영 가이드가 없으므로, 코드 정리·문서화·테스트·PR 절차를 표준화하는 초기 가이드를 추가하면 향후 동일한 이슈(컨텍스트 부족, 테스트 미완료, 미정 결정)에 대한 대응 속도와 일관성이 올라갈 것이다."\n  },\n  "playbook_update_markdown": "## 초기 개발·정리 가이드(추가 권장 항목)\\n\\n- 목적: 소스 가독성·유지보수성 향상, 신규 개발자 진입 비용 감소\\n\\n- 파일/폴더 구조 표준\\n  - 프로젝트 루트 주요 폴더(예: src/, lib/, tests/, docs/) 역할 정의\\n  - 모듈화 기준(기능 단위 폴더, 공통 유틸은 /lib 또는 /shared)\\n  - 폴더 네이밍 컨벤션 예시(소문자, 하이픈/언더바 규칙)\\n\\n- 네이밍 규칙\\n  - 파일/폴더/모듈 네이밍 사례와 금지 사례\\n  - 함수/클래스/변수 네이밍 기본 가이드라인 링크\\n\\n- 문서화 체크리스트(README 및 변경로그)\\n  - 변경 목적 한 줄 요약\\n  - 영향 범위(파일/기능 목록)\\n  - 사용 방법 및 간단 예제\\n  - 미해결 결정/추가 작업 리스트 및 책임자\\n\\n- PR 제출 전 체크리스트\\n  - 관련 설계/결정 문서 링크 포함 여부\\n  - 수정된 파일 구조와 네이밍 설명(요약)\\n  - 자동화 테스트 통과 여부(테스트가 없을 경우 최소 수동 체크 항목 명시)\\n  - 리뷰어에게 요청할 주요 판단 포인트 명시(예: 구조 변경 타당성, 성능 영향)\\n\\n- 테스트 규칙\\n  - 핵심 변경점은 단위/통합 테스트로 검증(간단한 예시 템플릿 포함)\\n  - 테스트 미작성 시 PR 템플릿에 이유와 향후 계획 명시\\n\\n- 결정 기록 템플릿\\n  - 결정 제목 / 배경 / 대안 / 선택한 방안 / 책임자 / 리뷰 예정일\\n\\n- 동기화(간단 미팅) 가이드\\n  - 결정 지연 항목은 15분 스탠드업으로 빠르게 합의\\n  - 미팅 전 의제와 필요한 자료(간단 설계/스크린샷) 미리 공유\\n\\n- 점진적 적용 권장\\n  - 우선순위: README/PR 템플릿 → 네이밍 규칙 → 테스트 커버리지\\n  - 작은 변경부터 규칙을 적용해 팀 합의 형성\\n\\n(이 항목들은 초기 가이드로서 저장해두고, 팀 피드백을 받아 2주 단위로 보완 권장)",\n  "next_action": "정리한 변경사항으로 PR을 제출하고 팀에 리뷰 요청을 보낸다.",\n  "mentor_comment": "오늘 한 작업은 다음 사람의 시간을 아낀다는 점에서 큰 가치가 있습니다. 특히 README 초안과 파일 구조 정리는 바로 활용 가능한 산출물이라 팀 효율에 즉시 기여할 수 있어요. 다만 설계/결정 기록과 테스트가 빠져 있으면 일부 리팩토링 판단을 미뤄야 하므로, PR과 함께 현재 미해결 항목(결정 필요 포인트)과 테스트 계획을 명확히 제시하면 리뷰 속도와 질이 더 좋아집니다. 짧은 동기화 미팅에서 핵심 쟁점을 빠르게 합의해 두는 것도 추천합니다.",\n  "next_reflection_mission": "팀 리뷰 후 받은 피드백을 분류해(예: 구조·네이밍·테스트) 공통 패턴 3가지를 찾아 다음 번 정리에 반영하고 그 변화를 기록하라.",\n  "anchoring_message": "문서 한 줄이 다음 개발자의 수십 분을 절약한다."\n}	2026-03-09 07:28:29.928228+00	2026-03-09 07:28:29.928228+00
4	1	2026-03-08	#### 오늘 한 일\n\n- [CHK-DAILY-005] organize source 1772956561955\n\n#### 수행 목적\n\n-\n\n#### 하이라이트\n\n-\n\n#### 로우라이트\n\n-\n\n#### 내일의 우선순위\n\n-\n\n#### 오늘 내가 팀에 기여한 가치\n\n-\n\n#### 오늘의 배움 또는 남길 말\n\n-\n\n#### 헬스 체크 (10점)\n\n-	\N	{\n  "total_score": 19,\n  "scores": {\n    "record_completeness": {\n      "score": 4,\n      "max_score": 15\n    },\n    "learning_signal_detection": {\n      "score": 4,\n      "max_score": 25\n    },\n    "cause_effect_connection": {\n      "score": 1,\n      "max_score": 20\n    },\n    "action_translation": {\n      "score": 3,\n      "max_score": 20\n    },\n    "learning_attitude_consistency": {\n      "score": 7,\n      "max_score": 20\n    }\n  },\n  "key_learning": "먼저 ‘무엇을 했는지’와 ‘하루의 핵심 배움’을 최소한으로라도 구조화해 적는 습관이 있어야 다음 행동으로 연결된다.",\n  "learning_sources": [\n    "highlight",\n    "lowlight",\n    "emotion",\n    "energy",\n    "decision"\n  ],\n  "playbook_relation": {\n    "related_playbook_item": "초기 일일 회고 템플릿 및 작성 가이드",\n    "relation_type": "extend",\n    "playbook_insight": "현재 회고가 거의 비어 있어, 일일 회고의 최소 입력 항목(목적, 성과/증거, 한 가지 배움, 다음 행동)을 명확히 제시하는 초기 플레이북이 필요하다. 짧고 반복 가능한 포맷이 효과적이다."\n  },\n  "playbook_update_markdown": "## 일일 회고 - 최소 템플릿\\n\\n목적: 매일 회고를 꾸준히 남기게 하기 위한 최소 입력 항목과 작성 가이드\\n\\n### 필수 입력 (5분 내 작성 권장)\\n- 오늘 한 일 (한 줄로): 수행한 핵심 작업을 간결히 적는다. 예: \\"소스 정리 - 모듈 X 리팩토링, 커밋 abc123\\"\\n- 수행 목적 (한 줄): 왜 했는지, 기대한 효과\\n- 성과/증거 (한 줄): 결과나 출력물(커밋, 파일, 링크, 시간 등)\\n- 핵심 배움 (한 문장): 오늘 얻은 통찰 또는 다음에 바꿀 점\\n- 다음 행동 (한 문장): 내일/다음에 구체적으로 할 일 1개\\n\\n### 권장 작성 원칙\\n- 시간 제한: 5~10분 내 작성 — 완벽함보다 지속성을 우선\\n- 한 문장 규칙: 각 항목은 가능하면 한 문장으로 정리\\n- 증거 중심: 성과에는 가능한 한 결과(커밋 해시, 파일명, 걸린 시간)를 적기\\n- 체크리스트: 하루 한 번 위 5개 항목을 채우는 것을 목표로 함\\n\\n### 예시\\n- 오늘 한 일: organize source 1772956561955 (리팩토링, 불필요 코드 제거)\\n- 수행 목적: 빌드 시간 단축 및 가독성 향상\\n- 성과/증거: 모듈 A 정리, 커밋 abc123, 빌드 시간 3% 단축\\n- 핵심 배움: 작은 리팩토링도 증거(벤치마크)가 있어야 효과를 확실히 알 수 있다\\n- 다음 행동: 내일은 변경 전/후 빌드 시간을 정량화해 기록하기\\n\\n### 운영 팁\\n- 회고가 빈칸일 경우: 먼저 '오늘 한 일'과 '다음 행동' 두 항목만이라도 채우게 독려\\n- 일주일 단위로 패턴을 확인: 반복되는 문제는 별도 액션 아이템으로 승격\\n\\n",\n  "next_action": "지금 바로 오늘 진행한 'organize source 1772956561955'의 목적(why), 결과(what/증거), 그리고 내일 할 한 가지를 10분 안에 한 줄씩 채워보자.",\n  "mentor_comment": "오늘은 최소한의 기록만 남겼지만 그 자체가 출발점입니다. 회고의 목적은 완벽한 글쓰기보다 반복 가능한 습관을 만드는 것입니다. '무엇을 했는지'와 '다음 행동' 두 줄만 매일 채워도 성장의 방향을 잡는 데 큰 도움이 됩니다. 다음엔 성과의 증거(커밋, 파일명, 소요시간 중 하나)를 꼭 붙여 보세요. 그래야 원인과 결과를 연결해 더 구체적인 배움을 얻을 수 있습니다.",\n  "next_reflection_mission": "다음 회고에서는 오늘 한 작업의 목적(why), 결과(증거 what), 그리고 내일의 한 가지 구체 행동을 반드시 채워서 제출해 보세요.",\n  "anchoring_message": "작은 기록 한 줄이 다음 행동을 만든다."\n}	2026-03-08 07:53:39.781731+00	2026-03-08 07:53:39.781731+00
3	1	2026-02-18	[CHK-DAILY-008] seeded 1773033217022	\N	\N	2026-03-08 02:45:13.155752+00	2026-03-08 02:45:13.155752+00
6	6	2026-02-18	[CHK-DAILY-008] seeded 1772978162449	\N	\N	2026-03-08 13:00:11.447673+00	2026-03-08 13:00:11.447673+00
5	6	2026-02-19	[CHK-DAILY-007] cancel source 1772975601209	\N	{\n  "total_score": 6,\n  "scores": {\n    "record_completeness": {\n      "score": 2,\n      "max_score": 15\n    },\n    "learning_signal_detection": {\n      "score": 1,\n      "max_score": 25\n    },\n    "cause_effect_connection": {\n      "score": 0,\n      "max_score": 20\n    },\n    "action_translation": {\n      "score": 0,\n      "max_score": 20\n    },\n    "learning_attitude_consistency": {\n      "score": 3,\n      "max_score": 20\n    }\n  },\n  "key_learning": "참조(피드백 소스)를 기록한 시도는 있었지만 맥락과 다음 행동이 빠져 있어, '기록'을 '학습'으로 바꾸려면 최소한 요약과 다음 행동을 항상 함께 적어야 한다.",\n  "learning_sources": [\n    "highlight",\n    "lowlight",\n    "decision"\n  ],\n  "playbook_relation": {\n    "related_playbook_item": "",\n    "relation_type": "none",\n    "playbook_insight": "아직 개인용 가이드가 없어 오늘의 기록은 포맷 부재로 맥락을 잃었다. 기본 템플릿을 도입하면 같은 시도라도 학습으로 연결되기 쉬워진다."\n  },\n  "playbook_update_markdown": "### Daily Feedback Log - 최소 템플릿\\n- id: (ex. 1772975573176)\\n- 작성시간: YYYY-MM-DD HH:MM\\n- 요약(한 문장): 피드백의 핵심 내용 한 줄\\n- 왜 중요한가(한 문장): 이 피드백이 나에게 주는 의미\\n- 감정/에너지: 받은 즉시의 감정(예: 당황/안도/무관심)과 에너지(높음/보통/낮음)\\n- 즉시 할 행동(1개): 다음에 내가 당장 할 구체적 행동\\n- 추적일(선택): follow-up을 확인할 날짜\\n\\n지침:\\n- 매번 최소 '요약'과 '즉시 할 행동'을 반드시 작성한다.\\n- 시간이 부족하면 한 줄 요약만이라도 남기고, 24시간 내에 행동 항목을 추가한다.",\n  "next_action": "이 피드백 기록에 대해 한 문장 요약과 당장 할 행동 하나를 추가로 적어보자.",\n  "mentor_comment": "참조 번호를 남긴 건 좋은 습관의 시작이야 — 기록하려는 의지가 보인다. 다만 지금 상태는 '메모'에 머물러 있어. 그 메모를 학습으로 바꾸려면 '이게 왜 중요한지'와 '다음에 무엇을 할지'를 함께 적는 연습이 필요해. 다음엔 간단한 템플릿(요약+다음 행동)으로 한 번만 더 작성해보자. 그렇게 하면 작은 기록들이 쌓여 의미 있는 개선으로 이어질 거야.",\n  "next_reflection_mission": "오늘 적어둔 피드백의 핵심을 한 문장으로 요약하고, 그걸 바탕으로 24시간 내 할 행동 한 가지를 적어오세요.",\n  "anchoring_message": "기록은 시작, 요약과 다음 행동이 비로소 학습을 만든다."\n}	2026-03-08 13:00:05.190457+00	2026-03-08 13:00:05.190457+00
7	3	2026-03-09	[E2E-PROF-STUDENT-DAILY] 2026-03-09	\N	\N	2026-03-09 04:54:55.673932+00	2026-03-09 04:54:55.673932+00
9	8	2026-03-09	SRCH012-1773042229467 클릭 이동 테스트 내용	\N	\N	2026-03-09 07:38:29.60248+00	2026-03-09 07:38:29.60248+00
10	8	2026-02-19	[CHK-DAILY-002] seed 1773043189619	\N	\N	2026-03-09 07:59:12.984749+00	2026-03-09 07:59:12.984749+00
2	1	2026-02-19	[CHK-DAILY-007] cancel source 1773033213433	\N	{\n  "total_score": 8,\n  "scores": {\n    "record_completeness": {\n      "score": 3,\n      "max_score": 15\n    },\n    "learning_signal_detection": {\n      "score": 1,\n      "max_score": 25\n    },\n    "cause_effect_connection": {\n      "score": 0,\n      "max_score": 20\n    },\n    "action_translation": {\n      "score": 0,\n      "max_score": 20\n    },\n    "learning_attitude_consistency": {\n      "score": 4,\n      "max_score": 20\n    }\n  },\n  "key_learning": "A recorded label by itself doesn't become learning — capture the feedback content, its context, and a concrete next step to turn notes into improvement.",\n  "learning_sources": [\n    "lowlight",\n    "decision",\n    "energy"\n  ],\n  "playbook_relation": {\n    "related_playbook_item": "",\n    "relation_type": "none",\n    "playbook_insight": "There is no existing personal guidance saved yet; starting with a simple reflection template will make future entries useful and actionable."\n  },\n  "playbook_update_markdown": "## Reflection Entry Template\\n\\nPurpose: Make each quick log turn into a usable learning asset.\\n\\nFields:\\n- id: (auto) unique id / timestamp\\n- title: one-line summary of the note\\n- source: who or what gave the feedback\\n- context: 1–2 sentences describing situation\\n- content: the actual feedback / observation (quote if possible)\\n- immediate reaction: how you felt or what you thought in one sentence\\n- implication: what this means for your goals/product/behavior\\n- next_action: one concrete next step you will take within 48 hours\\n- confidence/priority: low/medium/high\\n- tags: e.g., user-feedback / investor / task / bug\\n\\nGuidelines:\\n- If an entry is shorter than 3 fields filled, prompt: \\"Can you add: who, what, next step?\\"\\n- Encourage adding the entry within 10 minutes of the event while memory is fresh.\\n- For feedback items, capture at least one concrete action to test the insight.\\n",\n  "next_action": "Open the original feedback source and write a 3-sentence summary: what was said, why it matters, and one concrete next step to test/respond.",\n  "mentor_comment": "Good that you logged the item — the habit of capturing signals is the first step. Right now the entry is too brief to act on. Next time, write down who gave the feedback, the exact point made (or a short quote), why it matters for your current goal, and one specific follow-up you can test within a couple of days. That will turn a label into learning.",\n  "next_reflection_mission": "For your next entry, capture: (1) source of the feedback, (2) exact content in one sentence, (3) one experiment you'll run in response.",\n  "anchoring_message": "A short label remembers an event; context and a next step turn it into growth."\n}	2026-03-08 02:43:50.249472+00	2026-03-08 02:43:50.249472+00
\.


--
-- Data for Name: notification_settings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notification_settings (user_id, notify_post_author, notify_mentions, notify_participants, created_at, updated_at) FROM stdin;
7	t	t	t	2026-03-09 11:42:22.126528+00	2026-03-09 11:42:22.126528+00
4	t	t	t	2026-03-09 11:42:22.126528+00	2026-03-09 11:42:22.126528+00
5	t	t	t	2026-03-09 11:42:22.126528+00	2026-03-09 11:42:22.126528+00
6	t	t	t	2026-03-09 11:42:22.126528+00	2026-03-09 11:42:22.126528+00
8	t	t	t	2026-03-09 11:42:22.126528+00	2026-03-09 11:42:22.126528+00
1	t	t	t	2026-03-09 11:42:22.126528+00	2026-03-09 11:42:22.126528+00
2	t	t	t	2026-03-09 11:42:22.126528+00	2026-03-09 11:42:22.126528+00
3	t	t	t	2026-03-09 11:42:22.126528+00	2026-03-09 11:42:22.126528+00
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notifications (id, user_id, actor_user_id, type, daily_snippet_id, weekly_snippet_id, comment_id, is_read, read_at, dedupe_key, created_at) FROM stdin;
1	3	2	comment_on_my_snippet	\N	1	1	f	\N	comment:1:recipient:3:type:comment_on_my_snippet	2026-03-08 02:44:50.913871+00
2	3	2	comment_on_my_snippet	\N	1	2	f	\N	comment:2:recipient:3:type:comment_on_my_snippet	2026-03-08 02:50:02.345683+00
3	3	2	comment_on_my_snippet	\N	1	3	f	\N	comment:3:recipient:3:type:comment_on_my_snippet	2026-03-08 12:53:35.778595+00
4	3	2	comment_on_my_snippet	\N	1	4	f	\N	comment:4:recipient:3:type:comment_on_my_snippet	2026-03-08 12:59:44.05793+00
5	3	2	comment_on_my_snippet	\N	1	5	f	\N	comment:5:recipient:3:type:comment_on_my_snippet	2026-03-08 13:11:54.846234+00
6	3	2	comment_on_my_snippet	\N	6	6	f	\N	comment:6:recipient:3:type:comment_on_my_snippet	2026-03-09 04:55:04.663913+00
7	3	2	comment_on_my_snippet	\N	6	7	f	\N	comment:7:recipient:3:type:comment_on_my_snippet	2026-03-09 04:57:32.295979+00
8	3	2	comment_on_my_snippet	\N	6	8	f	\N	comment:8:recipient:3:type:comment_on_my_snippet	2026-03-09 04:59:32.160103+00
9	3	2	comment_on_my_snippet	\N	6	9	f	\N	comment:9:recipient:3:type:comment_on_my_snippet	2026-03-09 07:31:25.430099+00
10	3	2	comment_on_my_snippet	\N	6	10	f	\N	comment:10:recipient:3:type:comment_on_my_snippet	2026-03-09 07:33:45.860897+00
11	8	2	comment_on_my_snippet	\N	7	11	f	\N	comment:11:recipient:8:type:comment_on_my_snippet	2026-03-09 07:41:21.48753+00
\.


--
-- Data for Name: peer_evaluation_session_members; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.peer_evaluation_session_members (id, session_id, student_user_id, team_label, created_at) FROM stdin;
12	14	1	1조	2026-03-10 04:44:38.679597+00
13	14	8	1조	2026-03-10 04:44:38.679597+00
14	14	5	1조	2026-03-10 04:44:38.679597+00
\.


--
-- Data for Name: peer_evaluation_sessions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.peer_evaluation_sessions (id, title, professor_user_id, is_open, access_token, created_at, updated_at) FROM stdin;
14	rrr	1	t	DAVUvzmwrt1ykamGQMHvk0vIy1tJ1qcd	2026-03-10 04:44:21.169123+00	2026-03-10 04:44:21.169123+00
\.


--
-- Data for Name: peer_evaluation_submissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.peer_evaluation_submissions (id, session_id, evaluator_user_id, evaluatee_user_id, contribution_percent, fit_yes_no, created_at, updated_at) FROM stdin;
12	14	1	1	34	t	2026-03-10 04:46:08.56833+00	2026-03-10 04:46:08.56833+00
13	14	1	5	33	t	2026-03-10 04:46:08.56833+00	2026-03-10 04:46:08.56833+00
14	14	1	8	33	t	2026-03-10 04:46:08.56833+00	2026-03-10 04:46:08.56833+00
\.


--
-- Data for Name: role_assignment_rules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.role_assignment_rules (id, rule_type, rule_value, assigned_role, priority, is_active, created_at) FROM stdin;
3	email_list	{"emails": ["namjookim@gachon.ac.kr"]}	admin	10	t	2026-03-06 06:55:35.832383+00
4	email_pattern	{"pattern": "%@gachon.ac.kr"}	가천대학교	100	t	2026-03-06 06:55:35.832383+00
5	email_list	{"emails": ["test@gachon.ac.kr"]}	가천대학교	100	t	2026-03-08 12:59:30.724678+00
1	email_list	{"emails": ["namjookim@gachon.ac.kr"]}	gcs	20	t	2026-03-06 06:55:35.832383+00
2	email_list	{"emails": ["namjookim@gachon.ac.kr"]}	교수	30	t	2026-03-06 06:55:35.832383+00
\.


--
-- Data for Name: route_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.route_permissions (id, path, method, is_public, roles) FROM stdin;
1	/openapi.json	GET	t	[]
2	/openapi.json	HEAD	t	[]
3	/docs	GET	t	[]
4	/docs	HEAD	t	[]
5	/docs/oauth2-redirect	GET	t	[]
6	/docs/oauth2-redirect	HEAD	t	[]
7	/redoc	GET	t	[]
8	/redoc	HEAD	t	[]
9	/auth/google/login	GET	t	[]
10	/auth/google/callback	GET	t	[]
11	/auth/csrf	GET	f	["gcs", "\\uad50\\uc218", "admin"]
12	/auth/logout	POST	f	["gcs", "\\uad50\\uc218", "admin"]
13	/auth/me	GET	f	["gcs", "\\uad50\\uc218", "admin", "\\uac00\\ucc9c\\ub300\\ud559\\uad50"]
14	/terms	GET	t	[]
15	/consents	POST	f	["gcs", "\\uad50\\uc218", "admin"]
16	/auth/tokens	GET	f	["gcs", "\\uad50\\uc218", "admin"]
17	/auth/tokens	POST	f	["gcs", "\\uad50\\uc218", "admin"]
18	/auth/tokens/{token_id}	DELETE	f	["gcs", "\\uad50\\uc218", "admin"]
19	/teams/me	GET	f	["gcs", "\\uad50\\uc218", "admin"]
20	/teams	POST	f	["gcs", "\\uad50\\uc218", "admin"]
21	/teams/join	POST	f	["gcs", "\\uad50\\uc218", "admin"]
22	/teams/leave	POST	f	["gcs", "\\uad50\\uc218", "admin"]
23	/teams/me	PATCH	f	["gcs", "\\uad50\\uc218", "admin"]
24	/teams/me/league	PATCH	f	["gcs", "\\uad50\\uc218", "admin"]
25	/users/me/league	GET	f	["gcs", "\\uad50\\uc218", "admin"]
26	/users/me/league	PATCH	f	["gcs", "\\uad50\\uc218", "admin"]
27	/leaderboards	GET	f	["gcs", "\\uad50\\uc218", "admin"]
28	/achievements/me	GET	f	["gcs", "\\uad50\\uc218", "admin"]
29	/achievements/recent	GET	f	["gcs", "\\uad50\\uc218", "admin"]
30	/snippet_date	GET	f	["gcs", "\\uad50\\uc218", "admin"]
31	/daily-snippets/page-data	GET	f	["gcs", "\\uad50\\uc218", "admin"]
32	/daily-snippets/{snippet_id:int}	GET	f	["gcs", "\\uad50\\uc218", "admin"]
33	/daily-snippets	GET	f	["gcs", "\\uad50\\uc218", "admin"]
34	/daily-snippets	POST	f	["gcs", "\\uad50\\uc218", "admin"]
35	/daily-snippets/organize	POST	f	["gcs", "\\uad50\\uc218", "admin"]
36	/daily-snippets/feedback	GET	f	["gcs", "\\uad50\\uc218", "admin"]
37	/daily-snippets/{snippet_id:int}	PUT	f	["gcs", "\\uad50\\uc218", "admin"]
38	/daily-snippets/{snippet_id:int}	DELETE	f	["gcs", "\\uad50\\uc218", "admin"]
39	/weekly-snippets/page-data	GET	f	["gcs", "\\uad50\\uc218", "admin"]
40	/weekly-snippets/{snippet_id:int}	GET	f	["gcs", "\\uad50\\uc218", "admin"]
41	/weekly-snippets	GET	f	["gcs", "\\uad50\\uc218", "admin"]
42	/weekly-snippets	POST	f	["gcs", "\\uad50\\uc218", "admin"]
43	/weekly-snippets/organize	POST	f	["gcs", "\\uad50\\uc218", "admin"]
44	/weekly-snippets/feedback	GET	f	["gcs", "\\uad50\\uc218", "admin"]
45	/weekly-snippets/{snippet_id:int}	PUT	f	["gcs", "\\uad50\\uc218", "admin"]
46	/weekly-snippets/{snippet_id:int}	DELETE	f	["gcs", "\\uad50\\uc218", "admin"]
47	/comments	POST	f	["gcs", "\\uad50\\uc218", "admin"]
48	/comments	GET	f	["gcs", "\\uad50\\uc218", "admin"]
49	/comments/{comment_id}	PUT	f	["gcs", "\\uad50\\uc218", "admin"]
50	/comments/{comment_id}	DELETE	f	["gcs", "\\uad50\\uc218", "admin"]
51	/notifications	GET	f	["gcs", "\\uad50\\uc218", "admin"]
52	/notifications/{notification_id}/read	PATCH	f	["gcs", "\\uad50\\uc218", "admin"]
53	/notifications/read-all	PATCH	f	["gcs", "\\uad50\\uc218", "admin"]
54	/notifications/unread-count	GET	f	["gcs", "\\uad50\\uc218", "admin"]
55	/notifications/settings	GET	f	["gcs", "\\uad50\\uc218", "admin"]
56	/notifications/settings	PATCH	f	["gcs", "\\uad50\\uc218", "admin"]
57	/notifications/sse	GET	f	["gcs", "\\uad50\\uc218", "admin"]
58	/mcp	GET	f	["gcs", "\\uad50\\uc218", "admin"]
59	/mcp	POST	f	["gcs", "\\uad50\\uc218", "admin"]
60	/mcp	DELETE	f	["gcs", "\\uad50\\uc218", "admin"]
61	/mcp	HEAD	f	["gcs", "\\uad50\\uc218", "admin"]
62	/professor/overview	GET	f	["gcs", "\\uad50\\uc218", "admin"]
63	/professor/risk-queue	GET	f	["gcs", "\\uad50\\uc218", "admin"]
64	/professor/students/{user_id}/risk-history	GET	f	["gcs", "\\uad50\\uc218", "admin"]
65	/professor/students/{user_id}/risk-evaluate	POST	f	["gcs", "\\uad50\\uc218", "admin"]
66	/peer-evaluations/sessions	POST	f	["gcs", "\\uad50\\uc218", "admin"]
67	/peer-evaluations/sessions/{session_id}/members:parse	POST	f	["gcs", "\\uad50\\uc218", "admin"]
68	/peer-evaluations/sessions/{session_id}/members:confirm	POST	f	["gcs", "\\uad50\\uc218", "admin"]
69	/peer-evaluations/sessions/{session_id}	GET	f	["gcs", "\\uad50\\uc218", "admin"]
70	/peer-evaluations/sessions/{session_id}/results	GET	f	["gcs", "\\uad50\\uc218", "admin"]
71	/peer-evaluations/forms/{token}	GET	f	["gcs", "\\uad50\\uc218", "admin"]
72	/peer-evaluations/forms/{token}/submit	POST	f	["gcs", "\\uad50\\uc218", "admin"]
73	/peer-evaluations/forms/{token}/my-summary	GET	f	["gcs", "\\uad50\\uc218", "admin"]
\.


--
-- Data for Name: student_risk_snapshots; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.student_risk_snapshots (id, user_id, evaluated_at, l1, l2, l3, risk_score, risk_band, confidence, reasons_json, tone_policy_json, daily_subscores_json, weekly_subscores_json, trend_subscores_json, needs_professor_review, created_at) FROM stdin;
1	3	2026-03-08 02:37:51.168135+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 02:37:51.168135+00
2	3	2026-03-08 02:44:16.590643+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 02:44:16.590643+00
3	3	2026-03-08 02:44:18.785212+00	70	65	13.67	48.42	Medium	{"score": 0.281, "data_coverage": 0.0, "signal_agreement": 0.4367, "history_depth": 0.75}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.6734}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6835, "m_relapse_rate": 0.0}	f	2026-03-08 02:44:18.785212+00
4	3	2026-03-08 02:44:45.761161+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 02:44:45.761161+00
5	3	2026-03-08 02:44:47.349998+00	70	65	24.5	51.78	Medium	{"score": 0.3635, "data_coverage": 0.0, "signal_agreement": 0.545, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7022}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.725, "m_relapse_rate": 1.0}	f	2026-03-08 02:44:47.349998+00
6	3	2026-03-08 02:44:48.287816+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 02:44:48.287816+00
7	3	2026-03-08 02:44:52.872662+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 02:44:52.872662+00
8	3	2026-03-08 02:49:56.551827+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 02:49:56.551827+00
16	3	2026-03-08 12:50:45.162516+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 12:50:45.162516+00
9	4	2026-03-08 02:49:58.140064+00	70	65	0	43.87	Medium	{"score": 0.14, "data_coverage": 0.0, "signal_agreement": 0.3, "history_depth": 0.25}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.624}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.0, "m_relapse_rate": 0.0}	f	2026-03-08 02:49:58.140064+00
10	4	2026-03-08 02:49:58.140725+00	70	65	0	43.87	Medium	{"score": 0.14, "data_coverage": 0.0, "signal_agreement": 0.3, "history_depth": 0.25}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.624}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.0, "m_relapse_rate": 0.0}	f	2026-03-08 02:49:58.140725+00
11	3	2026-03-08 02:49:58.699255+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-08 02:49:58.699255+00
12	3	2026-03-08 02:49:59.606972+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 02:49:59.606972+00
13	3	2026-03-08 02:50:04.332668+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 02:50:04.332668+00
14	3	2026-03-08 05:34:15.375425+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 05:34:15.375425+00
15	3	2026-03-08 12:48:59.541716+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 12:48:59.541716+00
17	3	2026-03-08 12:53:25.272049+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 12:53:25.272049+00
18	5	2026-03-08 12:53:30.772204+00	70	65	0	43.87	Medium	{"score": 0.14, "data_coverage": 0.0, "signal_agreement": 0.3, "history_depth": 0.25}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.624}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.0, "m_relapse_rate": 0.0}	f	2026-03-08 12:53:30.772204+00
19	5	2026-03-08 12:53:30.771553+00	70	65	0	43.87	Medium	{"score": 0.14, "data_coverage": 0.0, "signal_agreement": 0.3, "history_depth": 0.25}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.624}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.0, "m_relapse_rate": 0.0}	f	2026-03-08 12:53:30.771553+00
20	6	2026-03-08 12:53:30.944806+00	70	65	0	43.87	Medium	{"score": 0.14, "data_coverage": 0.0, "signal_agreement": 0.3, "history_depth": 0.25}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.624}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.0, "m_relapse_rate": 0.0}	f	2026-03-08 12:53:30.944806+00
21	6	2026-03-08 12:53:30.969763+00	70	65	0	44.27	Medium	{"score": 0.19, "data_coverage": 0.0, "signal_agreement": 0.3, "history_depth": 0.5}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.6415}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.0, "m_relapse_rate": 0.0}	f	2026-03-08 12:53:30.969763+00
37	3	2026-03-09 04:55:06.764036+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 04:55:06.764036+00
22	3	2026-03-08 12:53:31.773459+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-08 12:53:31.773459+00
23	3	2026-03-08 12:53:32.722928+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 12:53:32.722928+00
24	3	2026-03-08 12:53:37.820141+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 12:53:37.820141+00
25	3	2026-03-08 12:59:38.361071+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 12:59:38.361071+00
26	3	2026-03-08 12:59:40.06666+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-08 12:59:40.06666+00
27	3	2026-03-08 12:59:41.109744+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 12:59:41.109744+00
28	3	2026-03-08 12:59:46.106266+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 12:59:46.106266+00
29	3	2026-03-08 13:11:48.734053+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 13:11:48.734053+00
30	3	2026-03-08 13:11:51.014987+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-08 13:11:51.014987+00
31	3	2026-03-08 13:11:52.032796+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 13:11:52.032796+00
32	3	2026-03-08 13:11:56.805721+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-08 13:11:56.805721+00
33	3	2026-03-09 04:54:55.673932+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 04:54:55.673932+00
34	7	2026-03-09 04:54:59.384095+00	70	65	0	43.87	Medium	{"score": 0.14, "data_coverage": 0.0, "signal_agreement": 0.3, "history_depth": 0.25}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.624}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.0, "m_relapse_rate": 0.0}	f	2026-03-09 04:54:59.384095+00
35	3	2026-03-09 04:55:00.485048+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-09 04:55:00.485048+00
36	3	2026-03-09 04:55:01.633475+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 04:55:01.633475+00
38	3	2026-03-09 04:57:24.007163+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 04:57:24.007163+00
39	3	2026-03-09 04:57:28.093962+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-09 04:57:28.093962+00
40	3	2026-03-09 04:57:29.261529+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 04:57:29.261529+00
41	3	2026-03-09 04:57:34.468933+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 04:57:34.468933+00
42	3	2026-03-09 04:59:25.357223+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 04:59:25.357223+00
43	3	2026-03-09 04:59:27.975326+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-09 04:59:27.975326+00
44	3	2026-03-09 04:59:29.099776+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 04:59:29.099776+00
45	3	2026-03-09 04:59:34.29168+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 04:59:34.29168+00
46	3	2026-03-09 05:07:38.05138+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 05:07:38.05138+00
47	3	2026-03-09 05:11:35.278019+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 05:11:35.278019+00
48	3	2026-03-09 05:11:37.99169+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-09 05:11:37.99169+00
49	3	2026-03-09 05:11:55.173893+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 05:11:55.173893+00
50	3	2026-03-09 05:15:09.941837+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 05:15:09.941837+00
51	3	2026-03-09 05:15:16.511078+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 05:15:16.511078+00
52	3	2026-03-09 05:15:18.602757+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-09 05:15:18.602757+00
53	3	2026-03-09 05:15:22.991633+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 05:15:22.991633+00
54	3	2026-03-09 05:15:25.166913+00	70	65	24.5	51.78	Medium	{"score": 0.3635, "data_coverage": 0.0, "signal_agreement": 0.545, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7022}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.725, "m_relapse_rate": 1.0}	f	2026-03-09 05:15:25.166913+00
55	3	2026-03-09 05:15:29.597557+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 05:15:29.597557+00
56	3	2026-03-09 05:15:31.700418+00	70	65	24.5	51.78	Medium	{"score": 0.3635, "data_coverage": 0.0, "signal_agreement": 0.545, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7022}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.725, "m_relapse_rate": 1.0}	f	2026-03-09 05:15:31.700418+00
57	3	2026-03-09 05:15:35.94928+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 05:15:35.94928+00
58	3	2026-03-09 07:13:18.599359+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:13:18.599359+00
59	3	2026-03-09 07:31:18.910624+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:31:18.910624+00
60	3	2026-03-09 07:31:21.315214+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-09 07:31:21.315214+00
61	3	2026-03-09 07:31:22.363539+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:31:22.363539+00
62	3	2026-03-09 07:31:27.672989+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:31:27.672989+00
63	3	2026-03-09 07:33:39.806717+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:33:39.806717+00
64	8	2026-03-09 07:33:40.990948+00	70	65	0	43.87	Medium	{"score": 0.14, "data_coverage": 0.0, "signal_agreement": 0.3, "history_depth": 0.25}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.624}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.0, "m_relapse_rate": 0.0}	f	2026-03-09 07:33:40.990948+00
65	8	2026-03-09 07:33:40.99112+00	70	65	0	43.87	Medium	{"score": 0.14, "data_coverage": 0.0, "signal_agreement": 0.3, "history_depth": 0.25}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.624}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.0, "m_relapse_rate": 0.0}	f	2026-03-09 07:33:40.99112+00
66	3	2026-03-09 07:33:41.670099+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-09 07:33:41.670099+00
67	3	2026-03-09 07:33:42.776581+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:33:42.776581+00
68	3	2026-03-09 07:33:48.064923+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:33:48.064923+00
69	3	2026-03-09 07:38:18.59512+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:38:18.59512+00
70	3	2026-03-09 07:40:37.284751+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:40:37.284751+00
71	3	2026-03-09 07:40:39.495334+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-09 07:40:39.495334+00
72	3	2026-03-09 07:41:16.261552+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:41:16.261552+00
73	3	2026-03-09 07:41:17.934795+00	70	65	24.5	51.78	Medium	{"score": 0.3635, "data_coverage": 0.0, "signal_agreement": 0.545, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7022}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.725, "m_relapse_rate": 1.0}	f	2026-03-09 07:41:17.934795+00
74	3	2026-03-09 07:41:19.131359+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:41:19.131359+00
75	3	2026-03-09 07:41:23.772192+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:41:23.772192+00
76	3	2026-03-09 07:43:27.437206+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:43:27.437206+00
77	3	2026-03-09 07:43:30.781861+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-09 07:43:30.781861+00
78	3	2026-03-09 07:48:55.845317+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:48:55.845317+00
79	3	2026-03-09 07:51:34.65648+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:51:34.65648+00
80	3	2026-03-09 07:53:36.598832+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:53:36.598832+00
81	3	2026-03-09 07:53:39.24296+00	70	65	22.56	51.25	Medium	{"score": 0.3577, "data_coverage": 0.0, "signal_agreement": 0.5256, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7002}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.6279, "m_relapse_rate": 1.0}	f	2026-03-09 07:53:39.24296+00
82	3	2026-03-09 07:53:40.302446+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:53:40.302446+00
83	3	2026-03-09 07:58:59.129534+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 07:58:59.129534+00
84	3	2026-03-09 07:59:03.749363+00	70	65	24.5	51.78	Medium	{"score": 0.3635, "data_coverage": 0.0, "signal_agreement": 0.545, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7022}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.725, "m_relapse_rate": 1.0}	f	2026-03-09 07:59:03.749363+00
85	3	2026-03-09 08:04:22.531429+00	92	94	88	93.5	Critical	{"score": 0.95, "data_coverage": 0.9, "signal_agreement": 0.97, "history_depth": 0.9}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action"], "severity": "high", "impact": 18.5, "evidence": "E2E seeded high risk actionability issue", "why_it_matters": "E2E seeded reason"}]	{"primary": "\\uc9c8\\ubb38", "secondary": ["\\uc81c\\uc548"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P5_strategy_mismatch"], "policy_confidence": 0.9}	{"rubric_risk": 0.9}	{"weekly_rubric_risk": 0.92}	{"m_trend_accel": 0.8}	t	2026-03-09 08:04:22.531429+00
86	3	2026-03-09 08:04:27.116842+00	70	65	24.5	51.78	Medium	{"score": 0.3635, "data_coverage": 0.0, "signal_agreement": 0.545, "history_depth": 1.0}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L3", "risk_factor": "RF9_trend_relapse", "prompt_items": ["\\uc8fc\\ucc28\\ubcc4 L2 \\uc774\\ub825"], "severity": "medium", "impact": 10.0, "evidence": "\\ucd5c\\uadfc \\uc8fc\\ucc28\\uc5d0\\uc11c \\uc704\\ud5d8\\ub3c4 \\uc545\\ud654 \\uac00\\uc18d \\ub610\\ub294 \\uc7ac\\ubc1c \\uc2e0\\ud638\\uac00 \\uad00\\ucc30\\ub429\\ub2c8\\ub2e4.", "why_it_matters": "\\ucd94\\uc138 \\uc545\\ud654\\ub294 \\ub2e8\\uae30 \\uac1c\\uc785 \\uc9c0\\uc5f0 \\uc2dc \\uc774\\ud0c8\\ub85c \\uc774\\uc5b4\\uc9c8 \\uac00\\ub2a5\\uc131\\uc774 \\ud07d\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.7022}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.725, "m_relapse_rate": 1.0}	f	2026-03-09 08:04:27.116842+00
87	2	2026-03-10 13:56:43.504967+00	70	65	0	43.87	Medium	{"score": 0.14, "data_coverage": 0.0, "signal_agreement": 0.3, "history_depth": 0.25}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.624}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.0, "m_relapse_rate": 0.0}	f	2026-03-10 13:56:43.504967+00
88	2	2026-03-10 13:56:43.516631+00	70	65	0	43.87	Medium	{"score": 0.14, "data_coverage": 0.0, "signal_agreement": 0.3, "history_depth": 0.25}	[{"layer": "L2", "risk_factor": "RF4_actionability", "prompt_items": ["action_translation", "next_action", "\\ub2e4\\uc74c\\uc8fc \\uc8fc\\uc694 \\ud560 \\uc77c"], "severity": "high", "impact": 28.6, "evidence": "\\ud68c\\uace0\\uac00 \\ub2e4\\uc74c \\uc2e4\\ud589\\uc73c\\ub85c \\ucda9\\ubd84\\ud788 \\uc5f0\\uacb0\\ub418\\uc9c0 \\uc54a\\uc558\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\ud589\\ub3d9 \\uc804\\ud658\\uc774 \\uc57d\\ud558\\uba74 \\ud559\\uc2b5 \\uc2e0\\ud638\\uac00 \\ub204\\uc801\\ub418\\uc9c0 \\uc54a\\uc2b5\\ub2c8\\ub2e4."}, {"layer": "L2", "risk_factor": "RF8_strategy_drift", "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"], "severity": "high", "impact": 24.0, "evidence": "\\uc804\\ub7b5 \\uc7ac\\uc815\\ub82c \\uc2e0\\ud638\\uac00 \\ubc18\\ubcf5\\ub418\\uace0 \\uc788\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc804\\ub7b5 \\ubd88\\uc77c\\uce58\\uac00 \\ub204\\uc801\\ub418\\uba74 \\uc2e4\\ud589 \\uc2e4\\ud328 \\ud655\\ub960\\uc774 \\uc99d\\uac00\\ud569\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF1_execution_continuity", "prompt_items": ["record_completeness"], "severity": "high", "impact": 19.6, "evidence": "\\uc77c\\uac04 \\uae30\\ub85d \\uc644\\uc131\\ub3c4 \\ub610\\ub294 \\uad6c\\uc870 \\uacb0\\uc190 \\ube44\\uc728\\uc774 \\ub192\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uae30\\ub85d \\uc5f0\\uc18d\\uc131\\uc774 \\uae68\\uc9c0\\uba74 \\ud68c\\ubcf5 \\ub8e8\\ud2f4\\uc774 \\uc57d\\ud574\\uc9d1\\ub2c8\\ub2e4."}, {"layer": "L1", "risk_factor": "RF7_affective_strain", "prompt_items": ["learning_sources", "\\ud5ec\\uc2a4 \\uccb4\\ud06c (10\\uc810)", "emotion", "energy"], "severity": "low", "impact": 3.0, "evidence": "\\uc815\\uc11c/\\uc5d0\\ub108\\uc9c0 \\uc800\\ud558\\uc640 \\ucee8\\ub514\\uc158 \\ud558\\ub77d \\uc2e0\\ud638\\uac00 \\uac10\\uc9c0\\ub418\\uc5c8\\uc2b5\\ub2c8\\ub2e4.", "why_it_matters": "\\uc815\\uc11c\\uc801 \\ubd80\\ub2f4\\uc774 \\ucee4\\uc9c0\\uba74 \\uc2e4\\ud589 \\uc9c0\\uc18d\\uc131\\uc774 \\uae09\\uaca9\\ud788 \\ub0ae\\uc544\\uc9c8 \\uc218 \\uc788\\uc2b5\\ub2c8\\ub2e4."}]	{"primary": "\\uaca9\\ub824", "secondary": ["\\uc9c8\\ubb38"], "suppressed": ["\\ud6c8\\uacc4"], "trigger_patterns": ["P3_affective_strain"], "policy_confidence": 0.624}	{"rubric_risk": 0.7, "m_daily_structure_gap": 1.0, "m_frequency_gap": 1.0, "m_affective_strain": 0.6}	{"weekly_rubric_risk": 0.65, "m_strategy_drift": 0.8, "m_action_carryover": 0.7, "m_daily_instability": 0.6}	{"m_trend_accel": 0.0, "m_trend_slope_4w": 0.0, "m_trend_volatility": 0.0, "m_relapse_rate": 0.0}	f	2026-03-10 13:56:43.516631+00
\.


--
-- Data for Name: teams; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.teams (id, name, invite_code, league_type, created_at) FROM stdin;
1	E2E Professor Student Team	GK10RP3L	none	2026-03-08 02:37:51.168135+00
\.


--
-- Data for Name: terms; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.terms (id, type, version, content, is_required, is_active, created_at) FROM stdin;
1	privacy	v1.0	This is the privacy policy...	t	t	2026-03-06 06:55:32.253974+00
2	tos	v1.0	These are the terms of service...	t	t	2026-03-06 06:55:32.253974+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, email, name, picture, created_at, roles, league_type, team_id) FROM stdin;
2	e2e-professor@gachon.ac.kr	E2E Professor		2026-03-08 02:37:50.213083+00	["\\uac00\\ucc9c\\ub300\\ud559\\uad50"]	none	\N
6	test@gachon.ac.kr	E2E Test User		2026-03-08 12:53:19.745812+00	["\\uac00\\ucc9c\\ub300\\ud559\\uad50"]	none	\N
8	professor@gachon.ac.kr	가천 교수		2026-03-09 07:33:34.419308+00	["\\uac00\\ucc9c\\ub300\\ud559\\uad50"]	none	\N
1	namjookim@gachon.ac.kr	김남주/스타트업칼리지	https://lh3.googleusercontent.com/a/ACg8ocI7UD41rxbdFXI9NU4CyTyOWHEqsgA4xU9d31YxvxJ2xC0d99Y=s96-c	2026-03-08 02:37:43.331754+00	["admin", "gcs", "\\uad50\\uc218", "\\uac00\\ucc9c\\ub300\\ud559\\uad50"]	none	\N
9	e2e-professor-peer@gachon.ac.kr	E2E Peer Professor		2026-03-10 06:27:03.966591+00	["gcs"]	none	\N
7	bypass@example.com	Bypass User		2026-03-09 04:54:48.794338+00	["user"]	none	\N
5	test@example.com	Test User		2026-03-08 07:52:55.228812+00	["gcs"]	none	\N
4	e2e-outsider@example.com	E2E Outsider		2026-03-08 02:44:51.862658+00	["user"]	none	\N
3	e2e-prof-student@gachon.ac.kr	E2E Professor Student		2026-03-08 02:37:51.067324+00	["\\uac00\\ucc9c\\ub300\\ud559\\uad50"]	none	1
\.


--
-- Data for Name: weekly_snippets; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.weekly_snippets (id, user_id, week, content, playbook, feedback, created_at, updated_at) FROM stdin;
1	3	2026-03-02	[E2E-PROF-STUDENT-WEEKLY] 2026-03-02	\N	\N	2026-03-08 02:37:51.168135+00	2026-03-08 02:37:51.168135+00
6	3	2026-03-09	[E2E-PROF-STUDENT-WEEKLY] 2026-03-09	\N	\N	2026-03-09 04:54:55.673932+00	2026-03-09 04:54:55.673932+00
7	8	2026-03-09	SRCH009-1773042225532 주간 전용 내용	\N	\N	2026-03-09 07:38:31.688246+00	2026-03-09 07:38:31.688246+00
3	6	2026-02-16	[CHK-WEEKLY-007] seeded 1772978013278	\N	{\n  "total_score": 17,\n  "scores": {\n    "record_completeness": {\n      "score": 3,\n      "max_score": 15\n    },\n    "learning_signal_detection": {\n      "score": 4,\n      "max_score": 25\n    },\n    "cause_effect_connection": {\n      "score": 2,\n      "max_score": 20\n    },\n    "action_translation": {\n      "score": 5,\n      "max_score": 20\n    },\n    "learning_attitude_consistency": {\n      "score": 3,\n      "max_score": 20\n    }\n  },\n  "key_learning": "이번 주 기록은 'feedback source 1772975646902'라는 식별자만 남아 있어 실질적인 학습 신호가 거의 없음. 현재 할 일은 피드백 원문을 확보하고 구조화하여 유의미한 인사이트로 바꾸는 것.",\n  "next_action": "1) 해당 피드백 소스(아이디)를 열어 원문을 다운로드 또는 복사한다. 2) 피드백의 메타데이터(작성자·채널·일시)를 기록한다. 3) 원문을 읽고 간단 요약(한 문장)과 핵심 문구(인용)를 뽑는다. 4) 주제 태그(예: UX, 가격, 기능 결함, 요청)와 감정(긍정·중립·부정)을 표시한다. 5) 영향도(빈도 또는 심각성) 기준으로 상위 3가지 문제를 선정한다. 6) 각 문제에 대해 가능한 원인 가설과 우선 실험/수정 액션을 정한다. 7) 다음 미팅까지 진행 담당자와 완료 기한을 설정한다.",\n  "mentor_comment": "기록 자체가 너무 간단해서 분석이 불가능합니다. 우선 피드백 원문 확보가 급선무예요. 기술적 문제가 아니라 프로세스 문제(피드백을 수집·정리하는 루틴 부재)로 보입니다. 이번 주 목표는 '피드백을 읽고 요약·분류하여 우선순위 3개를 도출하는 것'으로 잡고, 그 결과를 다음 회고에서 공유하세요. 필요하면 제가 피드백 요약 양식과 우선순위 매트릭스를 만들어 드릴게요.",\n  "next_reflection_mission": "다음 회고 전까지 해당 소스의 원문 피드백 1건 이상을 완전히 처리(원문, 요약, 태그, 감정, 영향도, 제안 액션)하여 제출하세요. 각 처리 항목은 5분 내로 읽고 요약할 수 있게 간결하게 작성할 것.",\n  "anchoring_message": "증거(피드백 원문)를 모아라. 데이터가 있으면 해답이 보입니다 — 작은 루틴으로 시작하면 개선은 따라옵니다.",\n  "strategy_linkage": {\n    "current_strategy": "피드백 수집의 초기 식별 단계(소스 ID만 파악된 상태)",\n    "weekly_signal": "피드백 소스만 확인됨 — 내용과 맥락 부재",\n    "recommended_shift": "소스 식별 → 원문 확보 → 요약·분류 → 영향도 기반 우선순위 설정 → 실행 가설 수립 및 실험",\n    "confidence": "medium"\n  },\n  "playbook_update_markdown": "## 피드백 인테이크 플레이북(초안)\\n\\n### 목적\\n피드백 소스가 식별되었을 때 빠르게 원문을 확보하고, 정량·정성적으로 분류해 우선순위를 매겨 실행으로 연결하기 위함.\\n\\n### 필수 필드(피드백 항목마다 기록)\\n- 소스 ID/링크\\n- 채널(예: 이메일, 인터뷰, 고객지원 티켓)\\n- 작성자(익명 가능)\\n- 수집일시\\n- 원문\\n- 한줄 요약(핵심 메시지)\\n- 핵심 인용(가능하면 그대로 복사)\\n- 태그(기능, UX, 가격, 성능, 기타)\\n- 감정(긍정/중립/부정)\\n- 영향도(높음/중간/낮음)\\n- 제안 액션(짧게)\\n- 담당자와 기한\\n\\n### 분석 체크리스트(5분 요약용)\\n1. 이 피드백은 어떤 문제를 지적하는가? (한 문장)\\n2. 문제의 빈도나 심각성은 어느 정도인가? (숫자/직관)\\n3. 즉시 시행 가능한 개선 조치는 무엇인가? (최대 3개)\\n4. 검증 방법(측정 지표)은 무엇인가?\\n\\n### 우선순위 기준(간단 매트릭스)\\n- 심각도(고·중·저) × 빈도(빈번·가끔·한번) → 합산 점수로 상위 3개 선정\\n\\n### 운영 규칙\\n- 피드백이 들어오면 48시간 이내에 인테이크 폼을 채운다.\\n- 주 1회 피드백 회의에서 상위 3개를 선정하고 실행 계획을 세운다.\\n- 실행 후 2주 내 결과(지표 변화)를 리뷰한다.\\n\\n### 템플릿(복사해서 사용)\\n- 소스 ID: \\n- 채널: \\n- 날짜: \\n- 원문: \\n- 요약: \\n- 태그: \\n- 감정: \\n- 영향도: \\n- 제안 액션: \\n- 담당자/기한:\\n\\n(이 초안을 기반으로 다음 회고에서 실제 피드백 하나를 넣어 테스트해 보고, 개선 포인트를 반영해 플레이북을 고도화합시다.)"\n}	2026-03-08 13:01:25.084337+00	2026-03-08 13:01:25.084337+00
4	6	2026-02-09	[CHK-WEEKLY-007] seeded 1772978165157	\N	\N	2026-03-08 13:54:03.107549+00	2026-03-08 13:54:03.107549+00
8	8	2026-02-16	[CHK-WEEKLY-002] seed 1773043200497	\N	\N	2026-03-09 07:59:15.125823+00	2026-03-09 07:59:15.125823+00
2	1	2026-02-16	[CHK-WEEKLY-006] feedback source 1773033258059	\N	{\n  "total_score": 14,\n  "scores": {\n    "record_completeness": {\n      "score": 2,\n      "max_score": 15\n    },\n    "learning_signal_detection": {\n      "score": 3,\n      "max_score": 25\n    },\n    "cause_effect_connection": {\n      "score": 2,\n      "max_score": 20\n    },\n    "action_translation": {\n      "score": 2,\n      "max_score": 20\n    },\n    "learning_attitude_consistency": {\n      "score": 5,\n      "max_score": 20\n    }\n  },\n  "key_learning": "기록이 너무 빈약하여 학습 신호를 추출할 수 없음. 'feedback source 1773033258059'는 피드백 존재를 가리키지만 내용·맥락·출처·시점·감정·권장조치가 빠져 있어 다음 행동으로 연결되지 않음.",\n  "next_action": "원본 피드백을 즉시 찾아 완전한 텍스트를 기록하라. 다음 항목을 채워라: (1) 수신자/발신자, (2) 날짜·채널, (3) 원문 요약(한 문장), (4) 핵심 불만·요구·아이디어, (5) 감정(긍정/중립/부정), (6) 우선순위(높음/중간/낮음), (7) 권장 대응(담당자·기한). 피드백이 없다면 출처 ID를 어떻게 얻었는지 기록하라. 완료 후 30분 내로 스냅샷을 공유하라.",\n  "mentor_comment": "잘 시작하셨습니다—피드백 기록 자체를 남긴 것은 긍정적 신호입니다. 다만 학습과 실행으로 연결하려면 표준화된 항목으로 기록해야 합니다. 짧은 습관(원본 붙여넣기 + 1분 메타데이터 작성)을 만들면 다음 회고에서 의미 있는 패턴을 추출할 수 있습니다. 아래 제시한 템플릿을 이번 주 바로 적용해보세요.",\n  "next_reflection_mission": "이번 주 내에 동일한 템플릿으로 최소 3건의 피드백을 정리하고, 공통된 문제(최대 2개)를 도출하라. 각 문제에 대해 가설 2개를 세우고 우선순위가 높은 가설 1개를 다음주에 검증할 작은 실험(목표·가설·측정지표·기간)을 설계하라.",\n  "anchoring_message": "피드백은 기록으로부터 실행으로 연결될 때 비로소 성장 자원이 됩니다. 작은 습관으로 기록을 표준화하세요.",\n  "strategy_linkage": {\n    "current_strategy": "기록/플레이북 미구축 — 피드백 원천만 식별됨",\n    "weekly_signal": "피드백 존재표시만 있고 세부내용 부재 → 실행전환 불가",\n    "recommended_shift": "피드백을 즉시 표준 템플릿으로 캡쳐하고 분류·우선순위화하여 구체적 대응계획으로 연결",\n    "confidence": "medium"\n  },\n  "playbook_update_markdown": "제안: '피드백 캡처 및 회고' 모듈 추가\\n\\n목표: 피드백을 빠르게 구조화하여 실행가능한 인사이트로 전환\\n\\n피드백 템플릿(매 피드백에 적용)\\n- id: (자동생성 또는 출처ID)\\n- 수신자/발신자:\\n- 날짜/채널:\\n- 원문 요약(1문장):\\n- 핵심 이슈/요구/아이디어(핵심어):\\n- 감정/톤(긍정/중립/부정):\\n- 영향도(높음/중/낮음):\\n- 권장 대응(담당자 · 기한 · 우선순위):\\n- 상태(신규/검토중/실행중/완료)\\n\\n주간 루틴\\n1) 피드백 발생 시 24시간 내 템플릿 채움(원문 붙여넣기 필수)\\n2) 주간 회고에서 최소 3건 이상 분류·패턴화\\n3) 패턴별 가설 2개 작성 및 우선순위 지정\\n4) 우선가설 1개에 대한 1주 단위 실험 설계·실행·측정\\n\\n도구 팁\\n- 간단한 구글 시트 또는 노션 데이터베이스로 템플릿 구현\\n- 슬랙/이메일 연동으로 자동 id·채널 기록\\n\\n적용 체크리스트(다음 주 검증용)\\n- 이번 주 템플릿으로 3건 이상 기록했는가?\\n- 각 항목에 담당자와 기한이 정해졌는가?\\n- 패턴·가설·실험이 명확히 정의되었는가?\\n\\n(짧고 반복 가능한 습관이 장기적 학습을 만듭니다.)"\n}	2026-03-08 02:44:03.949153+00	2026-03-08 02:44:03.949153+00
5	1	2026-02-09	[CHK-WEEKLY-007] seeded 1773033290967	\N	\N	2026-03-08 14:26:38.423715+00	2026-03-08 14:26:38.423715+00
\.


--
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: realtime; Owner: -
--

COPY realtime.schema_migrations (version, inserted_at) FROM stdin;
20211116024918	2026-02-13 00:06:58
20211116045059	2026-02-13 00:06:59
20211116050929	2026-02-13 00:07:00
20211116051442	2026-02-13 00:07:00
20211116212300	2026-02-13 00:07:01
20211116213355	2026-02-13 00:07:02
20211116213934	2026-02-13 00:07:03
20211116214523	2026-02-13 00:07:04
20211122062447	2026-02-13 00:07:04
20211124070109	2026-02-13 00:07:05
20211202204204	2026-02-13 00:07:06
20211202204605	2026-02-13 00:07:06
20211210212804	2026-02-13 00:07:09
20211228014915	2026-02-13 00:07:09
20220107221237	2026-02-13 00:07:10
20220228202821	2026-02-13 00:07:11
20220312004840	2026-02-13 00:07:11
20220603231003	2026-02-13 00:07:12
20220603232444	2026-02-13 00:07:13
20220615214548	2026-02-13 00:07:14
20220712093339	2026-02-13 00:07:15
20220908172859	2026-02-13 00:07:15
20220916233421	2026-02-13 00:07:16
20230119133233	2026-02-13 00:07:17
20230128025114	2026-02-13 00:07:18
20230128025212	2026-02-13 00:07:18
20230227211149	2026-02-13 00:07:19
20230228184745	2026-02-13 00:07:20
20230308225145	2026-02-13 00:07:20
20230328144023	2026-02-13 00:07:21
20231018144023	2026-02-13 00:07:22
20231204144023	2026-02-13 00:07:23
20231204144024	2026-02-13 00:07:24
20231204144025	2026-02-13 00:07:24
20240108234812	2026-02-13 00:07:25
20240109165339	2026-02-13 00:07:26
20240227174441	2026-02-13 00:07:27
20240311171622	2026-02-13 00:07:28
20240321100241	2026-02-13 00:07:29
20240401105812	2026-02-13 00:07:31
20240418121054	2026-02-13 00:07:32
20240523004032	2026-02-13 00:07:35
20240618124746	2026-02-13 00:07:35
20240801235015	2026-02-13 00:07:36
20240805133720	2026-02-13 00:07:37
20240827160934	2026-02-13 00:07:37
20240919163303	2026-02-13 00:07:38
20240919163305	2026-02-13 00:07:39
20241019105805	2026-02-13 00:07:40
20241030150047	2026-02-13 00:07:42
20241108114728	2026-02-13 00:07:43
20241121104152	2026-02-13 00:07:44
20241130184212	2026-02-13 00:07:45
20241220035512	2026-02-13 00:07:45
20241220123912	2026-02-13 00:07:46
20241224161212	2026-02-13 00:07:47
20250107150512	2026-02-13 00:07:47
20250110162412	2026-02-13 00:07:48
20250123174212	2026-02-13 00:07:49
20250128220012	2026-02-13 00:07:49
20250506224012	2026-02-13 00:07:50
20250523164012	2026-02-13 00:07:51
20250714121412	2026-02-13 00:07:51
20250905041441	2026-02-13 00:07:52
20251103001201	2026-02-13 00:07:53
20251120212548	2026-02-13 00:07:54
20251120215549	2026-02-13 00:07:54
20260218120000	2026-03-03 02:26:32
\.


--
-- Data for Name: subscription; Type: TABLE DATA; Schema: realtime; Owner: -
--

COPY realtime.subscription (id, subscription_id, entity, filters, claims, created_at, action_filter) FROM stdin;
\.


--
-- Data for Name: buckets; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.buckets (id, name, owner, created_at, updated_at, public, avif_autodetection, file_size_limit, allowed_mime_types, owner_id, type) FROM stdin;
\.


--
-- Data for Name: buckets_analytics; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.buckets_analytics (name, type, format, created_at, updated_at, id, deleted_at) FROM stdin;
\.


--
-- Data for Name: buckets_vectors; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.buckets_vectors (id, type, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: migrations; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.migrations (id, name, hash, executed_at) FROM stdin;
0	create-migrations-table	e18db593bcde2aca2a408c4d1100f6abba2195df	2026-02-13 00:09:14.062032
1	initialmigration	6ab16121fbaa08bbd11b712d05f358f9b555d777	2026-02-13 00:09:14.069889
2	storage-schema	f6a1fa2c93cbcd16d4e487b362e45fca157a8dbd	2026-02-13 00:09:14.077568
3	pathtoken-column	2cb1b0004b817b29d5b0a971af16bafeede4b70d	2026-02-13 00:09:14.092912
4	add-migrations-rls	427c5b63fe1c5937495d9c635c263ee7a5905058	2026-02-13 00:09:14.101693
5	add-size-functions	79e081a1455b63666c1294a440f8ad4b1e6a7f84	2026-02-13 00:09:14.106866
6	change-column-name-in-get-size	ded78e2f1b5d7e616117897e6443a925965b30d2	2026-02-13 00:09:14.112515
7	add-rls-to-buckets	e7e7f86adbc51049f341dfe8d30256c1abca17aa	2026-02-13 00:09:14.117989
8	add-public-to-buckets	fd670db39ed65f9d08b01db09d6202503ca2bab3	2026-02-13 00:09:14.123304
9	fix-search-function	af597a1b590c70519b464a4ab3be54490712796b	2026-02-13 00:09:14.128537
10	search-files-search-function	b595f05e92f7e91211af1bbfe9c6a13bb3391e16	2026-02-13 00:09:14.133787
11	add-trigger-to-auto-update-updated_at-column	7425bdb14366d1739fa8a18c83100636d74dcaa2	2026-02-13 00:09:14.139357
12	add-automatic-avif-detection-flag	8e92e1266eb29518b6a4c5313ab8f29dd0d08df9	2026-02-13 00:09:14.144861
13	add-bucket-custom-limits	cce962054138135cd9a8c4bcd531598684b25e7d	2026-02-13 00:09:14.149863
14	use-bytes-for-max-size	941c41b346f9802b411f06f30e972ad4744dad27	2026-02-13 00:09:14.155027
15	add-can-insert-object-function	934146bc38ead475f4ef4b555c524ee5d66799e5	2026-02-13 00:09:14.177124
16	add-version	76debf38d3fd07dcfc747ca49096457d95b1221b	2026-02-13 00:09:14.182384
17	drop-owner-foreign-key	f1cbb288f1b7a4c1eb8c38504b80ae2a0153d101	2026-02-13 00:09:14.18744
18	add_owner_id_column_deprecate_owner	e7a511b379110b08e2f214be852c35414749fe66	2026-02-13 00:09:14.192444
19	alter-default-value-objects-id	02e5e22a78626187e00d173dc45f58fa66a4f043	2026-02-13 00:09:14.200931
20	list-objects-with-delimiter	cd694ae708e51ba82bf012bba00caf4f3b6393b7	2026-02-13 00:09:14.206015
21	s3-multipart-uploads	8c804d4a566c40cd1e4cc5b3725a664a9303657f	2026-02-13 00:09:14.212804
22	s3-multipart-uploads-big-ints	9737dc258d2397953c9953d9b86920b8be0cdb73	2026-02-13 00:09:14.225087
23	optimize-search-function	9d7e604cddc4b56a5422dc68c9313f4a1b6f132c	2026-02-13 00:09:14.236344
24	operation-function	8312e37c2bf9e76bbe841aa5fda889206d2bf8aa	2026-02-13 00:09:14.241656
25	custom-metadata	d974c6057c3db1c1f847afa0e291e6165693b990	2026-02-13 00:09:14.246914
26	objects-prefixes	215cabcb7f78121892a5a2037a09fedf9a1ae322	2026-02-13 00:09:14.252198
27	search-v2	859ba38092ac96eb3964d83bf53ccc0b141663a6	2026-02-13 00:09:14.256871
28	object-bucket-name-sorting	c73a2b5b5d4041e39705814fd3a1b95502d38ce4	2026-02-13 00:09:14.261456
29	create-prefixes	ad2c1207f76703d11a9f9007f821620017a66c21	2026-02-13 00:09:14.266227
30	update-object-levels	2be814ff05c8252fdfdc7cfb4b7f5c7e17f0bed6	2026-02-13 00:09:14.270875
31	objects-level-index	b40367c14c3440ec75f19bbce2d71e914ddd3da0	2026-02-13 00:09:14.275646
32	backward-compatible-index-on-objects	e0c37182b0f7aee3efd823298fb3c76f1042c0f7	2026-02-13 00:09:14.28055
33	backward-compatible-index-on-prefixes	b480e99ed951e0900f033ec4eb34b5bdcb4e3d49	2026-02-13 00:09:14.285321
34	optimize-search-function-v1	ca80a3dc7bfef894df17108785ce29a7fc8ee456	2026-02-13 00:09:14.290072
35	add-insert-trigger-prefixes	458fe0ffd07ec53f5e3ce9df51bfdf4861929ccc	2026-02-13 00:09:14.294978
36	optimise-existing-functions	6ae5fca6af5c55abe95369cd4f93985d1814ca8f	2026-02-13 00:09:14.299739
37	add-bucket-name-length-trigger	3944135b4e3e8b22d6d4cbb568fe3b0b51df15c1	2026-02-13 00:09:14.304728
38	iceberg-catalog-flag-on-buckets	02716b81ceec9705aed84aa1501657095b32e5c5	2026-02-13 00:09:14.310836
39	add-search-v2-sort-support	6706c5f2928846abee18461279799ad12b279b78	2026-02-13 00:09:14.321468
40	fix-prefix-race-conditions-optimized	7ad69982ae2d372b21f48fc4829ae9752c518f6b	2026-02-13 00:09:14.326329
41	add-object-level-update-trigger	07fcf1a22165849b7a029deed059ffcde08d1ae0	2026-02-13 00:09:14.331061
42	rollback-prefix-triggers	771479077764adc09e2ea2043eb627503c034cd4	2026-02-13 00:09:14.337515
43	fix-object-level	84b35d6caca9d937478ad8a797491f38b8c2979f	2026-02-13 00:09:14.342421
44	vector-bucket-type	99c20c0ffd52bb1ff1f32fb992f3b351e3ef8fb3	2026-02-13 00:09:14.349818
45	vector-buckets	049e27196d77a7cb76497a85afae669d8b230953	2026-02-13 00:09:14.35882
46	buckets-objects-grants	fedeb96d60fefd8e02ab3ded9fbde05632f84aed	2026-02-13 00:09:14.372675
47	iceberg-table-metadata	649df56855c24d8b36dd4cc1aeb8251aa9ad42c2	2026-02-13 00:09:14.379021
48	iceberg-catalog-ids	e0e8b460c609b9999ccd0df9ad14294613eed939	2026-02-13 00:09:14.384314
49	buckets-objects-grants-postgres	072b1195d0d5a2f888af6b2302a1938dd94b8b3d	2026-02-13 00:09:14.400403
50	search-v2-optimised	6323ac4f850aa14e7387eb32102869578b5bd478	2026-02-13 00:09:14.406616
51	index-backward-compatible-search	2ee395d433f76e38bcd3856debaf6e0e5b674011	2026-02-13 00:09:14.484085
52	drop-not-used-indexes-and-functions	5cc44c8696749ac11dd0dc37f2a3802075f3a171	2026-02-13 00:09:14.486259
53	drop-index-lower-name	d0cb18777d9e2a98ebe0bc5cc7a42e57ebe41854	2026-02-13 00:09:14.497292
54	drop-index-object-level	6289e048b1472da17c31a7eba1ded625a6457e67	2026-02-13 00:09:14.500486
55	prevent-direct-deletes	262a4798d5e0f2e7c8970232e03ce8be695d5819	2026-02-13 00:09:14.502633
56	fix-optimized-search-function	cb58526ebc23048049fd5bf2fd148d18b04a2073	2026-02-13 00:09:14.508612
\.


--
-- Data for Name: objects; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.objects (id, bucket_id, name, owner, created_at, updated_at, last_accessed_at, metadata, version, owner_id, user_metadata) FROM stdin;
\.


--
-- Data for Name: s3_multipart_uploads; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.s3_multipart_uploads (id, in_progress_size, upload_signature, bucket_id, key, version, owner_id, created_at, user_metadata) FROM stdin;
\.


--
-- Data for Name: s3_multipart_uploads_parts; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.s3_multipart_uploads_parts (id, upload_id, size, part_number, bucket_id, key, etag, owner_id, version, created_at) FROM stdin;
\.


--
-- Data for Name: vector_indexes; Type: TABLE DATA; Schema: storage; Owner: -
--

COPY storage.vector_indexes (id, name, bucket_id, data_type, dimension, distance_metric, metadata_configuration, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: secrets; Type: TABLE DATA; Schema: vault; Owner: -
--

COPY vault.secrets (id, name, description, secret, key_id, nonce, created_at, updated_at) FROM stdin;
\.


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE SET; Schema: auth; Owner: -
--

SELECT pg_catalog.setval('auth.refresh_tokens_id_seq', 1, false);


--
-- Name: achievement_definitions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.achievement_definitions_id_seq', 15, true);


--
-- Name: achievement_grants_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.achievement_grants_id_seq', 3, true);


--
-- Name: api_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.api_tokens_id_seq', 16, true);


--
-- Name: comments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.comments_id_seq', 11, true);


--
-- Name: consents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.consents_id_seq', 44, true);


--
-- Name: daily_snippets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.daily_snippets_id_seq', 10, true);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notifications_id_seq', 11, true);


--
-- Name: peer_evaluation_session_members_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.peer_evaluation_session_members_id_seq', 20, true);


--
-- Name: peer_evaluation_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.peer_evaluation_sessions_id_seq', 19, true);


--
-- Name: peer_evaluation_submissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.peer_evaluation_submissions_id_seq', 14, true);


--
-- Name: role_assignment_rules_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.role_assignment_rules_id_seq', 5, true);


--
-- Name: route_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.route_permissions_id_seq', 73, true);


--
-- Name: student_risk_snapshots_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.student_risk_snapshots_id_seq', 88, true);


--
-- Name: teams_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.teams_id_seq', 35, true);


--
-- Name: terms_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.terms_id_seq', 6, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 9, true);


--
-- Name: weekly_snippets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.weekly_snippets_id_seq', 8, true);


--
-- Name: subscription_id_seq; Type: SEQUENCE SET; Schema: realtime; Owner: -
--

SELECT pg_catalog.setval('realtime.subscription_id_seq', 1, false);


--
-- Name: mfa_amr_claims amr_id_pk; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT amr_id_pk PRIMARY KEY (id);


--
-- Name: audit_log_entries audit_log_entries_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.audit_log_entries
    ADD CONSTRAINT audit_log_entries_pkey PRIMARY KEY (id);


--
-- Name: custom_oauth_providers custom_oauth_providers_identifier_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.custom_oauth_providers
    ADD CONSTRAINT custom_oauth_providers_identifier_key UNIQUE (identifier);


--
-- Name: custom_oauth_providers custom_oauth_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.custom_oauth_providers
    ADD CONSTRAINT custom_oauth_providers_pkey PRIMARY KEY (id);


--
-- Name: flow_state flow_state_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.flow_state
    ADD CONSTRAINT flow_state_pkey PRIMARY KEY (id);


--
-- Name: identities identities_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_pkey PRIMARY KEY (id);


--
-- Name: identities identities_provider_id_provider_unique; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_provider_id_provider_unique UNIQUE (provider_id, provider);


--
-- Name: instances instances_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.instances
    ADD CONSTRAINT instances_pkey PRIMARY KEY (id);


--
-- Name: mfa_amr_claims mfa_amr_claims_session_id_authentication_method_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT mfa_amr_claims_session_id_authentication_method_pkey UNIQUE (session_id, authentication_method);


--
-- Name: mfa_challenges mfa_challenges_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_challenges
    ADD CONSTRAINT mfa_challenges_pkey PRIMARY KEY (id);


--
-- Name: mfa_factors mfa_factors_last_challenged_at_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_last_challenged_at_key UNIQUE (last_challenged_at);


--
-- Name: mfa_factors mfa_factors_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_pkey PRIMARY KEY (id);


--
-- Name: oauth_authorizations oauth_authorizations_authorization_code_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_authorizations
    ADD CONSTRAINT oauth_authorizations_authorization_code_key UNIQUE (authorization_code);


--
-- Name: oauth_authorizations oauth_authorizations_authorization_id_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_authorizations
    ADD CONSTRAINT oauth_authorizations_authorization_id_key UNIQUE (authorization_id);


--
-- Name: oauth_authorizations oauth_authorizations_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_authorizations
    ADD CONSTRAINT oauth_authorizations_pkey PRIMARY KEY (id);


--
-- Name: oauth_client_states oauth_client_states_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_client_states
    ADD CONSTRAINT oauth_client_states_pkey PRIMARY KEY (id);


--
-- Name: oauth_clients oauth_clients_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_clients
    ADD CONSTRAINT oauth_clients_pkey PRIMARY KEY (id);


--
-- Name: oauth_consents oauth_consents_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_consents
    ADD CONSTRAINT oauth_consents_pkey PRIMARY KEY (id);


--
-- Name: oauth_consents oauth_consents_user_client_unique; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_consents
    ADD CONSTRAINT oauth_consents_user_client_unique UNIQUE (user_id, client_id);


--
-- Name: one_time_tokens one_time_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.one_time_tokens
    ADD CONSTRAINT one_time_tokens_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_token_unique; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_token_unique UNIQUE (token);


--
-- Name: saml_providers saml_providers_entity_id_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_entity_id_key UNIQUE (entity_id);


--
-- Name: saml_providers saml_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_pkey PRIMARY KEY (id);


--
-- Name: saml_relay_states saml_relay_states_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: sso_domains sso_domains_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sso_domains
    ADD CONSTRAINT sso_domains_pkey PRIMARY KEY (id);


--
-- Name: sso_providers sso_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sso_providers
    ADD CONSTRAINT sso_providers_pkey PRIMARY KEY (id);


--
-- Name: users users_phone_key; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_phone_key UNIQUE (phone);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: route_permissions _path_method_uc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.route_permissions
    ADD CONSTRAINT _path_method_uc UNIQUE (path, method);


--
-- Name: terms _type_version_uc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT _type_version_uc UNIQUE (type, version);


--
-- Name: daily_snippets _user_date_uc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_snippets
    ADD CONSTRAINT _user_date_uc UNIQUE (user_id, date);


--
-- Name: consents _user_term_uc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consents
    ADD CONSTRAINT _user_term_uc UNIQUE (user_id, term_id);


--
-- Name: weekly_snippets _user_week_uc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weekly_snippets
    ADD CONSTRAINT _user_week_uc UNIQUE (user_id, week);


--
-- Name: achievement_definitions achievement_definitions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.achievement_definitions
    ADD CONSTRAINT achievement_definitions_pkey PRIMARY KEY (id);


--
-- Name: achievement_grants achievement_grants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.achievement_grants
    ADD CONSTRAINT achievement_grants_pkey PRIMARY KEY (id);


--
-- Name: api_tokens api_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_tokens
    ADD CONSTRAINT api_tokens_pkey PRIMARY KEY (id);


--
-- Name: comments comments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_pkey PRIMARY KEY (id);


--
-- Name: consents consents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consents
    ADD CONSTRAINT consents_pkey PRIMARY KEY (id);


--
-- Name: daily_snippets daily_snippets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_snippets
    ADD CONSTRAINT daily_snippets_pkey PRIMARY KEY (id);


--
-- Name: notification_settings notification_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_settings
    ADD CONSTRAINT notification_settings_pkey PRIMARY KEY (user_id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: peer_evaluation_session_members peer_evaluation_session_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_session_members
    ADD CONSTRAINT peer_evaluation_session_members_pkey PRIMARY KEY (id);


--
-- Name: peer_evaluation_sessions peer_evaluation_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_sessions
    ADD CONSTRAINT peer_evaluation_sessions_pkey PRIMARY KEY (id);


--
-- Name: peer_evaluation_submissions peer_evaluation_submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_submissions
    ADD CONSTRAINT peer_evaluation_submissions_pkey PRIMARY KEY (id);


--
-- Name: role_assignment_rules role_assignment_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_assignment_rules
    ADD CONSTRAINT role_assignment_rules_pkey PRIMARY KEY (id);


--
-- Name: route_permissions route_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.route_permissions
    ADD CONSTRAINT route_permissions_pkey PRIMARY KEY (id);


--
-- Name: student_risk_snapshots student_risk_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_risk_snapshots
    ADD CONSTRAINT student_risk_snapshots_pkey PRIMARY KEY (id);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: terms terms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.terms
    ADD CONSTRAINT terms_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: api_tokens ux_api_token_user_id_idempotency_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_tokens
    ADD CONSTRAINT ux_api_token_user_id_idempotency_key UNIQUE (user_id, idempotency_key);


--
-- Name: notifications ux_notifications_dedupe_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT ux_notifications_dedupe_key UNIQUE (dedupe_key);


--
-- Name: peer_evaluation_session_members ux_peer_eval_session_member_session_student; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_session_members
    ADD CONSTRAINT ux_peer_eval_session_member_session_student UNIQUE (session_id, student_user_id);


--
-- Name: peer_evaluation_submissions ux_peer_eval_submission_session_evaluator_evaluatee; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_submissions
    ADD CONSTRAINT ux_peer_eval_submission_session_evaluator_evaluatee UNIQUE (session_id, evaluator_user_id, evaluatee_user_id);


--
-- Name: weekly_snippets weekly_snippets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weekly_snippets
    ADD CONSTRAINT weekly_snippets_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: realtime; Owner: -
--

ALTER TABLE ONLY realtime.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id, inserted_at);


--
-- Name: subscription pk_subscription; Type: CONSTRAINT; Schema: realtime; Owner: -
--

ALTER TABLE ONLY realtime.subscription
    ADD CONSTRAINT pk_subscription PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: realtime; Owner: -
--

ALTER TABLE ONLY realtime.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: buckets_analytics buckets_analytics_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.buckets_analytics
    ADD CONSTRAINT buckets_analytics_pkey PRIMARY KEY (id);


--
-- Name: buckets buckets_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.buckets
    ADD CONSTRAINT buckets_pkey PRIMARY KEY (id);


--
-- Name: buckets_vectors buckets_vectors_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.buckets_vectors
    ADD CONSTRAINT buckets_vectors_pkey PRIMARY KEY (id);


--
-- Name: migrations migrations_name_key; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.migrations
    ADD CONSTRAINT migrations_name_key UNIQUE (name);


--
-- Name: migrations migrations_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.migrations
    ADD CONSTRAINT migrations_pkey PRIMARY KEY (id);


--
-- Name: objects objects_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.objects
    ADD CONSTRAINT objects_pkey PRIMARY KEY (id);


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_pkey PRIMARY KEY (id);


--
-- Name: s3_multipart_uploads s3_multipart_uploads_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads
    ADD CONSTRAINT s3_multipart_uploads_pkey PRIMARY KEY (id);


--
-- Name: vector_indexes vector_indexes_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.vector_indexes
    ADD CONSTRAINT vector_indexes_pkey PRIMARY KEY (id);


--
-- Name: audit_logs_instance_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX audit_logs_instance_id_idx ON auth.audit_log_entries USING btree (instance_id);


--
-- Name: confirmation_token_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX confirmation_token_idx ON auth.users USING btree (confirmation_token) WHERE ((confirmation_token)::text !~ '^[0-9 ]*$'::text);


--
-- Name: custom_oauth_providers_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX custom_oauth_providers_created_at_idx ON auth.custom_oauth_providers USING btree (created_at);


--
-- Name: custom_oauth_providers_enabled_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX custom_oauth_providers_enabled_idx ON auth.custom_oauth_providers USING btree (enabled);


--
-- Name: custom_oauth_providers_identifier_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX custom_oauth_providers_identifier_idx ON auth.custom_oauth_providers USING btree (identifier);


--
-- Name: custom_oauth_providers_provider_type_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX custom_oauth_providers_provider_type_idx ON auth.custom_oauth_providers USING btree (provider_type);


--
-- Name: email_change_token_current_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX email_change_token_current_idx ON auth.users USING btree (email_change_token_current) WHERE ((email_change_token_current)::text !~ '^[0-9 ]*$'::text);


--
-- Name: email_change_token_new_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX email_change_token_new_idx ON auth.users USING btree (email_change_token_new) WHERE ((email_change_token_new)::text !~ '^[0-9 ]*$'::text);


--
-- Name: factor_id_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX factor_id_created_at_idx ON auth.mfa_factors USING btree (user_id, created_at);


--
-- Name: flow_state_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX flow_state_created_at_idx ON auth.flow_state USING btree (created_at DESC);


--
-- Name: identities_email_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX identities_email_idx ON auth.identities USING btree (email text_pattern_ops);


--
-- Name: INDEX identities_email_idx; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON INDEX auth.identities_email_idx IS 'Auth: Ensures indexed queries on the email column';


--
-- Name: identities_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX identities_user_id_idx ON auth.identities USING btree (user_id);


--
-- Name: idx_auth_code; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX idx_auth_code ON auth.flow_state USING btree (auth_code);


--
-- Name: idx_oauth_client_states_created_at; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX idx_oauth_client_states_created_at ON auth.oauth_client_states USING btree (created_at);


--
-- Name: idx_user_id_auth_method; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX idx_user_id_auth_method ON auth.flow_state USING btree (user_id, authentication_method);


--
-- Name: mfa_challenge_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX mfa_challenge_created_at_idx ON auth.mfa_challenges USING btree (created_at DESC);


--
-- Name: mfa_factors_user_friendly_name_unique; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX mfa_factors_user_friendly_name_unique ON auth.mfa_factors USING btree (friendly_name, user_id) WHERE (TRIM(BOTH FROM friendly_name) <> ''::text);


--
-- Name: mfa_factors_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX mfa_factors_user_id_idx ON auth.mfa_factors USING btree (user_id);


--
-- Name: oauth_auth_pending_exp_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX oauth_auth_pending_exp_idx ON auth.oauth_authorizations USING btree (expires_at) WHERE (status = 'pending'::auth.oauth_authorization_status);


--
-- Name: oauth_clients_deleted_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX oauth_clients_deleted_at_idx ON auth.oauth_clients USING btree (deleted_at);


--
-- Name: oauth_consents_active_client_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX oauth_consents_active_client_idx ON auth.oauth_consents USING btree (client_id) WHERE (revoked_at IS NULL);


--
-- Name: oauth_consents_active_user_client_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX oauth_consents_active_user_client_idx ON auth.oauth_consents USING btree (user_id, client_id) WHERE (revoked_at IS NULL);


--
-- Name: oauth_consents_user_order_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX oauth_consents_user_order_idx ON auth.oauth_consents USING btree (user_id, granted_at DESC);


--
-- Name: one_time_tokens_relates_to_hash_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX one_time_tokens_relates_to_hash_idx ON auth.one_time_tokens USING hash (relates_to);


--
-- Name: one_time_tokens_token_hash_hash_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX one_time_tokens_token_hash_hash_idx ON auth.one_time_tokens USING hash (token_hash);


--
-- Name: one_time_tokens_user_id_token_type_key; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX one_time_tokens_user_id_token_type_key ON auth.one_time_tokens USING btree (user_id, token_type);


--
-- Name: reauthentication_token_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX reauthentication_token_idx ON auth.users USING btree (reauthentication_token) WHERE ((reauthentication_token)::text !~ '^[0-9 ]*$'::text);


--
-- Name: recovery_token_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX recovery_token_idx ON auth.users USING btree (recovery_token) WHERE ((recovery_token)::text !~ '^[0-9 ]*$'::text);


--
-- Name: refresh_tokens_instance_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_instance_id_idx ON auth.refresh_tokens USING btree (instance_id);


--
-- Name: refresh_tokens_instance_id_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_instance_id_user_id_idx ON auth.refresh_tokens USING btree (instance_id, user_id);


--
-- Name: refresh_tokens_parent_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_parent_idx ON auth.refresh_tokens USING btree (parent);


--
-- Name: refresh_tokens_session_id_revoked_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_session_id_revoked_idx ON auth.refresh_tokens USING btree (session_id, revoked);


--
-- Name: refresh_tokens_updated_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX refresh_tokens_updated_at_idx ON auth.refresh_tokens USING btree (updated_at DESC);


--
-- Name: saml_providers_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX saml_providers_sso_provider_id_idx ON auth.saml_providers USING btree (sso_provider_id);


--
-- Name: saml_relay_states_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX saml_relay_states_created_at_idx ON auth.saml_relay_states USING btree (created_at DESC);


--
-- Name: saml_relay_states_for_email_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX saml_relay_states_for_email_idx ON auth.saml_relay_states USING btree (for_email);


--
-- Name: saml_relay_states_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX saml_relay_states_sso_provider_id_idx ON auth.saml_relay_states USING btree (sso_provider_id);


--
-- Name: sessions_not_after_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sessions_not_after_idx ON auth.sessions USING btree (not_after DESC);


--
-- Name: sessions_oauth_client_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sessions_oauth_client_id_idx ON auth.sessions USING btree (oauth_client_id);


--
-- Name: sessions_user_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sessions_user_id_idx ON auth.sessions USING btree (user_id);


--
-- Name: sso_domains_domain_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX sso_domains_domain_idx ON auth.sso_domains USING btree (lower(domain));


--
-- Name: sso_domains_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sso_domains_sso_provider_id_idx ON auth.sso_domains USING btree (sso_provider_id);


--
-- Name: sso_providers_resource_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX sso_providers_resource_id_idx ON auth.sso_providers USING btree (lower(resource_id));


--
-- Name: sso_providers_resource_id_pattern_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX sso_providers_resource_id_pattern_idx ON auth.sso_providers USING btree (resource_id text_pattern_ops);


--
-- Name: unique_phone_factor_per_user; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX unique_phone_factor_per_user ON auth.mfa_factors USING btree (user_id, phone);


--
-- Name: user_id_created_at_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX user_id_created_at_idx ON auth.sessions USING btree (user_id, created_at);


--
-- Name: users_email_partial_key; Type: INDEX; Schema: auth; Owner: -
--

CREATE UNIQUE INDEX users_email_partial_key ON auth.users USING btree (email) WHERE (is_sso_user = false);


--
-- Name: INDEX users_email_partial_key; Type: COMMENT; Schema: auth; Owner: -
--

COMMENT ON INDEX auth.users_email_partial_key IS 'Auth: A partial unique index that applies only when is_sso_user is false';


--
-- Name: users_instance_id_email_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX users_instance_id_email_idx ON auth.users USING btree (instance_id, lower((email)::text));


--
-- Name: users_instance_id_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX users_instance_id_idx ON auth.users USING btree (instance_id);


--
-- Name: users_is_anonymous_idx; Type: INDEX; Schema: auth; Owner: -
--

CREATE INDEX users_is_anonymous_idx ON auth.users USING btree (is_anonymous);


--
-- Name: ix_achievement_definitions_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_achievement_definitions_code ON public.achievement_definitions USING btree (code);


--
-- Name: ix_achievement_definitions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_achievement_definitions_id ON public.achievement_definitions USING btree (id);


--
-- Name: ix_achievement_definitions_is_public_announceable; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_achievement_definitions_is_public_announceable ON public.achievement_definitions USING btree (is_public_announceable);


--
-- Name: ix_achievement_grants_achievement_definition_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_achievement_grants_achievement_definition_id ON public.achievement_grants USING btree (achievement_definition_id);


--
-- Name: ix_achievement_grants_external_grant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_achievement_grants_external_grant_id ON public.achievement_grants USING btree (external_grant_id) WHERE (external_grant_id IS NOT NULL);


--
-- Name: ix_achievement_grants_granted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_achievement_grants_granted_at ON public.achievement_grants USING btree (granted_at);


--
-- Name: ix_achievement_grants_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_achievement_grants_id ON public.achievement_grants USING btree (id);


--
-- Name: ix_achievement_grants_publish_end_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_achievement_grants_publish_end_at ON public.achievement_grants USING btree (publish_end_at);


--
-- Name: ix_achievement_grants_publish_start_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_achievement_grants_publish_start_at ON public.achievement_grants USING btree (publish_start_at);


--
-- Name: ix_achievement_grants_publish_window; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_achievement_grants_publish_window ON public.achievement_grants USING btree (publish_start_at, publish_end_at);


--
-- Name: ix_achievement_grants_user_granted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_achievement_grants_user_granted_at ON public.achievement_grants USING btree (user_id, granted_at DESC);


--
-- Name: ix_achievement_grants_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_achievement_grants_user_id ON public.achievement_grants USING btree (user_id);


--
-- Name: ix_api_tokens_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_api_tokens_id ON public.api_tokens USING btree (id);


--
-- Name: ix_api_tokens_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_api_tokens_token_hash ON public.api_tokens USING btree (token_hash);


--
-- Name: ix_api_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_api_tokens_user_id ON public.api_tokens USING btree (user_id);


--
-- Name: ix_comments_comment_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_comments_comment_type ON public.comments USING btree (comment_type);


--
-- Name: ix_comments_daily_snippet_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_comments_daily_snippet_id ON public.comments USING btree (daily_snippet_id);


--
-- Name: ix_comments_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_comments_id ON public.comments USING btree (id);


--
-- Name: ix_comments_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_comments_user_id ON public.comments USING btree (user_id);


--
-- Name: ix_comments_weekly_snippet_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_comments_weekly_snippet_id ON public.comments USING btree (weekly_snippet_id);


--
-- Name: ix_consents_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_consents_id ON public.consents USING btree (id);


--
-- Name: ix_daily_snippets_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_daily_snippets_date ON public.daily_snippets USING btree (date);


--
-- Name: ix_daily_snippets_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_daily_snippets_id ON public.daily_snippets USING btree (id);


--
-- Name: ix_daily_snippets_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_daily_snippets_user_id ON public.daily_snippets USING btree (user_id);


--
-- Name: ix_notifications_actor_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_actor_user_id ON public.notifications USING btree (actor_user_id);


--
-- Name: ix_notifications_comment_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_comment_id ON public.notifications USING btree (comment_id);


--
-- Name: ix_notifications_daily_snippet_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_daily_snippet_id ON public.notifications USING btree (daily_snippet_id);


--
-- Name: ix_notifications_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_id ON public.notifications USING btree (id);


--
-- Name: ix_notifications_type_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_type_created_at ON public.notifications USING btree (type, created_at);


--
-- Name: ix_notifications_user_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_user_created_at ON public.notifications USING btree (user_id, created_at);


--
-- Name: ix_notifications_user_id_is_read_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_user_id_is_read_created_at ON public.notifications USING btree (user_id, is_read, created_at);


--
-- Name: ix_notifications_weekly_snippet_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_weekly_snippet_id ON public.notifications USING btree (weekly_snippet_id);


--
-- Name: ix_peer_eval_session_members_session_team; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peer_eval_session_members_session_team ON public.peer_evaluation_session_members USING btree (session_id, team_label);


--
-- Name: ix_peer_eval_submission_session_evaluatee; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peer_eval_submission_session_evaluatee ON public.peer_evaluation_submissions USING btree (session_id, evaluatee_user_id);


--
-- Name: ix_peer_eval_submission_session_evaluator; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peer_eval_submission_session_evaluator ON public.peer_evaluation_submissions USING btree (session_id, evaluator_user_id);


--
-- Name: ix_peer_evaluation_session_members_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peer_evaluation_session_members_id ON public.peer_evaluation_session_members USING btree (id);


--
-- Name: ix_peer_evaluation_session_members_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peer_evaluation_session_members_session_id ON public.peer_evaluation_session_members USING btree (session_id);


--
-- Name: ix_peer_evaluation_session_members_student_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peer_evaluation_session_members_student_user_id ON public.peer_evaluation_session_members USING btree (student_user_id);


--
-- Name: ix_peer_evaluation_sessions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peer_evaluation_sessions_id ON public.peer_evaluation_sessions USING btree (id);


--
-- Name: ix_peer_evaluation_sessions_professor_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peer_evaluation_sessions_professor_user_id ON public.peer_evaluation_sessions USING btree (professor_user_id);


--
-- Name: ix_peer_evaluation_submissions_evaluatee_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peer_evaluation_submissions_evaluatee_user_id ON public.peer_evaluation_submissions USING btree (evaluatee_user_id);


--
-- Name: ix_peer_evaluation_submissions_evaluator_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peer_evaluation_submissions_evaluator_user_id ON public.peer_evaluation_submissions USING btree (evaluator_user_id);


--
-- Name: ix_peer_evaluation_submissions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peer_evaluation_submissions_id ON public.peer_evaluation_submissions USING btree (id);


--
-- Name: ix_peer_evaluation_submissions_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peer_evaluation_submissions_session_id ON public.peer_evaluation_submissions USING btree (session_id);


--
-- Name: ix_role_assignment_rules_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_role_assignment_rules_id ON public.role_assignment_rules USING btree (id);


--
-- Name: ix_route_permissions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_route_permissions_id ON public.route_permissions USING btree (id);


--
-- Name: ix_student_risk_snapshots_band_score_evaluated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_risk_snapshots_band_score_evaluated_at ON public.student_risk_snapshots USING btree (risk_band, risk_score, evaluated_at);


--
-- Name: ix_student_risk_snapshots_evaluated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_risk_snapshots_evaluated_at ON public.student_risk_snapshots USING btree (evaluated_at);


--
-- Name: ix_student_risk_snapshots_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_risk_snapshots_id ON public.student_risk_snapshots USING btree (id);


--
-- Name: ix_student_risk_snapshots_risk_band; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_risk_snapshots_risk_band ON public.student_risk_snapshots USING btree (risk_band);


--
-- Name: ix_student_risk_snapshots_risk_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_risk_snapshots_risk_score ON public.student_risk_snapshots USING btree (risk_score);


--
-- Name: ix_student_risk_snapshots_user_evaluated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_risk_snapshots_user_evaluated_at ON public.student_risk_snapshots USING btree (user_id, evaluated_at);


--
-- Name: ix_student_risk_snapshots_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_risk_snapshots_user_id ON public.student_risk_snapshots USING btree (user_id);


--
-- Name: ix_teams_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teams_id ON public.teams USING btree (id);


--
-- Name: ix_teams_league_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teams_league_type ON public.teams USING btree (league_type);


--
-- Name: ix_terms_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_terms_id ON public.terms USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_league_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_league_type ON public.users USING btree (league_type);


--
-- Name: ix_users_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_team_id ON public.users USING btree (team_id);


--
-- Name: ix_weekly_snippets_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_weekly_snippets_id ON public.weekly_snippets USING btree (id);


--
-- Name: ix_weekly_snippets_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_weekly_snippets_user_id ON public.weekly_snippets USING btree (user_id);


--
-- Name: ix_weekly_snippets_week; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_weekly_snippets_week ON public.weekly_snippets USING btree (week);


--
-- Name: ux_peer_evaluation_sessions_access_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_peer_evaluation_sessions_access_token ON public.peer_evaluation_sessions USING btree (access_token);


--
-- Name: ux_teams_invite_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_teams_invite_code ON public.teams USING btree (invite_code);


--
-- Name: ix_realtime_subscription_entity; Type: INDEX; Schema: realtime; Owner: -
--

CREATE INDEX ix_realtime_subscription_entity ON realtime.subscription USING btree (entity);


--
-- Name: messages_inserted_at_topic_index; Type: INDEX; Schema: realtime; Owner: -
--

CREATE INDEX messages_inserted_at_topic_index ON ONLY realtime.messages USING btree (inserted_at DESC, topic) WHERE ((extension = 'broadcast'::text) AND (private IS TRUE));


--
-- Name: subscription_subscription_id_entity_filters_action_filter_key; Type: INDEX; Schema: realtime; Owner: -
--

CREATE UNIQUE INDEX subscription_subscription_id_entity_filters_action_filter_key ON realtime.subscription USING btree (subscription_id, entity, filters, action_filter);


--
-- Name: bname; Type: INDEX; Schema: storage; Owner: -
--

CREATE UNIQUE INDEX bname ON storage.buckets USING btree (name);


--
-- Name: bucketid_objname; Type: INDEX; Schema: storage; Owner: -
--

CREATE UNIQUE INDEX bucketid_objname ON storage.objects USING btree (bucket_id, name);


--
-- Name: buckets_analytics_unique_name_idx; Type: INDEX; Schema: storage; Owner: -
--

CREATE UNIQUE INDEX buckets_analytics_unique_name_idx ON storage.buckets_analytics USING btree (name) WHERE (deleted_at IS NULL);


--
-- Name: idx_multipart_uploads_list; Type: INDEX; Schema: storage; Owner: -
--

CREATE INDEX idx_multipart_uploads_list ON storage.s3_multipart_uploads USING btree (bucket_id, key, created_at);


--
-- Name: idx_objects_bucket_id_name; Type: INDEX; Schema: storage; Owner: -
--

CREATE INDEX idx_objects_bucket_id_name ON storage.objects USING btree (bucket_id, name COLLATE "C");


--
-- Name: idx_objects_bucket_id_name_lower; Type: INDEX; Schema: storage; Owner: -
--

CREATE INDEX idx_objects_bucket_id_name_lower ON storage.objects USING btree (bucket_id, lower(name) COLLATE "C");


--
-- Name: name_prefix_search; Type: INDEX; Schema: storage; Owner: -
--

CREATE INDEX name_prefix_search ON storage.objects USING btree (name text_pattern_ops);


--
-- Name: vector_indexes_name_bucket_id_idx; Type: INDEX; Schema: storage; Owner: -
--

CREATE UNIQUE INDEX vector_indexes_name_bucket_id_idx ON storage.vector_indexes USING btree (name, bucket_id);


--
-- Name: subscription tr_check_filters; Type: TRIGGER; Schema: realtime; Owner: -
--

CREATE TRIGGER tr_check_filters BEFORE INSERT OR UPDATE ON realtime.subscription FOR EACH ROW EXECUTE FUNCTION realtime.subscription_check_filters();


--
-- Name: buckets enforce_bucket_name_length_trigger; Type: TRIGGER; Schema: storage; Owner: -
--

CREATE TRIGGER enforce_bucket_name_length_trigger BEFORE INSERT OR UPDATE OF name ON storage.buckets FOR EACH ROW EXECUTE FUNCTION storage.enforce_bucket_name_length();


--
-- Name: buckets protect_buckets_delete; Type: TRIGGER; Schema: storage; Owner: -
--

CREATE TRIGGER protect_buckets_delete BEFORE DELETE ON storage.buckets FOR EACH STATEMENT EXECUTE FUNCTION storage.protect_delete();


--
-- Name: objects protect_objects_delete; Type: TRIGGER; Schema: storage; Owner: -
--

CREATE TRIGGER protect_objects_delete BEFORE DELETE ON storage.objects FOR EACH STATEMENT EXECUTE FUNCTION storage.protect_delete();


--
-- Name: objects update_objects_updated_at; Type: TRIGGER; Schema: storage; Owner: -
--

CREATE TRIGGER update_objects_updated_at BEFORE UPDATE ON storage.objects FOR EACH ROW EXECUTE FUNCTION storage.update_updated_at_column();


--
-- Name: identities identities_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: mfa_amr_claims mfa_amr_claims_session_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT mfa_amr_claims_session_id_fkey FOREIGN KEY (session_id) REFERENCES auth.sessions(id) ON DELETE CASCADE;


--
-- Name: mfa_challenges mfa_challenges_auth_factor_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_challenges
    ADD CONSTRAINT mfa_challenges_auth_factor_id_fkey FOREIGN KEY (factor_id) REFERENCES auth.mfa_factors(id) ON DELETE CASCADE;


--
-- Name: mfa_factors mfa_factors_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: oauth_authorizations oauth_authorizations_client_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_authorizations
    ADD CONSTRAINT oauth_authorizations_client_id_fkey FOREIGN KEY (client_id) REFERENCES auth.oauth_clients(id) ON DELETE CASCADE;


--
-- Name: oauth_authorizations oauth_authorizations_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_authorizations
    ADD CONSTRAINT oauth_authorizations_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: oauth_consents oauth_consents_client_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_consents
    ADD CONSTRAINT oauth_consents_client_id_fkey FOREIGN KEY (client_id) REFERENCES auth.oauth_clients(id) ON DELETE CASCADE;


--
-- Name: oauth_consents oauth_consents_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.oauth_consents
    ADD CONSTRAINT oauth_consents_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: one_time_tokens one_time_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.one_time_tokens
    ADD CONSTRAINT one_time_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: refresh_tokens refresh_tokens_session_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_session_id_fkey FOREIGN KEY (session_id) REFERENCES auth.sessions(id) ON DELETE CASCADE;


--
-- Name: saml_providers saml_providers_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;


--
-- Name: saml_relay_states saml_relay_states_flow_state_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_flow_state_id_fkey FOREIGN KEY (flow_state_id) REFERENCES auth.flow_state(id) ON DELETE CASCADE;


--
-- Name: saml_relay_states saml_relay_states_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_oauth_client_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sessions
    ADD CONSTRAINT sessions_oauth_client_id_fkey FOREIGN KEY (oauth_client_id) REFERENCES auth.oauth_clients(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: sso_domains sso_domains_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: -
--

ALTER TABLE ONLY auth.sso_domains
    ADD CONSTRAINT sso_domains_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;


--
-- Name: achievement_grants achievement_grants_achievement_definition_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.achievement_grants
    ADD CONSTRAINT achievement_grants_achievement_definition_id_fkey FOREIGN KEY (achievement_definition_id) REFERENCES public.achievement_definitions(id);


--
-- Name: achievement_grants achievement_grants_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.achievement_grants
    ADD CONSTRAINT achievement_grants_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: api_tokens api_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_tokens
    ADD CONSTRAINT api_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: comments comments_daily_snippet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_daily_snippet_id_fkey FOREIGN KEY (daily_snippet_id) REFERENCES public.daily_snippets(id);


--
-- Name: comments comments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: comments comments_weekly_snippet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_weekly_snippet_id_fkey FOREIGN KEY (weekly_snippet_id) REFERENCES public.weekly_snippets(id);


--
-- Name: consents consents_term_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consents
    ADD CONSTRAINT consents_term_id_fkey FOREIGN KEY (term_id) REFERENCES public.terms(id);


--
-- Name: consents consents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consents
    ADD CONSTRAINT consents_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: daily_snippets daily_snippets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_snippets
    ADD CONSTRAINT daily_snippets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notification_settings notification_settings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_settings
    ADD CONSTRAINT notification_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notifications notifications_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(id);


--
-- Name: notifications notifications_comment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES public.comments(id);


--
-- Name: notifications notifications_daily_snippet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_daily_snippet_id_fkey FOREIGN KEY (daily_snippet_id) REFERENCES public.daily_snippets(id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: notifications notifications_weekly_snippet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_weekly_snippet_id_fkey FOREIGN KEY (weekly_snippet_id) REFERENCES public.weekly_snippets(id);


--
-- Name: peer_evaluation_session_members peer_evaluation_session_members_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_session_members
    ADD CONSTRAINT peer_evaluation_session_members_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.peer_evaluation_sessions(id);


--
-- Name: peer_evaluation_session_members peer_evaluation_session_members_student_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_session_members
    ADD CONSTRAINT peer_evaluation_session_members_student_user_id_fkey FOREIGN KEY (student_user_id) REFERENCES public.users(id);


--
-- Name: peer_evaluation_sessions peer_evaluation_sessions_professor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_sessions
    ADD CONSTRAINT peer_evaluation_sessions_professor_user_id_fkey FOREIGN KEY (professor_user_id) REFERENCES public.users(id);


--
-- Name: peer_evaluation_submissions peer_evaluation_submissions_evaluatee_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_submissions
    ADD CONSTRAINT peer_evaluation_submissions_evaluatee_user_id_fkey FOREIGN KEY (evaluatee_user_id) REFERENCES public.users(id);


--
-- Name: peer_evaluation_submissions peer_evaluation_submissions_evaluator_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_submissions
    ADD CONSTRAINT peer_evaluation_submissions_evaluator_user_id_fkey FOREIGN KEY (evaluator_user_id) REFERENCES public.users(id);


--
-- Name: peer_evaluation_submissions peer_evaluation_submissions_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peer_evaluation_submissions
    ADD CONSTRAINT peer_evaluation_submissions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.peer_evaluation_sessions(id);


--
-- Name: student_risk_snapshots student_risk_snapshots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_risk_snapshots
    ADD CONSTRAINT student_risk_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: users users_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id);


--
-- Name: weekly_snippets weekly_snippets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.weekly_snippets
    ADD CONSTRAINT weekly_snippets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: objects objects_bucketId_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.objects
    ADD CONSTRAINT "objects_bucketId_fkey" FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);


--
-- Name: s3_multipart_uploads s3_multipart_uploads_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads
    ADD CONSTRAINT s3_multipart_uploads_bucket_id_fkey FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_bucket_id_fkey FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_upload_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_upload_id_fkey FOREIGN KEY (upload_id) REFERENCES storage.s3_multipart_uploads(id) ON DELETE CASCADE;


--
-- Name: vector_indexes vector_indexes_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.vector_indexes
    ADD CONSTRAINT vector_indexes_bucket_id_fkey FOREIGN KEY (bucket_id) REFERENCES storage.buckets_vectors(id);


--
-- Name: audit_log_entries; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.audit_log_entries ENABLE ROW LEVEL SECURITY;

--
-- Name: flow_state; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.flow_state ENABLE ROW LEVEL SECURITY;

--
-- Name: identities; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.identities ENABLE ROW LEVEL SECURITY;

--
-- Name: instances; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.instances ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_amr_claims; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.mfa_amr_claims ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_challenges; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.mfa_challenges ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_factors; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.mfa_factors ENABLE ROW LEVEL SECURITY;

--
-- Name: one_time_tokens; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.one_time_tokens ENABLE ROW LEVEL SECURITY;

--
-- Name: refresh_tokens; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.refresh_tokens ENABLE ROW LEVEL SECURITY;

--
-- Name: saml_providers; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.saml_providers ENABLE ROW LEVEL SECURITY;

--
-- Name: saml_relay_states; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.saml_relay_states ENABLE ROW LEVEL SECURITY;

--
-- Name: schema_migrations; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.schema_migrations ENABLE ROW LEVEL SECURITY;

--
-- Name: sessions; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.sessions ENABLE ROW LEVEL SECURITY;

--
-- Name: sso_domains; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.sso_domains ENABLE ROW LEVEL SECURITY;

--
-- Name: sso_providers; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.sso_providers ENABLE ROW LEVEL SECURITY;

--
-- Name: users; Type: ROW SECURITY; Schema: auth; Owner: -
--

ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;

--
-- Name: messages; Type: ROW SECURITY; Schema: realtime; Owner: -
--

ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY;

--
-- Name: buckets; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.buckets ENABLE ROW LEVEL SECURITY;

--
-- Name: buckets_analytics; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.buckets_analytics ENABLE ROW LEVEL SECURITY;

--
-- Name: buckets_vectors; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.buckets_vectors ENABLE ROW LEVEL SECURITY;

--
-- Name: migrations; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.migrations ENABLE ROW LEVEL SECURITY;

--
-- Name: objects; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

--
-- Name: s3_multipart_uploads; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.s3_multipart_uploads ENABLE ROW LEVEL SECURITY;

--
-- Name: s3_multipart_uploads_parts; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.s3_multipart_uploads_parts ENABLE ROW LEVEL SECURITY;

--
-- Name: vector_indexes; Type: ROW SECURITY; Schema: storage; Owner: -
--

ALTER TABLE storage.vector_indexes ENABLE ROW LEVEL SECURITY;

--
-- Name: issue_graphql_placeholder; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_graphql_placeholder ON sql_drop
         WHEN TAG IN ('DROP EXTENSION')
   EXECUTE FUNCTION extensions.set_graphql_placeholder();


--
-- Name: issue_pg_cron_access; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_pg_cron_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_cron_access();


--
-- Name: issue_pg_graphql_access; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_pg_graphql_access ON ddl_command_end
         WHEN TAG IN ('CREATE FUNCTION')
   EXECUTE FUNCTION extensions.grant_pg_graphql_access();


--
-- Name: issue_pg_net_access; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER issue_pg_net_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_net_access();


--
-- Name: pgrst_ddl_watch; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER pgrst_ddl_watch ON ddl_command_end
   EXECUTE FUNCTION extensions.pgrst_ddl_watch();


--
-- Name: pgrst_drop_watch; Type: EVENT TRIGGER; Schema: -; Owner: -
--

CREATE EVENT TRIGGER pgrst_drop_watch ON sql_drop
   EXECUTE FUNCTION extensions.pgrst_drop_watch();


--
-- PostgreSQL database dump complete
--

\unrestrict QFafwNu6ErhifFMsbFtj7BZ8bhWG9wiSQ4UWkxbjdGqeNYdWBdvifa6saYxyI9R

