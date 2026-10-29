# Family Ombi notification preferences

The operator requires each genuine family Plex account to have its own Discord
account number in Ombi's notification preferences. Store the number independently
of notification enablement. Notification sending remains disabled unless separately
requested. Never create local lookalike users or request family Plex passwords.

Earlier context: docs/TEST_RESULTS.md, section "2026-10-28: matched Plex availability,
native family identities and routing" records the successful native family import,
roles and disabled Discord preferences on Ombi4.53.10. Earlier checkpoint text says
to collect optional IDs securely; it does not contain the actual account numbers.
The prior adapter posted an empty Discord target. That is not proof that the
operator's account numbers were saved.

## API method

Use the authenticated Ombi administrator API. Resolve each username (lenora8,
rebel739, beanie08) to its current Ombi user ID; require userType2 (Plex).

Read: GET /api/v1/Identity/notificationpreferences/{ombiUserId}

Write: POST /api/v1/Identity/NotificationPreferences

The body is an array, not one object:

```json
[
  {
    "userId": "RESOLVED_OMBI_USER_ID",
    "agent": 1,
    "value": "DISCORD_NUMERIC_ACCOUNT_ID",
    "enabled": false
  }
]
```

agent1 is Discord. Require the POST to return true and GET the same user's
preferences again. Check exactly one Discord row, the exact target value and
notifications disabled. Do not print targets in evidence or checkpoint JSON.
Adapter: installarr/ombi_family.py, ensure_discord_preference. configure_family
uses the same helper alongside dynamically resolved roles/root/profile overrides.
An omitted target preserves an already saved ID while keeping notifications off.

## Private collection and reuse

The normal guided install collects optional IDs when family presets are selected.
To supply them independently from this checkout:

```sh
sudo ./installarr.sh family-accounts
```

Hidden prompts collect IDs. The root-owned0600 file is:
/var/lib/installarr-setup/family/family.json inside a0700 directory. Its mapping keys
are the three Plex usernames; values are numeric Discord IDs. Existing valid files
are reused without recollection. Nonsecret configuration contains only the absolute
ombi_family_preferences_file path, not the account numbers.

At the operator's request, the live retained Ombi was read: all three Discord target
values were empty and notifications disabled. Relevant private Ombi/family/provider
fixture JSON stores contained no reusable Discord targets. No production system
was inspected. Actual target POST/readback awaits local collection; synthetic
unit tests already cover distinct targets, disabled flags, reruns, preservation,
private storage, invalid input and no identifiers in normal result/checkpoints.


## Locally supplied targets applied

Operator supplied IDs privately for rebel739 and beanie08. Both were POSTed to
these native Plex users' notification preferences, exact-value GET readback passed,
repeat reconciliation was stable, and both persisted through an actual Ombi service
restart. Notifications remain disabled. No ID values were printed or saved in
nonsecret evidence. lenora8 was omitted; operator explicitly confirmed leaving it
blank for now. Root-private reusable store remains
/var/lib/installarr-setup/family/family.json. This supersedes the earlier pending
collection status above. Family roles/root/profile settings were not changed by
this target-only update.
