# Calendar App — Claude Guidelines

## User Defaults

- **Email:** `dhopkins@vendasta.com`
- **Timezone:** `America/Swift_Current` (CST, UTC-6)

## Google Calendar API Defaults

- **Always include the organizer as an attendee.** When creating events via the API, add `dhopkins@vendasta.com` to the attendees list. The API does not automatically include the organizer.
- **Always include a Google Meet link.** When creating events, set `conferenceData` with `createRequest` and use `conferenceDataVersion=1` on the insert call. Example:
  ```python
  event['conferenceData'] = {
      'createRequest': {
          'requestId': '<unique-id>',
          'conferenceSolutionKey': {'type': 'hangoutsMeet'},
      }
  }
  service.events().insert(
      calendarId='primary',
      body=event,
      sendUpdates='all',
      conferenceDataVersion=1,
  ).execute()
  ```

## Scheduling New Meetings

- **Use the FreeBusy API** to check attendee availability before booking. Query all attendees (including self) for the desired window, then find slots where everyone is free.

## Recurring Events

- **`_R` prefixed event IDs cannot have their start time changed.** These are recurring events created from a "this and following" edit. The API returns "Invalid start time" on update. The workaround is to delete the old recurring series and create a new one with the desired time.
