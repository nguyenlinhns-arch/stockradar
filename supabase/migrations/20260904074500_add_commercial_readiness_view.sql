create view private.commercial_readiness_v1
with (security_invoker = true)
as
select
  case
    when s.data_ready
      and s.data_rights_approved
      and s.compliance_approved
      and s.api_enabled
      and s.active_manifest_ref is not null
      and s.active_snapshot_id is not null
    then 'READY'
    else 'BLOCKED'
  end as market_data_status,
  case
    when e.provider_configured
      and e.sender_domain_verified
      and e.unsubscribe_ready
      and e.bounce_complaint_ready
      and e.compliance_approved
      and e.sending_enabled
    then 'READY'
    else 'BLOCKED'
  end as email_status,
  case
    when b.provider_configured
      and b.webhook_signature_verified
      and b.reconciliation_ready
      and b.refund_chargeback_ready
      and b.tax_compliance_approved
      and b.checkout_enabled
    then 'READY'
    else 'BLOCKED'
  end as billing_status,
  case
    when s.data_ready
      and s.data_rights_approved
      and s.compliance_approved
      and s.api_enabled
      and s.active_manifest_ref is not null
      and s.active_snapshot_id is not null
      and e.provider_configured
      and e.sender_domain_verified
      and e.unsubscribe_ready
      and e.bounce_complaint_ready
      and e.compliance_approved
      and e.sending_enabled
      and b.provider_configured
      and b.webhook_signature_verified
      and b.reconciliation_ready
      and b.refund_chargeback_ready
      and b.tax_compliance_approved
      and b.checkout_enabled
    then 'READY_TO_SELL'
    else 'BLOCKED'
  end as commercial_status,
  array_remove(array[
    case when not s.data_ready then 'MARKET_DATA_NOT_READY' end,
    case when not s.data_rights_approved then 'MARKET_DATA_RIGHTS_NOT_APPROVED' end,
    case when not s.compliance_approved then 'MARKET_DATA_COMPLIANCE_NOT_APPROVED' end,
    case when not s.api_enabled then 'STOCK_API_NOT_ENABLED' end,
    case when s.active_manifest_ref is null then 'ACTIVE_MANIFEST_MISSING' end,
    case when s.active_snapshot_id is null then 'ACTIVE_SNAPSHOT_MISSING' end,
    case when not e.provider_configured then 'EMAIL_PROVIDER_NOT_CONFIGURED' end,
    case when not e.sender_domain_verified then 'EMAIL_DOMAIN_NOT_VERIFIED' end,
    case when not e.unsubscribe_ready then 'EMAIL_UNSUBSCRIBE_NOT_READY' end,
    case when not e.bounce_complaint_ready then 'EMAIL_BOUNCE_COMPLAINT_NOT_READY' end,
    case when not e.compliance_approved then 'EMAIL_COMPLIANCE_NOT_APPROVED' end,
    case when not e.sending_enabled then 'EMAIL_SENDING_NOT_ENABLED' end,
    case when not b.provider_configured then 'BILLING_PROVIDER_NOT_CONFIGURED' end,
    case when not b.webhook_signature_verified then 'BILLING_WEBHOOK_NOT_VERIFIED' end,
    case when not b.reconciliation_ready then 'BILLING_RECONCILIATION_NOT_READY' end,
    case when not b.refund_chargeback_ready then 'BILLING_REFUND_CHARGEBACK_NOT_READY' end,
    case when not b.tax_compliance_approved then 'BILLING_TAX_COMPLIANCE_NOT_APPROVED' end,
    case when not b.checkout_enabled then 'CHECKOUT_NOT_ENABLED' end
  ], null) as blockers,
  greatest(s.updated_at, e.updated_at, b.updated_at) as last_gate_change_at
from private.stock_api_gate s
cross join private.email_delivery_gate e
cross join private.billing_gate b
where s.singleton = true
  and e.singleton = true
  and b.singleton = true;

revoke all on private.commercial_readiness_v1 from public, anon, authenticated;
