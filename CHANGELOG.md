# Changelog

All notable changes to NosyPet are recorded here.

## [Unreleased] · Quality pass

### Added
- Test suite: 25 tests covering signals, decay, services, views, API, rate limit
- `PetActionLog` model and admin for action history
- Heal action: revive a fainted or near-dead pet for 20 coins
- Rename pet from the dashboard via a dialog
- Password reset flow (request, done, confirm, complete templates)
- Email field on signup, console email backend in dev
- Mobile hamburger nav with focus rings for keyboard users
- 404 and 500 templates
- Inline-SVG favicon and Open Graph meta tags
- GitHub Actions CI: lint, system check, migrations check, tests
- Ruff config (`pyproject.toml`)
- Structured logging config

### Changed
- Decay rates tuned (hunger 1.2, happiness 0.9, energy 0.7 per minute)
- XP curve made exponential so leveling is meaningful
- Mutating API endpoints now run inside a transaction with `select_for_update`
- All mutating endpoints rate-limited per user
- Polling pauses while the tab is hidden
- Toast stays on screen 3.5 seconds for level-ups (1.8 s otherwise)
- Production refuses to boot with the default insecure SECRET_KEY
- Static files use ManifestStaticFilesStorage only when `DEBUG=False`

### Fixed
- Decay no longer rounds fractional points down spuriously
  (`int(80 - 0.01) == 79` bug)
- Dashboard creates a pet on demand for petless superusers
- Heal button shows when pet is fainted or any stat below 20

### Removed
- Shop feature (per request); coins remain on the model and now have a
  use through the Heal action
