insert into storage.buckets (id, name, public)
values
  ('invoice-originals', 'invoice-originals', false),
  ('invoice-exports', 'invoice-exports', false),
  ('ocr-raw-results', 'ocr-raw-results', false)
on conflict (id) do update set public = excluded.public;

create policy "private originals are backend managed" on storage.objects
  for all using (bucket_id = 'invoice-originals' and auth.role() = 'service_role')
  with check (bucket_id = 'invoice-originals' and auth.role() = 'service_role');

create policy "private exports are backend managed" on storage.objects
  for all using (bucket_id = 'invoice-exports' and auth.role() = 'service_role')
  with check (bucket_id = 'invoice-exports' and auth.role() = 'service_role');

create policy "private ocr raw results are backend managed" on storage.objects
  for all using (bucket_id = 'ocr-raw-results' and auth.role() = 'service_role')
  with check (bucket_id = 'ocr-raw-results' and auth.role() = 'service_role');
