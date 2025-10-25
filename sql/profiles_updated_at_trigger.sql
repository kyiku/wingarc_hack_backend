-- Ensure updated_at auto-updates on row modifications for public.profiles

-- 1) Trigger function
create or replace function public.trigger_set_timestamp()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := timezone('utc', now());
  return new;
end;
$$;

-- 2) Trigger
drop trigger if exists set_timestamp_on_profiles on public.profiles;
create trigger set_timestamp_on_profiles
before update on public.profiles
for each row
execute function public.trigger_set_timestamp();

-- Optional: ensure column has a sane default on insert
alter table public.profiles
  alter column updated_at set default timezone('utc', now());

