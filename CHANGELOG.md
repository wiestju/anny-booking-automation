# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Opening mode** (`BOOKING_MODE=opening`): books at each floor's real
  `advance_start_time`, read live so it self-adjusts if the library shifts times.
- Multi-floor discovery: automatically finds and books across all bookable floors.
- **Floor preferences** (`FLOORS`) and **seat preferences** (`PREFERRED_RESOURCES`).
- **anny favorites**: automatically prioritizes seats/floors you starred in anny
  (`USE_ANNY_FAVORITES`), with a log line reminding you which ones are active.
- Pure, unit-tested selection helpers (`booking/selection.py`) and a test suite.
- CI (ruff + pytest across Python 3.10–3.12), `pyproject.toml`, and community docs
  (CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, DISCLAIMER).

### Changed
- Booking is now **calm**: one spot per time window, gentle concurrency, stop on
  first success. Removed all spamming, pre-firing, connection pre-warming, and the
  midnight retry-storm.

### Fixed
- Per-floor service ids: each resource is booked with its own floor's service.
- HTTP 429 handling no longer misclassified as "not yet open".
