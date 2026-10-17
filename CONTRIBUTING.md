# Contributing

Changes are welcome by pull request. Every pull request runs the browser
walk-through in `checks/journey.py` (including the accessibility checks);
it has to pass before anything is merged.

Keep the site plain: HTML and CSS only, no JavaScript, no outside fonts,
images or trackers. The security headers in `public/_headers` block scripts,
so any script added would not run.

## Names

Every OSCivic project name is "OS" plus a CamelCase noun: OSGovt, OSCivic,
OSFairground, OSRoster, OSNeighbors. Write domains and repositories that way
wherever people read them: OSGovt.com, OSCivic.com, OSFairground.com,
OSGovt/OSGovt.com. Web addresses (https://osgovt.com, utopia.osgovt.com) and
email addresses stay lowercase. If something seems to call for a different
format, ask in an issue before using it.

The walk-through's `names` step enforces this on every page.

By contributing you agree your work is released under the
[GNU Affero General Public License v3.0 or later](LICENSE).
