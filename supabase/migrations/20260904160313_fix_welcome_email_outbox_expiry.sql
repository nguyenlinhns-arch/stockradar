alter table private.email_outbox
  alter column expires_at set default (now() + interval '24 hours');

comment on column private.email_outbox.expires_at is
  'Absolute delivery expiry. Defaults to 24 hours for transactional/welcome rows that omit an explicit window; product email enqueue RPCs still pass an explicit expiry.';
