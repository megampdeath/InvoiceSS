do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'invoice_app') then
    create role invoice_app login password '16b1438382d34ca9bedaa24188d7ca26bd981eb0' bypassrls;
  else
    alter role invoice_app with login password '16b1438382d34ca9bedaa24188d7ca26bd981eb0' bypassrls;
  end if;
end
$$;
grant usage on schema public to invoice_app;
grant all privileges on all tables in schema public to invoice_app;
grant all privileges on all sequences in schema public to invoice_app;
alter default privileges in schema public grant all privileges on tables to invoice_app;
alter default privileges in schema public grant all privileges on sequences to invoice_app;
