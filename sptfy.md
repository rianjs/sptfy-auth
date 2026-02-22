# sptfy — Spotify playlist CLI tool (future)

Plan for a full Go CLI tool following the conventions in `~/dev`. Saved for posterity — the current approach uses a Claude Code skill instead.

## Approach

Build a Go CLI tool (`sptfy`) using Cobra, keychain auth, `~/.config/sptfy/`, Makefile + GoReleaser. Talks to the Spotify Web API via `github.com/zmb3/spotify/v2`.

### Detection strategy (no hardcoded show names)

Use generic heuristics:

1. **Album type**: Spotify marks albums as `album`, `single`, or `compilation`. Radio show episodes are compilations.
2. **Album track count**: Radio show albums have many tracks (20+) from diverse artists.
3. **Title parentheticals**: Track titles contain show-like identifiers `(ASOT 1263)`, `(FYHTOP2025)` — NOT standard mix descriptors.
4. **Composite signal**: A track flagged by any combination gets searched for standalone versions.

### Replacement search strategy

1. Strip the show-like parenthetical from the track title -> base song name.
2. Identify the "real" artist(s).
3. Search Spotify for: `"{base song name}" {artist}` — look for matches on non-compilation albums.
4. Also try: `"{base song name} Extended Mix"`, `"{base song name} Radio Edit"`.
5. Rank candidates: prefer extended mix > radio edit > original, prefer same artists, prefer non-compilation albums.

## Commands

```
sptfy init                          # OAuth2 setup
sptfy config show                   # Show current config
sptfy config clear                  # Clear config + token

sptfy playlists                     # List user's playlists
sptfy tracks <playlist-name-or-id>  # List tracks in a playlist

sptfy scan <playlist-name-or-id>    # Scan playlist, output plan JSON
sptfy scan --all                    # Scan all user playlists

sptfy search "<query>"              # Search Spotify for tracks

sptfy replace <plan-file>           # Apply approved replacements from plan file
```

## Plan file format

`sptfy scan` outputs a JSON file:

```json
{
  "generated_at": "2026-02-22T10:30:00Z",
  "playlist": {
    "id": "abc123",
    "name": "Electronica 2026"
  },
  "replacements": [
    {
      "action": "replace",
      "original": {
        "id": "spotify:track:xxx",
        "name": "Dopamine Machine (ASOT 1263)",
        "artists": ["Armin van Buuren", "Lilly Palmer"],
        "album": "ASOT 1263 - A State of Trance Episode 1263",
        "album_type": "compilation",
        "position": 3,
        "duration_ms": 144000
      },
      "candidates": [
        {
          "id": "spotify:track:yyy",
          "name": "Dopamine Machine (Extended Mix)",
          "artists": ["Lilly Palmer"],
          "album": "Dopamine Machine",
          "album_type": "single",
          "duration_ms": 398000,
          "selected": true
        }
      ]
    }
  ]
}
```

## Project structure

```
~/dev/spotify-cli/
├── cmd/sptfy/main.go
├── internal/
│   ├── cmd/{root,initcmd,configcmd,playlists,tracks,scan,search,replace}/
│   ├── auth/auth.go
│   ├── config/config.go
│   ├── keychain/
│   ├── detector/detector.go
│   ├── matcher/matcher.go
│   ├── plan/plan.go
│   ├── output/output.go
│   └── version/version.go
├── Makefile
├── .goreleaser.yml
└── go.mod
```

## Auth flow

1. User creates Spotify Developer App at https://developer.spotify.com/dashboard
2. Sets redirect URI to `http://localhost:8765/callback`
3. Runs `sptfy init` — prompted for Client ID
4. Browser opens for consent, local server catches callback
5. Token stored in macOS Keychain (fallback: token.json)
6. Auto-refreshes via PersistentTokenSource

## Dependencies

- `github.com/zmb3/spotify/v2`
- `github.com/spf13/cobra`
- `github.com/fatih/color`
- `github.com/charmbracelet/huh`
- `golang.org/x/oauth2`
