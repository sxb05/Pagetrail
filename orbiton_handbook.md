# Orbiton Platform Operations Handbook (v4.2)

## 1. Overview and Ownership
The Orbiton Platform Operations Handbook (version 4.2) is maintained by the Platform Reliability team, led by Priya Venkataraman. The on-call rotation changes weekly, with handover every Monday at 10:00 IST. Operational questions go to the Slack channel #orbiton-ops, and pages are sent through the PagerBridge tool.

## 2. Authentication Errors
ERR_AUTH_4012 means the access token has expired. Clients should call /v2/token/refresh with their refresh token to obtain a new one. ERR_AUTH_4031 means the token is valid but lacks the required scope. ERR_AUTH_4090 means the account is locked after 5 failed login attempts; the lock clears automatically after 30 minutes.

## 3. Rate Limiting
The Free tier allows 60 requests per minute, the Pro tier allows 600 requests per minute, and the Enterprise tier allows 6000 requests per minute. Bursts are measured over a 10-second window. When a burst is exceeded the API returns ERR_RATE_429A together with the X-Orbiton-Retry-After header, which gives the wait time in seconds.

## 4. Database
The primary database is a PostgreSQL 15 cluster named Kestrel running in ap-south-1, with a read replica named Merlin. Automatic failover completes within 45 seconds. Nightly backups run at 02:30 UTC and are kept for 35 days. ERR_DB_5203 is raised when replication lag exceeds 30 seconds.

## 5. Caching
The caching layer is a Redis cluster named Falcon. The default time-to-live is 900 seconds and the eviction policy is allkeys-lru. ERR_CACHE_7710 signals a cache stampede, which is mitigated by request coalescing.

## 6. Deployments
Deployments use a blue-green strategy. The standard deploy window is Tuesday and Thursday from 14:00 to 16:00 IST. A change freeze applies from December 20 to January 3. Every release starts as a canary serving 5% of traffic for 20 minutes and needs approval from two reviewers. To revert, run orbitctl rollback --to-previous.

## 7. Monitoring and Alerting
Dashboards live in Grafana under the name Skyline. An alert fires when p95 latency passes 800 ms. An error rate above 2% for 5 minutes is classified as SEV2. SEV1 means a total outage or data loss. The on-call engineer must acknowledge SEV1 within 5 minutes and SEV2 within 15 minutes.

## 8. Incident Process
Each incident has an incident commander. For SEV1 the status page is updated every 30 minutes. A blameless postmortem is due within 5 business days and uses the template named Lantern.

## 9. Data Retention and Privacy
Application logs are retained for 90 days and audit logs for 400 days. Personal data is encrypted with AES-256-GCM using the KMS alias orbiton-prod-key, which is rotated every 180 days. Customer deletion requests are completed within 30 days.

## 10. Billing
Invoices are generated on the 1st of each month. The Pro plan costs $49 per month, and Enterprise pricing is custom. Usage beyond quota is billed at $0.80 per 1,000 requests. ERR_BILL_6104 means the payment method was declined; the system retries 3 times over 7 days.

## 11. File Uploads
The maximum upload size is 25 MB. Allowed file types are pdf, docx, png and csv. Files are stored in the bucket orbiton-uploads-prod and scanned by ClamShield. ERR_UPLOAD_3307 means the file type is not supported, and ERR_UPLOAD_3315 means the virus scan failed.

## 12. Webhooks
Webhook payloads are signed with HMAC-SHA256 and sent in the X-Orbiton-Signature header. Payloads can be at most 256 KB. If delivery fails, Orbiton retries 5 times with exponential backoff starting at 2 seconds. ERR_HOOK_8801 means the receiving endpoint did not answer within 10 seconds.

## 13. Regions and Compliance
Orbiton runs in three regions: ap-south-1 (Mumbai), eu-west-1 (Ireland) and us-east-2 (Ohio). Tenant data residency is pinned to one region. The platform holds a SOC 2 Type II report, audited by Northgate Assurance.

## 14. Support
Enterprise customers get 24x7 support with a first-response SLA of 1 hour. Pro customers get support from 09:00 to 18:00 IST, Monday to Friday, with a first response within 8 business hours. Contact support@orbiton.example.
