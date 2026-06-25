create or replace function public.is_org_member(org_id text)
returns boolean
language sql
security definer
set search_path = public
as $$
  select exists (
    select 1
    from organization_members
    where organization_id = org_id
      and user_id = auth.uid()::text
  );
$$;

create or replace function public.has_org_role(org_id text, allowed_roles text[])
returns boolean
language sql
security definer
set search_path = public
as $$
  select exists (
    select 1
    from organization_members
    where organization_id = org_id
      and user_id = auth.uid()::text
      and role = any(allowed_roles)
  );
$$;

alter table users enable row level security;
alter table organizations enable row level security;
alter table organization_members enable row level security;
alter table invoices enable row level security;
alter table invoice_parties enable row level security;
alter table suppliers enable row level security;
alter table invoice_line_items enable row level security;
alter table invoice_tax_breakdowns enable row level security;
alter table extraction_fields enable row level security;
alter table extraction_warnings enable row level security;
alter table export_jobs enable row level security;
alter table usage_events enable row level security;
alter table audit_logs enable row level security;

create policy "users can read own profile" on users
  for select using (id = auth.uid()::text);

create policy "members can read organizations" on organizations
  for select using (is_org_member(id));

create policy "members can read memberships" on organization_members
  for select using (is_org_member(organization_id));

create policy "members can read invoices" on invoices
  for select using (is_org_member(organization_id));

create policy "contributors can write invoices" on invoices
  for all using (has_org_role(organization_id, array['owner','admin','member']))
  with check (has_org_role(organization_id, array['owner','admin','member']));

create policy "members can read invoice parties" on invoice_parties
  for select using (exists (select 1 from invoices where invoices.id = invoice_id and is_org_member(invoices.organization_id)));

create policy "contributors can write invoice parties" on invoice_parties
  for all using (exists (select 1 from invoices where invoices.id = invoice_id and has_org_role(invoices.organization_id, array['owner','admin','member'])))
  with check (exists (select 1 from invoices where invoices.id = invoice_id and has_org_role(invoices.organization_id, array['owner','admin','member'])));

create policy "members can read suppliers" on suppliers
  for select using (is_org_member(organization_id));

create policy "contributors can write suppliers" on suppliers
  for all using (has_org_role(organization_id, array['owner','admin','member']))
  with check (has_org_role(organization_id, array['owner','admin','member']));

create policy "members can read export jobs" on export_jobs
  for select using (is_org_member(organization_id));

create policy "contributors can create export jobs" on export_jobs
  for insert with check (has_org_role(organization_id, array['owner','admin','member']));
