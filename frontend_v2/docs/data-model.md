# Owner-scoped data model

Every private record is stored under the anonymous `OwnerId` supplied separately to repository methods. The server issues that identifier in a signed, HttpOnly, SameSite=Lax cookie. The service does not create an account or login.

- `Profile`: display name, research interests, consent timestamp.
- `CvAsset`: private bytes, file metadata, owner, identifier.
- `TargetLab`, `ContactDraft`, `ScheduleItem`: owner-scoped downstream records used by later features.

The judge build persists each owner aggregate to a server-side JSON file configured by `PROFILE_DATA_FILE`. Writes use a temporary file followed by an atomic rename, so profiles and private CV bytes survive a server restart. Every write validates that the record owner matches the signed owner cookie, and reset physically removes the complete aggregate. A database and private object-store adapter can replace this file repository without changing the feature service.

CV bytes never appear in API responses or direct object URLs. Uploads allow PDF or plain text up to 5 MiB. Reset removes the complete owner aggregate, including uploaded bytes and derived records.
