# Calendar App — Claude Guidelines

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
