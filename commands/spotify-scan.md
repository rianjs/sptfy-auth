---
allowed-tools: Bash(python3:*), Bash(curl:*)
description: Scan Spotify playlists for radio show tracks and propose standalone replacements
argument-hint: [playlist name]
---

# Spotify Playlist Scanner

You are scanning the user's Spotify playlists to find tracks saved from radio show compilations (ASOT, Find Your Harmony, Corsten's Countdown, ABGT, etc.) and proposing swaps to standalone releases (extended mix, radio edit, or original).

## Target playlist
$ARGUMENTS

## Step 1: Authenticate

Get a valid Spotify access token:

```bash
python3 ~/dev/sptfy-auth/spotify_auth.py token
```

If this fails, tell the user to run `python3 ~/dev/sptfy-auth/spotify_auth.py login --client-id <CLIENT_ID>` first.

Store the token in a variable for subsequent curl calls.

## Step 2: Find the target playlist

If `$ARGUMENTS` is provided, search for a matching playlist. Otherwise, list playlists and ask the user which one(s) to scan.

```bash
curl -s -H "Authorization: Bearer $TOKEN" "https://api.spotify.com/v1/me/playlists?limit=50"
```

Paginate using the `next` URL if needed. Match playlist names case-insensitively.

## Step 3: Fetch all tracks

```bash
curl -s -H "Authorization: Bearer $TOKEN" "https://api.spotify.com/v1/playlists/$PLAYLIST_ID/tracks?limit=100"
```

Paginate through all tracks. For each track, capture:
- Track ID and URI
- Track name
- Artists (names and IDs)
- Album name, ID, and type (`album`, `single`, or `compilation`)
- Track position in the playlist
- Duration

## Step 4: Identify radio show tracks

Analyze each track's metadata to determine if it's from a radio show compilation rather than a standalone release. You are the detection engine — use your contextual understanding. Signals include:

- **Album type is `compilation`** and the album name looks like a radio show episode (contains episode numbers, show names like "A State of Trance", "Find Your Harmony", "Group Therapy", "Corsten's Countdown", etc.)
- **Track title contains a show-specific parenthetical** like `(ASOT 1263)`, `(FYHTOP2025)`, `(ABGT550)` — NOT standard mix descriptors like `(Extended Mix)`, `(Radio Edit)`, `(Remix)`, `(Original Mix)`, `(Club Mix)`, `(Acoustic)`, `(Live)`
- **Track duration is unusually short** for an electronic track (under 3 minutes) which might indicate a radio show edit

If uncertain about a track, include it for review — the user can always skip it.

Present a summary of flagged tracks before proceeding.

## Step 5: Search for standalone replacements

For each flagged track:

1. Extract the base song name by removing the show parenthetical from the title
2. Identify the "real" artists — the show host (e.g. Armin van Buuren for ASOT, Andrew Rayel for FYH) may be listed as an artist on the compilation but not on the standalone release
3. Search Spotify:

```bash
curl -s -H "Authorization: Bearer $TOKEN" "https://api.spotify.com/v1/search?type=track&q=QUERY&limit=10"
```

Try these search queries in order:
- `"{base song name}" artist:{real artist}` — most specific
- `"{base song name} Extended Mix" artist:{real artist}` — look for extended
- `"{base song name}"` — broader fallback

4. From results, filter for tracks that are NOT from compilation albums. Prefer:
   - Extended Mix > Radio Edit > Original (for trance/electronica, extended mixes are usually preferred)
   - Same original artists
   - From `album` or `single` type releases, not compilations

## Step 6: Propose swaps

For each flagged track with candidates found, present the swap proposal to the user using AskUserQuestion. Show:
- Original: track name, artists, album, duration
- Proposed replacement: track name, artists, album, duration

Let the user approve or skip each swap. If multiple candidates exist, let them choose.

## Step 7: Apply approved swaps

For each approved swap:

1. Remove the old track at its position:
```bash
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"tracks":[{"uri":"OLD_TRACK_URI","positions":[POSITION]}]}' \
  "https://api.spotify.com/v1/playlists/$PLAYLIST_ID/tracks"
```

2. Add the new track at the same position:
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"uris":["NEW_TRACK_URI"],"position":POSITION}' \
  "https://api.spotify.com/v1/playlists/$PLAYLIST_ID/tracks"
```

**Important**: Process swaps one at a time from the END of the playlist toward the beginning, so that position indices remain valid as you make changes.

## Notes

- The Spotify API rate limit is generous for personal use but if you get 429 responses, wait and retry
- Track URIs look like `spotify:track:6rqhFgbbKwnb9MLmUQDhG6`
- Album types: `album` (standard release), `single` (single/EP), `compilation` (various artists / radio shows)
- All curl calls use the base URL `https://api.spotify.com/v1`
